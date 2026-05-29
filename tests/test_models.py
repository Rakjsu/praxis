"""Testes de round-trip dos modelos."""

from praxis.models import Combo, ComboStep, PotionRule, Profile, Settings, Skill


def test_skill_roundtrip():
    s = Skill(name="Fireball", key="2", interval_ms=1234, enabled=False, hold=True)
    assert Skill.from_dict(s.to_dict()) == s


def test_combo_roundtrip():
    c = Combo(enabled=True, loop=False, steps=[ComboStep("1", 200), ComboStep("2", 400)])
    back = Combo.from_dict(c.to_dict())
    assert back == c
    assert [s.key for s in back.steps] == ["1", "2"]


def test_combo_defaults():
    assert Combo.from_dict({}) == Combo()


def test_potion_roundtrip_and_is_configured():
    p = PotionRule(enabled=True, key="q", region=[10, 20, 110, 60], threshold_pct=0.3)
    assert PotionRule.from_dict(p.to_dict()) == p
    assert p.is_configured() is True
    assert PotionRule(enabled=True, region=[0, 0, 0, 0]).is_configured() is False


def test_profile_roundtrip():
    prof = Profile(
        name="Diablo",
        toggle_hotkey="f8",
        skills=[Skill(key="1"), Skill(key="2", enabled=False)],
        potion=PotionRule(enabled=True, region=[1, 2, 3, 4]),
        resource=PotionRule(enabled=True, key="w", region=[5, 6, 7, 8], color=[40, 80, 200]),
        combo=Combo(enabled=True, steps=[ComboStep("3", 250)]),
        target_window="Diablo IV",
        jitter_pct=15,
    )
    back = Profile.from_dict(prof.to_dict())
    assert back.name == prof.name
    assert [s.key for s in back.skills] == ["1", "2"]
    assert back.potion.region == [1, 2, 3, 4]
    assert back.resource.key == "w"
    assert back.resource.region == [5, 6, 7, 8]
    assert back.combo.enabled and back.combo.steps[0].key == "3"
    assert back.target_window == "Diablo IV"
    assert back.jitter_pct == 15


def test_profile_backward_compatible():
    # Perfil antigo (sem os campos novos) deve carregar com defaults.
    old = {"name": "Velho", "toggle_hotkey": "f8", "skills": [{"key": "1"}], "potion": {}}
    p = Profile.from_dict(old)
    assert p.target_window == ""
    assert p.jitter_pct == 0
    assert p.combo.steps == []
    assert p.resource.enabled is False


def test_settings_roundtrip_and_defaults():
    assert Settings.from_dict({}) == Settings()
    s = Settings(start_minimized=True, overlay_enabled=False, panic_key="f10", log_to_file=True)
    assert Settings.from_dict(s.to_dict()) == s
