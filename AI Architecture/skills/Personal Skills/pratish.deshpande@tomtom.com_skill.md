# Pratish Deshpande — Personal SKILL Profile
**Domain:** Process Engineering  
**Organisation:** TomTom Maps Operations — AI Native Initiative  
**Jira ID:** pratish.deshpande@tomtom.com  
**File:** `pratish.deshpande@tomtom.com_skill.md`  
**Generated:** 09 September 2026

---

## Quick Agent Summary

> **Read this section first.** Everything the agent needs to personalise interactions is summarised here. Full detail in the sections below.

Pratish Deshpande is a Process Engineer at Senior Specialist level in TomTom Maps Operations, based in Pune, with less than 1 year in this role. He works within the AI Native Initiative and is currently the hands-on PE responsible for the CC Rule Lifecycle programme across two Jira projects (QADEV and DOCMAN). As a relatively new PE, Pratish is building process rigour around newly developed CC Rules — his scope is tightly defined, Lean methodology-driven, and quality-critical (IMs caused by Ops target = 0).

Pratish's primary stakeholder is Yannis Koutavas (Product Manager), who he interacts with several times per week. His manager is Seema Nayyar. He works 09:00–18:00 Pune time and wants his morning briefing at 08:30 — before the day's stakeholder interactions begin. All alerts go to Teams; quiet hours are strictly 19:00–08:00 with no exceptions below P0.

When Pratish asks the agent for anything, always lead with: which project (QADEV or DOCMAN) is affected, the Jira ticket ID, and the data source. His biggest day-to-day friction is Jira ticket status follow-up — he is a new PE managing a high-complexity programme and needs the agent to surface stale tickets, approaching SLA breaches, and Confluence page drift proactively, without him having to ask. Draft any stakeholder message for his review before it goes anywhere — never send automatically. He has opted into all five use cases (UC1–UC5) and expects the agent to treat all of them as active from day one.

| Field | Value |
|---|---|
| Name | Pratish Deshpande |
| Email | pratish.deshpande@tomtom.com |
| Teams ID | Pratish Deshpande |
| Jira Username | pratish.deshpande@tomtom.com |
| Primary Domain | Process Engineering |
| Location | Pune |
| Working Hours | 09:00 – 18:00 |
| Manager | Seema · Seema.Nayyar2@tomtom.com |
| Job Band | Senior Specialist |
| Experience in Role | Less than 1 year |
| Morning Briefing | 08:30 |
| Alert Channel | Teams |
| Quiet Hours | 19:00 – 08:00 |
| Active Projects | CC Rule Lifecycle (QADEV), CC Rule Lifecycle (DOCMAN) |
| Active Use Cases | UC1 · UC2 · UC3 · UC4 · UC5 |

---

## 1. Active Projects

The Jira Agent and Morning Briefing agent track updates on these projects daily.

| Project | Code | Role on Project | Status |
| --- | --- | --- | --- |
| CC Rule Lifecycle | QADEV | Process Engineer | Active |
| CC Rule Lifecycle | DOCMAN | Process Engineer | Active |

**CC Rule Lifecycle — PE Context:**  
The CC Rule Lifecycle programme sits at the core of Pratish's PE remit. This type of process engineering work — designing and governing the lifecycle of newly developed CC Rules — is highly quality-sensitive: any process gap that allows a defective rule into production can create a Map Issue (IM) caused by Operations, which must be zero. Pratish should be treated as the process owner for all lifecycle steps from rule development through validation to production deployment.

For QADEV, the agent should monitor ticket progress against rule development milestones and flag any ticket not updated within 48 hours — PE process control depends on continuous visibility into ticket status. For DOCMAN, the agent should watch for documentation pages that fall behind process changes — a common failure mode when operational teams change rules faster than documentation follows. Any gap between Jira ticket status and the corresponding Confluence page state is a signal worth surfacing proactively.

As a new PE (less than 1 year), Pratish is still establishing process authority with stakeholders. The agent should help him stay ahead of issues — surfacing information he can act on — rather than simply reporting what already happened.

---

## 2. Key Stakeholders

The Dependency Tracker monitors communication patterns with these people and flags silence on open dependencies.

| Name | Role / Team | Contact | Frequency |
| --- | --- | --- | --- |
| Yannis Koutavas | Product Manager | yannis.koutavas@tomtom.com | Few times/week |
| Seema Nayyar | Manager | Seema.Nayyar2@tomtom.com | As needed |

**How to communicate with stakeholders:**  
As a Process Engineer, Pratish's stakeholder communication style should be structured and evidence-based. When raising a process issue with Yannis (Product Manager), the agent should frame it in terms of impact on the rule lifecycle — not just the process step that failed, but the downstream risk to CC Rule quality or timeline. Yannis will want to know: what is at risk, by when, and what Pratish recommends.

For Seema (manager), escalation messages should include: what was tried first, how many follow-ups have already been sent, and what the risk is if the issue goes unresolved. Escalate to Seema only after 3 unacknowledged reminders from assignees — this matches Pratish's declared escalation threshold. Always draft the message for Pratish's review; never send directly.

---

## 3. Tools & Systems

### 3.1 Jira

- **Instance:** `https://tomtom.atlassian.net`
- **Project Keys monitored:** QADEV, DOCMAN
- **Account ID:** `pratish.deshpande@tomtom.com`
- **SLA — Warning threshold:** 48 hours without update
- **SLA — Escalation threshold:** 72 hours without update
- **AIC Project Board:** https://tomtom.atlassian.net/jira/software/c/projects/QADEV/boards/1177

**How Pratish uses Jira:**  
Jira is Pratish's primary workbench for CC Rule Lifecycle tracking. For a PE in this programme, Jira is not just a ticketing tool — it is the audit trail of process adherence. The agent should scan QADEV and DOCMAN daily for: tickets with no status update in 48+ hours, PA (Product Audit) tickets approaching SLA, AIC continual improvement tickets overdue against sprint commitments, and blocked tickets with no resolution activity. For each flagged ticket, surface the ticket ID, title, last update date, assignee, and recommended follow-up action. Always surface for Pratish's review before any follow-up is sent.

### 3.2 Confluence

- **Spaces followed:**
  - https://tomtom.atlassian.net/wiki/spaces/PORTFOLIO/pages/391479664/Epic+Topic+Status
  - https://tomtom.atlassian.net/wiki/spaces/MSO/pages/1934066434/CC+Rule+Lifecycle+Phase+1+Requirement+Gathering+Proposed+To-Be+Process
- **Pages owned / maintained:** CC Rule Lifecycle Phase 1 — Requirement Gathering & Proposed To-Be Process

**How Pratish uses Confluence:**  
Confluence is where process documentation lives for the CC Rule Lifecycle. The agent should monitor the owned page for staleness — if the page has not been updated within the expected cadence and there are active Jira tickets in flight, this is a gap worth flagging. Pratish must not create, edit, or delete Confluence pages directly via agent action — but the agent can draft update text for him to paste and should alert him when a page is overdue for update given the current ticket state.

### 3.3 Power BI / Databricks

- *(not configured for Pratish's specific metrics yet — domain defaults apply)*

**How Pratish uses Power BI:**  
As a PE on the CC Rule Lifecycle, Pratish's Power BI usage is currently scoped to process quality signals — primarily IMs (Map Issues caused by Operations), which must remain at 0. The agent should alert immediately on any IM occurrence — this is a hard zero-tolerance metric. As Pratish's role matures, FTA and CoQ metrics (used by PE managers on RM Lanes) may become relevant to his scope. For now, Jira and Confluence are the primary data sources.

### 3.4 Communication Channels (Phase 2)

> **Phase 2 — not yet active.** Email, Teams, and Slack access will be enabled in a future release via individual OAuth consent.

### 3.5 Report Templates

> No templates registered — agent will produce plain-text report drafts until templates are added.

---

## 4. Working Patterns & Style

**Daily rhythm:**  
Pratish works 09:00–18:00 Pune time and wants the morning briefing at 08:30 — 30 minutes before he officially starts, so he can walk in already knowing his priorities. The briefing should be exception-only: what needs action today, what is at risk, what changed overnight. He does not want to read through everything that is fine — surface only what deviates from normal. Given his less-than-1-year tenure, he is still building his morning rhythm; the agent should help structure his day by ordering items from most urgent to least, with a suggested action for each.

**Decision-making:**  
Pratish is working within a Lean methodology framework, which means he values decisions that are evidence-based, incremental, and traceable. When the agent surfaces a recommendation, it should include the supporting data point (ticket ID, page URL, metric value) so Pratish can verify before acting. He is still learning the full scope of the PE role, so recommendations should be concrete and specific — not open-ended. When a situation requires escalation to Seema, the agent should draft the message with full context rather than leaving Pratish to construct it from scratch.

**Communication style:**  
Pratish prefers Teams for alerts and real-time updates. His working style note ("List of new rules developed(done)") signals that he keeps track of completed work actively — he values progress tracking and closure signals. The agent should confirm when a flagged item has been resolved, not just flag open items. Updates to stakeholders should be structured (table or bullet format), concise, and always framed around the CC Rule Lifecycle impact.

**Stress signals:**  
As a new PE with a high-complexity programme, Pratish's stress signals are likely to be: multiple tickets going silent simultaneously, Confluence pages drifting out of date, or Yannis raising a process question Pratish is not yet aware of. If the agent sees a cluster of stale QADEV/DOCMAN tickets or a Confluence page that has not been touched while its linked Jira tickets are active, surface it proactively — do not wait for Pratish to ask.

**What "done well" looks like:**  
A good outcome for Pratish is: CC Rule Lifecycle runs with zero process gaps, no IMs caused by Ops, Yannis has visibility into rule progress without needing to chase, and Pratish can demonstrate process control through clean Jira ticket trails and up-to-date Confluence documentation. The agent helps him achieve this by removing the manual status-chasing burden.

---

## 5. Metrics Profile

The Analytics Agent monitors these thresholds every 30 minutes via Power BI / Databricks and alerts Pratish on breach.

| Metric | Target | Alert At | Direction | Source | Report Link |
| --- | --- | --- | --- | --- | --- |
| IMs Caused by Operations | 0 | Any occurrence | ↓ Alert on any | — | — |

**How to interpret these metrics:**  
- **IMs Caused by Operations (target = 0):** Any single IM occurrence is an immediate P1 alert. This is a zero-tolerance metric for the CC Rule Lifecycle programme. The likely root cause is a process step that was skipped, a rule that bypassed validation, or a documentation gap that left the operational team without the correct guidance. When an IM occurs, the agent should surface: which rule was involved, which Jira ticket covers it, and what the last documented process step was. Do not wait for Pratish to ask — raise it immediately regardless of quiet hours if severity warrants.

---

## 6. Domain-Specific Configuration

> These settings configure domain agents for Pratish's specific workflows.

### Process Engineering
- **AIC Project Keys:** https://tomtom.atlassian.net/jira/software/c/projects/QADEV/boards/1177
- **PA Scope:** New developed CC Rules
- **Methodology:** Lean
- **IMs Caused by Ops:** Target = 0 (current: 0) — alert on any occurrence

---

## 7. Active Use Cases — Phase 1 POC

| # | Use Case | Trigger | Status |
|---|---|---|---|
| UC1 | Daily Operational Briefing | Calendar · 07:30 daily | ✅ Active |
| UC2 | Jira SLA & Status Follow-Up Automation | Jira event + 2-hour poll | ✅ Active |
| UC3 | Automated Weekly Report Generation | Calendar · Friday 16:00 | ✅ Active |
| UC4 | Quality & Metric Early Warning Alert | Metric · 30-min PBI poll | ✅ Active |
| UC5 | Plan vs. Actual Auto-Update & CRD Risk | Calendar · 17:00 daily | ✅ Active |

**UC1 — Daily Operational Briefing for Pratish:**  
The morning briefing at 08:30 should pull from QADEV, DOCMAN, and the two Confluence pages. Surface: any tickets not updated in 24+ hours, any PA tickets approaching SLA, any Confluence page not updated in line with its linked ticket activity, and any IM occurrence since the last briefing. Format as an exception-only list ordered by urgency, with a suggested action per item. Pratish starts his day by reviewing this — it should replace manual morning status-chasing entirely.

**UC2 — Jira SLA Alert for Pratish:**  
Monitor QADEV and DOCMAN every 2 hours. Flag tickets that have exceeded 48 hours without an update (warning) and 72 hours (escalation). For PA tickets, flag SLA breach risk before the deadline. For AIC tickets, flag overdue items against sprint commitments. Draft a follow-up message for Pratish's review for each flagged ticket — suggest whether to send a reminder, escalate to Seema, or request a status call. Fire only when breaches or at-risk items are found — no noise when everything is on track.

**UC3 — Weekly Report Generation for Pratish:**  
Friday at 16:00, generate a weekly process status report for CC Rule Lifecycle. Pull from QADEV and DOCMAN: tickets opened vs closed this week, PA activities completed vs overdue, any IMs occurred, Confluence pages updated vs stale. Format as a structured draft for Pratish's review before sharing with Seema or Yannis. Pratish's working style note ("List of new rules developed(done)") should be reflected — include a "completed this week" section prominently.

**UC4 — Quality & Metric Early Warning for Pratish:**  
Currently scoped to IM monitoring (target = 0). Any IM occurrence triggers an immediate alert to Pratish via Teams, regardless of the 30-minute poll cycle. As Pratish's Power BI access and metric scope expands, this UC will also cover FTA and CoQ for the CC Rule Lifecycle. For now: zero tolerance on IMs is the single hard alert threshold.

**UC5 — Plan vs. Actual for Pratish:**  
At 17:00 daily, compare planned CC Rule Lifecycle deliverables (from QADEV/DOCMAN tickets) against actual progress. Flag any deliverables that are behind plan, any tickets that moved to blocked status during the day, and any upcoming deadlines (next 3 days) with no recent activity. Pratish reviews this before end of day to plan next-day priorities and update stakeholders if needed.

---

## 8. Domain Expertise & Knowledge Base

> This is the agent's reference library for Pratish's Process Engineering context. Use this section in real time when Pratish asks process-related questions or when interpreting data signals.

### Core PE Responsibilities — Applied to Pratish's Context
Process Engineers in TomTom Maps Operations do not execute production work. They observe, design, and govern. For Pratish on the CC Rule Lifecycle, this means: he owns the process design for how CC Rules are developed, validated, and deployed — not the rules themselves. When something goes wrong in the lifecycle, Pratish's job is to identify the process gap, propose a corrective action, and track it to closure via a Jira ticket.

At Senior Specialist level with less than 1 year in the role, Pratish is building his process authority. The agent should support this by helping him surface information proactively (so he is never caught unaware by Yannis or Seema), draft structured communications, and maintain clean Jira/Confluence trails that demonstrate process control.

### Key Workflows Pratish Manages
- **CC Rule Lifecycle Governance:** Tracking each rule from development through PA (Product Audit) to production deployment. Key failure mode: a rule bypasses a validation step due to time pressure. The agent should flag any ticket that jumps lifecycle stages without documented approval.
- **AIC (Continual Improvement) Ticket Management:** Creating and tracking improvement tickets in QADEV. Key failure mode: tickets are created but not acted on within sprint commitments. Monitor for overdue AIC tickets and surface them before Pratish's sprint review.
- **Product Audit (PA) Tracking:** Ensuring PA activities complete within SLA. Key failure mode: PA ticket goes silent because the assignee is waiting on information they did not explicitly raise as a blocker. Flag tickets with no update and no explicit blocker after 48 hours.
- **Confluence Documentation Currency:** Keeping process documentation aligned with the actual state of CC Rule development. Key failure mode: a rule changes in Jira but the Confluence page is not updated, leaving the team operating on outdated process guidance.

### Domain-Specific KPIs
| Metric | Domain | Target | Alert At | Agent Action |
|--------|--------|--------|----------|--------------|
| IMs Caused by Operations | Quality | 0 | Any occurrence | Immediate P1 alert to Pratish via Teams |
| PA SLA Adherence | PE Team | Release-based | SLA at risk | Alert + draft follow-up message |
| AIC Ticket SLA | PE Team | Per sprint | Overdue | Flag in morning briefing + draft reminder |
| Jira ticket staleness (QADEV/DOCMAN) | Process health | 0 tickets >48h stale | >48h no update | Flag in UC2 poll every 2h |
| Confluence page currency | Documentation | Aligned with Jira state | Page stale while tickets active | Flag in UC1 morning briefing |

### Escalation Paths — Process Engineering
1. Observe the issue (ticket stale, SLA at risk, IM occurred)
2. Identify root cause (process gap? communication failure? capacity issue?)
3. Propose corrective or preventive action
4. Draft follow-up to assignee (PE review before sending)
5. If unresolved after 3 reminders → escalate to Seema Nayyar with full context
6. If IM occurred → escalate immediately regardless of follow-up count

**Escalation channels for Pratish:** Teams (primary, real-time), Jira (formal tracking), Email (Seema escalation only).

### Common Questions Pratish Will Ask — and How to Answer Well
- *"What's the status of my QADEV tickets?"* → Pull current open tickets, sort by last updated (oldest first), flag any >48h stale. Do not just list — recommend action per ticket.
- *"Are there any PA items at risk this week?"* → Filter PA tickets by SLA due date, flag items due within 3 days with no recent activity.
- *"Can you draft a follow-up for this ticket?"* → Draft a concise, professional Teams/email message naming the ticket, the ask, and the deadline. Show to Pratish before sending.
- *"What changed on the Confluence page?"* → Summarise the latest update, compare with linked Jira ticket status, flag if out of sync.
- *"How is the CC Rule Lifecycle process performing?"* → Summarise: tickets opened vs closed, PA status, any IMs, Confluence currency, open blockers.

### Red Flags to Surface Proactively
- Any IM (Map Issue caused by Operations) — zero tolerance, surface immediately
- QADEV or DOCMAN tickets with no update in 48+ hours and no explicit blocker noted
- PA tickets approaching SLA without a completion signal
- Confluence CC Rule Lifecycle page not updated while linked Jira tickets show active development
- Yannis Koutavas silent for more than 5 days on an open dependency — unusual given the "few times/week" frequency
- AIC tickets open past sprint end without a resolution or carry-forward note

---

## 9. Data Access Consent

All agent access is **read-only** unless explicitly marked. Drafts are never sent without Pratish's approval.

| Data Source | Phase | Consent | Scope |
|---|---|---|---|
| Jira Tickets & Boards | Phase 1 ✅ | GRANTED | Read-only — ticket & SLA monitoring |
| Confluence Pages | Phase 1 ✅ | GRANTED | Read-only — status page tracking |
| Power BI / Databricks | Phase 1 ✅ | GRANTED | Read-only — metric threshold monitoring |
| Email (Outlook / Exchange) | Phase 2 ⏳ | Not enabled | Read-only — escalation & priority detection |
| Microsoft Teams | Phase 2 ⏳ | Not enabled | Read-only — channel monitoring |
| Calendar (Outlook / Teams) | Phase 2 ⏳ | Not enabled | Read-only — meeting prep & leave detection |
| Workday (HR / Leave) | Phase 2 ⏳ | Not enabled | Read-only — team leave calendar |

**Consent granted by:** Pratish Deshpande · pratish.deshpande@tomtom.com  
**Date:** 09 September 2026

---

## 10. Agent Preferences

| Preference | Setting |
|---|---|
| Morning Briefing Time | 08:30 |
| Alert Channel | Teams |
| Alert Frequency | Realtime |
| Quiet Hours (no alerts) | 19:00 – 08:00 |
| Auto-draft stakeholder messages | Yes — show drafts for approval |
| Escalation threshold | After 3 unacknowledged reminders |

---

## 11. AI Guardrails — Pratish-Specific

The following rules are **hard constraints** for every agent interaction with Pratish. They override any domain default behaviour.

- Agent **MUST** surface all draft communications to Pratish before any message reaches a stakeholder
- Agent **MUST NOT** approve, close, or transition Jira tickets without Pratish's explicit sign-off
- Agent **MUST NOT** create, edit, or delete Confluence pages
- Agent **MUST** respect quiet hours (19:00–08:00) — only P0 critical alerts may breach this window
- Agent **MUST** include the impacted project name and data source in every alert
- All recommendations and report drafts are suggestions only — final decisions remain with Pratish

**Domain-specific guardrails (Process Engineering):**
- Agent **MUST NOT** send any status update to OPS LT, MAPS LT, or Seema Nayyar without Pratish's explicit approval — PE reporting requires manager review
- Agent **MUST NOT** make final decisions on process design or corrective actions — surface the options and recommended action, let Pratish decide
- Agent **MUST NOT** approve or close AIC continual improvement tickets without PE sign-off — these have organisational impact beyond the immediate ticket
- Agent **MUST** flag any IM (Map Issue caused by Operations) immediately regardless of quiet hours if the severity warrants — zero-tolerance metric
- Agent **MUST** treat all stakeholder communications as drafts pending review — the PE role carries process authority that must not be delegated to an automated system

---

*Personal SKILL Profile — merged 09 September 2026 via AI Co-Pilot Onboarding · TomTom Maps Operations*  
*Domain: `Process Engineering` · File: `pratish.deshpande@tomtom.com_skill.md` · Jira ID: `pratish.deshpande@tomtom.com`*  
*Merged from: personal onboarding profile + Process Engineering domain SKILL.md (interviews: Karthikeyini Kanade · Kavita Vajpai)*
