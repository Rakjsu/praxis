"""Modelos de dados do macro: Skill, PotionRule e Profile."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Skill:
    """Uma habilidade que dispara uma tecla em intervalo fixo."""

    name: str = "Skill"
    key: str = "1"
    interval_ms: int = 1000
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        return cls(
            name=data.get("name", "Skill"),
            key=str(data.get("key", "1")),
            interval_ms=int(data.get("interval_ms", 1000)),
            enabled=bool(data.get("enabled", True)),
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
class Profile:
    """Perfil de macro para um jogo específico."""

    name: str = "Novo Perfil"
    toggle_hotkey: str = "f8"
    skills: list[Skill] = field(default_factory=list)
    potion: PotionRule = field(default_factory=PotionRule)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "toggle_hotkey": self.toggle_hotkey,
            "skills": [s.to_dict() for s in self.skills],
            "potion": self.potion.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        return cls(
            name=data.get("name", "Novo Perfil"),
            toggle_hotkey=str(data.get("toggle_hotkey", "f8")),
            skills=[Skill.from_dict(s) for s in data.get("skills", [])],
            potion=PotionRule.from_dict(data.get("potion", {})),
        )
