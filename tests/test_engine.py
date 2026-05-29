"""Testes da lógica do motor: cast condicional e detecção de cooldown.

`sender` e `screen` são mockados para não enviar input nem capturar a tela.
"""

import pytest

from praxis import screen, sender
from praxis.engine import MacroEngine
from praxis.models import Skill


@pytest.fixture(autouse=True)
def no_io(monkeypatch):
    monkeypatch.setattr(sender, "tap", lambda k, hold_ms=30: True)
    monkeypatch.setattr(sender, "key_down", lambda k: True)
    monkeypatch.setattr(sender, "key_up", lambda k: True)


def test_condition_none_always_ok():
    e = MacroEngine()
    assert e._condition_ok(Skill(condition="none")) is True


def test_condition_health_below():
    e = MacroEngine()
    s = Skill(condition="health_below", condition_pct=40)
    e.last_health = 0.8
    assert e._condition_ok(s) is False
    e.last_health = 0.2
    assert e._condition_ok(s) is True


def test_condition_health_above():
    e = MacroEngine()
    s = Skill(condition="health_above", condition_pct=50)
    e.last_health = 0.8
    assert e._condition_ok(s) is True
    e.last_health = 0.3
    assert e._condition_ok(s) is False


def test_condition_resource_below():
    e = MacroEngine()
    s = Skill(condition="resource_below", condition_pct=25)
    e.last_resource = 0.5
    assert e._condition_ok(s) is False
    e.last_resource = 0.1
    assert e._condition_ok(s) is True


def test_condition_without_reading_is_ok():
    e = MacroEngine()
    s = Skill(condition="health_below", condition_pct=40)
    e.last_health = None
    assert e._condition_ok(s) is True  # não trava sem leitura


def test_skill_ready_no_check():
    e = MacroEngine()
    assert e._skill_ready(Skill(key="1")) is True


def test_skill_ready_with_cooldown(monkeypatch):
    e = MacroEngine()
    s = Skill(key="2", cooldown_region=[1, 2, 30, 10], ready_threshold=0.5)
    monkeypatch.setattr(screen, "health_fraction", lambda r, c, t: 0.9)
    assert e._skill_ready(s) is True
    monkeypatch.setattr(screen, "health_fraction", lambda r, c, t: 0.1)
    assert e._skill_ready(s) is False


def test_skill_ready_read_failure_does_not_block(monkeypatch):
    e = MacroEngine()
    s = Skill(key="2", cooldown_region=[1, 2, 30, 10])

    def boom(*a):
        raise RuntimeError("captura falhou")

    monkeypatch.setattr(screen, "health_fraction", boom)
    assert e._skill_ready(s) is True
