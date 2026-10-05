# Process Engineering — Skill Profile
## AI Co-Pilot Interview Analysis | TomTom Maps Operations | August 2026

**Synthesised from:** 2 interviews — Karthikeyini Kanade (Process Engineering Manager) · Kavita Vajpai (Manager I, PE Team)  
**Interview dates:** 31 July – 10 August 2026  
**Interviewers:** Pratish Deshpande

---

## 1. Role Identity

### What This Role Is
Process Engineering in Maps Operations sits at the intersection of operations and process design. PEs do not execute production work — they watch how work gets done, identify where it slows down, breaks, or drifts from standard, and turn those observations into structured improvements: documented processes, tracked action items, and metrics leadership can trust. At manager level, the role also carries people management, AIC (continual improvement) ticket governance, and Product Audit (PA) oversight.

### Role Levels Covered
| Role | Scope | Base |
|------|-------|------|
| Process Engineering Manager | Lead PE activities across Maps Platform & Operations unit (500+ operational footprint); RM Lanes program; FNR team support | OCC Hyderabad |
| Manager I (PE Team) | People manager for 18 PE team members in Pune; AIC continual improvement ticket governance; Product Audit (PA) tracking | Pune |

### What Only the PE Can Decide
- Process design effectiveness — whether a new or changed process is sound given operational context, architecture, and constraints
- AIC (continual improvement) ticket execution and prioritisation — Kavita Vajpai
- Corrective and preventive action selection when a process gap or quality issue is identified
- When a non-adherence situation escalates vs gets handled at team level

---

## 2. Daily Operating Rhythm

### Morning Sequence (both interviewees)
| Step | Action | Tool | Time |
|------|--------|------|------|
| 1 | Read emails — identify overnight escalations, scope changes, stakeholder inputs | Outlook | 10–20 min |
| 2 | Check Jira tickets — status of ongoing PA activities, critical process tickets, overdue items | Jira | 15–20 min |
| 3 | Check Confluence pages — status updates on process deliverables and team activities | Confluence | 10–15 min |
| 4 | Check Workday — team leaves, pending HR actions | Workday | 5–10 min |
| 5 | Check pre-production process status — any process impacting new deployment (Karthikeyini) | PBI dashboards / email | 10–15 min |
| 6 | Set priorities, assign tasks, plan follow-ups for the day | — | 10–15 min |

**Total morning overhead: 60–90 minutes — heavily driven by manual status chasing across Jira and Confluence**

### Reactive vs Proactive Split
| Person | Proactive | Reactive |
|--------|-----------|----------|
| Karthikeyini Kanade | Mostly proactive | Reactive for escalations |
| Kavita Vajpai | ~50% | ~50% |

---

## 3. Metrics Monitored

### Karthikeyini Kanade — Process Health & Quality
| Metric | Target | Alert At | Source |
|--------|--------|----------|--------|
| Productivity Improvement | — | Declining trend | Power BI |
| Map Issues Caused by Operations (IMs) | 0 | Any occurrence | — |
| Productivity Improvement (AI-enabled) | — | Declining trend | — |
| Yield & Efficiency (RM Lanes) | — | Deviation from baseline | Power BI |
| FTA (First Time Acceptance) | — | Declining trend | Power BI |
| CoQ (Cost of Quality) | — | Rising trend | Power BI |

### Kavita Vajpai — PE Team Operations
| Metric | Target | Alert At | Source |
|--------|--------|----------|--------|
| Product Audit (PA) | Release-based | SLA not met | Manual |
| Quality | 95% | Below 95% | PBI Reports |
| AIC Ticket SLA | Per agreement | Overdue | Jira |

---

## 4. Reporting Portfolio

### Weekly Reports
| Report | Owner | Recipients | Cadence |
|--------|-------|------------|---------|
| RM Lanes Weekly Report-Out | Karthikeyini | OPS LT · MAPS LT · OPS Contributors · Platform Members | Weekly |
| Documentation Status Update | Kavita | OPS-LT team | Weekly |

### Monthly / Quarterly Reports
| Report | Owner | Recipients | Cadence |
|--------|-------|------------|---------|
| Metric Report-Out (goals vs achievement) | Karthikeyini | OPS LT | Monthly |
| KPI Slides Update | Kavita | Monthly KPI review | Monthly |
| OKR Review & Update | Kavita | — | Quarterly |
| QC Effectiveness Programme Deliverables | Karthikeyini | Leadership | Quarterly |

---

## 5. Tools & Data Stack

| Tool | Used For | Frequency | Manual Effort |
|------|----------|-----------|---------------|
| Jira | Process ticket tracking, AIC tickets, PA follow-up, escalations | Multiple times/day | Manual status chasing — biggest time sink |
| Confluence | Process documentation, PA status pages, team deliverable tracking | Multiple times/day | Manual status updates and follow-up checks |
| Workday | Team leave management, HR actions, capacity awareness | Daily | Daily manual check |
| Outlook | Communication, escalation intake, stakeholder requirements | Daily | Email triage and information gathering |
| Teams / Slack | Stakeholder syncs, PE team communication, program-level alignment | Daily | Meeting-heavy; follow-up coordination |
| Power BI | Yield & Efficiency, FTA, CoQ dashboards (RM Lanes specific) | Not daily — situational | Dashboard review for RM Lanes program |

---

## 6. Stakeholder Network

| Stakeholder | What They Come For | Channel | Frequency |
|-------------|---------------------|---------|-----------|
| Project Manager (PM) | Deliverables, process improvements, requirements | Slack · Teams · Email | Daily |
| Program Manager | Requirements, challenges with proposed solutions | Slack · Teams · Email | Few times/week |
| PE Team (3 direct) | Deliverable updates, technical PE support | Slack · Teams · Email | Daily |
| Delivery / Development Team | Requirements, FNR deliverables, follow-up | Slack · Teams · Email | Weekly |
| Piotr Klusek | Daily operational follow-up (Kavita) | Teams call | Daily |
| QualityManagement group | PA follow-up, quality escalations (Kavita) | Teams · Email · Jira | Daily |
| Project Office | Activity follow-up, AIC tickets | Jira | As needed |

---

## 7. Issue Detection & Escalation

### How Issues Are Detected
1. Jira auto-notifications and manual ticket review
2. Emails and Teams messages from stakeholders
3. Manager or PM raising inputs during syncs
4. Team syncs — daily PE team check-in surfaces blocked items
5. Self-initiated monitoring — process health checks against PBI dashboards

### Severity Classification
| Severity | Criteria | Action |
|----------|----------|--------|
| Critical | Process has a major gap; key parameters ignored; not effective; quality concern; SLA not met; PM blocker | Immediate root cause investigation + corrective action |
| High | Quality concern; escalation received; SLA at risk | Escalate to manager after initial investigation |
| Monitor | Daily activity follow-up; items approaching deadline | Continue monitoring, send reminders |
| Low | Minor process deviation with no operational impact | Jira ticket, address in next sprint |

### Escalation Protocol
1. Get more details on the issue
2. Identify the root cause
3. Propose preventive or corrective action to avoid recurrence
4. Escalate to manager or PM if non-adherence persists after multiple follow-ups

**Escalate when:** Non-adherence after multiple reminders · SLA breach without recovery plan · escalation received from PM or leadership

**Escalation channels:** Conversation over chat or call (Karthikeyini) · Jira and Email (Kavita)

**Unofficial rule (Karthikeyini):** *"Reach out to all stakeholders instantly as you see the need — don't wait for escalation. Take up the role the situation demands instead of waiting for the assigned person."*

### Late-Catch Pattern
- Q1: RM Lanes challenges were overlooked and not escalated due to high demand vs PE team supply — not enough PE bandwidth to monitor deeply across all workstreams simultaneously
- Jira auto-notification is the only early warning mechanism currently in use (Kavita)

---

## 8. Pain Points & Friction

| Pain Point | Description | Cost |
|------------|-------------|------|
| **Jira status follow-up** | #1 pain for both interviewees — manually chasing ticket status across multiple stakeholders, multiple times per day. Kavita named this as most time-consuming, most automatable, AND most frustrating (all three pain categories). | Multiple hours/week |
| **Information seeking across stakeholders** | Challenges in production and pain areas require active follow-up to surface — information is not proactively shared | Unpredictable — delays process design decisions |
| **Scope change communication gaps** | Scope changes (e.g., RM Lanes) not cascaded clearly to all stakeholders; only discovered through persistent follow-up | Risk of process gaps going undetected |
| **Meeting overload** | Too many meetings leave insufficient time for individual process improvement and AI exploration work | Karthikeyini: day exceeds 9 hours regularly |
| **Limited PE team bandwidth** | High demand vs supply — small PE team (3 + 18 Pune) serving 500+ operational footprint means deep dives on individual programs are regularly sacrificed | Direct contributor to Q1 near-miss |
| **Documentation and learning deprioritised** | Kavita: documentation updates, team learning, informatory reading consistently displaced by follow-up work | Long-term capability risk |

---

## 9. AI Integration Points

### Top AI Use Cases (Direct from Interviews)

**Priority 1 — Daily To-Do Prioritisation with Suggested Actions (Karthikeyini + Kavita)**
- Auto-generate morning priority list from emails, Jira tickets, and Confluence page changes
- Suggest specific next actions for each item (not just surface — recommend what to do)
- *"Prioritize and suggest actions"* — Karthikeyini, morning automation #1
- *"My to do activity"* — Kavita, morning automation #1

**Priority 2 — Automated Jira Status Follow-Up (Kavita — named it 3 times)**
- Auto-monitor critical Jira tickets and PA activities for status staleness
- Send automated follow-up reminders to assignees when status not updated by deadline
- Alert manager when ticket is overdue and assignee unresponsive
- *"Status follow up on Jira ticket"* — most time-consuming, most automatable, most frustrating

**Priority 3 — SLA Follow-Up Automation (Kavita)**
- Monitor PA (Product Audit) SLAs and send automated reminders before breach
- Flag to manager/QTM when SLA approaching without status update
- *"SLA follow up"* — morning automation #2

**Priority 4 — Product Audit Status Auto-Report (Kavita)**
- Auto-generate PA status report for QTM team — current status, overdue items, at-risk items
- Eliminate manual compilation from Jira + Confluence
- *"Product Audit status assigned to QTM team"*

**Priority 5 — RM Lane Efficiency Weekly Report Auto-Generation (Karthikeyini)**
- Auto-pull Yield, FTA, CoQ, Efficiency data from Power BI for RM Lanes
- Generate formatted weekly report for OPS LT, MAPS LT, and contributors
- *"RM Lane efficiency weekly report, this is on its way to be completed"*

**Priority 6 — Stakeholder Follow-Up for Dependent Updates (Karthikeyini)**
- Track open dependencies across PE deliverables and auto-follow-up with responsible parties
- Surface which dependencies are blocking which PE deliverables
- *"Follow up dependent for updates"* — morning automation #2

**Priority 7 — PE Customer Satisfaction Early Warning (Karthikeyini)**
- Proactively surface signals of stakeholder dissatisfaction with PE service delivery
- *"PE customer satisfaction report"* — most valuable early warning

**Priority 8 — Process Health & Delivery Success Rate Recommendations (Karthikeyini)**
- AI recommends process health status and PE delivery success rate based on current data
- Surface areas where improvement actions are needed before they become escalations
- *"Process health, Process delivery success rate"* — comfortable for AI to recommend

---

## 10. AI Guardrails

### AI CAN — Automate, Recommend, Alert
- Generate morning priority list with suggested next actions from Jira + email + Confluence
- Send automated follow-up reminders for overdue Jira tickets and PA activities
- Flag SLA breach risk before the deadline is missed
- Auto-generate PA status report for QTM team from Jira + Confluence data
- Auto-generate RM Lanes weekly report from Power BI data
- Recommend which process health areas need attention based on metrics
- Alert on any Map Issue (IM) caused by Operations (target: 0)
- Track dependent deliverables and auto-notify responsible stakeholders
- Highlight team and stakeholder interaction areas needing improvement
- Recommend process delivery success rate signals from Jira and PBI data

### AI MUST NOT — Without Human Review
- Send any communication to stakeholders automatically — always BA/PE review first
- Reply to escalations on behalf of the PE manager
- Make final decisions on process design or corrective actions
- Approve or close AIC continual improvement tickets without PE manager sign-off
- Modify Confluence process documentation without explicit PE review
- Send status updates to OPS LT or leadership without manager approval

**Trust-building requirement (Karthikeyini):** *"Near to perfect from the content POV — it will grow as consistent completeness is achieved with each result generation."*

---

## 11. Prompt Templates

### Template 1: Morning Priority Briefing
```
You are my PE morning assistant for TomTom Maps Operations.

Review and prioritise:
1. Emails since yesterday: escalations, scope changes, new requirements — flag action vs FYI
2. Jira tickets: overdue or status-stale tickets (no update in 24+ hours) — list by criticality
3. Confluence pages: any PA or process status pages not updated since [date]
4. Workday: team leaves today and tomorrow — flag impact on delivery

Output: prioritised action list (1–2 lines per item), urgent at top.
Suggest a specific action for each item. Max 1 page.
```

### Template 2: Jira Ticket Status Alert
```
Scan all Jira tickets in [project/board] assigned to [team/person].

Flag:
1. Tickets not updated in 48+ hours — by assignee, priority, due date
2. PA (Product Audit) tickets approaching SLA breach
3. AIC continual improvement tickets overdue by sprint commitment
4. Blocked tickets with no blocker resolution activity

For each flagged ticket:
- Ticket ID and title
- Last update date
- Assignee
- Recommended follow-up action (auto-reminder / escalate to manager / request status call)

Output: structured table. Do not send reminders automatically — surface for PE review first.
```

### Template 3: Product Audit Status Report
```
Generate Product Audit (PA) status report for QTM team as of [date].

Pull from Jira + Confluence:
1. Total PA tickets: open / in progress / completed / overdue
2. SLA status per PA item: on track / at risk / breached
3. Items requiring immediate QTM attention (flag ⚠️)
4. Completed PAs this week — count and release reference

Format: table with RAG status per item. PE manager reviews before sending to QTM.
```

### Template 4: RM Lanes Weekly Report Draft
```
Generate RM Lanes weekly report for w/e [date].

Pull from Power BI:
- Yield: current vs baseline
- Efficiency: current vs baseline
- FTA (First Time Acceptance): current vs target
- CoQ (Cost of Quality): current vs target

For each metric:
1. Current value
2. Week-over-week trend (↑/↓/→)
3. RAG status
4. Any metric at risk — flag with recommended action

Append: initiatives update, challenges, risks from [Jira/Confluence source].
Format: structured slides draft for OPS LT / MAPS LT review.
```

### Template 5: Dependency Follow-Up Tracker
```
Track all open PE deliverables with external dependencies.

For each deliverable in [Jira/Confluence]:
1. Deliverable name and owner
2. Blocked by: [person / team / decision]
3. Last follow-up date and outcome
4. Days since last response from dependency owner
5. Risk to delivery timeline if unresolved

If dependency stale >3 days: draft a follow-up message for PE manager review.
Do not send automatically.
```

### Template 6: Process Health Summary
```
Generate a process health summary for [program/domain] as of [date].

Using data from Jira (ticket closure rate, SLA adherence), PBI (FTA, CoQ, efficiency):

1. Process delivery success rate: % of PE deliverables completed on time
2. Open process gaps: count by severity (critical / high / monitor)
3. Map Issues (IMs) caused by Operations this period: target = 0
4. Continual improvement (AIC) tickets: opened vs closed this quarter
5. Areas recommended for immediate PE attention

Output: 1-page summary for PE manager review before sharing with OPS LT.
```

---

## 12. Appendix: Metrics Quick Reference

| Metric | Domain | Target | Alert At | Source | Owner |
|--------|--------|--------|----------|--------|-------|
| Productivity Improvement | Cross-domain | — | Declining trend | Power BI | Karthikeyini Kanade |
| Map Issues caused by Operations | Quality | 0 | Any occurrence | — | Karthikeyini Kanade |
| Productivity Improvement (AI) | Cross-domain | — | Declining trend | — | Karthikeyini Kanade |
| Yield (RM Lanes) | RM Lanes | Baseline | Deviation from baseline | Power BI | Karthikeyini Kanade |
| FTA | RM Lanes | — | Declining trend | Power BI | Karthikeyini Kanade |
| CoQ | RM Lanes | — | Rising trend | Power BI | Karthikeyini Kanade |
| Product Audit (PA) | PE Team | Release-based | SLA not met | Manual / Jira | Kavita Vajpai |
| Quality | PE Team | 95% | Below 95% | PBI Reports | Kavita Vajpai |
| AIC Ticket SLA | PE Team | Per agreement | Overdue | Jira | Kavita Vajpai |

---

*Generated: August 2026 | Synthesised from 2 Process Engineering interviews | TomTom Maps Operations AI Co-Pilot Initiative*
