# AGENTS.md — iitrpr-campus-3d

## RULES

- Everything must be reproducible via make targets. Never hand-edit generated files (nav.json, scatter.json, .glb).
- Never invent campus facts (room numbers, hours, official names, photos). Unknown = empty or TODO.
- Every guessed value (floors, colours, heights, roof types) must have verified=false and be listed in README under "Values to verify" and in TODO_VERIFY.md.
- Respect source licences and terms of service. Do not scrape imagery or data from sources that forbid it.
- Keep OpenStreetMap attribution and the reference-project credit in NOTICE.
- Budgets enforced by `make check`: <=150,000 triangles in view, <=5 MB model, <=4 materials, <=2 textures, IDs identical across the GLB, campus.json and nav.json, and tours/landmarks referencing only real campus buildings.
- Work in phases. After each phase: run its checks, fix failures, git commit with a clear message, update PLAN.md, print a 5-line status. Do not start the next phase until its checks pass.
- Prefer small working increments. If a step fails, diagnose and retry before asking me.

## MAKE COMMANDS

- `make dev` — start the Next.js dev server
- `make phone` — start the dev server with the mobile viewport / touch defaults
- `make osm` — download OSM data for the IIT Ropar campus into data-src/
- `make dem` — download + convert the campus DEM into data-src/dem.tif
- `make blend` — run the headless Blender build script
- `make assets` — bake/export campus.glb, nav.json, scatter.json
- `make check` — run all budget + consistency checks (<=150k tris in view, <=5 MB GLB, <=4 materials, <=2 textures, GLB/campus.json/nav.json ID parity, tour/landmark id + reference checks)
- `make test` — run Vitest unit tests
- `make e2e` — run Playwright tests
- `make build` — production static export
- `make preview` — render PNG previews of the Blender scene into build/preview/
- `make verify` — full verification suite; must end by printing "ALL GREEN"

## PHASE ORDER

1. Environment · 2. Map data · 3. Building table and data · 4. Blender model · 5. Web app · 6. Tests and deployment
