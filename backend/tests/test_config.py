from app.core.config import Settings


def test_configuration_loads_and_redacts_backend_secret() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        frontend_origins="http://localhost:5173,http://localhost:3000",
        supabase_secret_key="not-a-real-secret",
    )

    assert settings.environment == "test"
    assert settings.frontend_origins == (
        "http://localhost:5173",
        "http://localhost:3000",
    )
    assert "not-a-real-secret" not in str(settings.model_dump())
    assert settings.supabase_secret_key is not None
    assert settings.supabase_secret_key.get_secret_value() == "not-a-real-secret"


def test_configuration_parses_a_dotenv_style_frontend_origin() -> None:
    settings = Settings(
        _env_file=None,
        FRONTEND_ORIGIN="http://localhost:5173,http://localhost:3000",
    )

    assert settings.frontend_origins == (
        "http://localhost:5173",
        "http://localhost:3000",
    )
