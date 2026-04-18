"""Progress tracking and cancellation for Metashape operations.

Tracks global operation state so get_processing_status can report it.
Supports cancellation via a shared flag that causes Metashape to abort
the current operation through its progress callback.

Handles two cancellation scenarios:
  1. Explicit cancel — user calls cancel_processing tool, sets _cancel_event
  2. Superseded operation — a new operation starts while an old one is still
     running (e.g. client disconnected mid-operation). The old callback
     detects it is no longer the active operation and aborts.
"""

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

# Current operation ID — each make_tracking_callback creates a unique sentinel.
# If a callback's ID no longer matches, it was superseded by a newer operation
# and should abort.  This handles orphaned operations from client disconnects.
_current_op_id = None
_op_lock = threading.Lock()

# If no progress callback fires within this window, assume the operation died.
# Large operations may have gaps between callbacks — 120s is conservative.
_STALE_TIMEOUT = 120.0


def request_cancel():
    """Signal all running operations to cancel and clear operation state."""
    _cancel_event.set()
    _clear_operation()


def clear_cancel():
    """Clear the cancel flag (called before starting a new operation)."""
    _cancel_event.clear()


def get_operation_state() -> dict:
    """Return a snapshot of the current operation state.

    Auto-clears stale state if no progress callback has fired within
    _STALE_TIMEOUT seconds — handles the case where Metashape dies
    mid-operation and the callback never fires again.
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


def _set_operation(operation: str, progress: float = 0.0):
    """Update the global operation state."""
    # Clamp progress to 0-1 range (some Metashape operations report > 1.0)
    progress = max(0.0, min(1.0, progress))
    with _state_lock:
        _operation_state["active"] = True
        _operation_state["operation"] = operation
        _operation_state["progress"] = progress
        _operation_state["last_callback_at"] = time.time()
        if progress == 0.0:
            _operation_state["started_at"] = time.time()


def _clear_operation():
    """Mark the current operation as finished."""
    with _state_lock:
        _operation_state["active"] = False
        _operation_state["progress"] = 1.0
        _operation_state["operation"] = ""
        _operation_state["started_at"] = 0.0
        _operation_state["last_callback_at"] = 0.0


def make_tracking_callback(operation: str):
    """Create a progress callback that tracks state and supports cancellation.

    Metashape calls progress(float) synchronously with values 0.0-1.0.
    This updates global operation state for status queries and checks
    the cancel flag to abort if requested.

    Each callback gets a unique operation ID.  If a new operation starts
    (new callback created), the previous callback will detect that its ID
    no longer matches the global current ID and abort — this handles
    orphaned operations from client disconnects without race conditions.

    Args:
        operation: Human-readable operation name.

    Returns:
        A callable(float) -> bool suitable for Metashape's progress parameter.
    """
    # Create a unique sentinel for this operation
    op_id = object()
    with _op_lock:
        global _current_op_id
        _current_op_id = op_id

    clear_cancel()

    def callback(progress_value: float) -> bool:
        _set_operation(operation, progress_value)

        # Check if this operation was superseded by a newer one
        with _op_lock:
            if _current_op_id is not op_id:
                _clear_operation()
                raise RuntimeError(
                    f"Operation aborted (superseded by newer request): {operation}"
                )

        # Check for explicit cancel request
        if _cancel_event.is_set():
            _cancel_event.clear()
            _clear_operation()
            raise RuntimeError(f"Operation cancelled: {operation}")

        return True

    return callback
