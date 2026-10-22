"""Profile parsing (MultiAgent_Briefing/skill_registry.py): every user's SKILL.md drives what the
engine does for them, so the parsers are pinned here."""
import pytest

import skill_registry as sr


@pytest.mark.parametrize("raw,hour,minute,dow", [
    ("Calendar · 07:30 daily", 7, 30, "*"),
    ("Calendar · Friday 16:00", 16, 0, "fri"),
    ("Calendar · 16:00 Friday", 16, 0, "fri")])
def test_calendar_triggers(raw, hour, minute, dow):
    t = sr._parse_trigger(raw)
    assert (t["type"], t["hour"], t["minute"], t["day_of_week"]) == ("cron", hour, minute, dow)


def test_poll_triggers():
    assert sr._parse_trigger("Jira event + 2-hour poll")["type"] == "poll"
    assert sr._parse_trigger("Metric · continuous Databricks poll")["type"] == "unknown"


def test_quiet_hours_and_timezone():
    assert sr._extract_quiet_hours("| Quiet Hours (no alerts) | 19:00 – 08:00 |") == (19, 8)
    assert sr._extract_quiet_hours("nothing") is None
    assert sr._extract_timezone("based in Amsterdam") == "Europe/Amsterdam"
    assert sr._extract_timezone("x") == "Asia/Kolkata"


@pytest.mark.parametrize("name,key", [("CoPQ — Cost of Poor Quality", "copq"), ("CoQ", "coq"),
                                      ("User Efficiency", "efficiency"), ("Sampling", None)])
def test_metric_names(name, key):
    assert sr._normalize_metric_key(name) == key


def test_thresholds_and_direction():
    assert sr._parse_pct("below 92%") == 92.0
    assert sr._parse_pct("<9,5%") == 9.5
    assert sr._parse_pct("n/a") is None
    assert sr._parse_direction("above 10%", "") == "rise"
    assert sr._parse_direction("92%", "↓ Alert on drop") == "drop"


def test_sla_defaults_and_cc():
    assert sorted(sr._extract_sla_thresholds("").values()) == [48, 72]
    assert sorted(sr._extract_sla_thresholds("SLA Warning: 24 hours\nSLA Escalation: 36 hours").values()) == [24, 36]
    assert sr._extract_cc_recipients("**Briefing CC:** a@b.com; c@d.com, nobody") == ["a@b.com", "c@d.com"]


def test_load_skill_takes_owner_from_filename(tmp_path):
    p = tmp_path / "jane.doe@tomtom.com_skill.md"
    p.write_text("# Jane Doe\n", encoding="utf-8")
    s = sr.load_skill(p)
    assert s["user"] == "jane.doe@tomtom.com" and s["user_first_name"] == "Jane"
    with pytest.raises(FileNotFoundError):
        sr.load_skill(tmp_path / "missing@tomtom.com_skill.md")
