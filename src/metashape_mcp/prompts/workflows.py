"""Workflow prompt templates for common photogrammetry pipelines."""

AGENT_RULES = """**MANDATORY AGENT RULES — READ BEFORE PROCEEDING:**

1. **NEVER write a script that batches these tool calls.** You are an AI agent.
   Call each tool INDIVIDUALLY as a separate agent action. Check the result.
   Reason about it. Then call the next tool. Writing a Python script that
   chains MCP calls defeats the entire purpose of this server.
2. **ALWAYS keep_keypoints=True** when calling match_photos (it is the default).
3. **Save after every major step** — call save_project() between operations.
4. **GPU/CPU rule**: set_gpu_config(cpu_enable=True) BEFORE alignment only.
   set_gpu_config(cpu_enable=False) BEFORE depth maps, meshing, texturing.
5. **USGS tie point filtering**: RU=10, PA=3, RE=0.3. NEVER remove more than
   50% of tie points in one pass. The tool auto-raises the threshold if needed.
6. **Tool calls block until done.** No timeouts. No polling. Wait for results.

"""


def register(mcp) -> None:
    """Register workflow prompts."""

    @mcp.prompt()
    def aerial_survey_pipeline(
        project_path: str,
        photo_folder: str,
        crs_epsg: str = "4326",
        quality: str = "medium",
    ) -> str:
        """Complete aerial/drone survey processing workflow.

        Generates a step-by-step prompt for processing drone imagery
        from photos to orthomosaic and DEM.

        Args:
            project_path: Path for the Metashape project file.
            photo_folder: Directory containing drone photos.
            crs_epsg: EPSG code for the coordinate system.
            quality: Processing quality: "ultra", "high", "medium", "low".
        """
        downscale_map = {"ultra": 1, "high": 2, "medium": 4, "low": 8}
        ds = downscale_map.get(quality, 4)

        return AGENT_RULES + f"""Process this aerial/drone survey step by step:

1. **Create Project**: create_project("{project_path}")
2. **Add Photos**: add_photos(["{photo_folder}"])
3. **Analyze Quality**: analyze_images() - check for blurry images
4. **Remove Bad Photos**: If any cameras have quality < 0.5, remove them
5. **Set CRS**: set_crs(epsg_code={crs_epsg})
6. **Enable CPU for Alignment**: set_gpu_config(cpu_enable=True)
7. **Match Photos**: match_photos(downscale={ds}, generic_preselection=True, reference_preselection=True, keep_keypoints=True)
8. **Align Cameras**: align_cameras(adaptive_fitting=True)
9. **Filter Tie Points** (USGS workflow):
   a. filter_tie_points(criterion="ReconstructionUncertainty", threshold=10) then optimize_cameras()
   b. filter_tie_points(criterion="ProjectionAccuracy", threshold=3) then optimize_cameras()
   c. filter_tie_points(criterion="ReprojectionError", threshold=0.3) then optimize_cameras()
   d. Repeat c until <10 points removed per iteration
10. **Disable CPU for Dense Processing**: set_gpu_config(cpu_enable=False)
11. **Build Depth Maps**: build_depth_maps(downscale={ds}, filter_mode="mild")
12. **Build Point Cloud**: build_point_cloud(point_colors=True, point_confidence=True)
13. **Classify Ground**: classify_ground_points() - for terrain extraction
14. **Build DEM**: build_dem(source_data="point_cloud", classes=[2])
15. **Build Orthomosaic**: build_orthomosaic(surface_data="elevation", blending_mode="mosaic")
16. **Build Model** (optional): build_model(surface_type="height_field", source_data="depth_maps")
17. **Save Project**: save_project()

After each step, check the result and report progress.
Quality setting: {quality} (downscale={ds})
Use resources to monitor processing state between steps.
"""

    @mcp.prompt()
    def close_range_pipeline(
        project_path: str,
        photo_folder: str,
        quality: str = "medium",
    ) -> str:
        """Object/close-range reconstruction workflow.

        Generates a prompt for reconstructing 3D objects from
        close-range photography.

        Args:
            project_path: Path for the Metashape project file.
            photo_folder: Directory containing photos.
            quality: Processing quality: "ultra", "high", "medium", "low".
        """
        downscale_map = {"ultra": 1, "high": 2, "medium": 4, "low": 8}
        ds = downscale_map.get(quality, 4)

        return AGENT_RULES + f"""Process this close-range/object reconstruction step by step:

1. **Create Project**: create_project("{project_path}")
2. **Add Photos**: add_photos(["{photo_folder}"])
3. **Analyze Quality**: analyze_images()
4. **Enable CPU for Alignment**: set_gpu_config(cpu_enable=True)
5. **Match Photos**: match_photos(downscale={ds}, generic_preselection=True, keep_keypoints=True)
6. **Align Cameras**: align_cameras(adaptive_fitting=True)
7. **Check Alignment**: Use metashape://chunk/Chunk 1/cameras to verify alignment rate
8. **Filter Tie Points** (USGS workflow):
   a. filter_tie_points(criterion="ReconstructionUncertainty", threshold=10) then optimize_cameras()
   b. filter_tie_points(criterion="ProjectionAccuracy", threshold=3) then optimize_cameras()
   c. filter_tie_points(criterion="ReprojectionError", threshold=0.3) then optimize_cameras()
   d. Repeat c until <10 points removed per iteration
9. **Disable CPU for Dense Processing**: set_gpu_config(cpu_enable=False)
10. **Build Depth Maps**: build_depth_maps(downscale={ds}, filter_mode="moderate")
11. **Build Model**: build_model(surface_type="arbitrary", source_data="depth_maps", face_count="high")
12. **Clean Model**: clean_model(criterion="component_size", level=50)
13. **Smooth Model** (optional): smooth_model(strength=2, preserve_edges=True)
14. **Build UV**: build_uv(mapping_mode="generic", texture_size=8192)
15. **Build Texture**: build_texture(blending_mode="mosaic", texture_size=8192, ghosting_filter=True)
    # additional options: anti_aliasing=1, source_model_key=<int>, transfer_texture=True,
    # source_data="model" when baking from another mesh
16. **Save Project**: save_project()

Quality setting: {quality} (downscale={ds})
For objects, use "arbitrary" surface type (not "height_field").
"""

    @mcp.prompt()
    def batch_export(
        output_folder: str,
        formats: str = "all",
    ) -> str:
        """Export all available products from the current project.

        Args:
            output_folder: Directory for exported files.
            formats: "all" or comma-separated list of products.
        """
        return AGENT_RULES + f"""Export all available processing results:

First, check what's available using metashape://project/chunks resource.

Then export each available product to "{output_folder}":

1. **Point Cloud** (if available): export_point_cloud("{output_folder}/point_cloud.laz", format="laz")
2. **Model** (if available): export_model("{output_folder}/model.obj", format="obj", save_texture=True)
3. **DEM** (if available): export_dem("{output_folder}/dem.tif", format="tif")
4. **Orthomosaic** (if available): export_orthomosaic("{output_folder}/orthomosaic.tif", format="tif")
5. **Tiled Model** (if available): export_tiled_model("{output_folder}/tiled_model", format="cesium")
6. **Report**: export_report("{output_folder}/report.pdf")
7. **Cameras**: export_cameras("{output_folder}/cameras.xml", format="xml")

Skip products that don't exist. Report file sizes after export.
Requested formats: {formats}
"""

    @mcp.prompt()
    def road_corridor_pipeline(
        project_path: str,
        photo_folder: str,
        gps_csv: str = "",
        crs_epsg: str = "4326",
        quality: str = "medium",
        target_faces: str = "5000000",
        export_format: str = "fbx",
    ) -> str:
        """Vehicle-mounted road corridor capture to driving simulator mesh.

        Optimized for large-scale fisheye road captures with EXR+alpha
        sky masks. Uses an adaptive, iterative alignment strategy —
        checks results after each step and adjusts approach based on
        what's working. Builds mesh from point cloud (not depth maps)
        to avoid the sky tunnel/interpolation problem.

        Args:
            project_path: Path for the Metashape project file.
            photo_folder: Directory containing EXR photos.
            gps_csv: Path to CSV with GPS coordinates (columns: label,x,y,z).
            crs_epsg: EPSG code for coordinate system.
            quality: Processing quality: "high", "medium", "low".
            target_faces: Target face count for the mesh.
            export_format: Export format: "fbx", "obj", "gltf".
        """
        downscale_map = {"ultra": 1, "high": 2, "medium": 4, "low": 8}
        ds = downscale_map.get(quality, 4)
        faces = int(target_faces)

        gps_step = ""
        if gps_csv:
            gps_step = f"""
4. **Import GPS Reference**: import_reference("{gps_csv}", format="csv", columns="nxyz", delimiter=",", crs_epsg={crs_epsg})"""
        else:
            gps_step = f"""
4. **Set CRS**: set_crs(epsg_code={crs_epsg}) — GPS will be loaded from EXIF"""

        return AGENT_RULES + f"""Process this road corridor capture for driving simulator use.

**YOU ARE AN ITERATIVE OPERATOR, NOT A SCRIPT RUNNER.**
Do NOT blindly execute steps. After every operation, CHECK the results
using resources (metashape://chunk/*/cameras, metashape://chunk/*/summary, etc.)
and ADAPT your approach based on what you see. Ask the user when unsure.

**Key facts about this workflow:**
- Vehicle-mounted fisheye capture along a road corridor
- Photos are EXR with alpha channel for sky masking
- Build mesh from POINT CLOUD, not depth maps (avoids sky tunnel/interpolation artifacts)
- Masks ARE respected during point cloud generation but NOT during depth map meshing
- Alignment is ALWAYS incremental — never try to align all photos at once
- Road captures have two directions: outbound and inbound, overlapping along the centerline
- Max ~2000 photos per alignment batch

---

**Phase 1: Setup**

1. **Create Project**: create_project("{project_path}")
2. **Add ALL Photos**: add_photos(["{photo_folder}"])
   - Import everything upfront — outbound and inbound directions
   - All photos go into one chunk
3. **Analyze Quality**: analyze_images() — flag blurry frames from the drive
{gps_step}

**Phase 2: Alignment (ALWAYS INCREMENTAL)**

Alignment is ALWAYS done in batches of ~2000 photos max. Never try to
align everything at once — it will fail on large corridor datasets.

Road corridor captures have two travel directions (outbound and inbound)
that overlap along the road centerline. The user handles camera selection
in one of two ways:

**Option A — Select in the GUI**: All photos are already imported. The user
selects camera dots in Metashape's reference pane based on GPS position
and enables only the batch they want to align. You wait for the user to
tell you which cameras are enabled.

**Option B — Separate folders**: Outbound and inbound photos are in separate
folders. You add from the head of one direction and the tail of the other
to build up coverage incrementally.

**GPU/CPU Rule:** CPU speeds up alignment but slows down EVERYTHING else.
- set_gpu_config(cpu_enable=True) BEFORE matching/aligning
- set_gpu_config(cpu_enable=False) BEFORE depth maps, point cloud, meshing, texturing

**The alignment loop:**

1. **User enables a batch of ~2000 cameras** (or tells you to add a batch from a folder)
2. **Enable CPU**: set_gpu_config(cpu_enable=True)
3. match_photos(downscale=1, generic_preselection=True, reference_preselection=True, keep_keypoints=True, keypoint_limit=60000, tiepoint_limit=4000, guided_matching=True)
4. align_cameras(adaptive_fitting=True, reset_alignment=False)
   - reset_alignment=False is CRITICAL after the first batch — always build on existing alignment
5. **CHECK**: Read metashape://chunk/*/cameras. Report alignment rate to the user.
6. **Filter tie points (USGS workflow) then optimize:**
   a. filter_tie_points(criterion="ReconstructionUncertainty", threshold=10)
   b. optimize_cameras(adaptive_fitting=True, fit_k4=True)
   c. filter_tie_points(criterion="ProjectionAccuracy", threshold=3)
   d. optimize_cameras(adaptive_fitting=True, fit_k4=True)
   e. filter_tie_points(criterion="ReprojectionError", threshold=0.3)
   f. optimize_cameras(adaptive_fitting=True, fit_k4=True)
   g. Repeat step e-f until <10 points are removed per iteration
7. **Report results and wait.** The user decides:
   - Enable the next batch and repeat
   - Place GCPs at this point to stabilize before adding more
   - Remove problem cameras
   - Adjust settings
   - Continue to dense reconstruction
8. **Repeat** until the user says alignment is done.

**GCP Placement (OPTIONAL — can happen at any point during alignment)**

The user may want to place GCPs between alignment batches to improve
accuracy. GCPs are placed manually in the Metashape GUI at road markings
(stop bars, crosswalks, intersection paint).

- When the user says they've placed GCPs: optimize_cameras(adaptive_fitting=True)
- list_markers() — report errors for each marker
- Flag any GCP with >3x the average error — likely misprojected
- GCPs are not required for every project — the user decides

**Phase 3: Dense Reconstruction (SKY-SAFE)**

11. **Disable CPU**: set_gpu_config(cpu_enable=False) — CPU slows down dense processing
12. **Build Depth Maps**: build_depth_maps(downscale={ds}, filter_mode="moderate", max_neighbors=16)
13. **Build Point Cloud**: build_point_cloud(source_data="depth_maps", point_colors=True, point_confidence=True)
    - Masks ARE respected here — sky points will be excluded
14. **Classify Ground**: classify_ground_points(max_angle=10, max_distance=1.0, cell_size=50)
15. **Crop Region**: set_region() — limit vertical extent to just above tallest features

**Phase 4: Mesh (FROM POINT CLOUD, NOT DEPTH MAPS)**

16. **Build Model**: build_model(source_data="point_cloud", surface_type="arbitrary", face_count="custom", face_count_custom={faces}, interpolation="enabled")
    - CRITICAL: source_data="point_cloud" NOT "depth_maps"
    - Depth map meshing ignores masks and creates sky tunnels
    - Point cloud meshing respects the masked sky gaps
17. **Clean Model**: clean_model(criterion="component_size", level=60)
    - Aggressively remove floating debris and sky remnants
18. **Decimate** (if needed): decimate_model(face_count={faces})

**Phase 5: Texture & Export**

19. **Build UV**: build_uv(mapping_mode="generic", texture_size=8192)
20. **Build Texture**: build_texture(blending_mode="mosaic", texture_size=8192, ghosting_filter=True)
    - Mosaic blending preserves sharp road markings
    - Ghosting filter handles cars that moved between frames
    - Optional parameters allow baking from a different model (see tool docs)
21. **Export**: export_model("{project_path.replace('.psx', '')}.{export_format}", format="{export_format}", save_texture=True)
22. **Export Report**: export_report("{project_path.replace('.psx', '_report.pdf')}")
23. **Save Project**: save_project()

Quality: {quality} (downscale={ds}) | Target faces: {faces:,} | Export: {export_format}
"""
