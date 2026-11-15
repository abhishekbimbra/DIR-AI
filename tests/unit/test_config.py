from __future__ import annotations

import pytest

from dir_ai.config import DEFAULT_MODELS, ConfigError, Settings


def test_defaults_with_google_key() -> None:
    settings = Settings.from_env({"GOOGLE_API_KEY": "abc"})
    assert settings.provider == "gemini"
    assert settings.model == DEFAULT_MODELS["gemini"]
    assert settings.api_key == "abc"
    assert settings.requires_key is True


def test_gemini_alias_is_accepted() -> None:
    settings = Settings.from_env({"GEMINI_API_KEY": "alias-key"})
    assert settings.google_api_key == "alias-key"


def test_google_key_wins_over_alias() -> None:
    settings = Settings.from_env({"GOOGLE_API_KEY": "primary", "GEMINI_API_KEY": "alias"})
    assert settings.google_api_key == "primary"


def test_local_provider_needs_no_key() -> None:
    settings = Settings.from_env({"DIRAI_PROVIDER": "ollama"})
    assert settings.provider == "ollama"
    assert settings.model == DEFAULT_MODELS["ollama"]
    assert settings.base_url == "http://127.0.0.1:11434"


def test_lmstudio_base_url_override() -> None:
    settings = Settings.from_env(
        {"DIRAI_PROVIDER": "lmstudio", "LMSTUDIO_BASE_URL": "http://localhost:9999/v1"}
    )
    assert settings.base_url == "http://localhost:9999/v1"


def test_missing_key_fails_clearly() -> None:
    with pytest.raises(ConfigError) as exc:
        Settings.from_env({})
    message = str(exc.value)
    assert "GOOGLE_API_KEY" in message
    assert "GEMINI_API_KEY" in message
    assert ".env" in message


def test_unknown_provider_fails() -> None:
    with pytest.raises(ConfigError, match="Unknown provider"):
        Settings.from_env({"GOOGLE_API_KEY": "x", "DIRAI_PROVIDER": "nope"})


@pytest.mark.parametrize(
    ("env", "match"),
    [
        ({"DIRAI_TEMPERATURE": "hot"}, "must be a number"),
        ({"DIRAI_TEMPERATURE": "9"}, "between 0 and 2"),
        ({"DIRAI_TIMEOUT": "0"}, "greater than zero"),
        ({"DIRAI_MAX_ITERATIONS": "0"}, "at least 1"),
    ],
)
def test_invalid_numbers_fail(env: dict[str, str], match: str) -> None:
    with pytest.raises(ConfigError, match=match):
        Settings.from_env({"GOOGLE_API_KEY": "x", **env})


def test_redacted_never_contains_secret(settings: Settings) -> None:
    view = settings.redacted()
    assert view["google_api_key"] == "<set>"
    assert "test-key-not-real" not in str(view)


def test_with_overrides_revalidates(settings: Settings) -> None:
    updated = settings.with_overrides(model="other-model")
    assert updated.model == "other-model"
    with pytest.raises(ConfigError):
        settings.with_overrides(provider="groq")
