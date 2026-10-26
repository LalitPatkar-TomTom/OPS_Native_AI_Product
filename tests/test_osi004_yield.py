"""OSI-004 (26 Oct): Yield across every work unit like FTA / Eff vs BL / CoQ, Yield per planning ID, the "Orbit SD only" note."""
import email_html as E
import trigger_engine as T
from agents import analytics_agent as A

JIRA = {"sla_breaches": [], "sla_warnings": []}


def test_yield_counts_every_work_unit_like_the_other_metrics():
    # same rule as FTA / Eff vs BL / CoQ: no work-unit list, so DPU RMSI and any new work unit count (26 Oct)
    for sql in (A._YIELD_SQL, A._YIELD_BY_PT_WU_SQL, A._YIELD_BY_PID_SQL):
        assert "work_unit) in" not in sql.lower()


def test_no_sd_yield_shows_the_note_not_na():
    an = {"yield_current": None, "yield_note": A.YIELD_SD_ONLY_NOTE, "fta_current": 99.0}
    kpis = E._build_kpi_row(an, JIRA, {"fta", "yield"})
    assert "Orbit SD work only" in kpis
    summary = E._build_exec_summary(JIRA, an, {"fta", "yield"}, {})
    assert "Yield is currently available for Orbit SD work only" in summary


def test_yield_with_data_keeps_its_value_and_badge():
    an = {"yield_current": 84.79, "yield_rag": "RED", "yield_note": "", "fta_current": 99.0}
    kpis = E._build_kpi_row(an, JIRA, {"yield"})
    assert "84.79%" in kpis and "Orbit SD work only" not in kpis


def test_planning_id_yield_rows_can_alert():
    rule = [{"metric": "yield", "level": "planning", "scope": ["ADAS-RMLanes"], "alert": 85.0, "direction": "drop"}]
    an = {"planning_breakdown": [{"planning_id": "ADAS-RMLanes", "yield_pct": 80.0, "total_hrs": 900, "fta_rag": "GREEN"},
                                 {"planning_id": "Other", "yield_pct": 50.0, "total_hrs": 10, "fta_rag": "GREEN"}]}
    hits = T.scoped_breaches(an, rule, "yield")
    assert [(h[1]["planning_id"], h[2]) for h in hits] == [("ADAS-RMLanes", 80.0)]
    an["planning_breakdown"][0]["yield_pct"] = None          # no SD yield for that planning ID: nothing to alert
    assert T.scoped_breaches(an, rule, "yield") == []
