"""API routers for CodeGraph backend."""

from .graph import router as graph_router
from .commits import router as commits_router
from .validation import router as validation_router
from .index import router as index_router
from .snapshots import router as snapshots_router
from .functions import router as functions_router
from .analysis import router as analysis_router
from .files import router as files_router
from .websocket import router as websocket_router
from .watch import router as watch_router

__all__ = [
    'graph_router',
    'commits_router',
    'validation_router',
    'index_router',
    'snapshots_router',
    'functions_router',
    'analysis_router',
    'files_router',
    'websocket_router',
    'watch_router',
]
