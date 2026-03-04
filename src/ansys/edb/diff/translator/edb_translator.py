from collections import OrderedDict
from contextlib import nullcontext
from time import time

from ansys.edb.core.database import Database
from ansys.edb.core.session import session
from ansys.edb.core.utility.io_manager import IOMangementType, enable_io_manager

from ansys.edb.diff.visitor import VisitorBase
from ansys.edb.diff.exporter import ExporterBase


class EdbTranslator:
    def __init__(
        self,
        version: str,
        ansys_em_root: str,
        host: str,
        port: int,
        enable_io_manager: bool,
        visitor: VisitorBase,
        exporter: ExporterBase,
        logger=None,
    ):
        self.version = version
        self.ansys_em_root = ansys_em_root
        self.host = host
        self.port = port
        self.enable_io_manager = enable_io_manager
        self.visitor = visitor
        self.exporter = exporter
        self.logger = logger

    def execute(self, edb_path: str, output_file: str = ""):
        with session(self.ansys_em_root, self.port):
            with enable_io_manager(IOMangementType.READ) if self.enable_io_manager else nullcontext():
                start = time()
                self._execute(edb_path, output_file)
                end = time()
                if self.logger is not None:
                    self.logger.info(f"EDB diff execution time: {end - start:.2f} seconds")

    def _execute(self, edb_path: str, output_file: str = ""):
        edb = None
        try:
            edb = Database.open(edb_path, True)
            results = OrderedDict()
            results["version"] = self.version
            results["database"] = self.visitor.visit(edb, True)
            if len(output_file) > 0:
                self.exporter.execute(results, output_file)
            else:
                print(results)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Failed to open EDB files: {e}")
        finally:
            if edb:
                edb.close()
