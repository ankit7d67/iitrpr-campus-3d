PYTHON ?= python
NODE ?= node
NPM ?= npm
BLENDER ?= blender
BLENDER_BIN ?= blender
FLAT ?=

SRC := data-src
PUB := public
MODEL := $(PUB)/models/campus.glb
NAV := $(PUB)/data/nav.json
SCAT := $(PUB)/data/scatter.json
CAMPUS := $(PUB)/data/campus.json
OSM := $(SRC)/osm_campus.geojson
BBOX := $(SRC)/campus_bbox.json
DEM := $(SRC)/dem.tif

.DEFAULT_GOAL := help

.PHONY: help all dev phone osm dem blend assets check test e2e build preview verify clean

help:
	@echo "Targets: dev, phone, osm, dem, blend, assets, check, test, e2e, build, preview, verify, clean"

dev:
	$(NPM) run dev

phone:
	$(NPM) run dev

osm: $(SRC)/scripts/fetch_osm.py $(SRC)/scripts/facade_table.py
	$(PYTHON) $(SRC)/scripts/fetch_osm.py --bbox-file $(BBOX) --out $(OSM)

dem: $(SRC)/scripts/fetch_dem.py
	$(PYTHON) $(SRC)/scripts/fetch_dem.py --out $(DEM) $(if $(FLAT),--flat)

blend: $(BL_DIR)/scripts/import_osm.py $(BL_DIR)/scripts/bake.py
	$(BLENDER_BIN) -b -P $(BL_DIR)/scripts/import_osm.py

assets: blend $(BL_DIR)/scripts/bake.py
	$(BLENDER_BIN) -b -P $(BL_DIR)/scripts/bake.py --export-format glb

check:
	$(PYTHON) scripts/check_budget.py --campus $(CAMPUS) --nav $(NAV) --model $(MODEL) --scatter $(SCAT) --tris-in-view 150000 --max-model-mb 5 --max-materials 4 --max-textures 2

test:
	$(NPM) run test

e2e:
	$(NPM) run e2e

build:
	$(NPM) run build

preview: $(BL_DIR)/scripts/import_osm.py
	mkdir -p build/preview
	$(BLENDER_BIN) -b -P $(BL_DIR)/scripts/render_preview.py

verify: check test build
	@echo "ALL GREEN"

clean:
	rm -rf build .next out node_modules
