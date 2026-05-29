"""Hotkey global de liga/desliga usando a biblioteca `keyboard`.

O `keyboard` instala um hook de baixo nível no Windows, então a tecla é
capturada mesmo com o jogo em foco. Usamos apenas para detectar a tecla —
o envio de input para o jogo é feito pelo `sender` (SendInput).
"""

from __future__ import annotations

from typing import Callable

try:
    import keyboard  # type: ignore
    _AVAILABLE = True
except Exception:  # pragma: no cover - dependência opcional
    keyboard = None  # type: ignore
    _AVAILABLE = False


class HotkeyManager:
    def __init__(self) -> None:
        self._handle = None
        self._current: str | None = None

    @property
    def available(self) -> bool:
        return _AVAILABLE

    def register(self, hotkey: str, callback: Callable[[], None]) -> bool:
        """(Re)registra a hotkey global. Retorna True em caso de sucesso."""
        if not _AVAILABLE:
            return False
        self.unregister()
        try:
            self._handle = keyboard.add_hotkey(hotkey, callback)
            self._current = hotkey
            return True
        except Exception:
            self._handle = None
            self._current = None
            return False

    def unregister(self) -> None:
        if _AVAILABLE and self._handle is not None:
            try:
                keyboard.remove_hotkey(self._handle)
            except Exception:
                pass
        self._handle = None
        self._current = None
