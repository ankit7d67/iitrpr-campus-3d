PYTHON ?= python
NODE ?= node
NPM ?= npm
BLENDER ?= C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
BLENDER_BIN ?= $(BLENDER)
FLAT ?=

SRC := data-src
BL_DIR := blender
PUB := public
MODEL := $(PUB)/models/campus.glb
NAV := $(PUB)/data/nav.json
SCAT := $(PUB)/data/scatter.json
CAMPUS := $(PUB)/data/campus.json
OSM := $(SRC)/osm_campus.geojson
BBOX := $(SRC)/campus_bbox.json
DEM := $(SRC)/dem.tif

.DEFAULT_GOAL := help

.PHONY: help all dev phone osm audit dem dem-grid clip-roads blend assets check test e2e build preview verify clean

help:
	@echo "Targets: dev, phone, osm, audit, dem, blend, assets, check, test, e2e, build, preview, verify, clean"

dev:
	$(NPM) run dev

phone:
	$(NPM) run dev

# Full Phase 2 pipeline: fetch OSM, write the audit, then regenerate the facade
# sheet and campus.json from buildings that fall inside the campus boundary.
osm: $(SRC)/scripts/fetch_osm.py scripts/osm_audit.py scripts/facade_table.py
	$(PYTHON) $(SRC)/scripts/fetch_osm.py --bbox-out $(BBOX) --out $(OSM)
	$(PYTHON) scripts/osm_audit.py
	$(PYTHON) scripts/facade_table.py

audit: scripts/osm_audit.py
	$(PYTHON) scripts/osm_audit.py

dem: $(SRC)/scripts/fetch_dem.py
	$(PYTHON) $(SRC)/scripts/fetch_dem.py --out $(DEM) $(if $(FLAT),--flat)
	$(PYTHON) scripts/dem_grid.py

# build/dem_grid.json is regenerated when data-src/dem.tif exists; import_osm.py falls
# back to a flat ground if it is missing (so CI/verify never needs the DEM).
dem-grid:
	-$(PYTHON) scripts/dem_grid.py

# build/roads_clip.geojson = roads/footpaths clipped to the campus polygon + 100 m
# (needs shapely in the system Python; import_osm.py falls back to unclipped if missing).
clip-roads:
	-$(PYTHON) scripts/clip_roads.py

blend: $(BL_DIR)/scripts/import_osm.py dem-grid clip-roads
	$(PYTHON) -c "import os; os.makedirs('build', exist_ok=True)"
	"$(BLENDER_BIN)" -b -P $(BL_DIR)/scripts/import_osm.py

assets: blend
	"$(BLENDER_BIN)" -b build/campus.blend -P $(BL_DIR)/scripts/bake.py -- --out build/raw_campus.glb
	$(NODE) scripts/compress_glb.mjs
	$(PYTHON) scripts/build_nav.py
	$(NODE) scripts/manifest.mjs

check:
	$(PYTHON) scripts/check_budget.py --campus $(CAMPUS) --nav $(NAV) --model $(MODEL) --scatter $(SCAT) --tris-in-view 150000 --max-model-mb 5 --max-materials 4 --max-textures 2 --require-meshopt --require-webp-textures

test:
	$(NPM) run test

e2e:
	$(NPM) run e2e

build:
	$(NPM) run build

preview: blend
	"$(BLENDER_BIN)" -b build/campus.blend -P $(BL_DIR)/scripts/render_preview.py

verify: check test build
	@echo "ALL GREEN"

clean:
	rm -rf build .next out node_modules
