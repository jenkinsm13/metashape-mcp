"""String-to-Metashape enum mapping.

LLMs send string parameter values. This module maps human-readable strings
to the corresponding Metashape enum values with clear error messages.
"""

from typing import Any

import Metashape

# Each category maps lowercase strings to Metashape enum values.
_ENUM_MAP = {
    "filter_mode": {
        "none": Metashape.NoFiltering,
        "mild": Metashape.MildFiltering,
        "moderate": Metashape.ModerateFiltering,
        "aggressive": Metashape.AggressiveFiltering,
    },
    "surface_type": {
        "arbitrary": Metashape.Arbitrary,
        "height_field": Metashape.HeightField,
    },
    "interpolation": {
        "disabled": Metashape.DisabledInterpolation,
        "enabled": Metashape.EnabledInterpolation,
        "extrapolated": Metashape.Extrapolated,
    },
    "face_count": {
        "low": Metashape.LowFaceCount,
        "medium": Metashape.MediumFaceCount,
        "high": Metashape.HighFaceCount,
        "custom": Metashape.CustomFaceCount,
    },
    "blending_mode": {
        "average": Metashape.AverageBlending,
        "mosaic": Metashape.MosaicBlending,
        "natural": Metashape.NaturalBlending,
        "min": Metashape.MinBlending,
        "max": Metashape.MaxBlending,
        "disabled": Metashape.DisabledBlending,
    },
    "mapping_mode": {
        "generic": Metashape.GenericMapping,
        "orthophoto": Metashape.OrthophotoMapping,
        "adaptive_orthophoto": Metashape.AdaptiveOrthophotoMapping,
        "spherical": Metashape.SphericalMapping,
        "camera": Metashape.CameraMapping,
    },
    "data_source": {
        "tie_points": Metashape.TiePointsData,
        "point_cloud": Metashape.PointCloudData,
        "model": Metashape.ModelData,
        "tiled_model": Metashape.TiledModelData,
        "elevation": Metashape.ElevationData,
        "orthomosaic": Metashape.OrthomosaicData,
        "depth_maps": Metashape.DepthMapsData,
        "depth_maps_and_laser_scans": Metashape.DepthMapsAndLaserScansData,
        "images": Metashape.ImagesData,
        "laser_scans": Metashape.LaserScansData,
    },
    "target_type": {
        "circular_12bit": Metashape.CircularTarget12bit,
        "circular_14bit": Metashape.CircularTarget14bit,
        "circular_16bit": Metashape.CircularTarget16bit,
        "circular_20bit": Metashape.CircularTarget20bit,
        "circular": Metashape.CircularTarget,
        "cross": Metashape.CrossTarget,
    },
    "model_format": {
        "obj": Metashape.ModelFormatOBJ,
        "3ds": Metashape.ModelFormat3DS,
        "ply": Metashape.ModelFormatPLY,
        "collada": Metashape.ModelFormatCOLLADA,
        "fbx": Metashape.ModelFormatFBX,
        "stl": Metashape.ModelFormatSTL,
        "gltf": Metashape.ModelFormatGLTF,
        "dxf": Metashape.ModelFormatDXF,
        "kmz": Metashape.ModelFormatKMZ,
    },
    "point_cloud_format": {
        "las": Metashape.PointCloudFormatLAS,
        "laz": Metashape.PointCloudFormatLAZ,
        "ply": Metashape.PointCloudFormatPLY,
        "xyz": Metashape.PointCloudFormatXYZ,
        "e57": Metashape.PointCloudFormatE57,
        "obj": Metashape.PointCloudFormatOBJ,
        "cesium": Metashape.PointCloudFormatCesium,
        "pcd": Metashape.PointCloudFormatPCD,
        "copc": Metashape.PointCloudFormatCOPC,
    },
    "raster_format": {
        "tif": Metashape.RasterFormatTiles,
        "kmz": Metashape.RasterFormatKMZ,
        "xyz": Metashape.RasterFormatXYZ,
        "mbtiles": Metashape.RasterFormatMBTiles,
        "geopackage": Metashape.RasterFormatGeoPackage,
    },
    "tiled_model_format": {
        "cesium": Metashape.TiledModelFormatCesium,
        "zip": Metashape.TiledModelFormatZIP,
        "3mx": Metashape.TiledModelFormat3MX,
        "slpk": Metashape.TiledModelFormatSLPK,
    },
    "cameras_format": {
        "xml": Metashape.CamerasFormatXML,
        "bundler": Metashape.CamerasFormatBundler,
        "chan": Metashape.CamerasFormatCHAN,
        "opk": Metashape.CamerasFormatOPK,
        "colmap": Metashape.CamerasFormatColmap,
        "fbx": Metashape.CamerasFormatFBX,
    },
    "shapes_format": {
        "shp": Metashape.ShapesFormatSHP,
        "kml": Metashape.ShapesFormatKML,
        "dxf": Metashape.ShapesFormatDXF,
        "geojson": Metashape.ShapesFormatGeoJSON,
        "geopackage": Metashape.ShapesFormatGeoPackage,
        "csv": Metashape.ShapesFormatCSV,
    },
    "reference_format": {
        "csv": Metashape.ReferenceFormatCSV,
        "xml": Metashape.ReferenceFormatXML,
        "tel": Metashape.ReferenceFormatTEL,
    },
}


def resolve_enum(category: str, value: str) -> Any:
    """Convert a string value to its Metashape enum equivalent.

    Args:
        category: Enum category name (e.g., "filter_mode", "surface_type").
        value: Human-readable string (e.g., "mild", "arbitrary").

    Returns:
        The corresponding Metashape enum value.

    Raises:
        ValueError: If category or value is unknown.
    """
    if category not in _ENUM_MAP:
        raise ValueError(
            f"Unknown enum category '{category}'. "
            f"Available: {sorted(_ENUM_MAP.keys())}"
        )

    mapping = _ENUM_MAP[category]
    key = value.lower().strip()
    if key not in mapping:
        raise ValueError(
            f"Unknown {category} value '{value}'. "
            f"Available: {sorted(mapping.keys())}"
        )
    return mapping[key]
