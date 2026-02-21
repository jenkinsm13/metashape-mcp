# Metashape MCP Server

A full-featured [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server for **Agisoft Metashape Professional 2.3+** that enables LLM-driven photogrammetry workflows.

The server runs embedded inside Metashape's Python environment and exposes the complete photogrammetry pipeline as MCP Tools, Resources, and Prompts over Streamable HTTP transport.

## Features

- **53 tools** covering the full photogrammetry pipeline
- **10 resources** for inspecting project state
- **5 prompts** for common workflows and diagnostics
- Runs inside Metashape's embedded Python 3.12
- Streamable HTTP transport on `http://127.0.0.1:8765`

### Tool Categories

| Module | Tools | Description |
|--------|-------|-------------|
| `project` | 6 | Open, save, create projects; manage chunks |
| `photos` | 4 | Add photos, analyze quality, import video |
| `alignment` | 4 | Match photos, align/optimize cameras |
| `dense` | 4 | Depth maps, point cloud, ground classification |
| `mesh` | 5 | Build, decimate, smooth, clean, refine models |
| `texture` | 4 | UV mapping, textures, color/reflectance calibration |
| `survey` | 5 | DEM, orthomosaic, tiled model, contours, panorama |
| `export` | 8 | Export all product types (model, point cloud, raster, etc.) |
| `import` | 5 | Import models, point clouds, reference data, cameras, shapes |
| `markers` | 5 | Detect markers, add GCPs, scalebars |
| `coordinate` | 3 | Set CRS, region, update transform |
| `network` | 5 | Network processing: submit, monitor, abort batches |

### Resources

| URI | Description |
|-----|-------------|
| `metashape://project/info` | Project path, status, chunk count |
| `metashape://project/chunks` | All chunks with processing state |
| `metashape://chunk/{label}/summary` | Detailed chunk statistics |
| `metashape://chunk/{label}/cameras` | Camera list with alignment status |
| `metashape://chunk/{label}/sensors` | Sensor calibration info |
| `metashape://chunk/{label}/tie_points` | Tie point statistics |
| `metashape://chunk/{label}/point_cloud` | Point cloud statistics |
| `metashape://chunk/{label}/model` | Model geometry stats |
| `metashape://chunk/{label}/dem` | DEM extent and resolution |
| `metashape://chunk/{label}/orthomosaic` | Orthomosaic info |

### Prompts

| Name | Description |
|------|-------------|
| `aerial_survey_pipeline` | Complete drone survey workflow |
| `close_range_pipeline` | Object reconstruction workflow |
| `batch_export` | Export all available products |
| `diagnose_alignment` | Alignment quality diagnostics |
| `optimize_quality_settings` | Settings recommendations by dataset size |

## Installation

### Prerequisites

- Agisoft Metashape Professional 2.3+
- The MCP Python SDK: `pip install "mcp[cli]>=1.2.0"`

### Setup

1. Install the MCP SDK in Metashape's Python environment:
   ```
   # From Metashape's Python console or bundled pip:
   pip install "mcp[cli]>=1.2.0"
   ```

2. Clone or copy this repository to a location accessible by Metashape.

3. Add the `src/` directory to Metashape's Python path.

### Starting the Server

**Option A: From Metashape's Python Console**

```python
import sys
sys.path.insert(0, "/path/to/metashape-mcp/src")

from metashape_mcp.server import start_background
start_background()
# Server running on http://127.0.0.1:8765
```

**Option B: As a Metashape Startup Script**

Save a script as `start_mcp.py`:

```python
import sys
sys.path.insert(0, "/path/to/metashape-mcp/src")
from metashape_mcp.server import start_background
start_background()
```

Run it via Metashape's Tools > Run Script menu, or pass it with `-r`:

```bash
metashape.exe -r start_mcp.py
```

### Connecting from Claude Desktop

Add to your Claude Desktop MCP configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "metashape": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

## Usage Examples

### Aerial Survey Pipeline

Use the `aerial_survey_pipeline` prompt:

```
Process an aerial survey:
- Project: C:/projects/site.psx
- Photos: C:/photos/drone_flight/
- CRS: EPSG:32633 (UTM Zone 33N)
- Quality: high
```

### Close-Range Object Scan

```
Reconstruct a 3D object:
1. Create project at C:/projects/artifact.psx
2. Add photos from C:/photos/artifact/
3. Process at high quality
4. Export as OBJ with texture
```

### Inspect Project State

The LLM can read project resources to understand the current state:

```
What's the current state of my Metashape project?
How many cameras are aligned?
What processing steps have been completed?
```

## Architecture

The server uses a flat module architecture organized by workflow stage:

- Each tool module stays under 200 lines for maintainability
- All Metashape API calls go through `utils/bridge.py` for safe access
- String parameters are mapped to Metashape enums via `utils/enums.py`
- Long operations report progress via MCP's progress reporting

## License

MIT
