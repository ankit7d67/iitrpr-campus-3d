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
GROUND_SEGS = 80  # ground grid subdivisions (terrain follows the DEM inside the bbox)
ROAD_Z = 0.06
ROAD_LIFT = 0.1    # road surface above the GROUND mesh surface (m)
ROAD_SEG_M = 10.0  # densify longer segments so ribbons follow the terrain mesh
KERB_H = 0.15   # kerb rise above the road surface (m)
KERB_W = 0.35   # kerb lip width (m)
KERB_HIGHWAYS = {"tertiary", "unclassified"}  # only real streets get kerbs
PAD_OFFSET = 1.5  # level-pad width around a building footprint (m)


def load_dem_grid() -> dict | None:
    """Load build/dem_grid.json (written by scripts/dem_grid.py) or None -> flat ground."""
    path = os.path.join(ROOT, "build", "dem_grid.json")
    if not os.path.exists(path):
        print("DEM: no build/dem_grid.json -> flat ground")
        return None
    try:
        with open(path) as f:
            grid = json.load(f)
        print(f"DEM: grid {grid['rows']}x{grid['cols']} mean={grid['mean']:.1f} m -> terrain on")
        return grid
    except Exception as exc:  # noqa: BLE001 - never fail the build over a missing DEM
        print(f"WARN: dem_grid unreadable ({exc}) -> flat ground")
        return None


def dem_sample(grid: dict | None, lat: float, lon: float) -> float:
    """Bilinear DEM height (m); clamps to the grid edge outside coverage."""
    if not grid:
        return 0.0
    west, south, east, north = grid["west"], grid["south"], grid["east"], grid["north"]
    cols, rows = grid["cols"], grid["rows"]
    fx = (lon - west) / (east - west) * (cols - 1)
    fy = (north - lat) / (north - south) * (rows - 1)
    fx = min(max(fx, 0.0), cols - 1.001)
    fy = min(max(fy, 0.0), rows - 1.001)
    x0, y0 = int(fx), int(fy)
    tx, ty = fx - x0, fy - y0
    h = grid["heights"]
    h00, h10 = h[y0][x0], h[y0][x0 + 1]
    h01, h11 = h[y0 + 1][x0], h[y0 + 1][x0 + 1]
    return (h00 * (1 - tx) * (1 - ty) + h10 * tx * (1 - ty)
            + h01 * (1 - tx) * ty + h11 * tx * ty)


def terrain_z(grid: dict | None, lat: float, lon: float) -> float:
    """Terrain height relative to the campus mean (so buildings keep their z=0 base)."""
    if not grid:
        return 0.0
    return dem_sample(grid, lat, lon) - grid["mean"]


def terrain_z_xy(grid: dict | None, x: float, y: float, lat0: float, lon0: float) -> float:
    if not grid:
        return 0.0
    m_lat, m_lon = local_scale(lat0)
    return terrain_z(grid, lat0 + y / m_lat, lon0 + x / m_lon)


def ground_surface_z(grid: dict | None, x: float, y: float, lat0: float, lon0: float) -> float:
    """Height of the GROUND mesh surface itself at (x, y).

    build_ground writes explicit triangles split along the cell diagonal
    (a, a+1, a+row+1) / (a, a+row+1, a+row) with terrain_z_xy() at each node, so
    road/kerb vertices interpolate those SAME triangle planes. Sampling the raw
    DEM (or a bilinear approximation) put roads on a different surface than the
    ground and they intermittently sank below it (dashed look).
    """
    if not grid:
        return 0.0
    half = GROUND_SIZE / 2.0
    segs = GROUND_SEGS
    cell = GROUND_SIZE / segs
    fx = (x + half) / cell
    fy = (y + half) / cell
    i = min(max(int(fx), 0), segs - 1)
    j = min(max(int(fy), 0), segs - 1)
    tx = min(max(fx - i, 0.0), 1.0)
    ty = min(max(fy - j, 0.0), 1.0)
    x0, y0 = -half + i * cell, -half + j * cell
    x1, y1 = x0 + cell, y0 + cell
    h00 = terrain_z_xy(grid, x0, y0, lat0, lon0)
    h10 = terrain_z_xy(grid, x1, y0, lat0, lon0)
    h01 = terrain_z_xy(grid, x0, y1, lat0, lon0)
    h11 = terrain_z_xy(grid, x1, y1, lat0, lon0)
    if ty <= tx:  # lower-right triangle (h00, h10, h11)
        return (1.0 - tx) * h00 + (tx - ty) * h10 + ty * h11
    # upper-left triangle (h00, h11, h01)
    return (1.0 - ty) * h00 + tx * h11 + (ty - tx) * h01


def densify(points: list[tuple[float, float]], max_len: float = ROAD_SEG_M) -> list:
    """Insert vertices so no segment is longer than max_len (terrain following)."""
    if len(points) < 2:
        return points
    out = [points[0]]
    for pt in points[1:]:
        x0, y0 = out[-1]
        x1, y1 = pt
        d = math.hypot(x1 - x0, y1 - y0)
        if d > max_len:
            n = int(d / max_len)
            for k in range(1, n + 1):
                t = k * max_len / d
                if t < 1.0:
                    out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        out.append(pt)
    return out


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


def offset_ring(ring: list[tuple[float, float]], dist: float) -> list[tuple[float, float]]:
    """Outward offset of a CCW ring along vertex bisectors (mitre, length-clamped)."""
    n = len(ring)

    def edge_normal(p0, p1):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return (0.0, 0.0)
        return (dy / length, -dx / length)  # right of travel = outward for CCW

    out = []
    for i in range(n):
        prev_p, cur, nxt = ring[i - 1], ring[i], ring[(i + 1) % n]
        n1 = edge_normal(prev_p, cur)
        n2 = edge_normal(cur, nxt)
        denom = max(1.0 + n1[0] * n2[0] + n1[1] * n2[1], 0.1)  # mitre, clamp spikes
        dx = (n1[0] + n2[0]) / denom * dist
        dy = (n1[1] + n2[1]) / denom * dist
        m = math.hypot(dx, dy)
        if m > dist * 3.0:  # bevel very sharp corners instead of spiking
            dx, dy = dx / m * dist * 3.0, dy / m * dist * 3.0
        out.append((cur[0] + dx, cur[1] + dy))
    return out


def build_building(bid: str, ring: list[tuple[float, float]], floors: int, wall_mat, roof_mat,
                   base_z: float = 0.0, ground_z=None) -> None:
    """Extrude a building and, when ground_z is given, sit it on a level pad:
    base_z becomes the highest terrain under the footprint (nothing is buried),
    a PAD_OFFSET-wide pad annulus closes the ring to grade, and retaining walls
    drop (or rise, on the uphill side) from the pad edge to the ground surface.
    All ground contact uses the same surface the GROUND mesh is made of.
    """
    if len(ring) < 3:
        return
    if signed_area(ring) < 0:
        ring = list(reversed(ring))
    if ground_z is not None:
        gz_ring = [ground_z(x, y) for x, y in ring]
        base_z = max(gz_ring)  # level pad = highest ground under the footprint
    else:
        gz_ring = None
    height = PLINTH_HEIGHT + max(1, floors) * FLOOR_HEIGHT
    n = len(ring)
    verts = [(x, y, base_z) for x, y in ring] + [(x, y, base_z + height) for x, y in ring]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    faces.append(tuple(range(n, 2 * n)))  # flat roof
    # Walls use material 0, the roof face uses material 1.
    face_mats = [0] * (len(faces) - 1) + [1]
    if ground_z is not None:
        pad = offset_ring(ring, PAD_OFFSET)
        gz_pad = [ground_z(x, y) for x, y in pad]
        top_off = 2 * n   # pad edge verts (z = base_z)
        bot_off = 3 * n   # retaining-wall feet (z = terrain at the pad edge)
        verts += [(x, y, base_z) for x, y in pad]
        verts += [(x, y, gz_pad[i]) for i, (x, y) in enumerate(pad)]
        for i in range(n):
            j = (i + 1) % n
            # Pad top: quad between footprint ring and pad edge, normal +z.
            faces.append((i, top_off + i, top_off + j, j))
            face_mats.append(0)
            # Retaining wall at the pad edge; order by which end is higher so the
            # face normal points away from the building on both cut and fill sides.
            if (gz_pad[i] + gz_pad[j]) * 0.5 <= base_z:
                faces.append((top_off + i, bot_off + i, bot_off + j, top_off + j))
            else:
                faces.append((bot_off + i, top_off + i, top_off + j, bot_off + j))
            face_mats.append(0)
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


def build_ground(mat, grid: dict | None, lat0: float, lon0: float) -> None:
    """Subdivided ground plane that follows the DEM inside the campus bbox (clamped flat
    outside it). Without a DEM this degrades to the old flat quad."""
    half = GROUND_SIZE / 2.0
    if not grid:
        verts = [(-half, -half, 0.0), (half, -half, 0.0), (half, half, 0.0), (-half, half, 0.0)]
        obj = add_mesh_object("GROUND", verts, [(0, 1, 2, 3)], [mat])
        obj["bid"] = "GROUND"
        return
    segs = GROUND_SEGS
    verts = []
    for j in range(segs + 1):
        y = -half + GROUND_SIZE * j / segs
        for i in range(segs + 1):
            x = -half + GROUND_SIZE * i / segs
            verts.append((x, y, terrain_z_xy(grid, x, y, lat0, lon0)))
    faces = []
    row = segs + 1
    for j in range(segs):
        for i in range(segs):
            a = j * row + i
            # Explicit triangles with the diagonal ground_surface_z() interpolates over,
            # so the exported mesh has no re-tessellation ambiguity.
            faces.append((a, a + 1, a + row + 1))
            faces.append((a, a + row + 1, a + row))
    obj = add_mesh_object("GROUND", verts, faces, [mat])
    obj["bid"] = "GROUND"


def road_ribbon(points: list[tuple[float, float]], width: float, z_of=None,
                kerb: bool = False) -> tuple[list, list]:
    """Road ribbon quads; with kerb=True also builds a raised kerb (0.15 m face + 0.35 m lip)
    along both edges, reusing the road material (no new material, no textures)."""
    verts, faces = [], []
    for i in range(len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        dx, dy = x1 - x0, y1 - y0
        seg = math.hypot(dx, dy)
        if seg < 1e-3:
            continue
        ux, uy = -dy / seg, dx / seg  # unit left normal
        hl = width / 2.0
        lx0, ly0 = x0 + ux * hl, y0 + uy * hl
        rx0, ry0 = x0 - ux * hl, y0 - uy * hl
        lx1, ly1 = x1 + ux * hl, y1 + uy * hl
        rx1, ry1 = x1 - ux * hl, y1 - uy * hl
        if z_of is None:
            zl0 = zr0 = zl1 = zr1 = ROAD_Z
        else:
            zl0, zr0 = z_of(lx0, ly0), z_of(rx0, ry0)
            zl1, zr1 = z_of(lx1, ly1), z_of(rx1, ry1)
        base = len(verts)
        verts += [
            (lx0, ly0, zl0),
            (rx0, ry0, zr0),
            (rx1, ry1, zr1),
            (lx1, ly1, zl1),
        ]
        faces.append((base, base + 1, base + 2, base + 3))
        if not kerb:
            continue
        for s in (1, -1):  # +1 left edge, -1 right edge
            zb0 = zl0 if s > 0 else zr0
            zb1 = zl1 if s > 0 else zr1
            ex0, ey0 = x0 + ux * hl * s, y0 + uy * hl * s
            ex1, ey1 = x1 + ux * hl * s, y1 + uy * hl * s
            ox0, oy0 = ex0 + ux * KERB_W * s, ey0 + uy * KERB_W * s
            ox1, oy1 = ex1 + ux * KERB_W * s, ey1 + uy * KERB_W * s
            zt0, zt1 = zb0 + KERB_H, zb1 + KERB_H
            b = len(verts)
            verts += [
                (ex0, ey0, zb0), (ex1, ey1, zb1),      # bottom edge
                (ex0, ey0, zt0), (ex1, ey1, zt1),      # top edge
                (ox0, oy0, zt0), (ox1, oy1, zt1),      # outer top
            ]
            if s > 0:
                faces.append((b, b + 2, b + 3, b + 1))  # vertical face, normal +n
                faces.append((b + 2, b + 3, b + 5, b + 4))  # lip, normal +z
            else:
                faces.append((b, b + 1, b + 3, b + 2))  # vertical face, normal -n
                faces.append((b + 2, b + 4, b + 5, b + 3))  # lip, normal +z
    return verts, faces


def build_roads(features: list, lat0: float, lon0: float, south: float, north: float,
                west: float, east: float, mat, grid: dict | None = None) -> int:
    margin = 0.0015  # ~150 m, matches the nav graph buffer
    # Prefer the shapely-clipped source (campus polygon + 100 m, scripts/clip_roads.py);
    # fall back to the raw bbox selection only if it is missing.
    clip_path = os.path.join(ROOT, "build", "roads_clip.geojson")
    if os.path.exists(clip_path):
        with open(clip_path) as f:
            features = json.load(f).get("features", [])
        print(f"ROADS: clipped source build/roads_clip.geojson ({len(features)} ways)")
    else:
        print("WARN: build/roads_clip.geojson missing -> unclipped bbox roads")
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
        pts = densify(pts)  # follow the terrain mesh between its grid cells
        width = ROAD_WIDTHS.get(p.get("highway") or "", 3.0)
        kerb = (p.get("highway") or "") in KERB_HIGHWAYS

        def z_of(x, y, _lat0=lat0, _lon0=lon0, _grid=grid):
            # Same surface as the GROUND mesh + a small constant lift (no z-fighting).
            return ground_surface_z(_grid, x, y, _lat0, _lon0) + ROAD_LIFT

        v, fc = road_ribbon(pts, width, z_of, kerb=kerb)
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
    roof_mat = material("MAT_roof", "#8a8578")
    ground_mat = material("MAT_ground", "#8f9d7a", roughness=1.0)
    road_mat = material("MAT_road", "#7d7d78", roughness=1.0)

    grid = load_dem_grid()
    build_ground(ground_mat, grid, lat0, lon0)

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
        ring_ll = geom["coordinates"][0]
        ring = ring_metres(ring_ll, lat0, lon0)
        # Level pad + retaining walls: base sits on the highest ground under the
        # footprint (same surface the GROUND mesh uses), so nothing floats or sinks.
        gz_fn = (lambda x, y, _g=grid, _la=lat0, _lo=lon0:
                 ground_surface_z(_g, x, y, _la, _lo))
        build_building(bid, ring, int(row.get("floors") or 1), wall_mat, roof_mat,
                       ground_z=gz_fn)
        built += 1
        ent = nearest_road_point((ring[0][0], ring[0][1], 0.0), geojson.get("features", []), lat0, lon0, south, north, west, east)
        if ent is not None:
            ent_z = ground_surface_z(grid, ent[0], ent[1], lat0, lon0) + PLINTH_HEIGHT
            add_entrance(f"ENTR_{bid[len('BLDG_'):]}", (ent[0], ent[1], ent_z), ground_mat)

    roads = build_roads(geojson.get("features", []), lat0, lon0, south, north, west, east, road_mat, grid)

    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "build", "campus.blend"))
    print(f"BLEND_OK buildings={built} roads={roads} -> build/campus.blend")


if __name__ == "__main__":
    main()
