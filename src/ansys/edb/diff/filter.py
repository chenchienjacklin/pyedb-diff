from abc import ABC, abstractmethod
from collections import OrderedDict

from ansys.edb.core.definition.component_def import ComponentDef
from ansys.edb.core.definition.material_def import MaterialDef
from ansys.edb.core.definition.padstack_def import PadstackDef
from ansys.edb.core.inner.layout_obj import LayoutObj


class FilterBase(ABC):
    @abstractmethod
    def is_applicable(self, edb_obj_type) -> bool:
        pass

    @abstractmethod
    def execute(self, data: OrderedDict) -> bool:
        pass


class EdbDiffFilter(FilterBase):
    def __init__(self, logger=None):
        self.logger = logger
        self.obj_types = [MaterialDef, PadstackDef, ComponentDef, LayoutObj]

    def is_applicable(self, edb_obj_type) -> bool:
        for obj_type in self.obj_types:
            if issubclass(edb_obj_type, obj_type):
                return True
        return False

    def execute(self, data: OrderedDict) -> bool:
        for value in data.items():
            val = value[1]
            if isinstance(val, tuple):
                if not self._execute(val):
                    return False
            elif isinstance(val, OrderedDict):
                if not self.execute(val):
                    return False
        return True

    def _execute(self, entry: tuple) -> bool:
        if not isinstance(entry, tuple) or len(entry) != 3:
            return False
        val1, val2, is_equal = entry
        return is_equal
