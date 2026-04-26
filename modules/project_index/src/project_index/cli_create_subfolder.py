import argparse

from project_index import utils


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dccs", nargs="+", required=True, help="DCC folder list")

    namespace = parser.parse_args(args)

    utils.add_dcc_folders(namespace.dccs)


if __name__ == "__main__":
    main()
