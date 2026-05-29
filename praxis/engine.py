"""Motor do macro: roda numa thread e dispara skills, combo e auto-poções.

O loop é leve (sleep curto) e respeita, de forma independente por timestamp:
intervalo de cada skill, passos do combo e cooldown de cada poção (vida/recurso).
Recursos: foreground-gating, skills em "hold", jitter de tempo e estatísticas.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Callable

from . import screen, sender, window
from .models import PotionRule, Profile

# Log callback: recebe uma string para a UI exibir.
LogFn = Callable[[str], None]


class MacroEngine:
    def __init__(self, log: LogFn | None = None) -> None:
        self._log = log or (lambda _msg: None)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._profile: Profile | None = None
        self._lock = threading.Lock()
        self._held: set[str] = set()

        # Estado exposto para overlay/UI.
        self.last_health: float | None = None
        self.last_resource: float | None = None
        self.casts = 0
        self.potions_used = 0
        self._started_at: float | None = None

    # --- estado ------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def uptime(self) -> float:
        return 0.0 if self._started_at is None else max(0.0, time.monotonic() - self._started_at)

    def set_profile(self, profile: Profile) -> None:
        with self._lock:
            self._profile = profile

    # --- controle ----------------------------------------------------------

    def start(self, profile: Profile) -> None:
        if self.running:
            return
        self.set_profile(profile)
        self._stop.clear()
        self.casts = 0
        self.potions_used = 0
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._log("[ON] Macro ativado")

    def stop(self) -> None:
        if not self.running:
            return
        self._stop.set()
        self._thread.join(timeout=1.0)
        self._release_held()
        self.last_health = None
        self.last_resource = None
        self._started_at = None
        self._log("[OFF] Macro desativado")

    def toggle(self, profile: Profile) -> bool:
        if self.running:
            self.stop()
            return False
        self.start(profile)
        return True

    # --- helpers -----------------------------------------------------------

    def _jitter(self, ms: float, jitter_pct: int) -> float:
        base = max(0.05, ms / 1000)
        if jitter_pct <= 0:
            return base
        j = min(0.9, jitter_pct / 100)
        return base * random.uniform(1 - j, 1 + j)

    def _press_held(self, profile: Profile) -> None:
        for skill in profile.skills:
            if skill.enabled and skill.hold and skill.key not in self._held:
                if sender.key_down(skill.key):
                    self._held.add(skill.key)

    def _release_held(self) -> None:
        for key in list(self._held):
            sender.key_up(key)
        self._held.clear()

    def _run_potion(
        self, rule: PotionRule, label: str, now_t: float, due: float
    ) -> tuple[float | None, float]:
        """Lê a barra e usa a poção se preciso. Retorna (fração_lida, próximo_due)."""
        if not rule.is_configured():
            return (None, due)
        if now_t < due:
            return (None, due)
        try:
            frac = screen.health_fraction(rule.region, rule.color, rule.tolerance)
        except Exception as exc:
            self._log(f"[!] leitura de tela ({label}) falhou: {exc}")
            frac = 1.0
        if frac < rule.threshold_pct:
            sender.tap(rule.key)
            self.potions_used += 1
            self._log(f"poção ({label})! {frac:.0%} -> {rule.key}")
            return (frac, now_t + max(0.2, rule.cooldown_ms / 1000))
        return (frac, due)

    # --- loop --------------------------------------------------------------

    def _run(self) -> None:
        now = time.monotonic
        next_skill: dict[int, float] = {}
        next_potion = 0.0
        next_resource = 0.0
        next_combo = 0.0
        combo_idx = 0
        was_active = True

        while not self._stop.is_set():
            with self._lock:
                profile = self._profile
            if profile is None:
                break

            active = window.matches(profile.target_window)
            if active and not was_active:
                self._press_held(profile)  # recuperou o foco
            elif not active and was_active:
                self._release_held()  # perdeu o foco
            was_active = active

            if not active:
                time.sleep(0.05)
                continue

            self._press_held(profile)
            t = now()

            # Skills por intervalo (as em hold não entram aqui)
            for idx, skill in enumerate(profile.skills):
                if not skill.enabled or skill.hold:
                    continue
                if t >= next_skill.get(idx, 0.0):
                    if sender.tap(skill.key):
                        self.casts += 1
                        self._log(f"skill '{skill.name}' -> {skill.key}")
                    else:
                        self._log(f"[!] tecla desconhecida: {skill.key}")
                    next_skill[idx] = t + self._jitter(skill.interval_ms, profile.jitter_pct)

            # Combo / sequência ordenada
            combo = profile.combo
            if combo.enabled and combo.steps and t >= next_combo:
                if combo_idx >= len(combo.steps):
                    combo_idx = 0 if combo.loop else len(combo.steps)
                if combo_idx < len(combo.steps):
                    step = combo.steps[combo_idx]
                    if sender.tap(step.key):
                        self.casts += 1
                        self._log(f"combo[{combo_idx}] -> {step.key}")
                    next_combo = t + self._jitter(step.delay_ms, profile.jitter_pct)
                    combo_idx += 1

            # Auto-poções (vida e recurso)
            frac_h, next_potion = self._run_potion(profile.potion, "vida", t, next_potion)
            if frac_h is not None:
                self.last_health = frac_h
            frac_r, next_resource = self._run_potion(profile.resource, "recurso", t, next_resource)
            if frac_r is not None:
                self.last_resource = frac_r

            time.sleep(0.02)

        self._release_held()
