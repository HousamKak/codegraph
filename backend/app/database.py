"""Database connection management with snapshot support."""

import os
from codegraph import CodeGraphDB, QueryInterface, ConservationValidator, SnapshotManager
from codegraph.git_snapshot import GitSnapshotManager
from .config import settings


class DatabaseManager:
    """Manages database connections and provides access to analysis services."""

    def __init__(self):
        self.db: CodeGraphDB = None
        self.query: QueryInterface = None
        self.validator: ConservationValidator = None
        self.snapshot_manager: SnapshotManager = None
        self.git_snapshot_manager: GitSnapshotManager = None

    def connect(self):
        """Connect to Neo4j database."""
        self.db = CodeGraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        self.query = QueryInterface(self.db)
        self.validator = ConservationValidator(self.db)
        self.snapshot_manager = SnapshotManager(self.db, storage_dir=settings.snapshot_storage_path)

        # Initialize git snapshot manager if repo path is configured
        repo_path = settings.repo_path or os.getcwd()

        # Search up directory tree for .git folder
        search_path = repo_path
        git_dir = None
        while search_path:
            potential_git = os.path.join(search_path, '.git')
            if os.path.exists(potential_git):
                git_dir = potential_git
                repo_path = search_path
                break
            parent = os.path.dirname(search_path)
            if parent == search_path:  # Reached root
                break
            search_path = parent

        if git_dir:
            git_storage = os.path.join(settings.snapshot_storage_path, 'git')
            self.git_snapshot_manager = GitSnapshotManager(repo_path, git_storage, self.db)

    def disconnect(self):
        """Disconnect from database."""
        if self.db:
            self.db.close()
            self.db = None
            self.query = None
            self.validator = None
            self.snapshot_manager = None
            self.git_snapshot_manager = None

    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self.db is not None


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> CodeGraphDB:
    """Get database instance."""
    if not db_manager.is_connected():
        db_manager.connect()
    return db_manager.db


def get_query() -> QueryInterface:
    """Get query interface instance."""
    if not db_manager.is_connected():
        db_manager.connect()
    return db_manager.query


def get_validator() -> ConservationValidator:
    """Get validator instance."""
    if not db_manager.is_connected():
        db_manager.connect()
    return db_manager.validator


def get_snapshot_manager() -> SnapshotManager:
    """Get snapshot manager instance."""
    if not db_manager.is_connected():
        db_manager.connect()
    return db_manager.snapshot_manager


def get_git_snapshot_manager() -> GitSnapshotManager:
    """Get git snapshot manager instance."""
    if not db_manager.is_connected():
        db_manager.connect()
    return db_manager.git_snapshot_manager
