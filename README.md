# IIT Ropar Campus 3D

A low-poly 3D map of IIT Ropar's main campus in Rupnagar, Punjab. You can look
around the campus, search for a building, plan a walking route, and take a short
orientation tour. The model is built from OpenStreetMap data and a small amount
of hand-added overlay data.

> This is an unofficial student project. It is not affiliated with IIT Ropar.
> Please talk to the institute before using its name or logo anywhere public.

## Live demo

The site is hosted at <https://ankit7d67.github.io/iitrpr-campus-3d/>.

## Running it locally

You need Node.js, npm and Python. Blender 4.2 is only needed if you want to
rebuild the 3D model from source.

```bash
npm install
make dev
```

The dev server runs at <http://localhost:3000>. A few other useful commands:

```bash
make test       # unit tests
make e2e        # browser tests (install Playwright browsers first)
make build      # static export into out/
make verify     # budget check + unit tests + build
make preview    # re-render the Blender preview images
```

If you change the map data or the Blender script, run `make assets` to rebuild
the compressed model, navigation graph and generated data files.

## Asset URLs on GitHub Pages

GitHub Pages serves project sites under a path, so the build needs to know the
repository name:

- `NEXT_PUBLIC_BASE_PATH=/iitrpr-campus-3d` prefixes asset URLs and Next.js's
  own base path.
- `NEXT_PUBLIC_SITE_URL=https://ankit7d67.github.io` gives share links an
  absolute URL.

The GitHub Actions workflow in `.github/workflows/deploy.yml` sets both of
these. Generated file URLs also carry a short content hash (`?v=...`) so a
rebuild only busts the browser cache for files that actually changed.

## How the data is made

```
OpenStreetMap (Nominatim + Overpass)  ->  data-src/*.geojson
+ hand overlay data-src/campus_extra.json  ->  overrides, tours, landmarks
Blender 4.2 (import_osm.py + bake.py)  ->  public/models/campus.glb
                                      ->  nav.json, scatter.json, campus.json
Next.js static export  ->  GitHub Pages
```

The committed GLB is compressed with Meshopt and WebP. Keeping it compressed in
the repo means CI does not need Blender; `make assets` is only for regenerating
it locally.

Object names in the model follow a simple convention:

- `BLDG_<ID>` for buildings (with the OSM id in a `bid` custom property)
- `ENTR_<ID>` for entrance points used by routing
- `GROUND`, `ROAD_ALL`, `PROP_*`, `NAV_graph`, `SCAT_<type>_###` for everything else

## Things that still need checking

Some details are guesses rather than surveyed facts. They are marked
`verified=false` in the data and collected in [TODO_VERIFY.md](./TODO_VERIFY.md).
This includes floor counts, wall colours, roof types, the campus boundary area,
the decorative trees and lamps, and the fixed-sun baked shadow/window texture.
Nothing in those files should be treated as an official campus map.


