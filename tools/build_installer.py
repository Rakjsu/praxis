"""Compila o instalador do Praxis (Inno Setup) com a versão da fonte única.

Lê `__version__` de `praxis/__init__.py`, garante que `dist/Praxis.exe` existe
(buildando se necessário) e chama o ISCC passando `/DMyAppVersion=<versão>`.

Uso:
    python tools/build_installer.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from praxis import __version__  # noqa: E402

ISS = ROOT / "installer" / "praxis.iss"
EXE = ROOT / "dist" / "Praxis.exe"

_ISCC_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


def find_iscc() -> Path | None:
    for c in _ISCC_CANDIDATES:
        if c.exists():
            return c
    return None


def main() -> int:
    iscc = find_iscc()
    if iscc is None:
        print("ISCC.exe (Inno Setup) não encontrado.")
        print("Instale com: winget install -e --id JRSoftware.InnoSetup")
        return 1

    if not EXE.exists():
        print("dist/Praxis.exe ausente; rodando build do executável...")
        subprocess.run([sys.executable, str(ROOT / "tools" / "build.py")], check=True)

    cmd = [str(iscc), f"/DMyAppVersion={__version__}", str(ISS)]
    print("Executando:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        out = ROOT / "installer" / "Output" / f"Praxis-Setup-{__version__}.exe"
        print("\nOK ->", out)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
