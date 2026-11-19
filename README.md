#IIT Ropar Campus 3D

An interactive, low-poly 3D map of the IIT Ropar main campus in Rupnagar, Punjab. Search for a building, plan a walking route, take an orientation tour, and change the time of day to watch the sun move and the windows light up at night.

live demo : https://ankit7d67.github.io/iitrpr-campus-3d/

Features
3D campus view with orbit and touch controls (works on phones)
Search for buildings, hostels and departments
Walking routes over the campus road and footpath network
Orientation tour, sun by time of day (IST) and a night mode
Quality setting (Auto / Low / High) and shareable links
Run locally

Needs Node.js, npm and Python. Blender 4.2 is only needed to rebuild the model.

bash
npm install
make dev        # http://localhost:3000
Command	Purpose
make test / make e2e	Unit tests / browser tests
make build	Static export into out/
make verify	Budget check + tests + build
make assets	Rebuild model and data (needs Blender)
How it works
text
OpenStreetMap + Copernicus DEM + data-src/campus_extra.json
   -> Blender 4.2 (import_osm.py, bake.py)
   -> campus.glb, nav.json, scatter.json, campus.json
   -> Next.js static export -> GitHub Pages

Built with Python, Blender, Next.js, React, TypeScript, three.js / React Three Fiber, Vitest and Playwright. The committed .glb is compressed, so CI does not need Blender.

Known limitations

This is a prototype on open data, not an official map. Floor counts, colours, roof types and trees are guesses (marked verified=false, see TODO_VERIFY.md). OpenStreetMap coverage is incomplete (see OSM_AUDIT.md), and room details are empty for now.

Contributing

The best fix is better map data: edit the campus on openstreetmap.org with verified names and floors, then run make osm and make assets. Pull requests are welcome.


