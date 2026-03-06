from abc import ABC, abstractmethod
from collections import OrderedDict
from functools import wraps
from enum import Enum

from ansys.edb.core.database import Database
from ansys.edb.core.definition.component_def import ComponentDef
from ansys.edb.core.definition.component_model import ComponentModel
from ansys.edb.core.definition.component_property import ComponentProperty
from ansys.edb.core.definition.ic_component_property import ICComponentProperty
from ansys.edb.core.definition.io_component_property import IOComponentProperty
from ansys.edb.core.definition.rlc_component_property import RLCComponentProperty
from ansys.edb.core.definition.material_def import MaterialDef
from ansys.edb.core.definition.padstack_def import PadstackDef, PadstackDefData
from ansys.edb.core.definition.padstack_def_data import PadType
from ansys.edb.core.definition.bondwire_def import BondwireDef, ApdBondwireDef, Jedec4BondwireDef, Jedec5BondwireDef
from ansys.edb.core.definition.package_def import PackageDef
from ansys.edb.core.geometry.polygon_data import PolygonData
from ansys.edb.core.hierarchy.component_group import ComponentGroup
from ansys.edb.core.hierarchy.group import Group
from ansys.edb.core.hierarchy.hierarchy_obj import HierarchyObj
from ansys.edb.core.hierarchy.structure3d import Structure3D
from ansys.edb.core.hierarchy.via_group import ViaGroup
from ansys.edb.core.inner.conn_obj import ConnObj
from ansys.edb.core.layout.cell import Cell
from ansys.edb.core.layout.layout import Layout
from ansys.edb.core.primitive.circle import Circle
from ansys.edb.core.primitive.padstack_instance import PadstackInstance
from ansys.edb.core.primitive.path import Path
from ansys.edb.core.primitive.polygon import Polygon
from ansys.edb.core.primitive.primitive import Primitive
from ansys.edb.core.primitive.rectangle import Rectangle
from ansys.edb.core.primitive.primitive_instance_collection import PrimitiveInstanceCollection
from ansys.edb.core.primitive.bondwire import Bondwire
from ansys.edb.core.utility.transform import Transform


class VisitorBase(ABC):
    @abstractmethod
    def set_visit_rules(self, rules: dict):
        pass

    @abstractmethod
    def visit(self, edb_obj, recursive: bool):
        pass


class EdbObjVisitorV1(VisitorBase):
    def __init__(self, logger=None):
        self.logger = logger
        self.visit_map = {
            Database: self.visit_database,
            MaterialDef: self.visit_material_def,
            PadstackDef: self.visit_padstack_def,
            PadstackDefData: self.visit_padstack_def_data,
            ComponentDef: self.visit_component_def,
            ComponentModel: self.visit_component_model,
            ApdBondwireDef: self.visit_bondwire_def,
            Jedec4BondwireDef: self.visit_bondwire_def,
            Jedec5BondwireDef: self.visit_bondwire_def,
            PackageDef: self.visit_package_def,
            Cell: self.visit_cell,
            Layout: self.visit_layout,
            Rectangle: self.visit_rectangle,
            Circle: self.visit_circle,
            Polygon: self.visit_polygon,
            PolygonData: self.visit_polygon_data,
            Path: self.visit_path,
            PrimitiveInstanceCollection: self.visit_primitive_instance_collection,
            Bondwire: self.visit_bondwire,
            HierarchyObj: self.visit_hierarchy_obj,
            Transform: self.visit_transform,
            PadstackInstance: self.visit_padstack_instance,
            ComponentGroup: self.visit_component_group,
            ICComponentProperty: self.visit_component_property,
            IOComponentProperty: self.visit_component_property,
            RLCComponentProperty: self.visit_component_property,
            Structure3D: self.visit_structure3d,
            ViaGroup: self.visit_via_group,
        }
        
        # Initialize visit rules with empty lists for all EDB object types
        self.visit_rules = {
            Database: [],
            MaterialDef: [],
            PadstackDef: [],
            PadstackDefData: [],
            ComponentDef: [],
            ComponentModel: [],
            BondwireDef: [],
            PackageDef: [],
            Cell: [],
            Layout: [],
            Primitive: [],
            Rectangle: [],
            Circle: [],
            Polygon: [],
            PolygonData: [],
            Path: [],
            PrimitiveInstanceCollection: [],
            Bondwire: [],
            PadstackInstance: [],
            HierarchyObj: [],
            Transform: [],
            ComponentGroup: [],
            ComponentProperty: [],
            Structure3D: [],
            ViaGroup: [],
        }

        self.visit_functions = {
            MaterialDef: {"material_properties": self.visit_material_properties},
            PadstackDefData: {"pad_parameters": self.visit_pad_parameters},
            BondwireDef: {"parameters": lambda obj: obj.get_parameters() if hasattr(obj, "get_parameters") else None},
            Layout: {"primitives": lambda obj: self.visit_primitives(obj.primitives) if hasattr(obj, "primitives") else None,
                     "groups": lambda obj: self.visit_groups(obj.groups) if hasattr(obj, "groups") else None},
            Primitive: {"net_name": lambda obj: obj.net.name if hasattr(obj, "net") and obj.net is not None else None,
                        "layer_name": lambda obj: obj.layer.name if hasattr(obj, "layer") and obj.layer is not None else None,
                        "owner": lambda obj: obj.owner.edb_uid if hasattr(obj, "owner") and obj.owner is not None else None,
                        "voids": lambda obj: self.visit_primitives(obj.voids) if hasattr(obj, "has_voids") and obj.has_voids else None},
            Rectangle: {"parameters": lambda obj: obj.get_parameters() if hasattr(obj, "get_parameters") else None},
            Circle: {"parameters": lambda obj: obj.get_parameters() if hasattr(obj, "get_parameters") else None},
            HierarchyObj: {"net_name": lambda obj: obj.net.name if hasattr(obj, "net") and obj.net is not None else None,
                           "placement_layer": lambda obj: obj.placement_layer.name if hasattr(obj, "placement_layer") and obj.placement_layer is not None else None},
            ComponentProperty: {"package_def": lambda obj: obj.package_def.name if hasattr(obj, "package_def") and not obj.package_def.is_null else None},
            Structure3D: {"material": lambda obj: obj.get_material(evaluate=True) if hasattr(obj, "get_material") else None},
        }

    def set_visit_rules(self, rules):
        for edb_obj, _ in self.visit_rules.items():
            self.visit_rules[edb_obj] = rules.get(edb_obj.__name__, [])
    
    def visit_properties(self, obj, obj_type):
        properties = OrderedDict()
        visit_funcs = self.visit_functions.get(obj_type, {})
        for prop in self.visit_rules.get(obj_type, []):
            visit_func = visit_funcs.get(prop, None)
            if visit_func is not None:
                try:
                    properties[prop] = visit_func(obj)
                except Exception as e:
                    if self.logger is not None:
                        self.logger.warning(f"Failed to visit property {prop} for {obj_type.__name__}: {e}")
                continue
            
            if hasattr(obj, prop):
                properties[prop] = getattr(obj, prop)
            else:
                self.logger.warning(f"{obj_type.__name__} object does not have property {prop}")
        return properties

    def visit(self, edb_obj, recursive=False):
        if edb_obj is None:
            return None
        
        if recursive:
            if isinstance(edb_obj, list):
                return [self.visit(item, recursive=True) for item in edb_obj]
            elif isinstance(edb_obj, dict):
                return {k: self.visit(v, recursive=True) for k, v in edb_obj.items()}
            elif isinstance(edb_obj, tuple):
                return tuple(self.visit(item, recursive=True) for item in edb_obj)

        visitor = self.visit_map.get(type(edb_obj), None)
        if visitor is not None:
            properties = visitor(edb_obj)
            if recursive:
                return self.visit(properties, recursive=True)
            return properties
        
        return self.to_string(edb_obj)

    def to_string(self, val):
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        elif isinstance(val, tuple):
            return ", ".join(self.to_string(v) for v in val)
        elif isinstance(val, Enum):
            return val.name
        return str(val)

    def visit_database(self, database: Database):
        return self.visit_properties(database, Database)

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

    def visit_padstack_def(self, padstack_def: PadstackDef):
        return self.visit_properties(padstack_def, PadstackDef)

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

    def visit_component_def(self, component_def: ComponentDef):
        return self.visit_properties(component_def, ComponentDef)

    def visit_component_model(self, component_model: ComponentModel):
        return self.visit_properties(component_model, ComponentModel)

    def visit_bondwire_def(self, bondwire_def: BondwireDef):
        return self.visit_properties(bondwire_def, BondwireDef)
    
    def visit_package_def(self, package_def: PackageDef):
        return self.visit_properties(package_def, PackageDef)

    def visit_cell(self, cell: Cell):
        return self.visit_properties(cell, Cell)

    def visit_layout(self, layout: Layout):
        return self.visit_properties(layout, Layout)

    def visit_primitives(self, primitives: list[Primitive]):
        prims = {"rectangles": [], "circles": [], "polygons": [], "paths": [], "primitive_instance_collections": [], "bondwires": []}
        visit_prim_types = [prim for prim in [Rectangle, Circle, Polygon, Path, PrimitiveInstanceCollection, Bondwire] if len(self.visit_rules.get(prim, [])) > 0]
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
                elif PrimitiveInstanceCollection in visit_prim_types and isinstance(primitive, PrimitiveInstanceCollection):
                    prims["primitive_instance_collections"].append(primitive)
                elif Bondwire in visit_prim_types and isinstance(primitive, Bondwire):
                    prims["bondwires"].append(primitive)
            except Exception as e:
                if self.logger is not None:
                    self.logger.warning(f"Skipping primitive due to error: {e}")
                continue
        return prims

    def visit_connobj(func):
        @wraps(func)
        def wrapper(self, obj: ConnObj):
            objbase_properties = OrderedDict()
            if not isinstance(obj, ConnObj):
                self.logger.warning(f"Expected ConnObj instance, got {type(obj)}")
                return objbase_properties

            if obj.id == 0:
                return objbase_properties

            objbase_properties["id"] = obj.edb_uid
            properties = func(self, obj)

            if isinstance(properties, dict):
                objbase_properties.update(properties)
            return objbase_properties

        return wrapper

    def visit_primitive(func):
        @wraps(func)
        def wrapper(self, primitive: Primitive):
            primitive_properties = self.visit_properties(primitive, Primitive)
            properties = func(self, primitive)
            if isinstance(properties, dict):
                primitive_properties.update(properties)

            return primitive_properties

        return wrapper

    @visit_connobj
    @visit_primitive
    def visit_rectangle(self, rectangle: Rectangle):
        return self.visit_properties(rectangle, Rectangle)

    @visit_connobj
    @visit_primitive
    def visit_circle(self, circle: Circle):
        return self.visit_properties(circle, Circle)

    @visit_connobj
    @visit_primitive
    def visit_polygon(self, polygon: Polygon):
        return self.visit_properties(polygon, Polygon)

    def visit_polygon_data(self, polygon_data: PolygonData):
        return self.visit_properties(polygon_data, PolygonData)

    @visit_connobj
    @visit_primitive
    def visit_path(self, path: Path):
        return self.visit_properties(path, Path)
    
    @visit_connobj
    @visit_primitive
    def visit_primitive_instance_collection(self, primitive_instance_collection: PrimitiveInstanceCollection):
        return self.visit_properties(primitive_instance_collection, PrimitiveInstanceCollection)

    @visit_connobj
    @visit_primitive
    def visit_bondwire(self, bondwire: Bondwire):
        return self.visit_properties(bondwire, Bondwire)

    @visit_connobj
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
                "group_name": padstack_instance.group.name if padstack_instance.group is not None else "",
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

    def visit_transform(self, transform: Transform):
        return self.visit_properties(transform, Transform)

    @visit_connobj
    @visit_hierarchy_obj
    def visit_component_group(self, component_group: ComponentGroup):
        return self.visit_properties(component_group, ComponentGroup)
    
    def visit_component_property(self, component_property: ComponentProperty):
        return self.visit_properties(component_property, ComponentProperty)

    @visit_connobj
    @visit_hierarchy_obj
    def visit_structure3d(self, structure3d: Structure3D):
        return self.visit_properties(structure3d, Structure3D)
    
    @visit_connobj
    @visit_hierarchy_obj
    def visit_via_group(self, via_group: ViaGroup):
        return self.visit_properties(via_group, ViaGroup)
