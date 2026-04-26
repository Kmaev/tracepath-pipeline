import os


# ==========================================
# USD HDA functions to solve the env variables

def get_env_group() -> str:
    return os.environ.get("PR_GROUP")


def get_env_item() -> str:
    return os.environ.get("PR_ITEM")


def get_env_task() -> str:
    return os.environ.get("PR_TASK")
