"""
demo_run.py — Visual agent pipeline runner for stakeholder demos.

Shows a live scrolling step log of the full orchestration:
  Trigger -> Orchestrator -> Agents (parallel) -> Briefing -> Delivery

Usage:
    py demo_run.py --uc UC1
    py demo_run.py --uc UC2
    py demo_run.py --uc UC4
"""
import sys
import time
import threading
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from config import SKILLS_DIR, USE_CASES, OUTPUT_DIR
from skill_registry import load_skill
from agents import jira_agent, analytics_agent, briefing_agent, confluence_agent
from delivery import deliver

console = Console()

# ── Step log ───────────────────────────────────────────────────────────────────

class StepLog:
    def __init__(self, uc_name: str, user: str, project: str):
        self.steps    = []
        self.start    = time.time()
        self.uc_name  = uc_name
        self.user     = user
        self.project  = project
        self._lock    = threading.Lock()

    def emit(self, component: str, message: str, status: str = "ok"):
        """status: ok | running | info | error | skip"""
        with self._lock:
            self.steps.append({
                "t":         round(time.time() - self.start, 1),
                "component": component,
                "message":   message,
                "status":    status,
            })

    def render(self) -> Panel:
        elapsed = round(time.time() - self.start, 1)

        table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
        table.add_column("t",    width=6,  no_wrap=True, style="dim")
        table.add_column("comp", width=16, no_wrap=True)
        table.add_column("msg",  ratio=1)

        with self._lock:
            rows = list(self.steps)

        for s in rows:
            t    = f"{s['t']:>5.1f}s"
            comp = s["component"]
            msg  = s["message"]
            st   = s["status"]

            if st == "ok":
                comp_r = f"[bold green]{comp:<15}[/bold green]"
                msg_r  = msg
            elif st == "running":
                comp_r = f"[bold yellow]{comp:<15}[/bold yellow]"
                msg_r  = f"[yellow]{msg}[/yellow]"
            elif st == "error":
                comp_r = f"[bold red]{comp:<15}[/bold red]"
                msg_r  = f"[red]{msg}[/red]"
            elif st == "skip":
                comp_r = f"[dim]{comp:<15}[/dim]"
                msg_r  = f"[dim]{msg}[/dim]"
            else:  # info / header
                comp_r = f"[bold cyan]{comp:<15}[/bold cyan]"
                msg_r  = f"[cyan]{msg}[/cyan]"

            table.add_row(t, comp_r, msg_r)

        title = Text.assemble(
            ("  OPS Native AI  ", "bold white on red"),
            "  ",
            (self.uc_name, "bold cyan"),
        )
        subtitle = (
            f"[dim]User: {self.user}  |  Project: {self.project}"
            f"  |  Elapsed: {elapsed}s[/dim]"
        )
        return Panel(
            table,
            title=title,
            subtitle=subtitle,
            border_style="bright_black",
            padding=(0, 1),
            box=box.ROUNDED,
        )


# ── Agent wrappers (emit sub-steps + run real agents) ─────────────────────────

def _run_jira(skill: dict, log: StepLog, results: dict):
    proj = skill.get("jira_project", "")
    log.emit("JIRA AGENT", f"Authenticating with Jira API", "running")
    time.sleep(0.15)
    log.emit("JIRA AGENT", f"Fetching open tickets — project: {proj}", "running")
    try:
        result = jira_agent.run(skill)
        total   = result.get("total_open", 0)
        breach  = len(result.get("sla_breaches", []))
        warning = len(result.get("sla_warnings", []))
        log.emit("JIRA AGENT", f"Fetched {total} open tickets", "ok")
        log.emit("JIRA AGENT", f"SLA evaluation: {breach} breach(es)  |  {warning} warning(s)", "ok")
        results["jira"] = result
    except Exception as exc:
        log.emit("JIRA AGENT", f"ERROR: {str(exc)[:70]}", "error")
        results["jira"] = {"error": str(exc), "open_tickets": [],
                           "sla_breaches": [], "sla_warnings": [], "total_open": 0}


def _run_analytics(skill: dict, log: StepLog, results: dict):
    pt  = skill.get("databricks_process_types") or []
    pid = skill.get("databricks_planning_ids") or []
    scope_desc = f"processType IN ({len(pt)} types)" if pt else (
                 f"planningId LIKE {pid[:2]}" if pid else "full table")
    log.emit("ANALYTICS",    "Connecting to Databricks SQL Warehouse", "running")
    time.sleep(0.2)
    log.emit("ANALYTICS",    f"Scope filter: {scope_desc}", "running")
    time.sleep(0.1)
    log.emit("ANALYTICS",    "Executing metrics query (last 4 weeks)...", "running")
    try:
        result = analytics_agent.run(skill)
        fta   = result.get("fta_current", 0)
        rag   = result.get("fta_rag", "")
        coq   = result.get("coq_current", 0)
        eff   = result.get("efficiency_vs_bl")
        src   = "live" if result.get("live") else "cached"
        bd    = len(result.get("process_breakdown", []))
        week  = result.get("week_label", "")
        log.emit("ANALYTICS",    f"FTA: {fta:.2f}% ({rag})  |  CoQ: {coq:.1f}%"
                                 + (f"  |  Eff vs Baseline: {eff:.0f}%" if eff else ""), "ok")
        log.emit("ANALYTICS",    f"Process breakdown: {bd} type(s)  |  Week: {week}  |  Source: {src}", "ok")
        results["analytics"] = result
    except Exception as exc:
        log.emit("ANALYTICS",    f"ERROR: {str(exc)[:70]}", "error")
        results["analytics"] = {"error": str(exc), "fta_current": 0,
                                 "fta_rag": "UNKNOWN", "live": False}


def _run_confluence(skill: dict, log: StepLog, results: dict):
    log.emit("CONFLUENCE",   "Authenticating with Confluence API", "running")
    time.sleep(0.1)
    log.emit("CONFLUENCE",   "Fetching progress page(s)...", "running")
    try:
        result = confluence_agent.run(skill)
        pages   = result.get("page_count", 0)
        overdue = len(result.get("overdue_pages", []))
        log.emit("CONFLUENCE",   f"Fetched {pages} page(s)"
                                 + (f"  |  {overdue} overdue item(s)" if overdue else ""), "ok")
        results["confluence"] = result
    except Exception as exc:
        log.emit("CONFLUENCE",   f"ERROR: {str(exc)[:70]}", "error")
        results["confluence"] = {"error": str(exc), "pages": [], "page_count": 0}


# ── UC1 ────────────────────────────────────────────────────────────────────────

def run_uc1_demo(skill_file: Path | None = None):
    _file = skill_file or next(SKILLS_DIR.glob("*_skill.md"), None)
    if not _file:
        console.print("[red]No skill file found.[/red]")
        sys.exit(1)

    skill    = load_skill(_file)
    user     = skill.get("user", "?")
    project  = skill.get("project_name") or skill.get("jira_project") or "Project"
    uc_name  = USE_CASES["UC1"]["name"]

    log = StepLog(uc_name, user, project)
    results: dict = {}

    with Live(log.render(), refresh_per_second=12, console=console) as live:

        # Trigger
        log.emit("TRIGGER",      "Calendar 07:30 daily  |  Running manually via demo_run.py", "info")
        live.update(log.render())
        time.sleep(0.2)

        # Orchestrator — init
        log.emit("ORCHESTRATOR", "UC1 Daily Operational Briefing — started", "info")
        live.update(log.render())
        time.sleep(0.1)

        # Skill profile
        log.emit("ORCHESTRATOR", "Reading personal skill profile...", "running")
        live.update(log.render())
        pt  = skill.get("databricks_process_types") or []
        pid = skill.get("databricks_planning_ids") or []
        role = skill.get("role", "")
        log.emit("ORCHESTRATOR", f"Skill loaded: {user} ({role})  |  Project: {project}", "ok")
        log.emit("ORCHESTRATOR", f"Analytics scope: {len(pt)} process type(s)  |  {len(pid)} planning ID(s)", "ok")
        live.update(log.render())
        time.sleep(0.15)

        # Dispatch parallel agents
        log.emit("ORCHESTRATOR", "Dispatching Jira, Analytics and Confluence Agents in parallel...", "info")
        live.update(log.render())
        time.sleep(0.1)

        threads = [
            threading.Thread(target=_run_jira,       args=(skill, log, results), daemon=True),
            threading.Thread(target=_run_analytics,  args=(skill, log, results), daemon=True),
            threading.Thread(target=_run_confluence, args=(skill, log, results), daemon=True),
        ]
        for t in threads: t.start()

        while any(t.is_alive() for t in threads):
            live.update(log.render())
            time.sleep(0.08)
        for t in threads: t.join()
        live.update(log.render())

        # Orchestrator collects
        jira_r       = results.get("jira",       {})
        analytics_r  = results.get("analytics",  {})
        confluence_r = results.get("confluence", {})
        log.emit("ORCHESTRATOR", "All agents returned — collecting results", "ok")
        live.update(log.render())
        time.sleep(0.1)

        # Briefing Agent
        log.emit("ORCHESTRATOR", "Dispatching Briefing Agent...", "info")
        live.update(log.render())
        log.emit("BRIEFING",     "Merging Jira + Analytics + Confluence data", "running")
        live.update(log.render())
        time.sleep(0.15)
        log.emit("BRIEFING",     "Composing daily briefing (markdown)...", "running")
        live.update(log.render())
        try:
            briefing_text = briefing_agent.run(jira_r, analytics_r, confluence_r, skill=skill)
            date_stamp    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            out_path      = OUTPUT_DIR / f"{date_stamp}_UC1_Daily_Briefing.md"
            out_path.write_text(briefing_text, encoding="utf-8")
            log.emit("BRIEFING",     f"Briefing composed and saved -> {out_path.name}", "ok")
        except Exception as exc:
            log.emit("BRIEFING",     f"ERROR: {str(exc)[:70]}", "error")
            briefing_text = ""
            out_path = None
        live.update(log.render())
        time.sleep(0.1)

        # Delivery
        log.emit("ORCHESTRATOR", "Dispatching Email Delivery...", "info")
        live.update(log.render())
        fta     = analytics_r.get("fta_current", 0)
        slas    = len(jira_r.get("sla_breaches", []))
        rag     = "AMBER" if jira_r.get("sla_breaches") else "GREEN"
        subject = f"[{rag}] UC1 Daily Briefing -- {project} | {slas} SLA breach(es) | FTA {fta:.1f}%"
        log.emit("DELIVERY",     f"Composing HTML email: {rag} | {slas} SLA breach(es) | FTA {fta:.1f}%", "running")
        live.update(log.render())
        time.sleep(0.15)
        log.emit("DELIVERY",     f"Sending via Outlook -> {skill.get('email','')}", "running")
        live.update(log.render())
        try:
            cc_list = skill.get("cc_recipients") or []
            dr = deliver(briefing_text, skill, subject=subject,
                         jira=jira_r, analytics=analytics_r,
                         confluence=confluence_r,
                         cc_recipients=cc_list if cc_list else None)
            ok_ch   = [ch for ch, ok in dr.items() if ok]
            fail_ch = [ch for ch, ok in dr.items() if not ok]
            if ok_ch:
                log.emit("DELIVERY", f"Email sent via: {', '.join(ok_ch)}", "ok")
            if fail_ch:
                log.emit("DELIVERY", f"Skipped: {', '.join(fail_ch)}", "skip")
        except Exception as exc:
            log.emit("DELIVERY", f"ERROR: {str(exc)[:70]}", "error")
        live.update(log.render())

        elapsed = round(time.time() - log.start, 1)
        log.emit("ORCHESTRATOR", f"UC1 complete in {elapsed}s", "info")
        live.update(log.render())
        time.sleep(0.8)

    console.print()
    console.rule("[bold green]UC1 — Daily Operational Briefing Complete[/bold green]")
    console.print()


# ── UC2 ────────────────────────────────────────────────────────────────────────

def run_uc2_demo(skill_file: Path | None = None):
    _file = skill_file or next(SKILLS_DIR.glob("*_skill.md"), None)
    if not _file:
        console.print("[red]No skill file found.[/red]")
        sys.exit(1)

    skill   = load_skill(_file)
    user    = skill.get("user", "?")
    project = skill.get("project_name") or skill.get("jira_project") or "Project"
    uc_name = USE_CASES["UC2"]["name"]

    log = StepLog(uc_name, user, project)
    results: dict = {}

    with Live(log.render(), refresh_per_second=12, console=console) as live:

        log.emit("TRIGGER",      "Jira event + 2-hour poll  |  Running manually via demo_run.py", "info")
        live.update(log.render())
        time.sleep(0.2)
        log.emit("ORCHESTRATOR", "UC2 Jira SLA & Status Follow-Up — started", "info")
        live.update(log.render())
        time.sleep(0.1)
        log.emit("ORCHESTRATOR", f"Skill loaded: {user}  |  Project: {project}", "ok")
        live.update(log.render())
        time.sleep(0.1)
        log.emit("ORCHESTRATOR", "Dispatching Jira Agent...", "info")
        live.update(log.render())

        t = threading.Thread(target=_run_jira, args=(skill, log, results), daemon=True)
        t.start()
        while t.is_alive():
            live.update(log.render())
            time.sleep(0.08)
        t.join()

        jira_r  = results.get("jira", {})
        breach  = jira_r.get("sla_breaches", [])
        warning = jira_r.get("sla_warnings", [])

        log.emit("ORCHESTRATOR", "Jira Agent returned — evaluating SLA thresholds...", "ok")
        live.update(log.render())
        time.sleep(0.2)

        if not breach and not warning:
            log.emit("ORCHESTRATOR", "All tickets on track — no alert required", "ok")
            log.emit("DELIVERY",     "No email sent (nothing to report)", "skip")
        else:
            rag     = "RED" if breach else "AMBER"
            log.emit("ORCHESTRATOR", f"({rag}) {len(breach)} breach(es)  |  {len(warning)} warning(s) — alert required", "ok")
            live.update(log.render())
            log.emit("ORCHESTRATOR", "Dispatching Email Delivery...", "info")
            live.update(log.render())
            log.emit("DELIVERY",     f"Composing SLA alert email ({rag})", "running")
            live.update(log.render())
            time.sleep(0.2)
            log.emit("DELIVERY",     f"Sending via Outlook -> {skill.get('email','')}", "running")
            live.update(log.render())
            try:
                subject = f"[{rag}] UC2 SLA Alert -- {project} | {len(breach)} breach(es)"
                cc_list = skill.get("cc_recipients") or []
                lines   = [f"# UC2 -- Jira SLA Alert ({project})", ""]
                for t2 in breach:
                    lines.append(f"- [{t2['key']}] {t2['summary']} | {t2['assignee']} | {t2['hours_stale']}h stale")
                for t2 in warning:
                    lines.append(f"- [{t2['key']}] {t2['summary']} | {t2['assignee']} | {t2['hours_stale']}h")
                content = "\n".join(lines)
                dr = deliver(content, skill, subject=subject,
                             jira=jira_r, analytics={},
                             cc_recipients=cc_list or None)
                ok_ch = [ch for ch, ok in dr.items() if ok]
                log.emit("DELIVERY", f"Alert sent via: {', '.join(ok_ch)}" if ok_ch else "No channel available", "ok" if ok_ch else "skip")
            except Exception as exc:
                log.emit("DELIVERY", f"ERROR: {str(exc)[:70]}", "error")

        elapsed = round(time.time() - log.start, 1)
        log.emit("ORCHESTRATOR", f"UC2 complete in {elapsed}s", "info")
        live.update(log.render())
        time.sleep(0.8)

    console.print()
    console.rule("[bold green]UC2 — Jira SLA Follow-Up Complete[/bold green]")
    console.print()


# ── UC4 ────────────────────────────────────────────────────────────────────────

def run_uc4_demo(skill_file: Path | None = None):
    _file = skill_file or next(SKILLS_DIR.glob("*_skill.md"), None)
    if not _file:
        console.print("[red]No skill file found.[/red]")
        sys.exit(1)

    skill   = load_skill(_file)
    user    = skill.get("user", "?")
    project = skill.get("project_name") or skill.get("jira_project") or "Project"
    uc_name = USE_CASES["UC4"]["name"]
    target  = skill["fta_thresholds"]["target"]
    alert   = skill["fta_thresholds"]["alert"]

    log = StepLog(uc_name, user, project)
    results: dict = {}

    with Live(log.render(), refresh_per_second=12, console=console) as live:

        log.emit("TRIGGER",      "Metric poll every 30 min  |  Running manually via demo_run.py", "info")
        live.update(log.render())
        time.sleep(0.2)
        log.emit("ORCHESTRATOR", "UC4 Quality & Metric Early Warning — started", "info")
        live.update(log.render())
        time.sleep(0.1)
        log.emit("ORCHESTRATOR", f"Skill loaded: {user}  |  FTA target: {target}%  alert: {alert}%", "ok")
        live.update(log.render())
        time.sleep(0.1)
        log.emit("ORCHESTRATOR", "Dispatching Analytics Agent...", "info")
        live.update(log.render())

        t = threading.Thread(target=_run_analytics, args=(skill, log, results), daemon=True)
        t.start()
        while t.is_alive():
            live.update(log.render())
            time.sleep(0.08)
        t.join()

        analytics_r = results.get("analytics", {})
        fta   = analytics_r.get("fta_current", 0)
        trend = analytics_r.get("fta_trend", "stable")

        log.emit("ORCHESTRATOR", "Analytics Agent returned — checking thresholds...", "ok")
        live.update(log.render())
        time.sleep(0.2)

        if fta >= target:
            log.emit("ORCHESTRATOR", f"FTA {fta:.2f}% >= {target}% target — GREEN — no alert required", "ok")
            log.emit("DELIVERY",     "No email sent (FTA healthy)", "skip")
        else:
            level = "AMBER" if fta >= alert else "RED P1"
            rag   = "AMBER" if fta >= alert else "RED"
            log.emit("ORCHESTRATOR", f"FTA {fta:.2f}% below target ({target}%) — ({level}) — alert required", "ok")
            live.update(log.render())
            log.emit("ORCHESTRATOR", "Dispatching Email Delivery...", "info")
            live.update(log.render())
            log.emit("DELIVERY",     f"Composing FTA alert email ({level}) | trend: {trend}", "running")
            live.update(log.render())
            time.sleep(0.2)
            log.emit("DELIVERY",     f"Sending via Outlook -> {skill.get('email','')}", "running")
            live.update(log.render())
            try:
                subject = f"[{rag}] UC4 FTA Alert -- {project} | {fta:.2f}% ({level})"
                cc_list = skill.get("cc_recipients") or []
                content = f"# UC4 -- FTA Quality Alert ({level})\n\nFTA: {fta:.2f}%  Target: {target}%  Alert: {alert}%  Trend: {trend}"
                dr = deliver(content, skill, subject=subject,
                             jira={}, analytics=analytics_r,
                             cc_recipients=cc_list or None)
                ok_ch = [ch for ch, ok in dr.items() if ok]
                log.emit("DELIVERY", f"Alert sent via: {', '.join(ok_ch)}" if ok_ch else "No channel available", "ok" if ok_ch else "skip")
            except Exception as exc:
                log.emit("DELIVERY", f"ERROR: {str(exc)[:70]}", "error")

        elapsed = round(time.time() - log.start, 1)
        log.emit("ORCHESTRATOR", f"UC4 complete in {elapsed}s", "info")
        live.update(log.render())
        time.sleep(0.8)

    console.print()
    console.rule("[bold green]UC4 — Quality Early Warning Complete[/bold green]")
    console.print()


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo runner — visual agent pipeline")
    parser.add_argument("--uc",    default="UC1", choices=["UC1", "UC2", "UC4"])
    parser.add_argument("--skill", default=None)
    args = parser.parse_args()

    skill_file = Path(args.skill) if args.skill else None

    console.print()
    console.rule(f"[bold cyan]OPS Native AI  |  {args.uc}[/bold cyan]")
    console.print()

    if args.uc == "UC1":
        run_uc1_demo(skill_file)
    elif args.uc == "UC2":
        run_uc2_demo(skill_file)
    elif args.uc == "UC4":
        run_uc4_demo(skill_file)
