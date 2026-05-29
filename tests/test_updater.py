"""Testes do auto-update (sem rede — _fetch_latest é mockado)."""

import hashlib

from praxis import updater


def test_parse_version():
    assert updater.parse_version("v1.2.3") == (1, 2, 3)
    assert updater.parse_version("0.1.0") == (0, 1, 0)
    # Sufixo não-numérico vira 0 (pré-release não conta como mais novo).
    assert updater.parse_version("v2.0.0-beta1") == (2, 0, 0, 0)
    assert updater.parse_version("2.0.0-3") == (2, 0, 0, 3)


def test_is_newer():
    assert updater.is_newer("0.2.0", "0.1.0") is True
    assert updater.is_newer("0.1.0", "0.1.0") is False
    assert updater.is_newer("1.0.0", "0.9.9") is True


def _fake_release(tag="v9.9.9"):
    return {
        "tag_name": tag,
        "html_url": "https://github.com/Rakjsu/praxis/releases/tag/" + tag,
        "assets": [
            {"name": "Praxis-Setup-9.9.9.exe",
             "browser_download_url": "https://x/Praxis-Setup-9.9.9.exe"},
            {"name": "Praxis-Setup-9.9.9.exe.sha256",
             "browser_download_url": "https://x/Praxis-Setup-9.9.9.exe.sha256"},
        ],
    }


def test_check_for_update_finds_newer(monkeypatch):
    monkeypatch.setattr(updater, "_fetch_latest", lambda repo: _fake_release())
    info = updater.check_for_update("0.1.0", "Rakjsu/praxis")
    assert info is not None
    assert info.version == "9.9.9"
    assert info.download_url.endswith(".exe")
    assert info.sha256_url.endswith(".sha256")


def test_check_for_update_when_current_is_latest(monkeypatch):
    monkeypatch.setattr(updater, "_fetch_latest", lambda repo: _fake_release("v0.1.0"))
    assert updater.check_for_update("0.1.0", "Rakjsu/praxis") is None


def test_check_for_update_no_data(monkeypatch):
    monkeypatch.setattr(updater, "_fetch_latest", lambda repo: None)
    assert updater.check_for_update("0.1.0", "Rakjsu/praxis") is None


def test_expected_hash_parsing():
    h = "a" * 64
    assert updater._expected_hash(f"{h}  Praxis-Setup.exe") == h
    assert updater._expected_hash(h + "\n") == h
    assert updater._expected_hash("") == ""


def test_verify_file(tmp_path):
    f = tmp_path / "blob.bin"
    f.write_bytes(b"praxis-update")
    digest = hashlib.sha256(b"praxis-update").hexdigest()
    assert updater.verify_file(str(f), digest) is True
    assert updater.verify_file(str(f), "deadbeef") is False
    assert updater.verify_file(str(f), "") is False
