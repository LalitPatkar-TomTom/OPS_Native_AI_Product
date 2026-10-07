"""
Word (.docx) report builder for UC3 Weekly Operational Report.
Mirrors the HTML email content — used as the email attachment.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any


def build(
    jira: dict[str, Any],
    analytics: dict[str, Any],
    confluence: dict[str, Any] | None = None,
    skill: dict[str, Any] | None = None,
) -> bytes:
    """
    Build a Word report from the same data as the weekly HTML email.
    Returns raw .docx bytes.
    Raises RuntimeError if python-docx is not installed.
    """
    try:
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        raise RuntimeError("python-docx not installed. Run: pip install python-docx")

    _s           = skill or {}
    project_name = _s.get("project_name") or "Project"
    jira_project = _s.get("jira_project") or ""
    user_name    = _s.get("user_first_name") or "you"
    pm           = set(_s.get("primary_metrics") or ["fta", "efficiency", "coq"])
    proj_label   = f"{project_name} ({jira_project})" if jira_project else project_name

    confluence   = confluence or {}
    week         = analytics.get("week_label", datetime.now().strftime("%Y-%m-%d"))
    now          = datetime.now(timezone.utc)
    date_str     = now.strftime("%A, %d %B %Y  ·  %H:%M UTC")
    m4w          = list(reversed(analytics.get("metrics_4w", [])))
    breakdown    = analytics.get("process_breakdown", [])
    source       = analytics.get("source", "Databricks")

    fta_current  = analytics.get("fta_current", 0.0)
    fta_prev     = analytics.get("fta_prev_week", fta_current)
    fta_rag      = analytics.get("fta_rag", "GREEN")
    coq_current  = analytics.get("coq_current", 0.0)
    coq_rag      = analytics.get("coq_rag", "GREEN")
    eff_vs_bl    = analytics.get("efficiency_vs_bl")
    eff_rag      = analytics.get("efficiency_rag", "GREEN")

    # RAG colours (RGB)
    _C = {
        "GREEN":  RGBColor(0x15, 0x80, 0x3D),
        "AMBER":  RGBColor(0xB0, 0x60, 0x00),
        "RED":    RGBColor(0xC0, 0x39, 0x2B),
        "NAVY":   RGBColor(0x1A, 0x1A, 0x2E),
        "GRAY":   RGBColor(0x64, 0x74, 0x8B),
        "WHITE":  RGBColor(0xFF, 0xFF, 0xFF),
    }

    overall = "GREEN"
    if jira.get("sla_breaches") or fta_rag == "RED":
        overall = "RED"
    elif jira.get("sla_warnings") or fta_rag == "AMBER" or coq_rag in ("AMBER", "RED"):
        overall = "AMBER"

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _set_cell_bg(cell, hex_color: str):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  hex_color)
        tcPr.append(shd)

    def _hdr_row(table, *cols, bg="1A1A2E"):
        row = table.rows[0]
        for i, text in enumerate(cols):
            cell = row.cells[i]
            _set_cell_bg(cell, bg)
            p    = cell.paragraphs[0]
            p.clear()
            run  = p.add_run(text)
            run.font.bold       = True
            run.font.size       = Pt(9)
            run.font.color.rgb  = _C["WHITE"]
            p.alignment         = WD_ALIGN_PARAGRAPH.CENTER

    def _data_row(table, row_idx, *vals, bg=None):
        row = table.rows[row_idx]
        for i, text in enumerate(vals):
            cell = row.cells[i]
            if bg:
                _set_cell_bg(cell, bg)
            p    = cell.paragraphs[0]
            p.clear()
            run  = p.add_run(str(text))
            run.font.size       = Pt(9)
            p.alignment         = WD_ALIGN_PARAGRAPH.CENTER

    def _section_heading(doc, title: str, n: int):
        p   = doc.add_paragraph()
        run = p.add_run(f"{n}.  {title}")
        run.font.bold      = True
        run.font.size      = Pt(11)
        run.font.color.rgb = _C["NAVY"]
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after  = Pt(4)

    def _delta_str(curr: float, prev: float, higher_is_good: bool = True) -> str:
        d    = curr - prev
        sign = "+" if d >= 0 else ""
        dir_ = "▲" if d > 0 else ("▼" if d < 0 else "→")
        return f"{dir_} {sign}{d:.2f}%"

    def _eff_str(val) -> str:
        if val is None:
            return "N/A"
        diff = val - 100
        sign = "+" if diff >= 0 else ""
        return f"{val:.1f}% ({sign}{diff:.1f}%)"

    # ── Document setup ─────────────────────────────────────────────────────────

    doc = Document()
    for sect in doc.sections:
        sect.top_margin    = Cm(1.8)
        sect.bottom_margin = Cm(1.8)
        sect.left_margin   = Cm(2.0)
        sect.right_margin  = Cm(2.0)

    # ── Cover header ───────────────────────────────────────────────────────────

    title_p = doc.add_paragraph()
    title_r = title_p.add_run("Weekly Operational Report")
    title_r.font.bold      = True
    title_r.font.size      = Pt(18)
    title_r.font.color.rgb = _C["NAVY"]
    title_p.alignment      = WD_ALIGN_PARAGRAPH.LEFT

    sub_p = doc.add_paragraph()
    sub_r = sub_p.add_run(f"{proj_label}  ·  Week of {week}  ·  {date_str}")
    sub_r.font.size      = Pt(10)
    sub_r.font.color.rgb = _C["GRAY"]
    sub_p.paragraph_format.space_after = Pt(2)

    rag_p = doc.add_paragraph()
    rag_r = rag_p.add_run(f"Overall Status:  ● {overall}")
    rag_r.font.bold      = True
    rag_r.font.size      = Pt(11)
    rag_r.font.color.rgb = _C.get(overall, _C["GRAY"])
    rag_p.paragraph_format.space_after = Pt(10)

    doc.add_paragraph().add_run().add_break()  # spacer

    # ── Section 1: KPI Summary ─────────────────────────────────────────────────

    sec_n = [0]

    def section(title):
        sec_n[0] += 1
        _section_heading(doc, title, sec_n[0])

    section("Key Performance Indicators")

    kpi_cols = []
    if "fta" in pm:
        kpi_cols.append(("FTA — First Time Accuracy", fta_current, fta_prev, True, fta_rag))
    if "coq" in pm or "copq" in pm:
        prev_coq = m4w[1]["coq"] if len(m4w) > 1 else coq_current
        kpi_cols.append(("CoQ — Cost of Quality", coq_current, prev_coq, False, coq_rag))
    if "efficiency" in pm and eff_vs_bl is not None:
        kpi_cols.append(("Efficiency vs Baseline", eff_vs_bl, None, True, eff_rag))

    if kpi_cols:
        tbl = doc.add_table(rows=2, cols=len(kpi_cols))
        tbl.style = "Table Grid"
        _hdr_row(tbl, *[k[0] for k in kpi_cols])
        row = tbl.rows[1]
        for i, (label, curr, prev, hig, rag) in enumerate(kpi_cols):
            cell = row.cells[i]
            bg   = {"GREEN": "D5F5E3", "AMBER": "FEF3E2", "RED": "FDE8E8"}.get(rag, "F1F5F9")
            _set_cell_bg(cell, bg)
            p    = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            val_r = p.add_run(f"{curr:.2f}%")
            val_r.font.bold      = True
            val_r.font.size      = Pt(14)
            val_r.font.color.rgb = _C.get(rag, _C["GRAY"])
            if prev is not None:
                p.add_run("\n")
                d_r = p.add_run(_delta_str(curr, prev, hig))
                d_r.font.size      = Pt(9)
                d_r.font.color.rgb = _C.get(rag, _C["GRAY"])
                p.add_run(f"\nvs {prev:.2f}% prior week").font.size = Pt(8)

    # ── Section 2: 4-Week Trend ────────────────────────────────────────────────

    if m4w:
        section(f"4-Week Trend — {project_name}")
        headers = ["Week"]
        if "fta" in pm:        headers.append("FTA")
        if "coq" in pm:        headers.append("CoQ")
        if "efficiency" in pm: headers.append("Efficiency vs BL")

        tbl = doc.add_table(rows=1 + len(m4w), cols=len(headers))
        tbl.style = "Table Grid"
        _hdr_row(tbl, *headers)
        for ri, w in enumerate(m4w):
            is_latest = ri == len(m4w) - 1
            vals = [f"{w['week']}{'  ← Latest' if is_latest else ''}"]
            if "fta" in pm:
                fta = w.get("fta", 0.0)
                arr = ""
                if ri > 0:
                    d = fta - m4w[ri - 1].get("fta", fta)
                    arr = " ▲" if d > 0.5 else (" ▼" if d < -0.5 else " →")
                vals.append(f"{fta:.2f}%{arr}")
            if "coq" in pm:
                coq = w.get("coq", 0.0)
                arr = ""
                if ri > 0:
                    d = coq - m4w[ri - 1].get("coq", coq)
                    arr = " ▲" if d > 0.2 else (" ▼" if d < -0.2 else " →")
                vals.append(f"{coq:.2f}%{arr}")
            if "efficiency" in pm:
                ev = w.get("efficiency_vs_bl")
                vals.append(_eff_str(ev))
            bg = "EBF5FB" if is_latest else None
            _data_row(tbl, ri + 1, *vals, bg=bg)

        src_p = doc.add_paragraph(f"Source: {source}")
        src_p.runs[0].font.size      = Pt(8)
        src_p.runs[0].font.color.rgb = _C["GRAY"]

    # ── Section 3: Process Type Highlights ─────────────────────────────────────

    if breakdown:
        section("Process Type Highlights")
        needs = [p for p in breakdown if p.get("fta_rag") in ("AMBER", "RED")]
        top   = [p for p in breakdown if p.get("fta_rag") == "GREEN"
                 and (p.get("eff_vs_bl") or 0) >= 100][:5]

        for group_label, group, hdr_bg in [
            ("⚠ Needs Attention", needs, "C0392B"),
            ("✓ Top Performers",  top,   "15803D"),
        ]:
            if not group:
                continue
            lbl_p = doc.add_paragraph(group_label)
            lbl_p.runs[0].font.bold      = True
            lbl_p.runs[0].font.size      = Pt(9)
            lbl_p.runs[0].font.color.rgb = _C["RED"] if "Attention" in group_label else _C["GREEN"]
            lbl_p.paragraph_format.space_before = Pt(6)
            lbl_p.paragraph_format.space_after  = Pt(2)

            tbl = doc.add_table(rows=1 + len(group), cols=4)
            tbl.style = "Table Grid"
            _hdr_row(tbl, "Process Type", "FTA", "Eff vs BL", "Hours", bg=hdr_bg)
            for ri, p in enumerate(group):
                _data_row(
                    tbl, ri + 1,
                    p.get("process_type", ""),
                    f'{p.get("fta_pct", 0):.2f}%',
                    _eff_str(p.get("eff_vs_bl")),
                    f'{p.get("total_hrs", 0):.0f}h',
                )
        wk_p = doc.add_paragraph(f"Week: {week}")
        wk_p.runs[0].font.size      = Pt(8)
        wk_p.runs[0].font.color.rgb = _C["GRAY"]

    # ── Section 4: Jira Sprint Health ─────────────────────────────────────────

    breaches = jira.get("sla_breaches", []) or []
    warnings = jira.get("sla_warnings", []) or []
    open_cnt = jira.get("open_tickets", 0) or 0
    on_track = jira.get("on_track", 0) or 0

    section(f"{jira_project} Sprint Health" if jira_project else "Sprint Health")
    sprint_tbl = doc.add_table(rows=2, cols=4)
    sprint_tbl.style = "Table Grid"
    _hdr_row(sprint_tbl, "Total Open", "SLA Breach", "SLA Warning", "On Track")
    for i, val in enumerate([str(open_cnt), str(len(breaches)), str(len(warnings)), str(on_track)]):
        cell = sprint_tbl.rows[1].cells[i]
        bg   = "FDE8E8" if (i == 1 and len(breaches)) else (
               "FEF3E2" if (i == 2 and len(warnings)) else "F0FDF4")
        _set_cell_bg(cell, bg)
        p    = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r    = p.add_run(val)
        r.font.bold = True
        r.font.size = Pt(12)

    if breaches:
        doc.add_paragraph()
        br_p = doc.add_paragraph("⚠ SLA Breaches")
        br_p.runs[0].font.bold      = True
        br_p.runs[0].font.color.rgb = _C["RED"]
        br_p.runs[0].font.size      = Pt(9)
        for t in breaches:
            bp = doc.add_paragraph(f"  • {t.get('key', '')}  —  stale {t.get('hours_stale', '')}h",
                                   style="List Bullet")
            bp.runs[0].font.size = Pt(9)

    jira_src = jira.get("source", f"Jira {jira_project}")
    js_p = doc.add_paragraph(f"Source: {jira_src}")
    js_p.runs[0].font.size      = Pt(8)
    js_p.runs[0].font.color.rgb = _C["GRAY"]

    # ── Section 5: Confluence — Weekly Progress ────────────────────────────────

    conf_pages = confluence.get("pages", []) or []
    if conf_pages:
        section("Confluence — Weekly Progress")
        for page in conf_pages[:5]:
            title   = page.get("title", "Untitled")
            updated = page.get("last_updated", "")
            author  = page.get("last_author", "")
            excerpt = page.get("excerpt", "")
            line = f"{title}"
            if updated:
                line += f"  ·  Updated {updated}"
            if author:
                line += f" by {author}"
            cp = doc.add_paragraph(f"  • {line}")
            cp.runs[0].font.size = Pt(9)
            if excerpt:
                ep = doc.add_paragraph(f"    {excerpt[:150]}{'…' if len(excerpt) > 150 else ''}")
                ep.runs[0].font.size      = Pt(8)
                ep.runs[0].font.color.rgb = _C["GRAY"]

    # ── Section 6: Focus for Next Week ────────────────────────────────────────

    focus_items = []
    if "fta" in pm and fta_current < 95:
        rag = "RED" if fta_current < 92 else "AMBER"
        focus_items.append((rag, f"FTA at {fta_current:.2f}% — monitor process types below target."))
    if ("coq" in pm or "copq" in pm) and coq_current >= 7:
        rag = "RED" if coq_current >= 10 else "AMBER"
        focus_items.append((rag, f"CoQ at {coq_current:.2f}% — identify top rework drivers. Target <7%."))
    if "efficiency" in pm and eff_rag == "RED":
        focus_items.append(("RED", "Efficiency below 90% of baseline — review capacity and task distribution."))
    for p in breakdown:
        if p.get("fta_rag") in ("AMBER", "RED"):
            focus_items.append((p["fta_rag"],
                f'{p["process_type"]} — FTA {p.get("fta_pct", 0):.2f}%: review rejection root cause.'))
    for t in breaches:
        focus_items.append(("RED", f'Resolve SLA breach on {t.get("key", "")} — stale {t.get("hours_stale", "")}h.'))
    for t in warnings:
        focus_items.append(("AMBER", f'Follow up on {t.get("key", "")} approaching 48h SLA.'))

    if not focus_items:
        focus_items.append(("GREEN", "All metrics healthy — maintain current execution standards."))

    section(f"Focus for Next Week — {user_name}'s Review")
    for rag, text in focus_items:
        fp = doc.add_paragraph(f"  {'🔴' if rag == 'RED' else ('⚠' if rag == 'AMBER' else '✓')}  {text}")
        fp.runs[0].font.size      = Pt(9)
        fp.runs[0].font.color.rgb = _C.get(rag, _C["GRAY"])
        fp.paragraph_format.space_after = Pt(3)

    # ── Footer ─────────────────────────────────────────────────────────────────

    doc.add_paragraph()
    foot_p = doc.add_paragraph(
        f"UC3 Weekly Report  ·  {jira_project}  ·  Databricks  ·  Confluence"
        f"\nDraft for {user_name}'s review before any distribution."
        f"\nGenerated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    foot_p.runs[0].font.size      = Pt(8)
    foot_p.runs[0].font.color.rgb = _C["GRAY"]

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
