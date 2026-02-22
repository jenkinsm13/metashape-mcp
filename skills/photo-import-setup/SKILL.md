---
name: photo-import-setup
description: Set up a new Metashape project from scratch — import photos, load GPS reference, configure sensors (fisheye, rolling shutter, multi-camera), import EXR alpha masks, run image quality analysis, and disable bad frames. The first skill to use on any new capture. Works through the Metashape MCP server.
user-invocable: false
---

# Photo Import & Project Setup

## Overview

Every photogrammetry project starts with the same sequence: create project, import photos, load GPS, configure sensors, import masks, check image quality. This skill covers that entire setup phase, getting a project ready for alignment.

## When to Use

- Starting a new project from raw photos
- Adding a new camera/capture to an existing project
- Re-importing after changing folder structure or GPS data
- Setting up sensors for the first time (fisheye, rolling shutter, etc.)

## Prerequisites

- Photos on disk (EXR, JPEG, TIFF, PNG, DNG)
- GPS data (EXIF embedded or external CSV)
- Metashape MCP server running

## Setup Pipeline

### Step 1: Create or open project
```
create_project(path="E:\\Projects\\MyProject.psx")
```
Or for existing:
```
open_project(path="E:\\Projects\\MyProject.psx")
```

### Step 2: Import photos

For a single folder:
```
add_photos(paths=["E:\\Captures\\Day1\\"])
```

For multiple folders (multi-day, multi-camera):
```
add_photos(paths=["E:\\Captures\\Day1\\", "E:\\Captures\\Day2\\"])
```

For glob patterns:
```
add_photos(paths=["E:\\Captures\\**\\*.exr"])
```

**After import, verify:**
```
list_chunks()
```
Check camera count matches expected photo count.

### Step 3: Import GPS reference

If GPS is NOT in EXIF (common for vehicle-mounted captures):
```
import_reference(
    path="E:\\Captures\\gps_data.csv",
    columns="nxyz",        # n=label, x=longitude, y=latitude, z=altitude
    delimiter=","
)
```

**Column format options:**
- `"nxyz"` — label, lon, lat, alt (most common)
- `"nxy"` — label, lon, lat (no altitude)
- `"nxyzabc"` — label, lon, lat, alt, accuracy_x, accuracy_y, accuracy_z

**After import, verify GPS loaded:**
```
get_alignment_stats()
```
Check `cameras_with_reference` matches expected count.

### Step 4: Configure sensors

This is the most critical setup step. Wrong sensor configuration is the #1 cause of total alignment failure.

**Check current sensors:**
```
list_sensors()
```

**For fisheye lenses (vehicle-mounted, GoPro, 360 cameras):**
```
set_sensor(
    sensor_index=0,
    sensor_type="fisheye",
    pixel_width=0.00488,      # Check camera spec sheet
    pixel_height=0.00488,
    focal_length=8.0           # Nominal focal length in mm
)
```

**CRITICAL: If you have a fisheye lens and don't set sensor_type="fisheye", alignment WILL fail.** This is the single most common setup error. The alignment-doctor agent exists largely because of this mistake.

**For rolling shutter cameras (most consumer cameras, phones, GoPros):**
Rolling shutter compensation is set during `match_photos`, not sensor config. But knowing your camera uses electronic (rolling) shutter vs mechanical (global) shutter matters for choosing settings.

**Multi-camera rigs:**
If you have multiple camera bodies, each needs its own sensor:
```
# Check if Metashape auto-detected separate sensors
list_sensors()
# If all cameras share one sensor but shouldn't:
# Separate cameras by body/lens in the Metashape GUI, then configure each sensor
```

### Step 5: Import masks (for EXR with alpha)

For EXR files where the alpha channel masks the sky:
```
import_masks(
    method="alpha",
    path="{filename}"
)
```

The `{filename}` template tells Metashape to use each camera's own file as the mask source, reading the alpha channel.

**Other mask sources:**

| Method | Use Case |
|--------|----------|
| `"alpha"` | EXR/PNG with alpha channel (sky mask) |
| `"file"` | Separate mask files (8-bit images, black=masked) |
| `"model"` | Generate from 3D model (requires existing model) |
| `"background"` | Auto-detect static background |

**After mask import, verify:**
```
get_camera_metadata(label="your_first_camera_label")
```
Check that mask information is present.

### Step 6: Analyze image quality

```
analyze_images()
```

This estimates sharpness quality for every camera. Review results:

```
select_cameras(max_quality=0.5)
```

**Quality thresholds:**
- **>0.7**: Good quality
- **0.5-0.7**: Acceptable, may cause issues in sparse areas
- **<0.5**: Poor — likely blurry from motion, defocus, or obstruction

**Disable low-quality cameras:**
```
enable_cameras(labels=[...poor_quality_labels...], enable=False)
```

Or disable all below threshold in one step:
```
remove_cameras(quality_threshold=0.5)
```
WARNING: `remove_cameras` DELETES them. Use `enable_cameras(enable=False)` to keep them disabled but available for re-enabling later.

### Step 7: Set reference accuracy

Tell Metashape how accurate your GPS is:
```
set_reference_settings(
    camera_accuracy_xy=3.0,     # Consumer GPS: 3-5m
    camera_accuracy_z=5.0       # Vertical always worse
)
```

**GPS accuracy by type:**

| GPS Type | XY Accuracy | Z Accuracy |
|----------|-------------|------------|
| Consumer EXIF | 5.0 m | 10.0 m |
| Phone GPS | 3.0 m | 5.0 m |
| L1 GPS logger | 1.0 m | 2.0 m |
| RTK/PPK | 0.02 m | 0.04 m |

### Step 8: Set GPU config for alignment

```
set_gpu_config(cpu_enable=True)
```

CPU is ON for alignment (match_photos + align_cameras). It will be turned OFF before dense reconstruction.

## Setup Complete — Ready for Alignment

At this point your project is ready. Next steps:
- For corridor captures: use the `corridor-alignment-pipeline` skill
- For aerial/close-range: proceed with `match_photos` + `align_cameras` directly
- If alignment fails: invoke the `alignment-doctor` agent

## Decision Tree

```
Photos imported?
├── NO → Step 2: add_photos
├── YES → GPS loaded?
    ├── NO → Step 3: import_reference
    ├── YES → Sensors configured?
        ├── NO → Step 4: set_sensor (CHECK FISHEYE!)
        ├── YES → Masks needed?
            ├── YES (EXR) → Step 5: import_masks
            ├── NO → Quality checked?
                ├── NO → Step 6: analyze_images
                ├── YES → Ready for alignment
```

## Common Setup Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Fisheye not set as fisheye | Total alignment failure (<20%) | `set_sensor(sensor_type="fisheye")` |
| GPS CSV wrong column order | Cameras placed in wrong hemisphere | Check `columns` parameter matches your CSV |
| GPS in wrong CRS | Cameras scattered randomly on map | Set chunk CRS to match GPS datum before import |
| Masks not imported | Sky reconstructed as tunnel | `import_masks(method="alpha", path="{filename}")` |
| Rolling shutter not enabled | Wavy/distorted alignment | Enable in `match_photos` settings |
| All cameras enabled despite blur | Poor alignment quality | `analyze_images()` then disable <0.5 quality |

## Road Corridor Specifics

For Decker Canyon-style vehicle-mounted fisheye captures:
- Camera: full-frame with fisheye lens → `set_sensor(sensor_type="fisheye")`
- Format: EXR with alpha → `import_masks(method="alpha", path="{filename}")`
- GPS: CSV from logger → `import_reference(path="gps.csv", columns="nxyz")`
- Quality: motion blur on turns → `analyze_images()`, disable <0.5
- Batch size: ~200 cameras per alignment batch
- Reference accuracy: consumer GPS → `camera_accuracy_xy=3.0`
