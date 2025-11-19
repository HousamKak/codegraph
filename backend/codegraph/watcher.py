"""File watcher for real-time code change detection."""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
from typing import Optional, Set, Callable, Awaitable, Dict
from datetime import datetime
from pathlib import Path
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class CodeFileHandler(FileSystemEventHandler):
    """Handles file system events for Python source files."""

    def __init__(self,
                 on_change_callback: Callable[[str], Awaitable[None]],
                 debounce_seconds: float = 0.5):
        """
        Initialize file handler.

        Args:
            on_change_callback: Async function to call when a file changes
            debounce_seconds: Wait time to debounce rapid changes
        """
        super().__init__()
        self.on_change_callback = on_change_callback
        self.debounce_seconds = debounce_seconds

        # Track pending changes for debouncing
        self._pending_changes: Dict[str, float] = {}
        self._debounce_task: Optional[asyncio.Task] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info(f"CodeFileHandler initialized with {debounce_seconds}s debounce")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop for async operations."""
        self._event_loop = loop

    def _should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed."""
        # Only process Python files
        if not file_path.endswith('.py'):
            return False

        # Ignore common patterns
        ignore_patterns = [
            '__pycache__',
            '.venv',
            'venv',
            '.git',
            '.mypy_cache',
            '.pytest_cache',
            'node_modules',
        ]

        for pattern in ignore_patterns:
            if pattern in file_path:
                return False

        return True

    def _schedule_change(self, file_path: str):
        """Schedule a file change for processing with debouncing."""
        if not self._should_process_file(file_path):
            return

        # Record the change time
        self._pending_changes[file_path] = time.time()

        # Schedule debounced processing
        if self._event_loop and not (self._debounce_task and not self._debounce_task.done()):
            self._debounce_task = asyncio.run_coroutine_threadsafe(
                self._process_pending_changes(),
                self._event_loop
            )

    async def _process_pending_changes(self):
        """Process pending changes after debounce period."""
        await asyncio.sleep(self.debounce_seconds)

        current_time = time.time()
        files_to_process = []

        # Find files that haven't changed in debounce_seconds
        for file_path, change_time in list(self._pending_changes.items()):
            if current_time - change_time >= self.debounce_seconds:
                files_to_process.append(file_path)
                del self._pending_changes[file_path]

        # Process each file
        for file_path in files_to_process:
            try:
                logger.info(f"Processing file change: {file_path}")
                await self.on_change_callback(file_path)
            except Exception as e:
                logger.error(f"Error processing file change {file_path}: {e}", exc_info=True)

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            logger.debug(f"File modified: {event.src_path}")
            self._schedule_change(event.src_path)

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            logger.debug(f"File created: {event.src_path}")
            self._schedule_change(event.src_path)

    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory and self._should_process_file(event.src_path):
            logger.info(f"File deleted: {event.src_path}")
            # For deletions, process immediately without debouncing
            if self._event_loop:
                asyncio.run_coroutine_threadsafe(
                    self.on_change_callback(event.src_path),
                    self._event_loop
                )


class FileWatcher:
    """Watches a directory for Python file changes and triggers reindexing."""

    def __init__(self,
                 watch_directory: Optional[str] = None,
                 on_change_callback: Optional[Callable[[str], Awaitable[None]]] = None,
                 debounce_seconds: float = 0.5):
        """
        Initialize file watcher.

        Args:
            watch_directory: Directory to watch (can be set later)
            on_change_callback: Async callback for file changes
            debounce_seconds: Debounce period for rapid changes
        """
        self.watch_directory = watch_directory
        self.on_change_callback = on_change_callback
        self.debounce_seconds = debounce_seconds

        self.observer: Optional[Observer] = None
        self.event_handler: Optional[CodeFileHandler] = None
        self._running = False

        logger.info("FileWatcher initialized")

    def set_callback(self, callback: Callable[[str], Awaitable[None]]):
        """Set the file change callback."""
        self.on_change_callback = callback

    def start(self, event_loop: asyncio.AbstractEventLoop):
        """
        Start watching for file changes.

        Args:
            event_loop: The event loop to use for async operations
        """
        if not self.watch_directory:
            logger.warning("No watch directory set, file watching disabled")
            return

        if not self.on_change_callback:
            logger.warning("No callback set, file watching disabled")
            return

        if self._running:
            logger.warning("FileWatcher already running")
            return

        # Create event handler
        self.event_handler = CodeFileHandler(
            on_change_callback=self.on_change_callback,
            debounce_seconds=self.debounce_seconds
        )
        self.event_handler.set_event_loop(event_loop)

        # Create observer
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            self.watch_directory,
            recursive=True
        )

        # Start observing
        self.observer.start()
        self._running = True

        logger.info(f"FileWatcher started for directory: {self.watch_directory}")

    def stop(self):
        """Stop watching for file changes."""
        if not self._running:
            return

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None

        self.event_handler = None
        self._running = False

        logger.info("FileWatcher stopped")

    def set_watch_directory(self, directory: str, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        Set or change the watched directory.

        Args:
            directory: New directory to watch
            event_loop: Event loop (required if starting)
        """
        was_running = self._running

        if was_running:
            self.stop()

        self.watch_directory = directory
        logger.info(f"Watch directory set to: {directory}")

        if was_running and event_loop:
            self.start(event_loop)

    @property
    def is_running(self) -> bool:
        """Check if watcher is currently running."""
        return self._running
