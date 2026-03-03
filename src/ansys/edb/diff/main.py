import argparse
import logging

from ansys.edb.diff.edb_diff_builder import EdbDiffBuilderBase

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger("edb_diff")


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--edb_diff_config", required=False, help="Path to the EDB diff configuration YAML file"
    )
    parser.add_argument("edb_path1", help="Path to the first EDB file")
    parser.add_argument("edb_path2", help="Path to the second EDB file")
    parser.add_argument("output_file", nargs="?", default = "", help="Path to output diff file  (optional)")

    args = parser.parse_args()

    builder = EdbDiffBuilderBase().set_logger(LOGGER)
    if args.edb_diff_config:
        builder.set_config_file(args.edb_diff_config)
    edb_diff = builder.build()
    edb_diff.execute(args.edb_path1, args.edb_path2, args.output_file)


if __name__ == "__main__":
    main()
