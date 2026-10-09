"""
MultiAgent Briefing Orchestrator — UC1 Daily Operational Briefing

Trigger: Calendar 07:30 daily  (delivered at 08:30 per lalit's preference)

Architecture
────────────
  [Orchestrator]
       │
       ├── [Jira Agent]       → MCPET open tickets, SLA status
       ├── [Analytics Agent]  → FTA, Efficiency, CoQ from Databricks
       └── [Briefing Agent]   → formats & saves markdown output

All agents run sequentially; Jira and Analytics are independent and can be
parallelised in a future async version.
"""
import sys
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from this package when run directly
sys.path.insert(0, str(Path(__file__).parent))

from config import OUTPUT_DIR, SKILLS_DIR, USE_CASES
from agents import jira_agent, analytics_agent, briefing_agent, confluence_agent
from skill_registry import load_skill, load_all_skills
from delivery import deliver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("orchestrator")


# ── Skill reader ───────────────────────────────────────────────────────────────

def load_uc_definition(uc_id: str = "UC1", skill_file: Path | None = None) -> dict:
    """Read the personal SKILL profile and extract the requested use case."""
    _file = skill_file or next(SKILLS_DIR.glob("*_skill.md"), None)
    try:
        text = _file.read_text(encoding="utf-8") if _file else ""
    except FileNotFoundError:
        return {"name": USE_CASES[uc_id]["name"], "trigger": USE_CASES[uc_id]["trigger"],
                "definition": "(skill file not found)"}

    uc_info = USE_CASES.get(uc_id, {})
    marker = f"**{uc_id} —"
    start = text.find(marker)
    end   = text.find("\n**UC", start + 1) if start != -1 else -1
    definition = text[start:end].strip() if start != -1 and end != -1 else "(definition not found)"

    return {
        "id":         uc_id,
        "name":       uc_info.get("name", ""),
        "trigger":    uc_info.get("trigger", ""),
        "definition": definition,
    }


# ── Orchestrator ───────────────────────────────────────────────────────────────

def run_uc1(skill_file: Path | None = None) -> Path:
    """
    Execute the UC1 Daily Operational Briefing pipeline end-to-end.

    skill_file: path to a specific *_skill.md; if None, picks the first file
                in SKILLS_DIR (single-user / CLI convenience).
    Returns the path to the saved briefing file.
    """
    _file = skill_file or next(SKILLS_DIR.glob("*_skill.md"), None)
    if _file is None:
        raise FileNotFoundError(f"No skill files found in {SKILLS_DIR}")

    start_ts = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("UC1 — Daily Operational Briefing triggered")

    # Step 1 — Read personal skill definition for UC1
    log.info("Step 1/4  Reading skill profile …")
    skill = load_skill(_file)
    uc    = load_uc_definition("UC1", skill_file=_file)
    log.info(f"          User: {skill['user']}  |  Project: {skill.get('project_name', '')} ({skill.get('jira_project', '')})")
    log.info(f"          UC: {uc['name']}  |  Trigger: {uc['trigger']}")
    scope_mode = skill.get("scope_mode", "defined")
    pts        = skill.get("databricks_process_types") or []
    pids       = skill.get("databricks_planning_ids") or []
    if scope_mode in ("all", "keyword:gen", "keyword:lane", "keyword:gen,lane"):
        db_scope_label = scope_mode
    elif pts:
        db_scope_label = f"processType IN ({', '.join(pts[:3])}{'...' if len(pts) > 3 else ''})"
    elif pids:
        db_scope_label = f"planningid LIKE {pids[0]}"
    else:
        db_scope_label = "full table"
    log.info(f"          Analytics scope: {db_scope_label}")

    # Step 2 — Dispatch Jira, Analytics & Confluence agents in parallel
    log.info("Step 2/4  Dispatching Jira, Analytics and Confluence Agents in parallel …")
    jira_result       = {}
    analytics_result  = {}
    confluence_result = {}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(jira_agent.run,                          skill): "jira",
            pool.submit(analytics_agent.run, skill, "daily"):           "analytics",
            pool.submit(confluence_agent.run,                    skill): "confluence",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                if name == "jira":
                    jira_result = result
                    log.info(f"          Jira Agent       done — {result.get('total_open', 0)} open tickets, "
                             f"{len(result.get('sla_breaches', []))} breach(es)")
                elif name == "analytics":
                    analytics_result = result
                    log.info(f"          Analytics Agent  done — FTA {result.get('fta_current', 0):.2f}%  "
                             f"({'live' if result.get('live') else 'cached'})")
                else:
                    confluence_result = result
                    pages = result.get("page_count", 0)
                    overdue = result.get("overdue_pages", [])
                    log.info(f"          Confluence Agent done — {pages} page(s) fetched"
                             + (f", {len(overdue)} overdue" if overdue else ""))
            except Exception as exc:
                log.error(f"          {name} agent raised: {exc}")
                if name == "jira":
                    _jira_src = f"Jira {skill.get('jira_project', '')}" if skill.get("jira_project") else "Jira"
                    jira_result = {"error": str(exc), "open_tickets": [], "sla_breaches": [],
                                   "sla_warnings": [], "total_open": 0, "source": _jira_src}
                elif name == "analytics":
                    analytics_result = {"error": str(exc), "fta_current": 0, "fta_rag": "UNKNOWN",
                                        "source": "unavailable", "live": False}
                else:
                    confluence_result = {"error": str(exc), "pages": [], "page_count": 0,
                                         "source": "Confluence"}

    # Step 3 — Format briefing
    log.info("Step 3/5  Briefing Agent formatting output …")
    briefing_text = briefing_agent.run(jira_result, analytics_result, confluence_result, skill=skill)

    # Step 4 — Save to output/
    log.info("Step 4/5  Saving briefing …")
    date_stamp  = start_ts.strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"{date_stamp}_UC1_Daily_Briefing.md"
    output_path.write_text(briefing_text, encoding="utf-8")
    log.info(f"          Saved -> {output_path}")

    # Also save a machine-readable snapshot for downstream agents
    snapshot = {
        "uc":           uc,
        "jira":         jira_result,
        "analytics":    analytics_result,
        "generated_at": start_ts.isoformat(),
        "output_file":  str(output_path),
    }
    snapshot_path = OUTPUT_DIR / f"{date_stamp}_UC1_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    # Step 5 — Deliver (email + Teams if configured)
    log.info("Step 5/5  Delivering briefing …")
    rag   = "AMBER" if jira_result.get("sla_breaches") else "GREEN"
    slas  = len(jira_result.get("sla_breaches", []))
    fta   = analytics_result.get("fta_current", 0)
    proj_label = skill.get("project_name") or skill.get("jira_project") or "Project"
    subject = f"[{rag}] UC1 Daily Briefing — {proj_label} | {slas} SLA breach(es) | FTA {fta:.1f}%"
    cc_list = skill.get("cc_recipients") or []
    delivery_results = deliver(
        briefing_text, skill, subject=subject,
        jira=jira_result, analytics=analytics_result,
        confluence=confluence_result,
        cc_recipients=cc_list if cc_list else None,
    )
    for channel, ok in delivery_results.items():
        status = "OK" if ok else "FAILED/SKIPPED"
        log.info(f"          {channel:<15} {status}")

    elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()
    log.info(f"UC1 complete in {elapsed:.1f}s")
    log.info("=" * 60)

    return {
        "path":      output_path,
        "analytics": analytics_result,
        "jira":      jira_result,
    }


# ── UC2 — Jira SLA Alert ───────────────────────────────────────────────────────

def run_uc2(skill_file: Path | None = None) -> Path | None:
    """
    Poll Jira for SLA breaches/warnings and deliver an alert email if any found.
    Returns path to saved alert file, or None if everything is on track.
    """
    _file = skill_file or next(SKILLS_DIR.glob("*_skill.md"), None)
    if _file is None:
        raise FileNotFoundError(f"No skill files found in {SKILLS_DIR}")

    start_ts = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("UC2 — Jira SLA Poll triggered")

    skill        = load_skill(_file)
    proj_name    = skill.get("project_name") or "Project"
    jira_project = skill.get("jira_project") or ""
    proj_label   = f"{proj_name} ({jira_project})" if jira_project else proj_name
    user_first   = skill.get("user_first_name") or "you"
    cc_list      = skill.get("cc_recipients") or []

    log.info(f"          User: {skill['user']}  |  Project: {proj_label}")

    from agents import jira_agent
    jira     = jira_agent.run(skill)
    breaches = jira.get("sla_breaches", [])
    warnings = jira.get("sla_warnings", [])

    if not breaches and not warnings:
        log.info("          No SLA issues detected — all tickets on track.")
        log.info("=" * 60)
        return None

    lines = [
        f"# UC2 — Jira SLA Alert ({proj_label})",
        f"**Generated:** {start_ts.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
    ]
    if breaches:
        lines.append(f"## SLA BREACH — {len(breaches)} ticket(s) over 72h\n")
        for t in breaches:
            lines.append(
                f"- [{t['key']}]({t['url']}) — {t['summary']}  "
                f"| Owner: **{t['assignee']}** | Silent: **{t['hours_stale']}h**"
            )
        lines.append(f"\n> Draft follow-up ready for {user_first}'s approval.")
    if warnings:
        lines.append(f"\n## SLA WARNING — {len(warnings)} ticket(s) approaching 48h\n")
        for t in warnings:
            lines.append(
                f"- [{t['key']}]({t['url']}) — {t['summary']}  "
                f"| Owner: **{t['assignee']}** | Silent: **{t['hours_stale']}h**"
            )

    content    = "\n".join(lines)
    date_stamp = start_ts.strftime("%Y-%m-%d_%H%M")
    out_path   = OUTPUT_DIR / f"{date_stamp}_UC2_SLA_Alert.md"
    out_path.write_text(content, encoding="utf-8")

    slas    = len(breaches)
    rag     = "RED" if breaches else "AMBER"
    subject = f"[{rag}] UC2 SLA Alert — {proj_label} | {slas} breach(es), {len(warnings)} warning(s)"
    deliver(content, skill, subject=subject, jira=jira, analytics={},
            cc_recipients=cc_list or None)

    elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()
    log.info(f"          Saved -> {out_path}")
    log.info(f"UC2 complete in {elapsed:.1f}s")
    log.info("=" * 60)
    return out_path


# ── UC4 — FTA Quality Alert ────────────────────────────────────────────────────

def run_uc4(skill_file: Path | None = None) -> Path | None:
    """
    Poll Databricks for current FTA and deliver an alert if below threshold.
    Returns path to saved alert file, or None if FTA is healthy.
    """
    _file = skill_file or next(SKILLS_DIR.glob("*_skill.md"), None)
    if _file is None:
        raise FileNotFoundError(f"No skill files found in {SKILLS_DIR}")

    start_ts = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("UC4 — FTA Quality Alert Poll triggered")

    skill        = load_skill(_file)
    proj_name    = skill.get("project_name") or "Project"
    jira_project = skill.get("jira_project") or ""
    proj_label   = f"{proj_name} ({jira_project})" if jira_project else proj_name
    cc_list      = skill.get("cc_recipients") or []
    target       = skill["fta_thresholds"]["target"]
    alert        = skill["fta_thresholds"]["alert"]

    log.info(f"          User: {skill['user']}  |  Project: {proj_label}")
    log.info(f"          FTA thresholds — target: {target}%  alert: {alert}%")

    from agents import analytics_agent
    analytics = analytics_agent.run(skill)

    fta    = analytics.get("fta_current", 0.0)
    trend  = analytics.get("fta_trend", "stable")
    prev   = analytics.get("fta_prev_week", fta)
    source = analytics.get("source", "Databricks")

    if fta >= target:
        log.info(f"          FTA {fta:.2f}% — healthy (>= {target}%) — no alert needed.")
        log.info("=" * 60)
        return None

    level = "AMBER" if fta >= alert else "RED P1"
    rag   = "AMBER" if fta >= alert else "RED"
    log.info(f"          FTA {fta:.2f}% — {level} — alert firing")

    lines = [
        f"# UC4 — FTA Quality Alert ({level})",
        f"**Project:** {proj_label}  |  **Generated:** {start_ts.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        f"## FTA: {fta:.2f}% — {'Watch item' if rag == 'AMBER' else 'IMMEDIATE ACTION REQUIRED'}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Current FTA | {fta:.2f}% |",
        f"| Target | {target}% |",
        f"| Alert threshold | {alert}% |",
        f"| Trend | {trend} (prev week: {prev:.2f}%) |",
        f"| Source | {source} |",
        "",
        f"> Cross-reference {jira_project} Jira board for quality-labelled tickets." if jira_project
        else "> Cross-reference Jira board for quality-labelled tickets.",
    ]

    content    = "\n".join(lines)
    date_stamp = start_ts.strftime("%Y-%m-%d_%H%M")
    out_path   = OUTPUT_DIR / f"{date_stamp}_UC4_FTA_Alert.md"
    out_path.write_text(content, encoding="utf-8")

    subject = f"[{rag}] UC4 FTA Alert — {proj_label} | {fta:.2f}% ({level})"
    deliver(content, skill, subject=subject, jira={}, analytics=analytics,
            cc_recipients=cc_list or None)

    elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()
    log.info(f"          Saved -> {out_path}")
    log.info(f"UC4 complete in {elapsed:.1f}s")
    log.info("=" * 60)
    return out_path


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MultiAgent Briefing Orchestrator")
    parser.add_argument("--uc", default="UC1", choices=["UC1", "UC2", "UC4"],
                        help="Use case to run  UC1=Daily Briefing  UC2=SLA Alert  UC4=FTA Alert")
    parser.add_argument("--skill", default=None,
                        help="Path to a specific *_skill.md (default: first file in Personal Skills/)")
    args = parser.parse_args()

    skill_file = Path(args.skill) if args.skill else None

    if args.uc == "UC1":
        result = run_uc1(skill_file)
        out = result["path"]
        print(f"\nBriefing saved to: {out}")
        print("\n" + "=" * 60)
        content = out.read_text(encoding="utf-8")
        sys.stdout.buffer.write(content.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")

    elif args.uc == "UC2":
        out = run_uc2(skill_file)
        if out:
            print(f"\nSLA alert saved to: {out}")
            content = out.read_text(encoding="utf-8")
            sys.stdout.buffer.write(content.encode("utf-8", errors="replace"))
            sys.stdout.buffer.write(b"\n")
        else:
            print("\nAll Jira tickets on track — no SLA alert needed.")

    elif args.uc == "UC4":
        out = run_uc4(skill_file)
        if out:
            print(f"\nFTA alert saved to: {out}")
            content = out.read_text(encoding="utf-8")
            sys.stdout.buffer.write(content.encode("utf-8", errors="replace"))
            sys.stdout.buffer.write(b"\n")
        else:
            print("\nFTA is healthy — no alert needed.")

    else:
        print(f"UC '{args.uc}' not yet implemented (UC3/UC5 are placeholders).")
        sys.exit(1)
