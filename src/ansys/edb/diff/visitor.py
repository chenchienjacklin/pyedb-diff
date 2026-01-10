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
    def set_visit_types(self, visit_types: dict):
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

    def set_visit_types(self, visit_types: dict):
        excluded_types = [
            edb_obj
            for edb_obj, _ in self.visit_map.items()
            if not visit_types.get(edb_obj.__name__, False)
        ]
        for edb_obj in excluded_types:
            self.visit_map.pop(edb_obj)

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
        return OrderedDict(
            {
                "directory": database.directory,
                "version": database.version,
                "source": database.source,
                "source_version": database.source_version,
                "material_defs": database.material_defs if MaterialDef in self.visit_map else [],
                "padstack_defs": database.padstack_defs if PadstackDef in self.visit_map else [],
                "component_defs": database.component_defs if ComponentDef in self.visit_map else [],
                "circuit_cells": database.circuit_cells if Cell in self.visit_map else [],
                "footprint_cells": database.footprint_cells,
            }
        )

    @visit_objbase
    def visit_material_def(self, material_def: MaterialDef):
        material_properties = OrderedDict()
        for material_property in material_def.all_properties:
            row, col = material_def.get_dimensions(material_property)
            values = []
            for r in range(row):
                for c in range(col):
                    values.append(material_def.get_property(material_property, r, c))
            material_properties[material_property.name] = values

        return OrderedDict(
            {
                "name": material_def.name,
                "material_properties": material_properties,
            }
        )

    @visit_objbase
    def visit_padstack_def(self, padstack_def: PadstackDef):
        return OrderedDict(
            {
                "name": padstack_def.name,
                "data": padstack_def.data if PadstackDefData in self.visit_map else None,
            }
        )

    @visit_objbase
    def visit_padstack_def_data(self, padstack_def_data: PadstackDefData):
        return OrderedDict(
            {
                "material": padstack_def_data.material,
                "layer_names": padstack_def_data.layer_names,
                "pad_parameters": self.visit_pad_parameters(padstack_def_data),
            }
        )

    def visit_pad_parameters(self, padstack_def_data: PadstackDefData):
        params = OrderedDict()
        for pad_type in [PadType.REGULAR_PAD, PadType.ANTI_PAD, PadType.THERMAL_PAD]:
            params[pad_type.name] = OrderedDict()
            for layer_name in padstack_def_data.layer_names:
                params[pad_type.name][layer_name] = padstack_def_data.get_pad_parameters(
                    layer_name, pad_type
                )
        return params

    @visit_objbase
    def visit_component_def(self, component_def: ComponentDef):
        return OrderedDict(
            {
                "name": component_def.name,
                "component_models": component_def.component_models,
            }
        )

    @visit_objbase
    def visit_component_model(self, component_model: ComponentModel):
        return OrderedDict(
            {
                "reference_file": component_model.reference_file,
                "name": component_model.name,
                "component_model_type": component_model.component_model_type,
            }
        )

    @visit_objbase
    def visit_cell(self, cell: Cell):
        return OrderedDict(
            {
                "layout": cell.layout,
                "is_footprint": cell.is_footprint,
                "is_blackbox": cell.is_blackbox,
                "suppress_pads": cell.suppress_pads,
                "anti_pads_always_on": cell.anti_pads_always_on,
                "anti_pads_option": cell.anti_pads_option,
                "is_symbolic_footprint": cell.is_symbolic_footprint,
                "name": cell.name,
                "design_mode": cell.design_mode,
            }
        )

    @visit_objbase
    def visit_layout(self, layout: Layout):
        return OrderedDict(
            {
                "primitives": self.visit_primitives(layout.primitives)
                if any(prim in self.visit_map for prim in [Rectangle, Circle, Polygon, Path])
                else {},
                "padstack_instances": layout.padstack_instances
                if PadstackInstance in self.visit_map
                else [],
                "groups": self.visit_groups(layout.groups)
                if any(grp in self.visit_map for grp in [ComponentGroup, Structure3D, ViaGroup])
                else {},
            }
        )

    def visit_primitives(self, primitives: list[Primitive]):
        prims = {"rectangles": [], "circles": [], "polygons": [], "paths": []}
        for primitive in primitives:
            try:
                layer = primitive.layer.is_null
                if Rectangle in self.visit_map and isinstance(primitive, Rectangle):
                    prims["rectangles"].append(primitive)
                elif Circle in self.visit_map and isinstance(primitive, Circle):
                    prims["circles"].append(primitive)
                elif Polygon in self.visit_map and isinstance(primitive, Polygon):
                    prims["polygons"].append(primitive)
                elif Path in self.visit_map and isinstance(primitive, Path):
                    prims["paths"].append(primitive)
            except Exception as e:
                continue
        return prims

    def visit_primitive(func):
        @wraps(func)
        def wrapper(self, primitive: Primitive):
            primitive_properties = OrderedDict(
                {
                    "net_name": primitive.net.name if primitive.net is not None else "",
                    "primitive_type": primitive.primitive_type,
                    "layer_name": primitive.layer.name,
                    "is_negative": primitive.is_negative,
                    "is_void": primitive.is_void,
                    "has_voids": primitive.has_voids,
                    "owner": primitive.owner,
                    "is_parameterized": primitive.is_parameterized,
                    "is_zone_primitive": primitive.is_zone_primitive,
                    "can_be_zone_primitive": primitive.can_be_zone_primitive,
                }
            )

            if primitive.is_void:
                primitive_properties.update(
                    {
                        "voids:": self.visit_primitives(primitive.voids),
                    }
                )

            properties = func(self, primitive)

            if isinstance(properties, dict):
                primitive_properties.update(properties)

            return primitive_properties

        return wrapper

    @visit_objbase
    @visit_primitive
    def visit_rectangle(self, rectangle: Rectangle):
        return OrderedDict(
            {
                "parameters": rectangle.get_parameters(),
            }
        )

    @visit_objbase
    @visit_primitive
    def visit_circle(self, circle: Circle):
        return OrderedDict(
            {
                "parameters": circle.get_parameters(),
            }
        )

    @visit_objbase
    @visit_primitive
    def visit_polygon(self, polygon: Polygon):
        return OrderedDict(
            {
                "polygon_data": self.visit_polygon_data(polygon.polygon_data),
            }
        )

    def visit_polygon_data(self, polygon_data: PolygonData):
        return OrderedDict(
            {
                "points": polygon_data.points,
                "is_closed": polygon_data.is_closed,
                "sense": polygon_data.sense,
            }
        )

    @visit_objbase
    @visit_primitive
    def visit_path(self, path: Path):
        return OrderedDict(
            {
                "center_line": self.visit_polygon_data(path.center_line),
                "width": path.width,
            }
        )

    @visit_objbase
    def visit_padstack_instance(self, padstack_instance: PadstackInstance):
        position_and_rotation = padstack_instance.get_position_and_rotation()
        return OrderedDict(
            {
                "net_name": padstack_instance.net.name if padstack_instance.net is not None else "",
                "name": padstack_instance.name,
                "position": (position_and_rotation[0], position_and_rotation[1]),
                "rotation": position_and_rotation[2],
                "padstack_def": padstack_instance.padstack_def,
                "layer_range": [layer.name for layer in padstack_instance.get_layer_range()],
                "hole_overrides": padstack_instance.get_hole_overrides(),
                "is_layout_pin": padstack_instance.is_layout_pin,
                "group": padstack_instance.group,
            }
        )

    def visit_groups(self, groups: list[Group]):
        grps = {"component_groups": [], "structure3d_groups": [], "via_groups": []}
        for group in groups:
            try:
                grp = group.cast()
                if ComponentGroup in self.visit_map and isinstance(grp, ComponentGroup):
                    grps["component_groups"].append(grp)
                elif Structure3D in self.visit_map and isinstance(grp, Structure3D):
                    grps["structure3d_groups"].append(grp)
                elif ViaGroup in self.visit_map and isinstance(grp, ViaGroup):
                    grps["via_groups"].append(grp)
            except Exception as e:
                continue
        return grps

    def visit_hierarchy_obj(func):
        @wraps(func)
        def wrapper(self, hierarchy_obj: HierarchyObj):
            hierarchy_obj_properties = OrderedDict(
                {
                    "net_name": hierarchy_obj.net.name if hierarchy_obj.net is not None else "",
                    "transform": hierarchy_obj.transform,
                    "name": hierarchy_obj.name,
                    "component_def": hierarchy_obj.component_def,
                    "placement_layer": hierarchy_obj.placement_layer,
                    "location": hierarchy_obj.location,
                    "solve_independent_preference": hierarchy_obj.solve_independent_preference,
                }
            )

            properties = func(self, hierarchy_obj)

            if isinstance(properties, dict):
                hierarchy_obj_properties.update(properties)

            return hierarchy_obj_properties

        return wrapper

    @visit_objbase
    @visit_hierarchy_obj
    def visit_component_group(self, component_group: ComponentGroup):
        return OrderedDict(
            {
                "num_pins": component_group.num_pins,
                "component_property": component_group.component_property,
                "component_type": component_group.component_type,
            }
        )

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
        return OrderedDict(
            {
                "outline": self.visit_polygon_data(via_group.outline),
                "conductor_percentage": via_group.conductor_percentage,
                "persistent": via_group.persistent,
            }
        )
