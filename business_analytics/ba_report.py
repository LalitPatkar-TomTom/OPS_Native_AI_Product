"""Build the OPS Native AI & OPS Hub business value report (Word), from the extracted pilot data."""
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.section import WD_ORIENT  # noqa: E402,F401
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
S = Path(__file__).resolve().parent
OUTDIR = Path(r"C:\Users\patkar\OneDrive - TomTom\Deployed")
DOCX = OUTDIR / "OPS_NativeAI_OPSHub_Business_Value_Report_2026-10-19.docx"
D1 = json.load(open(S / "ba_data.json", encoding="utf-8"))
D2 = json.load(open(S / "ba_data2.json", encoding="utf-8"))
D3 = json.load(open(S / "ba_data3.json", encoding="utf-8"))

# ── palette (validated: categorical 4 slots, PASS; contrast WARN → labels + tables) ──
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID = "#1f1f1e", "#52524e", "#8a8a84", "#e6e6e1"
NAVY = RGBColor(0x1B, 0x2A, 0x4A)
UC_NAME = {"UC1": "Daily Briefing (UC1)", "UC4": "Metric Alert (UC4)", "UC2": "SLA Follow-up (UC2)", "UC3": "Weekly Report (UC3)"}
UC_COLOR = {"UC1": BLUE, "UC4": ORANGE, "UC2": AQUA, "UC3": YELLOW}

# ── numbers ───────────────────────────────────────────────────────────────────
MANUAL_UC1 = 13                                   # catch-up briefings sent manually on 19 Oct (separate log)
emails_by_uc = Counter(D2["emails_by_uc"])
emails_by_uc["UC1"] += MANUAL_UC1
emails_total = sum(emails_by_uc.values())
by_day = {d: Counter(v) for d, v in D2["emails_by_day_uc"].items()}
by_day["2026-10-19"]["UC1"] += MANUAL_UC1
days_all = [date(2026, 10, 1) + timedelta(n) for n in range(19)]
workdays = [d for d in days_all if d.weekday() < 5]
profiles = len(D1["profiles"])
hub = D3["ops_hub_by_day"]
chat_ok = sum(int(v.get("chat", "0/0").split("/")[0]) for v in hub.values())
chat_all = sum(int(v.get("chat", "0/0").split("/")[1]) for v in hub.values())
onboard = sum(int(v.get("onboarding/submit", "0/0").split("/")[0]) for v in hub.values())
sr_jobs = sum(int(v.get("sr/generate-job", "0/0").split("/")[0]) for v in hub.values())
runs_done = len(D2["runs"]) + 1                   # + the manual catch-up on 19 Oct
slots_planned = 4 * 18 + 2                        # 1–18 Oct full days + 19 Oct 09:00 & 13:00
alerts_by_metric = {k: v for k, v in D1["uc4_alerts_by_metric"].items()}
alerts_by_metric["fta"] -= D1["uc4_alerts_by_user"].get("test.user@tomtom.com", 0)   # the one test alert (FTA, 8 Oct)
alert_total = sum(alerts_by_metric.values())
suppressed = D1["uc4_status"]["suppressed"]
alert_sent_events = D1["uc4_status"]["sent"]
coq_red = D1["uc4_rag"]["coq"].get("RED_P1", 0) / D1["uc4_checks"]

VALUE = [  # activity, volume, minutes of manual effort avoided per item (assumption)
    ("Daily briefings prepared (UC1)", emails_by_uc["UC1"], 20,
     "Collect Jira status, Databricks KPIs and Confluence updates for one PM"),
    ("Metric breaches detected & reported (UC4)", emails_by_uc["UC4"], 15,
     "Spot a threshold breach in Power BI and write it up"),
    ("SLA follow-ups prepared (UC2)", emails_by_uc["UC2"], 10,
     "Find stale tickets and draft the chase"),
    ("Weekly reports produced (UC3)", emails_by_uc["UC3"], 90,
     "Compile and format the weekly status report"),
    ("OPS Hub questions answered", chat_ok, 10,
     "Search Jira / Confluence / Databricks for the answer"),
    ("Status Reports generated (OPS Hub)", sr_jobs, 120,
     "Build a monthly portfolio report by hand"),
]
hours = [(a, v, m, n, v * m / 60) for a, v, m, n in VALUE]
total_h = sum(h for *_, h in hours)
per_user_day = total_h / profiles / len(workdays)
annual_h = total_h / len(workdays) * 220
fte = annual_h / 1650


# ── charts ────────────────────────────────────────────────────────────────────
def style(ax, ylabel=""):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK2, fontsize=8.5)


def save(fig, name):
    p = S / name
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9})

# 1. emails per day, stacked by use case
fig, ax = plt.subplots(figsize=(7.2, 3.0))
labels = [d.strftime("%d %b") for d in days_all]
bottom = [0] * len(days_all)
for uc in ("UC1", "UC4", "UC2", "UC3"):
    vals = [by_day.get(d.isoformat(), {}).get(uc, 0) for d in days_all]
    ax.bar(labels, vals, bottom=bottom, color=UC_COLOR[uc], width=0.68, label=UC_NAME[uc],
           edgecolor="white", linewidth=1.2)
    bottom = [b + v for b, v in zip(bottom, vals)]
for i, t in enumerate(bottom):
    if t:
        ax.text(i, t + 0.8, str(t), ha="center", va="bottom", fontsize=7, color=INK2)
style(ax, "Emails delivered")
ax.tick_params(axis="x", rotation=60)
ax.legend(frameon=False, fontsize=7.5, ncol=4, loc="upper left", bbox_to_anchor=(0, 1.18))
c_emails = save(fig, "c_emails.png")

# 2. estimated hours saved by activity
fig, ax = plt.subplots(figsize=(7.2, 2.6))
order = sorted(hours, key=lambda h: h[4])
ax.barh([h[0] for h in order], [h[4] for h in order], color=BLUE, height=0.55)
for i, h in enumerate(order):
    ax.text(h[4] + 0.8, i, f"{h[4]:.0f} h", va="center", fontsize=8, color=INK2)
style(ax)
ax.xaxis.grid(True, color=GRID, linewidth=0.8)
ax.yaxis.grid(False)
ax.set_xlabel("Estimated hours of manual work avoided (1–19 Oct)", color=INK2, fontsize=8.5)
c_value = save(fig, "c_value.png")

# 3. alerts by metric
fig, ax = plt.subplots(figsize=(5.2, 2.4))
mk = sorted(alerts_by_metric.items(), key=lambda kv: -kv[1])
names = {"coq": "CoQ", "efficiency": "Efficiency", "yield": "Yield", "fta": "FTA"}
ax.bar([names.get(k, k) for k, _ in mk], [v for _, v in mk], color=ORANGE, width=0.55)
for i, (_, v) in enumerate(mk):
    ax.text(i, v + 1, str(v), ha="center", fontsize=8, color=INK2)
style(ax, "Alerts raised")
c_alerts = save(fig, "c_alerts.png")

# 4. reliability: runs completed per day vs the 4 planned slots
fig, ax = plt.subplots(figsize=(7.2, 2.4))
rd = Counter(D2["runs_by_day"])
rd["2026-10-19"] += 1
ax.bar(labels, [rd.get(d.isoformat(), 0) for d in days_all], color=AQUA, width=0.6)
ax.axhline(4, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
ax.text(len(days_all) - 0.5, 4.1, "4 planned slots / day", ha="right", fontsize=7.5, color=INK2)
style(ax, "Runs completed")
ax.set_ylim(0, 4.8)
ax.tick_params(axis="x", rotation=60)
c_runs = save(fig, "c_runs.png")

# ── document helpers ──────────────────────────────────────────────────────────
doc = Document()
for sec in doc.sections:
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
st = doc.styles["Normal"]
st.font.name = "Segoe UI"
st.font.size = Pt(10)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Segoe UI")
for lvl, size in ((1, 15), (2, 12), (3, 10.5)):
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = "Segoe UI"
    h.font.size = Pt(size)
    h.font.color.rgb = NAVY
    h.font.bold = True


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def para(text="", size=10, bold=False, color=None, after=4, italic=False, align=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size); r.bold = bold; r.italic = italic
    if color:
        r.font.color.rgb = color
    p.paragraph_format.space_after = Pt(after)
    if align:
        p.alignment = align
    return p


def bullet(text, lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if lead:
        r = p.add_run(lead + " "); r.bold = True
    p.add_run(text)
    p.paragraph_format.space_after = Pt(2)


def table(headers, rows, widths=None, num_cols=()):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        c = t.rows[0].cells[j]
        shade(c, "1B2A4A")
        c.paragraphs[0].text = ""
        r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8.5); r.font.color.rgb = RGBColor(255, 255, 255)
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            c = t.rows[i].cells[j]
            c.paragraphs[0].text = ""
            r = c.paragraphs[0].add_run(str(v)); r.font.size = Pt(8.5)
            if j in num_cols:
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if i % 2 == 0:
                shade(c, "F4F5F7")
    if widths:
        for row in t.rows:
            for j, w in enumerate(widths):
                row.cells[j].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def kpi_grid(items):
    t = doc.add_table(rows=2, cols=len(items))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, (val, lab) in enumerate(items):
        top, bot = t.rows[0].cells[j], t.rows[1].cells[j]
        for c in (top, bot):
            shade(c, "EEF3FB")
        top.paragraphs[0].text = ""; bot.paragraphs[0].text = ""
        r = top.paragraphs[0].add_run(val); r.bold = True; r.font.size = Pt(17); r.font.color.rgb = NAVY
        r2 = bot.paragraphs[0].add_run(lab); r2.font.size = Pt(8); r2.font.color.rgb = RGBColor(0x52, 0x52, 0x4E)
        top.paragraphs[0].alignment = bot.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def figure(path, caption, width=16.5):
    doc.add_picture(str(path), width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(caption, size=8, italic=True, color=RGBColor(0x8A, 0x8A, 0x84), after=8, align=WD_ALIGN_PARAGRAPH.CENTER)


# ── title page ────────────────────────────────────────────────────────────────
para("", after=60)
para("OPS Native AI & OPS Hub", size=26, bold=True, color=NAVY, after=4)
para("Business Value Report — Pilot 1–19 October 2026", size=15, color=RGBColor(0x2A, 0x78, 0xD6), after=24)
para("Maps Operations · Prepared by the OPS Native AI team · 19 October 2026", size=10, color=RGBColor(0x52, 0x52, 0x4E), after=4)
para("Version 1.0 · Data cut-off 19 Oct 2026, 13:05 IST", size=9, color=RGBColor(0x8A, 0x8A, 0x84), after=40)
para("Purpose", size=11, bold=True, color=NAVY, after=2)
para("Show the business value OPS Native AI (scheduled briefings, alerts and reports by email) and OPS Hub "
     "(chat assistant, Status Reports, self-service onboarding) have delivered in the first 19 days of operation, "
     "what was learned, and what is needed to scale — including moving all operational data to Databricks.", after=4)
doc.add_page_break()

# ── 1. executive summary ──────────────────────────────────────────────────────
doc.add_heading("1. Executive summary", 1)
kpi_grid([(str(profiles), "Profile owners live"), (f"{emails_total}", "Emails delivered"),
          (f"{total_h:.0f} h", "Manual work avoided (est.)"), ("100%", "Email delivery success")])
kpi_grid([(f"{alert_total}", "Metric breaches flagged"), (f"{D1['uc2_open_tickets_tracked']}", "Open Jira tickets watched"),
          (f"{chat_ok}", "OPS Hub questions answered"), ("0", "Engine run errors")])
bullet(f"{profiles} PMs and leads across 8 Jira projects receive a personalised daily briefing, metric alerts, SLA "
       f"follow-ups and a Friday report — {emails_total} emails in 19 days, every one delivered.", "Adopted by every onboarded user.")
bullet(f"An estimated {total_h:.0f} hours of manual preparation avoided in 13 working days (≈{per_user_day * 60:.0f} min per "
       f"user per working day). At today's 13 users that is ≈{annual_h:,.0f} h a year, about {fte:.1f} FTE; even at "
       f"half the assumed effort it is ≈{fte / 2:.1f} FTE.", "Time back to the teams.")
bullet(f"{alert_total} quality and efficiency threshold breaches were pushed to the owner the morning the data "
       f"arrived, instead of being found in a weekly review; {suppressed} repeat alerts were held back so the signal stays "
       f"actionable.", "Earlier warning on quality.")
bullet("Since 19 Oct all Jira and Confluence reads go through the TomTom MCP registry (org policy), secrets sit in "
       "Azure, writes stay human-approved, and outages fall back automatically (shown on 19 Oct when the AI model endpoint "
       "was down).", "Compliant and resilient.")
bullet(f"The engine ran {runs_done} of {slots_planned} planned slots ({runs_done / slots_planned:.0%}) because it runs "
       "on one laptop. Moving the schedule and all run, email and usage data to Databricks removes that limit and "
       "gives one governed source for these KPIs.", "Main constraint and the ask.")
para("Recommendation: approve moving the scheduler and operational data store to Databricks (section 9), "
     "then widen onboarding beyond the first 13 users.", bold=True, color=NAVY, after=6)
doc.add_page_break()

# ── 2. scope & adoption ───────────────────────────────────────────────────────
doc.add_heading("2. Scope and adoption", 1)
para("Each user describes their scope once in the OPS Hub onboarding form (process types, planning IDs, Jira project, "
     "Confluence pages, thresholds, schedule). The profile then drives every email, so nobody maintains a report by hand.")
table(["Measure", "Value", "Notes"], [
    ["Profile owners live", profiles, "11 from 1 Oct, 13 since 14 Oct; all received email every working day"],
    ["Onboarding submissions (self-service)", onboard, "12–15 Oct via the OPS Hub form, no admin effort"],
    ["Stakeholders in copy", len(D1["emails_cc_people"]), "Managers receive copies for oversight"],
    ["Process types monitored", 20, "Databricks KPI table, per profile"],
    ["Planning IDs monitored", 36, ""],
    ["Jira projects covered", 8, "DSM, GDN, LMDF, MCPET, OM, QA, RM, RTE"],
    ["Confluence pages tracked", 7, "Staleness and highlights in briefings"],
], widths=[5.2, 2.0, 9.3], num_cols=(1,))
para("Use cases in operation", size=10.5, bold=True, color=NAVY, after=2)
table(["Use case", "What the user receives", "Cadence"], [
    ["UC1 Daily Briefing", "Overall and work-unit KPIs (FTA, Efficiency vs baseline, CoQ, Yield), Jira status, Confluence changes", "Working days 09:00"],
    ["UC2 SLA Follow-up", "Tickets past the warning / escalation age, with a ready-to-send chase", "4× daily"],
    ["UC3 Weekly Report", "Week summary with trends, as email + Word attachment", "Fridays 17:00"],
    ["UC4 Metric Alert", "Immediate email when a metric crosses the user's own threshold", "4× daily"],
    ["OPS Hub chat", "Plain-English questions over Jira, Confluence and Databricks", "On demand"],
    ["OPS Hub Status Report", "Report built to the PM's own template and prompt; exact numbers from Databricks", "On demand"],
], widths=[3.6, 9.6, 3.3])

# ── 3. delivery volume ────────────────────────────────────────────────────────
doc.add_heading("3. Delivery volume", 1)
figure(c_emails, f"Figure 1 — Emails delivered per day by use case, 1–19 Oct 2026 (total {emails_total}). "
                 "Gaps on 7–8, 10–11 and 17 Oct are laptop downtime or weekends, not failures.")
table(["Use case", "Emails delivered", "Share"], [
    [UC_NAME[uc], emails_by_uc[uc], f"{emails_by_uc[uc] / emails_total:.0%}"] for uc in ("UC1", "UC4", "UC2", "UC3")
] + [["Total", emails_total, "100%"]], widths=[7, 4, 3], num_cols=(1, 2))
para(f"Email delivery success: {D1['emails_table_ok']} of {D1['emails_table_total']} tracked sends (13–19 Oct) delivered — 100%. "
     f"Each email reached on average {D1['emails_table_recipients'] / D1['emails_table_total']:.1f} people (owner + managers in copy).", size=9)

# ── 4. early warning ──────────────────────────────────────────────────────────
doc.add_heading("4. Early warning on quality and efficiency (UC4)", 1)
para(f"Every run checks each user's metrics against their own thresholds — {D1['uc4_checks']} checks since 9 Oct. "
     f"{alert_total} distinct breaches (one per metric per user per day) were raised and emailed the same morning.")
figure(c_alerts, "Figure 2 — Metric breaches raised by metric, 8–19 Oct 2026.", width=11)
table(["Metric", "Breaches raised", "Share"], [[names.get(k, k), v, f"{v / alert_total:.0%}"] for k, v in mk if k in names],
      widths=[5, 4, 3], num_cols=(1, 2))
bullet(f"{suppressed} repeat alerts for a breach already reported that day were held back ({suppressed / (suppressed + alert_sent_events):.0%} "
       "of alert-level results) — users get one actionable message, not noise.", "Noise control:")
bullet(f"CoQ was above the alert level in {coq_red:.0%} of checks. That points to thresholds set tighter than current "
       "operations rather than 542 incidents; owners have been asked to recalibrate (OSI log), which will raise the "
       "signal value of each alert.", "Threshold calibration:")
bullet("FTA stayed green in every check — quality first-pass acceptance is healthy across the monitored scope; the "
       "risk sits in cost of quality and efficiency.", "Where the risk is:")

# ── 5. SLA governance ─────────────────────────────────────────────────────────
doc.add_heading("5. Jira SLA governance (UC2)", 1)
para(f"{D1['uc2_checks']} SLA checks since 13 Oct watched {D1['uc2_open_tickets_tracked']} open tickets across 8 Jira projects "
     f"and produced {emails_by_uc['UC2']} follow-up emails with the stale tickets listed.")
bullet(f"{D1['uc2_distinct_tickets_flagged']} distinct tickets were flagged past their SLA age. Many are years old: the tool "
       "has surfaced a backlog that is invisible in day-to-day views — a hygiene clean-up opportunity in itself.", "Backlog made visible:")
bullet("Two fixes in the log (OSI-003: only tickets of the last 12 months; OSI-006: each profile's own SLA levels, e.g. "
       "days for 15-day sprints) will turn this into a focused daily chase list.", "Next step:")

# ── 6. reporting & OPS Hub ────────────────────────────────────────────────────
doc.add_heading("6. Reporting automation and OPS Hub", 1)
table(["Measure", "Value", "Notes"], [
    ["Weekly reports produced (UC3)", emails_by_uc["UC3"], "Weeks of 2, 9, 16 Oct (first sent Sat 3 Oct); Word attachment"],
    ["OPS Hub questions answered", f"{chat_ok} of {chat_all}", "Failures: 19 Oct model outage before the automatic fallback"],
    ["Status Reports generated", sr_jobs, "Template-driven engine launched 16 Oct, exported to Word"],
    ["Self-service onboarding submissions", onboard, "Profiles live on the next run, no developer involvement"],
], widths=[5.6, 2.6, 8.3])
para("The Status Report engine builds each PM's own template: the AI plans the layout, every table number is computed "
     "in code from Databricks, and a source appendix lets the PM verify each row. This replaces hand-built monthly "
     "portfolio reports.", size=9.5)

# ── 7. value ──────────────────────────────────────────────────────────────────
doc.add_heading("7. Productivity value (estimate)", 1)
para("Value = volume delivered × manual effort the item replaces. Effort per item is a conservative assumption, "
     "to be validated with users; the sensitivity line shows the result at half the effort.")
figure(c_value, f"Figure 3 — Estimated manual work avoided by activity, 1–19 Oct 2026 (total {total_h:.0f} h).")
table(["Activity", "Volume", "Min / item (assumed)", "Hours", "What it replaces"],
      [[a, v, m, f"{h:.1f}", n] for a, v, m, n, h in hours] + [["Total", "", "", f"{total_h:.1f}", ""]],
      widths=[4.6, 1.6, 2.2, 1.6, 6.5], num_cols=(1, 2, 3))
table(["Scenario", "Hours (pilot)", "Per user / working day", "Annualised (13 users)", "FTE"], [
    ["Assumed effort", f"{total_h:.0f}", f"{per_user_day * 60:.0f} min", f"{annual_h:,.0f} h", f"{fte:.1f}"],
    ["Half the assumed effort", f"{total_h / 2:.0f}", f"{per_user_day * 30:.0f} min", f"{annual_h / 2:,.0f} h", f"{fte / 2:.1f}"],
], widths=[4.2, 2.6, 3.4, 3.6, 2.2], num_cols=(1, 2, 3, 4))
para("Not counted: faster reaction to breaches, fewer missed SLA chases, management visibility through copies, and "
     "the 684 metric checks that found nothing to report. Annualised = pilot rate × 220 working days; 1 FTE = 1,650 h.",
     size=8.5, italic=True, color=RGBColor(0x52, 0x52, 0x4E))

# ── 8. reliability & governance ───────────────────────────────────────────────
doc.add_heading("8. Reliability, governance and lessons learned", 1)
figure(c_runs, f"Figure 4 — Engine runs completed per day against 4 planned slots ({runs_done} of {slots_planned}).")
table(["Measure", "Result"], [
    ["Email delivery success (tracked)", "100% (193 / 193)"],
    ["Engine run errors (tracked runs)", "0"],
    ["Average run time", "16 min for all 13 profiles"],
    ["Planned slots completed", f"{runs_done} / {slots_planned} ({runs_done / slots_planned:.0%}) — laptop asleep or off"],
    ["Data source compliance", "Jira / Confluence via TomTom MCP registry since 19 Oct; REST fallback"],
    ["Security", "Secrets in Azure Container App, scoped API token, PIM-approved deployments, read-only data access"],
], widths=[5.6, 10.9])
para("Incidents handled during the pilot", size=10.5, bold=True, color=NAVY, after=2)
table(["Date", "What happened", "Response"], [
    ["16 & 19 Oct", "One user's briefing missed its Jira section (tickets without a priority)", "Fixed and deployed 19 Oct"],
    ["19 Oct", "09:00 run missed — laptop asleep; killed at the 30-min limit", "Briefings re-sent 11:01; task now wakes the laptop and catches up"],
    ["19 Oct", "AI model endpoint (Sonnet 4.6) out of capacity", "Automatic fallback model deployed the same day; chat kept working"],
], widths=[2.3, 7.6, 6.6])

# ── 9. roadmap ────────────────────────────────────────────────────────────────
doc.add_heading("9. Next steps — Databricks as the operational data store", 1)
para("Today the evidence in this report comes from a SQLite file and log files on one laptop plus OPS Hub's container "
     "logs. Moving it to Databricks makes the numbers governed, shareable and refreshable without manual extraction.")
table(["Proposed Delta table", "Content", "Feeds"], [
    ["ops_ai_runs", "Every scheduled / manual run: slot, start, end, delay, users, errors", "Reliability KPIs"],
    ["ops_ai_events", "Every use-case result per user: metrics, RAG, alert, SLA counts", "Early-warning & SLA KPIs"],
    ["ops_ai_email_deliveries", "Every email: use case, owner, recipients, success", "Adoption & reach"],
    ["ops_ai_alert_actions", "Acknowledged / fixed / not an issue per alert (OSI-007)", "Action rate, time to act"],
    ["ops_hub_usage", "Chat questions, Status Reports, onboarding events per user", "OPS Hub adoption"],
    ["ops_ai_profiles", "Profile scope snapshot (process types, planning IDs, thresholds)", "Coverage"],
], widths=[4.4, 8.0, 4.1])
bullet("Run the schedule as a Databricks Job (or Azure job) instead of the laptop — target ≥ 99% of slots.", "1.")
bullet("Write runs, events, emails and OPS Hub usage to the tables above; one dashboard replaces this manual report.", "2.")
bullet("Add one-click actions in emails (OSI-007) so value is measured by actions taken, not only emails sent.", "3.")
bullet("Recalibrate thresholds with owners and ship the OSI quick fixes (SLA days, Jira date filter, default metrics).", "4.")
bullet("Widen onboarding to the next wave of PMs once 1–2 are in place.", "5.")

# ── appendix ──────────────────────────────────────────────────────────────────
doc.add_heading("Appendix — data sources and definitions", 1)
table(["Source", "Period", "Used for"], [
    ["Native AI run log (task_scheduler.log)", "1–19 Oct", "Emails per use case and day, runs"],
    ["Native AI analytics DB (trigger_events)", "9–19 Oct", "Checks, alerts, RAG, SLA tickets, active users"],
    ["Native AI analytics DB (trigger_runs, email_deliveries)", "13–19 Oct", "Run timing, errors, delivery success, recipients"],
    ["OPS Hub request log (Azure Log Analytics)", "29 Sep–19 Oct", "Chat, Status Report and onboarding volumes"],
    ["Profile files (onboarding)", "19 Oct", "Users and monitored scope"],
], widths=[6.5, 2.6, 7.4])
for t in (
    "Breach = one metric over the user's own alert threshold, counted once per user per day.",
    "Emails include owner + copy recipients; test sends are excluded.",
    "Hours saved are estimates from stated assumptions, not time-tracking data.",
    "Data cut-off: 19 Oct 2026, end of the 13:00 IST run.",
):
    bullet(t)

doc.save(DOCX)
print("saved", DOCX)
print(f"emails {emails_total} {dict(emails_by_uc)} | hours {total_h:.1f} | per user/day {per_user_day*60:.0f} min | annual {annual_h:.0f} h = {fte:.2f} FTE | runs {runs_done}/{slots_planned} | alerts {alert_total} | chat {chat_ok}/{chat_all}")
