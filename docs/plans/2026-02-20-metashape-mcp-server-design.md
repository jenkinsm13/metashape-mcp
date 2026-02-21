# Metashape MCP Server - Design Document

**Date:** 2026-02-20
**Status:** Approved

## Summary

A full-featured MCP (Model Context Protocol) server for Agisoft Metashape Professional 2.3+, enabling LLM-driven photogrammetry workflows. The server runs embedded inside Metashape's Python environment and exposes the complete photogrammetry pipeline as MCP Tools, Resources, and Prompts over Streamable HTTP transport.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Connection mode | Embedded in Metashape | Direct access to `Metashape.app.document`, most natural integration |
| Transport | Streamable HTTP | Can't use STDIO inside Metashape; modern MCP transport |
| API coverage | Full workflow (~53 tools) | Covers complete photogrammetry pipeline without overwhelming |
| MCP features | Tools + Resources + Prompts | Full MCP feature set for rich LLM interaction |
| Architecture | Flat module by workflow stage | Keeps files under 200 lines, natural pipeline mapping |
| Module size | 100-200 lines max | Maintainability requirement |

## Architecture

```
metashape-mcp/
├── src/
│   └── metashape_mcp/
│       ├── __init__.py
│       ├── server.py              # FastMCP server + HTTP transport (~80 lines)
│       ├── tools/
│       │   ├── __init__.py        # Auto-discovery registration
│       │   ├── project.py         # Document operations (6 tools, ~150 lines)
│       │   ├── photos.py          # Photo management (4 tools, ~120 lines)
│       │   ├── alignment.py       # Alignment pipeline (4 tools, ~150 lines)
│       │   ├── dense.py           # Dense reconstruction (4 tools, ~150 lines)
│       │   ├── mesh.py            # Mesh operations (5 tools, ~180 lines)
│       │   ├── texture.py         # Texturing (4 tools, ~130 lines)
│       │   ├── survey.py          # Survey products (5 tools, ~180 lines)
│       │   ├── export.py          # Export operations (8 tools, ~200 lines)
│       │   ├── import_data.py     # Import operations (5 tools, ~150 lines)
│       │   ├── markers.py         # Markers & GCPs (5 tools, ~150 lines)
│       │   ├── coordinate.py      # CRS & region (3 tools, ~100 lines)
│       │   └── network.py         # Network processing (5 tools, ~150 lines)
│       ├── resources/
│       │   ├── __init__.py
│       │   ├── project_info.py    # Project/chunk state (~100 lines)
│       │   ├── camera_info.py     # Camera/sensor details (~100 lines)
│       │   └── processing.py      # Processing status/stats (~100 lines)
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── workflows.py       # Pipeline workflow prompts (~150 lines)
│       │   └── troubleshooting.py # Diagnostic prompts (~100 lines)
│       └── utils/
│           ├── __init__.py
│           ├── bridge.py          # Metashape module access (~100 lines)
│           ├── enums.py           # Enum string mapping (~100 lines)
│           └── progress.py        # Progress tracking (~80 lines)
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

## Tools Catalog (53 tools across 12 modules)

### project.py - Project Management
- `open_project(path, read_only=False)` - Open a Metashape project
- `save_project(path=None)` - Save current project
- `create_project(path)` - Create new empty project
- `add_chunk(label=None)` - Add new chunk
- `set_active_chunk(label_or_index)` - Switch active chunk
- `list_chunks()` - List all chunks with summary

### photos.py - Photo Management
- `add_photos(paths)` - Add photos to active chunk
- `analyze_images(filter_mask=False)` - Estimate image quality
- `import_video(path, frame_step="custom", custom_step=1)` - Import video
- `remove_cameras(labels=None, quality_threshold=None)` - Remove cameras

### alignment.py - Photo Alignment
- `match_photos(downscale=1, generic_preselection=True, reference_preselection=False, keypoint_limit=40000, tiepoint_limit=4000)` - Feature matching
- `align_cameras(adaptive_fitting=False, reset_alignment=False)` - Camera alignment
- `optimize_cameras(fit_f=True, fit_cx=True, fit_cy=True, fit_k1=True, fit_k2=True, fit_k3=True, fit_p1=True, fit_p2=True)` - Optimize calibration
- `reset_alignment()` - Clear alignment data

### dense.py - Dense Reconstruction
- `build_depth_maps(downscale=4, filter_mode="mild", max_neighbors=16)` - Generate depth maps
- `build_point_cloud(point_colors=True, point_confidence=False)` - Build dense point cloud
- `filter_point_cloud(point_spacing=0, clip_to_region=False)` - Filter point cloud
- `classify_point_cloud(classes=None, source="point_cloud")` - Classify ground/vegetation

### mesh.py - 3D Mesh Operations
- `build_model(surface_type="arbitrary", face_count="high", source_data="depth_maps", interpolation="enabled")` - Build mesh
- `decimate_model(face_count=200000)` - Reduce mesh complexity
- `smooth_model(strength=3, preserve_edges=False)` - Smooth mesh
- `clean_model(criterion="component_size", level=0)` - Remove artifacts
- `refine_model(downscale=4, iterations=10, smoothness=0.5)` - Refine geometry

### texture.py - Texturing
- `build_uv(mapping_mode="generic", page_count=1, texture_size=8192)` - Generate UV
- `build_texture(blending_mode="mosaic", texture_size=8192, ghosting_filter=True)` - Build texture
- `calibrate_colors(white_balance=False)` - Calibrate colors
- `calibrate_reflectance(use_panels=True, use_sun_sensor=False)` - Calibrate reflectance

### survey.py - Survey Products
- `build_dem(source_data="point_cloud", interpolation="enabled", resolution=0)` - Build DEM
- `build_orthomosaic(surface_data="model", blending_mode="mosaic", resolution=0)` - Build orthomosaic
- `build_tiled_model(pixel_size=0, tile_size=256, face_count=20000)` - Build tiled model
- `build_contours(interval=1, source_data="elevation")` - Generate contours
- `build_panorama(blending_mode="mosaic")` - Build panoramas

### export.py - Export Operations
- `export_model(path, format="obj", save_texture=True)` - Export 3D model
- `export_point_cloud(path, format="las", save_colors=True)` - Export point cloud
- `export_orthomosaic(path, format="tif")` - Export orthomosaic
- `export_dem(path, format="tif")` - Export DEM
- `export_report(path, title="", description="")` - Export PDF report
- `export_cameras(path, format="xml")` - Export camera data
- `export_tiled_model(path, format="cesium")` - Export tiled model
- `export_shapes(path, format="shp")` - Export shapes

### import_data.py - Import Operations
- `import_model(path, format=None, crs=None)` - Import 3D model
- `import_point_cloud(path, format=None, crs=None)` - Import point cloud
- `import_reference(path, format="csv", columns="nxyz", delimiter=",")` - Import GCPs/reference
- `import_cameras(path, format="xml")` - Import camera orientations
- `import_shapes(path, format=None)` - Import GIS shapes

### markers.py - Markers & Ground Control
- `detect_markers(target_type="circular_12bit", tolerance=50)` - Auto-detect targets
- `add_marker(label=None, position=None)` - Add marker manually
- `add_scalebar(marker1, marker2, distance)` - Add scalebar
- `refine_markers()` - Refine marker positions
- `list_markers()` - List markers with coordinates and errors

### coordinate.py - Coordinate Reference Systems
- `set_crs(epsg_code=None, wkt=None)` - Set chunk CRS
- `set_region(center=None, size=None)` - Set processing region
- `update_transform()` - Update chunk transformation

### network.py - Network Processing
- `network_connect(host, port=5840)` - Connect to server
- `network_submit_batch(tasks)` - Submit batch job
- `network_list_batches()` - List batches
- `network_batch_status(batch_id)` - Get batch status
- `network_abort_batch(batch_id)` - Abort batch

## Resources

| URI Pattern | Returns |
|-------------|---------|
| `metashape://project/info` | Project path, read-only, chunk count, modified |
| `metashape://project/chunks` | All chunks with processing state summary |
| `metashape://chunk/{label}/summary` | Detailed chunk stats |
| `metashape://chunk/{label}/cameras` | Camera list with alignment status |
| `metashape://chunk/{label}/sensors` | Sensor calibration info |
| `metashape://chunk/{label}/tie_points` | Tie point statistics |
| `metashape://chunk/{label}/point_cloud` | Point cloud statistics |
| `metashape://chunk/{label}/model` | Model geometry stats |
| `metashape://chunk/{label}/dem` | DEM extent and resolution |
| `metashape://chunk/{label}/orthomosaic` | Orthomosaic info |

## Prompts

| Name | Purpose | Arguments |
|------|---------|-----------|
| `aerial_survey_pipeline` | Complete drone survey workflow | `project_path`, `photo_folder`, `crs_epsg`, `quality` |
| `close_range_pipeline` | Object reconstruction workflow | `project_path`, `photo_folder`, `quality` |
| `scan_to_mesh_pipeline` | Laser scan processing | `project_path`, `scan_folder` |
| `batch_export` | Export all products | `output_folder`, `formats` |
| `diagnose_alignment` | Alignment quality check | - |
| `optimize_quality_settings` | Settings recommendation | `photo_count`, `ram_gb` |
| `check_ground_control` | GCP validation | - |

## Key Implementation Details

### Threading
Metashape's Python API is NOT thread-safe. The HTTP server runs in a background thread, but all Metashape API calls are dispatched to the main thread via a queue. This uses Python's `queue.Queue` and Metashape's `app.addTask()` or a simple polling loop.

### Enum Mapping
LLMs pass string parameters. Each enum has a string→value mapping:
- Quality: `"ultra"→1, "high"→2, "medium"→4, "low"→8, "lowest"→16`
- Filter: `"none"→NoFiltering, "mild"→MildFiltering, "moderate"→ModerateFiltering, "aggressive"→AggressiveFiltering`
- etc.

### Error Handling
All tools wrap Metashape calls in try/except and return structured error messages. Common errors:
- No project open
- No active chunk
- Missing prerequisite data (e.g., building texture without UV)
- Invalid file paths

### Progress Reporting
Long operations use MCP Context's `report_progress()` to send real-time progress updates to the client.

## Dependencies
- `mcp[cli]` >= 1.2.0 (MCP Python SDK)
- `Metashape` (provided by Metashape Professional's Python environment)
- `uvicorn` or built-in HTTP server for Streamable HTTP transport
