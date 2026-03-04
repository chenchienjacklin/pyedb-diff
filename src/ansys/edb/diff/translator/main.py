import argparse
import logging

from ansys.edb.diff.translator.edb_translator_builder import EdbTranslatorBuilderBase

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger("edb_diff")


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--edb_diff_config", required=False, help="Path to the EDB diff configuration YAML file"
    )
    parser.add_argument("edb_path", help="Path to the EDB file")
    parser.add_argument("output_file", nargs="?", default = "", help="Path to output diff file  (optional)")

    args = parser.parse_args()

    builder = EdbTranslatorBuilderBase().set_logger(LOGGER)
    if args.edb_diff_config:
        builder.set_config_file(args.edb_diff_config)
    edb_translator = builder.build()
    edb_translator.execute(args.edb_path, args.output_file)


if __name__ == "__main__":
    main()
