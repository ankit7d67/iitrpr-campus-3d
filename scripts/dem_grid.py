"""Convert data-src/dem.tif into build/dem_grid.json for the Blender importer.

Blender's bundled Python has no rasterio, so the DEM is sampled here (regular Python)
and handed to import_osm.py as a plain JSON grid.
"""

import json
import os

import numpy as np
import rasterio

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEM = os.path.join(ROOT, "data-src", "dem.tif")
OUT = os.path.join(ROOT, "build", "dem_grid.json")


def main() -> int:
    with rasterio.open(DEM) as src:
        arr = src.read(1).astype("float64")
        b = src.bounds
        transform = src.transform
    n_rows, n_cols = arr.shape
    grid = {
        "west": float(b.left),
        "south": float(b.bottom),
        "east": float(b.right),
        "north": float(b.top),
        "cols": int(n_cols),
        "rows": int(n_rows),
        "mean": float(arr.mean()),
        "heights": [[float(v) for v in row] for row in arr],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(grid, f)
    print(f"DEM_GRID_OK rows={n_rows} cols={n_cols} mean={grid['mean']:.2f} "
          f"min={arr.min():.2f} max={arr.max():.2f} -> build/dem_grid.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
