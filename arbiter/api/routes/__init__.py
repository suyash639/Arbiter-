"""
arbiter/api/routes
------------------
API route module definitions.
"""

from arbiter.api.routes.health import router as health_router
from arbiter.api.routes.metadata import router as metadata_router
from arbiter.api.routes.query import router as query_router

__all__ = ["health_router", "metadata_router", "query_router"]
