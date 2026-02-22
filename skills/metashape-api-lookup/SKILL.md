---
name: metashape-api-lookup
description: Look up Metashape Python API parameters and enums from local reference files when building or fixing MCP tools. Use when you need to verify parameter names, types, defaults, or enum values for Metashape API calls.
user-invocable: false
---

# Metashape API Lookup

When working on metashape-mcp tools, always verify API parameters against the local reference files rather than guessing.

## Reference Files

The project contains these Metashape API references:

| File | Contents | When to Use |
|------|----------|-------------|
| `api_reference.txt` | Full Python API reference (text, searchable) | Primary reference for parameter names, types, defaults |
| `metashape_python_api_2_3_0.pdf` | Official PDF API docs | Backup if text version is unclear |
| `metashape-pro_2_3_en.pdf` | Metashape Pro user manual | For understanding workflow context and UI equivalents |
| `usgs_ofr20211039.pdf` | USGS photogrammetry best practices | For filtering thresholds and workflow order |

## Lookup Procedure

When implementing or modifying an MCP tool:

1. **Search `api_reference.txt` first** — Use Grep to find the exact method signature:
   ```
   Grep for: "chunk.buildModel" or "buildModel" or "Chunk.buildModel"
   ```

2. **Check parameter types** — Metashape uses its own enum types. Verify which enum a parameter expects:
   ```
   Grep for: "SurfaceType" or "DataSource" or the specific enum class
   ```

3. **Check `utils/enums.py`** — See if the string-to-enum mapping already exists. If not, add it.

4. **Verify defaults** — The MCP tool defaults should match best-practice defaults, which may differ from Metashape API defaults. Example:
   - `keep_keypoints`: Metashape default=False, MCP default=True (required for incremental alignment)
   - `blending_mode`: Use "natural" for best quality, not necessarily the API default

## Common Gotchas

These are verified facts from the API reference — do NOT guess these:

| Topic | Correct Answer |
|-------|---------------|
| `alignChunks` method param | Plain `int` (0=tiepoints, 1=markers, 2=cameras), NOT an enum |
| `RasterFormatTiles` | IS the correct enum for GeoTIFF export — there is no `RasterFormatGeoTIFF` |
| `face_count` param | Use `Metashape.CustomFaceCount` with `face_count_custom=0` for unlimited |
| `cam.meta["key"]` | Bracket access only — MetaData is C++ object, no `.get()` method |
| `chunk.tie_points.points` | Can be `None` — always check before `len()` |
| `classifyGroundPoints` | On `chunk.point_cloud`, NOT on `chunk` directly |
| `exportRaster` | Handles both DEM and orthomosaic (use `source_data` parameter) |
| `progress` callback | `Callable[[float], bool]` — return True to continue, raise to cancel |

## Cross-Referencing Workflow

When adding a new tool or parameter:

1. Find the method in `api_reference.txt`
2. List ALL parameters with their types and defaults
3. Decide which to expose in the MCP tool (expose useful ones, hardcode obvious ones)
4. Check if enums need new mappings in `enums.py`
5. Verify prerequisite requirements (what must exist before this method works)
