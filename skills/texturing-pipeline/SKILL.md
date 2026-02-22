---
name: texturing-pipeline
description: Guide UV mapping, texture atlas generation, color calibration, and texture quality optimization in Metashape MCP. Covers blending modes, ghosting filter, texture size selection by use case, and diagnosing common texture artifacts. Works through the Metashape MCP server.
user-invocable: false
---

# Texturing Pipeline

## Overview

Generate photo-realistic texture atlases for 3D meshes in Metashape. Covers UV mapping, texture generation, color calibration, and quality optimization. This skill is used AFTER mesh building and BEFORE export.

## When to Use

- After mesh is built and cleaned, ready for texturing
- When choosing texture settings for a specific output (game engine, web viewer, print)
- When texture quality is poor (blurry, seams, ghosting, color shifts)
- When re-texturing after mesh edits

## Prerequisites

- Mesh exists in chunk (`get_model_stats()` should return data)
- Cameras aligned with good reprojection error (<1.0 px)
- Mesh cleaned of artifacts (run `clean_model` first)

## Standard Texture Pipeline

### Step 1: Build UV Map

```
build_uv(
    mapping_mode="generic",
    texture_size=8192
)
```

**UV mapping modes:**

| Mode | Best For | Trade-offs |
|------|---------|------------|
| `generic` | General purpose, arbitrary geometry | Good balance of distortion and coverage |
| `adaptive_orthophoto` | Terrain, aerial surveys | Optimized for top-down viewing |
| `orthophoto` | Flat surfaces, DEM overlay | Only works for near-planar geometry |
| `camera` | Single-camera texturing | Uses one camera's projection |

**For road corridors:** `generic` is the right choice. The geometry is too complex (walls, overhangs, road surface) for orthophoto modes.

### Step 2: Build Texture Atlas

```
build_texture(
    blending_mode="mosaic",
    texture_size=8192,
    ghosting_filter=True
)
```

### Step 3: (Optional) Color Calibration

If colors look inconsistent across the mesh:
```
calibrate_colors(
    source_data="model"
)
```

Run this BEFORE `build_texture` for best results. Color calibration normalizes brightness/color across cameras — critical for long corridors captured over varying lighting conditions.

## Blending Modes — When to Use What

This is the most important texture decision. Each mode produces dramatically different results.

### Mosaic
```
build_texture(blending_mode="mosaic", ...)
```
- **How it works:** Each face gets texture from the single best camera (closest, most perpendicular)
- **Result:** Sharpest possible detail per-patch. Road markings, text, and fine detail are crisp.
- **Downside:** Visible seams between patches where camera color/exposure differs
- **Best for:** Road corridors (sharp road markings), architectural detail, anything where sharpness > seamlessness

### Natural
```
build_texture(blending_mode="natural", ...)
```
- **How it works:** Blends multiple camera contributions with smooth falloff at seams
- **Result:** Smooth color transitions, no visible seams. Slightly softer detail.
- **Downside:** Road markings and text slightly blurry from multi-camera averaging
- **Best for:** Organic surfaces, vegetation, rock faces, anything where seamlessness > sharpness

### Average
```
build_texture(blending_mode="average", ...)
```
- **How it works:** Arithmetic mean of all camera contributions per texel
- **Result:** Very smooth but noticeably blurry. Reduces noise but loses detail.
- **Downside:** Blurriest option. Not recommended for most use cases.
- **Best for:** Noisy datasets, very low-res cameras, preview textures

### Max / Min
- `max`: Brightest camera value per texel. Useful for detecting features.
- `min`: Darkest camera value. Rarely useful.

## Texture Size Selection

| Output | Recommended Size | Why |
|--------|-----------------|-----|
| Game engine (Unreal/Unity) | 8192 | VRAM budget sweet spot |
| Web viewer (Cesium, Sketchfab) | 4096 | Bandwidth constraints |
| Film/VFX | 16384 | Maximum detail for close-up renders |
| Preview/testing | 2048–4096 | Fast generation |
| Print (orthophoto poster) | 16384 | DPI requirements |

**VRAM budget reality:**
- 4096x4096 × 4 channels = ~64 MB per tile
- 8192x8192 × 4 channels = ~256 MB per tile
- 16384x16384 × 4 channels = ~1 GB per tile

For 80 tiles at 8192: ~20 GB texture memory. Most game engines stream/LOD this, but it's worth knowing.

## Ghosting Filter

```
build_texture(ghosting_filter=True, ...)
```

**What it does:** Detects and removes texture contributions from cameras that captured moving objects (vehicles, pedestrians, shadows).

**Always enable for road corridors.** Vehicles and pedestrians appear in multiple camera views at different positions — without ghosting filter, they create blurred/duplicated artifacts on the road surface.

**When to disable:** Static indoor scenes, objects on turntables, anything without moving elements.

## Re-Texturing After Mesh Edits

If the mesh was modified (decimated, cleaned, split) after initial texturing:

```
# UV map may be invalid after mesh changes — rebuild
build_uv(mapping_mode="generic", texture_size=8192)
build_texture(blending_mode="mosaic", texture_size=8192, ghosting_filter=True)
```

If only small edits were made and UV is still valid:
```
# Just rebuild texture, keep existing UV
build_texture(blending_mode="mosaic", texture_size=8192, ghosting_filter=True)
```

## Diagnosing Texture Problems

### Blurry texture
| Cause | Fix |
|-------|-----|
| Texture size too low | Increase to 8192 or 16384 |
| Blending mode is "average" | Switch to "mosaic" or "natural" |
| Camera resolution too low for mesh detail | Accept or decimate mesh |
| Cameras not well-aligned (high reproj error) | Re-optimize alignment |

### Visible seams
| Cause | Fix |
|-------|-----|
| "mosaic" blending with inconsistent exposure | Switch to "natural", or run `calibrate_colors` first |
| Lighting changed during capture (dawn→day) | Run `calibrate_colors`, or split into lighting-consistent chunks |

### Ghosting / double images
| Cause | Fix |
|-------|-----|
| Moving objects (cars, people) | Enable `ghosting_filter=True` |
| Camera positions slightly wrong | Re-optimize alignment, check reprojection error |

### Color shifts / banding
| Cause | Fix |
|-------|-----|
| Auto-exposure changes during capture | `calibrate_colors(source_data="model")` |
| White balance shifts | Color calibration, or manual white balance in RAW processing |
| Vignetting from fisheye lens | Calibration should handle this; check sensor calibration |

## Texture for Tiled Export

When exporting tiles for Blender/game engine, each tile gets its own texture atlas. For consistent look:

1. Run `calibrate_colors` ONCE on the full mesh
2. Build UV + texture on the full mesh
3. Export tiles individually — each tile carries its portion of the atlas

Or, if tiling is done in Blender:
1. Export untextured mesh tiles (PLY with vertex colors)
2. Process in Blender (cleanup, classification)
3. Re-import cleaned tiles into Metashape
4. Re-texture with the cleaned geometry

The **handoff-coordinator** agent manages this round-trip.

## Common Settings Combinations

### Road corridor (driving simulator)
```
calibrate_colors(source_data="model")
build_uv(mapping_mode="generic", texture_size=8192)
build_texture(blending_mode="mosaic", texture_size=8192, ghosting_filter=True)
```

### Aerial terrain (orthomosaic alternative)
```
build_uv(mapping_mode="adaptive_orthophoto", texture_size=8192)
build_texture(blending_mode="natural", texture_size=8192, ghosting_filter=False)
```

### Detailed object (statue, artifact)
```
build_uv(mapping_mode="generic", texture_size=16384)
build_texture(blending_mode="natural", texture_size=16384, ghosting_filter=False)
```

### Quick preview
```
build_uv(mapping_mode="generic", texture_size=4096)
build_texture(blending_mode="mosaic", texture_size=4096, ghosting_filter=False)
```
