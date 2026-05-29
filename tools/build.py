"""Build do executável do Praxis com PyInstaller.

Gera dist/Praxis.exe (onefile, sem console), embutindo o ícone e o perfil
padrão (como semente em `seed/`). Regenera o ícone antes, se necessário.

Uso:
    python tools/build.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON = ROOT / "assets" / "icon.ico"
SEED = ROOT / "profiles" / "diablo.json"


def main() -> int:
    if not ICON.exists():
        print("Ícone ausente; gerando...")
        subprocess.run([sys.executable, str(ROOT / "tools" / "make_icon.py")], check=True)

    # No Windows o separador de --add-data é ';'
    add_data = f"{SEED};seed"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", "Praxis",
        "--icon", str(ICON),
        "--add-data", add_data,
        str(ROOT / "run.py"),
    ]
    print("Executando:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print("\nOK ->", ROOT / "dist" / "Praxis.exe")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
