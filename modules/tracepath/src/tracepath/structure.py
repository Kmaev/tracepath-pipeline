import os


# ==========================================
# USD HDA functions to solve the env variables

def get_env_group() -> str:
    """
    Get the PR_GROUP environment variable.

    Returns:
        str: Group value.
    """
    return os.environ.get("PR_GROUP")


def get_env_item() -> str:
    """
    Get the PR_ITEM environment variable.

    Returns:
        str: Item value.
    """
    return os.environ.get("PR_ITEM")


def get_env_task() -> str:
    """
    Get the PR_TASK environment variable.

    Returns:
        str: Task value.
    """
    return os.environ.get("PR_TASK")
