"""Network processing tools: connect, submit, monitor, abort batches."""

import Metashape

from metashape_mcp.utils.bridge import get_document


def register(mcp) -> None:
    """Register network processing tools."""

    def _get_client() -> Metashape.NetworkClient:
        """Get or create the NetworkClient singleton."""
        if not hasattr(_get_client, "_client"):
            _get_client._client = Metashape.NetworkClient()
        return _get_client._client

    @mcp.tool()
    def network_connect(host: str, port: int = 5840) -> dict:
        """Connect to a Metashape network processing server.

        Args:
            host: Server hostname or IP address.
            port: Communication port (default 5840).

        Returns:
            Connection status and server info.
        """
        client = _get_client()
        client.connect(host, port=port)

        try:
            info = client.serverVersion()
        except Exception:
            info = {}

        return {
            "status": "connected",
            "host": host,
            "port": port,
            "server_version": info,
        }

    @mcp.tool()
    def network_submit_batch(
        task_names: list[str],
        task_params: list[dict] | None = None,
    ) -> dict:
        """Submit a batch of processing tasks to the network server.

        Creates network tasks from task class names and submits them as
        a batch job. The project must be saved before submission.

        Args:
            task_names: List of Metashape task names (e.g., ["MatchPhotos",
                       "AlignCameras", "BuildDepthMaps"]).
            task_params: Optional list of parameter dicts (one per task).

        Returns:
            Batch ID and status.
        """
        doc = get_document()
        if not doc.path:
            raise RuntimeError("Save the project before submitting network tasks.")

        client = _get_client()
        chunk = doc.chunk

        tasks = []
        params = task_params or [{}] * len(task_names)

        for name, params_dict in zip(task_names, params):
            task_class = getattr(Metashape.Tasks, name, None)
            if task_class is None:
                raise ValueError(
                    f"Unknown task class '{name}'. "
                    f"Use Metashape task class names like 'MatchPhotos', "
                    f"'AlignCameras', 'BuildDepthMaps', etc."
                )

            task = task_class()
            for k, v in params_dict.items():
                setattr(task, k, v)

            network_task = task.toNetworkTask(chunk)
            tasks.append(network_task)

        batch_id = client.createBatch(doc.path, tasks)
        client.setBatchPaused(batch_id, False)

        return {
            "batch_id": batch_id,
            "tasks_submitted": len(tasks),
            "status": "running",
        }

    @mcp.tool()
    def network_list_batches() -> list[dict]:
        """List all batches on the network server.

        Returns:
            List of batch summaries with IDs and statuses.
        """
        client = _get_client()
        batches = client.batchList()
        return batches if isinstance(batches, list) else [batches]

    @mcp.tool()
    def network_batch_status(batch_id: int) -> dict:
        """Get detailed status of a network batch.

        Args:
            batch_id: The batch identifier.

        Returns:
            Batch info including task statuses and progress.
        """
        client = _get_client()
        return client.batchInfo(batch_id)

    @mcp.tool()
    def network_abort_batch(batch_id: int) -> dict:
        """Abort a running network batch.

        Args:
            batch_id: The batch identifier to abort.

        Returns:
            Confirmation of abort.
        """
        client = _get_client()
        client.abortBatch(batch_id)
        return {"batch_id": batch_id, "status": "aborted"}
