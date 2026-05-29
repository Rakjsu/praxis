"""Modelos de dados do macro: Skill, PotionRule e Profile."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Skill:
    """Uma habilidade que dispara uma tecla em intervalo fixo.

    Se `hold=True`, a tecla é mantida pressionada enquanto o macro estiver ativo
    (ataque básico/skill canalizada), em vez de ser pressionada em intervalos.
    """

    name: str = "Skill"
    key: str = "1"
    interval_ms: int = 1000
    enabled: bool = True
    hold: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        return cls(
            name=data.get("name", "Skill"),
            key=str(data.get("key", "1")),
            interval_ms=int(data.get("interval_ms", 1000)),
            enabled=bool(data.get("enabled", True)),
            hold=bool(data.get("hold", False)),
        )


@dataclass
class ComboStep:
    """Um passo de um combo: pressiona `key` e espera `delay_ms` antes do próximo."""

    key: str = "1"
    delay_ms: int = 300

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ComboStep":
        return cls(
            key=str(data.get("key", "1")),
            delay_ms=int(data.get("delay_ms", 300)),
        )


@dataclass
class Combo:
    """Sequência ordenada de passos (rotação de build)."""

    enabled: bool = False
    loop: bool = True
    steps: list[ComboStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "loop": self.loop,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Combo":
        return cls(
            enabled=bool(data.get("enabled", False)),
            loop=bool(data.get("loop", True)),
            steps=[ComboStep.from_dict(s) for s in data.get("steps", [])],
        )


@dataclass
class PotionRule:
    """Regra de auto-poção: lê uma região da tela e usa poção quando a vida cai.

    A região é (x1, y1, x2, y2) em pixels da tela. Conta-se a fração de pixels
    cuja cor se aproxima de `color` (cor da vida cheia). Quando essa fração cai
    abaixo de `threshold_pct`, a tecla `key` é pressionada (respeitando cooldown).
    """

    enabled: bool = False
    key: str = "q"
    region: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    color: list[int] = field(default_factory=lambda: [190, 30, 30])  # vermelho da vida
    tolerance: int = 70
    threshold_pct: float = 0.45
    cooldown_ms: int = 2000

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PotionRule":
        return cls(
            enabled=bool(data.get("enabled", False)),
            key=str(data.get("key", "q")),
            region=list(data.get("region", [0, 0, 0, 0])),
            color=list(data.get("color", [190, 30, 30])),
            tolerance=int(data.get("tolerance", 70)),
            threshold_pct=float(data.get("threshold_pct", 0.45)),
            cooldown_ms=int(data.get("cooldown_ms", 2000)),
        )

    def is_configured(self) -> bool:
        x1, y1, x2, y2 = self.region
        return self.enabled and x2 > x1 and y2 > y1


@dataclass
class Settings:
    """Configurações globais do app (não pertencem a um perfil específico)."""

    start_minimized: bool = False
    overlay_enabled: bool = True
    panic_key: str = "f9"
    log_to_file: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        return cls(
            start_minimized=bool(data.get("start_minimized", False)),
            overlay_enabled=bool(data.get("overlay_enabled", True)),
            panic_key=str(data.get("panic_key", "f9")),
            log_to_file=bool(data.get("log_to_file", False)),
        )


@dataclass
class Profile:
    """Perfil de macro para um jogo específico."""

    name: str = "Novo Perfil"
    toggle_hotkey: str = "f8"
    skills: list[Skill] = field(default_factory=list)
    potion: PotionRule = field(default_factory=PotionRule)
    resource: PotionRule = field(default_factory=lambda: PotionRule(key="w", color=[40, 80, 200]))
    combo: Combo = field(default_factory=Combo)
    target_window: str = ""
    jitter_pct: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "toggle_hotkey": self.toggle_hotkey,
            "skills": [s.to_dict() for s in self.skills],
            "potion": self.potion.to_dict(),
            "resource": self.resource.to_dict(),
            "combo": self.combo.to_dict(),
            "target_window": self.target_window,
            "jitter_pct": self.jitter_pct,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        return cls(
            name=data.get("name", "Novo Perfil"),
            toggle_hotkey=str(data.get("toggle_hotkey", "f8")),
            skills=[Skill.from_dict(s) for s in data.get("skills", [])],
            potion=PotionRule.from_dict(data.get("potion", {})),
            resource=PotionRule.from_dict(
                data.get("resource", {"key": "w", "color": [40, 80, 200]})
            ),
            combo=Combo.from_dict(data.get("combo", {})),
            target_window=str(data.get("target_window", "")),
            jitter_pct=int(data.get("jitter_pct", 0)),
        )
