# Business Analyst — Skill Profile
## AI Co-Pilot Interview Analysis | TomTom Maps Operations | August 2026

**Synthesised from:** 2 interviews — Nitin Patil (OCC Reporting) · Madhura Athavale (Maps Operations)  
**Interview dates:** 11–13 August 2026  
**Interviewers:** Lalit Patkar · Pratish Deshpande

---

## 1. Role Identity

### What This Role Is
A Business Analyst in Maps Operations is the **data intelligence layer** between raw operational output and leadership decision-making. BAs do not just produce reports — they own KPI calculation logic, validate data accuracy across sources, maintain business-critical dashboards, and design automation solutions that reduce manual reporting overhead for operational teams.

### Role Levels Covered
| Role | Scope | Base |
|------|-------|------|
| Business Analyst (OCC Reporting) | LM · RM · Genesis workflows; company-wide efficiency dashboards | OCC Hyderabad |
| Business Analyst (Maps Operations) | OCC · RMSI · Noida · Hyderabad · GlobalLogic; cost of quality KPIs | Pune (team of 7) |

### What Only the BA Can Decide
- Correct reporting logic and KPI calculation methodology
- Data validation readiness — whether a report is accurate enough to share with stakeholders
- Metric interpretation when source data is ambiguous or conflicting
- Prioritisation of competing stakeholder reporting requests

---

## 2. Daily Operating Rhythm

### Morning Sequence (both interviewees)
| Step | Action | Tool | Time |
|------|--------|------|------|
| 1 | Review Teams messages, emails, Outlook calendar for meeting priorities and urgent requests | Teams · Outlook | 10–15 min |
| 2 | Check Jira board — DSM tickets for new requests, open blockers, sprint status | Jira | 10–15 min |
| 3 | Review critical dashboards and report health — identify refresh failures or data anomalies | Power BI · Databricks | 15–20 min |
| 4 | Manually validate data accuracy across impacted reports before stakeholder sharing | Excel · Power BI | 15–30 min |
| 5 | Prioritise the day based on stakeholder urgency, ticket criticality, and delivery deadlines | — | 5–10 min |

**Total morning data-gathering: 45–90 minutes before the first stakeholder insight can be delivered**

### Reactive vs Proactive Split
| Person | Proactive | Reactive |
|--------|-----------|----------|
| Nitin Patil | 60% | 40% |
| Madhura Athavale | 50% | 50% |

---

## 3. Metrics Monitored

### Universal (Both BAs)
| Metric | Target | Alert At | Source |
|--------|--------|----------|--------|
| Manual Efficiency | — | Deviation from trend | Power BI |
| QC after QC | 97% | 95% | Power BI |
| One ACI | 98% | 96% | Power BI |

### Madhura Athavale — Cost of Quality Portfolio
| Metric | Target | Alert At | Source |
|--------|--------|----------|--------|
| Cost of Quality — Genesis | 6% | 8% | Power BI |
| Cost of Quality — LM | 7% | 9% | Power BI |
| Cost of Quality — RM | 9% | 11% | Power BI |
| Cost of Production Waste | — | Sudden trend change | Multiple Power BI |

### Nitin Patil — Efficiency & Quality Portfolio
| Metric | Target | Alert At | Source |
|--------|--------|----------|--------|
| User Efficiency | Benchmark | Below benchmark | Power BI |
| Top Performer Index | — | Drop vs. prior period | Power BI |
| Quality Effectiveness | — | Declining trend | Power BI |
| Operational Waste | — | Upward trend | Power BI |

---

## 4. Reporting Portfolio

### Weekly Reports
| Report | Owner | Recipients | Cadence |
|--------|-------|------------|---------|
| Manual Efficiency | Nitin | Ops Teams, Management | Weekly |
| User Efficiency | Nitin | Team Leads, Management | Weekly |
| Top Performer | Nitin | Ops Teams, Leadership | Weekly |
| Quality Effectiveness | Nitin | Ops, Management | Weekly |
| Weekly Ops | Nitin | Ops Teams, PMs, Leadership | Weekly |
| Operational Waste | Nitin | Ops Teams, Management | Weekly |
| Release Notes | Nitin | Cross-functional stakeholders | Weekly |
| Waste Analysis (Async Wait Time) | Madhura | PM · QTM · Project Leads | Weekly |

### Monthly / Quarterly Reports
| Report | Owner | Recipients | Cadence |
|--------|-------|------------|---------|
| Cost of Quality (Genesis/LM/RM) | Madhura | Leadership | Monthly |
| ACI Tracking | Madhura | Operations, PM | Monthly |
| OM/IM Deliverable Closure | Madhura | PM, Ops | Monthly |
| DPIP/EFFIMP/PRS Metrics Review | Madhura | Ops Teams | Monthly |
| OCC Monthly PPT Review | Madhura | Leadership | Monthly |
| KPI Performance Trend Analysis | Nitin | Leadership | Quarterly |

---

## 5. Tools & Data Stack

| Tool | Used For | Frequency | Manual Effort |
|------|----------|-----------|---------------|
| Power BI | All KPI dashboards, report maintenance, stakeholder views | Daily | Report monitoring, data validation |
| Databricks | Source data for Power BI; efficiency and quality data pipelines | Daily | Query validation |
| Jira | Ticket management, sprint tracking, requirement intake, DSM tickets | Daily | Status tracking, triaging |
| Excel | Supplementary data, cross-validation, ad hoc analysis | Daily | Manual cross-referencing |
| Teams / Outlook | Communication, escalation, stakeholder alignment | Daily | Triage, meeting prep |

---

## 6. Stakeholder Network

| Stakeholder | What They Come For | Channel | Frequency |
|-------------|---------------------|---------|-----------|
| Project Managers | KPI performance data, delivery trends, capacity inputs | Teams · Jira | As needed |
| Operational Leads | Productivity analytics, efficiency data, operational KPIs | Teams · PBI | As needed |
| Leadership | Strategic KPI reports, trend analysis, monthly/quarterly reviews | Reports · PPT | Monthly/Quarterly |
| QTM / Project Leads | Waste analysis, quality trends, metric status | Teams · Jira | Weekly |
| OCC Reporting Team | Jira ticket status, sprint alignment | Sprint meetings · Jira | Few times/week |
| Vrushali Kashikar | Report accuracy, waste analysis review | Team meetings · Email | Weekly |

---

## 7. Issue Detection & Escalation

### How Issues Are Detected
1. Automated Power BI report monitoring — refresh failures or anomaly flags
2. Stakeholder escalations via Teams or Jira tickets
3. Manual data validation — inconsistencies between source and dashboard output
4. Operational review meetings — KPI anomalies surface during discussions
5. Self-initiated data review — proactive spot checks

### Severity Classification
| Severity | Criteria | Action |
|----------|----------|--------|
| Critical | Reporting accuracy impacting business decisions, SLA commitments, or monthly/weekly reviews | Immediate fix + manager notification |
| High | Metric discrepancy with workaround available | Investigate independently, monitor closely |
| Medium | Minor deviation or data gap | Track, flag in next reporting cycle |
| Low | UI or formatting issue | Backlog via Jira ticket |

### Escalation Protocol
1. Detect issue (monitoring / Jira ticket / self-review)
2. Assess business impact
3. Validate data and identify root cause
4. Coordinate with data owners and stakeholders
5. Implement fix and verify results
6. Communicate closure to affected stakeholders

**Escalate to manager when:** High business impact · cross-team dependencies · risk to delivery timelines · KPI metric reporting at risk

**Escalation message includes:** Issue description · business impact · root cause (if known) · mitigation plan · required support · expected resolution timeline

### Late-Catch Warning Signs
- Unusual KPI trends diverging from historical pattern
- Stakeholder-reported discrepancies not yet visible in dashboards
- Inconsistencies between source data and dashboard output
- Proactive stakeholder communication expected even before formal escalation

---

## 8. Pain Points & Friction

| Pain Point | Description | Cost |
|------------|-------------|------|
| Manual data validation | Cross-checking report data across multiple sources before every stakeholder share | 15–30 min per report cycle |
| Data reconciliation across systems | Different data structures in Genesis, Orbis, LM, RM require manual mapping | Recurring — hours per week |
| No unified real-time operational view | No single source of truth across LM, RM, Genesis, Orbis without manual integration | High — prevents proactive detection |
| QC after QC reporting | Manual validation and weekly reporting cycle for QC accuracy data | Weekly recurring effort |
| Requirement clarification delays | Access to source data and cross-team inputs takes longest when multiple stakeholders involved | Unpredictable — blocks delivery |
| Reporting discrepancies detected late | Inconsistencies persist longer than expected before identified and corrected | Risk to stakeholder trust |

---

## 9. AI Integration Points

### Top AI Use Cases (Direct from Interviews)

**Priority 1 — Automated Data Validation (Nitin Patil)**
- Auto-validate all reports against trusted Databricks/Power BI source data before sharing
- Flag discrepancies immediately rather than relying on manual spot checks
- *"Automatically validate data"* — morning automation ask #1

**Priority 2 — Weekly Ops & Operational Waste Auto-Generation (Nitin Patil)**
- Auto-generate Weekly Ops and Operational Waste reports with data already validated
- Remove the manual assembly and cross-check step entirely
- *"The Weekly Ops and Operational Waste reports — fully validated"*

**Priority 3 — Daily To-Do & Sprint Status Briefing (Madhura Athavale)**
- Morning: auto-generate today's priority list from Jira board, email, Teams
- Include quick sprint status — tickets completed, remaining, at-risk items
- *"My daily To-Do activities" + "Quick status on Current Sprint"*

**Priority 4 — Waste Trend Alert (Madhura Athavale)**
- Email/Teams alert when weekly waste report shows sudden upward or downward trend
- Threshold-based: alert only when deviation exceeds configured band
- *"Flag out or sent email alert on weekly waste report if the weekly trend shows sudden down or up trend"*

**Priority 5 — Early Warning: Data Quality Issues (Nitin Patil)**
- Detect data quality anomalies before reports are generated
- Flag source data problems at pipeline level (Databricks) before they surface in Power BI
- *"Early detection of data quality issues"*

**Priority 6 — Root Cause Hypothesis Generation (Nitin Patil)**
- When a KPI drops or anomaly is flagged, AI recommends root-cause hypotheses
- BA reviews and confirms before any action or communication
- *"AI recommending root-cause hypotheses, report insights, prioritization suggestions"*

### Additional High-Value Automation Points
- Sprint ticket assignment — allocate DSM tickets within sprint based on workload and categorisation
- Monthly OCC PPT auto-generation — pull OCC metrics from Power BI, generate structured slide deck
- ACI tracking auto-report — pull One ACI data, flag items approaching 96% threshold
- Cost of Quality monthly report — aggregate Genesis/LM/RM CoQ data, generate report draft for review

---

## 10. AI Guardrails

### AI CAN — Automate, Recommend, Alert
- Validate report data against Databricks source and flag discrepancies before publishing
- Auto-generate report drafts (Weekly Ops, Operational Waste, Monthly OCC PPT)
- Alert on KPI threshold breaches (CoQ, ACI, QC after QC, Waste trend)
- Recommend root-cause hypotheses when metrics drop unexpectedly
- Summarise Jira sprint status and open ticket priorities
- Generate daily To-Do list from Jira + Teams + calendar inputs
- Alert on waste trend anomalies before reports are published to stakeholders
- Recommend sprint ticket assignments based on workload and categorisation

### AI MUST NOT — Without Human Review
- Publish any report change to stakeholders automatically
- Approve business-critical decisions or KPI methodology changes
- Communicate stakeholder-impacting updates without BA review and approval
- Make autonomous conclusions from metric analysis
- Change KPI calculation logic without explicit BA sign-off
- Assign Jira tickets or close items without BA confirmation

**Trust-building requirement (Nitin Patil):** *"Consistently accurate, explainable, validated against trusted data sources, and have a proven track record of reliability over time."*

---

## 11. Prompt Templates

### Template 1: Morning Briefing
```
You are my BA morning assistant for TomTom Maps Operations.

Review and summarise:
1. New Jira tickets opened since yesterday (DSM board): title, priority, requester
2. Teams/email messages requiring action: flagged vs FYI
3. Power BI dashboard health: any report refresh failures or anomaly flags
4. Sprint status: tickets completed vs planned, remaining effort, blockers

Output format: bullet list by category, urgent items at top. Max 1 page.
```

### Template 2: Data Validation Check
```
Validate the [report name] dataset against Databricks source before publishing.

Check:
1. Row counts match between source and Power BI staging layer
2. Key metrics ([metric 1], [metric 2]) match within [tolerance]%
3. Date range is complete — no missing weeks
4. No null values in mandatory fields ([field list])

Output: PASS / FAIL with specific discrepancies listed. Do not publish if FAIL.
```

### Template 3: Weekly Ops Report Draft
```
Generate Weekly Ops report for w/e [date].

Data sources:
- Manual Efficiency: [Databricks table]
- User Efficiency: [Databricks table]
- Quality Effectiveness: [PBI source]

Include:
1. Week-over-week trend (↑/↓/→) for each KPI
2. Top 3 performers by efficiency
3. Any metric below threshold (flag with ⚠️)
4. No narrative — data and trend indicators only

Format: structured table, validated, ready for stakeholder sharing.
```

### Template 4: Cost of Quality Monthly Report
```
Generate Cost of Quality monthly report for [month].

Pull from Power BI:
- CoQ Genesis: target 6%, alert 8%
- CoQ LM: target 7%, alert 9%
- CoQ RM: target 9%, alert 11%

For each domain:
1. Current month actual vs target
2. Month-over-month trend
3. RAG status (Green / Amber / Red)
4. Flag if alert threshold exceeded

Output: structured table + 2-sentence summary per domain for PM review.
```

### Template 5: Waste Trend Alert Check
```
Run weekly waste trend check for w/e [date].

Pull Async Wait Time waste data from [source].

Compare:
- Current week vs prior 4-week average
- Flag if deviation exceeds [X]% up or down

If threshold exceeded, generate Teams/email alert with:
- Current value vs average
- Direction of change and affected scope
- Recommended next step for BA review (not for automatic action)
```

### Template 6: Anomaly Root Cause Analysis
```
Analytics flagged an anomaly: [metric] [dropped/spiked] by [X]% in week [n].

Investigate using available data:
1. What changed that week? (staffing, data volume, source data quality, system changes)
2. Was the same pattern seen in prior periods / same seasonal window?
3. Did other related metrics move in the same direction?
4. Is this a one-time event or the start of a trend?

Output: 3–5 root cause hypotheses ranked by likelihood.
BA will confirm before any action or stakeholder communication.
```

---

## 12. Appendix: Metrics Quick Reference

| Metric | Domain | Target | Alert At | Source | Owner |
|--------|--------|--------|----------|--------|-------|
| Manual Efficiency | Cross-domain | — | Trend deviation | Power BI | Nitin Patil |
| User Efficiency | Cross-domain | Benchmark | Below benchmark | Power BI | Nitin Patil |
| Top Performer Index | Cross-domain | — | Drop vs prior | Power BI | Nitin Patil |
| Quality Effectiveness | Cross-domain | — | Declining trend | Power BI | Nitin Patil |
| Operational Waste | Cross-domain | — | Upward trend | Power BI | Nitin Patil |
| QC after QC | OCC | 97% | 95% | Power BI | Madhura Athavale |
| One ACI | OCC | 98% | 96% | Power BI | Madhura Athavale |
| CoQ — Genesis | Genesis | 6% | 8% | Power BI | Madhura Athavale |
| CoQ — LM | LM | 7% | 9% | Power BI | Madhura Athavale |
| CoQ — RM | RM | 9% | 11% | Power BI | Madhura Athavale |
| Cost of Production Waste | Cross-domain | — | Sudden trend change | Multiple PBI | Madhura Athavale |

---

*Generated: August 2026 | Synthesised from 2 BA interviews | TomTom Maps Operations AI Co-Pilot Initiative*
