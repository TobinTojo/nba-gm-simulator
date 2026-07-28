"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.game import router as game_router
from app.routers.leaderboard import router as leaderboard_router
from app.routers.multiplayer import router as multiplayer_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.app_name,
    description="Name Rush basketball initials game API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")
app.include_router(multiplayer_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Name Rush Game API", "docs": "/docs"}
