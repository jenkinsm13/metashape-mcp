---
name: mcp-tool-scaffolding
description: Scaffold a new Metashape MCP tool with correct imports, registration, progress tracking, and auto-save patterns. Use when adding new tools to the metashape-mcp server.
disable-model-invocation: true
---

# MCP Tool Scaffolding

Generate a new Metashape MCP tool module or add a tool to an existing module, following all project conventions.

## Module Template

Every tool module follows this exact pattern:

```python
"""[Module description] tools."""

import Metashape

from metashape_mcp.utils.bridge import auto_save, get_chunk, get_document
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import make_tracking_callback


def register(mcp) -> None:
    """Register [module] tools."""

    @mcp.tool()
    def tool_name(
        param1: str = "default",
        param2: int = 1,
    ) -> dict:
        """One-line description of what this tool does.

        Longer explanation if needed. Mention prerequisites
        (e.g., "Run match_photos first.").

        Args:
            param1: Description of param1.
            param2: Description of param2.

        Returns:
            Description of return dict fields.
        """
        chunk = get_chunk()
        # Or: doc = get_document()

        # Prerequisite checks (import from bridge as needed):
        # require_tie_points(chunk)
        # require_model(chunk)
        # require_depth_maps(chunk)
        # require_point_cloud(chunk)

        # Resolve enums for Metashape API parameters:
        # resolved = resolve_enum("category", param1)

        # Progress callback for long operations:
        cb = make_tracking_callback("Operation name")

        # Call Metashape API:
        chunk.someMethod(
            param1=param1,
            param2=param2,
            progress=cb,
        )

        # Always auto-save after state-mutating operations:
        auto_save()

        return {
            "status": "operation_complete",
            "key_metric": some_value,
        }
```

## Conventions Checklist

Before writing a tool, verify ALL of these:

1. **Synchronous only** — NO `async def`. All tools are plain `def`. Metashape API is not thread-safe.
2. **No `Context` parameter** — Never import or use `from mcp.server.fastmcp import Context`.
3. **Use `get_chunk()` / `get_document()`** — Never access `Metashape.app.document` directly.
4. **Use `resolve_enum()`** — For all Metashape enum parameters. Check `utils/enums.py` for existing mappings, add new ones there.
5. **Use `make_tracking_callback()`** — For any operation that takes a `progress` parameter.
6. **Call `auto_save()`** — After every state-mutating operation. Import from `utils.bridge`.
7. **Use prerequisite helpers** — `require_tie_points()`, `require_model()`, `require_depth_maps()`, `require_point_cloud()` before operations that need them.
8. **Return dicts** — All tools return `dict` (or `list[dict]`). Include actionable metrics.
9. **Hardcode sensible defaults** — Match Metashape's best-practice defaults, not necessarily API defaults (e.g., `keep_keypoints=True` overrides Metashape's `False`).
10. **Module size** — Keep each module under 200 lines. Split into new module if needed.

## Adding to an Existing Module

1. Open the target module in `src/metashape_mcp/tools/`
2. Add the new `@mcp.tool()` function inside the existing `register(mcp)` function
3. Add any new imports at the top (bridge helpers, enums)
4. Follow the same parameter style as sibling tools in that module

## Creating a New Module

1. Create `src/metashape_mcp/tools/new_module.py`
2. Use the template above
3. Register it in `src/metashape_mcp/tools/__init__.py`:
   ```python
   from . import new_module
   # In the register_all function:
   new_module.register(mcp)
   ```

## Enum Mapping

If the tool needs a new enum category, add it to `src/metashape_mcp/utils/enums.py`:

```python
"new_category": {
    "option_a": Metashape.SomeEnum.OptionA,
    "option_b": Metashape.SomeEnum.OptionB,
},
```

Then use: `resolved = resolve_enum("new_category", user_string)`

## Common Patterns

**Read-only tool** (no auto_save needed):
```python
@mcp.tool()
def get_something_stats() -> dict:
    chunk = get_chunk()
    require_model(chunk)
    return {"faces": len(chunk.model.faces)}
```

**Tool with optional filtering by class**:
```python
@mcp.tool()
def build_something(classes: list[int] | None = None) -> dict:
    kwargs = {"progress": cb}
    if classes is not None:
        kwargs["classes"] = classes
    chunk.buildSomething(**kwargs)
```

**Tool that wraps a long operation**:
```python
cb = make_tracking_callback("Building thing")
chunk.buildThing(progress=cb)
auto_save()
```
