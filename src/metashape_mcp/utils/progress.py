"""Progress callback adapter for MCP context reporting.

Wraps Metashape's synchronous progress callback (float 0-1) into
MCP Context.report_progress() calls. Supports cancellation via a
shared flag that causes Metashape to abort the current operation.

Tracks global operation state so get_processing_status can report it.
"""

import asyncio
import threading
import time


# Global cancel flag — set by cancel_processing tool, checked by progress callbacks
_cancel_event = threading.Event()

# Global operation state — updated by progress callbacks, read by status tool
_operation_state = {
    "active": False,
    "operation": "",
    "progress": 0.0,
    "started_at": 0.0,
    "last_callback_at": 0.0,
}
_state_lock = threading.Lock()

# If no progress callback fires within this window, assume the operation died.
# Large operations may have gaps between callbacks — 120s is conservative.
_STALE_TIMEOUT = 120.0


def request_cancel():
    """Signal all running operations to cancel and clear operation state."""
    _cancel_event.set()
    _clear_operation()


def is_cancel_requested() -> bool:
    """Check if cancellation has been requested."""
    return _cancel_event.is_set()


def clear_cancel():
    """Clear the cancel flag (called before starting a new operation)."""
    _cancel_event.clear()


def get_operation_state() -> dict:
    """Return a snapshot of the current operation state.

    Auto-clears stale state if no progress callback has fired within
    _STALE_TIMEOUT seconds — handles the case where Metashape dies
    mid-operation and the finally block in run_in_thread never fires.
    """
    now = time.time()
    with _state_lock:
        if (
            _operation_state["active"]
            and _operation_state["last_callback_at"] > 0
            and now - _operation_state["last_callback_at"] > _STALE_TIMEOUT
        ):
            _operation_state["active"] = False
            _operation_state["progress"] = 0.0
            _operation_state["operation"] = ""
        state = dict(_operation_state)
    if state["active"] and state["started_at"]:
        state["elapsed_seconds"] = round(now - state["started_at"], 1)
    return state


def _set_operation(operation: str, progress: float = 0.0, active: bool = True):
    """Update the global operation state."""
    # Clamp progress to 0-1 range (some Metashape operations report > 1.0)
    progress = max(0.0, min(1.0, progress))
    with _state_lock:
        _operation_state["active"] = active
        _operation_state["operation"] = operation
        _operation_state["progress"] = progress
        _operation_state["last_callback_at"] = time.time()
        if active and progress == 0.0:
            _operation_state["started_at"] = time.time()


def _clear_operation():
    """Mark the current operation as finished."""
    with _state_lock:
        _operation_state["active"] = False
        _operation_state["progress"] = 1.0
        _operation_state["operation"] = ""
        _operation_state["started_at"] = 0.0
        _operation_state["last_callback_at"] = 0.0


def make_progress_callback(ctx, operation: str):
    """Create a Metashape-compatible progress callback.

    Metashape calls progress(float) synchronously with values 0.0-1.0.
    This bridges that to MCP's async progress reporting and updates
    global operation state for status queries.
    If cancellation is requested, raises an exception to abort the operation.

    NOTE: Does NOT set operation state at factory time — run_in_thread
    handles that after the anti-queuing guard check.

    Args:
        ctx: MCP Context object with report_progress method.
        operation: Human-readable operation name for progress messages.

    Returns:
        A callable(float) -> bool suitable for Metashape's progress parameter.
    """
    clear_cancel()
    loop = _get_or_create_loop()

    def callback(progress_value: float) -> bool:
        _set_operation(operation, progress_value)

        if _cancel_event.is_set():
            _cancel_event.clear()
            _clear_operation()
            raise RuntimeError(f"Operation cancelled: {operation}")

        try:
            pv = max(0.0, min(1.0, progress_value))
            coro = ctx.report_progress(
                progress=pv,
                total=1.0,
                message=f"{operation}: {pv:.0%}",
            )
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, loop)
            else:
                loop.run_until_complete(coro)
        except Exception:
            pass  # Don't let progress reporting break the operation

        return True

    return callback


def make_tracking_callback(operation: str):
    """Create a progress callback that only tracks state (no MCP context).

    Use this when ctx is None but you still want status tracking.

    NOTE: Does NOT set operation state at factory time — run_in_thread
    handles that after the anti-queuing guard check.

    Args:
        operation: Human-readable operation name.

    Returns:
        A callable(float) -> bool suitable for Metashape's progress parameter.
    """
    clear_cancel()

    def callback(progress_value: float) -> bool:
        _set_operation(operation, progress_value)

        if _cancel_event.is_set():
            _cancel_event.clear()
            _clear_operation()
            raise RuntimeError(f"Operation cancelled: {operation}")

        return True

    return callback


def is_operation_active() -> bool:
    """Check if a processing operation is currently running (non-stale)."""
    now = time.time()
    with _state_lock:
        if not _operation_state["active"]:
            return False
        # Check if stale
        if (
            _operation_state["last_callback_at"] > 0
            and now - _operation_state["last_callback_at"] > _STALE_TIMEOUT
        ):
            _operation_state["active"] = False
            _operation_state["progress"] = 0.0
            _operation_state["operation"] = ""
            return False
        return True


async def run_in_thread(func, *args, **kwargs):
    """Run a blocking Metashape operation in a background thread.

    Keeps the asyncio event loop responsive so other MCP requests
    (like get_processing_status) can be served while the operation runs.
    Clears operation state when the call completes or fails.

    Raises RuntimeError if another operation is already running,
    preventing request queuing.
    """
    if is_operation_active():
        with _state_lock:
            op = _operation_state["operation"]
        raise RuntimeError(
            f"Cannot start new operation: '{op}' is already running. "
            f"Cancel it first with cancel_processing, then retry."
        )
    try:
        return await asyncio.to_thread(func, *args, **kwargs)
    finally:
        _clear_operation()


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    """Get the running event loop or create a new one."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
