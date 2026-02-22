---
name: metashape-reconstruction
description: Guide dense reconstruction, mesh building, and texturing in Metashape MCP. Covers depth maps, point cloud, mesh, texture, DEM, and orthomosaic generation with correct GPU/CPU settings and quality parameters. Works through the Metashape MCP server.
user-invocable: false
---

# Metashape Dense Reconstruction via MCP

## Overview

Build dense products from aligned cameras in Metashape using MCP tools. This covers everything AFTER alignment: depth maps, dense point cloud, mesh, texture, DEM, and orthomosaic. All MCP tool calls block until complete — no polling, no timeouts.

## When to Use

- Building depth maps, point cloud, mesh, or texture in Metashape
- Generating DEM or orthomosaic survey products
- Any processing step after photo alignment is complete

## Golden Rules

1. **CPU OFF for all dense operations.** `set_gpu_config(cpu_enable=False)` before depth maps, point cloud, meshing, texturing, DEM, orthomosaic. CPU slows GPU operations. CPU is ONLY for alignment (match_photos, align_cameras).
2. **NEVER write pipeline scripts.** Call each MCP tool individually, check the result, adapt. This is an AGENT workflow.
3. **No timeouts.** Dense operations can take hours or days. MCP calls block until done.
4. **No polling.** Don't call `get_processing_status` in a loop.
5. **Save after every step.** The MCP tools auto-save, but verify with `save_project()` after major operations.
6. **Check prerequisites.** Each step requires the previous step's output. Verify before proceeding.

## Standard Dense Pipeline

### Step 0: Verify alignment is complete
```
get_alignment_stats()
# Check: alignment_rate should be >95%
# Check: tie_point_count_valid should be reasonable
```

### Step 1: GPU config — CPU OFF
```
set_gpu_config(cpu_enable=False)
```

### Step 2: Build depth maps
```
build_depth_maps(
    downscale=2,          # 1=Ultra, 2=High, 4=Medium, 8=Low, 16=Lowest
    filter_mode="mild",   # mild for complex terrain, moderate default, aggressive for clean scenes
    reuse_depth=True      # Reuse existing depth maps for aligned cameras
)
```
**Quality guide:**
- `downscale=1` (Ultra): Final production, small projects. Very slow.
- `downscale=2` (High): Standard production quality. Good balance.
- `downscale=4` (Medium): Quick results, large projects, testing.

### Step 3: Build point cloud (optional — needed for classification)
```
build_point_cloud(
    point_colors=True,
    point_confidence=True
)
```
Skip if going directly to mesh from depth maps.

### Step 4: (Optional) Classify ground points
Only needed for terrain/DEM workflows:
```
classify_ground_points(
    max_angle=15.0,
    max_distance=1.0,
    cell_size=50.0
)
```

### Step 5: Build mesh
```
build_model(
    surface_type="arbitrary",    # "arbitrary" for 3D, "height_field" for terrain/DEM
    source_data="depth_maps",    # "depth_maps", "point_cloud", "depth_maps_and_laser_scans"
    interpolation="enabled",     # "disabled", "enabled", "extrapolated"
    vertex_colors=True,
    vertex_confidence=True,
    volumetric_masks=False,
    keep_depth=True
)
```
- `face_count_custom=0` is hardcoded (unlimited faces)
- `trimming_radius=0` is hardcoded (no trimming)
- For terrain-only mesh from classified point cloud: `classes=[2]` (ground only)

### Step 6: Build UV
```
build_uv(
    mapping_mode="generic",    # "generic", "adaptive_orthophoto", "orthophoto", "camera"
    texture_size=8192          # Power of 2: 4096, 8192, 16384
)
```

### Step 7: Build texture
```
build_texture(
    blending_mode="natural",   # "natural" (default, best quality), "mosaic", "average", "max", "min"
    texture_size=8192,
    ghosting_filter=True
)
```

### Step 8: (Optional) Survey products

**DEM:**
```
build_dem(
    source_data="point_cloud",  # or "mesh"
    interpolation="enabled",
    classes=[2]                  # Ground only, if classified
)
```

**Orthomosaic:**
```
build_orthomosaic(
    surface_data="dem",         # or "mesh", "none"
    blending_mode="mosaic",
    ghosting_filter=True
)
```

## Surface Type Selection

| Use Case | surface_type | source_data |
|----------|-------------|-------------|
| 3D object/scene | arbitrary | depth_maps |
| Terrain/landscape | height_field | depth_maps |
| With laser scans | arbitrary | depth_maps_and_laser_scans |
| From dense cloud | arbitrary | point_cloud |
| Quick preview | arbitrary | tie_points |

## Depth Map Filter Modes

| Mode | When to Use |
|------|-------------|
| mild | Complex terrain, vegetation, rock faces — preserves detail |
| moderate | Default, good for most scenes |
| aggressive | Clean/flat surfaces, buildings — removes more noise |

## Texture Blending Modes

| Mode | When to Use |
|------|-------------|
| natural | Default. Best color continuity across seams |
| mosaic | Sharpest detail per-patch but visible seams |
| average | Smooth blending, can be slightly blurry |

## Quality vs Speed Tradeoffs

For **testing/preview**: `downscale=4` depth maps, `texture_size=4096`
For **production**: `downscale=2` depth maps, `texture_size=8192`
For **ultra quality**: `downscale=1` depth maps, `texture_size=16384`

## Common Issues

- **Out of GPU memory on depth maps**: Increase `downscale` (e.g., 2→4). Ultra (1) requires significant VRAM.
- **Holes in mesh**: Try `interpolation="extrapolated"` or build from point cloud instead of depth maps.
- **Blurry texture**: Increase `texture_size`, or try `blending_mode="mosaic"` for sharper (but seam-visible) results.
- **Mesh too large for export**: Use `decimate_model(face_count=target)` after building.
