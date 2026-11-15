from __future__ import annotations

import pytest

from dir_ai import __version__
from dir_ai.main import build_parser, main


def test_package_imports() -> None:
    import dir_ai
    import dir_ai.config
    import dir_ai.main

    assert dir_ai.__version__ == __version__


def test_help_works_without_credentials() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_missing_key_returns_exit_code_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DIRAI_PROVIDER", "gemini")
    assert main(["--no-boot"]) == 2
    assert "Configuration error" in capsys.readouterr().err


def test_fake_llm_flag_parses() -> None:
    args = build_parser().parse_args(["--fake-llm", "--no-boot"])
    assert args.fake_llm is True
    assert args.no_boot is True
