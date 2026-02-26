from abc import ABC, abstractmethod
from collections import OrderedDict

from ansys.edb.core.inner.base import ObjBase

class FilterBase(ABC):
    @abstractmethod
    def set_filter_rules(self, rules: dict):
        pass

    @abstractmethod
    def is_applicable(self, edb_obj_type) -> bool:
        pass

    @abstractmethod
    def execute(self, data: OrderedDict) -> bool:
        pass


class EdbDiffFilterV1(FilterBase):
    def __init__(self, logger=None):
        self.logger = logger
        self.filter_rules = {
            ObjBase: {}
        }
    
    def set_filter_rules(self, rules: dict):
        for edb_obj, _ in self.filter_rules.items():
            self.filter_rules[edb_obj] = rules.get(edb_obj.__name__, {})

    def is_applicable(self, edb_obj_type) -> bool:
        for obj_type in self.filter_rules:
            if issubclass(edb_obj_type, obj_type):
                return True
        return False

    def execute(self, data: OrderedDict) -> bool:
        is_equal = True
        filter_keys = []
        filter_rule = self.filter_rules.get(ObjBase, {})
        for value in data.items():
            key, val = value
            if key in filter_rule.get("excluded_properties", []):
                if self._execute(val):
                    filter_keys.append(key)
                continue

            if isinstance(val, tuple):
                if not self._execute(val):
                    is_equal = False
                else:
                    if key not in filter_rule.get("reserved_properties", []):
                        filter_keys.append(key)
            elif isinstance(val, OrderedDict):
                if not self.execute(val):
                    is_equal = False
                else:
                    if key not in filter_rule.get("reserved_properties", []):
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
                    if key not in filter_rule.get("reserved_properties", []):
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
