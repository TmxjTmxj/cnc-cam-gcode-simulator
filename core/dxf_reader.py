"""DXF reader for supported two-dimensional drawing entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians, sin
from pathlib import Path
from typing import Iterable

import ezdxf
from ezdxf import DXFError


SPLINE_SAMPLE_COUNT = 48
ALL_LAYERS_LABEL = "\u5168\u90e8\u56fe\u5c42"


@dataclass(frozen=True)
class DxfLine:
    """A two-dimensional DXF LINE entity."""

    start_x: float
    start_y: float
    end_x: float
    end_y: float
    layer: str = "0"


@dataclass(frozen=True)
class DxfCircle:
    """A two-dimensional DXF CIRCLE entity."""

    center_x: float
    center_y: float
    radius: float
    layer: str = "0"


@dataclass(frozen=True)
class DxfArc:
    """A two-dimensional DXF ARC entity."""

    center_x: float
    center_y: float
    radius: float
    start_angle: float
    end_angle: float
    layer: str = "0"


@dataclass(frozen=True)
class DxfPolyline:
    """A two-dimensional DXF LWPOLYLINE, POLYLINE, or flattened SPLINE entity."""

    points: list[tuple[float, float]]
    is_closed: bool
    layer: str = "0"


@dataclass(frozen=True)
class DxfReadResult:
    """Parsed DXF geometry and summary data for UI display."""

    lines: list[DxfLine] = field(default_factory=list)
    circles: list[DxfCircle] = field(default_factory=list)
    arcs: list[DxfArc] = field(default_factory=list)
    polylines: list[DxfPolyline] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def entity_count(self) -> int:
        """Return the total number of supported entities."""
        return len(self.lines) + len(self.circles) + len(self.arcs) + len(self.polylines)

    @property
    def layers(self) -> list[str]:
        """Return sorted DXF layer names used by supported entities."""
        names = {entity.layer for entity in self.lines + self.circles + self.arcs + self.polylines}
        return sorted(name for name in names if name)

    def filtered_by_layer(self, layer_name: str | None) -> "DxfReadResult":
        """Return a copy containing only geometry on one layer."""
        if not layer_name or layer_name in {ALL_LAYERS_LABEL, "All Layers"}:
            return self
        return DxfReadResult(
            lines=[line for line in self.lines if line.layer == layer_name],
            circles=[circle for circle in self.circles if circle.layer == layer_name],
            arcs=[arc for arc in self.arcs if arc.layer == layer_name],
            polylines=[polyline for polyline in self.polylines if polyline.layer == layer_name],
            warnings=list(self.warnings),
        )

    @property
    def bounds(self) -> tuple[float, float, float, float] | None:
        """Return drawing bounds as min_x, min_y, max_x, max_y."""
        points = self._bounds_points()
        if not points:
            return None
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), min(ys), max(xs), max(ys)

    def summary(self) -> str:
        """Return a compact Chinese summary for the status bar."""
        return (
            f"LINE {len(self.lines)} \u4e2a?"
            f"CIRCLE {len(self.circles)} \u4e2a?"
            f"ARC {len(self.arcs)} \u4e2a?"
            f"POLYLINE {len(self.polylines)} \u4e2a"
        )

    def _bounds_points(self) -> list[tuple[float, float]]:
        """Collect representative points for drawing bounds."""
        points: list[tuple[float, float]] = []
        for line in self.lines:
            points.extend([(line.start_x, line.start_y), (line.end_x, line.end_y)])
        for circle in self.circles:
            points.extend(
                [
                    (circle.center_x - circle.radius, circle.center_y),
                    (circle.center_x + circle.radius, circle.center_y),
                    (circle.center_x, circle.center_y - circle.radius),
                    (circle.center_x, circle.center_y + circle.radius),
                ]
            )
        for arc in self.arcs:
            points.extend(self._arc_sample_points(arc))
        for polyline in self.polylines:
            points.extend(polyline.points)
        return points

    def _arc_sample_points(self, arc: DxfArc) -> list[tuple[float, float]]:
        """Sample an arc so bounds remain useful without heavy geometry."""
        start = arc.start_angle
        end = arc.end_angle
        if end < start:
            end += 360.0
        step_count = 24
        points: list[tuple[float, float]] = []
        for index in range(step_count + 1):
            angle = radians(start + (end - start) * index / step_count)
            points.append(
                (
                    arc.center_x + arc.radius * cos(angle),
                    arc.center_y + arc.radius * sin(angle),
                )
            )
        return points


class DxfReader:
    """Read supported DXF geometry with ezdxf."""

    def read(self, file_path: str | Path) -> DxfReadResult:
        """Read a DXF file and return supported two-dimensional geometry."""
        path = Path(file_path)
        try:
            document = ezdxf.readfile(path)
        except (OSError, IOError, DXFError) as exc:
            raise ValueError(f"\u65e0\u6cd5\u8bfb\u53d6DXF\u6587\u4ef6?{exc}") from exc

        lines: list[DxfLine] = []
        circles: list[DxfCircle] = []
        arcs: list[DxfArc] = []
        polylines: list[DxfPolyline] = []
        warnings: list[str] = []

        for entity in self._iter_supported_entities(document.modelspace(), warnings):
            dxftype = entity.dxftype()
            try:
                if dxftype == "LINE":
                    lines.append(self._read_line(entity))
                elif dxftype == "CIRCLE":
                    circles.append(self._read_circle(entity))
                elif dxftype == "ARC":
                    arcs.append(self._read_arc(entity))
                elif dxftype == "LWPOLYLINE":
                    polylines.append(self._read_lwpolyline(entity))
                elif dxftype == "POLYLINE":
                    polylines.append(self._read_polyline(entity))
                elif dxftype == "SPLINE":
                    polylines.append(self._read_spline(entity))
            except (AttributeError, TypeError, ValueError) as exc:
                warnings.append(f"{dxftype} \u56fe\u5143\u8bfb\u53d6\u5931\u8d25?{exc}")

        return DxfReadResult(
            lines=lines,
            circles=circles,
            arcs=arcs,
            polylines=polylines,
            warnings=warnings,
        )

    def _iter_supported_entities(self, modelspace: object, warnings: list[str]) -> Iterable[object]:
        """Yield supported modelspace entities, expanding INSERT references when possible."""
        for entity in modelspace:
            dxftype = entity.dxftype()
            if dxftype == "INSERT":
                insert_layer = self._entity_layer(entity)
                try:
                    for virtual in entity.virtual_entities():
                        if self._is_supported_type(virtual.dxftype()):
                            if hasattr(virtual, "dxf"):
                                virtual.dxf.layer = insert_layer
                            yield virtual
                except (DXFError, AttributeError, TypeError, ValueError) as exc:
                    warnings.append(f"INSERT \u5757\u5f15\u7528\u5c55\u5f00\u5931\u8d25?{exc}")
                continue
            if self._is_supported_type(dxftype):
                yield entity

    def _is_supported_type(self, dxftype: str) -> bool:
        """Return whether an entity type can be converted into 2D preview geometry."""
        return dxftype in {"LINE", "CIRCLE", "ARC", "LWPOLYLINE", "POLYLINE", "SPLINE"}

    def _entity_layer(self, entity: object) -> str:
        """Return the entity layer, defaulting to layer 0."""
        return str(getattr(entity.dxf, "layer", "0") or "0")

    def _read_line(self, entity: object) -> DxfLine:
        """Convert an ezdxf LINE entity to a DxfLine."""
        start = entity.dxf.start
        end = entity.dxf.end
        return DxfLine(float(start.x), float(start.y), float(end.x), float(end.y), self._entity_layer(entity))

    def _read_circle(self, entity: object) -> DxfCircle:
        """Convert an ezdxf CIRCLE entity to a DxfCircle."""
        center = entity.dxf.center
        return DxfCircle(float(center.x), float(center.y), float(entity.dxf.radius), self._entity_layer(entity))

    def _read_arc(self, entity: object) -> DxfArc:
        """Convert an ezdxf ARC entity to a DxfArc."""
        center = entity.dxf.center
        return DxfArc(
            center_x=float(center.x),
            center_y=float(center.y),
            radius=float(entity.dxf.radius),
            start_angle=float(entity.dxf.start_angle),
            end_angle=float(entity.dxf.end_angle),
            layer=self._entity_layer(entity),
        )

    def _read_lwpolyline(self, entity: object) -> DxfPolyline:
        """Convert an ezdxf LWPOLYLINE entity to a DxfPolyline."""
        points = [(float(x), float(y)) for x, y in entity.get_points("xy")]
        return DxfPolyline(points=points, is_closed=bool(entity.closed), layer=self._entity_layer(entity))

    def _read_polyline(self, entity: object) -> DxfPolyline:
        """Convert an ezdxf POLYLINE entity to a DxfPolyline."""
        points = [
            (float(vertex.dxf.location.x), float(vertex.dxf.location.y))
            for vertex in entity.vertices
        ]
        return DxfPolyline(points=points, is_closed=bool(entity.is_closed), layer=self._entity_layer(entity))

    def _read_spline(self, entity: object) -> DxfPolyline:
        """Flatten an ezdxf SPLINE entity into a polyline approximation."""
        try:
            points = [(float(point.x), float(point.y)) for point in entity.flattening(0.05)]
        except (AttributeError, TypeError, ValueError):
            construction = entity.construction_tool()
            points = [(float(point.x), float(point.y)) for point in construction.approximate(SPLINE_SAMPLE_COUNT)]
        if len(points) < 2:
            raise ValueError("SPLINE \u79bb\u6563\u540e\u70b9\u6570\u4e0d\u8db3")
        return DxfPolyline(points=points, is_closed=False, layer=self._entity_layer(entity))
