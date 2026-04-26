import json
import logging
import os
import re
from pathlib import Path

logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")


# Generic functions to load environment and work with files in a project context

def get_env() -> dict:
    """
    Get environment used to set up a project context.

    Returns:
        dict: A dictionary containing:
            - "pr_projects_path": The root path to all projects, read from the PR_PROJECTS_PATH.
            - "pr_show": The current show identifier, read from the PR_SHOW.
    """
    env_data = {
        "pr_projects_path": os.getenv("PR_PROJECTS_PATH"),
        "pr_show": os.getenv("PR_SHOW")
    }
    return env_data


def get_path_structure_templ(template: str) -> str | list | None:
    """
    Load a path structure template from config file (folder_structure.json).

    Args:
        template: The name of the template to retrieve.

    Returns:
        str | list | None:
            - The template value (string or list) if the key exists.
            - None if the key is not found.
    """
    json_path = Path(__file__).parent / "folder_structure.json"

    if not json_path.is_file():
        logging.error(f"Template config not found: {json_path}")
        return None

    try:
        with open(json_path) as f:
            folder_structure = json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in {json_path}")
        return None

    value = folder_structure.get(template)

    if value is None:
        logging.error(f"Template key '{template}' not found in {json_path.name}")

    return value


def find_file_in_context(base_path: str, version: int) -> str | None:
    """
    Find a file matching the given version within the context directory.

    Searches subfolders of the provided base path and returns the first file
    that matches the version pattern.

    Args:
        base_path: A path to the folder with the versions.
        version: A version to search.

    Returns:
        str | None:
            - The first matching file path if the specified version is found.
            - None if no file matching the version exists within the given path.
    """
    node_version = str(version).zfill(3)
    base = Path(base_path)
    results = []
    for subfolder in base.iterdir():
        if subfolder.is_dir() and node_version in subfolder.name:
            for file in subfolder.iterdir():

                if node_version in file.name:
                    results.append(file)
    return results[0] if results else None


def get_latest_version_number(context: str) -> int | None:
    """
    Get the highest version number from versioned subfolders in a given context.

    Args:
        context: A path to the folder that contains version.

    Returns:
        int | None: The latest version number.
    """
    context_path = Path(context)
    if not context_path.exists():
        return None

    versioned_dirs = []
    for d in context_path.iterdir():
        match = re.search(r'\d+', d.name)
        if match:
            versioned_dirs.append(int(match.group()))
    if versioned_dirs:
        version = sorted(versioned_dirs, reverse=True)[0]
        return version
    else:
        return None


# Publishing

def get_show_data_folder() -> Path:
    """
    Helper function to get the data folder.

    Returns:
        Path: A path to the folder that contains project data.

    """
    env_vars = get_env()
    return Path(env_vars["pr_projects_path"]) / env_vars["pr_show"] / "show_data"


def get_published_data(data_folder: Path) -> dict:
    """
    Load published asset data from a JSON file.

    If the JSON file does not exist, creates a file and returns an empty dictionary.

    Args:
        data_folder: Path to the folder with the published JSON data file.

    Returns:
        dict: loaded dictionary from the path.
    """
    data_folder.mkdir(parents=True, exist_ok=True)
    published_data_path = data_folder / "published_data.json"

    if not published_data_path.exists():
        published_data_path.write_text('{}')

    return json.loads(published_data_path.read_text())


def write_published_data(data_folder: Path, published_data: dict) -> None:
    """
    Writes the published assets data to a JSON published assets metadata file.

    Args:
        data_folder: Path to the folder that contains the published data JSON file.
        published_data: A dictionary containing the data to write.
    """
    published_data_path = data_folder / "published_data.json"
    published_data_path.write_text(json.dumps(published_data, indent=4))


# Save or open DCC scene files

def make_scene_path(dcc, ext, scene_name, ) -> str | None:
    """
    Create a scene file path based on the DCC application, file extension, and the scene file name.

    Args:
        dcc: Name of the current DCC application.
        ext: File extension
        scene_name: The base name of the scene file.

    Returns:
        str | None:
            - The resolved file path for a scene based on the 'scene_file' template
              and the given DCC.
            - None if the scene path could not be created (e.g. if no scene
              name is provided).
    """

    if scene_name != "":
        check_required_env(["PR_PROJECTS_PATH", "PR_SHOW", "PR_ITEM", "PR_GROUP", "PR_TASK"])
        env_data = {
            "pr_projects_path": os.getenv("PR_PROJECTS_PATH"),
            "pr_show": os.getenv("PR_SHOW"),
            "pr_item": os.getenv("PR_ITEM"),
            "pr_group": os.getenv("PR_GROUP"),
            "pr_task": os.getenv("PR_TASK"),
            "dcc": dcc,
            "name": scene_name,
            "version": "001",
            "ext": ext,
        }
        templ = get_path_structure_templ("scene_file")
        if not templ:
            raise RuntimeError("Template 'scene_file' not found.")

        scene_path = os.path.normpath(templ.format(**env_data))
        scenes_folder = os.path.dirname(scene_path)
        if not os.path.isdir(scenes_folder) or not os.path.isfile(scene_path):
            return scene_path
        latest = (get_latest_version_number(scenes_folder) or 0) + 1
        env_data["version"] = "%03d" % latest
        return os.path.normpath(templ.format(**env_data))
    else:
        return None


def get_task_context() -> str:
    """
    Solve a task context path based on an environment variables.

    Returns:
        str: A context path.

    """
    check_required_env(["PR_PROJECTS_PATH", "PR_SHOW", "PR_ITEM", "PR_GROUP", "PR_TASK"])
    context = os.path.join(os.environ.get("PR_PROJECTS_PATH"), os.environ.get("PR_SHOW"),
                           os.environ.get("PR_GROUP"),
                           os.environ.get("PR_ITEM"), os.getenv("PR_TASK"))
    context = os.path.normpath(context)
    return context


def check_required_env(keys: list[str]) -> None:
    """
    Helper function to ensure that all required environment variables are set.

    Args:
        keys: Required environment variable names.
    """
    miss = [k for k in keys if not os.getenv(k)]
    if miss:
        raise RuntimeError("Missing environment variables: " + ", ".join(miss))
