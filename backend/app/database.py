"""Database connection management."""

from codegraph import CodeGraphDB, QueryInterface, ConservationValidator
from .config import settings


class DatabaseManager:
    """Manages database connections and provides access to services."""

    def __init__(self):
        self.db: CodeGraphDB = None
        self.query: QueryInterface = None
        self.validator: ConservationValidator = None

    def connect(self):
        """Connect to Neo4j database."""
        self.db = CodeGraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        self.query = QueryInterface(self.db)
        self.validator = ConservationValidator(self.db)

    def disconnect(self):
        """Disconnect from database."""
        if self.db:
            self.db.close()
            self.db = None
            self.query = None
            self.validator = None

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
