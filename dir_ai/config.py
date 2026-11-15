"""Configuration loading and validation.

Environment is read explicitly (never at import time) so tests and the CLI can
fail cleanly before any UI is drawn.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from dotenv import load_dotenv

PROVIDERS: tuple[str, ...] = ("gemini", "groq", "mistral", "ollama", "lmstudio")

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "mistral": "mistral-small-latest",
    "ollama": "qwen2.5-coder:7b",
    "lmstudio": "qwen2.5-coder-7b-instruct",
}

_KEY_VARS: dict[str, tuple[str, ...]] = {
    "gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "groq": ("GROQ_API_KEY",),
    "mistral": ("MISTRAL_API_KEY",),
}


class ConfigError(ValueError):
    """Raised when configuration is missing or invalid."""


def _text(env: Mapping[str, str], name: str, default: str = "") -> str:
    value = env.get(name, default)
    return value.strip() if isinstance(value, str) else default


def _number(env: Mapping[str, str], name: str, default: float, cast: type) -> float:
    raw = _text(env, name)
    if not raw:
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}.") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings for a single DIR-AI session."""

    provider: str = "gemini"
    model: str = ""
    temperature: float = 0.2
    timeout: float = 120.0
    max_iterations: int = 20
    max_tool_output_chars: int = 20_000
    google_api_key: str | None = None
    groq_api_key: str | None = None
    mistral_api_key: str | None = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, *, load_file: bool = False) -> Settings:
        if load_file:
            load_dotenv(override=False)
        source: Mapping[str, str] = os.environ if env is None else env

        google_key = _text(source, "GOOGLE_API_KEY") or _text(source, "GEMINI_API_KEY") or None
        groq_key = _text(source, "GROQ_API_KEY") or None
        mistral_key = _text(source, "MISTRAL_API_KEY") or None

        provider = _text(source, "DIRAI_PROVIDER", "gemini").lower()
        model = _text(source, "DIRAI_MODEL") or DEFAULT_MODELS.get(provider, "")

        settings = cls(
            provider=provider,
            model=model,
            temperature=_number(source, "DIRAI_TEMPERATURE", 0.2, float),
            timeout=_number(source, "DIRAI_TIMEOUT", 120.0, float),
            max_iterations=int(_number(source, "DIRAI_MAX_ITERATIONS", 20, int)),
            max_tool_output_chars=int(_number(source, "DIRAI_MAX_TOOL_OUTPUT", 20_000, int)),
            google_api_key=google_key,
            groq_api_key=groq_key,
            mistral_api_key=mistral_key,
            ollama_base_url=_text(source, "OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            lmstudio_base_url=_text(source, "LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1"),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.provider not in PROVIDERS:
            raise ConfigError(
                f"Unknown provider {self.provider!r}. Choose one of: {', '.join(PROVIDERS)}."
            )
        if not self.model:
            raise ConfigError(f"Provider {self.provider!r} has no default model; set DIRAI_MODEL.")
        if not 0.0 <= self.temperature <= 2.0:
            raise ConfigError("DIRAI_TEMPERATURE must be between 0 and 2.")
        if self.timeout <= 0:
            raise ConfigError("DIRAI_TIMEOUT must be greater than zero.")
        if self.max_iterations < 1:
            raise ConfigError("DIRAI_MAX_ITERATIONS must be at least 1.")
        if self.requires_key and not self.api_key:
            names = " or ".join(_KEY_VARS[self.provider])
            raise ConfigError(
                f"Provider {self.provider!r} requires {names}.\n"
                "Copy .env.example to .env and set the key, or choose a local provider."
            )

    @property
    def requires_key(self) -> bool:
        return self.provider in _KEY_VARS

    @property
    def api_key(self) -> str | None:
        if self.provider == "gemini":
            return self.google_api_key
        if self.provider == "groq":
            return self.groq_api_key
        if self.provider == "mistral":
            return self.mistral_api_key
        return None

    @property
    def base_url(self) -> str | None:
        if self.provider == "ollama":
            return self.ollama_base_url
        if self.provider == "lmstudio":
            return self.lmstudio_base_url
        return None

    def with_overrides(self, **overrides: Any) -> Settings:
        clean = {key: value for key, value in overrides.items() if value is not None}
        updated = replace(self, **clean)
        updated.validate()
        return updated

    def redacted(self) -> dict[str, object]:
        """A log-safe view: keys become presence flags, never values."""

        def flag(value: str | None) -> str:
            return "<set>" if value else "<missing>"

        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "google_api_key": flag(self.google_api_key),
            "groq_api_key": flag(self.groq_api_key),
            "mistral_api_key": flag(self.mistral_api_key),
            "ollama_base_url": self.ollama_base_url,
            "lmstudio_base_url": self.lmstudio_base_url,
        }
