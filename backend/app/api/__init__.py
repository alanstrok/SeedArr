"""API routes."""
from fastapi import APIRouter

from app.api import connections, trackers, rules, torrents, system

api_router = APIRouter()

api_router.include_router(connections.router, prefix="/connections", tags=["connections"])
api_router.include_router(trackers.router, prefix="/trackers", tags=["trackers"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(torrents.router, prefix="/torrents", tags=["torrents"])
api_router.include_router(system.router, tags=["system"])
