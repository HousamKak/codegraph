"""CodeGraph - A graph database analyzer for Python codebases with snapshot comparison."""

__version__ = "0.2.0"

from .db import CodeGraphDB
from .parser import PythonParser
from .builder import GraphBuilder
from .query import QueryInterface
from .validators import ConservationValidator
from .snapshot import SnapshotManager

__all__ = [
    "CodeGraphDB",
    "PythonParser",
    "GraphBuilder",
    "QueryInterface",
    "ConservationValidator",
    "SnapshotManager",
]
