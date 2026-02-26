from abc import ABC, abstractmethod
from collections import OrderedDict
from enum import Enum

from ansys.edb.core.inner.base import ObjBase

from ansys.edb.diff.filter import FilterBase
from ansys.edb.diff.matcher import MatcherBase
from ansys.edb.diff.visitor import VisitorBase


class ComparatorBase(ABC):
    @abstractmethod
    def execute_all(self, objs1, objs2, edb_obj_type=""):
        pass

    @abstractmethod
    def execute(self, obj1, obj2):
        pass


class EdbComparatorV1(ComparatorBase):
    def __init__(
        self, visitor: VisitorBase, matcher: MatcherBase, filters: list[FilterBase], logger=None
    ):
        super().__init__()
        self.logger = logger
        self.visitor = visitor
        self.matcher = matcher
        self.filters = filters

    def execute_all(self, objs1, objs2, edb_obj_type=""):
        pairs = self.matcher.match(objs1, objs2, edb_obj_type)
        if len(pairs) == 0:
            return

        diffs_list = []
        for obj1, obj2 in pairs:
            try:
                diff = self.execute(obj1, obj2)
                if diff is not None:
                    diffs_list.append(diff)
            except Exception as e:
                if self.logger is not None:
                    self.logger.error(f"Failed to compare objects: {e}")
        return diffs_list if len(diffs_list) > 0 else None

    def execute(self, obj1, obj2):
        obj1_properties = self.visitor.visit(obj1)
        obj2_properties = self.visitor.visit(obj2)
        diff = self._diff_values(obj1_properties, obj2_properties)
        if diff is not None:
            if any(filter.is_applicable(type(obj1)) for filter in self.filters):
                if not all(filter.execute(diff) for filter in self.filters):
                    return diff
            else:
                return diff
        return None

    def _merge_keys_in_order(self, d1, d2):
        keys = []
        if isinstance(d1, dict):
            keys.extend(list(d1.keys()))
        if isinstance(d2, dict):
            for k in d2.keys():
                if not isinstance(d1, dict) or k not in d1:
                    keys.append(k)
        return keys

    def _diff_values(self, val1, val2):
        if isinstance(val1, dict) or isinstance(val2, dict):
            if val1 is None:
                val1 = {}
            if val2 is None:
                val2 = {}

            sub_diffs = OrderedDict()
            for sub_key in self._merge_keys_in_order(val1, val2):
                diff_value = self._diff_values(val1.get(sub_key, None), val2.get(sub_key, None))
                if diff_value is not None:
                    sub_diffs[sub_key] = diff_value
            return sub_diffs if len(sub_diffs) > 0 else None

        if isinstance(val1, list) or isinstance(val2, list):
            if val1 is None:
                val1 = []
            if val2 is None:
                val2 = []

            if len(val1) == 0 and len(val2) == 0:
                return None

            is_obj_base = (
                isinstance(val1[0], ObjBase) if len(val1) > 0 else isinstance(val2[0], ObjBase)
            )
            edb_obj_type = type(val1[0]).__name__ if len(val1) > 0 else type(val2[0]).__name__
            if is_obj_base:
                return self.execute_all(val1, val2, edb_obj_type)

        if isinstance(val1, tuple) or isinstance(val2, tuple):
            if val1 is None:
                val1 = tuple()
            if val2 is None:
                val2 = tuple()

            if len(val1) == 0 and len(val2) == 0:
                return None

            # Element-wise comparison for tuples, fill with None if lengths differ
            max_length = max(len(val1), len(val2))
            val1_extended = val1 + (None,) * (max_length - len(val1))
            val2_extended = val2 + (None,) * (max_length - len(val2))
            diffs = []
            for v1, v2 in zip(val1_extended, val2_extended):
                diff = self._diff_values(v1, v2)
                diffs.append(diff)
            return diffs if any(d is not None for d in diffs) else None

        if self.visitor.visit_map.get(type(val1)) is not None or self.visitor.visit_map.get(type(val2)) is not None:
            return self.execute(val1, val2)
        
        return self.to_string(val1), self.to_string(val2), val1 == val2

    def to_string(self, val):
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        elif isinstance(val, tuple):
            return ", ".join(self.to_string(v) for v in val)
        elif isinstance(val, Enum):
            return val.name
        return str(val)
