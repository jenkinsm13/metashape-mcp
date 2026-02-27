---
name: usgs-lidar-dem
description: Download USGS 3DEP LiDAR DEM data, colorize with satellite imagery, and import into Metashape as laser scan ground truth. Use when extending photogrammetry environments with surrounding terrain.
---

# USGS LiDAR DEM Acquisition & Satellite Colorization

## Overview

Download USGS 3DEP 1m LiDAR-derived DEM data for any US location, colorize points with ESRI World Imagery satellite tiles, and produce a CRS-tagged LAS file ready for Metashape import as a laser scan. This extends photogrammetry coverage with bare-earth ground truth beyond the camera footprint.

## When to Use

- Photogrammetry project needs terrain beyond the scanned corridor
- Need bare-earth ground truth under vegetation/canopy
- Building game environments (AC tracks, etc.) that need surrounding terrain
- DEM data needed as elevation reference for alignment QA

## Prerequisites

Python packages (install via pip):
```
pip install rasterio laspy numpy requests Pillow
```

Optional for programmatic DEM download:
```
pip install py3dep
```

## Pipeline Overview

```
1. Determine project bounds (from Metashape markers/cameras or manual bbox)
2. Find & download USGS 3DEP DEM GeoTIFF tiles (TNM API or py3dep)
3. Download ESRI World Imagery satellite tiles for the same extent
4. Mosaic DEM tiles, grid to points, sample satellite RGB at each point
5. Write LAS file (format 2 = RGB, classification=2=Ground, CRS VLR)
6. Import into Metashape chunk with is_laser_scan=True
7. Apply vertical datum correction (NAVD88 -> WGS84 ellipsoidal)
8. Verify alignment against photogrammetry
```

## Step 1: Determine Project Bounds

Get the geographic extent from Metashape. Use marker positions or camera bounding box.

```python
# Via Metashape MCP
markers = list_markers()  # returns lon/lat/alt for each marker
cameras = get_alignment_stats()  # returns camera count and bounds

# Or specify manually as (west, south, east, north) in WGS84 geographic
bbox = (-122.58, 37.88, -122.54, 37.93)  # Fisheye Loop example
```

Determine the UTM zone from longitude:
- Zone = floor((lon + 180) / 6) + 1
- For lon -122.5: Zone 10
- NAD83 UTM EPSG codes: 269xx where xx = zone (e.g., EPSG:26910 for Zone 10N)

## Step 2: Download USGS 3DEP DEM Tiles

### Option A: TNM API (direct tile download)

Query the USGS National Map API for available 1m DEM tiles:

```python
import requests

bbox = "-122.58,37.88,-122.54,37.93"  # west,south,east,north
url = "https://tnmaccess.nationalmap.gov/api/v1/products"
params = {
    "bbox": bbox,
    "datasets": "Digital Elevation Model (DEM) 1 meter",
    "prodFormats": "GeoTIFF",
    "max": 50
}
resp = requests.get(url, params=params)
items = resp.json().get("items", [])

for item in items:
    title = item["title"]
    download_url = item["downloadURL"]
    size_mb = item.get("sizeInBytes", 0) / 1e6
    print(f"{title}: {size_mb:.0f}MB -> {download_url}")
```

Download each tile:
```python
import os

out_dir = "path/to/dem_tiles"
os.makedirs(out_dir, exist_ok=True)

for item in items:
    fname = item["downloadURL"].split("/")[-1]
    out_path = os.path.join(out_dir, fname)
    if os.path.exists(out_path):
        continue
    print(f"Downloading {fname}...")
    r = requests.get(item["downloadURL"], stream=True)
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
```

### Option B: py3dep (programmatic, auto-mosaics)

```python
import py3dep
from shapely.geometry import box

# Define area of interest
bbox = box(-122.58, 37.88, -122.54, 37.93)  # (minx, miny, maxx, maxy)

# Download 10m DEM (fast, from static service)
dem_10m = py3dep.get_dem(bbox, resolution=10, geo_crs=4326, crs=5070)
dem_10m.rio.to_raster("dem_10m.tif")

# For 1m resolution, use dynamic service (slower, larger)
dem_1m = py3dep.get_dem(bbox, resolution=1, geo_crs=4326, crs=5070)
dem_1m.rio.to_raster("dem_1m.tif")
```

Note: py3dep output CRS is limited to EPSG:4326, 3857, or 5070. For UTM output, reproject afterward with rasterio.

### Tile naming convention

USGS 3DEP tiles are named by their grid position. Example: `USGS_1M_10_x54y42.tif` where 10 = UTM zone, x54y42 = grid cell. The TNM API returns the actual filenames.

## Step 3: Download Satellite Imagery (ESRI World Imagery)

ESRI World Imagery provides free satellite/aerial tiles at up to ~0.3m resolution in urban areas.

Tile URL template:
```
https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}
```

### Calculate tile coordinates from geographic bounds

```python
import math

def latlon_to_tile(lat, lon, zoom):
    """Convert lat/lon to tile x,y at given zoom level."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def download_satellite_tiles(bbox, zoom, out_dir):
    """Download all ESRI World Imagery tiles covering a bounding box.

    Args:
        bbox: (west, south, east, north) in WGS84 degrees
        zoom: Tile zoom level (17-18 recommended, 19 max)
        out_dir: Directory to save tiles

    Returns:
        List of (tile_x, tile_y, filepath) tuples
    """
    import requests, os, time
    os.makedirs(out_dir, exist_ok=True)

    west, south, east, north = bbox
    x_min, y_min = latlon_to_tile(north, west, zoom)  # Note: y is inverted
    x_max, y_max = latlon_to_tile(south, east, zoom)

    tiles = []
    base = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile"

    for ty in range(y_min, y_max + 1):
        for tx in range(x_min, x_max + 1):
            fname = f"tile_{zoom}_{tx}_{ty}.jpg"
            fpath = os.path.join(out_dir, fname)
            if not os.path.exists(fpath):
                url = f"{base}/{zoom}/{ty}/{tx}"
                r = requests.get(url)
                if r.status_code == 200:
                    with open(fpath, "wb") as f:
                        f.write(r.content)
                time.sleep(0.05)  # Be polite to the server
            tiles.append((tx, ty, fpath))

    print(f"Downloaded {len(tiles)} tiles at zoom {zoom}")
    return tiles
```

### Stitch tiles into a single georeferenced image

```python
from PIL import Image
import numpy as np

def stitch_satellite(tiles, zoom, out_path):
    """Stitch satellite tiles into a single image with geographic bounds.

    Returns:
        (image_array, bounds) where bounds = (west, south, east, north) in degrees
    """
    if not tiles:
        raise ValueError("No tiles to stitch")

    xs = [t[0] for t in tiles]
    ys = [t[1] for t in tiles]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Load one tile to get dimensions
    sample = Image.open(tiles[0][2])
    tw, th = sample.size  # typically 256x256

    # Create stitched image
    width = (x_max - x_min + 1) * tw
    height = (y_max - y_min + 1) * th
    stitched = Image.new("RGB", (width, height))

    for tx, ty, fpath in tiles:
        tile_img = Image.open(fpath)
        px = (tx - x_min) * tw
        py = (ty - y_min) * th
        stitched.paste(tile_img, (px, py))

    stitched.save(out_path)

    # Compute geographic bounds of stitched image
    n = 2 ** zoom
    west = x_min / n * 360.0 - 180.0
    east = (x_max + 1) / n * 360.0 - 180.0
    north_rad = math.atan(math.sinh(math.pi * (1 - 2 * y_min / n)))
    south_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y_max + 1) / n)))
    north = math.degrees(north_rad)
    south = math.degrees(south_rad)

    img_array = np.array(stitched)
    bounds = (west, south, east, north)
    print(f"Stitched: {width}x{height}px, bounds: {bounds}")
    return img_array, bounds
```

### Zoom level guide

| Zoom | ~Resolution | Use case |
|------|------------|----------|
| 15 | ~5m/px | Large area overview |
| 17 | ~1.2m/px | Good for 2m DEM coloring |
| 18 | ~0.6m/px | Good for 1m DEM coloring |
| 19 | ~0.3m/px | Maximum detail (not available everywhere) |

Match zoom to DEM resolution: for 2m DEM use zoom 17-18, for 1m DEM use zoom 18-19.

## Step 4: Convert DEM to Satellite-Colored LAS

This is the core pipeline — read DEM GeoTIFFs, grid to points, sample satellite RGB, write LAS.

```python
"""
Convert USGS 3DEP DEM GeoTIFFs to satellite-colored LAS point cloud.
Produces a CRS-tagged LAS file ready for Metashape import.
"""
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.transform import rowcol
import laspy
import os
import time
from PIL import Image
import math

# === CONFIGURATION ===
DEM_FILES = ["tile1.tif", "tile2.tif"]  # Downloaded USGS 3DEP GeoTIFFs
SATELLITE_IMG = "satellite_stitched.png"  # From Step 3
SAT_BOUNDS = (-122.58, 37.88, -122.54, 37.93)  # (west, south, east, north)
OUTPUT_LAS = "dem_ground_2m_colored.las"
RESOLUTION = 2.0  # meters — output point spacing
CRS_EPSG = 26910  # NAD83 / UTM Zone 10N (match your DEM tiles)

# Crop bounds in UTM (generous buffer around project area)
CROP = {
    "e_min": 541500, "e_max": 543500,
    "n_min": 4194000, "n_max": 4196500
}

def utm_to_latlon(easting, northing, zone=10, north=True):
    """Approximate UTM to WGS84 conversion for satellite sampling."""
    # For precise work, use pyproj. This is adequate for tile lookups.
    import pyproj
    utm_crs = pyproj.CRS(f"EPSG:{26900 + zone}")
    wgs84 = pyproj.CRS("EPSG:4326")
    transformer = pyproj.Transformer.from_crs(utm_crs, wgs84, always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return lat, lon

def sample_satellite_rgb(sat_img, sat_bounds, lats, lons):
    """Sample RGB from satellite image at given lat/lon positions.

    Args:
        sat_img: numpy array (H, W, 3) uint8
        sat_bounds: (west, south, east, north) in degrees
        lats, lons: arrays of positions to sample

    Returns:
        (red, green, blue) arrays, each uint16 (0-65535 for LAS)
    """
    west, south, east, north = sat_bounds
    h, w = sat_img.shape[:2]

    # Normalize positions to pixel coordinates
    px = ((lons - west) / (east - west) * w).astype(np.int32).clip(0, w - 1)
    py = ((north - lats) / (north - south) * h).astype(np.int32).clip(0, h - 1)

    r = sat_img[py, px, 0].astype(np.uint16) * 256  # 8-bit -> 16-bit for LAS
    g = sat_img[py, px, 1].astype(np.uint16) * 256
    b = sat_img[py, px, 2].astype(np.uint16) * 256

    return r, g, b

def make_colored_las():
    t0 = time.time()

    # --- Read and mosaic DEM ---
    print("Reading DEM tiles...")
    datasets = [rasterio.open(f) for f in DEM_FILES]
    mosaic, transform = merge(
        datasets,
        bounds=(CROP["e_min"], CROP["n_min"], CROP["e_max"], CROP["n_max"]),
        res=RESOLUTION,
        nodata=-999999.0
    )
    crs = datasets[0].crs
    for ds in datasets:
        ds.close()

    dem = mosaic[0]
    rows, cols = dem.shape
    valid = dem > -999000
    print(f"Grid: {cols}x{rows}, valid: {valid.sum():,} points")

    # --- Create UTM coordinate arrays ---
    col_idx, row_idx = np.meshgrid(np.arange(cols), np.arange(rows))
    utm_e = CROP["e_min"] + (col_idx + 0.5) * RESOLUTION
    utm_n = CROP["n_max"] - (row_idx + 0.5) * RESOLUTION

    x = utm_e[valid].astype(np.float64)
    y = utm_n[valid].astype(np.float64)
    z = dem[valid].astype(np.float64)

    print(f"X: {x.min():.1f} - {x.max():.1f}")
    print(f"Y: {y.min():.1f} - {y.max():.1f}")
    print(f"Z: {z.min():.1f} - {z.max():.1f}")

    # --- Sample satellite RGB ---
    print("Sampling satellite colors...")
    sat_img = np.array(Image.open(SATELLITE_IMG))

    # Convert UTM to lat/lon for satellite sampling
    import pyproj
    utm_crs = pyproj.CRS(f"EPSG:{CRS_EPSG}")
    wgs84 = pyproj.CRS("EPSG:4326")
    transformer = pyproj.Transformer.from_crs(utm_crs, wgs84, always_xy=True)
    lons, lats = transformer.transform(x, y)

    red, green, blue = sample_satellite_rgb(sat_img, SAT_BOUNDS, lats, lons)

    # --- Write LAS with RGB ---
    print("Writing LAS...")
    header = laspy.LasHeader(point_format=2, version="1.2")  # Format 2 = XYZ + RGB
    header.scales = [0.001, 0.001, 0.001]  # mm precision
    header.offsets = [np.floor(x.min()), np.floor(y.min()), np.floor(z.min())]

    las = laspy.LasData(header)
    las.x = x
    las.y = y
    las.z = z
    las.red = red
    las.green = green
    las.blue = blue
    las.classification = np.full(len(x), 2, dtype=np.uint8)  # Ground
    las.return_number = np.ones(len(x), dtype=np.uint8)
    las.number_of_returns = np.ones(len(x), dtype=np.uint8)

    las.write(OUTPUT_LAS)

    size_mb = os.path.getsize(OUTPUT_LAS) / 1e6
    elapsed = time.time() - t0
    print(f"\nResult: {len(x):,} points, {size_mb:.1f}MB, {elapsed:.1f}s")
    print(f"CRS: EPSG:{CRS_EPSG}")

make_colored_las()
```

### CRS VLR for Metashape compatibility

The above laspy code writes basic LAS. For Metashape to auto-detect CRS, add a GeoTIFF GeoKeys VLR:

```python
import struct

def add_crs_vlr(las, epsg_code):
    """Add GeoTIFF GeoKeys VLR for CRS identification."""
    # GeoKeyDirectoryTag: version=1, revision=1, minor=0, numKeys=3
    # GTModelTypeGeoKey (1024) = ProjectedCRS (1)
    # GTRasterTypeGeoKey (1025) = PixelIsArea (1)
    # ProjectedCSTypeGeoKey (3072) = epsg_code
    geo_keys = struct.pack('<16H',
        1, 1, 0, 3,             # version, revision, minor, numKeys
        1024, 0, 1, 1,          # GTModelTypeGeoKey = Projected
        1025, 0, 1, 1,          # GTRasterTypeGeoKey = PixelIsArea
        3072, 0, 1, epsg_code   # ProjectedCSTypeGeoKey
    )
    vlr = laspy.VLR(
        user_id="LASF_Projection",
        record_id=34735,
        description="GeoTiff GeoKeyDirectoryTag",
        record_data=geo_keys
    )
    las.vlrs.append(vlr)
```

Call `add_crs_vlr(las, 26910)` before `las.write()`.

## Step 5: Import into Metashape

Import the colored LAS as a laser scan into the **same chunk** as aligned cameras. NEVER import into a separate chunk.

```
# Via Metashape MCP
import_point_cloud(
    path="path/to/dem_ground_2m_colored.las",
    crs_epsg=26910,
    is_laser_scan=True
)
```

The `is_laser_scan=True` flag tells Metashape to:
- Treat points as ground-truth surface measurements
- Use them as constraints during mesh generation
- Display them separately from photogrammetry point clouds

## Step 6: Vertical Datum Correction

### The Problem

USGS 3DEP DEMs use **NAVD88** vertical datum (roughly orthometric/geoid height). Metashape photogrammetry uses **WGS84 ellipsoidal** height. The difference (geoid undulation) varies by location:

| Location | Approx offset (ellipsoidal - NAVD88) |
|----------|--------------------------------------|
| Southern California (34N) | ~-36m |
| Northern California (38N) | ~-32m |
| Colorado (39N) | ~-17m |
| East Coast (40N) | ~-33m |

The sign and magnitude depend on the specific geoid model and location. **Always measure empirically.**

### Measuring the Offset

Compare Metashape marker elevations (ellipsoidal) vs DEM elevation (NAVD88) at the same XY position:

```python
# Sample DEM at marker locations
import rasterio
from pyproj import Transformer

# Read marker positions from Metashape (WGS84 lon/lat/ellipsoidal_alt)
markers = [
    {"name": "point 1", "lon": -122.55, "lat": 37.90, "alt_ellipsoidal": 45.2},
    # ... more markers
]

# Transform marker positions to DEM CRS (UTM)
t = Transformer.from_crs("EPSG:4326", f"EPSG:{CRS_EPSG}", always_xy=True)

with rasterio.open(DEM_FILES[0]) as src:
    for m in markers:
        utm_e, utm_n = t.transform(m["lon"], m["lat"])
        row, col = src.index(utm_e, utm_n)
        dem_z = src.read(1)[row, col]
        offset = m["alt_ellipsoidal"] - dem_z
        print(f"{m['name']}: Metashape={m['alt_ellipsoidal']:.2f}, DEM={dem_z:.2f}, offset={offset:.2f}m")
```

The offset should be consistent across markers (within ~0.5m). Use the mean.

### Applying the Correction in Metashape

Shift the imported point cloud in ECEF space:

```python
import Metashape

chunk = Metashape.app.document.chunk
crs_wgs = Metashape.CoordinateSystem("EPSG::4326")
crs_ecef = Metashape.CoordinateSystem("EPSG::4978")

# Use project center and measured offset
VERTICAL_SHIFT = -32.11  # meters, measured for this location
ref_lon, ref_lat, ref_alt = -122.55, 37.90, 50.0  # approximate project center

ref = Metashape.Vector([ref_lon, ref_lat, ref_alt])
ref_shifted = Metashape.Vector([ref_lon, ref_lat, ref_alt + VERTICAL_SHIFT])

pt_orig = Metashape.CoordinateSystem.transform(ref, crs_wgs, crs_ecef)
pt_shifted = Metashape.CoordinateSystem.transform(ref_shifted, crs_wgs, crs_ecef)

# Apply to imported laser scan point cloud
# chunk.point_clouds is a list; index 0 = photogrammetry dense cloud, last = imported
pc = chunk.point_clouds[-1]  # the imported laser scan
T = pc.transform

T_new = Metashape.Matrix([
    [T[0,0], T[0,1], T[0,2], T[0,3] + (pt_shifted.x - pt_orig.x)],
    [T[1,0], T[1,1], T[1,2], T[1,3] + (pt_shifted.y - pt_orig.y)],
    [T[2,0], T[2,1], T[2,2], T[2,3] + (pt_shifted.z - pt_orig.z)],
    [0.0, 0.0, 0.0, 1.0]
])
pc.transform = T_new
```

**Important**: Save the original transform before shifting. Always compute shift from original, never incrementally.

### Alternative: Pre-shift Z in the LAS

Instead of shifting in Metashape, apply the offset when creating the LAS:

```python
# In Step 4, after reading DEM Z values:
GEOID_OFFSET = -32.11  # NAVD88 to WGS84 ellipsoidal
z = dem[valid].astype(np.float64) - GEOID_OFFSET  # shift before writing LAS
```

This is simpler but requires knowing the offset before import.

## Step 7: Verify Alignment

After import and datum correction, verify:

1. **Road surface**: DEM points should sit at road elevation (some slightly above/below is OK)
2. **Hillsides**: DEM bare-earth should align with photogrammetry terrain surfaces
3. **Vegetation areas**: DEM should be BELOW tree canopy (it's bare-earth)
4. **Z residuals**: Sample Metashape tie points vs DEM at same position, check stddev < 1m

## Vertical Datum Reference

| Datum | Description | Used by |
|-------|-------------|---------|
| NAVD88 | North American Vertical Datum 1988 (orthometric) | USGS 3DEP DEM |
| EGM96 | Earth Gravitational Model 1996 (geoid) | Some LiDAR point clouds |
| EGM2008 | Earth Gravitational Model 2008 (geoid) | Newer LiDAR products |
| WGS84 ellipsoid | Geometric reference surface | Metashape, GPS raw |

Conversion: `ellipsoidal_height = orthometric_height + geoid_undulation`

The geoid undulation (N) is always `N = h_ellipsoidal - H_orthometric`. In the US, N is typically negative (ellipsoid is below geoid), so ellipsoidal heights are LESS than orthometric.

Use [NGS GEOID tool](https://geodesy.noaa.gov/GEOID/) or `pyproj` to look up the exact undulation:

```python
from pyproj import Transformer
t = Transformer.from_crs("EPSG:26910+5703", "EPSG:26910+7912", always_xy=True)
# Transforms from NAD83/UTM10N + NAVD88 to NAD83/UTM10N + WGS84 ellipsoidal
```

## Troubleshooting

### "Null point cloud" after import
- The import succeeded but Metashape can't use it for operations like `classifyGroundPoints`
- This is expected for imported (non-photogrammetry) point clouds
- LiDAR data should already be classified; skip classification

### MemoryError on buildModel after import
- Metashape 2.3 bug with large imported point clouds
- Reduce point count: use 2m or 5m DEM resolution instead of 1m
- Or import only ground-classified points (class=2)

### Points import but don't align vertically
- This is the vertical datum issue (Step 6)
- ALWAYS measure the offset empirically; don't trust theoretical values alone

### LAS CRS not detected by Metashape
- Add the GeoTIFF GeoKeys VLR (see Step 4)
- Or specify `crs_epsg` explicitly in the import call

### Satellite tiles are blurry/low-res
- Try higher zoom level (18 or 19)
- Some rural areas only have low-res imagery; zoom 17 may be the max
- NAIP imagery (via USGS) is an alternative for US agricultural areas

### ESRI tiles returning 403/blank
- Rate limiting; add `time.sleep(0.1)` between requests
- Some zoom levels are restricted in certain areas
- Try zoom 17 instead of 19

## File Size Guide

| Resolution | 1km x 1km area | 5km x 5km area |
|-----------|----------------|----------------|
| 1m | 1M pts, ~25MB | 25M pts, ~625MB |
| 2m | 250K pts, ~6MB | 6.25M pts, ~156MB |
| 5m | 40K pts, ~1MB | 1M pts, ~25MB |

For Metashape import, 2m resolution is the sweet spot: enough detail for terrain mesh, small enough to not cause MemoryError.
