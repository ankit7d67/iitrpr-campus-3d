"""Headless Blender script: build the IIT Ropar campus from OSM GeoJSON + facade sheet.

Run:  blender -b -P blender/scripts/import_osm.py

Coordinate system
-----------------
Origin = centre of the campus bbox. Blender X = east (m), Y = north (m), Z = up (m).
The glTF exporter converts that to three.js X = east, Y = up, Z = -north, which is the
same convention `scripts/build_nav.py` uses for nav.json / scatter.json.

Only buildings listed in data-src/facade_sheet.csv are built, so contained duplicate
footprints (see build/dedupe.json) are never extruded twice. Nothing here invents campus
facts: floors/colours/roofs come from the facade sheet, flagged verified=false there.
"""

import csv
import json
import math
import os

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FLOOR_HEIGHT = 3.5
PLINTH_HEIGHT = 0.6
ROAD_WIDTHS = {"tertiary": 8.0, "unclassified": 6.0, "service": 4.0, "path": 2.5}
GROUND_SIZE = 5000.0
ROAD_Z = 0.06


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(value: str) -> tuple[float, float, float, float]:
    value = (value or "#c9c2b4").lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


def material(name: str, colour: str, roughness: float = 0.9) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = hex_rgba(colour)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def add_window_mask(mat: bpy.types.Material, wall_colour: tuple[float, float, float, float], window_colour: tuple[float, float, float, float], window_scale: float = 2.0) -> None:
    """Cheap procedural window rows on the wall material: Wave texture bands masked through a
    colour ramp. No extra geometry, no textures, no new material."""
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.9
    tex = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (window_scale, window_scale, window_scale)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = wall_colour
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = window_colour
    nt.links.new(tex.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return


def local_scale(lat: float) -> tuple[float, float]:
    """Metres per degree (lat, lon) at the given latitude."""
    phi = math.radians(lat)
    m_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    return m_lat, m_lon


def project(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    """lat/lon -> (east, north) metres."""
    m_lat, m_lon = local_scale(lat)
    return (lon - lon0) * m_lon, (lat - lat0) * m_lat


def ring_metres(ring: list, lat0: float, lon0: float) -> list[tuple[float, float]]:
    """GeoJSON building ring ([lat, lon] pairs) -> closed list of (east, north)."""
    pts = [project(pt[0], pt[1], lat0, lon0) for pt in ring]
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-6:
        pts = pts[:-1]
    # Drop consecutive duplicates that would create zero-area quads.
    out = []
    for pt in pts:
        if not out or math.dist(pt, out[-1]) > 1e-3:
            out.append(pt)
    if len(out) > 1 and math.dist(out[0], out[-1]) <= 1e-3:
        out.pop()
    return out


def signed_area(ring: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1]
        for i in range(len(ring))
    )


def add_mesh_object(name: str, verts: list, faces: list, mats: list, face_mats: list | None = None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for mat in mats:
        obj.data.materials.append(mat)
    if face_mats:
        for poly, index in zip(mesh.polygons, face_mats):
            poly.material_index = index
    return obj


def build_building(bid: str, ring: list[tuple[float, float]], floors: int, wall_mat, roof_mat) -> None:
    if len(ring) < 3:
        return
    if signed_area(ring) < 0:
        ring = list(reversed(ring))
    height = PLINTH_HEIGHT + max(1, floors) * FLOOR_HEIGHT
    n = len(ring)
    verts = [(x, y, 0.0) for x, y in ring] + [(x, y, height) for x, y in ring]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    faces.append(tuple(range(n, 2 * n)))  # flat roof
    # Walls use material 0, the roof face uses material 1.
    face_mats = [0] * (len(faces) - 1) + [1]
    obj = add_mesh_object(bid, verts, faces, [wall_mat, roof_mat], face_mats)
    obj["bid"] = bid
    obj["verified"] = "false"


def add_entrance(name: str, loc: tuple[float, float, float], mat, radius: float = 2.0) -> None:
    """Low-poly octahedron entrance marker at an (east, north, up) location."""
    x, y, z = loc
    r = radius
    verts = [
        (x + r, y, z), (x - r, y, z), (x, y + r, z), (x, y - r, z),
        (x, y, z + r), (x, y, z - r),
    ]
    faces = [
        (0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
        (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj["bid"] = name
    return obj


def nearest_road_point(pt: tuple[float, float, float], features: list, lat0: float, lon0: float,
                       south: float, north: float, west: float, east: float):
    """Nearest point on a near-campus road/footpath from a building point; returns (x, y, z, angle)."""
    bx, by = pt[0], pt[1]
    best = None
    for f in features:
        p = f.get("properties") or {}
        if p.get("layer") not in ("road", "footpath"):
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        coords = geom.get("coordinates") or []
        for i in range(len(coords) - 1):
            (a0, a1), (b0, b1) = coords[i], coords[i + 1]
            ax, ay = (a0 - lat0) * 110_900.0, (a1 - lon0) * 95_500.0
            bx2, by2 = (b0 - lat0) * 110_900.0, (b1 - lon0) * 95_500.0
            dx, dy = bx2 - ax, by2 - ay
            seg = math.hypot(dx, dy) or 1.0
            t = max(0.0, min(1.0, ((bx - ax) * dx + (by - ay) * dy) / (seg * seg)))
            cx, cy = ax + dx * t, ay + dy * t
            d = math.hypot(bx - cx, by - cy)
            if best is None or d < best[0]:
                best = (d, cx, cy, math.atan2(dy, dx))
    if best is None:
        return None
    d, ex, ey, angle = best
    out = math.hypot(ex - bx, ey - by) or 1.0
    return (ex + math.cos(angle) * 3.0, ey + math.sin(angle) * 3.0, PLINTH_HEIGHT, angle)


def build_ground(mat) -> None:
    half = GROUND_SIZE / 2.0
    verts = [(-half, -half, 0.0), (half, -half, 0.0), (half, half, 0.0), (-half, half, 0.0)]
    obj = add_mesh_object("GROUND", verts, [(0, 1, 2, 3)], [mat])
    obj["bid"] = "GROUND"


def road_ribbon(points: list[tuple[float, float]], width: float) -> tuple[list, list]:
    verts, faces = [], []
    for i in range(len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        dx, dy = x1 - x0, y1 - y0
        seg = math.hypot(dx, dy)
        if seg < 1e-3:
            continue
        nx, ny = -dy / seg * width / 2.0, dx / seg * width / 2.0
        base = len(verts)
        verts += [
            (x0 + nx, y0 + ny, ROAD_Z),
            (x0 - nx, y0 - ny, ROAD_Z),
            (x1 - nx, y1 - ny, ROAD_Z),
            (x1 + nx, y1 + ny, ROAD_Z),
        ]
        faces.append((base, base + 1, base + 2, base + 3))
    return verts, faces


def build_roads(features: list, lat0: float, lon0: float, south: float, north: float,
                west: float, east: float, mat) -> int:
    margin = 0.0015  # ~150 m, matches the nav graph buffer
    verts, faces = [], []
    count = 0
    for f in features:
        p = f.get("properties") or {}
        if p.get("layer") not in ("road", "footpath"):
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        coords = geom.get("coordinates") or []
        if not coords:
            continue
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        if max(lats) < south - margin or min(lats) > north + margin:
            continue
        if max(lons) < west - margin or min(lons) > east + margin:
            continue
        pts = ring_metres(coords, lat0, lon0)
        if len(pts) < 2:
            continue
        width = ROAD_WIDTHS.get(p.get("highway") or "", 3.0)
        v, fc = road_ribbon(pts, width)
        offset = len(verts)
        verts += v
        faces += [tuple(i + offset for i in face) for face in fc]
        count += 1
    if faces:
        obj = add_mesh_object("ROAD_ALL", verts, faces, [mat])
        obj["bid"] = "ROAD_ALL"
    return count


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)

    bbox = json.load(open(os.path.join(ROOT, "data-src", "campus_bbox.json")))
    south, north, west, east = (float(x) for x in bbox["boundingbox"][:4])
    lat0, lon0 = (south + north) / 2.0, (west + east) / 2.0

    facade = {}
    with open(os.path.join(ROOT, "data-src", "facade_sheet.csv"), newline="") as f:
        for row in csv.DictReader(f):
            facade[row["id"]] = row

    geojson = json.load(open(os.path.join(ROOT, "data-src", "osm_campus.geojson")))
    by_way = {}
    for feature in geojson.get("features", []):
        props = feature.get("properties") or {}
        if props.get("layer") == "building":
            by_way[str(props.get("osm_id"))] = feature

    wall_mat = material("MAT_wall", "#c9c2b4")
    add_window_mask(
        wall_mat,
        (srgb_to_linear(0.79), srgb_to_linear(0.76), srgb_to_linear(0.71), 1.0),
        (srgb_to_linear(0.83), srgb_to_linear(0.87), srgb_to_linear(0.92), 1.0),
    )
    roof_mat = material("MAT_roof", "#8a8578")
    ground_mat = material("MAT_ground", "#8f9d7a", roughness=1.0)
    road_mat = material("MAT_road", "#7d7d78", roughness=1.0)

    build_ground(ground_mat)

    built = 0
    for bid, row in sorted(facade.items()):
        feature = by_way.get(str(row.get("osm_way")))
        if not feature:
            print(f"WARN: no geometry for {bid}")
            continue
        geom = feature.get("geometry") or {}
        if geom.get("type") != "Polygon":
            print(f"WARN: {bid} is not a polygon")
            continue
        ring = ring_metres(geom["coordinates"][0], lat0, lon0)
        build_building(bid, ring, int(row.get("floors") or 1), wall_mat, roof_mat)
        built += 1
        ent = nearest_road_point((ring[0][0], ring[0][1], 0.0), geojson.get("features", []), lat0, lon0, south, north, west, east)
        if ent is not None:
            add_entrance(f"ENTR_{bid[len('BLDG_'):]}", (ent[0], ent[1], ent[2]), ground_mat)

    roads = build_roads(geojson.get("features", []), lat0, lon0, south, north, west, east, road_mat)

    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "build", "campus.blend"))
    print(f"BLEND_OK buildings={built} roads={roads} -> build/campus.blend")


if __name__ == "__main__":
    main()
