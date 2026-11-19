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


def despeckle(arr: np.ndarray) -> np.ndarray:
    """5x5 median filter (edge-padded).

    Copernicus GLO-30 has raster-aligned artifacts on the campus: a 2-row-wide,
    full-tile-width band at rows 23-24 (+2..+7 m vs neighbourhood, 15% one-pixel
    edges) plus isolated +5 m pixels. A 5x5 median removes features only 1-2
    pixels (30-60 m) wide while leaving wider terrain intact, so road ribbons
    (0.1 m lift) are not swamped by one bad cell. Genuine undulation survives;
    logged in PLAN.md / TODO_VERIFY.md as a processed-data note.
    """
    rows, cols = arr.shape
    p = np.pad(arr, 2, mode="edge")
    stack = np.stack([p[i:i + rows, j:j + cols] for i in range(5) for j in range(5)])
    return np.median(stack, axis=0)


def main() -> int:
    with rasterio.open(DEM) as src:
        arr = src.read(1).astype("float64")
        b = src.bounds
    raw_max_dev = float(np.max(np.abs(arr - despeckle(arr))))
    arr = despeckle(arr)
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
          f"min={arr.min():.2f} max={arr.max():.2f} despeckled_max_dev={raw_max_dev:.2f} "
          f"-> build/dem_grid.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
