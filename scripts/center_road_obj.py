"""Center and scale the road mesh OBJ to match the LiDAR terrain OBJ."""
import time
import sys

INPUT = "B:/Fisheye Loop/Export/road-mesh-2M-pm.obj"
OUTPUT = "B:/Fisheye Loop/Export/road-mesh-2M-centered.obj"

# Must match the terrain mesh centering from dem_to_obj.py
PM_CX = -13638150.00
PM_CY = 4566127.58
COS_LAT = 0.789030  # cos(37.905°)

t0 = time.time()
n_verts = 0
n_faces = 0

print(f"Transforming {INPUT}...")
print(f"  PM center: ({PM_CX}, {PM_CY})")
print(f"  cos(lat): {COS_LAT}")

with open(INPUT, "r") as fin, open(OUTPUT, "w") as fout:
    fout.write("# Road photogrammetry mesh - centered to match LiDAR terrain\n")
    fout.write(f"# PM center: X={PM_CX} Y={PM_CY}, cos(lat)={COS_LAT}\n\n")

    for line in fin:
        if line.startswith("v "):
            parts = line.split()
            pm_x = float(parts[1])  # PM easting
            pm_y = float(parts[2])  # PM northing
            elev = float(parts[3])  # elevation (meters)

            # Transform to local meters, Y-up OBJ convention
            # Same transform as terrain: E->X, elev->Y, N->-Z
            local_x = (pm_x - PM_CX) * COS_LAT
            local_y = elev
            local_z = -(pm_y - PM_CY) * COS_LAT

            fout.write(f"v {local_x:.4f} {local_y:.4f} {local_z:.4f}\n")
            n_verts += 1
        elif line.startswith("vn "):
            parts = line.split()
            nx, ny, nz = float(parts[1]), float(parts[2]), float(parts[3])
            # Rotate normals same way: (nx, ny, nz) -> (nx*cos, nz, -ny*cos)
            # Actually normals just need axis swap: PM(x,y,z) -> OBJ(x,z,-y)
            fout.write(f"vn {nx:.6f} {nz:.6f} {-ny:.6f}\n")
        elif line.startswith("f "):
            fout.write(line)
            n_faces += 1
        else:
            fout.write(line)

import os
size_mb = os.path.getsize(OUTPUT) / 1e6

print(f"\nResult:")
print(f"  Vertices: {n_verts:,}")
print(f"  Faces: {n_faces:,}")
print(f"  File: {OUTPUT} ({size_mb:.1f} MB)")
print(f"  Time: {time.time()-t0:.1f}s")
