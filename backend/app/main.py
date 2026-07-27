"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.game import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.app_name,
    description="NBA initials name-guessing game API",
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

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "NBA Initials Game API", "docs": "/docs"}
