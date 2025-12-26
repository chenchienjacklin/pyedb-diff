import inspect

from ansys.edb.core.definition.material_def import MaterialDef
from ansys.edb.core.definition.padstack_def import PadstackDef, PadstackDefData
from ansys.edb.core.inner.base import ObjBase
from ansys.edb.core.layout.cell import Cell
from ansys.edb.core.layout.layout import Layout
from ansys.edb.core.primitive.circle import Circle
from ansys.edb.core.primitive.padstack_instance import PadstackInstance
from ansys.edb.core.primitive.path import Path
from ansys.edb.core.primitive.polygon import Polygon
from ansys.edb.core.primitive.rectangle import Rectangle

import ansys.edb.diff.match_rules as match_rules_module
from ansys.edb.diff.match_rules import (
    MatchByCircleProperties,
    MatchByLayerName,
    MatchByName,
    MatchByPadstackInstanceProperties,
    MatchByPathProperties,
    MatchByPolygonProperties,
    MatchByRectangleProperties,
)


class NullCell(Cell):
    def __init__(self, msg=None):
        ObjBase.__init__(self, msg)


class NullLayout(Layout):
    def __init__(self, msg=None):
        ObjBase.__init__(self, msg)


class EdbObjMatcher:
    def __init__(self, logger=None):
        self.logger = logger
        self.match_rules = {
            "MaterialDef": [MatchByName],
            "PadstackDef": [MatchByName],
            "Cell": [MatchByName],
            "Rectangle": [MatchByLayerName, MatchByRectangleProperties],
            "Circle": [MatchByLayerName, MatchByCircleProperties],
            "Polygon": [MatchByLayerName, MatchByPolygonProperties],
            "Path": [MatchByLayerName, MatchByPathProperties],
            "PadstackInstance": [MatchByPadstackInstanceProperties],
        }

        self.null_edb_objects = {
            "MaterialDef": MaterialDef(None),
            "PackageDef": PadstackDef(None),
            "PadstackDefData": PadstackDefData(None),
            "Cell": NullCell(),
            "Layout": NullLayout(),
            "Rectangle": Rectangle(None),
            "Circle": Circle(None),
            "Polygon": Polygon(None),
            "Path": Path(None),
            "PadstackInstance": PadstackInstance(None),
        }

    def set_match_rules(self, rules: dict):
        rule_registry = {
            cls.__name__: cls for _, cls in inspect.getmembers(match_rules_module, inspect.isclass)
        }

        try:
            if not isinstance(rules, dict) or len(rules) == 0:
                return

            loaded_rules = {}
            for edb_type, rule_names in rules.items():
                if not isinstance(rule_names, list):
                    continue
                classes = []
                for name in rule_names:
                    cls = rule_registry.get(str(name))
                    if cls is not None:
                        classes.append(cls)
                if len(classes) > 0:
                    loaded_rules[str(edb_type)] = classes

            if len(loaded_rules) > 0:
                self.match_rules = loaded_rules
        except Exception as e:
            if self.logger is not None:
                self.logger.warning(f"Failed to set match rules: {e}")

    def match(self, objs1, objs2, edb_obj_type=""):
        if len(objs1) == 0 and len(objs2) == 0:
            return []

        if edb_obj_type is None or edb_obj_type == "":
            edb_obj_type = type(objs1[0]).__name__ if len(objs1) > 0 else type(objs2[0]).__name__

        mismatch_count = 0
        matched_pairs = []
        used_objs = set()
        for obj1 in objs1:
            found = False
            for obj2 in objs2:
                if obj2 in used_objs:
                    continue

                rules = self.match_rules.get(edb_obj_type, [])
                if all(rule.is_match(obj1, obj2) for rule in rules):
                    matched_pairs.append((obj1, obj2))
                    used_objs.add(obj2)
                    found = True
                    break
            if not found:
                mismatch_count += 1
                matched_pairs.append((obj1, self.null_edb_objects.get(edb_obj_type, None)))

        for obj2 in objs2:
            if obj2 not in used_objs:
                mismatch_count += 1
                matched_pairs.append((self.null_edb_objects.get(edb_obj_type, None), obj2))
        if self.logger is not None:
            self.logger.debug(
                f"Matched {len(matched_pairs) - mismatch_count} pairs, {mismatch_count} mismatches for {edb_obj_type}"
            )
        return matched_pairs
