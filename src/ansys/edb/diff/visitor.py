from collections import OrderedDict

from ansys.edb.core.database import Database
from ansys.edb.core.definition.material_def import MaterialDef
from ansys.edb.core.definition.padstack_def import PadstackDef, PadstackDefData
from ansys.edb.core.definition.padstack_def_data import PadType
from ansys.edb.core.geometry.polygon_data import PolygonData
from ansys.edb.core.layout.cell import Cell
from ansys.edb.core.layout.layout import Layout
from ansys.edb.core.primitive.circle import Circle
from ansys.edb.core.primitive.padstack_instance import PadstackInstance
from ansys.edb.core.primitive.path import Path
from ansys.edb.core.primitive.polygon import Polygon
from ansys.edb.core.primitive.primitive import Primitive
from ansys.edb.core.primitive.rectangle import Rectangle


class EdbObjVisitor:
    def __init__(self, logger=None):
        self.logger = logger
        self.visit_map = {
            Database: self.visit_database,
            MaterialDef: self.visit_material_def,
            PadstackDef: self.visit_padstack_def,
            PadstackDefData: self.visit_padstack_def_data,
            Cell: self.visit_cell,
            Layout: self.visit_layout,
            Rectangle: self.visit_rectangle,
            Circle: self.visit_circle,
            Polygon: self.visit_polygon,
            Path: self.visit_path,
            PadstackInstance: self.visit_padstack_instance,
        }

    def visit(self, edb_obj):
        visitor = self.visit_map.get(type(edb_obj), None)
        if visitor is not None:
            return visitor(edb_obj)
        return {}

    def visit_database(self, database: Database):
        if database.id == 0:
            return OrderedDict()

        return OrderedDict(
            {
                "directory": database.directory,
                "version": database.version,
                "source": database.source,
                "source_version": database.source_version,
                "material_defs": [md for md in database.material_defs],
                "padstack_defs": [pd for pd in database.padstack_defs],
                "circuit_cells": [cell for cell in database.circuit_cells],
                "footprint_cells": [cell for cell in database.footprint_cells],
            }
        )

    def visit_material_def(self, material_def: MaterialDef):
        if material_def.id == 0:
            return OrderedDict()

        material_properties = OrderedDict()
        for material_property in material_def.all_properties:
            row, col = material_def.get_dimensions(material_property)
            values = []
            for r in range(row):
                for c in range(col):
                    values.append(material_def.get_property(material_property, r, c))
            material_properties[material_property.name] = values

        return OrderedDict({"name": material_def.name, "material_properties": material_properties})

    def visit_padstack_def(self, padstack_def: PadstackDef):
        if padstack_def.id == 0:
            return OrderedDict()

        return OrderedDict(
            {
                "name": padstack_def.name,
                "data": padstack_def.data,
            }
        )

    def visit_padstack_def_data(self, padstack_def_data: PadstackDefData):
        if padstack_def_data.id == 0:
            return OrderedDict()

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

    def visit_cell(self, cell: Cell):
        if cell.id == 0:
            return OrderedDict()

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

    def visit_layout(self, layout: Layout):
        if layout.id == 0:
            return OrderedDict()

        return OrderedDict(
            {
                "primitives": self.visit_primitives(layout.primitives),
                "padstack_instances": layout.padstack_instances,
            }
        )

    def visit_primitives(self, primitives: list[Primitive]):
        prims = {"rectangles": [], "circles": [], "polygons": [], "paths": []}
        for primitive in primitives:
            try:
                layer = primitive.layer.is_null
                if isinstance(primitive, Rectangle):
                    prims["rectangles"].append(primitive)
                elif isinstance(primitive, Circle):
                    prims["circles"].append(primitive)
                elif isinstance(primitive, Polygon):
                    prims["polygons"].append(primitive)
                elif isinstance(primitive, Path):
                    prims["paths"].append(primitive)
            except Exception as e:
                continue
        return prims

    def visit_primitive(self, primitive: Primitive):
        if primitive.id == 0:
            return OrderedDict()

        properties = OrderedDict(
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
        if properties.get("is_void", False):
            properties.update(
                {
                    "voids:": self.visit_primitives(primitive.voids),
                }
            )
        return properties

    def visit_rectangle(self, rectangle: Rectangle):
        properties = self.visit_primitive(rectangle)
        if len(properties) != 0:
            properties.update(
                OrderedDict(
                    {
                        "parameters": rectangle.get_parameters(),
                    }
                )
            )
        return properties

    def visit_circle(self, circle: Circle):
        properties = self.visit_primitive(circle)
        if len(properties) != 0:
            properties.update(
                OrderedDict(
                    {
                        "parameters": circle.get_parameters(),
                    }
                )
            )
        return properties

    def visit_polygon(self, polygon: Polygon):
        properties = self.visit_primitive(polygon)
        if len(properties) != 0:
            properties.update(
                OrderedDict(
                    {
                        "polygon_data": self.visit_polygon_data(polygon.polygon_data),
                    }
                )
            )
        return properties

    def visit_polygon_data(self, polygon_data: PolygonData):
        return OrderedDict(
            {
                "points": polygon_data.points,
                "is_closed": polygon_data.is_closed,
                "sense": polygon_data.sense,
            }
        )

    def visit_path(self, path: Path):
        properties = self.visit_primitive(path)
        if len(properties) != 0:
            properties.update(
                OrderedDict(
                    {
                        "center_line": self.visit_polygon_data(path.center_line),
                        "width": path.width,
                    }
                )
            )
        return properties

    def visit_padstack_instance(self, padstack_instance: PadstackInstance):
        if padstack_instance.id == 0:
            return OrderedDict()

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
            }
        )
