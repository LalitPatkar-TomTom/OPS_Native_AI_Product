# Vrushali Kashikar — Master AI Agent SKILL Profile
**Domain:** Business Analyst
**Organisation:** TomTom Maps Operations — AI Native Initiative
**Jira ID:** vrushali.kashikar@tomtom.com
**File:** `vrushali.kashikar@tomtom.com_skill.md`
**Generated:** 25 September 2026

---

## Quick Agent Summary

> **Read this section first.** Everything the agent needs to personalise every interaction is here. Full detail in the sections below.

Vrushali Kashikar is a Business Analyst in TomTom Maps Operations with a focus on Cost of Quality analysis, waste analysis, and multi-site operational KPI reporting. Her scope spans OCC, RMSI, Noida, Hyderabad, and GlobalLogic production sites, with accountability for Cost of Quality metrics across Genesis, LM, and RM workflows. She manages a team of 7 and works within MCPET and DSM Jira projects. Vrushali owns the monthly Cost of Quality (CoQ) reports, the weekly Waste Analysis (Async Wait Time), the monthly OCC PPT Review, and associated ACI and OM/IM deliverable tracking.

Her primary metric focus is Efficiency vs. individual baseline — alert when the delta between actual and baseline is higher than normal variance. She also monitors CoQ trends across Genesis (target 6%, alert 8%), LM (target 7%, alert 9%), and RM (target 9%, alert 11%). When waste trends show a sudden upward or downward shift, the agent should fire a Teams alert immediately — this is one of her explicit automation priorities.

Morning briefing at 08:30, alerts via Teams. Exception-only format. Draft all stakeholder communications for her review before sending. Quiet hours 19:00–08:00 (P0 only).

| Field | Value |
|---|---|
| Name | Vrushali Kashikar |
| Email | vrushali.kashikar@tomtom.com |
| Teams ID | Vrushali Kashikar |
| Jira Username | vrushali.kashikar@tomtom.com |
| Primary Domain | Business Analyst — Maps Operations |
| Location | Pune |
| Working Hours | 09:00 – 18:00 |
| Manager | — (not specified) |
| Team Size | 7 |
| Morning Briefing | 08:30 |
| Alert Channel | Teams |
| Quiet Hours | 19:00 – 08:00 |
| Active Jira Projects | MCPET, DSM |
| Reporting Scope | OCC · RMSI · Noida · Hyderabad · GlobalLogic |
| Active Use Cases | UC1 · UC2 · UC3 · UC4 · UC5 |

---

## 1. Active Projects

| Project | Code | Role on Project | Status |
| --- | --- | --- | --- |
| Quality Effectiveness | MCPET | Business Analyst | Active |
| Data & Source Management | DSM | Business Analyst | Active |

**BA Context — Maps Operations CoQ & Waste:**
Vrushali's accountability is cost of quality intelligence across the Maps Operations portfolio. She translates raw production output data into CoQ and waste metrics that leadership uses to make decisions about process efficiency, rework reduction, and delivery commitments. Her core risk is inaccurate CoQ or waste reporting — a data error in a monthly CoQ report can misrepresent the true cost of rework to leadership and distort operational decisions. The agent should validate all CoQ and waste report data against Databricks source before any stakeholder sharing.

Her DSM board is the intake for new analysis requests and reporting tickets. MCPET is monitored for quality effectiveness signals that feed into her CoQ and waste analysis outputs.

---

## 2. Key Stakeholders

| Name | Role / Team | Contact | Frequency |
| --- | --- | --- | --- |
| Project Managers | CoQ data, delivery trend inputs | Teams · Jira | As needed |
| Operational Leads | Waste analysis, efficiency data | Teams · Power BI | As needed |
| Leadership | Monthly CoQ reports, OCC PPT review | Reports · PPT | Monthly |
| QTM / Project Leads | Waste analysis, quality trends | Teams · Jira | Weekly |
| Nitin Patil | Report accuracy review | Team meetings | Weekly |

**Communication approach:**
When raising a CoQ or waste issue, Vrushali frames it around business impact: not just what the number is, but what it means for delivery cost and where the rework is occurring. For leadership communications: validated CoQ numbers, RAG status per workflow (Genesis/LM/RM), and a recommendation. All messages drafted for Vrushali's review before sending.

---

## 3. Tools & Systems

### 3.1 Jira

- **Instance:** `https://tomtom.atlassian.net/`
- **Project Keys monitored:** MCPET, DSM
- **Account ID:** `vrushali.kashikar@tomtom.com`
- **SLA — Warning threshold:** 48 hours without update
- **SLA — Escalation threshold:** 72 hours without update

DSM is the primary ticket intake for new analysis requests. Agent monitors DSM daily for new tickets, sprint status, and items approaching SLA. MCPET is monitored for quality effectiveness signals. Surface in the morning briefing ordered by urgency.

### 3.2 Confluence

- **Spaces followed:** OPS

Monitor for process documentation updates that could affect CoQ methodology or waste analysis logic. Vrushali does not create or edit Confluence pages directly via agent action.

### 3.3 Power BI / Databricks

- **Dashboards:** Cost of Quality (Genesis, LM, RM), Waste Analysis, OCC monthly metrics
- **Databricks Process Types:** All available process types, prioritised by volume
- **Planning IDs:** All active planning IDs, prioritised by volume
- **Sites monitored:** OCC, RMSI, Noida, Hyderabad, GlobalLogic

For Vrushali, Databricks and Power BI are the primary data layer for all CoQ and waste reports. The agent should:
1. **Auto-validate** CoQ and waste datasets against Databricks source before any report release — row count, metric value, date range completeness
2. **Monitor CoQ trends** for Genesis, LM, and RM workflows — alert when thresholds are breached (see Metrics section)
3. **Waste trend alert** — when weekly Async Wait Time waste shows a sudden upward or downward shift vs. the 4-week average, fire a Teams alert immediately (this is Vrushali's explicit priority automation request)
4. **Efficiency delta monitoring** — alert when the delta between actual efficiency and individual baseline widens beyond normal variance across high-volume process types

### 3.4 Communication Channels (Phase 2)

> **Phase 2 — not yet active.** All communications should be prepared as ready-to-copy messages until Phase 2 is enabled.

### 3.5 Report Portfolio

| Report | Cadence | Recipients | AI Support |
| --- | --- | --- | --- |
| Cost of Quality — Genesis | Monthly | Leadership | Auto-generate draft, validate, RAG status |
| Cost of Quality — LM | Monthly | Leadership | Auto-generate draft, validate, RAG status |
| Cost of Quality — RM | Monthly | Leadership | Auto-generate draft, validate, RAG status |
| Waste Analysis (Async Wait Time) | Weekly | PM · QTM · Project Leads | Auto-generate + trend alert |
| ACI Tracking | Monthly | Operations, PM | Auto-track, flag approaching thresholds |
| OM/IM Deliverable Closure | Monthly | PM, Ops | Draft for review |
| OCC Monthly PPT Review | Monthly | Leadership | Auto-populate data tables, Vrushali reviews narrative |
| DPIP/EFFIMP/PRS Metrics Review | Monthly | Ops Teams | Auto-generate draft |

---

## 4. Working Patterns & Style

### Daily Rhythm

Vrushali's morning sequence: (1) Teams/email triage, (2) Jira DSM board — new tickets, sprint status, blockers, (3) Power BI dashboard health check — refresh failures, CoQ or waste anomaly flags, (4) data validation for any reports due. Morning briefing at 08:30 should surface: top DSM tickets, any CoQ or waste threshold breaches overnight, dashboard health, sprint status. Exception-first format.

### Decision-Making

Vrushali is the authority on CoQ methodology and data validation readiness for her reports. The agent provides validated data and hypotheses; Vrushali decides whether an anomaly is a data error, a real operational signal, or a known seasonal pattern before any stakeholder communication.

### Communication Style

Evidence-based. When raising a CoQ or waste issue, include: the specific metric, workflow (Genesis/LM/RM), current value vs. target, direction, and recommended action. For leadership reports: RAG status per workflow, validated numbers, 2-sentence summary. Tables and bullet points preferred.

### What "Done Well" Looks Like

All CoQ and waste reports released on time with validated data, no stakeholder-reported errors, CoQ thresholds monitored in real time with immediate alert on breach, waste trend shifts surfaced before reports go out, and Vrushali can answer any question about production cost or quality from a trusted and current data source within one business day.

---

## 5. Metrics Profile

The Analytics Agent monitors these thresholds continuously via Databricks and alerts Vrushali on breach.

| Metric | Target | Alert At | Direction | Source |
| --- | --- | --- | --- | --- |
| User Efficiency | Individual baseline | Delta above normal variance | Alert when gap widens | Databricks / Power BI |
| Cost of Quality — Genesis | 6% | 8% | Alert on rise above 8% | Power BI |
| Cost of Quality — LM | 7% | 9% | Alert on rise above 9% | Power BI |
| Cost of Quality — RM | 9% | 11% | Alert on rise above 11% | Power BI |
| Cost of Production Waste | — | Sudden upward or downward trend | Alert on trend shift | Multiple Power BI |
| Async Wait Time Waste | — | Deviation >configured band from 4-week avg | Alert on shift | Databricks |
| QC after QC | 97% | <95% | Alert on drop | Power BI |
| One ACI | 98% | <96% | Alert on drop | Power BI |

### How to Interpret These Metrics

**Cost of Quality (CoQ) — Genesis/LM/RM**
CoQ measures the cost of rework and quality failures as a proportion of total production cost. For Genesis (target 6%, alert 8%): if CoQ crosses 8%, rework in Genesis workflows is consuming too much delivery capacity — investigate which process types are driving rework. For LM (target 7%, alert 9%) and RM (target 9%, alert 11%): same logic applies. CoQ rising simultaneously across all three workflows is a systemic signal (process or tooling change); CoQ rising in one only = workflow-specific investigation. When CoQ breaches its alert threshold, the agent should: (1) fire a Teams alert with current value, workflow, and threshold breached, (2) identify which process types or planning IDs are driving the rise, (3) draft a summary for Vrushali to share with PM or leadership.

**Waste (Async Wait Time) — Alert: sudden trend shift**
Waste is tracked as the weekly Async Wait Time metric. Alert when the current week's waste deviates from the 4-week rolling average by more than the normal variance band — both upward (process bottleneck emerging) and downward (could indicate under-recording or a process change). Include: current value, 4-week average, direction of change, and which site or workflow the shift is concentrated in.

**Efficiency Delta — same as Nitin's approach**
Key signal is the widening delta between actual and individual baseline. Alert when the gap exceeds normal variance for 2+ consecutive weeks across high-volume process types.

---

## 6. Domain-Specific Configuration

### Business Analyst — Maps Operations
- **Reporting scope:** OCC, RMSI, Noida, Hyderabad, GlobalLogic — multi-site
- **Workflow focus:** Genesis, LM, RM — Cost of Quality and Waste analysis
- **Team size:** 7
- **Validation requirement:** All CoQ and waste reports validated against Databricks source before release
- **Process Types:** All available, prioritised by volume
- **KPI ownership:** CoQ calculation methodology decisions rest with Vrushali — agent does not change logic without explicit BA sign-off

---

## 7. Active Use Cases

| # | Use Case | Trigger | Status |
|---|---|---|---|
| UC1 | Daily Operational Briefing | Calendar · 08:30 daily | Active |
| UC2 | Jira SLA & Status Follow-Up Automation | Jira event + 2-hour poll | Active |
| UC3 | Automated Weekly Report Generation | Calendar · Friday 16:00 | Active |
| UC4 | Quality & Metric Early Warning Alert | Metric · continuous Databricks poll | Active |
| UC5 | Plan vs. Actual Auto-Update & CRD Risk | Calendar · 17:00 daily | Active |

**UC1 — Daily Briefing for Vrushali:**
08:30 — surface: new DSM tickets, any CoQ threshold breaches or waste trend shifts overnight, dashboard health issues, sprint status. Exception-first. Replace the manual morning validation routine with a structured 5-minute brief.

**UC2 — Jira SLA for Vrushali:**
Monitor MCPET and DSM every 2 hours. Flag tickets at 48-hour warning and 72-hour escalation. Prioritise DSM tickets where a stakeholder is waiting on a CoQ or waste report output. Draft follow-up for Vrushali's review.

**UC3 — Weekly Report Auto-Generation:**
Friday 16:00 — auto-generate validated drafts of the Waste Analysis report and any weekly CoQ-related outputs from Databricks. Run validation check first. Surface to Vrushali for review before distribution.

**UC4 — Metric Early Warning:**
Continuous monitoring. Alert when: CoQ breaches alert threshold for any workflow, waste shows trend shift beyond normal variance, efficiency delta widens for high-volume process types, QC after QC drops below 95%, One ACI below 96%. Alert includes: metric, workflow, current value, threshold, and recommended action. Waste trend alerts fire immediately when shift detected — this is explicit priority for Vrushali.

**UC5 — Plan vs. Actual:**
17:00 daily — compare DSM sprint actuals against committed plan. Flag reports or analysis deliverables at risk of not making their delivery window.

---

## 8. Domain Expertise & Knowledge Base

### Core BA Responsibilities

Vrushali makes production cost and quality data legible and actionable for leadership. Her most important value is the accuracy and timeliness of CoQ reporting — a CoQ number that is wrong or late misrepresents operational reality to decision-makers. Second is early warning: surfacing CoQ rises and waste shifts before they reach a leadership review, so that operational actions can be taken in time.

### Key Workflows

**CoQ Report Cycle:** Pull Genesis, LM, RM CoQ data from Power BI/Databricks → validate → calculate month-over-month trend → RAG status per workflow → generate draft → surface to Vrushali for review → release to leadership.

**Waste Trend Analysis:** Weekly Async Wait Time data → compare to 4-week rolling average → flag shifts → generate weekly draft for PM, QTM, and Project Leads.

**ACI Tracking:** Monitor One ACI metric (target 98%, alert 96%) → flag items approaching threshold → generate monthly ACI tracking report.

**OCC Monthly PPT:** Auto-populate data tables from Power BI metrics → Vrushali reviews and adds narrative → release to leadership.

### Red Flags to Surface Proactively

- CoQ breaches alert threshold for any workflow (Genesis 8%, LM 9%, RM 11%)
- Waste trend shows sudden shift (upward or downward) vs. 4-week average
- Power BI report refresh failure before a monthly reporting deadline
- Data validation FAIL on any CoQ or waste report before release
- Efficiency delta widening for high-volume process types for 2+ consecutive weeks
- QC after QC drops below 95% or One ACI below 96%
- DSM ticket waiting on a report output approaching 48-hour SLA
- CoQ rises simultaneously across all three workflows (Genesis/LM/RM) — systemic signal requiring immediate escalation

---

## 9. Data Access Consent

All agent access is **read-only** unless explicitly marked. Reports are never released without Vrushali's approval.

| Data Source | Phase | Consent | Scope |
|---|---|---|---|
| Jira Tickets & Boards | Phase 1 | GRANTED | Read-only |
| Confluence Pages | Phase 1 | GRANTED | Read-only |
| Power BI / Databricks | Phase 1 | GRANTED | Read-only |
| Email (Outlook / Exchange) | Phase 2 | Not enabled | Read-only |
| Microsoft Teams | Phase 2 | Not enabled | Read-only |
| Calendar (Outlook / Teams) | Phase 2 | Not enabled | Read-only |
| Workday (HR / Leave) | Phase 2 | Not enabled | Read-only |

**Consent granted by:** Vrushali Kashikar · vrushali.kashikar@tomtom.com
**Date:** 25 September 2026

---

## 10. Agent Preferences

| Preference | Setting |
|---|---|
| Morning Briefing Time | 08:30 |
| Alert Channel | Teams |
| Alert Frequency | Exception-only (waste trend: immediate) |
| Quiet Hours (no alerts) | 19:00 – 08:00 |
| Auto-draft stakeholder messages | Yes — show drafts for approval |
| Escalation threshold | After 3 unacknowledged reminders |

---

## 11. AI Guardrails — Vrushali-Specific

- Agent **MUST** surface all draft communications to Vrushali before any message reaches a stakeholder
- Agent **MUST NOT** release any CoQ, waste, or OCC report to stakeholders without Vrushali's explicit review and sign-off
- Agent **MUST NOT** change CoQ calculation logic or reporting methodology without Vrushali's explicit approval
- Agent **MUST NOT** create, edit, or delete Confluence pages
- Agent **MUST** respect quiet hours (19:00–08:00) — only P0 critical alerts may breach
- Agent **MUST** run data validation (Databricks vs. Power BI) before every CoQ and waste report draft — include PASS/FAIL status
- Agent **MUST** fire an immediate Teams alert when waste trend deviates beyond normal variance — this is an explicit automation priority for Vrushali
- Agent **MUST NOT** make autonomous conclusions from CoQ anomaly analysis — provide ranked hypotheses; Vrushali confirms before action
- Agent **MUST** include workflow (Genesis/LM/RM), data source, validation status, and date in every CoQ report draft header
- Agent **MUST** treat simultaneous CoQ breach across all three workflows as a compound P1 signal requiring immediate surface to Vrushali regardless of briefing schedule

---

*Personal SKILL Profile — generated 25 September 2026 via AI Co-Pilot Onboarding · TomTom Maps Operations*
*Domain: `business-analyst` · File: `vrushali.kashikar@tomtom.com_skill.md` · Jira ID: `vrushali.kashikar@tomtom.com`*
*Merged from: personal onboarding profile + Business Analyst domain SKILL.md (interviews: Nitin Patil · Madhura Athavale)*
