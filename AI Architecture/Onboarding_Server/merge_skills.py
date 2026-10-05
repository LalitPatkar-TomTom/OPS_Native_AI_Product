"""
LLM-powered skill profile merger.

Takes a user's personal skill.md (from the onboarding form) and the generic
domain SKILL.md, calls the Databricks Foundation Model API once, and writes
a single personalised combined skill.md to skills/combined/.

Fallback: if Databricks is not configured, appends domain content after a
separator — so the file is always produced.
"""
import logging
import re
from pathlib import Path
from typing import Any

import httpx

# Databricks Azure resource ID (fixed — same for all tenants)
_DATABRICKS_RESOURCE = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"

logger = logging.getLogger(__name__)

# Domain label as written in personal skill.md → subdirectory name under domains_dir
_DOMAIN_FOLDER: dict[str, str] = {
    "Operational Lead":  "operational-lead",
    "Quality Lead":      "quality-lead",
    "Business Analyst":  "business-analyst",
    "Process Engineer":  "Process Engineering",
    "Process Engineering": "Process Engineering",
    "Project Manager":   "project-manager",
}

_MERGE_PROMPT = """\
You are creating the master AI agent skill profile for {name} — a TomTom Maps Operations \
team member. This file is the single source of truth the AI Co-Pilot reads at the start of \
every interaction to understand exactly who this person is, how they work, and what they need. \
It must be deeply personalised, comprehensive, and rich enough to make the agent feel like it \
has worked alongside this person for months.

You have two source documents:

=== DOCUMENT 1 — PERSONAL ONBOARDING PROFILE (exact user data — preserve all numbers, names, dates) ===
{user_md}
=== END DOCUMENT 1 ===

=== DOCUMENT 2 — DOMAIN KNOWLEDGE BASE ({domain} domain — adapt to this user's context) ===
{domain_md}
=== END DOCUMENT 2 ===

Your output must be a single unified SKILL.md with the following structure and requirements:

---

## Structure to produce:

### Header
Keep the file header exactly as in Document 1 (name, domain, Jira ID, generated date, filename).

### Quick Agent Summary (rewrite this section — make it rich and specific)
Write 8–12 sentences that serve as a direct briefing to the agent. Cover:
- Who this person is: role, seniority, team scale, location, experience
- What they own: specific projects, workflow types, production targets
- How they think and communicate: decision style, preferred summary format, escalation threshold
- What stresses them: capacity risks, quality drops, missed deadlines, unclear scope
- What the agent must always do for them: their non-negotiables (e.g. "always include project name in alerts")
- Their Phase 1 data sources and primary use cases
Write directly to the agent: "This user is…", "When {first_name} asks about…", "Always…", "Never…"

### 1. Active Projects (preserve exactly from Document 1, then enrich)
Keep all project data. For each active project, add 2–3 sentences of domain context:
what this type of project typically involves in the {domain} domain, common risks, and what \
the agent should watch for given this user's declared metrics and KPIs.

### 2. Team & Stakeholders (preserve exactly from Document 1)
Keep as-is. Add a "How to communicate with stakeholders" paragraph drawn from the domain \
knowledge — specific to the communication patterns and escalation norms for a {domain}.

### 3. Tools & Systems (preserve exactly from Document 1)
Keep all configured tools. For each tool (Jira, Confluence, Power BI / Databricks), add a \
short paragraph on how a {domain} typically uses it — what queries to run, what to watch, \
what thresholds matter — personalised to the user's declared projects and metrics.

### 4. Working Patterns & Style (new section — synthesize from both documents)
Write a detailed section covering:
- Daily rhythm: how this person starts their day, what they check first, what a good morning \
  briefing looks like for them specifically
- Decision-making: how they weigh trade-offs, when they escalate vs solve themselves
- Communication style: how they write updates, what level of detail they want in alerts
- Stress signals and how the agent should respond
- What "done well" looks like for this person in their role
Draw heavily from the domain SKILL.md interview insights and ground them in this user's \
specific project context and declared preferences.

### 5. Metrics Profile (preserve table exactly, then add interpretation)
Keep the metrics table unchanged. Below it, add a "How to interpret these metrics" paragraph \
for each declared metric — what a normal vs alarming value looks like for a {domain}, \
what the likely root cause is, and what action the agent should suggest.

### 6. Domain-Specific Configuration (preserve exactly from Document 1)

### 7. Active Use Cases (preserve exactly from Document 1)
Keep the use case table. For each opted-in use case, add a paragraph explaining exactly how \
it applies to this user — which of their projects trigger it, what output they expect, and \
any personalisation based on their preferences.

### 8. Domain Expertise & Knowledge Base (new section — from Document 2, adapted to this user)
This is the agent's reference library for this user's domain. Include:
- The core responsibilities and pressures of a {domain} (adapted to this user's team scale \
  and project types — skip anything that clearly does not apply)
- Key workflows this user manages: how they work, common failure modes, what good looks like
- Domain-specific KPIs and thresholds the agent should know (aligned to user's declared metrics)
- Escalation paths and stakeholder communication norms for this domain
- Common questions this user is likely to ask and how to answer them well
- Red flags the agent should proactively surface without being asked
Be specific and detailed — this is not a summary, it is a reference the agent uses in real time.

### 9. Data Access Consent (preserve exactly from Document 1)

### 10. Agent Preferences (preserve exactly from Document 1)

### 11. AI Guardrails (preserve exactly from Document 1)
Keep all guardrails. Add 3–5 additional domain-specific guardrails drawn from Document 2 — \
things an agent must or must never do when working with a {domain}.

---

CRITICAL RULES:
- NEVER alter any personal data: names, email, Jira ID, project codes, dates, numbers, \
  consent flags, metrics targets, quiet hours. Preserve them character-for-character.
- DO NOT produce short summaries. Every section must be detailed, specific, and actionable.
- DO NOT include generic domain text that does not apply to this user's declared projects, \
  team scale, or opted-in use cases.
- The output must read as if written by someone who knows this person well — grounded in \
  their specific context, not a template with their name inserted.
- Output ONLY the merged markdown. No preamble, no explanation, no code fences.\
"""


def _extract_domain(user_md: str) -> str:
    """Return the domain label from the **Domain:** line in the personal skill.md."""
    m = re.search(r"\*\*Domain:\*\*\s*(.+?)(?:\s{2,}|\n)", user_md)
    return m.group(1).strip() if m else ""


def _extract_name(user_md: str) -> str:
    """Return the user's full name from the # heading in the personal skill.md."""
    m = re.search(r"^#\s+(.+?)\s+—", user_md, re.MULTILINE)
    return m.group(1).strip() if m else "the user"


def _load_domain_md(domain_label: str, domains_dir: Path) -> str:
    """Return domain SKILL.md content, or empty string if none found."""
    folder_name = _DOMAIN_FOLDER.get(domain_label, "")
    if not folder_name:
        logger.warning("No domain folder mapped for '%s' — skip domain merge", domain_label)
        return ""
    skill_path = domains_dir / folder_name / "SKILL.md"
    if not skill_path.exists():
        logger.warning("Domain SKILL.md not found: %s", skill_path)
        return ""
    logger.debug("Loaded domain SKILL.md: %s", skill_path)
    return skill_path.read_text(encoding="utf-8")


def _get_access_token(pat_token: str, credential: Any) -> str:
    """
    Return a Databricks bearer token.
    PAT takes priority; falls back to Azure credential (Service Principal / az login).
    """
    if pat_token:
        return pat_token
    if credential is None:
        return ""
    token = credential.get_token(f"{_DATABRICKS_RESOURCE}/.default")
    return token.token


def _call_llm(
    user_md: str,
    domain_md: str,
    domain_label: str,
    host: str,
    pat_token: str,
    model: str,
    credential: Any = None,
) -> str:
    """
    Call the Databricks Foundation Model API (OpenAI-compatible).
    Auth: PAT token if set, otherwise Azure credential (same as MultiTenantAgent_V3).
    Falls back to plain concatenation on any error.
    """
    if not host:
        logger.warning("DATABRICKS_HOST not set — concatenating without LLM merge")
        return _concat_fallback(user_md, domain_md)

    access_token = _get_access_token(pat_token, credential)
    if not access_token:
        logger.warning("No Databricks auth available — concatenating without LLM merge")
        return _concat_fallback(user_md, domain_md)

    name = _extract_name(user_md)
    first_name = name.split()[0] if name else "the user"
    prompt = _MERGE_PROMPT.format(
        user_md=user_md,
        domain_md=domain_md,
        domain=domain_label,
        name=name,
        first_name=first_name,
    )
    url = f"{host.rstrip('/')}/serving-endpoints/{model}/invocations"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16000,   # rich comprehensive output needs more tokens
        "temperature": 0.2,
    }

    logger.info("Calling LLM (%s) to merge skill profiles…", model)
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=180)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        logger.info("LLM merge complete (%d chars)", len(content))
        return content
    except Exception as exc:
        logger.error("LLM call failed (%s) — falling back to concatenation", exc)
        return _concat_fallback(user_md, domain_md)


def _concat_fallback(user_md: str, domain_md: str) -> str:
    if not domain_md:
        return user_md
    return (
        user_md
        + "\n\n---\n\n"
        + "## Domain Knowledge Context\n\n"
        + "_Note: LLM merge unavailable — domain context appended as-is._\n\n"
        + domain_md
    )


def merge(
    user_skill_path: Path,
    domains_dir: Path,
    combined_dir: Path,
    databricks_host: str,
    databricks_pat_token: str,
    databricks_llm_model: str,
    credential: Any = None,
) -> Path:
    """
    Merge a user's personal skill.md with the matching domain SKILL.md.
    Auth: PAT token if set, otherwise Azure credential (Service Principal / az login).
    Writes the result to combined_dir and returns the output path.
    """
    user_md = user_skill_path.read_text(encoding="utf-8")
    domain_label = _extract_domain(user_md)
    domain_md = _load_domain_md(domain_label, domains_dir)

    if domain_md:
        combined_md = _call_llm(
            user_md=user_md,
            domain_md=domain_md,
            domain_label=domain_label,
            host=databricks_host,
            pat_token=databricks_pat_token,
            model=databricks_llm_model,
            credential=credential,
        )
    else:
        logger.info(
            "No domain SKILL.md for '%s' — personal profile used as-is for '%s'",
            domain_label,
            user_skill_path.name,
        )
        combined_md = user_md

    combined_dir.mkdir(parents=True, exist_ok=True)
    out_path = combined_dir / user_skill_path.name
    out_path.write_text(combined_md, encoding="utf-8")
    logger.info("Combined skill written → %s", out_path)
    return out_path
