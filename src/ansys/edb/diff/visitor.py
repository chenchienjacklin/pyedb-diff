from abc import ABC, abstractmethod
from collections import OrderedDict
from functools import wraps

from ansys.edb.core.database import Database
from ansys.edb.core.definition.component_def import ComponentDef
from ansys.edb.core.definition.component_model import ComponentModel
from ansys.edb.core.definition.material_def import MaterialDef
from ansys.edb.core.definition.padstack_def import PadstackDef, PadstackDefData
from ansys.edb.core.definition.padstack_def_data import PadType
from ansys.edb.core.geometry.polygon_data import PolygonData
from ansys.edb.core.hierarchy.component_group import ComponentGroup
from ansys.edb.core.hierarchy.group import Group
from ansys.edb.core.hierarchy.hierarchy_obj import HierarchyObj
from ansys.edb.core.hierarchy.structure3d import Structure3D
from ansys.edb.core.hierarchy.via_group import ViaGroup
from ansys.edb.core.inner.base import ObjBase
from ansys.edb.core.layout.cell import Cell
from ansys.edb.core.layout.layout import Layout
from ansys.edb.core.primitive.circle import Circle
from ansys.edb.core.primitive.padstack_instance import PadstackInstance
from ansys.edb.core.primitive.path import Path
from ansys.edb.core.primitive.polygon import Polygon
from ansys.edb.core.primitive.primitive import Primitive
from ansys.edb.core.primitive.rectangle import Rectangle


class VisitorBase(ABC):
    @abstractmethod
    def set_visit_rules(self, rules: dict):
        pass

    @abstractmethod
    def visit(self, edb_obj):
        pass


class EdbObjVisitor(VisitorBase):
    def __init__(self, logger=None):
        self.logger = logger
        self.visit_map = {
            Database: self.visit_database,
            MaterialDef: self.visit_material_def,
            PadstackDef: self.visit_padstack_def,
            PadstackDefData: self.visit_padstack_def_data,
            ComponentDef: self.visit_component_def,
            ComponentModel: self.visit_component_model,
            Cell: self.visit_cell,
            Layout: self.visit_layout,
            Rectangle: self.visit_rectangle,
            Circle: self.visit_circle,
            Polygon: self.visit_polygon,
            Path: self.visit_path,
            PadstackInstance: self.visit_padstack_instance,
            ComponentGroup: self.visit_component_group,
            Structure3D: self.visit_structure3d,
            ViaGroup: self.visit_via_group,
        }
        
        self.visit_rules = {
            Database: [],
            MaterialDef: [],
            PadstackDef: [],
            PadstackDefData: [],
            ComponentDef: [],
            ComponentModel: [],
            Cell: [],
            Layout: [],
            Primitive: [],
            Rectangle: [],
            Circle: [],
            Polygon: [],
            PolygonData: [],
            Path: [],
            PadstackInstance: [],
            HierarchyObj: [],
            ComponentGroup: [],
            Structure3D: [],
            ViaGroup: [],
        }

        self.property_extractors = {
            "material_properties": self.visit_material_properties,
            "pad_parameters": self.visit_pad_parameters,
            "primitives": lambda obj: self.visit_primitives(obj.primitives) if hasattr(obj, "primitives") else None,
            "groups": lambda obj: self.visit_groups(obj.groups) if hasattr(obj, "groups") else None,
            "net_name": lambda obj: obj.net.name if hasattr(obj, "net") and obj.net is not None else None,
            "layer_name": lambda obj: obj.layer.name if hasattr(obj, "layer") and obj.layer is not None else None,
            "owner": lambda obj: obj.owner.id if hasattr(obj, "owner") and obj.owner is not None else None,
            "voids": lambda obj: self.visit_primitives(obj.voids) if hasattr(obj, "has_voids") and obj.has_voids else None,
            "parameters": lambda obj: obj.get_parameters() if hasattr(obj, "get_parameters") else None,
            "polygon_data": lambda obj: self.visit_polygon_data(obj.polygon_data) if hasattr(obj, "polygon_data") else None,
            "center_line": lambda obj: self.visit_polygon_data(obj.center_line) if hasattr(obj, "center_line") else None,
            "outline": lambda obj: self.visit_polygon_data(obj.outline) if hasattr(obj, "outline") else None,
        }
    
    def set_visit_rules(self, rules):
        for edb_obj, _ in self.visit_rules.items():
            self.visit_rules[edb_obj] = rules.get(edb_obj.__name__, [])
    
    def visit_properties(self, obj, obj_type):
        properties = OrderedDict()
        for prop in self.visit_rules.get(obj_type, []):
            if prop in self.property_extractors:
                try:
                    properties[prop] = self.property_extractors[prop](obj)
                except Exception as e:
                    if self.logger is not None:
                        self.logger.warning(f"Failed to extract property {prop} from {obj_type.__name__}: {e}")
                continue

            if hasattr(obj, prop):
                properties[prop] = getattr(obj, prop)
            else:
                self.logger.warning(f"{obj_type.__name__} object does not have property {prop}")
        return properties

    def visit(self, edb_obj):
        visitor = self.visit_map.get(type(edb_obj), None)
        if visitor is not None:
            return visitor(edb_obj)
        return {}

    def visit_objbase(func):
        @wraps(func)
        def wrapper(self, obj: ObjBase):
            objbase_properties = OrderedDict()
            if not isinstance(obj, ObjBase):
                self.logger.warning(f"Expected ObjBase instance, got {type(obj)}")
                return objbase_properties

            if obj.id == 0:
                return objbase_properties

            objbase_properties["id"] = obj.id
            properties = func(self, obj)

            if isinstance(properties, dict):
                objbase_properties.update(properties)
            return objbase_properties

        return wrapper

    @visit_objbase
    def visit_database(self, database: Database):
        return self.visit_properties(database, Database)

    @visit_objbase
    def visit_material_def(self, material_def: MaterialDef):
        return self.visit_properties(material_def, MaterialDef)
    
    def visit_material_properties(self, material_def: MaterialDef):
        material_properties = OrderedDict()
        for material_property in material_def.all_properties:
            row, col = material_def.get_dimensions(material_property)
            values = []
            for r in range(row):
                for c in range(col):
                    values.append(material_def.get_property(material_property, r, c))
            material_properties[material_property.name] = values
        return material_properties

    @visit_objbase
    def visit_padstack_def(self, padstack_def: PadstackDef):
        return self.visit_properties(padstack_def, PadstackDef)

    @visit_objbase
    def visit_padstack_def_data(self, padstack_def_data: PadstackDefData):
        return self.visit_properties(padstack_def_data, PadstackDefData)

    def visit_pad_parameters(self, padstack_def_data: PadstackDefData):
        params = OrderedDict()
        for pad_type in [PadType.REGULAR_PAD, PadType.ANTI_PAD, PadType.THERMAL_PAD]:
            params[pad_type.name] = OrderedDict()
            for layer_name in padstack_def_data.layer_names:
                pad_parameters = padstack_def_data.get_pad_parameters(layer_name, pad_type)
                if (
                    pad_parameters is not None
                    and len(pad_parameters) > 0
                    and isinstance(pad_parameters[0], PolygonData)
                ):
                    new_pad_parameters = list(pad_parameters)
                    new_pad_parameters[0] = self.visit_polygon_data(pad_parameters[0])
                    params[pad_type.name][layer_name] = tuple(new_pad_parameters)
                    continue

                params[pad_type.name][layer_name] = pad_parameters
        return params

    @visit_objbase
    def visit_component_def(self, component_def: ComponentDef):
        return self.visit_properties(component_def, ComponentDef)

    @visit_objbase
    def visit_component_model(self, component_model: ComponentModel):
        return self.visit_properties(component_model, ComponentModel)

    @visit_objbase
    def visit_cell(self, cell: Cell):
        return self.visit_properties(cell, Cell)

    @visit_objbase
    def visit_layout(self, layout: Layout):
        return self.visit_properties(layout, Layout)

    def visit_primitives(self, primitives: list[Primitive]):
        prims = {"rectangles": [], "circles": [], "polygons": [], "paths": []}
        visit_prim_types = [prim for prim in [Rectangle, Circle, Polygon, Path] if len(self.visit_rules.get(prim, [])) > 0]
        if len(visit_prim_types) == 0:
            return prims
        
        for primitive in primitives:
            try:
                layer = primitive.layer.is_null
                if Rectangle in visit_prim_types and isinstance(primitive, Rectangle):
                    prims["rectangles"].append(primitive)
                elif Circle in visit_prim_types and isinstance(primitive, Circle):
                    prims["circles"].append(primitive)
                elif Polygon in visit_prim_types and isinstance(primitive, Polygon):
                    prims["polygons"].append(primitive)
                elif Path in visit_prim_types and isinstance(primitive, Path):
                    prims["paths"].append(primitive)
            except Exception as e:
                if self.logger is not None:
                    self.logger.warning(f"Skipping primitive due to error: {e}")
                continue
        return prims

    def visit_primitive(func):
        @wraps(func)
        def wrapper(self, primitive: Primitive):
            primitive_properties = self.visit_properties(primitive, Primitive)
            properties = func(self, primitive)
            if isinstance(properties, dict):
                primitive_properties.update(properties)

            return primitive_properties

        return wrapper

    @visit_objbase
    @visit_primitive
    def visit_rectangle(self, rectangle: Rectangle):
        return self.visit_properties(rectangle, Rectangle)

    @visit_objbase
    @visit_primitive
    def visit_circle(self, circle: Circle):
        return self.visit_properties(circle, Circle)

    @visit_objbase
    @visit_primitive
    def visit_polygon(self, polygon: Polygon):
        return self.visit_properties(polygon, Polygon)

    def visit_polygon_data(self, polygon_data: PolygonData):
        return self.visit_properties(polygon_data, PolygonData)

    @visit_objbase
    @visit_primitive
    def visit_path(self, path: Path):
        return self.visit_properties(path, Path)

    @visit_objbase
    def visit_padstack_instance(self, padstack_instance: PadstackInstance):
        position_and_rotation = padstack_instance.get_position_and_rotation()
        layer_range = []
        try:
            layer_range = padstack_instance.get_layer_range()
        except Exception as e:
            if self.logger is not None:
                self.logger.warning(
                    f"Could not get layer range for padstack instance {padstack_instance.name}: {e}"
                )

        return OrderedDict(
            {
                "net_name": padstack_instance.net.name if padstack_instance.net is not None else "",
                "name": padstack_instance.name,
                "position": (position_and_rotation[0], position_and_rotation[1]),
                "rotation": position_and_rotation[2],
                "padstack_def": padstack_instance.padstack_def,
                "layer_range": [layer.name for layer in layer_range],
                "hole_overrides": padstack_instance.get_hole_overrides(),
                "is_layout_pin": padstack_instance.is_layout_pin,
                "group": padstack_instance.group,
            }
        )

    def visit_groups(self, groups: list[Group]):
        grps = {"component_groups": [], "structure3d_groups": [], "via_groups": []}
        visit_group_types = [grp for grp in [ComponentGroup, Structure3D, ViaGroup] if len(self.visit_rules.get(grp, [])) > 0]
        for group in groups:
            try:
                grp = group.cast()
                if ComponentGroup in visit_group_types and isinstance(grp, ComponentGroup):
                    grps["component_groups"].append(grp)
                elif Structure3D in visit_group_types and isinstance(grp, Structure3D):
                    grps["structure3d_groups"].append(grp)
                elif ViaGroup in visit_group_types and isinstance(grp, ViaGroup):
                    grps["via_groups"].append(grp)
            except Exception as e:
                continue
        return grps

    def visit_hierarchy_obj(func):
        @wraps(func)
        def wrapper(self, hierarchy_obj: HierarchyObj):
            hierarchy_obj_properties = self.visit_properties(hierarchy_obj, HierarchyObj)
            properties = func(self, hierarchy_obj)
            if isinstance(properties, dict):
                hierarchy_obj_properties.update(properties)

            return hierarchy_obj_properties

        return wrapper

    @visit_objbase
    @visit_hierarchy_obj
    def visit_component_group(self, component_group: ComponentGroup):
        return self.visit_properties(component_group, ComponentGroup)

    @visit_objbase
    @visit_hierarchy_obj
    def visit_structure3d(self, structure3d: Structure3D):
        return OrderedDict(
            {
                "material": structure3d.get_material(evaluate=True),
                "thickness": structure3d.thickness,
                "mesh_closure": structure3d.mesh_closure,
            }
        )

    @visit_objbase
    @visit_hierarchy_obj
    def visit_via_group(self, via_group: ViaGroup):
        return self.visit_properties(via_group, ViaGroup)
