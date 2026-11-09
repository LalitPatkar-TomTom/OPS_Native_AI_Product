"""Delivery forecast ("Ops Weather", ADR-014): work days left per work package and OM ticket from the real 4-week
pace; OM pace when the WP has none; trickle / stalled without a number; ADP, training and pilot left out; the
weekly email section; a failure never stops the weekly report."""
import time
from datetime import date

import pytest

import delivery_forecast as df
import email_html_weekly as W
from db_client import DatabricksSQLClient

MON = date(2026, 11, 9)


def _row(**kw) -> dict:
    """A query row as Databricks returns it (numbers as strings)."""
    base = {"wp": "WP_A", "src": "SD", "pt": "Orbis-DIR-OneWay", "om": "OM-301934", "pending": "1000",
            "tasks": None, "hrs": None, "eds": None, "om_tasks": None, "om_hrs": None, "om_eds": None,
            "om_pending": None, "om_wps": None}
    return {**base, **{k: (str(v) if v is not None else None) for k, v in kw.items()}}


class FakeClient:
    """Records the SQL and returns fixed rows, or raises."""
    def __init__(self, rows=None, exc=None):
        self.rows, self.exc, self.sql = rows or [], exc, ""

    def execute_sql(self, sql, max_rows=100):
        """Check the query is read-only, as the real client does, then answer."""
        DatabricksSQLClient._assert_select_only(sql)
        self.sql = sql
        if self.exc:
            raise self.exc
        return {"rows": self.rows}


# ── Functional ──────────────────────────────────────────────────────────────────

def test_pace_uses_the_last_four_full_weeks():
    assert df.pace_weeks(MON) == ("2026-10-12", "2026-11-02")
    assert df.pace_weeks(date(2026, 11, 13)) == ("2026-10-12", "2026-11-02")    # Friday: same weeks


def test_own_pace_gives_work_days():
    # 2,000 tasks in 20 work days = 100 a day; 1,000 pending = 10 days
    it = df.classify(_row(tasks=2000, hrs=200, eds=12))
    assert (it["days"], it["band"], it["basis"], it["editors"], it["tph"]) == (10.0, "sunny", "own", 12, 10.0)
    assert df.classify(_row(tasks=200, hrs=40, eds=3))["band"] == "rainy"         # 100 days


@pytest.mark.parametrize("days,band", [(20, "sunny"), (20.1, "cloudy"), (60, "cloudy"), (60.1, "rainy")])
def test_band_edges(days, band):
    assert df.band_of(days) == band


def test_wp_without_history_finishes_with_its_om():
    it = df.classify(_row(tasks=None, om_tasks=400, om_hrs=50, om_eds=7, om_pending=2000))
    # whole OM: 2,000 pending / (400 / 20 a day) = 100 days, with the OM's editors and pace
    assert (it["days"], it["basis"], it["editors"], it["tph"], it["band"]) == (100.0, "om", 7, 8.0, "rainy")


def test_trickle_and_stalled_get_no_number():
    trickle = df.classify(_row(tasks=1, hrs=1.7, eds=1))
    stalled = df.classify(_row())
    assert (trickle["days"], trickle["band"]) == (None, "trickle")
    assert (stalled["days"], stalled["band"]) == (None, "stalled")
    # an OM with only a trickle of work does not rescue the WP
    assert df.classify(_row(om_tasks=10, om_pending=500))["band"] == "trickle"


def test_om_rollup_uses_the_whole_om_pace():
    items = [df.classify(_row(wp="A", tasks=2000, hrs=100, om_tasks=2400, om_hrs=120, om_pending=6000)),
             df.classify(_row(wp="B", pending=5000, om_tasks=2400, om_hrs=120, om_pending=6000)),
             df.classify(_row(wp="C", om="OM-9", pending=50))]
    oms = df.om_rollup(items)
    assert [(g["om"], g["wps"], g["pending"], g["days"], g["band"]) for g in oms] == [
        ("OM-301934", 2, 6000, 50.0, "cloudy"), ("OM-9", 1, 50, None, "stalled")]


def test_summary_totals_add_up():
    out = df.summarise([_row(tasks=2000, hrs=10), _row(wp="B"), _row(wp="C", tasks=5)], df.pace_weeks(MON))
    assert out["pending_total"] == 3000 and out["pace_to"] == "2026-11-08"
    assert {b: t["wps"] for b, t in out["totals"].items()} == {
        "sunny": 1, "cloudy": 0, "rainy": 0, "trickle": 1, "stalled": 1}


# ── Technical ───────────────────────────────────────────────────────────────────

def test_query_is_read_only_and_leaves_out_adp_training_pilot():
    c = FakeClient([_row(tasks=2000, hrs=10)])
    out = df.run({"scope_mode": "keyword:lane"}, today=MON, client=c, table="kpi")
    assert out["items"][0]["band"] == "sunny"
    sql = c.sql
    assert "= 'adp'" in sql and "'%train%'" in sql and "'%pilot%'" in sql and "NOT (" in sql
    assert "BETWEEN '2026-10-12' AND '2026-11-02'" in sql
    assert "LOWER(p.pt) LIKE '%lane%'" in sql and "LOWER(p.wp) LIKE '%lane%'" in sql


def test_profile_names_are_escaped_and_full_scope_has_no_filter():
    sql = df.forecast_sql("kpi", {"databricks_process_types": ["it's"]}, "AND (x)", MON)
    assert "'%it''s%'" in sql and "IN (SELECT wpl FROM mine)" in sql
    assert "WHERE 1 = 1 \n" in df.forecast_sql("kpi", {"scope_mode": "all"}, "", MON)
    assert "WHERE 1 = 1 \n" in df.forecast_sql("kpi", None, "", MON)


def test_failure_switch_and_no_scope_never_raise(monkeypatch):
    assert "error" in df.run(None, today=MON, client=FakeClient(exc=RuntimeError("warehouse down")), table="t")
    assert "error" in df.run({"no_databricks_scope": True}, today=MON, client=FakeClient(), table="t")
    monkeypatch.setenv("DELIVERY_FORECAST", "0")
    assert df.run(None, today=MON, client=FakeClient(), table="t") == {"off": True}


def test_email_section_escapes_names_and_is_left_out_without_data():
    fc = df.summarise([_row(wp="<b>x</b>", tasks=2000, hrs=10), _row(wp="Waiting_WP", pending=900)],
                      df.pace_weeks(MON))
    html = W._build_forecast(fc)
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "<b>x</b>" not in html
    assert "Waiting_WP" in html and "No editor in 4 weeks" in html and "OM-301934" in html
    assert "ADP, training and pilot process types are left out" in html
    for empty in (None, {}, {"error": "x"}, {"off": True}, df.summarise([], df.pace_weeks(MON))):
        assert W._build_forecast(empty) == ""


def test_weekly_report_has_the_section_only_with_a_forecast():
    fc = df.summarise([_row(tasks=2000, hrs=10)], df.pace_weeks(MON))
    ana = {"no_scope": True}
    with_fc = W.build({}, ana, {}, skill={"project_name": "P"}, forecast=fc)
    without = W.build({}, ana, {}, skill={"project_name": "P"})
    assert "Delivery Forecast" in with_fc and "Delivery Forecast" not in without


# ── Performance ─────────────────────────────────────────────────────────────────

def test_full_table_size_is_fast():
    # the full table on 9 Nov: 3,031 WPs in scope; 5,000 rows must summarise and render well under a second
    rows = [_row(wp=f"WP_{i}", om=f"OM-{i % 700}", tasks=(i * 7) % 3000, hrs=50, om_tasks=900, om_hrs=80,
                 om_pending=20000) for i in range(5000)]
    t = time.perf_counter()
    fc = df.summarise(rows, df.pace_weeks(MON))
    html = W._build_forecast(fc)
    assert time.perf_counter() - t < 1.0 and len(html) < 60_000


# ── PM must understand the number (user, 9 Nov 2026) ────────────────────────────

def test_long_forecasts_read_more_than_a_year():
    assert (df.days_text(None), df.days_text(10.4), df.days_text(250), df.days_text(5134)) == (
        "–", "10", "250", "> 1 year")


def test_each_row_says_where_its_pace_comes_from():
    own = df.classify(_row(tasks=2000, hrs=200))
    om = df.classify(_row(om_tasks=96, om_hrs=36.1, om_eds=9, om_pending=24641, om_wps=134))
    assert df.basis_text(own) == "own pace: 2,000 tasks in 4 wks"
    assert df.basis_text(om) == ("no own work in 4 wks; done with OM-301934: 96 tasks in 4 wks, "
                                 "24,641 pending in 134 WPs")


def test_howto_box_works_through_a_real_om_row():
    # the 9 Nov OM-337351 row: 96 tasks in 4 weeks = 4.8 a day; 24,641 / 4.8 = 5,134 work days
    fc = df.summarise([_row(wp="WP_OWN", tasks=2000, hrs=100),
                       _row(wp="RMLanes_BaseMap_AME_MEX_TOP2", om="OM-337351", pending=3858, om_tasks=96,
                            om_hrs=36.1, om_eds=9, om_pending=24641, om_wps=134)], df.pace_weeks(MON))
    html = W._build_forecast(fc)
    assert "How to read this" in html and "not a plan" in html
    assert "24,641 &divide; 4.8 = 5,134 work days (shown as &ldquo;&gt; 1 year&rdquo;)" in html
    assert "> 1 year" in html
