# Metashape MCP Server

## Overview

MCP server for Agisoft Metashape Professional 2.3+ that runs embedded inside Metashape's Python 3.12 environment. Exposes the complete photogrammetry pipeline as 106 MCP tools, 10 resources, and 6 prompts over Streamable HTTP transport.

## Architecture

```
src/metashape_mcp/
├── server.py           # FastMCP entry point, HTTP transport (auto-port)
├── multiplexer.py      # Stdio MCP proxy — multi-instance routing
├── proxy.py            # Simple single-instance stdio proxy (legacy)
├── discovery.py        # Instance discovery file management
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

## Agent Usage Rules

- **NEVER write pipeline scripts.** This is an MCP server for AI agents. Call each tool individually, check the result, reason about it, then call the next tool. NEVER batch MCP calls into a Python script — that defeats the entire purpose of agent-driven tool calling.
- **Prefer MCP tools over `execute_python`.** Only use `execute_python` when there is no MCP tool for the operation (e.g. switching active model by key, texture transfer with `source_asset`). For everything else — decimation, UV mapping, texture building from images, export, alignment, etc. — use the dedicated MCP tools. They handle progress, errors, and timeouts better than raw Python.
- **ALWAYS `keep_keypoints=True`** when calling `match_photos`. This is the default in our tool (overriding Metashape's False default). Without it, incremental batch alignment fails.
- **USGS tie point filtering**: RU=10, PA=3, RE=0.3. NEVER remove more than 50% of tie points in one pass — the tool auto-raises the threshold if >50% would be selected.
- **No timeouts.** MCP tool calls block until the Metashape operation completes. Operations can take hours or days.

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

## Lessons Learned / Gotchas

- **`buildTexture` with `transfer_texture=True` requires `MosaicBlending`**: In Metashape 2.3.0, using the default `NaturalBlending` when baking from a source model (`source_data=ModelData`, `source_asset=key`, `transfer_texture=True`) causes assertion error `413929059` at line 388. Always use `blending_mode=Metashape.BlendingMode.MosaicBlending` for model-to-model texture transfers.
- **`decimate_model` creates a new model**: The MCP `decimate_model` tool (and Metashape's internal decimation) creates a new model rather than modifying the original in place. Do NOT duplicate the model before decimating — you'll end up with an unnecessary full-size copy wasting RAM.
- **Avoid `model.statistics()` on large models via MCP**: Calling `statistics()` on 10M+ poly models through `execute_python` can cause Metashape to lock up or timeout. Skip stats calls on large models — use lightweight checks (label, key, has_uv) instead.
- **UV builds on 500K-face models take ~3 minutes**: `buildUV` with generic mapping, 2 pages, 4096 on a 500K-face model takes approximately 3 minutes. The MCP proxy will likely timeout, but the operation continues in Metashape. Check `get_processing_status` after timeout to confirm completion.
- **Always set `doc.chunk = chunk` before processing**: Some operations (especially `buildTexture` with `source_asset`) require the chunk to be set as active on the document, not just `chunk.model` being set.
- **Texture page datatype mismatches after merge**: Merging models can create textures with heterogeneous page datatypes (some U16/4ch, some U8/3ch). `buildTexture` with `transfer_texture` fails with "Texture and page data types mismatch". Fix by iterating all pages via `tex.image(page_index)` and converting each to consistent U8/RGB: `img.convert("RGB", datatype="U8")` then `tex.setImage(fixed_img, page_index)` (positional args only — keyword args don't work on C++ bindings).
- **`tex.setImage()` uses positional args only**: `tex.setImage(img, page=1)` fails — Metashape C++ bindings don't accept keyword args. Use `tex.setImage(img, 1)`.
- **Check ALL texture pages, not just page 0**: `tex.image()` returns page 0. A texture may have 10+ pages — iterate `tex.image(i)` for `i in range(page_count)` to inspect/fix all of them.

## Workflow: PBR Multi-LOD Export

Creates medium and low quality versions of PBR model sets (diffuse/rough/metal) with matching UVs, bakes textures from originals, and exports in the standard PBR pattern.

### Prerequisites
- A chunk with 3 textured models sharing the same mesh: `{prefix}-diffuse`, `{prefix}-rough`, `{prefix}-metal`
- Example: `high-diffuse`, `high-rough`, `high-metal`

### Steps

**1. Decimate** — Set the diffuse model active, use `decimate_model` to target face count. This creates a new model. Rename it via `execute_python`: `chunk.model.label = "medium-diffuse"`

**2. Build UV** — Use `build_uv` (MCP tool) on the decimated model. **WARNING: UV unwrap takes several minutes (3+ min for 500K+ faces). The MCP proxy will likely timeout. After timeout, poll `get_processing_status` until idle before continuing.**
- Medium: 2 pages × 4096
- Low: 1 page × 4096

**3. Copy mesh** — Use `execute_python` to copy the diffuse model (with UV) for rough and metal variants. This guarantees identical UV layouts:
```python
med_diff = next(m for m in chunk.models if m.label == "medium-diffuse")
med_rough = med_diff.copy()
med_rough.label = "medium-rough"
med_metal = med_diff.copy()
med_metal.label = "medium-metal"
```

**4. Bake textures** — Use `execute_python` with `buildTexture`. Must use `MosaicBlending`:
```python
doc = Metashape.app.document
doc.chunk = chunk
chunk.model = target_model
chunk.buildTexture(
    blending_mode=Metashape.BlendingMode.MosaicBlending,
    texture_size=4096,
    fill_holes=False,
    anti_aliasing=1,
    source_asset=source_model.key,
    transfer_texture=True,
    source_data=Metashape.DataSource.ModelData,
)
```
Bake each pair: high-diffuse→medium-diffuse, high-rough→medium-rough, high-metal→medium-metal.

**5. Repeat steps 1-4** for low quality level.

**6. Export** — For each quality level:
- **diffuse**: `exportModel` as OBJ with JPG texture → `{name}_{quality}.obj` + `.mtl` + `.jpg`
- **rough**: export as OBJ, then delete `.obj` and `.mtl`, keep only `.jpg` → `{name}_{quality}_roughness.jpg`
- **metal**: same as rough → `{name}_{quality}_metalness.jpg`

### Notes
- Multi-page textures (e.g. `_high1.jpg`) are normal for higher quality levels
- Never call `model.statistics()` on large models — causes lockups
- Always set `doc.chunk = chunk` before `buildTexture` with `source_asset`

## Multi-Instance Support

Multiple Metashape instances can run simultaneously, each with its own MCP server.

### How it works

```
Claude Code/Desktop --stdio--> Multiplexer --HTTP--> Metashape A (:8765)
                                           --HTTP--> Metashape B (:8766)
                                           --HTTP--> Metashape C (:8767)
```

- **Auto-port**: Each instance auto-assigns a port from range 8765-8784 (override via `METASHAPE_MCP_PORT` env var)
- **Discovery files**: Each instance writes `%LOCALAPPDATA%/metashape-mcp/instances/{port}.json` on startup, cleaned up per-instance on exit. Stale files (from crashes) are auto-cleaned by TCP health checks.
- **Multiplexer proxy** (`multiplexer.py`): Stdio MCP server that discovers instances and forwards tool calls. Adds 2 tools:
  - `list_instances` — shows all running instances (port, PID, project, active status)
  - `switch_instance(port)` — routes all subsequent tool calls to that instance
- Auto-connects to first available instance on startup

### Client configuration

```json
{
  "mcpServers": {
    "metashape": {
      "command": "python",
      "args": ["X:/tools/mcps/metashape-mcp/src/metashape_mcp/multiplexer.py"]
    }
  }
}
```

### Key files
- `discovery.py` — Port scanning, discovery file I/O, stale cleanup
- `multiplexer.py` — Stdio MCP server using `mcp.server.lowlevel.Server` + `httpx` for HTTP forwarding
- `proxy.py` — Simple single-instance proxy (legacy, supports `METASHAPE_MCP_PORT` env var)

## Dependencies

- `mcp[cli]>=1.2.0` - MCP Python SDK with FastMCP
- `fastmcp>=2.0.0` - FastMCP high-level wrapper
- `httpx>=0.27.0` - Async HTTP client (for multiplexer forwarding)
- `Metashape` - provided by Metashape Professional (not pip-installable)

## Running

```python
# Inside Metashape console (auto-starts via scripts/ folder):
from metashape_mcp.server import start_background
start_background()  # Starts HTTP server on auto-assigned port

# Or standalone:
# python -m metashape_mcp.server
```
