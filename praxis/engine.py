"""Motor do macro: roda numa thread e dispara skills + auto-poção.

O loop é desenhado para ser leve (sleep curto) e respeitar o intervalo de cada
skill e o cooldown da poção de forma independente, usando timestamps.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from . import screen, sender
from .models import Profile

# Log callback: recebe uma string para a UI exibir.
LogFn = Callable[[str], None]


class MacroEngine:
    def __init__(self, log: LogFn | None = None) -> None:
        self._log = log or (lambda _msg: None)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._profile: Profile | None = None
        self._lock = threading.Lock()
        self.last_health: float | None = None  # última fração de vida lida

    # --- estado ------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def set_profile(self, profile: Profile) -> None:
        with self._lock:
            self._profile = profile

    # --- controle ----------------------------------------------------------

    def start(self, profile: Profile) -> None:
        if self.running:
            return
        self.set_profile(profile)
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._log("[ON] Macro ativado")

    def stop(self) -> None:
        if not self.running:
            return
        self._stop.set()
        self._thread.join(timeout=1.0)
        self.last_health = None
        self._log("[OFF] Macro desativado")

    def toggle(self, profile: Profile) -> bool:
        if self.running:
            self.stop()
            return False
        self.start(profile)
        return True

    # --- loop --------------------------------------------------------------

    def _run(self) -> None:
        now = time.monotonic
        next_skill: dict[int, float] = {}
        next_potion = 0.0

        while not self._stop.is_set():
            with self._lock:
                profile = self._profile
            if profile is None:
                break

            t = now()

            # Skills
            for idx, skill in enumerate(profile.skills):
                if not skill.enabled:
                    continue
                due = next_skill.get(idx, 0.0)
                if t >= due:
                    if sender.tap(skill.key):
                        self._log(f"skill '{skill.name}' -> {skill.key}")
                    else:
                        self._log(f"[!] tecla desconhecida: {skill.key}")
                    next_skill[idx] = t + max(0.05, skill.interval_ms / 1000)

            # Auto-poção
            pot = profile.potion
            if pot.is_configured() and t >= next_potion:
                try:
                    frac = screen.health_fraction(pot.region, pot.color, pot.tolerance)
                except Exception as exc:  # captura de tela pode falhar pontualmente
                    self._log(f"[!] leitura de tela falhou: {exc}")
                    frac = 1.0
                self.last_health = frac
                if frac < pot.threshold_pct:
                    sender.tap(pot.key)
                    self._log(f"poção! vida~{frac:.0%} -> {pot.key}")
                    next_potion = t + max(0.2, pot.cooldown_ms / 1000)

            time.sleep(0.02)
