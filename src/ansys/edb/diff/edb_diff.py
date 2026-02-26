from collections import OrderedDict
from contextlib import nullcontext
from time import time

from ansys.edb.core.database import Database
from ansys.edb.core.session import session
from ansys.edb.core.utility.io_manager import IOMangementType, enable_io_manager

from ansys.edb.diff.comparator import ComparatorBase
from ansys.edb.diff.exporter import ExporterBase


class EdbDiff:
    def __init__(
        self,
        version: str,
        ansys_em_root: str,
        host: str,
        port: int,
        enable_io_manager: bool,
        comparator: ComparatorBase,
        exporter: ExporterBase,
        logger=None,
    ):
        self.version = version
        self.ansys_em_root = ansys_em_root
        self.host = host
        self.port = port
        self.enable_io_manager = enable_io_manager
        self.comparator = comparator
        self.exporter = exporter
        self.logger = logger

    def execute(self, edb_path1: str, edb_path2: str, output_file: str = ""):
        with session(self.ansys_em_root, self.port):
            with enable_io_manager(IOMangementType.READ) if self.enable_io_manager else nullcontext():
                start = time()
                self._execute(edb_path1, edb_path2, output_file)
                end = time()
                if self.logger is not None:
                    self.logger.info(f"EDB diff execution time: {end - start:.2f} seconds")

    def _execute(self, edb_path1: str, edb_path2: str, output_file: str = ""):
        edb1 = None
        edb2 = None
        try:
            edb1 = Database.open(edb_path1, True)
            edb2 = Database.open(edb_path2, True)
            comparison_results = OrderedDict()
            comparison_results["version"] = self.version
            comparison_results["Database"] = self.comparator.execute(edb1, edb2)
            self.exporter.execute(comparison_results, output_file)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Failed to open EDB files: {e}")
        finally:
            if edb1:
                edb1.close()
            if edb2:
                edb2.close()
