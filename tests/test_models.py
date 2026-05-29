"""Testes de round-trip dos modelos."""

from praxis.models import PotionRule, Profile, Settings, Skill


def test_skill_roundtrip():
    s = Skill(name="Fireball", key="2", interval_ms=1234, enabled=False)
    assert Skill.from_dict(s.to_dict()) == s


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
    )
    back = Profile.from_dict(prof.to_dict())
    assert back.name == prof.name
    assert back.toggle_hotkey == prof.toggle_hotkey
    assert [s.key for s in back.skills] == ["1", "2"]
    assert back.potion.region == [1, 2, 3, 4]


def test_settings_roundtrip_and_defaults():
    assert Settings.from_dict({}) == Settings()
    s = Settings(start_minimized=True, overlay_enabled=False, panic_key="f10", log_to_file=True)
    assert Settings.from_dict(s.to_dict()) == s
