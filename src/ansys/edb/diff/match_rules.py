class CompareRule:
    @staticmethod
    def is_equal(item1, item2):
        raise NotImplementedError("Subclasses should implement this method")


class ComparePointData(CompareRule):
    @staticmethod
    def is_equal(point1, point2):
        if point1 is None and point2 is None:
            return True
        if point1 is None or point2 is None:
            return False
        return point1.equals(point2)


class MatchRule:
    @staticmethod
    def is_match(item1, item2):
        raise NotImplementedError("Subclasses should implement this method")


class MatchBySequence(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return True


class MatchByType(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return isinstance(item1, type(item2))


class MatchByName(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return item1.name == item2.name


class MatchById(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return item1.id == item2.id


class MatchByLayerId(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return item1.layer.id == item2.layer.id


class MatchByLayerName(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return item1.layer.name == item2.layer.name


class MatchByRectangleProperties(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return (
            item1.center_x == item2.center_x
            and item1.center_y == item2.center_y
            and item1.width == item2.width
            and item1.height == item2.height
        )


class MatchByCircleProperties(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return (
            item1.center_x == item2.center_x
            and item1.center_y == item2.center_y
            and item1.radius == item2.radius
        )


class MatchByPolygonProperties(MatchRule):
    def _get_identity_point(polygon):
        if hasattr(polygon, "identity_point"):
            return polygon.identity_point

        polygon.identity_point = None
        points = polygon.polygon_data.points
        if len(points) == 0:
            return None
        point = points[0]
        for i in range(1, len(points)):
            p = points[i]
            if p.is_arc is True:
                continue

            tolerance = 1e-9
            if p.x.double < point.x.double - tolerance:
                point = p
                continue

            if abs(p.x.double - point.x.double) < tolerance:
                if p.y.double < point.y.double - tolerance:
                    point = p
                elif abs(p.y.double - point.y.double) < tolerance:
                    if p.y.double < point.y.double:
                        point = p

        polygon.identity_point = point
        return point

    @staticmethod
    def is_match(item1, item2):
        return ComparePointData.is_equal(
            MatchByPolygonProperties._get_identity_point(item1),
            MatchByPolygonProperties._get_identity_point(item2),
        )


class MatchByPathProperties(MatchRule):
    def _get_identity_point(path):
        if hasattr(path, "identity_point"):
            return path.identity_point

        path.identity_point = None
        points = path.center_line.points
        if len(points) == 0:
            return None
        point = points[0]
        for i in range(1, len(points)):
            p = points[i]
            if p.is_arc is True:
                continue

            tolerance = 1e-9
            if p.x.double < point.x.double - tolerance:
                point = p
                continue

            if abs(p.x.double - point.x.double) < tolerance:
                if p.y.double < point.y.double - tolerance:
                    point = p
                elif abs(p.y.double - point.y.double) < tolerance:
                    if p.y.double < point.y.double:
                        point = p

        path.identity_point = point
        return point

    @staticmethod
    def is_match(item1, item2):
        return ComparePointData.is_equal(
            MatchByPathProperties._get_identity_point(item1),
            MatchByPathProperties._get_identity_point(item2),
        )


class MatchByPadstackInstanceProperties(MatchRule):
    @staticmethod
    def is_match(item1, item2):
        return (
            item1.is_layout_pin == item2.is_layout_pin
            and item1.get_position_and_rotation() == item2.get_position_and_rotation()
            and [layer.name for layer in item1.get_layer_range()]
            == [layer.name for layer in item2.get_layer_range()]
        )
