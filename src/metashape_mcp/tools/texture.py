"""Texturing tools: UV mapping, texture generation, color calibration."""

from metashape_mcp.utils.bridge import auto_save, get_chunk, require_model
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import make_tracking_callback


def register(mcp) -> None:
    """Register texturing tools."""

    @mcp.tool()
    def build_uv(
        mapping_mode: str = "generic",
        page_count: int = 1,
        texture_size: int = 8192,
    ) -> dict:
        """Generate UV mapping for the 3D model.

        Must be run before build_texture. UV mapping determines how the
        2D texture wraps around the 3D geometry.

        Args:
            mapping_mode: "generic", "orthophoto", "adaptive_orthophoto",
                         "spherical", or "camera".
            page_count: Number of texture atlas pages.
            texture_size: Expected texture size (guides UV packing density).

        Returns:
            UV mapping confirmation.
        """
        chunk = get_chunk()
        require_model(chunk)

        mode = resolve_enum("mapping_mode", mapping_mode)
        cb = make_tracking_callback("Building UV map")

        chunk.buildUV(
            mapping_mode=mode,
            page_count=page_count,
            texture_size=texture_size,
            progress=cb,
        )

        auto_save()
        return {
            "status": "uv_built",
            "mapping_mode": mapping_mode,
            "page_count": page_count,
        }

    @mcp.tool()
    def build_texture(
        blending_mode: str = "natural",
        texture_size: int = 8192,
        ghosting_filter: bool = True,
        fill_holes: bool = True,
    ) -> dict:
        """Generate texture atlas for the 3D model.

        Requires UV mapping (run build_uv first). Projects camera images
        onto the model surface to create the texture.

        Args:
            blending_mode: "natural" (default), "mosaic", "average", "min", "max", "disabled".
            texture_size: Texture page size in pixels.
            ghosting_filter: Filter ghosting artifacts from moving objects.
            fill_holes: Fill holes in the texture.

        Returns:
            Texture generation results.
        """
        chunk = get_chunk()
        require_model(chunk)

        if chunk.model.tex_vertices is None or len(chunk.model.tex_vertices) == 0:
            raise RuntimeError(
                "No UV mapping found. Run 'build_uv' first."
            )

        blend = resolve_enum("blending_mode", blending_mode)
        cb = make_tracking_callback("Building texture")

        chunk.buildTexture(
            blending_mode=blend,
            texture_size=texture_size,
            ghosting_filter=ghosting_filter,
            fill_holes=fill_holes,
            progress=cb,
        )

        auto_save()
        return {
            "status": "texture_built",
            "texture_size": texture_size,
            "blending_mode": blending_mode,
        }

    @mcp.tool()
    def calibrate_colors(
        white_balance: bool = False,
    ) -> dict:
        """Perform radiometric color calibration across cameras.

        Normalizes color and brightness differences between photos for
        more uniform textures and orthomosaics.

        Args:
            white_balance: Also calibrate white balance.

        Returns:
            Calibration confirmation.
        """
        chunk = get_chunk()

        cb = make_tracking_callback("Calibrating colors")

        chunk.calibrateColors(
            white_balance=white_balance,
            progress=cb,
        )

        return {"status": "colors_calibrated", "white_balance": white_balance}

    @mcp.tool()
    def calibrate_reflectance(
        use_panels: bool = True,
        use_sun_sensor: bool = False,
    ) -> dict:
        """Calibrate reflectance using panels and/or sun sensor.

        Used in multispectral workflows for absolute reflectance values.

        Args:
            use_panels: Use calibrated reflectance panels.
            use_sun_sensor: Apply irradiance sensor measurements.

        Returns:
            Calibration confirmation.
        """
        chunk = get_chunk()

        cb = make_tracking_callback("Calibrating reflectance")

        chunk.calibrateReflectance(
            use_reflectance_panels=use_panels,
            use_sun_sensor=use_sun_sensor,
            progress=cb,
        )

        return {
            "status": "reflectance_calibrated",
            "panels": use_panels,
            "sun_sensor": use_sun_sensor,
        }

    @mcp.tool()
    def remove_texture() -> dict:
        """Remove texture from the model but keep the mesh geometry.

        Returns:
            Confirmation that the texture was removed.
        """
        chunk = get_chunk()
        require_model(chunk)
        chunk.model.removeTexture()
        return {"status": "texture_removed"}
