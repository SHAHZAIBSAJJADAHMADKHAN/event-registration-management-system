"""Test configuration."""

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(autouse=True)
def deterministic_jwt_settings(monkeypatch: pytest.MonkeyPatch):
    """Supply non-secret backend settings so auth tests reach their intended assertions."""
    from app.core.config import get_settings
    from app.core.security import _build_jwt_verifier

    monkeypatch.setenv("SUPABASE_JWT_ISSUER", "https://auth.example.test")
    monkeypatch.setenv(
        "SUPABASE_JWKS_URL", "https://auth.example.test/.well-known/jwks.json"
    )
    monkeypatch.setenv("SUPABASE_URL", "https://project.example.test")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-only-secret-key")
    get_settings.cache_clear()
    _build_jwt_verifier.cache_clear()
    yield
    get_settings.cache_clear()
    _build_jwt_verifier.cache_clear()
