"""Supabase client factories kept separate from business logic."""

from supabase import Client, create_client

from app.core.config import Settings


def _required_secret_value(value: object, name: str) -> str:
    if value is None:
        raise RuntimeError(f"{name} is required before database operations can run.")
    return value.get_secret_value()


def create_publishable_client(settings: Settings) -> Client:
    """Create a client using the Supabase publishable key."""
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required before database operations can run.")
    return create_client(
        settings.supabase_url,
        _required_secret_value(
            settings.supabase_publishable_key,
            "SUPABASE_PUBLISHABLE_KEY",
        ),
    )


def create_secret_client(settings: Settings) -> Client:
    """Create a backend-only client. Never expose this key or client to React."""
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required before database operations can run.")
    return create_client(
        settings.supabase_url,
        _required_secret_value(
            settings.supabase_secret_key,
            "SUPABASE_SECRET_KEY",
        ),
    )
