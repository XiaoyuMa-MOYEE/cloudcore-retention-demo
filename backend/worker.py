"""Cloudflare Python Worker entrypoint for the FastAPI demo."""

from workers import asgi

from cloudflare_app import app

Default = asgi.entrypoint(app)
