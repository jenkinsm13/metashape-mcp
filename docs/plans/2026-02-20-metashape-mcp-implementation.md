# Metashape MCP Server - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-featured MCP server for Agisoft Metashape Professional 2.3+ that exposes the complete photogrammetry pipeline as Tools, Resources, and Prompts over Streamable HTTP transport.

**Architecture:** Flat module architecture organized by workflow stage. The server runs embedded inside Metashape's Python environment using FastMCP with Streamable HTTP transport. Each module file stays under 200 lines. All Metashape API calls go through a bridge utility that provides safe access to the active document/chunk with clear error messages.

**Tech Stack:** Python 3.8+ (Metashape's embedded Python), `mcp` SDK (FastMCP), `Metashape` module (provided by application), Streamable HTTP transport.

**Estimated total:** ~2,780 lines across 22 files, 53 tools, 10 resources, 7 prompts.

---

## Task List

### Task 1: Project Scaffolding
Create directory structure, pyproject.toml, server.py entry point, and all __init__.py files.

### Task 2: Utility Modules
Create bridge.py (safe Metashape access), enums.py (string-to-enum mapping), progress.py (progress callback).

### Task 3: Project Management Tools (6 tools)
open_project, save_project, create_project, add_chunk, set_active_chunk, list_chunks

### Task 4: Photo Management Tools (4 tools)
add_photos, analyze_images, import_video, remove_cameras

### Task 5: Alignment Tools (4 tools)
match_photos, align_cameras, optimize_cameras, reset_camera_alignment

### Task 6: Dense Reconstruction Tools (4 tools)
build_depth_maps, build_point_cloud, filter_point_cloud, clean_point_cloud

### Task 7: Mesh Tools (5 tools)
build_model, decimate_model, smooth_model, clean_model, refine_model

### Task 8: Texture Tools (4 tools)
build_uv, build_texture, calibrate_colors, calibrate_reflectance

### Task 9: Survey Products Tools (5 tools)
build_dem, build_orthomosaic, build_tiled_model, build_contours, build_panorama

### Task 10: Export Tools (8 tools)
export_model, export_point_cloud, export_orthomosaic, export_dem, export_report, export_cameras, export_tiled_model, export_shapes

### Task 11: Import Tools (5 tools)
import_model, import_point_cloud, import_reference, import_cameras, import_shapes

### Task 12: Marker & GCP Tools (5 tools)
detect_markers, add_marker, add_scalebar, refine_markers, list_markers

### Task 13: Coordinate System & Network Tools (3 + 5 tools)
set_crs, set_region, update_transform, network_connect, network_list_batches, network_batch_status, network_abort_batch, network_submit_batch

### Task 14: Resources (3 modules, 10 resources)
project_info.py, camera_info.py, processing.py

### Task 15: Prompts (2 modules, 7 prompts)
workflows.py (aerial_survey, close_range, batch_export), troubleshooting.py (diagnose_alignment, optimize_quality_settings)

### Task 16: CLAUDE.md Guide

### Task 17: README and Final Polish

---

See the design document at docs/plans/2026-02-20-metashape-mcp-server-design.md for full architectural details.

The complete implementation code for each task is embedded in this plan. Each task includes the full file contents to be created.
