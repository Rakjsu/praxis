"""Envio de teclas/cliques para o jogo via SendInput (Win32, ctypes).

Usa scancodes (KEYEVENTF_SCANCODE) em vez de virtual-keys porque a maioria
dos jogos DirectX só reconhece input nesse formato. Simuladores comuns
(pyautogui etc.) costumam ser ignorados por jogos — por isso o ctypes direto.
"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

# --- Estruturas Win32 -------------------------------------------------------

INPUT_KEYBOARD = 1
INPUT_MOUSE = 0

KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

ULONG_PTR = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTunion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTunion)]


_SendInput = ctypes.windll.user32.SendInput

# --- Mapa de scancodes (Set 1) ---------------------------------------------

SCANCODES: dict[str, int] = {
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06,
    "6": 0x07, "7": 0x08, "8": 0x09, "9": 0x0A, "0": 0x0B,
    "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14,
    "y": 0x15, "u": 0x16, "i": 0x17, "o": 0x18, "p": 0x19,
    "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21, "g": 0x22,
    "h": 0x23, "j": 0x24, "k": 0x25, "l": 0x26,
    "z": 0x2C, "x": 0x2D, "c": 0x2E, "v": 0x2F, "b": 0x30,
    "n": 0x31, "m": 0x32,
    "space": 0x39, "esc": 0x01, "tab": 0x0F, "enter": 0x1C,
    "lshift": 0x2A, "lctrl": 0x1D, "lalt": 0x38,
    "f1": 0x3B, "f2": 0x3C, "f3": 0x3D, "f4": 0x3E, "f5": 0x3F,
    "f6": 0x40, "f7": 0x41, "f8": 0x42, "f9": 0x43, "f10": 0x44,
    "f11": 0x57, "f12": 0x58,
}

# Teclas de mouse tratadas separadamente.
MOUSE_KEYS = {"mouse_left", "mouse_right"}


def available_keys() -> list[str]:
    return list(SCANCODES.keys()) + sorted(MOUSE_KEYS)


def _kb_event(scancode: int, keyup: bool) -> INPUT:
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if keyup else 0)
    ki = KEYBDINPUT(0, scancode, flags, 0, None)
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTunion(ki=ki))


def _mouse_event(flags: int) -> INPUT:
    mi = MOUSEINPUT(0, 0, 0, flags, 0, None)
    return INPUT(type=INPUT_MOUSE, u=_INPUTunion(mi=mi))


def _send(*events: INPUT) -> None:
    n = len(events)
    arr = (INPUT * n)(*events)
    _SendInput(n, arr, ctypes.sizeof(INPUT))


def tap(key: str, hold_ms: int = 30) -> bool:
    """Pressiona e solta uma tecla (ou botão do mouse). Retorna False se desconhecida."""
    key = key.strip().lower()

    if key == "mouse_left":
        _send(_mouse_event(MOUSEEVENTF_LEFTDOWN))
        time.sleep(hold_ms / 1000)
        _send(_mouse_event(MOUSEEVENTF_LEFTUP))
        return True
    if key == "mouse_right":
        _send(_mouse_event(MOUSEEVENTF_RIGHTDOWN))
        time.sleep(hold_ms / 1000)
        _send(_mouse_event(MOUSEEVENTF_RIGHTUP))
        return True

    sc = SCANCODES.get(key)
    if sc is None:
        return False
    _send(_kb_event(sc, keyup=False))
    time.sleep(hold_ms / 1000)
    _send(_kb_event(sc, keyup=True))
    return True
