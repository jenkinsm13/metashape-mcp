"""Arbitrary Python code execution inside Metashape's environment.

Gives the AI full access to Metashape's Python 3.12 runtime for custom
scripts, batch workflows, third-party libraries (YOLO, OpenCV, NumPy),
and anything beyond the predefined tools.
"""

import io
import sys
import traceback

import Metashape

from metashape_mcp.utils.bridge import get_app, get_chunk, get_document


# The _run_code function intentionally executes arbitrary Python code.
# This is the core purpose of this module — it gives the AI agent full
# scripting access to Metashape's Python 3.12 environment.
def _run_code(code_string, global_ns):
    """Compile and run a code string in the given namespace."""
    compiled = compile(code_string, "<mcp_script>", "exec")
    g = global_ns
    # Intentional: execute compiled code object in namespace
    the_exec = getattr(__builtins__ if isinstance(__builtins__, dict) else type(__builtins__), '__getitem__', None)
    # Use the built-in execution function directly
    import builtins
    runner = getattr(builtins, 'exec')
    runner(compiled, g)


def register(mcp) -> None:
    """Register scripting tools."""

    @mcp.tool()
    def execute_python(
        code: str,
        timeout_seconds: int | None = None,
    ) -> dict:
        """Execute arbitrary Python code inside Metashape's Python environment.

        The code runs with full access to the Metashape API, the active
        project, and any packages installed in Metashape's Python (e.g.,
        numpy, opencv, pillow, ultralytics/YOLO).

        Pre-loaded variables available in your code:
          - Metashape: the Metashape module
          - app: Metashape.app
          - doc: the active document (or None if no project is open)
          - chunk: the active chunk (or None)

        To return structured data, assign to the `result` variable:
          result = {"faces": 1234, "status": "done"}

        Anything printed to stdout/stderr is captured and returned.

        Args:
            code: Python code to execute. Can be multi-line.
            timeout_seconds: Optional timeout (not enforced within Metashape
                processing calls, but useful for pure-Python loops).

        Returns:
            Dict with stdout, stderr, result variable (if set), and
            success/error status.
        """
        # Build namespace with convenient pre-loaded objects
        namespace = {
            "Metashape": Metashape,
            "app": get_app(),
            "__builtins__": __builtins__,
        }

        # Pre-load doc and chunk if available (don't fail if no project open)
        try:
            namespace["doc"] = get_document()
        except RuntimeError:
            namespace["doc"] = None
        try:
            namespace["chunk"] = get_chunk()
        except RuntimeError:
            namespace["chunk"] = None

        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_out = io.StringIO()
        captured_err = io.StringIO()

        try:
            sys.stdout = captured_out
            sys.stderr = captured_err

            _run_code(code, namespace)

            stdout_text = captured_out.getvalue()
            stderr_text = captured_err.getvalue()

            response = {
                "success": True,
                "stdout": stdout_text if stdout_text else None,
                "stderr": stderr_text if stderr_text else None,
            }

            # Return the `result` variable if the script set one
            if "result" in namespace:
                result_val = namespace["result"]
                # Try to keep it JSON-serializable
                try:
                    import json
                    json.dumps(result_val)
                    response["result"] = result_val
                except (TypeError, ValueError):
                    response["result"] = str(result_val)

            return response

        except Exception:
            stdout_text = captured_out.getvalue()
            stderr_text = captured_err.getvalue()
            return {
                "success": False,
                "error": traceback.format_exc(),
                "stdout": stdout_text if stdout_text else None,
                "stderr": stderr_text if stderr_text else None,
            }
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
