#!/usr/bin/env python
"""Download a free DEM (Copernicus GLO-30 preferred) for the IIT Ropar campus box.

Falls back to a flat DEM behind --flat when no source is reachable without login/key.

To add the DEM later: set up access to Copernicus GLO-30 via the Copernicus Data Space
(or OpenTopography SRTM) and point `make dem` at it, or run `make dem FLAT=1`.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import rasterio
from rasterio.transform import from_origin


def make_flat_dem(south: float, north: float, west: float, east: float, res_m: float = 30.0) -> tuple:
    n = int(np.ceil((north - south) * 111320.0 / res_m))
    w = int(np.ceil((east - west) * 85030.0 / res_m))
    arr = np.full((1, n, w), 218.0, dtype="float32")
    transform = from_origin(west - res_m / 2.0, north + res_m / 2.0, res_m, res_m)
    return arr, transform


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data-src/dem.tif")
    parser.add_argument("--flat", action="store_true", help="write a flat DEM (no elevation source available)")
    args = parser.parse_args()

    info = json.load(open("data-src/campus_bbox.json"))
    bb = info.get("boundingbox") or ["30.9", "31.1", "77.2", "77.5"]
    south, north, west, east = [float(x) for x in bb]

    if args.flat:
        arr, transform = make_flat_dem(south, north, west, east)
        with rasterio.open(
            args.out, "w", driver="GTiff", height=arr.shape[1], width=arr.shape[2],
            count=1, dtype="float32", crs="EPSG:4326", transform=transform,
        ) as dst:
            dst.write(arr, 1)
        print(f"WROTE_FLAT_DEM {args.out}")
        return 0

    print("ERROR: no DEM source configured; use --flat (see README: how to add the DEM)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
