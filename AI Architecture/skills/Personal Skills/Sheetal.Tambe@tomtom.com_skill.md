# Sheetal Tambe — Master AI Agent SKILL Profile
**Domain:** Quality Lead
**Organisation:** TomTom Maps Operations — AI Native Initiative
**Jira ID:** Sheetal.Tambe@tomtom.com
**File:** `Sheetal.Tambe@tomtom.com_skill.md`
**Generated:** 25 September 2026

---

## Quick Agent Summary

> **Read this section first.** Everything the agent needs to personalise every interaction is here.

Sheetal Tambe is a Quality Lead in TomTom Maps Operations, responsible for monitoring and improving quality outcomes across all process types. Her primary focus is First Time Accuracy (FTA) and Cost of Quality (CoQ) — she needs to know immediately when quality metrics deviate from target, which process types are driving rejection, and how much rework cost (CopQ) the team is incurring. Efficiency reporting is not within her scope.

Morning briefing at 08:30, with a focus on quality exceptions only. Draft all stakeholder communications for her review before sending. Quiet hours 19:00–08:00 (P0 only).

| Field | Value |
|---|---|
| Name | Sheetal Tambe |
| Email | Sheetal.Tambe@tomtom.com |
| Teams ID | Sheetal Tambe |
| Jira Username | Sheetal.Tambe@tomtom.com |
| Primary Domain | Quality Lead — Maps Operations |
| Location | Pune |
| Working Hours | 09:00 – 18:00 |
| Morning Briefing Time | 08:30 |
| Alert Channel | Teams |
| Quiet Hours (no alerts) | 19:00 – 08:00 |
| Active Jira Projects | MCPET |

---

## 1. Active Projects

| Project | Code | Role on Project | Status |
| --- | --- | --- | --- |
| Quality Effectiveness | MCPET | Quality Lead | Active |

---

## 2. Key Stakeholders

| Name | Role / Team | Contact | Frequency |
| --- | --- | --- | --- |
| Project Managers | Delivery accountability | Teams · Jira | Daily |
| Operations Team | Production quality owners | Teams | As needed |
| Lalit Patkar | Director — escalation path | Teams | As needed |

---

## 3. Tools & Systems

### 3.1 Jira

- **Instance:** `https://tomtom.atlassian.net/`
- **Project Keys monitored:** MCPET
- **Account ID:** `Sheetal.Tambe@tomtom.com`
- **SLA — Warning threshold:** 48 hours without update
- **SLA — Escalation threshold:** 72 hours without update

Agent monitors MCPET daily for open tickets, SLA breaches, and quality-labelled items. Surface in the morning briefing ordered by urgency.

### 3.2 Databricks

Sheetal's scope covers all available process types prioritized by volume. The agent should report FTA and CoQ across all process types and highlight any process type falling below FTA target or showing elevated CoQ.

- **Scope:** All available process types (full table, sorted by volume)
- **Table:** `mo_occ_reporting.manual_efficiency.manual_efficiency_quality_all_weekly_tbl`

### 3.3 Confluence

No Confluence pages configured in skill.md.

---

## 4. Communication & Delivery Preferences

- **Format:** Exception-only — lead with what is wrong, not what is fine
- **Draft all outbound messages** for Sheetal's approval before sending
- **Alert immediately** when FTA drops below 92% or CoQ rises above 10%
- **Never close or transition** Jira tickets on her behalf

---

## 5. Metrics Profile

The Analytics Agent monitors these thresholds continuously via Databricks and alerts Sheetal on breach.

| Metric | Target | Alert At | Direction | Source |
| --- | --- | --- | --- | --- |
| FTA | 95% | below 92% | Alert on drop | Databricks |
| CoQ | <7% | above 10% | Alert on rise | Databricks |
| CopQ | Minimise | Sudden increase | Alert on spike | Databricks |

### How to Interpret These Metrics

**FTA (First Time Accuracy)**
FTA measures the proportion of tasks accepted on first QC check. Target 95%. If FTA drops to the amber zone (92–94.9%), monitor process-type breakdown for the source. Below 92% is a P1 alert — surface immediately with process type data.

**Cost of Quality (CoQ)**
CoQ is QC time as a proportion of total production + QC time. Target <7%. Amber zone 7–10%. Above 10% is P1 — identify which process types are driving rework and surface for investigation.

**Cost of Poor Quality (CopQ)**
CopQ is the rework cost attributable to rejected tasks — hours wasted on work that failed QC. Flag any week where CopQ hours show a significant spike versus the prior week.

---

## 6. Active Use Cases

| UC | Name | Trigger | Status |
|---|---|---|---|
| UC1 | Daily Operational Briefing | Calendar · 08:30 daily | ✅ Active |
| UC2 | Jira SLA & Status Follow-Up Automation | Jira event + 2-hour poll | ❌ Inactive |
| UC3 | Automated Weekly Report Generation | Calendar · Friday 16:00 | ✅ Active |
| UC4 | Quality & Metric Early Warning Alert | Metric · 30-min PBI poll | ✅ Active |
| UC5 | Plan vs. Actual Auto-Update & CRD Risk | Calendar · 17:00 daily | ❌ Inactive |

**UC1 — Daily Briefing for Sheetal:**
Morning briefing at 08:30. Lead with any FTA or CoQ exceptions. If all metrics are green, keep it brief — one summary line and the process-type table. No efficiency section needed.

---

## 7. Behaviour Rules

- **Quality first:** Always lead with FTA and CoQ. Do not include efficiency metrics.
- **Exception-only format:** If FTA ≥ 95% and CoQ < 7% and no Jira breaches, say so in one line.
- **Draft approval required:** Every outbound communication requires Sheetal's explicit approval.
- **Quiet hours:** No alerts 19:00–08:00 unless FTA < 92% (P0 threshold).
- **Data source:** Always cite Databricks and the week_start date when reporting metrics.
