from abc import ABC, abstractmethod
from collections import OrderedDict

from ansys.edb.core.database import Database
from ansys.edb.core.definition.component_def import ComponentDef
from ansys.edb.core.definition.material_def import MaterialDef
from ansys.edb.core.definition.padstack_def import PadstackDef
from ansys.edb.core.definition.padstack_def_data import PadstackDefData
from ansys.edb.core.definition.bondwire_def import BondwireDef
from ansys.edb.core.inner.layout_obj import LayoutObj
from ansys.edb.core.layout.cell import Cell


class FilterBase(ABC):
    @abstractmethod
    def is_applicable(self, edb_obj_type) -> bool:
        pass

    @abstractmethod
    def execute(self, data: OrderedDict) -> bool:
        pass


class EdbDiffFilterV1(FilterBase):
    def __init__(self, logger=None):
        self.logger = logger
        self.obj_types = [Database, MaterialDef, PadstackDef, PadstackDefData, ComponentDef, BondwireDef, Cell, LayoutObj]
        self.skip_properties = ["id", "owner"]
        self.reserved_properties = ["id", "name", "owner"]

    def is_applicable(self, edb_obj_type) -> bool:
        for obj_type in self.obj_types:
            if issubclass(edb_obj_type, obj_type):
                return True
        return False

    def execute(self, data: OrderedDict) -> bool:
        is_equal = True
        filter_keys = []
        for value in data.items():
            key = value[0]
            if key in self.skip_properties:
                continue

            val = value[1]
            if isinstance(val, tuple):
                if not self._execute(val):
                    is_equal = False
                else:
                    if key not in self.reserved_properties:
                        filter_keys.append(key)
            elif isinstance(val, OrderedDict):
                if not self.execute(val):
                    is_equal = False
                else:
                    if key not in self.reserved_properties:
                        filter_keys.append(key)
            elif isinstance(val, list):
                is_list_equal = True
                for item in val:
                    if not self._execute(item):
                        is_list_equal = False
                        break
                
                if not is_list_equal:
                    is_equal = False
                else:
                    if key not in self.reserved_properties:
                        filter_keys.append(key)

        if not is_equal:
            for key in filter_keys:
                data.pop(key)
        return is_equal

    def _execute(self, entry: tuple) -> bool:
        if not isinstance(entry, tuple) or len(entry) != 3:
            return False
        val1, val2, is_equal = entry
        return is_equal
