# Metashape MCP Server

## Overview

MCP server for Agisoft Metashape Professional 2.3+ that runs embedded inside Metashape's Python 3.12 environment. Exposes the complete photogrammetry pipeline as 64+ MCP tools, 10 resources, and 6 prompts over Streamable HTTP transport.

## Architecture

```
src/metashape_mcp/
├── server.py           # FastMCP entry point, HTTP transport
├── tools/              # 15 modules, 64+ tools total
│   ├── project.py      # open/save/create project, chunk management, GPU config
│   ├── photos.py       # add photos, analyze quality, import video
│   ├── camera.py       # enable/disable cameras, sensor config, masks
│   ├── alignment.py    # match photos, align/optimize cameras, filter tie points
│   ├── dense.py        # depth maps, point cloud, classification
│   ├── mesh.py         # build/decimate/smooth/clean/close holes/refine model
│   ├── texture.py      # UV mapping, texture, color calibration
│   ├── survey.py       # DEM, orthomosaic, tiled model, contours
│   ├── export.py       # export all product types
│   ├── import_data.py  # import models, point clouds, reference
│   ├── markers.py      # detect/add markers, scalebars, GCPs
│   ├── coordinate.py   # CRS, region, transform
│   ├── network.py      # network processing server interaction
│   ├── viewport.py     # viewport camera, screenshots
│   └── scripting.py    # arbitrary Python code execution (YOLO, batch, custom)
├── resources/          # 10 read-only state resources
├── prompts/            # workflow and troubleshooting templates
└── utils/
    ├── bridge.py       # Safe Metashape API access with error messages
    ├── enums.py        # String-to-Metashape enum mapping
    └── progress.py     # Async progress callback adapter
```

## Key Patterns

- **Module registration**: Each module has `register(mcp)` that decorates tools/resources/prompts
- **Bridge access**: Always use `get_document()`, `get_chunk()` from `utils.bridge` - never access `Metashape.app.document` directly
- **Enum mapping**: Use `resolve_enum(category, value)` for all Metashape enum parameters
- **Progress callbacks**: Use `make_progress_callback(ctx, "operation")` for long operations
- **Prerequisite checks**: Use `require_model()`, `require_point_cloud()`, etc. before operations
- **File size limit**: Keep each module under 200 lines

## Metashape API Notes

- `exportRaster()` handles both DEM and orthomosaic export (use `source_data` parameter)
- `classifyGroundPoints()` is on `chunk.point_cloud`, not on `chunk` directly
- All processing methods accept a `progress` callback: `Callable[[float], None]`
- Metashape API is NOT thread-safe - HTTP server runs in background thread
- Python 3.12 (Metashape 2.3 embedded) - can use modern syntax like `str | None`
- `cam.meta["key"]` uses bracket access, NOT `.get()` — MetaData is a C++ object
- `chunk.tie_points.points` can be None — always check before `len()`
- Metashape only reads DNG for camera raw — NOT NEF/CR2/ARW/etc.
- `PyStdout` lacks `isatty()` — must wrap with `_StdWrapper` for uvicorn
- GPU/CPU: Enable CPU only for alignment; disable for everything else

## Dependencies

- `mcp[cli]>=1.2.0` - MCP Python SDK with FastMCP
- `Metashape` - provided by Metashape Professional (not pip-installable)

## Running

```python
# Inside Metashape console:
from metashape_mcp.server import start_background
start_background()  # Starts HTTP server on port 8765

# Or standalone:
# python -m metashape_mcp.server
```
