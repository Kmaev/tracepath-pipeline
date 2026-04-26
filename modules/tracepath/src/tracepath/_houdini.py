import os
import re
from pathlib import Path

import hou

from tracepath import core_utils


# Generic functions for Load and Write USD HDAs in houdini

def get_node_env_data(node: hou.Node) -> dict:
    """
    Retrieve environment variables from HDA parameters.

    Args:
        node: Houdini TracePath Load USD Stage or USD Write HDA.

    Returns:
        dict: A dictionary containing:
        "pr_group", "pr_item", "pr_task" environment variables.
    """
    core_utils.check_required_env(["PR_GROUP", "PR_ITEM", "PR_TASK"])
    node_data = {
        "pr_group": node.parm("grp").eval(),
        "pr_item": node.parm("item").eval(),
        "pr_task": node.parm("task").eval()
    }
    return node_data


def get_manifest_context(node: hou.Node, templ) -> str:
    """
    Resolve the full context path for the USD shot manifest using template and environment values.
    Used in Houdini HDA.

    Args:
        node: A Houdini node from a TracePath Load USD Stage or USD Write HDA.
        templ: Template key used to look up a path structure definition.

    Returns:
        str: The resolved path to the main shot manifest folder.
    """
    env_vars = core_utils.get_env()
    node_vars = get_node_env_data(node)
    all_node_data = {**env_vars, **node_vars}

    templ_folder, _ = core_utils.get_path_structure_templ(templ)
    context = templ_folder.format(**all_node_data)

    return context


# Load USD Stage HDA

def set_latest_version(node: hou.Node, context: str) -> None:
    """
    Set the node's version parameter to the latest version found in the context folder. Used in Houdini HDA.

    Args:
        node: A Houdini node TracePath Load USD Stage or USD Write HDA.
        context: Task context path (Project/Group/Item/Task).
    """
    version = core_utils.get_latest_version_number(str(context))

    if not version:
        version = 1
    node.parm("version").set(version)


def load_shot_manifest(node: hou.Node) -> str:
    """
    Load the path to the main shot manifest file based on the version selected in the HDA.
    Used in Houdini HDA.

    Args:
        node: A Houdini node TracePath Load USD Stage or USD Write HDA.

    Returns:
        str: Path to the main shot manifest usd file.
    """
    context = get_manifest_context(node, "usd_shot_manifest_output")
    node_version = node.parm("version").evalAsString()
    file = core_utils.find_file_in_context(str(context), node_version)

    if not file or not Path(file).exists():
        raise RuntimeError(f"No matching file found for version '{node_version}' in: {context}")
    return str(file)


# Write USD HDA

def get_usd_output_path(node: hou.Node, template) -> str:
    """
    Solve the usd output file path using environment variables and the selected template.

    Args:
        node: A Houdini node TracePath Load USD Stage or USD Write HDA.
        template: The name of the template key to retrieve.

    Returns:
        str: A path to the usd file to write to.
    """
    env_vars = core_utils.get_env()
    node_vars = get_node_env_data(node)

    node_vars["name"] = node.parm("name").eval()
    node_vars["version"] = str(node.parm("version").eval()).zfill(3)
    node_vars["file_format"] = node.parm("format").evalAsString()
    node_vars["padding"] = ".$F4" if node.evalParm("trange") else ""
    all_node_data = {**env_vars, **node_vars}

    templ = core_utils.get_path_structure_templ(template)
    if not templ:
        raise RuntimeError(f"Template '{template}' not found.")
    output_path = templ.format(**all_node_data)
    return output_path


def get_first_frame_cache(node: hou.Node) -> float:
    """
    Get the first frame cache for a given node.

    This function is used to evaluate if just a single file cache or if it is a sequence should be written to disk.

    Args:
        node: A Houdini node TracePath Load USD Stage or USD Write HDA.

    Returns:
        float: A first frame of the cache.
    """
    first_frame = node.parm("f1").eval()
    cache_parm = node.parm("lopoutput").evalAtFrame(first_frame)
    return cache_parm


def apply_autoversion(node: hou.Node) -> None:
    """
    HDA call to trigger autoversion application, set an updated version value.

    Args:
        node: A Houdini node TracePath Load USD Stage or USD Write HDA.
    """
    version = 1
    if node.parm("autoversion").eval() == 1:
        context = Path(node.parm("lopoutput").evalAsString()).parent.parent
        if context.exists():
            latest_version = core_utils.get_latest_version_number(str(context))
            if latest_version:
                version = latest_version + 1
    else:
        version = node.parm("version").eval()

    node.parm("version").set(version)


def version_up_shot_manifest(node: hou.Node) -> str:
    """
    Create a versioned up output path.

    Using re extract the version number and increase the version. Used in Houdini HDA.

    Args:
        node: A Houdini node TracePath Load USD Stage or USD Write HDA.

    Returns:
        str: Versioned up main shot manifest output path.
    """
    new_output_path = ""
    context = Path(get_manifest_context(node, "usd_shot_manifest_output"))
    if context.exists():
        latest_version = core_utils.get_latest_version_number(str(context))
        if latest_version:
            output_path = core_utils.find_file_in_context(str(context), latest_version)
            if output_path:
                path = Path(output_path)
                parent_folder = path.parent
                file_name = path.name

                match = re.search(r"v(\d+)", parent_folder.name)

                if match:
                    version = match.group(1)
                    version_up = int(version) + (
                        1 if hou.frame() == node.parm("f1").eval() or node.parm("trange").eval() == 0 else 0)

                    new_version = str(version_up).zfill(len(version))
                    new_folder_name = parent_folder.name.replace(version, new_version)
                    new_folder = parent_folder.parent / new_folder_name

                    new_file_name = file_name.replace(f"v{version}", f"v{new_version}")
                    new_output_path = new_folder / new_file_name

    if not new_output_path:
        node_vars = {}
        node_vars["version"] = "001"
        node_vars["file_format"] = node.parm("format").evalAsString()

        _, templ_file = core_utils.get_path_structure_templ("usd_shot_manifest_output")
        new_file_path = Path(templ_file.format(**node_vars))
        new_output_path = context / new_file_path

    return str(new_output_path)


def find_stage_source_layer(node: hou.node) -> str:
    """
    Get the identifier of the USD layer on which the current edit was authored.

    Used in Houdini HDA to initialise a source layer for building the
    main shot manifest composition.

    Args:
        node: A Houdini node in LOP context.

    Returns:
        str: USD stage identifier.
    """
    return node.sourceLayer().identifier


# Publishing

def get_publish_key(node: hou.Node) -> str:
    """
    Helper function to get the publish key (consist of group and name)

    Args:
        node: A Houdini node TracePath USD Write HDA.
    Returns:
        str: A key combined from pr_group and pr_item.
    """
    node_data = get_node_env_data(node)
    return f"{node_data['pr_group']}_{node_data['pr_item']}"


def write_publish_comment(node: hou.Node) -> None:
    """
    Write a publishing comment from the node to metadata file.

    Args:
        node: A Houdini node TracePath USD Write HDA.
    """
    comment = node.parm("comment").eval()
    file = node.parm("shot_manifest_output").eval()

    data_folder = core_utils.get_show_data_folder()
    key = get_publish_key(node)

    published_data = core_utils.get_published_data(data_folder)
    published_data.setdefault(key, {})
    published_data[key][file] = comment

    core_utils.write_published_data(data_folder, published_data)
    node.parm("comment").set("")
    hou.ui.displayMessage(f"Shot manifest: \n{file} \npublished successfully!", severity=hou.severityType.Message)


def read_publish_comment(node: hou.Node) -> str | None:
    """
    Read published comment from the metadata file. Used in Houdini HDA

    Args:
        node: A Houdini node TracePath HDA.

    Returns:
        str | None: A comment from the published main shot manifest metadata file or None if no comment found.
    """
    file_path = node.parm("shot_manifest_read").evalAsString()
    data_folder = core_utils.get_show_data_folder()
    key = get_publish_key(node)
    published_data = core_utils.get_published_data(data_folder)

    file_to_comment = published_data.get(key, {})
    for f, comment in file_to_comment.items():
        if f == file_path:
            return comment

    return None


# Save HIP file

def get_current_file_name() -> str:
    """
    Retrieve HIPFILE name from $HIPNAME environment variable.

    Returns:
        str: hipfile name
    """
    hip_name = hou.getenv("HIPNAME")
    hip_name = "_".join(hip_name.split("_")[:-1])
    return hip_name


def is_fresh_scene() -> bool:
    """
    Check if the current Houdini session is a new scene
    (not yet saved to disk) or an existing saved scene.

    Returns:
        bool: True if the houdini session is a new scene False if it is a previously saved hip file.
    """
    path = hou.hipFile.name()
    path = os.path.exists(path)
    if path:
        return False
    return True


def hip_ext_from_session() -> str:
    """
    Check the license category of the current houdini session.
    Map the license category to the corresponding extension of the hip file.

    Returns:
        str: the .hip* extension for the current Houdini session.
    """
    if not hasattr(hou, "licenseCategory"):
        raise RuntimeError(
            "No valid Houdini license detected"
        )

    mapping = {
        hou.licenseCategoryType.Commercial: ".hip",
        hou.licenseCategoryType.Indie: ".hiplc",
        hou.licenseCategoryType.Apprentice: ".hipnc",
        hou.licenseCategoryType.Education: ".hipnc"
    }

    cat = hou.licenseCategory()
    try:
        return mapping[cat]
    except KeyError:
        raise RuntimeError(f"Unsupported/unknown license category: {cat!r}")


def save_scene(scene_path) -> None:
    """
    Save the current Houdini scene to the given path.

    Args:
        scene_path: Destination file path.
    """
    if not os.path.isdir(os.path.dirname(scene_path)):
        os.makedirs(os.path.dirname(scene_path))
    hou.hipFile.save(scene_path)
