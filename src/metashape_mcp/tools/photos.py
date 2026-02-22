"""Photo management tools: add photos, analyze quality, import video."""

import glob as globmod
import os

from metashape_mcp.utils.bridge import get_chunk
from metashape_mcp.utils.progress import make_tracking_callback


def register(mcp) -> None:
    """Register photo management tools."""

    @mcp.tool()
    def add_photos(paths: list[str]) -> dict:
        """Add photos to the active chunk.

        Supports glob patterns (e.g., '/photos/*.jpg') and directories.

        Args:
            paths: List of file paths, glob patterns, or directories.

        Returns:
            Number of photos added and total camera count.
        """
        chunk = get_chunk()
        before = len(chunk.cameras)

        # Expand globs and directories
        files = []
        for p in paths:
            if "*" in p or "?" in p:
                files.extend(globmod.glob(p, recursive=True))
            elif os.path.isdir(p):
                for ext in (
                    "*.jpg", "*.jpeg", "*.png", "*.tif", "*.tiff",
                    "*.dng", "*.exr", "*.hdr",
                    "*.bmp", "*.ppm",
                ):
                    files.extend(globmod.glob(os.path.join(p, ext)))
                    files.extend(globmod.glob(os.path.join(p, ext.upper())))
            elif os.path.isfile(p):
                files.append(p)
            else:
                raise FileNotFoundError(f"Path not found: {p}")

        if not files:
            raise ValueError("No image files found in the provided paths.")

        cb = make_tracking_callback("Adding photos")
        chunk.addPhotos(files, progress=cb)

        added = len(chunk.cameras) - before
        return {"added": added, "total_cameras": len(chunk.cameras)}

    @mcp.tool()
    def analyze_images(filter_mask: bool = False) -> dict:
        """Estimate image quality for all cameras in the active chunk.

        Cameras with quality < 0.5 are considered blurry. Returns quality
        statistics and a list of low-quality cameras.

        Args:
            filter_mask: Constrain analysis to unmasked image regions.

        Returns:
            Quality statistics and list of cameras below threshold.
        """
        chunk = get_chunk()
        if not chunk.cameras:
            raise RuntimeError("No cameras in the active chunk.")

        cb = make_tracking_callback("Analyzing images")
        chunk.analyzeImages(filter_mask=filter_mask, progress=cb)

        qualities = []
        low_quality = []
        for cam in chunk.cameras:
            try:
                q = float(cam.meta["Image/Quality"])
            except (KeyError, TypeError):
                continue
            qualities.append(q)
            if q < 0.5:
                low_quality.append({"label": cam.label, "quality": q})

        avg_q = sum(qualities) / len(qualities) if qualities else 0
        return {
            "total_cameras": len(chunk.cameras),
            "analyzed": len(qualities),
            "average_quality": round(avg_q, 3),
            "low_quality_count": len(low_quality),
            "low_quality_cameras": low_quality,
        }

    @mcp.tool()
    def import_video(
        path: str,
        frame_step: str = "custom",
        custom_step: int = 1,
    ) -> dict:
        """Import frames from a video file.

        Args:
            path: Path to the video file.
            frame_step: Frame step type: "custom", "small", "medium", "large".
            custom_step: Every Nth frame when frame_step is "custom".

        Returns:
            Number of frames imported.
        """
        import Metashape

        if not os.path.exists(path):
            raise FileNotFoundError(f"Video file not found: {path}")

        chunk = get_chunk()
        before = len(chunk.cameras)

        step_map = {
            "custom": Metashape.CustomFrameStep,
            "small": Metashape.SmallFrameStep,
            "medium": Metashape.MediumFrameStep,
            "large": Metashape.LargeFrameStep,
        }
        step = step_map.get(frame_step.lower(), Metashape.CustomFrameStep)

        # Build output path for frames
        base = os.path.splitext(os.path.basename(path))[0]
        out_dir = os.path.join(os.path.dirname(path), f"{base}_frames")
        os.makedirs(out_dir, exist_ok=True)
        image_path = os.path.join(out_dir, "frame{filenum}.png")

        cb = make_tracking_callback("Importing video")
        chunk.importVideo(
            path=path,
            image_path=image_path,
            frame_step=step,
            custom_frame_step=custom_step,
            progress=cb,
        )

        added = len(chunk.cameras) - before
        return {"frames_imported": added, "output_dir": out_dir}

    @mcp.tool()
    def remove_cameras(
        labels: list[str] | None = None,
        quality_threshold: float | None = None,
    ) -> dict:
        """Remove cameras from the active chunk.

        Either provide specific labels or a quality threshold (removes
        cameras with quality below the threshold).

        Args:
            labels: List of camera labels to remove.
            quality_threshold: Remove cameras below this quality score.

        Returns:
            Number of cameras removed and remaining count.
        """
        chunk = get_chunk()
        to_remove = []

        if labels:
            label_set = set(labels)
            to_remove = [c for c in chunk.cameras if c.label in label_set]
        elif quality_threshold is not None:
            for cam in chunk.cameras:
                try:
                    q = float(cam.meta["Image/Quality"])
                except (KeyError, TypeError):
                    continue
                if q < quality_threshold:
                    to_remove.append(cam)
        else:
            raise ValueError(
                "Provide either 'labels' or 'quality_threshold'."
            )

        if to_remove:
            chunk.remove(to_remove)

        return {
            "removed": len(to_remove),
            "remaining_cameras": len(chunk.cameras),
        }

    @mcp.tool()
    def rename_cameras(find: str, replace: str) -> dict:
        """Bulk rename cameras by replacing a substring in their labels.

        Useful for organizing cameras from different sources (e.g.,
        rename "DSC" prefix to "Z9_" for clarity).

        Args:
            find: Substring to search for in camera labels.
            replace: Replacement string.

        Returns:
            Number of cameras renamed and total camera count.
        """
        chunk = get_chunk()
        renamed = 0
        for cam in chunk.cameras:
            if find in cam.label:
                cam.label = cam.label.replace(find, replace)
                renamed += 1
        return {"renamed": renamed, "total_cameras": len(chunk.cameras)}
