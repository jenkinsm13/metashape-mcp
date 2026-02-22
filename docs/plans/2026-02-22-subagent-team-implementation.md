# Subagent Team Implementation Plan

**Date:** 2026-02-22
**Design:** [2026-02-22-subagent-team-design.md](./2026-02-22-subagent-team-design.md)
**Status:** Complete

## What Was Built

Five new specialized agents for the Metashape + Blender photogrammetry pipeline, plus one bonus agent (gcp-advisor, expanded from the design's dem-alignment-advisor to cover full GCP strategy).

### Agent Files

All agents live in `/agents/` and follow the same YAML frontmatter + markdown body format established by the existing `photogrammetry-qa.md` and `metashape-api-verifier.md`.

| File | Lines | Role | Color |
|------|-------|------|-------|
| `alignment-doctor.md` | 183 | Diagnoses alignment failures, prescribes fixes | `#D4380D` deep red |
| `gcp-advisor.md` | 280 | GCP strategy, marker error analysis, virtual checkpoints | `#CF8B17` amber |
| `handoff-coordinator.md` | 214 | Metashape <-> Blender export/import/verification | `#7B61FF` purple |
| `terrain-processor.md` | 290 | Blender mesh cleanup, classification, UV, game-ready | `#389E0D` green |
| `project-planner.md` | 219 | Status overview, stage classification, next-step routing | `#0958D9` blue |

### Pre-existing Agents (unchanged)

| File | Role | Color |
|------|------|-------|
| `photogrammetry-qa.md` | Post-processing QA checks | `#2E86AB` teal |
| `metashape-api-verifier.md` | API correctness audits | `#E8543E` red-orange |

## Agent Format

Each agent file contains:

```yaml
---
name: agent-name
description: One-paragraph description (shown in Claude's agent picker)
when_to_use: Specific trigger conditions
color: "#HEXCODE"
tools:
  - mcp__metashape__tool_name
  - mcp__blender__tool_name
---
```

Followed by a full markdown system prompt with:
- **Diagnostic/processing protocol** -- step-by-step what the agent does when invoked
- **Decision trees** -- flowcharts for common scenarios (as code blocks)
- **Code examples** -- ready-to-run Python for Blender execute_blender_code or Metashape tool calls
- **Output format** -- standardized report template
- **Rules** -- hard constraints the agent must follow

## Design Decisions Made During Implementation

### dem-alignment-advisor -> gcp-advisor
The design called for a "dem-alignment-advisor" focused on DEM ground truth. During implementation, this was expanded to a full **gcp-advisor** that covers:
- Traditional surveyed GCPs
- DEM-based virtual checkpoints
- Google Earth coordinate extraction
- Marker error diagnosis
- Reference accuracy settings by GPS type

This is more useful because GCP decisions come up even without a DEM.

### Classification Priority
Per user feedback: "points always have colors, mesh rarely."
- Spline-based (best, when KML available) > Color-based (vertex colors, always on points) > Normal-based (fallback)
- Documented in terrain-processor Phase 4 and in the design doc.

### Tool Lists
Each agent declares specific MCP tools in its frontmatter. These are the tools Claude will have available when running that agent. Tool lists were curated to match each agent's actual needs -- no agent has access to tools it doesn't use.

## Routing (No Orchestrator)

There is no orchestrator agent. Claude routes naturally based on agent descriptions. The `project-planner` agent recommends which agent to invoke next but does not call them directly.

Routing flow:
```
Session start -> project-planner (assess state, recommend next step)
  |
  +-- "Alignment needed" -> corridor-alignment-pipeline skill
  +-- "Alignment failed" -> alignment-doctor
  +-- "Drift detected" -> gcp-advisor
  +-- "Ready to export" -> handoff-coordinator
  +-- "Tiles in Blender" -> terrain-processor
  +-- "QA check" -> photogrammetry-qa
  +-- "API bug suspected" -> metashape-api-verifier
```

## Cross-References

Agents reference skills and each other by name:

| Agent | References |
|-------|-----------|
| alignment-doctor | corridor-alignment-pipeline skill |
| gcp-advisor | corridor-alignment-pipeline skill, project memory (-36m datum) |
| handoff-coordinator | tile-export-pipeline skill, photogrammetry-terrain-cleanup skill |
| terrain-processor | photogrammetry-terrain-cleanup skill, tile-export-pipeline skill |
| project-planner | All agents and skills by name |

## Plugin Registration

The agents are auto-discovered by Claude Code from the `/agents/` directory. No changes needed to `plugin.json` -- the plugin system reads agent files from the conventional directory.

## Remaining Work

- [ ] Push to origin (local is 1 commit ahead + uncommitted agent files)
- [ ] Test agent invocation in a live session with both MCP servers running
- [ ] Verify tool lists match actual MCP server tool names (run metashape-api-verifier if in doubt)
