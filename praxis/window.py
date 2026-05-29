"""Detecção da janela em foco (para o foreground-gating).

Permite que o motor só envie input quando a janela alvo está em primeiro plano,
evitando disparar teclas em outros aplicativos por engano.
"""

from __future__ import annotations


def foreground_title() -> str:
    """Título da janela atualmente em foco. Retorna "" se não for possível obter."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ""
    except Exception:
        return ""


def matches(target: str) -> bool:
    """True se `target` está vazio (sem gating) ou é substring do título em foco."""
    target = (target or "").strip().lower()
    if not target:
        return True
    return target in foreground_title().lower()
