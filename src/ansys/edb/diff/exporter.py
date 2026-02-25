from abc import ABC, abstractmethod
import json


class ExporterBase(ABC):
    @abstractmethod
    def execute(self, comparison_results, output_file):
        pass


class EdbDiffExporterV1(ExporterBase):
    def __init__(self, logger=None):
        self.logger = logger

    def execute(self, comparison_results, output_file):
        if output_file is None or output_file == "":
            if self.logger is not None:
                self.logger.error("Output file path is not specified.")
            return

        with open(output_file, "w") as f:
            f.write(json.dumps(comparison_results, indent=4))
