---
name: batch-export
description: Export all available products from the current Metashape project — point cloud, model, DEM, orthomosaic, tiled model, report, and cameras. Skips unavailable products automatically.
user-invocable: true
---

# Batch Export

Export all available processing results from the active Metashape chunk.

## Workflow

1. **Check available products**: Use `get_model_stats` and `get_point_cloud_stats` to see what exists
2. **Export each product** that is available to the user-specified output folder:
   - **Point Cloud**: `export_point_cloud(path, format="laz")`
   - **Model**: `export_model(path, format="obj", save_texture=True)`
   - **DEM**: `export_dem(path, format="tif")`
   - **Orthomosaic**: `export_orthomosaic(path, format="tif")`
   - **Tiled Model**: `export_tiled_model(path, format="cesium")`
   - **Report**: `export_report(path)` (PDF)
   - **Cameras**: `export_cameras(path, format="xml")`
3. **Skip** products that don't exist — don't error on missing data
4. **Report** file sizes after each export

## Rules

- Ask the user for the output folder before starting
- Save the project before exporting: `save_project()`
- If the user specifies particular formats (e.g. "just the DEM and ortho"), only export those
