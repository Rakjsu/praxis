"""Testes de config (perfis e settings) usando diretório temporário."""

import pytest

from praxis import config
from praxis.models import Profile, Settings, Skill


@pytest.fixture
def tmp_profiles(tmp_path, monkeypatch):
    pdir = tmp_path / "profiles"
    monkeypatch.setattr(config, "PROFILES_DIR", pdir)
    return pdir


def test_slug():
    assert config._slug("Diablo IV") == "diablo-iv"
    assert config._slug("  Path of Exile!! ") == "path-of-exile"
    assert config._slug("") == "perfil"


def test_profile_save_load_list_delete(tmp_profiles):
    prof = Profile(name="Meu Jogo", skills=[Skill(key="3")])
    path = config.save_profile(prof)
    assert path.exists()
    assert config.list_profiles() == [path.stem]

    loaded = config.load_profile(path.stem)
    assert loaded.name == "Meu Jogo"
    assert loaded.skills[0].key == "3"

    config.delete_profile(path.stem)
    assert config.list_profiles() == []


def test_settings_save_load(tmp_profiles):
    assert config.load_settings() == Settings()  # default quando não existe
    s = Settings(start_minimized=True, panic_key="f10")
    config.save_settings(s)
    assert config.load_settings() == s


def test_seed_defaults_copies_bundled(tmp_profiles):
    config.seed_defaults()
    # O perfil-semente (profiles/diablo.json do repo) deve ter sido copiado.
    assert any(tmp_profiles.glob("*.json"))
