"""Testes do foreground-gating."""

from praxis import window


def test_matches_empty_is_always_true():
    assert window.matches("") is True
    assert window.matches("   ") is True


def test_matches_substring(monkeypatch):
    monkeypatch.setattr(window, "foreground_title", lambda: "Diablo IV")
    assert window.matches("diablo") is True
    assert window.matches("Diablo IV") is True
    assert window.matches("starcraft") is False


def test_foreground_title_returns_str():
    assert isinstance(window.foreground_title(), str)
