"""Project and chunk state resources."""

import Metashape

from metashape_mcp.utils.bridge import get_chunk, get_document


def register(mcp) -> None:
    """Register project info resources."""

    @mcp.resource("metashape://agent/rules")
    def agent_rules() -> str:
        """Mandatory rules for AI agents using this MCP server. Read this first."""
        return (
            "MANDATORY AGENT RULES FOR METASHAPE MCP:\n\n"
            "1. NEVER write a script that batches multiple MCP tool calls. "
            "You are an AI agent — call each tool INDIVIDUALLY as a separate "
            "agent action. Check the result. Reason about it. Then call the "
            "next tool. Writing a Python script that chains MCP calls defeats "
            "the entire purpose of this server.\n\n"
            "2. ALWAYS keep_keypoints=True when calling match_photos. Without "
            "it, incremental batch alignment fails (keypoints are discarded "
            "after matching, preventing cross-batch matching).\n\n"
            "3. Save after every major step — call save_project() between "
            "operations.\n\n"
            "4. GPU/CPU rule: set_gpu_config(cpu_enable=True) BEFORE alignment "
            "only. set_gpu_config(cpu_enable=False) BEFORE depth maps, meshing, "
            "texturing. CPU slows down GPU operations.\n\n"
            "5. USGS tie point filtering thresholds: "
            "ReconstructionUncertainty=10, ProjectionAccuracy=3, "
            "ReprojectionError=0.3. NEVER remove more than 50%% of tie points "
            "in one pass. The tool enforces this automatically.\n\n"
            "6. Tool calls block until the Metashape operation completes. "
            "Never set timeouts. Never poll. Operations can take hours or days."
        )

    @mcp.resource("metashape://project/info")
    def project_info() -> dict:
        """Current project information: path, chunk count, status."""
        doc = get_document()
        return {
            "path": doc.path,
            "read_only": doc.read_only,
            "modified": doc.modified,
            "chunk_count": len(doc.chunks),
            "active_chunk": doc.chunk.label if doc.chunk else None,
        }

    @mcp.resource("metashape://project/chunks")
    def project_chunks() -> list[dict]:
        """Summary of all chunks and their processing state."""
        doc = get_document()
        result = []
        for i, c in enumerate(doc.chunks):
            aligned = sum(1 for cam in c.cameras if cam.transform is not None)
            info = {
                "index": i,
                "label": c.label,
                "enabled": c.enabled,
                "cameras": len(c.cameras),
                "aligned_cameras": aligned,
                "markers": len(c.markers),
                "scalebars": len(c.scalebars),
                "crs": c.crs.name if c.crs else None,
                "has_tie_points": c.tie_points is not None,
                "has_depth_maps": c.depth_maps is not None,
                "has_point_cloud": c.point_cloud is not None,
                "has_model": c.model is not None,
                "has_tiled_model": c.tiled_model is not None,
                "has_elevation": c.elevation is not None,
                "has_orthomosaic": c.orthomosaic is not None,
                "is_active": c == doc.chunk,
            }
            result.append(info)
        return result

    @mcp.resource("metashape://chunk/{label}/summary")
    def chunk_summary(label: str) -> dict:
        """Detailed statistics for a specific chunk."""
        chunk = get_chunk(label=label)

        aligned = sum(1 for cam in chunk.cameras if cam.transform is not None)

        info = {
            "label": chunk.label,
            "key": chunk.key,
            "enabled": chunk.enabled,
            "cameras": {
                "total": len(chunk.cameras),
                "aligned": aligned,
                "sensors": len(chunk.sensors),
            },
            "markers": len(chunk.markers),
            "scalebars": len(chunk.scalebars),
            "crs": chunk.crs.name if chunk.crs else None,
        }

        if chunk.tie_points:
            tp = chunk.tie_points
            info["tie_points"] = {
                "points": len(tp.points) if tp.points else 0,
                "tracks": len(tp.tracks) if tp.tracks else 0,
                "projections": len(tp.projections) if tp.projections else 0,
            }

        if chunk.point_cloud:
            pc = chunk.point_cloud
            info["point_cloud"] = {
                "points": len(pc.points) if pc.points else 0,
            }

        if chunk.model:
            m = chunk.model
            info["model"] = {
                "faces": len(m.faces) if m.faces else 0,
                "vertices": len(m.vertices) if m.vertices else 0,
                "has_uv": m.tex_vertices is not None and len(m.tex_vertices) > 0,
                "textures": len(m.textures) if m.textures else 0,
            }

        if chunk.elevation:
            info["dem"] = {"resolution": chunk.elevation.resolution}

        if chunk.orthomosaic:
            info["orthomosaic"] = {"resolution": chunk.orthomosaic.resolution}

        region = chunk.region
        info["region"] = {
            "center": list(region.center),
            "size": list(region.size),
        }

        return info
