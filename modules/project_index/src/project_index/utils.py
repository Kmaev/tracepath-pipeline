import difflib
import json
import logging
import os
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def get_dcc_template() -> dict:
    """Load DCC folder templates from config."""
    framework = os.getenv("PR_TRACEPATH_FRAMEWORK")
    file_path = os.path.join(framework, "config/applications_templates.json")

    with open(file_path) as f:
        templ_file = json.load(f)
    return templ_file


def create_dcc_folder_structure(dcc_name: str, parent_folder: str) -> None:
    """
    Create folder structure for a DCC.

    Args:
        dcc_name: DCC name.
        parent_folder: Parent folder path.
    """
    parent_folder = Path(parent_folder)
    templ_file = get_dcc_template()
    folders = templ_file.get(dcc_name, [])
    for folder in folders:
        folder_path = parent_folder / dcc_name / folder
        if not os.path.isdir(folder_path):
            os.makedirs(folder_path)


def dcc_template_check(dcc: str, templ_file: dict) -> str | None:
    """
    Return closest matching DCC name if not found.

    Args:
        dcc: DCC name to check.
        templ_file: Template data.
    """
    known_dccs = list(templ_file.keys())
    if dcc in known_dccs:
        return None
    suggestion = difflib.get_close_matches(dcc, known_dccs, n=1)
    return suggestion[0] if suggestion else None


# ======================================================================================================================
# CLI Create task tool

def get_context() -> str:
    """Build context path from environment variables."""
    context = os.path.join(os.environ.get("PR_PROJECTS_PATH"), os.environ.get("PR_SHOW"), os.environ.get("PR_GROUP"),
                           os.environ.get("PR_ITEM"))
    return context


def create_task(name: str, dcc_list: list[str]) -> None:
    """
    Create a task and associated DCC folders.

    Args:
        name: Task name.
        dcc_list: List of DCC names.
    """

    context = get_context()
    if not os.path.isdir(context):
        logging.error(f"Not valid context {context}")
    else:
        task_folder = os.path.join(context, name)
        # Add name validation check
        if not os.path.isdir(task_folder):
            os.makedirs(task_folder)
        checked_dcc = check_dcc_name(dcc_list)

        for dcc in checked_dcc:
            create_dcc_folder_structure(dcc, task_folder)
        logging.info(f"Created task '{name}' with DCC folder(s) '{checked_dcc}'")

        update_project_index(name)
        logging.info("Project index updated")


def check_dcc_name(dcc_list: list[str]) -> list[str]:
    """
    Validate DCC names and return valid entries.

    Args:
        dcc_list: List of DCC names.
    """
    _dcc_list = [re.sub(r'[^a-zA-Z0-9]', '', item) for item in dcc_list]

    templ = get_dcc_template()
    skipped_dcc = []
    checked_dcc_list = []
    confirmed_suggestions = []

    for _dcc in _dcc_list:
        suggestion = dcc_template_check(_dcc, templ)

        if suggestion:
            if suggestion not in confirmed_suggestions:
                while True:
                    user_input = input(
                        f"DCC '{_dcc}' not found. Did you mean '{suggestion}'? (yes/no): "
                    ).strip().lower()

                    if user_input in ['y', 'yes']:
                        dcc_name = suggestion
                        confirmed_suggestions.append(suggestion)
                        break
                    elif user_input in ['n', 'no']:
                        logging.info(f"Skipping DCC '{_dcc}'.")
                        dcc_name = None
                        break
                    else:
                        logging.info("Please enter 'y'/'yes' or 'n'/'no'.")
            else:
                dcc_name = suggestion
        else:
            dcc_name = _dcc

        if dcc_name not in templ.keys() and dcc_name not in skipped_dcc:
            skipped_dcc.append(dcc_name)
        else:
            checked_dcc_list.append(dcc_name)

    if skipped_dcc:
        logging.info(f"Skipping DCC '{skipped_dcc}'."
                     "Template Not Found\n"
                     "The following DCC(s) will be skipped during folder creation because "
                     "their templates were not found:\n\n"
                     + "\n".join(skipped_dcc)
                     )

    return checked_dcc_list


def update_project_index(task: str) -> None:
    """
    Update project index with a new task.

    Args:
        task: Task name.
    """
    framework = os.getenv("PR_TRACEPATH_FRAMEWORK")
    project_index_path = os.path.join(framework, "config/trace_project_index.json")
    project = os.environ.get("PR_SHOW")
    group = os.environ.get("PR_GROUP")
    item = os.environ.get("PR_ITEM")
    dirname = os.path.dirname(project_index_path)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    if os.path.exists(project_index_path):
        with open(project_index_path, 'r') as f:
            data = json.load(f)

    try:
        tasks = data[project]["groups"][group]["items"][item]["tasks"]
    except KeyError as e:
        raise KeyError(f"Missing key in project index: {e}")

    # Add task if it doesn't exist
    if task not in tasks:
        tasks[task] = {}

        # Write updated data back
        with open(project_index_path, 'w') as f:
            json.dump(data, f, indent=4)


def add_dcc_folders(dcc_list: list[str]) -> None:
    """
    Create DCC folders in the current context.

    Args:
        dcc_list: List of DCC names.
    """
    context = os.path.join(get_context(), os.environ.get("PR_TASK"))

    if not os.path.isdir(context):
        logging.error(f"Not valid context {context}")
    else:
        checked_dcc = check_dcc_name(dcc_list)

        for dcc in checked_dcc:
            create_dcc_folder_structure(dcc, context)
        logging.info(f"Created DCC folder(s) '{checked_dcc}'")
