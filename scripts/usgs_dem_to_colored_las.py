"""
Download USGS 3DEP DEM, colorize with ESRI World Imagery, write LAS for Metashape.

Produces a satellite-colored ground-truth point cloud ready for Metashape import
as a laser scan. Points are in UTM with RGB from aerial/satellite imagery.

Usage: python usgs_dem_to_colored_las.py
"""
import numpy as np
import math
import os
import time
import struct
import requests
from PIL import Image

# === CONFIGURATION ===
# Bounding box (west, south, east, north) in WGS84 degrees
BBOX = (-122.530, 37.891, -122.502, 37.917)

# Output
OUT_DIR = "B:/Fisheye Loop/lidar-gpx-etc"
DEM_TIF = os.path.join(OUT_DIR, "usgs_dem_1m.tif")  # already downloaded
LAS_OUT = os.path.join(OUT_DIR, "usgs_dem_2m_colored.las")

# DEM sampling resolution for point cloud (meters)
POINT_SPACING = 2.0

# Satellite imagery zoom level (17=~1.2m/px, 18=~0.6m/px)
SAT_ZOOM = 18

# UTM zone (auto-detected from bbox center longitude)
CENTER_LON = (BBOX[0] + BBOX[2]) / 2
CENTER_LAT = (BBOX[1] + BBOX[3]) / 2
UTM_ZONE = int((CENTER_LON + 180) / 6) + 1
CRS_EPSG = 26900 + UTM_ZONE  # NAD83 UTM (e.g., 26910 for zone 10N)

t0 = time.time()

# ---------------------------------------------------------------
# Step 1: Read DEM and reproject to UTM
# ---------------------------------------------------------------
print("Step 1: Reading DEM...")

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

# Reproject from EPSG:5070 (py3dep output) to UTM
with rasterio.open(DEM_TIF) as src:
    src_crs = src.crs
    dst_crs = f"EPSG:{CRS_EPSG}"

    transform, width, height = calculate_default_transform(
        src_crs, dst_crs, src.width, src.height, *src.bounds,
        resolution=POINT_SPACING
    )

    dem_utm = np.empty((height, width), dtype=np.float32)
    reproject(
        source=rasterio.band(src, 1),
        destination=dem_utm,
        src_transform=src.transform,
        src_crs=src_crs,
        dst_transform=transform,
        dst_crs=dst_crs,
        resampling=Resampling.bilinear,
        src_nodata=src.nodata,
        dst_nodata=-999999.0
    )

# Build UTM coordinate arrays
valid = dem_utm > -999000
rows, cols = dem_utm.shape

col_idx, row_idx = np.meshgrid(np.arange(cols), np.arange(rows))
# transform maps pixel -> UTM
utm_e = transform.c + (col_idx + 0.5) * transform.a
utm_n = transform.f + (row_idx + 0.5) * transform.e  # e is negative

x = utm_e[valid].astype(np.float64)
y = utm_n[valid].astype(np.float64)
z = dem_utm[valid].astype(np.float64)

print(f"  Grid: {cols}x{rows}, valid: {valid.sum():,} points")
print(f"  UTM E: {x.min():.1f} - {x.max():.1f}")
print(f"  UTM N: {y.min():.1f} - {y.max():.1f}")
print(f"  Z (NAVD88): {z.min():.1f} - {z.max():.1f}m")
print(f"  CRS: EPSG:{CRS_EPSG} ({time.time()-t0:.1f}s)")

# ---------------------------------------------------------------
# Step 2: Download ESRI World Imagery satellite tiles
# ---------------------------------------------------------------
print(f"\nStep 2: Downloading satellite tiles (zoom {SAT_ZOOM})...")

def latlon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    tx = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    ty = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return tx, ty

west, south, east, north = BBOX
tx_min, ty_min = latlon_to_tile(north, west, SAT_ZOOM)
tx_max, ty_max = latlon_to_tile(south, east, SAT_ZOOM)

tile_dir = os.path.join(OUT_DIR, f"sat_tiles_z{SAT_ZOOM}")
os.makedirs(tile_dir, exist_ok=True)

base_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile"
n_tiles = (tx_max - tx_min + 1) * (ty_max - ty_min + 1)
print(f"  Tiles: {tx_max-tx_min+1}x{ty_max-ty_min+1} = {n_tiles}")

downloaded = 0
for ty in range(ty_min, ty_max + 1):
    for tx in range(tx_min, tx_max + 1):
        fpath = os.path.join(tile_dir, f"{SAT_ZOOM}_{tx}_{ty}.jpg")
        if not os.path.exists(fpath):
            url = f"{base_url}/{SAT_ZOOM}/{ty}/{tx}"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with open(fpath, "wb") as f:
                    f.write(r.content)
                downloaded += 1
            time.sleep(0.05)

print(f"  Downloaded {downloaded} new tiles ({time.time()-t0:.1f}s)")

# ---------------------------------------------------------------
# Step 3: Stitch satellite tiles into single image
# ---------------------------------------------------------------
print("\nStep 3: Stitching satellite image...")

# Load first tile to get size
sample_path = os.path.join(tile_dir, f"{SAT_ZOOM}_{tx_min}_{ty_min}.jpg")
sample = Image.open(sample_path)
tw, th = sample.size

width_px = (tx_max - tx_min + 1) * tw
height_px = (ty_max - ty_min + 1) * th
stitched = Image.new("RGB", (width_px, height_px))

for ty in range(ty_min, ty_max + 1):
    for tx in range(tx_min, tx_max + 1):
        fpath = os.path.join(tile_dir, f"{SAT_ZOOM}_{tx}_{ty}.jpg")
        if os.path.exists(fpath):
            tile_img = Image.open(fpath)
            px = (tx - tx_min) * tw
            py = (ty - ty_min) * th
            stitched.paste(tile_img, (px, py))

# Compute geographic bounds of the stitched image
n_tiles_total = 2 ** SAT_ZOOM
sat_west = tx_min / n_tiles_total * 360.0 - 180.0
sat_east = (tx_max + 1) / n_tiles_total * 360.0 - 180.0
sat_north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty_min / n_tiles_total))))
sat_south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty_max + 1) / n_tiles_total))))

sat_img = np.array(stitched)
sat_path = os.path.join(OUT_DIR, "satellite_fisheye.png")
stitched.save(sat_path)
print(f"  Image: {width_px}x{height_px}px")
print(f"  Bounds: W={sat_west:.5f} S={sat_south:.5f} E={sat_east:.5f} N={sat_north:.5f}")
print(f"  Saved: {sat_path} ({time.time()-t0:.1f}s)")

# ---------------------------------------------------------------
# Step 4: Sample satellite RGB at each DEM point
# ---------------------------------------------------------------
print("\nStep 4: Sampling satellite colors at DEM points...")

# Convert UTM point positions to lat/lon for satellite sampling
from pyproj import Transformer
t_to_wgs = Transformer.from_crs(f"EPSG:{CRS_EPSG}", "EPSG:4326", always_xy=True)
lons, lats = t_to_wgs.transform(x, y)

# Sample satellite image
h_img, w_img = sat_img.shape[:2]
px = ((lons - sat_west) / (sat_east - sat_west) * w_img).astype(np.int32).clip(0, w_img - 1)
py = ((sat_north - lats) / (sat_north - sat_south) * h_img).astype(np.int32).clip(0, h_img - 1)

red = sat_img[py, px, 0].astype(np.uint16) * 256    # 8-bit -> 16-bit for LAS
green = sat_img[py, px, 1].astype(np.uint16) * 256
blue = sat_img[py, px, 2].astype(np.uint16) * 256

print(f"  Sampled {len(x):,} points ({time.time()-t0:.1f}s)")

# ---------------------------------------------------------------
# Step 5: Write LAS with RGB and CRS
# ---------------------------------------------------------------
print("\nStep 5: Writing colored LAS...")

import laspy

header = laspy.LasHeader(point_format=2, version="1.2")  # Format 2 = XYZ + RGB
header.scales = [0.001, 0.001, 0.001]  # mm precision
header.offsets = [np.floor(x.min()), np.floor(y.min()), np.floor(z.min())]

# Add CRS VLR (GeoTIFF GeoKeys) so Metashape auto-detects CRS
geo_keys = struct.pack('<16H',
    1, 1, 0, 3,               # version=1, revision=1, minor=0, numKeys=3
    1024, 0, 1, 1,            # GTModelTypeGeoKey = Projected
    1025, 0, 1, 1,            # GTRasterTypeGeoKey = PixelIsArea
    3072, 0, 1, CRS_EPSG      # ProjectedCSTypeGeoKey
)
vlr = laspy.VLR(
    user_id="LASF_Projection",
    record_id=34735,
    description="GeoTiff GeoKeyDirectoryTag",
    record_data=geo_keys
)
header.vlrs.append(vlr)

las = laspy.LasData(header)
las.x = x
las.y = y
las.z = z
las.red = red
las.green = green
las.blue = blue
las.classification = np.full(len(x), 2, dtype=np.uint8)  # Ground (2)
las.return_number = np.ones(len(x), dtype=np.uint8)
las.number_of_returns = np.ones(len(x), dtype=np.uint8)

las.write(LAS_OUT)

file_mb = os.path.getsize(LAS_OUT) / 1e6
elapsed = time.time() - t0

print(f"\n{'='*60}")
print(f"Result: {LAS_OUT}")
print(f"  Points: {len(x):,}")
print(f"  File size: {file_mb:.1f}MB")
print(f"  CRS: EPSG:{CRS_EPSG} (NAD83 / UTM Zone {UTM_ZONE}N)")
print(f"  Vertical datum: NAVD88")
print(f"  Z range: {z.min():.1f} - {z.max():.1f}m")
print(f"  Point spacing: {POINT_SPACING}m")
print(f"  RGB: satellite-colored (ESRI World Imagery zoom {SAT_ZOOM})")
print(f"  Classification: Ground (2)")
print(f"  Time: {elapsed:.1f}s")
print(f"{'='*60}")
print(f"\nNext: Import into Metashape with:")
print(f"  import_point_cloud(path='{LAS_OUT}', crs_epsg={CRS_EPSG}, is_laser_scan=True)")
