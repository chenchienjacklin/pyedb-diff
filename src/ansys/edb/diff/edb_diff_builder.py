import logging
import os
from pathlib import Path

from yaml import safe_load

from ansys.edb.diff.comparator import EdbComparator
from ansys.edb.diff.edb_diff import EdbDiff
from ansys.edb.diff.exporter import EdbDiffExporter
from ansys.edb.diff.filter import EdbDiffFilter
from ansys.edb.diff.matcher import EdbObjMatcher
from ansys.edb.diff.visitor import EdbObjVisitor


class EdbDiffBuilderBase:
    def __init__(self):
        self.ansys_em_root = ""
        self.config_file = Path(__file__).resolve().parent / "config" / "edb-diff-config.yaml"
        self.host = ""
        self.port = 0
        self.enable_io_manager = False
        self.debug = False
        self.visit_rules = {}
        self.match_rules = {}
        self.logger = None

    def set_ansys_em_root(self, ansys_em_root: str):
        self.ansys_em_root = ansys_em_root
        return self

    def set_host(self, host: str):
        self.host = host
        return self

    def set_port(self, port: int):
        self.port = port
        return self

    def set_logger(self, logger):
        self.logger = logger
        return self

    def set_config_file(self, config_file: str):
        if config_file is not None or len(config_file) > 0:
            self.config_file = config_file
        return self

    def load_config_file(self) -> bool:
        try:
            if not os.path.exists(self.config_file):
                raise FileNotFoundError(f"Config file {self.config_file} does not exist.")
            with open(self.config_file, "r") as f:
                data = safe_load(f) or {}
            self.ansys_em_root = data.get("ansys_em_root", self.ansys_em_root)
            self.host = data.get("host", self.host)
            self.port = data.get("port", self.port)
            self.enable_io_manager = data.get("enable_io_manager", self.enable_io_manager)
            self.debug = data.get("debug", self.debug)
            self.visit_rules = data.get("visit_rules", self.visit_rules)
            self.match_rules = data.get("match_rules", self.match_rules)
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Failed to load config file {self.config_file}: {e}")
            return False

    def validate(self) -> bool:
        if self.ansys_em_root == "":
            raise ValueError("Ansys EM root path is not set.")
        if self.host == "":
            raise ValueError("Host is not set.")
        if self.port <= 0:
            raise ValueError("Port is not set or invalid.")
        if self.logger is None:
            raise ValueError("Logger is not set.")
        return True

    def build(self) -> EdbDiff:
        if not self.load_config_file():
            raise ValueError("Failed to load EDB Diff configuration file.")
        if not self.validate():
            raise ValueError("EDB Diff Builder configuration is invalid.")
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        visitor = EdbObjVisitor(self.logger)
        if len(self.visit_rules) > 0:
            visitor.set_visit_rules(self.visit_rules)
        matcher = EdbObjMatcher(self.logger)
        if len(self.match_rules) > 0:
            matcher.set_match_rules(self.match_rules)
        comparator = EdbComparator(visitor, matcher, [EdbDiffFilter(self.logger)], self.logger)
        exporter = EdbDiffExporter(self.logger)
        edb_diff = EdbDiff(
            self.ansys_em_root,
            self.host,
            self.port,
            self.enable_io_manager,
            comparator,
            exporter,
            self.logger,
        )
        return edb_diff
