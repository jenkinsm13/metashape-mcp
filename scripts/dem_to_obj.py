"""Convert ground LiDAR CSV (EPSG:3857 PM) to terrain OBJ mesh."""
import numpy as np
import sys
import time

CSV_PATH = "B:/Fisheye Loop/lidar-gpx-etc/ground-pm-dec5.csv"
OBJ_PATH = "B:/Fisheye Loop/lidar-gpx-etc/terrain-2m.obj"
GRID_RES = 2.0  # meters per cell (ground distance)
FILL_RADIUS = 3  # cells — fill gaps within this distance of valid data
LAT_DEG = 37.905  # center latitude for PM->ground meter conversion
GEOID_OFFSET = 32.11  # EGM96->WGS84 ellipsoidal: subtract from LiDAR Z to match Metashape

t0 = time.time()

# --- Read CSV (Pseudo-Mercator coordinates) ---
print("Reading CSV...")
data = np.loadtxt(CSV_PATH, delimiter=",", skiprows=1, dtype=np.float64)
pm_x, pm_y, z = data[:, 0], data[:, 1], data[:, 2]

# Convert PM to approximate ground meters (centered)
cos_lat = np.cos(np.radians(LAT_DEG))
pm_cx = (pm_x.min() + pm_x.max()) / 2
pm_cy = (pm_y.min() + pm_y.max()) / 2
x = (pm_x - pm_cx) * cos_lat  # ground meters, centered
y = (pm_y - pm_cy) * cos_lat  # ground meters, centered

print(f"  {len(x):,} points in {time.time()-t0:.1f}s")
print(f"  PM center: X={pm_cx:.2f} Y={pm_cy:.2f}")
print(f"  cos(lat): {cos_lat:.6f}")
print(f"  X: {x.min():.1f} to {x.max():.1f} ({x.max()-x.min():.0f}m)")
print(f"  Y: {y.min():.1f} to {y.max():.1f} ({y.max()-y.min():.0f}m)")
print(f"  Z: {z.min():.1f} to {z.max():.1f}m")

# --- Grid into DEM ---
print(f"Gridding at {GRID_RES}m resolution...")
x_min, x_max = x.min(), x.max()
y_min, y_max = y.min(), y.max()

nx = int(np.ceil((x_max - x_min) / GRID_RES)) + 1
ny = int(np.ceil((y_max - y_min) / GRID_RES)) + 1

ix = ((x - x_min) / GRID_RES).astype(np.int32).clip(0, nx - 1)
iy = ((y - y_min) / GRID_RES).astype(np.int32).clip(0, ny - 1)

dem_sum = np.zeros((ny, nx), dtype=np.float64)
dem_cnt = np.zeros((ny, nx), dtype=np.int32)

# Shift LiDAR Z from EGM96 geoid to WGS84 ellipsoidal to match Metashape
z_shifted = z - GEOID_OFFSET
np.add.at(dem_sum, (iy, ix), z_shifted)
np.add.at(dem_cnt, (iy, ix), 1)

valid = dem_cnt > 0
dem = np.full((ny, nx), np.nan, dtype=np.float32)
dem[valid] = (dem_sum[valid] / dem_cnt[valid]).astype(np.float32)

n_valid = valid.sum()
print(f"  Grid: {nx} x {ny} = {nx*ny:,} cells")
print(f"  Valid: {n_valid:,} ({100*n_valid/(nx*ny):.1f}%)")

# --- Fill small gaps ---
print("Filling gaps...")
from scipy.ndimage import distance_transform_edt

invalid = ~valid
if invalid.any():
    dist, idx = distance_transform_edt(invalid, return_distances=True, return_indices=True)
    fill_mask = invalid & (dist <= FILL_RADIUS)
    dem[fill_mask] = dem[idx[0][fill_mask], idx[1][fill_mask]]
    valid = ~np.isnan(dem)
    print(f"  After fill: {valid.sum():,} ({100*valid.sum()/(nx*ny):.1f}%)")

# --- Write OBJ ---
print("Writing OBJ mesh...")

# Build vertex index map (coords already centered)
vert_idx = np.full((ny, nx), -1, dtype=np.int32)
vert_idx[valid] = np.arange(valid.sum()) + 1

with open(OBJ_PATH, "w") as f:
    f.write(f"# LiDAR terrain mesh - {GRID_RES}m grid\n")
    f.write(f"# Source: EPSG:3857 PM center X={pm_cx:.2f} Y={pm_cy:.2f}\n")
    f.write(f"# Approx lat: {LAT_DEG}, cos(lat): {cos_lat:.6f}\n")
    f.write(f"# Geoid offset: -{GEOID_OFFSET}m (EGM96 to WGS84 ellipsoidal)\n")
    f.write(f"# Coords: local meters, Y-up, centered, matches Metashape export\n\n")

    # Vertices: OBJ Y-up. Map ground_E->X, elev->Y, ground_N->-Z
    for row in range(ny):
        for col in range(nx):
            if valid[row, col]:
                vx = x_min + col * GRID_RES
                vy = float(dem[row, col])
                vz = -(y_min + row * GRID_RES)
                f.write(f"v {vx:.3f} {vy:.3f} {vz:.3f}\n")

    # Faces: triangulate grid quads
    n_faces = 0
    for row in range(ny - 1):
        for col in range(nx - 1):
            v00 = vert_idx[row, col]
            v10 = vert_idx[row + 1, col]
            v01 = vert_idx[row, col + 1]
            v11 = vert_idx[row + 1, col + 1]
            if v00 > 0 and v10 > 0 and v01 > 0 and v11 > 0:
                f.write(f"f {v00} {v10} {v11}\n")
                f.write(f"f {v00} {v11} {v01}\n")
                n_faces += 2

import os
file_mb = os.path.getsize(OBJ_PATH) / 1e6

print(f"\nResult:")
print(f"  Vertices: {valid.sum():,}")
print(f"  Faces: {n_faces:,}")
print(f"  File: {OBJ_PATH} ({file_mb:.1f} MB)")
print(f"  Time: {time.time()-t0:.1f}s")
print(f"\n  PM center: X={pm_cx:.2f} Y={pm_cy:.2f}")
print(f"  Ground extent: {x.max()-x.min():.0f}m E-W x {y.max()-y.min():.0f}m N-S")
