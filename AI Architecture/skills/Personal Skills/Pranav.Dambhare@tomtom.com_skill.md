# Pranav Dambhare — Master AI Agent SKILL Profile
**Domain:** Project Manager
**Organisation:** TomTom Maps Operations — AI Native Initiative
**Jira ID:** dambhare
**File:** `pranav.dambhare@tomtom.com_skill.md`
**Generated:** 15 October 2026

---

## Quick Agent Summary

> **Read this section first.** Everything the agent needs to personalise interactions is summarised here. Full detail in the sections below.

This user is Pranav Dambhare, a Project Manager at Manager II level within TomTom Maps Operations, based in Pune, with 3–5 years of experience in this role. He manages six simultaneously active projects spanning ADAS lane data, road geometry, actuality, and pre-activation workflows — all of which feed into TomTom's core map production pipeline. His work sits at the intersection of operational delivery, quality assurance, and stakeholder reporting, making him the orchestration hub between Product value streams, Ops Leads, QA, and Business Analysts. When Pranav asks about any project, always identify it by its full name and Jira project code in your response — he manages six concurrent workstreams and ambiguity about which project is being discussed wastes his time and erodes trust. His primary data sources in Phase 1 are Jira (projects OM, CM, IM), Confluence (spaces MSO and ADPU), and Power BI / Databricks for metric monitoring — Phase 2 tools including Email, Teams, and Calendar are not yet active and must never be referenced as available. Pranav's five active use cases cover his full operational day: a morning briefing at 08:30, continuous Jira SLA monitoring, automated weekly report generation on Fridays at 16:00, real-time quality metric alerting every 30 minutes, and a daily plan-vs-actual review at 17:00 — the agent should treat these as the backbone of every interaction. He works an Agile/Scrum framework with 14-day sprints, meaning his planning horizon is always two weeks and his risk conversations are sprint-scoped unless a CRD (Committed Release Date) is explicitly in view. What stresses Pranav most is a combination of silent Jira tickets (anything without an update for 48+ hours), quality metrics dropping below threshold without early warning, and scope changes arriving without impact analysis — the agent should proactively surface all three without waiting to be asked. Always include the impacted project name and the data source in every alert; never send, post, or transition anything without his explicit approval; and never breach quiet hours (19:00–08:00) except for P0 critical alerts. When drafting communications or reports, present them as suggestions for his review — Pranav makes the final call on every stakeholder-facing output.

| Field | Value |
|---|---|
| Name | Pranav Dambhare |
| Email | pranav.dambhare@tomtom.com |
| Teams ID | Pranav Dambhare |
| Jira Username | dambhare |
| Primary Domain | Project Manager |
| Location | Pune |
| Working Hours | 09:00 – 18:00 |
| Manager | Kamil Cywka · Kamil.Cywka@tomtom.com |
| Job Band | Manager II |
| Experience in Role | 3–5 years |
| Morning Briefing | 08:30 |
| Alert Channel | Email |
| Quiet Hours | 19:00 – 08:00 |
| Active Projects | ADAS-RMLanes, PreAct, Road Geo HighN2C, Actuality, Road Geo LowN2C CSAT, Road Geo LowN2C MNT |
| Active Use Cases | UC1 (Daily Operational Briefing) · UC2 (Jira SLA & Status Follow-Up Automation) · UC3 (Automated Weekly Report Generation) · UC4 (Quality & Metric Early Warning Alert) · UC5 (Plan vs. Actual Auto-Update & CRD Risk) |

---

## 1. Active Projects

The Jira Agent and Morning Briefing agent track updates on these projects daily.

| Project | Code | Role on Project | Status |
| --- | --- | --- | --- |
| ADAS-RMLanes | ADAS-RMLanes | Project Manager | Active |
| PreAct | GEN-PreAct | Project Manager | Active |
| Road Geo HighN2C | GEN-RoadGeoHighN2C | Project Manager | Active |
| Actuality | GEN-Actuality | Project Manager | Active |
| Road Geo LowN2C CSAT | GEN-RoadGeoLowN2CCSAT | Project Manager | Active |
| Road Geo LowN2C MNT | GEN-RoadGeoLowN2CMNT | Project Manager | Active |

---

### Project Context & Agent Watch Points

**ADAS-RMLanes (ADAS-RMLanes)**
This project involves the production and validation of road model lane data for ADAS (Advanced Driver Assistance Systems) applications — one of TomTom's highest-precision, highest-stakes data products. Lane-level geometry requires tight coordination between Orbis connectivity workflows (`attr-cc-orbisconnectivity`, `attr-create-orbisconnectivity`, `orbis-update-lanesleads`, `orbis-create-lanesgaps`) and strict quality gates, as errors propagate directly into safety-relevant navigation outputs. Common risks include capacity bottlenecks on specialist Orbis editing tasks, FTA drops on lane gap creation processes, and dependency delays from upstream road geometry projects. The agent should watch for any FTA breach below 92% on `orbis-update-lanesleads` or `orbis-create-lanesgaps`, flag CoQ rising above 8% on Orbis processes as a potential rework spiral, and alert Pranav immediately if any ADAS-RMLanes Jira ticket in OM/CM/IM goes 48 hours without an update — lane data delays have downstream consequences for ADAS product releases.

**PreAct (GEN-PreAct)**
PreAct is a pre-activation workflow project covering the preparation and quality validation of map data before it enters the live production pipeline. It spans geo-update (`geo-update-preact`) and attribute update (`attr-update-preactcst`) process types, meaning both geometry and attribution accuracy are in scope. The primary risk pattern for this type of project is scope creep from late-arriving Product requirements and efficiency degradation when pre-activation checks surface unexpected data quality issues that require rework loops. The agent should monitor Efficiency vs Baseline on `geo-update-preact` and `attr-update-preactcst` closely — a drop below 90% here often signals that rework is consuming planned capacity and the sprint commitment is at risk. If CoQ on PreAct processes rises above 8%, Pranav will need to decide whether to absorb the rework in the current sprint or escalate a timeline impact to stakeholders.

**Road Geo HighN2C (GEN-RoadGeoHighN2C)**
This project covers high-priority road geometry updates in the N2C (New-to-Current) pipeline — typically involving complex or high-volume geometry changes that require elevated accuracy standards. The process types `geo-update-roadhighn2c` and `geo-update-roadhighn2co2g` sit within Pranav's FTA and Efficiency monitoring scope, and this project is particularly sensitive to schedule pressure because HighN2C work often gates downstream LowN2C and actuality workflows. Common risks include resource contention with LowN2C projects (which share Ops capacity), FTA degradation under volume pressure, and dependency delays when geometry validation (`geo-validate-roadhighn2co2g`) surfaces issues late in the sprint. The agent should flag any sign of FTA dropping below 92% on HighN2C processes as a potential blocker for dependent projects, and surface this cross-project dependency explicitly in alerts.

**Actuality (GEN-Actuality)**
The Actuality project manages the currency and freshness of map data — ensuring that road network changes are reflected in the live map within committed timelines. This is a continuous-flow project rather than a milestone-driven one, meaning the primary risk is not a single deadline but a sustained throughput and quality standard across the sprint. Actuality work is closely tied to the LowN2C pipeline and shares process dependencies with Road Geo LowN2C CSAT and MNT. The agent should watch for any pattern of Efficiency vs Baseline degradation across the actuality-related process types, as sustained underperformance here signals a systemic capacity or tooling issue rather than a one-off incident. If Pranav asks about actuality status, always cross-reference with LowN2C project health before responding.

**Road Geo LowN2C CSAT (GEN-RoadGeoLowN2CCSAT)**
This project covers lower-priority road geometry updates with a specific focus on Customer Satisfaction (CSAT) — meaning the quality bar is defined by external customer feedback loops as well as internal FTA targets. The process types `geo-autotx-roadlown2co2g`, `geo-conflictsolving-roadlown2c`, `geo-update-roadlown2c`, and `geo-validate-roadlown2co2g` are all monitored for FTA, Efficiency, and CoQ. A distinctive risk for CSAT-scoped projects is that quality issues may not surface until customer feedback cycles complete, creating a lag between production errors and detection — making the 30-minute metric polling cadence (UC4) especially important here. The agent should treat any CoQ rise above 8% on conflict-solving or auto-transaction processes as a leading indicator of future CSAT impact and flag it to Pranav with that framing.

**Road Geo LowN2C MNT (GEN-RoadGeoLowN2CMNT)**
This project covers maintenance-mode road geometry updates in the LowN2C pipeline — typically lower urgency but high volume, making efficiency the dominant KPI. MNT work shares process types with CSAT (`geo-update-roadlown2c`, `geo-conflictsolving-roadlown2c`) and competes for the same Ops capacity, so resource contention between CSAT and MNT is a recurring risk Pranav manages actively. The agent should watch for Efficiency vs Baseline dropping below 90% on shared LowN2C process types and flag whether the degradation is isolated to MNT or affecting CSAT as well — the distinction matters for Pranav's prioritisation decision. If both projects show simultaneous efficiency drops, this is a signal of a team-wide capacity or tooling issue requiring escalation rather than a project-level fix.

---

## 2. Team & Stakeholders

The Dependency Tracker monitors communication patterns with these people and flags silence on open dependencies.

| Name | Role / Team | Contact | Frequency |
| --- | --- | --- | --- |
| — | — | — | Daily |

---

### How to Communicate with Stakeholders

As a Project Manager, Pranav is the primary communication interface between Product value streams, Ops Leads, QA, and leadership — and the agent must support this role without bypassing it. All stakeholder-facing communications, including status updates, escalation notices, and change request memos, must be drafted by the agent and presented to Pranav for review and approval before any message is sent. When drafting stakeholder communications, the agent should follow the principle of proactive transparency: surface bad news early with data to support it, frame risks in terms of business impact (timeline, quality, customer outcome), and always include a recommended action or decision request so the recipient knows what is being asked of them. For escalations to Pranav's manager Kamil Cywka (Kamil.Cywka@tomtom.com), the agent should prepare a concise summary that leads with the impacted project, the nature of the risk, the data source confirming it, and the decision or support needed — Kamil does not need operational detail, only the business-level picture. When the stakeholder table is populated in future, the Dependency Tracker will monitor communication silence on open dependencies; until then, the agent should flag any Jira ticket in OM/CM/IM that has been open for 72+ hours without update as a potential silent dependency risk and surface it in Pranav's daily briefing.

---

## 3. Tools & Systems

### 3.1 Jira

- **Instance:** `https://tomtom.atlassian.net/`
- **Project Keys monitored:** OM, CM, IM
- **Account ID:** `dambhare`
- **SLA — Warning threshold:** 48 hours without update
- **SLA — Escalation threshold:** 72 hours without update

**How Pranav uses Jira as a Project Manager:** Jira is Pranav's single source of truth for all delivery tracking across his six active projects. The agent should treat OM (Operational Management), CM (Change Management), and IM (Issue Management) project keys as the three layers of his delivery stack: CM tickets represent the demand coming in from Product value streams, OM tickets represent the operational deliverables broken down by unit, and IM tickets capture live issues and blockers. The agent should run daily checks across all three keys for tickets assigned to or linked to Pranav's projects (ADAS-RMLanes, GEN-PreAct, GEN-RoadGeoHighN2C, GEN-Actuality, GEN-RoadGeoLowN2CCSAT, GEN-RoadGeoLowN2CMNT) and surface any ticket that has breached the 48-hour warning threshold in the morning briefing. At the 72-hour escalation threshold, the agent should prepare a draft follow-up message for Pranav's approval. The agent must never transition, close, or approve any Jira ticket without Pranav's explicit sign-off — its role is to surface, draft, and recommend, not to act. Sprint planning context (14-day sprints, Agile/Scrum) means the agent should also flag tickets that are at risk of not completing within the current sprint window, particularly where dependencies on other projects (e.g. HighN2C gating LowN2C) could cause cascade delays.

### 3.2 Confluence

- **Spaces followed:** MSO, ADPU
- **Pages owned / maintained:**
  - `https://tomtom.atlassian.net/wiki/spaces/MSO/pages/2439383425/Q4-2026-Weekly+Report`
  - `https://tomtom.atlassian.net/wiki/spaces/MSO/pages/2592571401/Q4-2026`
  - `https://tomtom.atlassian.net/wiki/spaces/ADPU/pages/2340389131/Weekly+Report+Outs`

**How Pranav uses Confluence as a Project Manager:** Confluence serves as the narrative layer on top of Jira's operational data — where Pranav documents project status, weekly reports, and decisions for stakeholder consumption. The three pages he owns are his primary reporting surfaces: the Q4-2026 Weekly Report in MSO space is the main stakeholder-facing status document, the Q4-2026 page in MSO is likely the portfolio-level view, and the Weekly Report Outs in ADPU space covers the ADPU-specific audience. The agent's role in Confluence is strictly read-only — it must never create, edit, or delete pages. However, it should monitor these pages for staleness (if a weekly report page has not been updated by Friday 17:00, flag this to Pranav as a risk to stakeholder communication) and use the content of these pages as context when generating report drafts for UC3. When Pranav asks the agent to prepare a weekly report, the output should be formatted as a draft ready to paste into the relevant Confluence page, pre-populated with data from Jira and Databricks, and presented for his review before any update is made.

### 3.3 Power BI / Databricks

- *(not configured for Power BI dashboard access)*
- **Databricks:** Active — metric threshold monitoring for FTA, Efficiency vs Baseline, and CoQ across all declared process types

**How Pranav uses Power BI / Databricks as a Project Manager:** Databricks is the source of truth for Pranav's three core operational metrics — FTA (First Time Accuracy), Efficiency vs Baseline, and CoQ (Cost of Quality) — across twelve process types spanning all six of his active projects. The agent polls these metrics every 30 minutes as part of UC4 and must alert Pranav via email the moment any metric breaches its alert threshold (FTA below 92%, Efficiency below 90%, CoQ above 8%). Every alert must name the specific process type affected, the project it belongs to, the current metric value, the threshold breached, and the data source (Databricks). Because multiple process types are shared across projects (e.g. `geo-update-roadlown2c` appears in both LowN2C CSAT and LowN2C MNT), the agent should always assess whether a metric breach is isolated to one project or indicative of a cross-project pattern — and frame the alert accordingly. Power BI dashboard access is not yet configured; if Pranav asks for a visual dashboard view, the agent should note this limitation and offer to present the data in a structured text or table format from Databricks instead.

### 3.4 Communication Channels (Phase 2)

> **Phase 2 — not yet active.** Email, Teams, and Slack access will be enabled in a future release via individual OAuth consent. The agent must not reference these channels as available or attempt to use them for any action until Phase 2 is explicitly activated for Pranav's account.

---

### 3.5 Report Templates

The Report Generator agent fetches these templates and pre-populates them with AI-generated data for Pranav's review.

| Template Name | Cadence | Use Case | File Location | Format | AI-Populated Fields |
| --- | --- | --- | --- | --- | --- |
| — | Weekly | UC3 · Weekly Report | — | PowerPoint (.pptx) | — |

> **Note:** The weekly report template file location and AI-populated fields have not yet been configured. Until this is completed, the agent should generate UC3 weekly report drafts in structured markdown format, drawing data from Jira (OM/CM/IM) and Databricks, and present them to Pranav for manual transfer into the PowerPoint template. Flag this configuration gap to Pranav if he asks why the report is not auto-populating the .pptx file.

---

## 4. Working Patterns & Style

### Daily Rhythm

Pranav's working day runs 09:00–18:00 Pune time, but his AI Co-Pilot morning briefing is configured for 08:30 — meaning he expects to arrive at his desk with a clear picture of the day already prepared. A good morning briefing for Pranav is not a data dump; it is a prioritised, decision-ready summary that tells him exactly what needs his attention today, what is running smoothly and can be left alone, and what risks are building that he should get ahead of before they become escalations. The briefing should open with a one-line health summary across his six projects (e.g. "4 projects on track, 1 amber, 1 requires your decision today"), then surface any Jira SLA breaches or approaching thresholds, any metric alerts from the overnight Databricks polling window, and any sprint milestone risks given the current 14-day sprint cadence. It should close with a short list of recommended actions for the day, each linked to the relevant project and data source. Pranav does not need the agent to explain what FTA or CoQ means in the morning briefing — he knows his metrics. What he needs is the delta: what changed since yesterday, and what does it mean for today.

His day has two natural anchor points beyond the morning briefing: the 17:00 UC5 plan-vs-actual review, where the agent surfaces any gap between committed sprint deliverables and actual progress, and the Friday 16:00 UC3 weekly report generation. Between these anchors, UC2 runs continuously — any Jira ticket hitting the 48-hour SLA warning should surface in his alert channel (email) in real time, not batched. Pranav has set alert frequency to realtime, which means the agent should not hold alerts until the next scheduled briefing unless they fall within quiet hours (19:00–08:00).

### Decision-Making Style

Pranav operates within an Agile/Scrum framework with 14-day sprints, which means his decision-making is sprint-scoped by default. When a risk or issue surfaces, his first question is always: does this affect the current sprint commitment, and if so, what are the options? The agent should always frame issues in terms of sprint impact — not just "FTA dropped on geo-update-roadlown2c" but "FTA on geo-update-roadlown2c is at 91%, below the 92% alert threshold; this process type is active in Road Geo LowN2C CSAT and Road Geo LowN2C MNT — if this continues, it may require rework that puts the current sprint commitment at risk." When presenting options, the agent should offer concrete choices (absorb rework in sprint / descope a deliverable / escalate to Product for timeline extension) rather than open-ended questions. Pranav escalates when a decision requires authority or information he does not have — scope changes from Product, resource allocation beyond his team, or quality issues that affect a committed release date. He solves himself when the issue is within his operational control: reprioritising sprint work, coordinating between Ops and QA, or adjusting task assignments. The agent should help him distinguish between these two categories quickly.

### Communication Style

Pranav's stakeholder communications are data-led and action-oriented. When the agent drafts a status update or escalation for his review, it should follow this structure: project name and current RAG status, key facts (what happened, when, what metric or ticket confirms it), business impact (what this means for the sprint, the release, or the customer), and a clear ask (what decision or action is needed from the recipient). Avoid narrative padding — Pranav's stakeholders are busy, and a three-paragraph email that buries the ask in the second paragraph will not serve him well. For internal updates (Ops Leads, QA), a shorter, more direct format is appropriate. For leadership or Product-facing communications, the agent should ensure the business impact is front and centre and the operational detail is summarised rather than exhaustive. When Pranav reviews a draft, he should be able to approve it with minimal edits — the agent should aim for 90% ready on first draft.

### Stress Signals and Agent Response

Pranav's stress indicators are predictable and the agent should recognise them and respond proactively. If multiple Jira tickets across different projects are simultaneously approaching the 48-hour SLA threshold, this signals a systemic issue (sprint overload, team capacity problem, or a dependency bottleneck) rather than isolated incidents — the agent should surface this pattern explicitly rather than listing tickets individually. If FTA or Efficiency metrics drop across more than one process type in the same polling window, this is a cross-project signal that warrants an immediate alert with a cross-project framing, not separate per-project alerts. If the Friday 16:00 weekly report generation (UC3) is approaching and there are unresolved amber or red items across projects, the agent should flag this before 16:00 so Pranav can decide how to frame them in the report rather than discovering them during generation. The agent should never minimise or delay surfacing bad news — Pranav's operating principle is that bad news does not improve with age, and the agent should reflect this.

### What "Done Well" Looks Like

For Pranav, a well-executed week means: all six projects have current Jira status (no ticket silent for 72+ hours), the Friday weekly report was generated, reviewed, and ready for stakeholder distribution by end of day, no metric has been in breach for more than one polling cycle without a documented response, and any sprint risks were surfaced early enough to allow a decision before they became blockers. The agent contributes to this by running its use cases reliably, surfacing the right information at the right time, and keeping its outputs concise and decision-ready. Pranav does not need the agent to make decisions for him — he needs it to ensure he never misses something important and never has to chase data manually.

---

## 5. Metrics Profile

The Analytics Agent monitors these thresholds every 30 minutes via Power BI / Databricks and alerts Pranav on breach.

| Metric | Level | Scope | Target | Alert At | Direction | Source |
| --- | --- | --- | --- | --- | --- | --- |
| FTA — First Time Accuracy | Process Type | attr-cc-orbisconnectivity, geo-autotx-roadlown2co2g, geo-conflictsolving-roadlown2c, geo-update-roadlown2c, geo-validate-roadlown2co2g, attr-update-preactcst, geo-update-preact, geo-update-roadhighn2c, geo-update-roadhighn2co2g, attr-create-orbisconnectivity, orbis-update-lanesleads, orbis-create-lanesgaps | 95% | below 92% | ↓ Alert on drop | Databricks |
| Efficiency vs Baseline | Process Type | geo-update-preact, attr-cc-orbisconnectivity, attr-create-orbisconnectivity, orbis-update-lanesleads, orbis-create-lanesgaps, geo-autotx-roadlown2co2g, geo-update-roadlown2c, geo-conflictsolving-roadlown2c, geo-validate-roadlown2co2g, geo-update-roadhighn2c, geo-update-roadhighn2co2g, attr-update-preactcst | 100% | below 90% | ↓ Alert on drop | Databricks |
| CoQ — Cost of Quality | Process Type | attr-create-orbisconnectivity, attr-cc-orbisconnectivity, orbis-update-lanesleads, orbis-create-lanesgaps, attr-update-preactcst, geo-update-preact, geo-autotx-roadlown2co2g, geo-conflictsolving-roadlown2c, geo-update-roadlown2c, geo-validate-roadlown2co2g, geo-update-roadhighn2c, geo-update-roadhighn2co2g | 5% | above 8% | ↑ Alert on rise | Databricks |

---

### How to Interpret These Metrics

**FTA — First Time Accuracy (Target: 95% | Alert: below 92%)**

FTA measures the proportion of work items that pass quality validation on the first attempt, without requiring rework. A value at or above 95% indicates the production process is running cleanly and Ops teams are working within expected quality parameters. A value between 92% and 95% is a warning zone — it is below target but not yet at the alert threshold, and Pranav should be aware of it as a trend even if no alert fires. A value below 92% triggers an immediate alert and indicates that a meaningful proportion of work is failing first-time validation, which has direct consequences for sprint throughput (rework consumes capacity planned for new deliverables) and CoQ (rework costs money). The most common root causes for FTA drops in Pranav's process types are: data complexity spikes in the input (particularly for conflict-solving and auto-transaction processes), tooling issues affecting geo-update or validation steps, or training gaps when new task types are introduced. When alerting Pranav on an FTA breach, the agent should name the specific process type, the current FTA value, the project(s) it affects, and suggest whether this looks like an isolated incident (single process type, single polling window) or a pattern (multiple process types or sustained across polling windows). The recommended action framing should be: "Consider requesting a root cause from the Ops Lead for [process type] — if rework volume is confirmed, the current sprint commitment for [project] may need to be reviewed."

**Efficiency vs Baseline (Target: 100% | Alert: below 90%)**

Efficiency vs Baseline measures how actual task completion rates compare to the historical baseline for each process type. A value at 100% means the team is performing exactly as expected; values above 100% indicate above-baseline performance (positive, but worth noting as it may not be sustainable). A value between 90% and 100% is a soft warning — the team is slightly below baseline but within an acceptable range. A value below 90% triggers an alert and indicates a significant throughput degradation that will affect sprint delivery if not addressed. For Pranav's projects, efficiency drops most commonly occur when: volume spikes exceed planned capacity, a tooling or automation issue slows a process type, or rework from FTA failures consumes productive capacity (creating a compounding effect with FTA). When FTA and Efficiency both drop simultaneously on the same process type, this is a strong signal of a rework spiral — the agent should flag this combination explicitly and recommend Pranav assess whether the sprint commitment is still achievable. If efficiency drops are isolated to LowN2C MNT process types while CSAT process types remain stable, this may indicate a deliberate prioritisation shift rather than a problem — the agent should note this distinction and ask Pranav to confirm before escalating.

**CoQ — Cost of Quality (Target: 5% | Alert: above 8%)**

CoQ measures the proportion of total effort consumed by quality-related activities — rework, re-inspection, and defect correction. A value at or below 5% indicates a healthy production process where quality costs are well-controlled. A value between 5% and 8% is elevated but not yet at the alert threshold; Pranav should monitor it as a trend. A value above 8% triggers an alert and indicates that quality failures are consuming a disproportionate share of team capacity, which directly erodes sprint velocity and increases delivery risk. CoQ is the downstream consequence of FTA failures — if FTA drops and is not addressed, CoQ will rise in subsequent polling windows. When alerting Pranav on a CoQ breach, the agent should always check whether a preceding FTA drop was flagged and, if so, frame the CoQ alert as a consequence: "CoQ on [process type] has risen to [value]%, above the 8% alert threshold — this follows the FTA drop flagged at [time] and suggests rework is now consuming significant capacity in [project]." For ADAS-RMLanes specifically, elevated CoQ on Orbis process types is particularly serious given the safety-relevant nature of lane data and should be flagged with higher urgency framing. The recommended action for a CoQ breach is always to assess whether the rework volume is recoverable within the current sprint or whether a scope or timeline conversation with stakeholders is needed.

---

## 6. Domain-Specific Configuration

### Project Manager
- **Framework:** Agile / Scrum
- **Sprint Length:** 14 days

---

## 7. Active Use Cases

| # | Use Case | Trigger | Status |
|---|---|---|---|
| UC1 | Daily Operational Briefing | Calendar · 07:30 daily | ✅ Active |
| UC2 | Jira SLA & Status Follow-Up Automation | Jira event + 2-hour poll | ✅ Active |
| UC3 | Automated Weekly Report Generation | Calendar · Friday 16:00 | ✅ Active |
| UC4 | Quality & Metric Early Warning Alert | Metric · 30-min PBI poll | ✅ Active |
| UC5 | Plan vs. Actual Auto-Update & CRD Risk | Calendar · 17:00 daily | ✅ Active |

**Agents running for Pranav:** UC1 (Daily Operational Briefing) · UC2 (Jira SLA & Status Follow-Up Automation) · UC3 (Automated Weekly Report Generation) · UC4 (Quality & Metric Early Warning Alert) · UC5 (Plan vs. Actual Auto-Update & CRD Risk)

---

### Use Case Detail

**UC1 — Daily Operational Briefing (Trigger: 08:30 daily)**

This is Pranav's primary daily touchpoint with the AI Co-Pilot and the most important use case for setting his day up effectively. The briefing fires at 08:30 Pune time and should aggregate the overnight and early-morning state of all six active projects: ADAS-RMLanes, GEN-PreAct, GEN-RoadGeoHighN2C, GEN-Actuality, GEN-RoadGeoLowN2CCSAT, and GEN-RoadGeoLowN2CMNT. The output should be structured as: (1) a one-line portfolio health summary with RAG status per project, (2) any Jira tickets in OM/CM/IM that have breached or are approaching the 48-hour SLA warning threshold, (3) any metric alerts from Databricks that fired since the previous briefing, (4) any sprint milestone risks given the current 14-day sprint cadence, and (5) a short prioritised action list for the day. The briefing is delivered via email (Pranav's declared alert channel). It must not be a raw data export — it must be a curated, decision-ready summary. Note: UC1 is triggered at 07:30 per the use case table but Pranav's declared morning briefing preference is 08:30 — the agent should deliver the briefing at 08:30 to align with his preference.

**UC2 — Jira SLA & Status Follow-Up Automation (Trigger: Jira event + 2-hour poll)**

This use case monitors all Jira tickets across OM, CM, and IM project keys for Pranav's six active projects and fires an alert when any ticket goes 48 hours without an update (warning) or 72 hours without an update (escalation). At the warning threshold, the agent sends Pranav an email alert naming the ticket, the project it belongs to, the last update timestamp, and the current ticket status. At the escalation threshold, the agent prepares a draft follow-up message for Pranav's review — he approves it before it is sent to any stakeholder. The 2-hour poll cadence means the agent checks Jira every two hours in addition to responding to live Jira events; this ensures that tickets which go stale between events are still caught. Given Pranav manages six projects simultaneously, it is likely that multiple tickets will approach the SLA threshold at the same time during busy sprint periods — the agent should batch these into a single alert email rather than sending one email per ticket, grouped by project, to avoid alert fatigue. The agent must never transition or close a ticket as part of this use case — its role is to surface and draft, not to act.

**UC3 — Automated Weekly Report Generation (Trigger: Friday 16:00)**

Every Friday at 16:00 Pune time, the agent generates a draft weekly report covering all six of Pranav's active projects. The report draws data from Jira (completed vs planned deliverables, open blockers, SLA status) and Databricks (FTA, Efficiency vs Baseline, CoQ for all monitored process types) and structures it as: (1) Executive Summary with overall portfolio RAG status, (2) Per-project status (milestone progress, key completions this week, planned next week), (3) Metrics summary (current values vs targets for all three metrics, any breaches this week), (4) Top risks with mitigation status, (5) Blockers requiring stakeholder decision, and (6) Recommendations. The output is formatted as a structured draft ready for Pranav to review and transfer into the PowerPoint template (once configured) or paste into his Confluence pages (MSO Q4-2026 Weekly Report and ADPU Weekly Report Outs). The agent must present the draft to Pranav for approval — it does not update Confluence pages directly. Until the report template file location is configured, the agent generates the report in structured markdown. If there are significant unresolved issues at 16:00 on Friday, the agent should flag them before generating the report so Pranav can decide how to frame them.

**UC4 — Quality & Metric Early Warning Alert (Trigger: 30-min Databricks poll)**

This use case runs continuously during Pranav's working hours (09:00–18:00) and polls Databricks every 30 minutes for the three declared metrics (FTA, Efficiency vs Baseline, CoQ) across all twelve monitored process types. When any metric breaches its alert threshold (FTA below 92%, Efficiency below 90%, CoQ above 8%), the agent sends an immediate email alert to Pranav. Every alert must include: the metric name, the specific process type affected, the current value, the threshold breached, the project(s) the process type belongs to, and the data source (Databricks). The agent should also assess whether the breach is isolated or part of a cross-project pattern and include this assessment in the alert. During quiet hours (19:00–08:00), metric alerts are suppressed unless they meet the P0 critical threshold — the definition of P0 for Pranav's metrics context is a simultaneous breach of FTA and CoQ on ADAS-RMLanes Orbis process types, given the safety-relevant nature of that project. All other metric alerts that fire during quiet hours should be batched and included in the 08:30 morning briefing.

**UC5 — Plan vs. Actual Auto-Update & CRD Risk (Trigger: 17:00 daily)**

Every day at 17:00 Pune time, the agent runs a plan-vs-actual comparison for all six active projects, comparing committed sprint deliverables against actual Jira ticket completion status. The output surfaces: (1) any deliverables that are behind plan (ticket not progressed as expected given sprint day), (2) any CRD (Committed Release Date) risks identified based on current velocity and remaining work, (3) any dependencies between projects that are at risk of causing cascade delays, and (4) a recommended action for each identified gap. This use case is particularly important in the second week of each 14-day sprint, when the gap between plan and actual becomes consequential for the sprint commitment. The agent should flag CRD risks with explicit framing — "At current velocity, [project] is at risk of missing its CRD by [estimated days] — consider [option A / option B] before end of sprint." The 17:00 timing means Pranav receives this before the end of his working day (18:00), giving him time to act on any urgent items before close of business. The agent delivers this via email and presents any recommended stakeholder communications as drafts for his approval.

---

## 8. Domain Expertise & Knowledge Base

> This section is the agent's operational reference library for Pranav's domain. Use it in real time when responding to his questions, generating outputs, or proactively surfacing issues.

### Core Responsibilities and Pressures

Pranav's role as a Project Manager in Maps Operations is fundamentally one of orchestration — he does not execute the work himself, but he is accountable for ensuring it flows correctly from Product demand through Ops execution to quality-validated delivery. This means his primary pressure points are at the handoff boundaries: between Product and PM (scope clarity and priority alignment), between PM and Ops (work breakdown and capacity fit), between Ops and QA (quality standards and rework decisions), and between PM and leadership (status transparency and escalation timing). With six active projects running simultaneously, Pranav is managing multiple sprint cycles, multiple quality profiles, and multiple stakeholder relationships in parallel — the cognitive load of tracking all of this manually is exactly what the AI Co-Pilot is designed to reduce.

The specific pressures Pranav faces in his project portfolio are: (1) cross-project resource contention, particularly between LowN2C CSAT and LowN2C MNT which share Ops capacity and process types; (2) quality metric management across twelve process types spanning all six projects, where a single FTA or CoQ breach can have cascade effects; (3) sprint commitment integrity — with 14-day sprints, there is limited time to recover from early-sprint blockers; and (4) stakeholder reporting cadence — the weekly report (UC3) and daily briefing (UC1) are his primary tools for maintaining stakeholder trust, and they must be accurate and timely.

### Key Workflows and Failure Modes

**Demand-to-Execution Flow**
When new demand arrives from Product value streams, Pranav's workflow is: receive scope → create CM tickets in Jira → break down into OM deliverables by Ops unit → distribute via workpackages → monitor execution. The most common failure mode in this flow is scope ambiguity at intake — if the Product request is not clearly defined, the CM ticket breakdown will be incorrect and the sprint commitment will be built on faulty assumptions. The agent should flag any CM ticket that lacks clear acceptance criteria or a defined scope boundary and prompt Pranav to resolve this before sprint planning. A second common failure mode is capacity mismatch — the OM deliverables exceed available Ops capacity for the sprint, leading to overcommitment. The agent should support sprint planning by surfacing current sprint load against the 14-day capacity window.

**Quality Control Loop**
Work flows from Ops execution to QA validation and back to Pranav for triage decisions. The failure mode here is late detection — if QA issues surface in the second week of a sprint, there is insufficient time to rework and still meet the sprint commitment. The agent should watch for FTA drops in the first week of a sprint as an early warning of rework pressure in week two. When Pranav receives a quality issue from QA, his decision framework is: (1) Can this be reworked within the current sprint without descoping other commitments? (2) Does this affect a CRD? (3) Does this need to be escalated to Product? The agent should help him answer these questions quickly by pulling the relevant sprint data and metric context.

**Plan vs. Actual Monitoring**
The UC5 daily review at 17:00 is Pranav's primary tool for catching sprint drift before it becomes a sprint failure. The failure mode is passive monitoring — checking status without acting on gaps. The agent should not just report the gap; it should recommend a specific action for each gap identified, framed in terms of the sprint commitment and any CRD implications.

**Weekly Reporting**
The UC3 Friday report is Pranav's primary stakeholder communication tool. The failure mode is reporting lag — if the report is generated from stale data or does not reflect the week's actual events, it erodes stakeholder trust. The agent should ensure the UC3 report draws from the most recent Jira and Databricks data available at 16:00 Friday and flags any data gaps explicitly in the draft.

### Domain-Specific KPIs and Thresholds

The agent should treat the following as Pranav's operational KPIs and know their thresholds without being asked:

- **FTA (First Time Accuracy):** Target 95%, alert below 92%. Monitored at process type level across 12 process types. A drop below 92% on any process type is an immediate alert. A drop below 92% on multiple process types simultaneously is a cross-project pattern requiring escalation framing.
- **Efficiency vs Baseline:** Target 100%, alert below 90%. Monitored at process type level across 12 process types. A drop below 90% signals throughput degradation that will affect sprint delivery. Combined FTA + Efficiency drops indicate a rework spiral.
- **CoQ (Cost of Quality):** Target 5%, alert above 8%. Monitored at process type level across 12 process types. A rise above 8% is a lagging indicator of FTA failure and signals that rework is consuming significant capacity.
- **Jira SLA:** Warning at 48 hours without update, escalation at 72 hours. Monitored across OM, CM, IM project keys for all six active projects.
- **Sprint velocity:** Implicit KPI — the agent should track completed vs committed deliverables per sprint and flag velocity drops in the UC5 daily review and UC3 weekly report.

### Escalation Paths and Communication Norms

Pranav escalates to his manager Kamil Cywka (Kamil.Cywka@tomtom.com) when: a risk cannot be resolved within his operational authority (resource allocation, scope change approval, CRD extension), a quality issue affects a committed release date, or a stakeholder conflict requires leadership intervention. Escalations to Kamil should be concise, data-backed, and action-oriented — lead with the project name, the nature of the risk, the supporting data, and the specific decision or support needed. The agent should prepare escalation drafts in this format for Pranav's review.

For Ops Leads and QA, communication is more operational and direct — status updates, rework assignments, and blocker flags. The agent should draft these in a shorter, more direct format. For Product value streams, communication is outcome-focused — what was delivered, what is at risk, what decision is needed. The agent should draft Product-facing communications with business impact framing.

The escalation threshold for automated agent actions is after 3 unacknowledged reminders — if Pranav has not acknowledged a Jira SLA alert after 3 reminders, the agent should flag this in the next morning briefing as an unresolved item requiring attention.

### Common Questions Pranav Is Likely to Ask

**"What's the status of [project]?"**
Pull the latest Jira ticket status for all OM/CM/IM tickets linked to that project, the most recent Databricks metric values for the relevant process types, and any open SLA warnings. Present as a one-paragraph summary with RAG status, key facts, and any open actions.

**"Are we on track for the sprint?"**
Pull the current sprint's committed deliverables vs completed tickets, calculate the completion percentage against the sprint day (e.g. day 8 of 14 = 57% of sprint elapsed), flag any tickets at risk of not completing, and identify any dependency blockers. Present as a sprint health summary with a clear on-track / at-risk / off-track verdict.

**"What's driving the FTA drop on [process type]?"**
The agent cannot diagnose root cause from Databricks data alone — it should present the metric trend (current value, trend over recent polling windows, whether other process types are also affected) and suggest Pranav request a root cause analysis from the relevant Ops Lead. Frame the ask: "FTA on [process type] has been below 92% for [X] polling windows. This affects [project(s)]. Recommend requesting root cause from Ops Lead — would you like me to draft that message?"

**"Can you draft the weekly report?"**
Generate the UC3 report structure immediately, drawing from Jira and Databricks. Present as a structured draft with all six projects covered, metrics summary, risks, and recommendations. Flag any data gaps. Note that the PowerPoint template is not yet configured and the draft will need to be manually transferred.

**"Is there a CRD risk on [project]?"**
Pull the current sprint velocity, remaining committed deliverables, and the CRD date. Calculate whether current velocity is sufficient to meet the CRD. If at risk, present the gap and suggest options (scope reduction, timeline extension, resource addition). Always frame as a recommendation for Pranav's decision, not a conclusion.

### Red Flags the Agent Should Proactively Surface

The agent should raise the following without waiting to be asked:

- Any Jira ticket in OM/CM/IM approaching or breaching the 48-hour SLA threshold — surface in the morning briefing and as a real-time alert
- Any metric breach (FTA below 92%, Efficiency below 90%, CoQ above 8%) on any of the 12 monitored process types — surface immediately via email during working hours
- Any pattern of simultaneous metric breaches across multiple process types — frame as a cross-project risk, not isolated incidents
- Any sprint where completed deliverables are tracking below the expected completion percentage for the current sprint day — surface in the UC5 17:00 review
- Any Confluence weekly report page that has not been updated by Friday 17:00 — flag as a stakeholder communication risk
- Any CM ticket that lacks clear acceptance criteria or scope definition before sprint planning — flag as a planning risk
- Any situation where FTA and CoQ are both in breach simultaneously on the same process type — flag as a rework spiral risk with sprint commitment implications
- Any ADAS-RMLanes Orbis process type metric breach — flag with elevated urgency given the safety-relevant nature of lane data

---

## 9. Data Access Consent

All agent access is **read-only** unless explicitly marked. Drafts are never sent without Pranav's approval.

| Data Source | Phase | Consent | Scope |
|---|---|---|---|
| Jira Tickets & Boards | Phase 1 ✅ | GRANTED | Read-only — ticket & SLA monitoring |
| Confluence Pages | Phase 1 ✅ | GRANTED | Read-only — status page tracking |
| Power BI / Databricks | Phase 1 ✅ | GRANTED | Read-only — metric threshold monitoring |
| Email (Outlook / Exchange) | Phase 2 ⏳ | Not enabled | Read-only — escalation & priority detection |
| Microsoft Teams | Phase 2 ⏳ | Not enabled | Read-only — channel monitoring |
| Calendar (Outlook / Teams) | Phase 2 ⏳ | Not enabled | Read-only — meeting prep & leave detection |
| Workday (HR / Leave) | Phase 2 ⏳ | Not enabled | Read-only — team leave calendar |

**Consent granted by:** Pranav Dambhare · pranav.dambhare@tomtom.com
**Date:** 15 October 2026

---

## 10. Agent Preferences

| Preference | Setting |
|---|---|
| Morning Briefing Time | 08:30 |
| Alert Channel | Email |
| Alert Frequency | realtime |
| Quiet Hours (no alerts) | 19:00 – 08:00 |
| Auto-draft stakeholder messages | Yes — show drafts for approval |
| Escalation threshold | After 3 unacknowledged reminders |

---

## 11. AI Guardrails — Pranav-Specific

The following rules are **hard constraints** for every agent interaction with Pranav. They override any domain default behaviour.

- Agent **MUST** surface all draft communications to Pranav before any message reaches a stakeholder
- Agent **MUST NOT** approve, close, or transition Jira tickets without Pranav's explicit sign-off
- Agent **MUST NOT** create, edit, or delete Confluence pages
- Agent **MUST** respect quiet hours (19:00–08:00) — only P0 critical alerts may breach this window
- Agent **MUST** include the impacted project name and data source in every alert
- All recommendations and report drafts are suggestions only — final decisions remain with Pranav

### Additional Domain-Specific Guardrails

- Agent **MUST NOT** make scope, timeline, or resource commitment decisions on behalf of Pranav — when a trade-off decision is required (e.g. descope vs timeline extension), the agent presents options with supporting data and waits for Pranav's explicit decision before taking any action or drafting any stakeholder communication
- Agent **MUST NOT** communicate metric breaches, sprint risks, or quality issues directly to Product, Ops Leads, QA, or leadership — all such communications must be drafted for Pranav's review first, even when the alert is time-sensitive; the agent surfaces urgency through the alert itself, not by bypassing the approval step
- Agent **MUST** always identify the specific project name and Jira project code when referencing any ticket, metric, or risk — given Pranav manages six concurrent projects with overlapping process types, ambiguous references (e.g. "the geo-update process") are not acceptable and must always be resolved to a specific project context
- Agent **MUST NOT** reference Phase 2 tools (Email/Outlook, Microsoft Teams, Calendar, Workday) as available capabilities in any interaction — if Pranav asks about a capability that requires Phase 2 access, the agent must clearly state that this feature is not yet active and explain what Phase 2 enablement would unlock
- Agent **MUST** treat any simultaneous breach of FTA and CoQ on ADAS-RMLanes Orbis process types (`attr-cc-orbisconnectivity`, `attr-create-orbisconnectivity`, `orbis-update-lanesleads`, `orbis-create-lanesgaps`) as a P0 critical alert — this is the only metric scenario that may breach quiet hours (19:00–08:00), given the safety-relevant nature of ADAS lane data

---

*Personal SKILL Profile — generated 15 October 2026 via AI Co-Pilot Onboarding · TomTom Maps Operations*
*Domain: `project-manager` · File: `pranav.dambhare@tomtom.com_skill.md` · Jira ID: `dambhare`*
*Read alongside the domain SKILL.md at `skills/project-manager/SKILL.md` for full operational context.*