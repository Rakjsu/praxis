"""Sistema de versionamento (SemVer) do Praxis.

A versão tem fonte única em `praxis/__init__.py` (`__version__`). Este script
incrementa essa versão, atualiza o CHANGELOG (move a seção "Não lançado" para a
nova versão com data e cria uma nova seção vazia) e, opcionalmente, cria o
commit + tag git (que dispara o CI de release).

Uso:
    python tools/bump_version.py patch          # 0.1.0 -> 0.1.1
    python tools/bump_version.py minor          # 0.1.0 -> 0.2.0
    python tools/bump_version.py major          # 0.1.0 -> 1.0.0
    python tools/bump_version.py 1.4.2          # versão explícita
    python tools/bump_version.py patch --dry-run
    python tools/bump_version.py patch --git    # cria commit + tag local
    python tools/bump_version.py patch --git --push   # também faz push (dispara release)
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT = ROOT / "praxis" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"
REPO = "Rakjsu/praxis"

_VERSION_RE = re.compile(r'^__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', re.M)
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def read_version() -> tuple[int, int, int]:
    m = _VERSION_RE.search(INIT.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("Não encontrei __version__ em praxis/__init__.py")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def compute(cur: tuple[int, int, int], part: str) -> tuple[int, int, int]:
    major, minor, patch = cur
    if part == "major":
        return major + 1, 0, 0
    if part == "minor":
        return major, minor + 1, 0
    if part == "patch":
        return major, minor, patch + 1
    m = _SEMVER_RE.match(part)
    if not m:
        raise SystemExit(f"Argumento inválido: {part!r} (use major|minor|patch|X.Y.Z)")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def fmt(v: tuple[int, int, int]) -> str:
    return f"{v[0]}.{v[1]}.{v[2]}"


def update_init(new: str) -> None:
    text = INIT.read_text(encoding="utf-8")
    text = _VERSION_RE.sub(f'__version__ = "{new}"', text, count=1)
    INIT.write_text(text, encoding="utf-8")


def update_changelog(old: str, new: str) -> None:
    if not CHANGELOG.exists():
        return
    text = CHANGELOG.read_text(encoding="utf-8")
    today = datetime.date.today().isoformat()

    # Move o conteúdo de "Não lançado" para a nova versão e recria a seção vazia.
    marker = "## [Não lançado]"
    idx = text.find(marker)
    if idx != -1:
        after = idx + len(marker)
        nxt = text.find("\n## [", after)
        if nxt == -1:
            nxt = len(text)
        body = text[after:nxt].strip("\n")
        if not body.strip():
            body = "### Alterado\n- _(sem notas)_"
        replacement = (
            f"{marker}\n\n"
            f"## [{new}] - {today}\n{body}\n"
        )
        text = text[:idx] + replacement + text[nxt:]

    # Atualiza os links de comparação no rodapé.
    text = re.sub(
        r"\[Não lançado\]:.*",
        f"[Não lançado]: https://github.com/{REPO}/compare/v{new}...HEAD",
        text,
        count=1,
    )
    new_link = f"[{new}]: https://github.com/{REPO}/compare/v{old}...v{new}"
    if f"\n[{new}]:" not in text:
        text = re.sub(
            r"(\[Não lançado\]:.*\n)",
            r"\1" + new_link + "\n",
            text,
            count=1,
        )
    CHANGELOG.write_text(text, encoding="utf-8")


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Bump de versão do Praxis (SemVer).")
    ap.add_argument("part", help="major | minor | patch | X.Y.Z")
    ap.add_argument("--dry-run", action="store_true", help="mostra sem gravar")
    ap.add_argument("--git", action="store_true", help="cria commit + tag local")
    ap.add_argument("--push", action="store_true", help="faz push (dispara o release no CI)")
    args = ap.parse_args()

    cur = read_version()
    new = compute(cur, args.part)
    old_s, new_s = fmt(cur), fmt(new)

    if new <= cur:
        raise SystemExit(f"Nova versão {new_s} não é maior que a atual {old_s}.")

    print(f"Versão: {old_s} -> {new_s}")
    if args.dry_run:
        print("(dry-run) nenhuma alteração gravada.")
        return 0

    update_init(new_s)
    update_changelog(old_s, new_s)
    print(f"Atualizado: praxis/__init__.py e CHANGELOG.md")

    if args.git or args.push:
        git("add", "praxis/__init__.py", "CHANGELOG.md")
        git("commit", "-m", f"chore: release v{new_s}")
        git("tag", f"v{new_s}")
        print(f"Commit + tag v{new_s} criados.")
        if args.push:
            git("push")
            git("push", "origin", f"v{new_s}")
            print(f"Push feito. O CI vai buildar e publicar o release v{new_s}.")
        else:
            print(f"Para publicar: git push && git push origin v{new_s}")
    else:
        print("Próximos passos:")
        print(f"  git add -A && git commit -m \"chore: release v{new_s}\"")
        print(f"  git tag v{new_s} && git push && git push origin v{new_s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
