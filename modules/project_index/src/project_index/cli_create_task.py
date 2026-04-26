import argparse

from project_index import utils


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Task name")
    parser.add_argument("--dccs", nargs="+", required=True, help="DCC folder list")

    namespace = parser.parse_args(args)

    utils.create_task(namespace.name, namespace.dccs)


if __name__ == "__main__":
    main()
