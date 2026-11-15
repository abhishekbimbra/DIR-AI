"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from dir_ai.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        provider="gemini",
        model="gemini-test",
        google_api_key="test-key-not-real",
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A small fixture repo with a couple of files."""
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "notes.txt").write_text("hello\n", encoding="utf-8")
    return tmp_path
