r"""Carregamento e gravação de perfis em arquivos JSON.

Em desenvolvimento, os perfis ficam em `<repo>/profiles`. Quando o app roda
empacotado como `.exe` (PyInstaller, `sys.frozen`), essa pasta fica dentro de
"Arquivos de Programas" e é somente-leitura — então usamos
`%APPDATA%\Praxis\profiles`, que é gravável. O perfil padrão embutido é copiado
para lá na primeira execução por `seed_defaults()`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

from .models import Profile, Settings


def _profiles_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA", Path.home())) / "Praxis"
        return base / "profiles"
    return Path(__file__).resolve().parent.parent / "profiles"


def _bundled_seed_dir() -> Path:
    """Pasta com perfis-semente embutidos no pacote (via PyInstaller --add-data)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", ".")) / "seed"
    return Path(__file__).resolve().parent.parent / "profiles"


PROFILES_DIR = _profiles_dir()


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "perfil"


def ensure_profiles_dir() -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def seed_defaults() -> None:
    """Copia os perfis-semente para a pasta do usuário se ela estiver vazia."""
    ensure_profiles_dir()
    if any(PROFILES_DIR.glob("*.json")):
        return
    seed = _bundled_seed_dir()
    if seed.exists() and seed.resolve() != PROFILES_DIR.resolve():
        for src in seed.glob("*.json"):
            shutil.copy2(src, PROFILES_DIR / src.name)


def list_profiles() -> list[str]:
    """Retorna os nomes (sem extensão) de todos os perfis salvos."""
    ensure_profiles_dir()
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def profile_path(name: str) -> Path:
    return PROFILES_DIR / f"{_slug(name)}.json"


def load_profile(stem: str) -> Profile:
    path = PROFILES_DIR / f"{stem}.json"
    with path.open("r", encoding="utf-8") as fh:
        return Profile.from_dict(json.load(fh))


def save_profile(profile: Profile) -> Path:
    ensure_profiles_dir()
    path = profile_path(profile.name)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(profile.to_dict(), fh, indent=2, ensure_ascii=False)
    return path


def delete_profile(stem: str) -> None:
    path = PROFILES_DIR / f"{stem}.json"
    path.unlink(missing_ok=True)


def settings_path() -> Path:
    return PROFILES_DIR.parent / "settings.json"


def load_settings() -> Settings:
    path = settings_path()
    if not path.exists():
        return Settings()
    try:
        with path.open("r", encoding="utf-8") as fh:
            return Settings.from_dict(json.load(fh))
    except Exception:
        return Settings()


def save_settings(settings: Settings) -> Path:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(settings.to_dict(), fh, indent=2, ensure_ascii=False)
    return path
