"""Ícone na bandeja do sistema (system tray) via pystray.

O ícone roda numa thread própria. Os callbacks recebidos devem marshalar de
volta para a thread do Tkinter (o chamador usa `app.after(0, ...)`).
A dependência é opcional: se `pystray` não estiver disponível, a importação
desta classe falha e o app cai no comportamento sem tray.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pystray
from PIL import Image

_ICON = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"


class TrayController:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_toggle: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._on_show = on_show
        self._on_toggle = on_toggle
        self._on_quit = on_quit
        self._icon: pystray.Icon | None = None

    def _image(self) -> Image.Image:
        try:
            return Image.open(_ICON)
        except Exception:
            return Image.new("RGB", (64, 64), (99, 60, 255))

    def start(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Mostrar", lambda: self._on_show(), default=True),
            pystray.MenuItem("Iniciar / Parar", lambda: self._on_toggle()),
            pystray.MenuItem("Sair", lambda: self._quit()),
        )
        self._icon = pystray.Icon("praxis", self._image(), "Praxis", menu)
        # run_detached cria a própria thread e não bloqueia.
        self._icon.run_detached()

    def _quit(self) -> None:
        self._on_quit()
        self.stop()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
