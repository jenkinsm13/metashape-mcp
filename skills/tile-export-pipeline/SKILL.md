---
name: tile-export-pipeline
description: Export terrain tiles from Blender to game-ready FBX with correct transform, scale, and axis settings. Covers the full pipeline from photogrammetry mesh through Blender cleanup to FBX export via Blender MCP.
disable-model-invocation: true
---

# Tile Export Pipeline — Blender to Game-Ready FBX

## Overview

Export photogrammetry terrain tiles from Blender to FBX for game engines (Unreal, Unity, Godot). Enforces strict rules for transforms, scale, and axis conventions to ensure tiles load correctly.

## Golden Rules

1. **NEVER alter object-level transforms.** Location, Rotation, and Scale must stay at identity (0,0,0 / 0,0,0 / 1,1,1). All geometry changes happen in EDIT MODE only. If you need to move/rotate geometry, do it on the mesh data, not the object transform.
2. **FBX_SCALE_NONE** — never use FBX_SCALE_ALL or any other scale option. Photogrammetry tiles are already in real-world meters.
3. **Axis: forward='-Z', up='Y'** — standard Blender-to-game-engine convention.
4. **Tile naming: `Tile_X-Y`** where X-Y are grid coordinates.

## Export Settings

```python
bpy.ops.export_scene.fbx(
    filepath="/path/to/output/Tile_X-Y.fbx",
    use_selection=True,
    apply_scale_options='FBX_SCALE_NONE',
    axis_forward='-Z',
    axis_up='Y',
    use_mesh_modifiers=True,
    mesh_smooth_type='OFF',
    use_tspace=True,
    embed_textures=False,
    path_mode='COPY'
)
```

## Pre-Export Checklist

Before exporting any tile, verify:

1. **Identity transforms** — Object Location=(0,0,0), Rotation=(0,0,0), Scale=(1,1,1)
2. **Clean geometry** — No loose vertices, non-manifold edges removed if needed
3. **UVs present** — Top-down orthographic projection applied
4. **Correct selection** — Only the target tile object is selected
5. **Naming** — Object named `Tile_X-Y` matching grid position

## Batch Export Pattern

For each tile object in the scene:
```python
import bpy

for obj in bpy.data.objects:
    if not obj.name.startswith("Tile_"):
        continue

    # Deselect all, select this tile
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Verify identity transform
    assert obj.location.length < 0.001, f"{obj.name} has non-zero location!"
    assert abs(obj.scale.x - 1.0) < 0.001, f"{obj.name} has non-unit scale!"

    # Export
    filepath = f"/path/to/output/{obj.name}.fbx"
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        apply_scale_options='FBX_SCALE_NONE',
        axis_forward='-Z',
        axis_up='Y',
        use_mesh_modifiers=True,
        mesh_smooth_type='OFF',
        use_tspace=True,
        embed_textures=False
    )
```

## Common Issues

- **Scale looks wrong in engine**: Verify `FBX_SCALE_NONE` — any other option will bake Blender's scale factor.
- **Tile rotated/offset in engine**: Object transform was not identity. Check Location/Rotation/Scale in Blender.
- **UV seams visible**: Re-project UVs with orthographic top-down. Seam placement matters less for terrain.
