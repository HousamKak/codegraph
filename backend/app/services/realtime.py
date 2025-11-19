"""Real-time graph update service."""

from typing import Optional
import logging
import asyncio
from datetime import datetime

from codegraph.watcher import FileWatcher
from codegraph.db import CodeGraphDB
from codegraph.parser import PythonParser
from codegraph.builder import GraphBuilder
from codegraph.validators import ConservationValidator
from ..routers.websocket import get_connection_manager

logger = logging.getLogger(__name__)


class RealtimeGraphService:
    """
    Service that coordinates real-time graph updates.

    Watches for file changes, triggers reindexing, validates,
    and broadcasts updates via WebSocket.
    """

    def __init__(self, db: CodeGraphDB):
        """
        Initialize the real-time service.

        Args:
            db: CodeGraphDB instance
        """
        self.db = db
        self.parser = PythonParser()
        self.builder = GraphBuilder(db)
        self.validator = ConservationValidator(db)
        self.watcher = FileWatcher(debounce_seconds=0.5)
        self.ws_manager = get_connection_manager()

        self.watch_directory: Optional[str] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info("RealtimeGraphService initialized")

    async def handle_file_change(self, file_path: str):
        """
        Handle a file change event.

        This is called by the file watcher when a Python file changes.

        Args:
            file_path: Path to the changed file
        """
        try:
            logger.info(f"Processing file change: {file_path}")

            # Step 1: Delete old nodes from this file
            self.db.delete_nodes_from_file(file_path)

            # Step 2: Re-parse and rebuild graph
            try:
                entities, relationships = self.parser.parse_file(file_path)
                self.builder.build_graph(entities, relationships)

                # Step 3: Mark nodes as changed
                changed_count = self.db.mark_file_nodes_changed(file_path)

                # Step 4: Propagate changes to dependents
                propagation_counts = self.db.propagate_changes_to_dependents()

                # Step 5: Get validation results for changed nodes
                validation_report = self.validator.get_validation_report()

                # Step 6: Get changed nodes for frontend update
                changed_node_ids = self.db.get_changed_node_ids()

                # Step 7: Clear changed markers
                self.db.clear_changed_markers()

                # Step 8: Broadcast update to all connected clients
                await self.ws_manager.broadcast({
                    "type": "file_changed",
                    "file_path": file_path,
                    "timestamp": datetime.now().isoformat(),
                    "reindexing": {
                        "entities_indexed": len(entities),
                        "relationships_indexed": len(relationships),
                        "nodes_marked_changed": changed_count
                    },
                    "propagation": propagation_counts,
                    "validation": {
                        "is_valid": validation_report["errors"] == 0,
                        "errors": validation_report["errors"],
                        "warnings": validation_report["warnings"],
                        "violations": [
                            {
                                "type": v.violation_type.value,
                                "severity": v.severity,
                                "message": v.message,
                                "file_path": v.file_path,
                                "line_number": v.line_number,
                            }
                            for v in validation_report["violations"][:10]  # Limit to 10 violations
                        ]
                    },
                    "changed_node_ids": changed_node_ids[:100]  # Limit to 100 nodes
                })

                logger.info(f"File change processed successfully: {file_path}")

            except Exception as parse_error:
                # If parsing fails, still broadcast the error
                logger.error(f"Error parsing file {file_path}: {parse_error}", exc_info=True)

                await self.ws_manager.broadcast({
                    "type": "file_error",
                    "file_path": file_path,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(parse_error)
                })

        except Exception as e:
            logger.error(f"Error handling file change {file_path}: {e}", exc_info=True)

    def start_watching(self, directory: str, event_loop: asyncio.AbstractEventLoop):
        """
        Start watching a directory for changes.

        Args:
            directory: Directory to watch
            event_loop: Asyncio event loop for async operations
        """
        self.watch_directory = directory
        self._event_loop = event_loop

        # Set the callback for file changes
        self.watcher.set_callback(self.handle_file_change)

        # Start the watcher
        self.watcher.set_watch_directory(directory, event_loop)

        if not self.watcher.is_running:
            self.watcher.start(event_loop)

        logger.info(f"Started watching directory: {directory}")

    def stop_watching(self):
        """Stop watching for file changes."""
        if self.watcher.is_running:
            self.watcher.stop()
            logger.info("Stopped watching for file changes")

    def is_watching(self) -> bool:
        """Check if currently watching for changes."""
        return self.watcher.is_running


# Global instance
_realtime_service: Optional[RealtimeGraphService] = None


def get_realtime_service() -> Optional[RealtimeGraphService]:
    """Get the global realtime service instance."""
    return _realtime_service


def set_realtime_service(service: RealtimeGraphService):
    """Set the global realtime service instance."""
    global _realtime_service
    _realtime_service = service
