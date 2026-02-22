---
name: corridor-alignment-pipeline
description: Orchestrate incremental alignment of long road corridor captures with automatic drift detection and QA gates. Prevents alignment divergence by checking GPS deviation gradients and continuity between batches. Works through the Metashape MCP server.
user-invocable: false
---

# Corridor Alignment Pipeline with Drift Detection

## Overview

Align large road corridor captures incrementally in batches, with automatic drift detection between every batch. The pipeline stops if alignment diverges from GPS, preventing hours of wasted processing.

## When to Use

- Aligning road corridor captures (100+ cameras along a linear path)
- Any linear capture where drift is a concern (railways, pipelines, coastlines)
- When GPS reference data is available for cameras

## Prerequisites

- Photos imported into a chunk with GPS reference data (EXIF or imported CSV)
- Sensors configured (fisheye, rolling shutter, axes) per the `metashape-alignment` skill
- GPU config: `set_gpu_config(cpu_enable=True)` for alignment

## Pipeline Steps

For each batch of cameras (recommended ~200 per batch):

### 1. Enable batch cameras
```
enable_cameras(labels=batch_labels, enable=True)
```

### 2. Match and align
```
match_photos(
    generic_preselection=True,
    reference_preselection=True,
    keep_keypoints=True,          # ALWAYS True for incremental
    reset_matches=False            # True only for very first batch
)
align_cameras(
    reset_alignment=False          # True only for very first batch
)
save_project()
```

### 3. Check drift (CRITICAL — do this after EVERY batch)
```
get_camera_spatial_stats()
```

Evaluate the `error_gradient_per_100m` field:

| Gradient | Assessment | Action |
|----------|------------|--------|
| < 0.5 m/100m | **PASS** | Continue to next batch |
| 0.5 - 2.0 m/100m | **WARN** | Alert user. Suggest placing GCPs in the drifting region before continuing. |
| > 2.0 m/100m | **FAIL** | **STOP.** Report the problem. Do NOT continue alignment. |

### 4. Check continuity with previous batch
```
check_alignment_continuity(new_camera_labels=batch_labels)
```

If `continuous` is False:
- Report which cameras have position jumps or rotation breaks
- **STOP** and let the user investigate before continuing

### 5. Repeat for next batch

After all batches:

### 6. Full corridor assessment
```
get_corridor_drift_report(num_segments=10)
```

Review the segment-by-segment breakdown. If error increases along the corridor, GCPs should be placed in the high-error region.

### 7. If DEM is available
```
compare_alignment_to_dem(camera_height_offset=2.0)
```

This gives ground-truth vertical drift independent of GPS noise.

### 8. Optionally generate virtual checkpoints
```
generate_virtual_checkpoints(spacing_meters=200.0, camera_height_offset=2.0)
```

Creates evenly-spaced markers from DEM to measure alignment quality along the corridor. These are check points (for reporting), NOT control points (for optimization).

### 9. Proceed to USGS filtering
Only after drift assessment passes. See `metashape-alignment` skill for the filtering workflow.

## Decision Tree

```
After each batch:
├── error_gradient < 0.5 AND continuous → next batch
├── error_gradient 0.5-2.0 → WARN user
│   ├── User says continue → next batch (with note)
│   └── User says stop → place GCPs, re-evaluate
├── error_gradient > 2.0 → STOP
│   └── Recommend: place GCPs, possibly re-align last batch
└── discontinuity detected → STOP
    └── Recommend: check camera labels, matching settings
```

## Thresholds

These defaults work for vehicle-mounted cameras with consumer GPS (~3m accuracy):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `error_gradient` PASS | < 0.5 m/100m | Normal GPS noise |
| `error_gradient` WARN | 0.5 - 2.0 m/100m | Possible drift starting |
| `error_gradient` FAIL | > 2.0 m/100m | Alignment is diverging |
| `max_position_jump` | 5.0 m | Continuity check for position |
| `max_rotation_jump` | 15.0 degrees | Continuity check for rotation |

For RTK GPS (~2cm accuracy), tighten thresholds by 10x.

## Common Drift Causes

1. **Insufficient overlap** between batches — ensure 50+ cameras overlap between consecutive batches
2. **Repetitive road surface** — all asphalt looks the same. Enable `guided_matching=True`
3. **Long straight corridor** — no cross-track features to constrain. Place GCPs at curves
4. **Mixed lighting** — morning/evening batches don't match well across day boundaries
5. **GPS offset** — systematic GPS error in one direction. Not drift per se, but shows as gradient

## Example Conversation

User: "Align these 2000 Z9 cameras in batches of 200"

Agent workflow:
1. Disable all cameras
2. Enable first 200, match (reset_matches=True), align (reset_alignment=True)
3. Check drift → PASS (0.1 m/100m, first batch baseline)
4. Enable next 200, match, align (reset_alignment=False)
5. Check drift → PASS (0.15 m/100m)
6. ... repeat batches 3-8 ...
7. Check drift → WARN (0.8 m/100m, gradient increasing)
8. Report to user: "Drift is increasing in cameras 1600-1800 area. Recommend placing GCPs near [coordinates] before continuing."
9. User places GCPs, says "continue"
10. Enable next 200, match, align
11. Check drift → PASS (0.3 m/100m, GCPs stabilized it)
12. Continue remaining batches
13. Run full corridor report → PASS
14. Proceed to USGS filtering
