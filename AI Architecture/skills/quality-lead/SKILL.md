# Quality Lead / Quality Manager — AI Native Skill Profile
**Domain:** TomTom Maps Operations  
**Roles Covered:** Quality Lead, Quality Manager, Manager I (Geospatial Data Operations)  
**Source:** Synthesized from AI Co-Pilot interviews with Devika Shetty, Dhammaratna Dange, Joanna Pisiałek, Shital Tambe — July–August 2026  
**Version:** 2.0

---

## 1. Role Overview

A Quality Lead or Quality Manager in Maps Operations owns the quality of geospatial data delivery end-to-end. This role spans monitoring quality metrics, driving root cause analysis, managing team performance, coordinating with project managers and engineering, and ensuring delivery commitments are met without compromising quality standards.

### What this role is actually about

Most people outside this role think it is about tracking numbers and preparing reports. In reality, it is about:

- **Making judgment calls** when data shows multiple possible interpretations
- **Connecting the dots** across teams, workflows, systems, and time periods to surface risks early
- **Protecting customer commitments** by identifying and resolving quality and delivery risks before they escalate
- **Coaching teams and leads** to build sustainable quality performance — not just fixing today's problem
- **Translating data into action** — knowing which metrics matter most, which trends require escalation, and which can be monitored

### Team scale (typical ranges from interviews)
- Quality Managers: 30–75 team members, including production operators, quality operators, and team leads
- Quality Leads: 12–15 direct/indirect team members, focused on specific workflows or process types
- Coverage: Multiple workflows simultaneously (e.g., LM, RM, Genesis, Geocoding, Safety Cameras, ADAS)

### What a great month looks like
- All customer commitments and delivery targets met
- Key quality KPIs (FTA, COQ, COPQ, QC TAT, QC after QC) show positive or stable trends
- QC backlog aging remains under control with no SLA breaches
- RCA/CAPA actions closed on time and showing measurable improvement
- At least one automation or process improvement initiative showing measurable impact
- Team is engaged, leads are performing, and no unresolved escalations remain open
- Stakeholders have confidence in the team's performance and communication

---

## 2. Daily Operating Rhythm

### Morning Start Sequence (first 30–45 minutes)

Every day begins with a structured review before taking any action. The sequence is:

**Step 1 — Communications triage**
- Check Microsoft Teams and Outlook for urgent escalations, leave requests, or overnight stakeholder messages
- Identify any messages that require same-day response or immediate decision
- Flag critical emails that need a reply before stand-up

**Step 2 — Metrics check (operational health)**
- Open Databricks / Power BI dashboards
- Review overnight / previous day's data for:
  - QC TAT (P90 target: ≤24 hrs — alert if crossed)
  - COQ (target: ≤5% — alert if rising trend or exceeds threshold)
  - FTA per project / process type (target: ≥95%–100% depending on workflow)
  - QC after QC FTA (target: ≥97% H1, ≥98% H2)
  - QC backlog by aging bucket (flag anything approaching or past SLA)
  - Inflow vs outflow of QC tasks (detect backlog buildup early)
  - User-level efficiency: daily time spent, productive vs. non-productive hours (target >85% productive)

**Step 3 — Jira review**
- Open Jira boards filtered to Quality and Operations tickets
- Identify newly raised tickets, overdue actions, unresolved blockers, and RCA/CAPA tickets past their due date
- Check BED (Batch End Date) automation alerts for quality issues flagged before batch closure
- Review MCPRCA monitoring: flag any RCAs past SLA (target: 70% closed per SLA)

**Step 4 — Team availability**
- Check attendance, planned leaves, and shift coverage (via Workday or attendance trackers)
- Identify resource gaps and adjust QC workload allocation accordingly
- Decide if any temporary production users need to support QC — and assess their readiness profile

**Step 5 — Priority setting**
- Based on the above, identify the top 3–5 items requiring attention today
- Distinguish: "immediate action required" vs. "monitor and check tomorrow"
- Align with leads in morning stand-up or via Teams message

### Throughout the Day — Judgment Calls Made Daily

These are the decisions that require experience and cannot be delegated or automated without oversight:

| Decision | Context |
|---|---|
| Work prioritization | Which workflows/tasks take priority when resources are limited (SLA risk, customer impact, backlog severity) |
| Resource allocation | Who works on which QC tasks based on expertise, quality history, and current capacity |
| Issue escalation trigger | When an issue can be handled within the team vs. when PM or manager visibility is required |
| Immediate action vs. watch-and-wait | Whether a metric deviation is a one-off fluctuation or a trend requiring corrective action |
| RCA prioritization | Which quality issues get a full root cause investigation vs. which get a quick fix and monitoring |
| QC staffing for temp users | Whether a production operator is ready to work QC independently or needs supervision |
| Threshold exception approval | When circumstances justify a temporary deviation from standard quality thresholds |

### What triggers immediate action (do not wait)
- FTA drops below project PQR target across multiple users or for more than 2 consecutive days
- QC TAT P90 crosses 24 hours
- COQ rises above 5% or shows rapid upward trend
- QC backlog aging exceeds SLA thresholds
- Customer commitment at risk due to production or quality bottleneck
- Major spike in invalid QC rejections
- TQA or QC-after-QC results show systemic quality gaps
- Unplanned resource loss affecting delivery capacity
- Critical Jira escalation from PM or stakeholder

### What can be watched and monitored (do not over-react)
- Minor daily fluctuations in productivity within normal range
- Isolated single-user quality issues not showing a recurring pattern
- Short-term backlog fluctuations expected to recover without SLA impact
- QC TAT slightly above trend but not crossing 24-hour threshold
- One-off low FTA on a specific complex work type not seen before

### Crisis day triggers
- Multiple high-impact issues occurring simultaneously
- Customer delivery commitment at immediate risk
- Tool outage or workflow disruption affecting multiple teams
- Sudden unplanned absence of multiple leads or key team members
- Major quality finding in TQA / QC-after-QC affecting multiple process types
- Stakeholder or leadership escalation requiring immediate response and status

---

## 3. Weekly Activities & Cadence

### Every Week — Non-Negotiable

| Activity | Purpose | Output |
|---|---|---|
| FTA performance review with leads | Identify misses, understand root causes, agree corrective actions | Action plans per work unit |
| Quality KPI review | COQ, COPQ, QC effectiveness, error trends, recurring defect patterns | Exception list with actions |
| QC aging / TAT review | Identify backlog accumulation and SLA risk areas | Prioritization adjustments |
| TQA / QC-after-QC review | Assess quality gate performance, systemic gaps, recurring findings | Corrective actions or coaching needs |
| Jira ticket review | Track quality issues, RCA/CAPA progress, automation requests, operational blockers | Updated ticket statuses |
| RCA/CAPA progress review | Ensure actions are on track and delivering measurable impact | Closed actions or escalation flags |
| Customer commitment review | Verify delivery milestones are on track, identify risks early | Risk register updates |
| OKR progress check | Track automation, AI adoption, quality improvement initiative progress | Updated OKR status |
| Plan vs. Actual review | Compare planned vs. delivered output, quality, and productivity | Recovery actions where needed |
| Team performance check | Review productivity, efficiency, quality output, and aging by work unit | Coaching plans or workload adjustments |
| Workload planning with leads | Balance capacity across workflows for the coming week | Weekly allocation plan |
| Confluence update (relevant pages) | Keep operational and quality status pages current | Updated pages for stakeholders |

### Weekly Reports Produced

| Report | Recipients | Key Content |
|---|---|---|
| Project FTA report | Manager, PM, quality stakeholders | FTA by project/process type, misses, root causes, action plans |
| QC effectiveness / COQ summary | Quality governance, manager | COQ, COPQ, QC effectiveness trends, error patterns |
| QC aging and TAT report | Manager, leads, PM | Backlog distribution, aging buckets, SLA risk areas |
| TQA / QC-after-QC weekly scores | PM, quality governance | Quality gate performance, findings, trends |
| Customer commitment status | PM, stakeholders | Delivery milestone status, risks, dependencies |
| Jira tracking summary | Leads, PM, engineering | Open tickets, overdue actions, escalations |
| Geocoding / workflow quality metrics | Project Managers (per project) | FTA, QC volumes, rejection trends, key observations |
| Work unit performance summary | Manager, team leads | Productivity, quality, efficiency, aging by OCC/DPU/partner |

### Recurring Meetings

| Meeting | Frequency | Role | Focus |
|---|---|---|---|
| Geocoding QC Status / Progress & Challenges | Daily | Host / Decision Maker | Daily closure status, blockers, escalations |
| LM Basemap Daily Meeting | Daily | Presenter, Reviewer | Delivery progress, priorities, blockers, quality topics |
| Quality Lead Connects | Weekly | Lead / Decision Maker | Quality performance, risks, error trends, improvement actions |
| Plan vs. Actual Review | Weekly | Decision Maker | Variance analysis, recovery actions |
| QC Progress & Challenges (with SPOCs) | Tue/Thu | Reviewer / Decision Maker | QC performance, challenges, backlog, resource requirements |
| TQA / QC-after-QC Weekly Review | Weekly | Reviewer / Decision Maker | Quality gate scores, recurring findings, systemic gaps |
| Project-Specific Status / Sprint Meetings | Multiple/week | Participant, Reviewer | Delivery commitments, dependencies, risks, milestones |
| QC Effectiveness Program (OCC) | Weekly | Decision Maker | QC effectiveness metrics, improvement actions |
| OKR Initiative Review | Bi-weekly | Driver / Participant | Automation, AI adoption, workflow improvements progress |
| Weekly Team Sync | Weekly | Host | Team alignment, priorities, challenges |
| Operation Lead Sync | Tue/Thu | Participant | Cross-lead alignment |
| 1:1 with Team Leads | Weekly | Reviewer / Decision Maker | Performance, delivery, capacity, risks, coaching |
| Pre-Production Alignment | Weekly | Participant | Upcoming work, delivery readiness, resource requirements |
| AI Champion Meeting | Weekly | Participant | AI adoption, automation use cases, best practices |
| Weekly Leadership Meeting | Weekly | Participant | Business priorities, organizational performance, strategic updates |
| Weekly SPOC Call | Weekly | Participant | Operational actions across teams |
| RM QC Lead Sync | Weekly | Participant | QC progress across RM workflows |

---

## 4. Monthly & Quarterly Activities

### Month-End Activities

| Activity | Output | Recipients |
|---|---|---|
| Monthly Quality Metrics Report (per project) | FTA, QC volumes, rejection trends, insights, key observations | Project Managers (per project) |
| Confluence Process Review page update | Operational performance, achievements, quality trends, risks, improvement initiatives | Director, manager |
| KPI review slide preparation | All quality KPIs vs targets, trend charts, H1/H2 performance | Management, leadership |
| 1:1 with team members on performance | Individual performance feedback, development actions, goal alignment | Each team member |
| Monthly COQ review | Detailed breakdown of COQ calculation, reasons, trend analysis | PM, quality governance |
| Resource utilization review | Plan vs. actual allocation, utilization rates, upcoming capacity gaps | Manager, leads |
| RCA/CAPA effectiveness assessment | Are closed actions preventing recurrence? | Manager, quality governance |
| OAI (Observation and Action Item) closure review | All OAI items closed within 7-day SLA; escalate overdue items | Leads, manager |
| Monthly assessment completion tracking | Ensure ≥90% of team completed project assessments | Manager, training team |
| Lessons learned repository update | 3+ lessons learned per quarter; check for recurring lessons | Leads, Confluence |
| Gemba observation tracking | At least 1 Gemba per process per month; measurable outcomes documented | Manager, team |
| Actuals vs. planning hours check | WTC vs. workflow hours deviation; productive/non-productive split | Manager, finance |

### Quarter-End Activities

| Activity | Purpose |
|---|---|
| Quarterly performance trend analysis | Identify systemic improvements, recurring issues, long-term risks |
| OKR quarterly review | Assess progress against objectives, adjust targets if needed |
| Quality target review and reset | Review FTA, COQ, COPQ, QC TAT targets for next half-year with QTM and PMs |
| Process improvement initiative retrospective | Measure delivered efficiency gains from automation and process changes |
| Team development plan review | Update coaching plans, identify training needs, succession planning |
| External review preparation | Prepare for quarterly operating reviews or customer quality reviews |
| CMT compliance check | Ensure all users have completed mandatory CMT requirements for each project |

---

## 5. Key Metrics & Thresholds

### Core Quality Metrics

| Metric | Target | Alert Threshold | Source | Notes |
|---|---|---|---|---|
| **FTA (First Time Acceptance)** | Project PQR (typically ≥95%–100%) | Below PQR target | Databricks | Primary quality indicator; varies by project/workflow |
| **QC after QC FTA** | ≥97% (H1), ≥98% (H2) | Below target | Excel / PBI | Key second quality gate indicator |
| **COQ (Cost of Quality)** | Within KPI target | Rising trend or above threshold | Databricks | Alert when exceeds 5% or shows sharp upward trend |
| **COPQ (Cost of Poor Quality)** | <1% | Above threshold or increasing trend | Databricks | Subset of COQ; indicates poor quality cost impact |
| **QC TAT P90** | ≤24 hrs | Crossing 24 hrs | Databricks | 90th percentile of QC turnaround time |
| **TQA Score** | Meet PQR target | Below target threshold | Databricks | Third Quality Assurance scores per work unit |
| **QC Effectiveness** | Monitored via control chart | Up/down spikes | Databricks | Measure via control chart; trend matters more than single point |
| **Invalid Rejections by QCA** | Minimal | Increasing pattern | Databricks | Track to identify QCA training needs |
| **Repeated Errors in Orbit** | Minimal recurrence | Recurring or increasing pattern | Databricks | Recurring errors = systemic issue; trigger RCA |
| **CRD Rework / Re-QC** | Closed E2E within 24 hrs | Crossing 24 hrs | Databricks | Track rework closure time |
| **QC Inflow vs. Outflow** | Daily monitoring | Backlog growing | Databricks | Early warning for backlog accumulation |
| **QC Actual vs. Proposed Sampling** | Optimal sampling <15% | Significant deviation | Databricks | Flag when deviation from optimal sampling is significant |

### Operational Efficiency Metrics

| Metric | Target | Alert Threshold | Source |
|---|---|---|---|
| **Productive vs. Non-Productive Hours** | >85% productive | Below 85% benchmark | Databricks |
| **Resource Utilization (Plan vs. Actual)** | ±1% | Under/over utilization | Databricks |
| **Quality User Efficiency** | 10% improvement by EOY | Spike or downtrend | Databricks |
| **Production Efficiency** | Meeting production target | Spike or downtrend | Databricks |
| **On-Time Delivery** | 100% | <95% | Jira |
| **Deliverables Completion** | 100% plan adherence | Missed milestones | Jira |

### Process & Governance Metrics

| Metric | Target | Alert Threshold | Source |
|---|---|---|---|
| **MCPRCA Monitoring** | 70% RCA closed per SLA | Overdue or repeated incidents | Jira / PBI |
| **OAI Closure** | Within 7 days | Crossing 7-day SLA | Jira |
| **PRS converted to acceptable ideas** | >50% acceptance rate | Downtrend in acceptance | Jira |
| **Lessons Learned** | 3 per quarter | Recurrence of known issues | Jira / Confluence |
| **Gemba & Measurable Actions** | 1 Gemba per process per month | Missed Gemba or no measurable outcome | Jira / Excel |
| **Project Monthly Assessment** | ≥90% team attempting | Below target rating | HowNow / PBI |
| **User Onboarding (Quality & Production)** | 100% onboarded | Any deviation | PBI / Email |
| **CMT Compliance** | All users aligned with CMT mandate | Knowledge gap in user CMT scores | CMT tool |
| **Deep Checks (OFI reduction)** | Reduce OFI QoQ | Recurring issues | Excel / PBI / Jira |

### Metric Rules of Thumb (from interviews)

- A **trend** matters more than a single data point — never act on one day's deviation alone
- **FTA, COQ, COPQ, QC TAT, and TQA** are the four metrics that drive the highest management attention
- When **FTA declines + aging grows + COQ rises simultaneously**, it's a systemic issue requiring urgent cross-team RCA, not just individual coaching
- **QC effectiveness control chart**: both up spikes (too strict) and down spikes (too lenient) are signals
- **Not all metrics carry equal weight** — customer-impacting metrics (FTA, delivery) always take priority over internal efficiency metrics
- **COQ calculation differs** between KPI dashboard (against all realized hours) and PBI (against production hours) — always clarify which basis is being used

---

## 6. Data Sources & Tools

### Tool Usage Map

| Tool | Primary Use | Frequency | Manual Effort Today |
|---|---|---|---|
| **Databricks / Power BI (PBI)** | All quality and operational metrics: FTA, COQ, QC TAT, QC effectiveness, user efficiency, productivity | Multiple times/day | Download data → analyze in Excel or run Copilot agents |
| **Jira** | Deliverables tracking, RCA/CAPA tickets, escalation tickets, improvement initiatives, BED automation | Daily | Manual comments per ticket, checking updates, no auto-consolidation |
| **Confluence** | Quality tracker, process documentation, SOPs, monthly process review pages, lessons learned | Daily | Manual updates required; no auto-population from Databricks |
| **Microsoft Excel** | Consolidating metrics, LM QC-after-QC compilation, TQA results, user performance view, planning hours | Daily | Manual download + format from PBI; compile multiple sources |
| **Workday** | Leave management, team availability, attendance, expense approvals | Daily | — |
| **SharePoint** | Document storage, shared files | Multiple times/day | — |
| **Orbis Management Console** | Task management, adding planning IDs | Daily | Manual: adding planning IDs when missing |
| **CMT Tool** | Competency management, training tracking | Per project cycle | — |
| **HowNow** | Assessment completion tracking | Monthly | — |
| **Microsoft Teams / Outlook** | Stakeholder communication, escalations, meeting coordination | Multiple times/day | Email triage is manual; important mails can be missed |
| **Vertex (AI)** | Situational analysis, ad-hoc reasoning | Few times/week | — |

### Biggest Data Gaps Identified (from interviews)

1. **No single unified user performance dashboard** — FTA, efficiency, innovation ideas, LinkedIn learning progress, user delta, project delta, leaves, WTC vs workflow hours deviation, daily time spent, daily efficiency, invalid rejections, deep check findings, assessment completion are all in different places
2. **No predictive / forward-looking health indicator** — current dashboards show what happened, not what is about to happen
3. **No cross-team dependency visibility** — delays in one team's work affect downstream QC but this is not surfaced automatically
4. **COQ/COPQ split not consistent** — PBI shows COQ against production hours, KPI dashboard against all realized hours; needs reconciliation view
5. **QC staffing readiness not quantified** — no system to quickly assess if a temp production user is ready for QC based on history
6. **RCA/CAPA effectiveness not measured** — closure is tracked but not whether the action actually prevented recurrence

---

## 7. Issue Detection & Escalation

### How Issues Surface
1. Databricks / PBI dashboard anomalies (most common for metric-based issues)
2. Jira BED automation alerts (before batch end dates)
3. TQA / QC-after-QC / Product Audit findings
4. Direct team or stakeholder communication (Teams, email, meetings)
5. Manual data analysis revealing trends
6. Escalations from project managers or leadership

### Standard Response Process

```
Step 1: Validate — confirm the issue with data; don't act on a single unverified data point
Step 2: Assess impact — customer commitment? SLA risk? Quality risk? How many workflows affected?
Step 3: Root cause analysis — data issue, process issue, tooling issue, training issue, or resource issue?
Step 4: Immediate corrective action — reallocate work, resolve blocker, or escalate
Step 5: Communication — inform relevant stakeholders with: issue, impact, root cause, actions taken, recovery plan
Step 6: Monitor — verify the action resolved the issue; check for recurrence in next 2–3 data cycles
Step 7: Document — capture RCA, CAPA, and lessons learned in Jira/Confluence; update SOPs if needed
```

### Severity Classification

| Severity | Definition | Response |
|---|---|---|
| **Critical** | Customer commitment at risk; FTA below PQR; QC TAT >24hrs P90; COQ spike; major TQA/audit finding; tool outage affecting multiple workflows | Immediate action; same-hour stakeholder communication; cross-team coordination |
| **High** | Recurring quality issues showing trend; aging backlog approaching SLA; declining efficiency across multiple users; MCPRCA overdue | Action within same day; leads involved; recovery plan shared with PM |
| **Medium** | Isolated FTA miss not showing trend; single-user quality concern; OAI approaching 7-day SLA | Monitor for recurrence; coaching conversation with user; watch-and-wait with defined checkpoint |
| **Low** | Minor productivity fluctuation within normal range; isolated non-critical ticket aging; one-off deviation below threshold | Log and monitor; revisit in next weekly review |

### Escalation Decision Framework

**Handle within the team when:**
- Issue can be resolved through resource reallocation, coaching, or operational coordination
- Impact is local to one workflow or user, not spreading
- Recovery is achievable without additional capacity or stakeholder decisions

**Escalate to Manager or PM when:**
- Customer delivery commitment is at risk
- Issue requires cross-functional support or decisions beyond operational scope
- Production blockers or tool failures cannot be resolved by the team
- Quality concerns are systemic and require governance-level intervention
- Additional resources or priority changes are needed
- Resource constraints cannot be self-resolved

**Escalation communication format:**
```
ISSUE: [what happened, with specific metric data]
IMPACT: [what is at risk — customer, SLA, quality, delivery]
ROOT CAUSE: [initial assessment — data/process/tool/resource]
ACTIONS TAKEN: [what has already been done]
RECOVERY PLAN: [what will be done, by when, by whom]
SUPPORT NEEDED: [what decision or intervention is required from the escalation recipient]
```

### Known Late-Catch Warning Signs (from interviews)

These patterns have caused issues to be caught later than ideal in the past:
- **Declining FTA across multiple days** — often dismissed as a fluctuation before being recognized as a trend
- **Backlog aging creeping up slowly** — gradual growth is less visible than sudden spikes
- **Recurring errors in QC-after-QC** — often linked to temp production users switching to QC who lack sufficient quality background
- **COQ rising while FTA appears stable** — COQ can reflect rework that doesn't show in FTA until later
- **Multiple weak signals arriving simultaneously** — e.g., aging + FTA decline + COQ rise appearing as isolated issues in separate dashboards instead of one unified pattern

---

## 8. Stakeholder Communication Map

| Stakeholder | Topics Discussed | Frequency | Channel |
|---|---|---|---|
| **Team Leads (Production & Quality)** | Daily performance, backlog, aging, FTA trends, resource allocation, action plans, escalations | Daily | Teams, calls, stand-ups |
| **Quality SPOCs and QC Operators** | Operational guidance, quality expectations, process clarifications, issue resolution | Daily | Teams, meetings |
| **Project Managers (PMs)** | Project status, delivery commitments, quality risks, dependencies, milestone readiness, COQ, sampling decisions | Multiple times/week | Teams, Jira, meetings |
| **Quality Leads & SPOCs (cross-team)** | QC effectiveness, TQA results, audit findings, error trends, corrective actions | Daily | Teams, Jira, meetings |
| **Operations Managers (peer)** | KPI/MPI indicators, customer commitments, capacity planning, operational risks | Few times/week | Meetings, Teams |
| **Engineering Teams** | Tool issues, automation requests, workflow improvements, system enhancements | Weekly | Meetings, Teams |
| **External Delivery Partners (e.g., GlobalLogic, Cyient)** | Delivery performance, quality metrics, backlog, action plans, operational challenges | Weekly | Teams, review meetings |
| **Leadership (Manager / Skip Manager)** | Operational health, quality performance, customer commitments, risks, OKR progress, escalations | As needed | Meetings, email |

### What stakeholders come to the Quality Lead for
- FTA performance and trend data by project/work unit
- COQ breakdown and root causes
- QC backlog status and expected closure timelines
- MCPRCA details and closure status
- Hours deviation queries
- Resource readiness for QC work
- RCA/CAPA status and effectiveness
- Quality risk assessment for upcoming deliverables

---

## 9. Team Performance Management

### How individual performance is tracked
- User-level FTA performance by process type and work unit
- Daily time spent and productive vs. non-productive hours split
- User efficiency compared to project target and peer benchmark
- Invalid rejection rate (for QC operators)
- Deep check findings attributed to user
- TQA/QC-after-QC scores where applicable
- Assessment completion rate (HowNow)
- LinkedIn learning / training progress

### Performance coaching triggers
- User FTA consistently below PQR target across multiple data cycles
- Efficiency significantly below team average without explained cause
- Invalid rejection rate higher than team norm
- Deep check findings showing recurring error types
- Sudden unexplained drop in daily productivity
- Pattern of same error type appearing repeatedly

### Unofficial performance rules (from interviews)
- "The best reviewers are assigned where the risk is highest" — allocation depends on experience and quality history, not just availability
- Coaching conversations are held monthly 1:1 at minimum; critical performance issues are addressed immediately
- Positive recognition is important when a team member resolves a difficult issue or shows improvement
- Team members are expected to know their own performance; the quality lead's goal is to reduce how often they need to chase individuals for updates

---

## 10. AI Co-Pilot Use Cases

### Category A — Morning Automation (highest immediate value)

**A1. Daily Operational Health Summary**
Pull and consolidate the following every morning before the quality lead starts their review:
- FTA by project/process type vs. PQR target (flag anything below)
- COQ and COPQ vs. target (flag rising trends)
- QC TAT P90 vs. 24-hour threshold
- QC backlog: total open, aging distribution (0–12h, 12–24h, 24–48h, 48h+)
- QC inflow vs. outflow (last 24 hours)
- Open Jira quality tickets: overdue, newly raised, blocked
- Team attendance gaps affecting QC capacity
- Any TQA / QC-after-QC findings from past 24 hours
Output: A single 1-page briefing with only exceptions — green/amber/red per metric, sorted by urgency.

**A2. Email & Teams Triage**
- Scan incoming emails and Teams messages
- Categorize by: urgent action needed / FYI only / waiting for reply / low priority
- Draft suggested responses for routine queries (status requests, data questions)
- Flag messages referencing missed SLAs, customer escalations, or delivery risks as high priority

**A3. User Performance Pulse Check**
- Identify users who had <85% productive hours the previous day
- Identify users with FTA below PQR for 2+ consecutive days
- Surface any users with a sudden efficiency drop (>15% below their rolling average)
- Summarize in a team performance alert for the quality lead's action

---

### Category B — Automated Reports (highest time savings)

**B1. Weekly Quality Report (per project)**
Auto-generate from Databricks and Jira:
- FTA trend chart (last 4 weeks)
- COQ and COPQ weekly trend
- QC TAT P90 weekly trend
- QC volumes: total tasks, accepted, rejected, rejection rate
- Top 5 rejection reasons with frequency
- Open RCA/CAPA items and their status
- Actions from last week: closed vs. pending
- Risks and recommended actions for next week
Recipients: PM, quality stakeholders, team leads

**B2. Monthly Quality Metrics Report (per project)**
Auto-generate from Databricks, Jira, Excel:
- FTA month-over-month trend with root cause annotations
- COQ calculation (both production basis and all-realized-hours basis)
- QC after QC FTA vs. H1/H2 target
- TQA scores for the month
- Top recurring rejection categories with volume trends
- RCA/CAPA closure rate and effectiveness summary
- Month highlights, risks, and actions for next month
- Charts and tables formatted and ready to share with PMs

**B3. QC Backlog Aging Report**
Daily / on-demand:
- All tasks pending QC, grouped by aging bucket
- Flag tasks approaching or past SLA
- Estimated clearance time at current QC throughput
- Recommended QC resource allocation to clear within SLA

**B4. Confluence Process Review Page Update**
Monthly:
- Pull operational performance data from Databricks
- Compile quality trends and KPI vs. target tables
- Draft the monthly Confluence process review page content
- Include: achievements, risks, improvement initiatives, action items
- Present draft for quality lead review before posting

---

### Category C — Early Warning Alerts (highest proactive value)

**C1. FTA Degradation Early Warning**
Trigger when:
- FTA for any project/process type drops >3% below previous 7-day average
- Same error category appears in ≥3 different tasks within 48 hours
- FTA drop coincides with a temp production user recently assigned to QC

Alert content: Which work unit, which process type, what the FTA was vs. target, which error categories are driving it, which users are contributing most to the drop

**C2. COQ Risk Alert**
Trigger when:
- COQ rises above 4% (warning before the 5% hard threshold)
- COQ shows 3+ consecutive weeks of increase even if still below target
- Sampling rate is above 15% without a corresponding quality justification

**C3. QC TAT SLA Breach Warning**
Trigger when:
- QC TAT P90 is trending toward 20 hrs (warning before the 24-hr breach)
- QC inflow exceeds outflow for 2+ consecutive days (backlog building)
- More than 10% of QC tasks are in the 24–48 hr aging bucket

**C4. Delivery Commitment Risk Alert**
Trigger when:
- Current production throughput × remaining days < remaining work commitment
- A critical Jira deliverable ticket has not been updated in 3+ business days and deadline is within 7 days
- PM has submitted a priority escalation for a workflow where QC backlog is also growing

**C5. MCPRCA & OAI SLA Warning**
Trigger when:
- Any RCA ticket is within 2 days of its SLA deadline without a resolution comment
- OAI items are within 5 days of 7-day closure target
- More than 30% of open RCAs are past SLA (escalation trigger for management visibility)

---

### Category D — Workflow Automation (high efficiency gains)

**D1. Confluence Weekly Update (automated draft)**
Every week:
- Pull quality and operational metrics from Databricks
- Pull ticket status from Jira
- Draft the Confluence status update for the relevant project pages
- Present to quality lead for review and one-click approval

**D2. Monthly QC Metrics Confluence Page**
Every month-end:
- Auto-populate Total features, Accepted features, Rejected features from tracking data
- Generate charts and trend tables
- Draft the full Confluence page ready for review
- No more manual copy-paste from Excel trackers

**D3. RCA/CAPA Action Tracker**
Continuously:
- Track all open RCA and CAPA tickets in Jira
- Flag overdue actions to the responsible owner via Teams
- Generate a weekly closure rate summary
- Identify repeat incidents (same root cause appearing in multiple RCAs)
- Escalate to quality lead when closure rate drops below 70% of SLA

**D4. Jira Ticket Creation from Teams Chat**
When requested:
- Parse Teams chat messages referencing quality issues, escalations, or requests
- Draft a Jira ticket with: summary, description, severity classification, suggested assignee, linked project/process type
- Present to quality lead for review before creation

**D5. User Performance Feedback Automation**
Monthly:
- Generate personalized performance summaries for each team member
- Include: FTA trend, efficiency trend, innovative ideas, learning progress, attendance, WFO compliance, goal achievement
- Send as email to user with manager in CC
- Quality lead reviews before sending

---

### Category E — Decision Support (AI recommends, human decides)

**E1. QC Resource Recommendation**
When QC staffing decisions need to be made:
- Analyze available QC operators: quality history, error trends, throughput, experience on relevant process types
- Analyze temp production users being considered for QC: previous QC exposure, quality scores, rework history, TQA performance
- Recommend: which operators are best suited for which QC work, and which temp users are ready for independent QC vs. need supervision
- Quality lead makes final staffing call

**E2. Escalation Readiness Check**
Before escalating to PM or management:
- Summarize the situation: metric data, trend, actions already taken, current status
- Draft the escalation communication in the standard format (issue / impact / root cause / actions / recovery plan / support needed)
- Quality lead reviews and approves before sending

**E3. RCA Hypothesis Generator**
When a quality issue is identified:
- Based on historical patterns for similar issues in this process type, suggest the most likely root causes to investigate
- Cross-reference against: recent workflow changes, user assignments, data source updates, tool changes, new operators
- Generate an investigation checklist with hypotheses ranked by likelihood

**E4. Coaching Candidate Identification**
Weekly:
- Identify team members showing performance patterns that typically precede further quality decline (based on FTA trend, invalid rejections, efficiency drops)
- Flag them for a proactive coaching conversation before the issue becomes a formal concern
- Quality lead decides whether and how to act

---

## 11. Prompt Templates for Common Tasks

### Morning Briefing
```
Generate my morning quality briefing for today [DATE].

Pull from Databricks and Jira:
1. FTA by project/process type vs. PQR target — flag any below target
2. COQ and QC TAT P90 — flag if above threshold or trending up
3. QC backlog aging — flag tasks >24hrs
4. Open Jira quality tickets: count by status, flag overdue
5. Team attendance gaps affecting QC coverage today
6. Any TQA/QC-after-QC findings from the past 24 hrs

Output: Single exception-only briefing, red/amber/green per metric, sorted by urgency.
```

### Weekly FTA Review
```
Prepare the weekly FTA performance review for [PROJECT/WORK UNIT] covering [DATE RANGE].

Include:
1. FTA by process type vs. PQR target — week-over-week trend
2. Top rejection categories and their frequency (current week vs. previous 3 weeks)
3. Users with FTA below PQR for 2+ consecutive weeks — flag for coaching
4. Root cause hypotheses for any FTA drop >3%
5. Corrective actions currently open and their status

Format: Table with trend indicators + bullet points for recommended actions.
```

### Monthly Quality Report
```
Generate the monthly quality report for [PROJECT] for [MONTH YEAR].

Content required:
1. FTA: monthly average vs. target, week-by-week trend chart data
2. COQ: monthly average, calculation basis (production hrs), trend vs. previous 3 months
3. QC after QC FTA: monthly average vs. H1/H2 target
4. TQA scores: monthly summary, any below-target findings
5. QC volumes: total tasks, acceptance rate, rejection rate, top 5 rejection reasons
6. RCA/CAPA: items opened, items closed, closure rate vs. 70% SLA target
7. Key risks and issues: what happened, how it was resolved
8. Recommended actions for next month

Format: Ready to share with Project Manager — executive summary + tables + trend charts.
```

### Escalation Draft
```
Draft an escalation communication for the following situation:

ISSUE: [describe the quality or delivery issue with specific metric data]
RECIPIENT: [PM / Manager / Engineering]
CHANNEL: [Teams message / Email / Jira comment]

Use this structure:
- Issue (2 sentences, with data)
- Business impact (customer commitment risk, SLA risk, quality risk)
- Root cause (current assessment — state if still being investigated)
- Actions taken so far
- Recovery plan and timeline
- What is needed from the recipient (decision / resource / information)

Keep it under 200 words. Factual and action-oriented.
```

### RCA Investigation
```
I am investigating a quality issue in [PROCESS TYPE / WORK UNIT] where [describe what happened — e.g., FTA dropped from 97% to 88% over 3 days].

Based on historical patterns for this type of issue, suggest:
1. Top 5 most likely root cause hypotheses to investigate, ranked by probability
2. For each hypothesis: what data to check, what would confirm or rule it out
3. Any recent changes (workflow, team, data source, tool) that may be relevant
4. Investigation checklist with responsible parties

Format as a structured RCA investigation plan.
```

### QC Resource Allocation
```
I need to allocate QC resources for [WORKFLOW / WORK UNIT] for the week starting [DATE].

Current situation:
- Total QC backlog: [X tasks]
- Expected inflow: [Y tasks/day]
- Target clearance: [all within 24hr TAT]
- Available QC operators: [list]
- Temp production users being considered: [list]

Based on their historical quality performance, throughput, and experience on [process type]:
1. Recommend which operators to assign to which process types
2. Flag any temp users who should not work QC independently this week
3. Estimate if current capacity is sufficient to meet TAT target, or if additional support is needed
```

### User Performance Feedback Draft
```
Draft a monthly performance feedback message for [USER NAME] for [MONTH].

Performance data:
- FTA: [X%] vs. target [Y%] — trend: [improving / stable / declining]
- Efficiency: [X%] vs. team average [Y%]
- Innovative ideas: [count] submitted, [count] accepted
- Assessment completion: [complete / incomplete]
- Leave / WFO compliance: [summary]
- Notable achievements: [if any]
- Areas of concern: [if any]

Tone: Constructive and specific. Acknowledge strengths before discussing areas for improvement.
Length: 3–5 sentences. Include 1–2 specific recommended actions.
Send to user with manager in CC.
```

### Confluence Page Draft
```
Draft the monthly Confluence process review page for [PROJECT] for [MONTH].

Structure:
1. Executive Summary (3 sentences: what went well, what needs attention, key actions)
2. Quality Performance Table (FTA, COQ, QC TAT, QC-after-QC vs. targets)
3. Key Achievements (bullet points)
4. Risks and Issues (with status: open / resolved / monitoring)
5. Improvement Initiatives Progress (list with status)
6. Actions for Next Month (owner, due date)

Data to pull from: [list relevant Databricks dashboards / Jira filters]
Tone: Formal, data-driven. Suitable for Director-level review.
```

---

## 12. Workflow Automation Patterns

### Pattern 1 — Daily Quality Health Loop
```
[Databricks/PBI pulls overnight metrics]
        ↓
[AI Agent aggregates: FTA, COQ, QC TAT, backlog aging, user efficiency]
        ↓
[AI generates exception-only briefing]
        ↓
[Quality Lead reviews → takes action on flagged items]
        ↓
[Agent logs actions to Jira if new tickets needed]
        ↓
[Confluence daily log updated automatically]
```

### Pattern 2 — Quality Issue Response Loop
```
[Metric drops below threshold OR Jira ticket raised]
        ↓
[AI Agent: validate data → assess severity → identify affected scope]
        ↓
[AI generates: RCA hypotheses + investigation checklist]
        ↓
[Quality Lead validates root cause with leads]
        ↓
[AI drafts: CAPA action plan + escalation communication (if needed)]
        ↓
[Quality Lead approves → actions assigned in Jira]
        ↓
[AI monitors: tracks CAPA closure, checks for recurrence]
        ↓
[AI drafts: Confluence lessons learned update]
```

### Pattern 3 — Automated Report Generation
```
[Calendar trigger: end of week / end of month]
        ↓
[AI Agent pulls data from: Databricks, Jira, Excel trackers]
        ↓
[AI generates report draft: charts, tables, summaries]
        ↓
[Quality Lead reviews draft (10 min review vs. 2hr manual preparation)]
        ↓
[Quality Lead approves → AI distributes to recipients]
        ↓
[AI updates Confluence page with report content]
```

### Pattern 4 — QC Staffing Decision Support
```
[QC backlog forecast triggers staffing review]
        ↓
[AI Agent: analyzes current QC backlog by aging + process type]
        ↓
[AI pulls performance profiles: all eligible QC operators + temp users]
        ↓
[AI recommends: allocation by process type + readiness flags for temp users]
        ↓
[Quality Lead reviews recommendation → finalizes allocation]
        ↓
[AI drafts allocation plan → shared with leads via Teams]
```

---

## 13. Agent Integration Map

| Agent | Role in Quality Lead Workflow |
|---|---|
| **Analytics / BI Agent** | Pull FTA, COQ, COPQ, QC TAT, backlog, user efficiency from Databricks/PBI; generate trend analysis and exception summaries |
| **Jira Agent** | Monitor open tickets, flag overdue RCAs and OAIs, draft new tickets from issues identified, track CAPA closure rates |
| **Email / Teams Agent** | Triage incoming messages, draft escalation communications, send automated performance feedback, draft stakeholder updates |
| **Confluence Agent** | Auto-draft monthly process review pages, update quality tracker, populate weekly/monthly reports, capture lessons learned |
| **Calendar / Scheduling Agent** | Manage recurring meeting schedules, create RCA investigation sessions, set deadline reminders for MCPRCA and OAI closures |
| **Document / Report Agent** | Generate formatted quality reports with charts and tables ready for PM and leadership distribution |
| **Resource Planning Agent** | Analyze QC backlog vs. capacity, recommend resource allocation, flag temp user QC readiness based on performance profiles |

---

## 14. Institutional Knowledge & Unwritten Rules

These rules are not documented in any SOP but are widely understood and critical for effective quality operations:

- **Trends matter more than single data points** — never escalate or take corrective action based on one day's anomaly without checking the trend context
- **Quality issues rarely stay isolated** — when a recurring issue appears in one work unit, always proactively check whether the same pattern exists in adjacent workflows or process types
- **Backlog aging compounds quickly** — early intervention is significantly easier than recovery; once aging starts building, clearance time is exponentially harder
- **Escalating early is better than explaining a miss** — the cost of a premature escalation is low; the cost of a missed customer commitment is high
- **The best reviewers go where the risk is highest** — allocation is based on quality history and process expertise, not just availability
- **FTA, COQ, aging, and TQA/QC-after-QC findings drive the highest management attention** — other metrics matter, but these four are the ones that cause escalations to leadership
- **Customer-critical workflows always get different handling** — standard thresholds, monitoring frequency, and communication cadence are all adjusted for high-risk deliverables
- **Quality is never traded for productivity** — if a choice has to be made, quality takes precedence; a slower delivery with correct data is preferable to a fast delivery with quality issues

### Conditions for threshold exceptions
Exceptions to standard quality thresholds are occasionally approved for:
- Critical customer deliverables with explicit stakeholder sign-off
- New workflow rollouts during stabilization period
- High-complexity work types where standard PQR targets were not calibrated for the difficulty
- Temporary capacity constraints with a documented recovery plan
- Tooling disruptions causing involuntary deviations
- Production-to-QC transitions with supervision protocols in place

All exceptions must have: clear justification, risk assessment, stakeholder alignment, defined duration, and a recovery plan.

### Process areas requiring special handling
- **Customer-critical RM workflows** — extra monitoring, expedited QC, frequent PM updates
- **Manual Actions QC** — cannot be fully standardized; requires greater human judgment and closer oversight
- **LM Basemap** — different rules for different clients and scopes; verify requirements per client before QC
- **Temporary production users supporting QC** — never assign independently without checking readiness profile; higher QC-after-QC monitoring required
- **Cross-work-unit operations** — dependencies between work units must be tracked; a quality issue in one can cascade

---

## 15. What AI Should Never Do Automatically

Without a quality lead's explicit review and approval, AI must not:

| Action | Why |
|---|---|
| Send escalation communications to PM, customers, or leadership | Business and relationship impact; requires human judgment on tone and timing |
| Commit to or change delivery dates | Contractual and customer commitment implications |
| Reallocate resources or change workload priorities across workflows | Requires knowledge of team capability, interpersonal dynamics, and business priority |
| Approve or reject quality decisions that affect COQ or customer commitments | Quality accountability remains with the quality lead |
| Flag team members for performance improvement or coaching to third parties | People management requires context, sensitivity, and relationship awareness |
| Implement SOP or process changes | Requires stakeholder alignment and controlled rollout |
| Close high-priority Jira tickets or mark issues resolved | Requires human validation that the underlying issue is actually fixed |
| Approve sampling rate changes | Requires PM involvement and business impact assessment |
| Change QTM-defined quality targets | Targets are governance decisions, not operational ones |
| Approve new project participation for a user (CMT-related) | Must verify competency requirements are met before assigning |

---

## 16. How to Use This Skill File with AI Agents

### Provide context in every prompt
Always specify:
- **Work unit or project**: LM, RM, Genesis, Geocoding, Safety Cameras, etc.
- **Process type**: specific process (e.g., APT, Street Names, Areas, Postal SourcePrep)
- **Time period**: specific dates, sprint numbers, or week numbers
- **Metric**: which specific metric you are asking about
- **Threshold**: the relevant target or alert level for this context

### Iterative refinement
- Start with a high-level summary, then drill into anomalies
- Ask for views by time, by user, by process type, by work unit
- Cross-reference metric drops with changes in team composition or data sources

### Trust calibration
AI output on this skill can be trusted for:
- Metric aggregation and trend identification
- Exception flagging against known thresholds
- Report drafting from structured data
- Escalation communication drafting (for review)
- RCA hypothesis generation (for validation)

Human review remains required for:
- Final escalation decisions
- Resource allocation and staffing decisions
- Performance management actions
- Any communication going to external stakeholders or leadership

---

*Skill file built from AI Co-Pilot interviews conducted July–August 2026 with Quality Manager and Quality Lead roles in TomTom Maps Operations — OCC team. Synthesized across 4 individual interviews for generic applicability.*
