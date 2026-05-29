"""Auto-update via GitHub Releases (apenas stdlib).

Consulta a API pública de releases do repositório, compara a tag mais recente
com a versão atual e, se houver uma versão nova, baixa o instalador anexado ao
release e o executa para atualizar o app.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass

from . import __repo__, __version__

API_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
_TIMEOUT = 8


@dataclass
class UpdateInfo:
    version: str
    download_url: str | None
    release_url: str


def parse_version(text: str) -> tuple[int, ...]:
    """Converte 'v1.2.3' -> (1, 2, 3). Partes não-numéricas viram 0."""
    text = text.strip().lstrip("vV")
    parts = re.split(r"[.\-+]", text)
    out: list[int] = []
    for p in parts:
        m = re.match(r"\d+", p)
        out.append(int(m.group()) if m else 0)
    return tuple(out) or (0,)


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


def _fetch_latest(repo: str) -> dict | None:
    url = API_LATEST.format(repo=repo)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Praxis-Updater",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def check_for_update(
    current: str = __version__, repo: str = __repo__
) -> UpdateInfo | None:
    """Retorna UpdateInfo se houver versão mais nova publicada; senão None."""
    data = _fetch_latest(repo)
    if not data:
        return None
    tag = str(data.get("tag_name", "")).strip()
    if not tag or not is_newer(tag, current):
        return None

    download_url = None
    for asset in data.get("assets", []):
        name = str(asset.get("name", "")).lower()
        if name.endswith(".exe"):
            download_url = asset.get("browser_download_url")
            break
    return UpdateInfo(
        version=tag.lstrip("vV"),
        download_url=download_url,
        release_url=data.get("html_url", f"https://github.com/{repo}/releases"),
    )


def download_and_run(url: str) -> bool:
    """Baixa o instalador para %TEMP% e o executa. Retorna True se iniciou."""
    try:
        dest = os.path.join(tempfile.gettempdir(), "Praxis-Setup-update.exe")
        req = urllib.request.Request(url, headers={"User-Agent": "Praxis-Updater"})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp, open(
            dest, "wb"
        ) as fh:
            fh.write(resp.read())
        if sys.platform == "win32":
            os.startfile(dest)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([dest])
        return True
    except Exception:
        return False
