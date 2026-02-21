# Metashape MCP Server — AI-Powered Photogrammetry Automation

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![Metashape 2.3+](https://img.shields.io/badge/Metashape-2.3+-orange.svg)](https://www.agisoft.com/)

A comprehensive [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that brings **AI-powered automation to Agisoft Metashape Professional**. Control the full photogrammetry pipeline — from photo alignment to 3D model export — using natural language through Claude, Claude Code, or any MCP-compatible AI assistant.

> **Use AI to process drone surveys, build 3D models, generate DEMs, create orthomosaics, and export production-ready deliverables — all through conversation.**

## What This Does

This MCP server runs embedded inside Metashape's Python environment and exposes the **entire photogrammetry processing pipeline** as AI-callable tools. Instead of manually clicking through menus, you describe what you want and the AI executes the full workflow:

- **Drone aerial survey processing** — import photos, align cameras, build dense point clouds, generate DEMs and orthomosaics
- **Close-range 3D reconstruction** — object scanning, artifact digitization, heritage documentation
- **Terrain and surface modeling** — ground classification, mesh generation, texture mapping
- **GCP and marker workflows** — survey-grade accuracy with ground control points and coded markers
- **Batch export** — OBJ, PLY, FBX, TIFF, LAS, and all Metashape-supported formats
- **Network processing** — submit and monitor jobs on Metashape network processing clusters

## Features

- **53+ tools** covering every stage of the photogrammetry pipeline
- **10 resources** for real-time project state inspection
- **5 prompts** for guided workflows (aerial survey, close-range, diagnostics)
- Runs natively inside Metashape's embedded Python 3.12
- Streamable HTTP transport on `http://127.0.0.1:8765`
- Stdio proxy for Claude Code with no timeout limits on long operations
- Progress reporting for dense cloud, mesh, and texture generation
- Full coordinate reference system (CRS/EPSG) support
- **Non-blocking UI** — the Metashape GUI stays fully interactive while the AI processes in the background

### Tool Categories

| Module | Tools | Capabilities |
|--------|-------|-------------|
| **project** | 6 | Create, open, save projects; manage chunks; configure GPU/CPU |
| **photos** | 4 | Import photos and video frames, analyze image quality |
| **camera** | 3 | Enable/disable cameras, configure sensors, apply masks |
| **alignment** | 4 | Structure-from-Motion (SfM): match photos, align cameras, optimize, filter tie points |
| **dense** | 4 | Multi-View Stereo (MVS): depth maps, dense point cloud, ground classification |
| **mesh** | 5 | 3D mesh generation, decimation, smoothing, hole closing, mesh refinement |
| **texture** | 4 | UV mapping, texture atlas generation, color calibration |
| **survey** | 5 | DEM generation, orthomosaic creation, tiled models, contour lines, panoramas |
| **export** | 8 | Export to OBJ, PLY, FBX, LAS/LAZ, GeoTIFF, Cesium 3D Tiles, and more |
| **import** | 5 | Import models, point clouds, reference data, camera calibrations, shapes |
| **markers** | 5 | Detect coded markers, add GCPs, create scalebars, import/export reference |
| **coordinate** | 3 | Set CRS (EPSG codes), define bounding region, update coordinate transform |
| **network** | 5 | Network processing: batch submit, monitor, abort, configure server |
| **viewport** | 2 | Control 3D viewport camera, capture screenshots |

### Resources (Real-Time Project Inspection)

| URI | Description |
|-----|-------------|
| `metashape://project/info` | Project path, save status, chunk count |
| `metashape://project/chunks` | All chunks with processing state summary |
| `metashape://chunk/{label}/summary` | Detailed chunk statistics and quality metrics |
| `metashape://chunk/{label}/cameras` | Camera list with alignment status and error metrics |
| `metashape://chunk/{label}/sensors` | Sensor calibration parameters (focal length, distortion) |
| `metashape://chunk/{label}/tie_points` | Tie point count, projections, reprojection error |
| `metashape://chunk/{label}/point_cloud` | Dense point cloud statistics and classification |
| `metashape://chunk/{label}/model` | 3D model geometry — faces, vertices, texture resolution |
| `metashape://chunk/{label}/dem` | Digital Elevation Model extent and resolution |
| `metashape://chunk/{label}/orthomosaic` | Orthomosaic dimensions and ground sampling distance |

### Guided Workflow Prompts

| Prompt | Use Case |
|--------|----------|
| `aerial_survey_pipeline` | End-to-end drone mapping: photos → alignment → dense cloud → DEM → orthomosaic |
| `close_range_pipeline` | Object/heritage 3D reconstruction: photos → alignment → mesh → texture → export |
| `batch_export` | Export all available products from a completed project |
| `diagnose_alignment` | Troubleshoot poor camera alignment, high reprojection error |
| `optimize_quality_settings` | Get quality/speed recommendations based on dataset size |

## Prerequisites

- **Agisoft Metashape Professional 2.3+** (with Python 3.12 scripting)
- **MCP Python SDK**: `mcp[cli]>=1.2.0`
- **FastMCP**: `fastmcp>=2.0.0` — required for the stdio proxy that enables full functionality

## Installation

### 1. Clone this repository

```bash
git clone https://github.com/jenkinsm13/metashape-mcp.git
```

### 2. Install dependencies in Metashape's Python environment

Metashape ships its own embedded Python 3.12. You must install dependencies into **that** environment, not your system Python:

```bash
# Windows:
"C:\Program Files\Agisoft\Metashape Pro\python\python.exe" -m pip install "mcp[cli]>=1.2.0" "fastmcp>=2.0.0"

# macOS:
/Applications/MetashapePro.app/Contents/Frameworks/Python.framework/Versions/3.12/bin/pip3 install "mcp[cli]>=1.2.0" "fastmcp>=2.0.0"

# Linux:
/opt/metashape-pro/python/bin/pip3 install "mcp[cli]>=1.2.0" "fastmcp>=2.0.0"
```

> **Tip:** If Metashape's Python doesn't have pip, bootstrap it first:
> ```bash
> "C:\Program Files\Agisoft\Metashape Pro\python\python.exe" -m ensurepip
> ```

### 3. Start the MCP server inside Metashape

A ready-to-use startup script is included at [`scripts/start_mcp_server.py`](scripts/start_mcp_server.py).

**Option A: Auto-start with Metashape (recommended)**

1. Edit `scripts/start_mcp_server.py` and set `METASHAPE_MCP_SRC` to the path where you cloned this repo's `src/` folder
2. Copy the script to Metashape's auto-run scripts folder:
   - **Windows:** `C:\Users\<user>\AppData\Local\Agisoft\Metashape Pro\scripts\`
   - **macOS:** `~/Library/Application Support/Agisoft/Metashape Pro/scripts/`
   - **Linux:** `~/.local/share/Agisoft/Metashape Pro/scripts/`
3. Restart Metashape — the MCP server starts automatically

**Option B: Run manually via Tools > Run Script**

1. Open Metashape
2. Go to **Tools > Run Script**
3. Select `scripts/start_mcp_server.py` from this repository
4. The server starts in the background

**Option C: From Metashape's Python Console**

Open the console (**View > Console**) and run:

```python
import sys
sys.path.insert(0, r"C:\path\to\metashape-mcp\src")

from metashape_mcp.server import start_background
start_background()
# Server running on http://127.0.0.1:8765/mcp
```

> **Important:** After starting the server, open the Console panel (**View > Console**) to monitor MCP operations. You'll see progress updates, tool calls, and status messages as the AI works. The **Metashape UI is not blocked** — you can continue using menus, viewports, and tools while the AI processes in the background. This lets you visually inspect results in real time as the AI builds your photogrammetry products.

### 4. Connect your AI client

#### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "metashape": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

#### Claude Code (HTTP)

Add a `.mcp.json` file to your project directory:

```json
{
  "mcpServers": {
    "metashape": {
      "type": "http",
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

#### Claude Code with Stdio Proxy (recommended for full functionality)

The stdio proxy bridges Claude Code to the Metashape HTTP server without timeout limits. This is required for long-running operations like dense point cloud generation, mesh building, and texture generation that would otherwise fail over plain HTTP.

```bash
# Install fastmcp in your system Python (or wherever Claude Code runs)
pip install "fastmcp>=2.0.0"
```

Configure Claude Code to use the proxy in `.mcp.json`:

```json
{
  "mcpServers": {
    "metashape": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "metashape_mcp.proxy"]
    }
  }
}
```

## Usage Examples

### Drone Aerial Survey

```
Process my drone survey:
- Project path: C:/projects/site_survey.psx
- Photos folder: C:/photos/drone_flight_001/
- Coordinate system: EPSG:32633 (UTM Zone 33N)
- Quality: high
- Deliverables: DEM + orthomosaic as GeoTIFF
```

### 3D Object Reconstruction

```
Reconstruct a 3D model of this artifact:
1. Create a new project at C:/projects/artifact.psx
2. Add photos from C:/photos/artifact_scan/
3. Align cameras and build dense point cloud
4. Generate high-quality mesh with texture
5. Export as OBJ with texture atlas
```

### GCP Workflow for Survey-Grade Accuracy

```
Set up GCPs for my survey project:
1. Open project C:/projects/cadastral.psx
2. Detect coded markers in all photos
3. Import GCP coordinates from C:/gcp/control_points.csv
4. Optimize camera alignment with GCP constraints
5. Build orthomosaic at 2cm GSD
```

### Inspect Project State

```
What's the current state of my Metashape project?
How many cameras are aligned? What's the reprojection error?
What processing steps are still needed?
```

## Architecture

```
src/metashape_mcp/
├── server.py           # FastMCP entry point, Streamable HTTP transport
├── proxy.py            # Stdio-to-HTTP proxy for Claude Code
├── tools/              # 14 modules organized by photogrammetry stage
│   ├── project.py      # Project management and GPU configuration
│   ├── photos.py       # Photo import and quality analysis
│   ├── camera.py       # Camera/sensor configuration and masking
│   ├── alignment.py    # SfM: matching, alignment, optimization
│   ├── dense.py        # MVS: depth maps, dense cloud, classification
│   ├── mesh.py         # 3D mesh generation and editing
│   ├── texture.py      # UV mapping and texture generation
│   ├── survey.py       # DEM, orthomosaic, tiled model, contours
│   ├── export.py       # Multi-format export (OBJ, PLY, FBX, LAS, TIFF)
│   ├── import_data.py  # Import models, point clouds, reference data
│   ├── markers.py      # Coded markers, GCPs, scalebars
│   ├── coordinate.py   # CRS/EPSG, bounding region, transforms
│   ├── network.py      # Network processing server interaction
│   └── viewport.py     # 3D viewport control and screenshots
├── resources/          # 10 read-only project state resources
├── prompts/            # Guided workflow and troubleshooting templates
└── utils/
    ├── bridge.py       # Safe Metashape API access with error handling
    ├── enums.py        # String-to-Metashape enum parameter mapping
    └── progress.py     # Async progress callback adapter
```

**Key design patterns:**

- **Bridge layer** — All Metashape API calls go through `utils/bridge.py` for safe access with clear error messages when no project is open or a required processing step hasn't been completed
- **Enum mapping** — Human-readable string parameters (e.g., `"high"`, `"aggressive"`) are automatically mapped to Metashape's internal enum values
- **Progress reporting** — Long operations (dense cloud, mesh, texture) report progress percentage via MCP's progress callback system
- **GPU/CPU management** — CPU is automatically enabled only during alignment operations; disabled for all GPU-accelerated processing (dense cloud, meshing, texturing) where it would slow things down

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Server won't start** | Ensure `mcp[cli]` is installed in Metashape's Python, not system Python. Verify: `import mcp` in Metashape console. |
| **Connection refused** | Start the server inside Metashape first, then configure your AI client. The server must be running before connecting. |
| **Timeout on long operations** | Use the stdio proxy instead of direct HTTP. Dense cloud and mesh operations can take minutes to hours. |
| **Import errors** | Ensure `sys.path.insert(0, "/path/to/metashape-mcp/src")` points to the correct location of this repository. |
| **"No document open"** | Open or create a Metashape project before running processing tools. Use the `open_project` or `create_project` tool. |

## Frequently Asked Questions

### What is metashape-mcp?

metashape-mcp is an open-source MCP (Model Context Protocol) server that connects Agisoft Metashape Professional to AI assistants like Claude. It lets you automate photogrammetry workflows using natural language instead of manual GUI interaction or Python scripting.

### Can I use this to automate drone mapping?

Yes. metashape-mcp supports the complete drone aerial survey pipeline: importing geotagged photos, aligning cameras with Structure from Motion (SfM), building dense point clouds with Multi-View Stereo (MVS), generating Digital Elevation Models (DEMs), creating orthomosaics, and exporting to GeoTIFF and other standard formats. It also supports GCP (Ground Control Point) workflows for survey-grade accuracy.

### What AI assistants work with this?

Any MCP-compatible AI assistant can connect. This includes Claude Desktop, Claude Code, and any other application that supports the Model Context Protocol. The server uses Streamable HTTP transport and also provides a stdio proxy for clients that need it.

### Does this replace Metashape's GUI?

No. The MCP server runs alongside Metashape's GUI. Metashape must be open and running for the server to function. The AI assistant sends commands to Metashape through the MCP server, and you can still use the GUI simultaneously to inspect results, adjust viewports, or make manual corrections.

### What photogrammetry formats can I export?

metashape-mcp supports all export formats available in Metashape Professional, including: OBJ, PLY, FBX, COLLADA, STL, DXF, U3D, PDF for 3D models; LAS/LAZ for point clouds; GeoTIFF for DEMs and orthomosaics; Cesium 3D Tiles for web; KMZ for Google Earth; and Agisoft's native formats.

### Can I process ground control points (GCPs)?

Yes. The markers tools support detecting coded markers, manually placing GCPs, importing GCP coordinates from CSV files, creating scalebars for scale constraints, and optimizing camera alignment with GCP reference data. This enables survey-grade positional accuracy in your photogrammetry outputs.

### How does this handle long-running operations?

Photogrammetry operations like dense point cloud generation and mesh building can take minutes to hours depending on dataset size. The included stdio proxy (`proxy.py`) bridges the AI client to the HTTP server without timeout limits, ensuring operations complete fully. Progress percentage is reported back to the AI in real time.

### What version of Metashape do I need?

Agisoft Metashape Professional 2.3 or newer is required. The server uses Metashape's embedded Python 3.12 environment and API features introduced in version 2.3.

## Keywords

Agisoft Metashape, MCP server, Model Context Protocol, photogrammetry automation, AI photogrammetry, drone mapping, aerial survey, 3D reconstruction, point cloud processing, mesh generation, texture mapping, DEM generation, orthomosaic creation, GCP workflow, ground control points, Structure from Motion, SfM, Multi-View Stereo, MVS, Claude AI, Claude Desktop, Claude Code, LLM photogrammetry, LiDAR classification, geospatial, remote sensing, surveying, digital twin, heritage documentation, Cesium 3D Tiles, GeoTIFF export

## License

[MIT](LICENSE)
