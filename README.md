# IIT Ropar Campus 3D

Interactive 3D web map of the Indian Institute of Technology Ropar (IIT Ropar), Rupnagar, Punjab, India.

> **Status:** unofficial student project. Not affiliated with IIT Ropar. The institute must be
> consulted before using its name or logo publicly.

## Live demo

TODO — will be published to GitHub Pages at
`https://<user>.github.io/iitrpr-campus-3d/` once Phase 6 deployment is complete.

## Quick start

```bash
make dev        # start Next.js dev server
make test       # unit tests (Vitest)
make build      # static production export
make preview    # render Blender scene previews into build/preview/
make verify     # full check: budget + tests + build ; ends with "ALL GREEN"
```

## Commands

| Target | Description |
| --- | --- |
| `make dev` | Next.js dev server |
| `make phone` | dev server with mobile defaults |
| `make osm` | download OSM data for the campus |
| `make dem` | download + convert DEM |
| `make blend` | headless Blender build script |
| `make assets` | bake + export campus.glb, nav.json, scatter.json |
| `make check` | budget checks (<=150k tris in view, <=5 MB model, <=4 materials, <=2 textures, ID parity) |
| `make test` | Vitest unit tests |
| `make e2e` | Playwright tests |
| `make build` | production static export |
| `make preview` | render PNG previews into `build/preview/` |
| `make verify` | full verification; ends with `ALL GREEN` |
| `make clean` | remove generated artefacts |

## Data pipeline

```
OpenStreetMap (Nominatim + Overpass)  ->  data-src/*.geojson, data-src/campus_bbox.json
Blender 4.2 headless (import_osm.py + bake.py)  ->  public/models/campus.glb (Meshopt + WebP)
        ->  public/data/nav.json, scatter.json, public/data/campus.json
Next.js static export (React Three Fiber)  ->  GitHub Pages
```

## Naming conventions

- Blender buildings: `BLDG_<ID>` with custom property `bid`.
- Ground: `GROUND`; roads: `ROAD_ALL`; props: `PROP_*`; graph: `NAV_graph`; entrances: `ENTR_<ID>`;
  trees/lamps: `SCAT_<type>_###`.

## Values to verify

See [TODO_VERIFY.md](./TODO_VERIFY.md). Every guessed value (floors, colours, heights, roof types)
must carry `verified=false` and be listed here. Also unverified: the OSM duplicate/part
footprints that are deliberately not extruded, and the campus boundary polygon (390 acres vs the
~501–525 acres stated by the institute).

## Licence / attribution

See [NOTICE.md](./NOTICE.md).
