[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/jenkinsm13-metashape-mcp-badge.png)](https://mseep.ai/app/jenkinsm13-metashape-mcp)

# Metashape MCP Server — AI-Powered Photogrammetry Automation

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![Metashape 2.3+](https://img.shields.io/badge/Metashape-2.3+-orange.svg)](https://www.agisoft.com/)

A comprehensive [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that brings **AI-powered automation to Agisoft Metashape Professional**. 106 tools, 10 resources, and 6 prompts covering the full photogrammetry pipeline — from photo alignment to 3D model export — using natural language through Claude, Claude Code, or any MCP-compatible AI assistant.

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

- **106 tools** across 15 modules covering every stage of the photogrammetry pipeline
- **10 resources** for real-time project state inspection
- **6 prompts** for guided workflows (aerial survey, close-range, diagnostics)
- Runs natively inside Metashape's embedded Python 3.12
- Streamable HTTP transport (default `http://127.0.0.1:8765`, port is user-configurable via startup script or METASHAPE_MCP_PORT env)
- Stdio proxy for Claude Code with no timeout limits on long operations
- Progress reporting for dense cloud, mesh, and texture generation
- Full coordinate reference system (CRS/EPSG) support
- **Non-blocking UI** — the Metashape GUI stays fully interactive while the AI processes in the background
- **Headless mode** — run without GUI on remote servers, VMs, or CI pipelines for automated processing

### Tool Categories

| Module | Tools | Capabilities |
|--------|-------|-------------|
| **project** | 12 | Create, open, save projects; manage/merge/align/duplicate chunks; GPU/CPU config; processing status |
| **photos** | 5 | Import photos and video frames, analyze image quality, remove/rename cameras |
| **camera** | 8 | Enable/disable/select cameras, configure sensors, import/clear masks, camera metadata and reference |
| **alignment** | 6 | Structure-from-Motion (SfM): match photos, align cameras, optimize, filter tie points, reset alignment |
| **dense** | 12 | Multi-View Stereo (MVS): depth maps, dense point cloud, ground classification, filtering, smoothing, colorization |
| **mesh** | 8 | 3D mesh generation, decimation, smoothing, hole closing, mesh refinement, cleaning, colorization |
| **texture** | 5 | UV mapping, texture atlas generation, color calibration, texture removal |
| **survey** | 8 | DEM generation, orthomosaic creation, tiled models, contour lines, panoramas, raster export |
| **export** | 10 | Export to OBJ, PLY, FBX, LAS/LAZ, GeoTIFF, Cesium 3D Tiles, cameras, reference, report, and more |
| **import** | 6 | Import models, point clouds, reference data, camera calibrations, shapes, masks |
| **markers** | 9 | Detect coded markers, add/remove GCPs, create/remove scalebars, set reference, import/export markers |
| **coordinate** | 8 | Set CRS (EPSG codes), define bounding region, update coordinate transform, reprojection, localization |
| **network** | 5 | Network processing: connect, batch submit, list, monitor, abort |
| **viewport** | 3 | Capture viewport screenshots, read console output, auto-save project |
| **scripting** | 1 | Execute arbitrary Python code inside Metashape's environment |

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
- **MCP Python SDK** and **FastMCP** — auto-installed on first run by the startup scripts

## Installation

### 1. Clone this repository

```bash
git clone https://github.com/jenkinsm13/metashape-mcp.git
```

### 2. Start the MCP server inside Metashape

> **Dependencies are installed automatically.** The startup scripts detect missing packages (`mcp`, `fastmcp`) and install them into Metashape's Python on first run. No manual pip commands needed.

A ready-to-use startup script is included at [`scripts/start_mcp_server.py`](scripts/start_mcp_server.py).

The script now displays a small dialog on launch where you can view or
change the TCP port used by the MCP server.  Your choice is saved in
`~/.metashape_mcp_port` so subsequent sessions default to the same
value.  Changing the port will restart the embedded server automatically
(if one was already running).

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

**Option D: Headless mode (no GUI — remote servers, VMs, CI pipelines)**

For automated processing on machines without a display, run Metashape in headless/offscreen mode with [`scripts/start_mcp_headless.py`](scripts/start_mcp_headless.py):

```bash
# Windows:
"C:\Program Files\Agisoft\Metashape Pro\metashape.exe" -platform offscreen -r start_mcp_headless.py

# Linux:
metashape -platform offscreen -r start_mcp_headless.py

# macOS:
/Applications/MetashapePro.app/Contents/MacOS/MetashapePro -platform offscreen -r start_mcp_headless.py
```

The server runs in the foreground (blocks until Ctrl+C). All processing, export, import, and scripting tools work normally. Viewport/screenshot tools are unavailable in headless mode since there's no display.

> **Use cases for headless mode:** Remote processing servers, cloud VMs, Docker containers, CI/CD pipelines, automated batch processing, and any environment where you want the AI to drive Metashape without a graphical desktop.

### 3. Connect your AI client

#### Understanding the architecture (read this first)

```
┌──────────────────┐      stdio (no timeout)      ┌──────────────────┐      HTTP       ┌──────────────────┐
│   Claude Code    │ ◄──────────────────────────► │   proxy.py       │ ◄─────────────► │   Metashape      │
│   (AI client)    │                               │   (FastMCP)      │                  │   (port 8765)    │
└──────────────────┘                               └──────────────────┘                  └──────────────────┘
```

Two things are running:

1. **The HTTP server inside Metashape** — started in Step 2 above, listens on `http://127.0.0.1:8765/mcp`
2. **The stdio proxy** (`proxy.py`) — a tiny FastMCP process that Claude Code spawns. It forwards tool calls from stdio to the HTTP server with a **24-hour timeout** instead of the default ~60 seconds.

> **Why not connect Claude Code directly to `http://127.0.0.1:8765/mcp`?**
>
> You can, and it works for quick operations. But **photogrammetry operations take minutes to hours** (dense point clouds, mesh building, texturing large datasets). Claude Code's HTTP transport has a hard ~60-second read timeout. When a tool call takes longer than that, the connection drops and the operation appears to fail — even though Metashape is still processing. The stdio proxy has **no timeout**, so operations can run for as long as they need.

---

#### Claude Code (recommended setup — stdio proxy)

> **Multiple MCP instances?**
> 1. Choose a different port for each Metashape session using the
>    startup script dialog or `METASHAPE_MCP_PORT` env var.
> 2. Configure the same port on the **agent side**:
>    * For the stdio proxy, set `METASHAPE_MCP_PORT` in the environment
>      where you launch `proxy.py` (it uses the variable to build its URL).
>    * For direct HTTP connections, include the port in the `url` field of
>      your `.mcp.json` or Claude Desktop config (e.g.
>      `"url": "http://127.0.0.1:8766/mcp"`).
>    This ensures the client talks to the right server instead of the
>    default 8765 instance.


> **This is the setup you almost certainly want.** It handles both quick operations and hour-long processing without timeout failures.

**Step 1:** Find which Python Claude Code will use, and install FastMCP there:

```bash
# Find your Python's full path
python -c "import sys; print(sys.executable)"

# Install FastMCP in that Python (NOT Metashape's Python)
pip install "fastmcp>=2.0.0"
```

> **Multiple Python installations?** If you have multiple Pythons (Miniconda, Windows Store, standalone installs), Claude Code may pick a different one than your terminal uses. The `"command"` in Step 2 must point to the Python that has `fastmcp` installed. Use the **full path** from the command above instead of just `"python"` to avoid ambiguity — e.g., `"command": "C:/Users/you/AppData/Local/.../python.exe"`.

**Step 2:** Add to your `.mcp.json` (either `~/.claude/.mcp.json` for global, or `.mcp.json` in your project root):

```json
{
  "mcpServers": {
    "metashape": {
      "command": "python",
      "args": ["-m", "metashape_mcp.proxy"],
      "env": {
        "PYTHONPATH": "C:/path/to/metashape-mcp/src"
      }
    }
  }
}
```

> **Replace `C:/path/to/metashape-mcp/src`** with the actual path to where you cloned this repo's `src/` directory.
> For example: `"PYTHONPATH": "C:/Users/you/Documents/metashape-mcp/src"`
>
> **Replace `python`** with the full path to the Python executable that has `fastmcp` installed if you have multiple Python installations. See the note in Step 1.

**Step 3:** Verify it works — restart Claude Code (or run `/mcp` to reconnect), then ask Claude to list Metashape tools. You should see 106 tools appear.

---

#### Claude Code (direct HTTP — NOT recommended)

> **Warning:** This works for quick operations but **will timeout and fail on any operation taking longer than ~60 seconds**. This includes dense point cloud generation, mesh building, texturing, and many other core photogrammetry operations. Use the stdio proxy above instead.

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

---

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

> Claude Desktop manages its own HTTP connection and handles long-running operations differently from Claude Code. Direct HTTP works fine here.

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

### Custom Python Scripts (YOLO masking, batch workflows, etc.)

The `execute_python` tool gives the AI full access to Metashape's Python 3.12 runtime. It can import any package installed in Metashape's environment and run arbitrary code:

```
Run a YOLO model to generate masks for all photos:
- Use ultralytics to detect objects in each camera image
- Generate binary masks and apply them in Metashape
- Then rebuild the dense point cloud without the masked regions
```

```
Write a custom batch script that:
1. Opens every .psx file in C:/projects/batch/
2. Rebuilds the mesh at medium quality
3. Exports each as FBX to C:/exports/
4. Saves and closes each project
```

The AI has access to `Metashape`, `app`, `doc`, and `chunk` variables pre-loaded, plus any library you've pip-installed into Metashape's Python (numpy, opencv-python, ultralytics, pillow, etc.).

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
├── tools/              # 15 modules organized by photogrammetry stage
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
│   ├── viewport.py     # 3D viewport control and screenshots
│   └── scripting.py    # Arbitrary Python code execution (YOLO, batch, custom)
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
| **Server won't start** | Dependencies are auto-installed on first run. If auto-install fails, install manually: `"C:\Program Files\Agisoft\Metashape Pro\python\python.exe" -m pip install "mcp[cli]>=1.2.0" "fastmcp>=2.0.0"` (see below for macOS/Linux paths). |
| **Connection refused** | Start the server inside Metashape first (Step 2), then configure your AI client. The server must be running before connecting. |
| **"Failed to reconnect" in Claude Code** | **Most common cause:** Claude Code is spawning a different Python than the one with `fastmcp` installed. Check the debug log at `~/.claude/debug/` for `ModuleNotFoundError: No module named 'fastmcp'`. Fix: use the **full path** to the Python executable that has `fastmcp` installed in your `.mcp.json` `"command"` field instead of just `"python"`. Also verify: (1) you're using the stdio proxy config, not direct HTTP; (2) Metashape is running with the server started. Test the HTTP server directly with: `curl -s -X POST -H "Content-Type: application/json" -H "Accept: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1.0"}}}' http://127.0.0.1:8765/mcp` |
| **Timeout / dropped connection on long operations** | You're using direct HTTP instead of the stdio proxy. Switch to the stdio proxy config — direct HTTP has a ~60s timeout that kills long-running photogrammetry operations. See "Claude Code (recommended setup)" above. |
| **Import errors** | Ensure the `PYTHONPATH` in your `.mcp.json` points to `metashape-mcp/src`. If running manually, use `sys.path.insert(0, "/path/to/metashape-mcp/src")`. |
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

### Can I run this without a GUI (headless mode)?

Yes. metashape-mcp supports headless operation for remote servers, cloud VMs, Docker containers, and CI/CD pipelines. Run Metashape with `-platform offscreen` and the headless startup script. All photogrammetry processing, export, import, scripting, and network tools work normally in headless mode — only the viewport/screenshot tools require a display. This lets you set up fully automated AI-driven photogrammetry pipelines on machines without a graphical desktop.

### Can the AI run custom Python scripts in Metashape?

Yes. The `execute_python` tool gives the AI full access to Metashape's Python 3.12 runtime. It can write and run arbitrary code — import third-party libraries like YOLO/ultralytics, OpenCV, NumPy, or Pillow, script custom batch workflows across multiple projects, generate masks from ML models, do image processing, or anything else Python can do. The AI has pre-loaded access to the Metashape module, the active document, and the active chunk.

### What version of Metashape do I need?

Agisoft Metashape Professional 2.3 or newer is required. The server uses Metashape's embedded Python 3.12 environment and API features introduced in version 2.3.

## Keywords

Agisoft Metashape, MCP server, Model Context Protocol, photogrammetry automation, AI photogrammetry, drone mapping, aerial survey, 3D reconstruction, point cloud processing, mesh generation, texture mapping, DEM generation, orthomosaic creation, GCP workflow, ground control points, Structure from Motion, SfM, Multi-View Stereo, MVS, Claude AI, Claude Desktop, Claude Code, LLM photogrammetry, LiDAR classification, geospatial, remote sensing, surveying, digital twin, heritage documentation, Cesium 3D Tiles, GeoTIFF export, headless photogrammetry, batch processing, YOLO masking, Python scripting, automated pipeline, CI/CD photogrammetry

## License

[MIT](LICENSE)
