"""Cloudflare Python Worker entrypoint for the FastAPI demo."""

from workers import asgi

from backend.cloudflare_app import app

Default = asgi.entrypoint(app)
