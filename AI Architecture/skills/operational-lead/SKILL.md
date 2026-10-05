# Operational Lead / Team Lead — AI Native Skill Profile
**Domain:** TomTom Maps Operations  
**Roles Covered:** Team Lead, Team Lead II, Manager I, Manager II (Geospatial Data Operations)  
**Source:** Synthesized from AI Co-Pilot interviews with Altaf Shaikh, Joanna Pisiałek, Vikram Makhare, Dhananjay Uday Patil, Justyna Bialecka, Girish Patil & Satish Satam — July–August 2026  
**Version:** 1.0

---

## 1. Role Overview

An Operational Lead in Maps Operations owns the day-to-day delivery of geospatial data production workflows. This role spans planning production capacity, allocating work, monitoring output quality and efficiency, managing team performance, resolving blockers, and ensuring delivery commitments are met on time.

### What this role is actually about

Most people outside this role think it is about managing task queues and attendance. In reality, it is about:

- **Planning under uncertainty** — translating weekly or quarterly targets into daily production plans when capacity, scope, and data quality are all variable
- **Making fast prioritization calls** when competing demands arrive simultaneously (urgent reQC, reactive tasks, planned production, training)
- **Keeping 13–130 people productive** by proactively removing blockers, reallocating work, and identifying skill gaps before they become delivery risks
- **Connecting output to downstream commitments** — understanding how today's production rate affects the quarterly or monthly delivery date
- **Translating operational reality into stakeholder communication** — giving PMs and managers accurate, honest status updates before they have to ask

### Team scale (typical ranges from interviews)
- **Team Lead**: 13–36 direct team members, focused on 1–3 workflow types
- **Team Lead II**: 13 direct + up to 40 broader/indirect reports; multi-workflow oversight
- **Manager I**: ~40 people (2 Team Leads), multi-product coverage, OCC location management
- **Manager II**: 110–130 people, 6–7 Team Leads, multi-product and multi-system (IRIS/OrbIT/SD/OSM)
- **Coverage**: ADAS/Lane Model Basemap, TMC products (44 countries), Road Model Lanes, Safety Cameras, HD Genesis, Source Prepping, Geocoding

### What a great month looks like
- All production delivery targets met — no CRD misses, no plan-vs-actual deviations beyond ±1%
- FTA and User Efficiency are at or above target for all active users
- Capacity plan is accurate and proactively updated when scope or attendance changes
- No unresolved escalations or blockers older than 24 hours
- Team members are receiving regular feedback, learning goals are tracked, and CMT is current
- At least one process improvement or efficiency gain identified and actioned
- Stakeholders (PMs, managers, QA) have not had to chase for status updates

---

## 2. Daily Operating Rhythm

### Morning Start Sequence (first 30–60 minutes)

Every Operational Lead begins the day with a structured check before making any allocation decisions. The exact sequence varies by role level but the core pattern is consistent across all six interviews:

**Step 1 — Communications triage**
- Check Microsoft Teams and Outlook for overnight messages, leave requests, escalations, or urgent task redirects
- Respond to anything blocking team work before stand-up
- Flag emails needing a decision from PM or manager before work allocation begins

**Step 2 — Attendance and capacity check**
- Confirm who is present, who is on planned leave, and any unexpected absences
- Pull attendance data from Workday or the team tracker
- Calculate available production hours for the day and compare to daily plan target
- Adjust work allocation for absences before the team starts

**Step 3 — Production metrics review**
- Open Power BI (IRIS dashboard or PPS dashboard, depending on workflow)
- Review previous day's output: tasks completed, hours logged, efficiency vs. plan, FTA
- Identify any users below efficiency threshold or FTA alert level
- Check for any tasks stuck in queue, pending review, or marked as blocked

**Step 4 — Jira / task board review**
- Review open tickets: reactive tasks, reQC requests, urgent escalations from QA or PM
- Prioritize incoming reactive work against planned production
- Check if any tickets from the previous day remain unresolved

**Step 5 — Daily work allocation**
- Based on available capacity, production targets, and reactive queue: assign tasks for the day
- Communicate priorities to team in stand-up or Teams message
- Confirm any adjustments to plan with PM if significant deviations expected

### Throughout the Day — Judgment Calls Made Daily

| Decision | Context |
|---|---|
| Production vs. reactive balance | Whether to pull users from planned production to handle urgent reQC, incident, or reactive task — and who to pull |
| User-level task assignment | Which user to assign to which task based on skill profile, CMT certification, current efficiency, and task complexity |
| Escalation trigger | When to inform PM vs. resolve internally; when to involve QA vs. handle as production issue |
| Plan deviation acknowledgment | When to proactively flag a plan vs. actual deviation to PM vs. absorb within the day |
| Blocker resolution | Whether a blocker can be resolved within the team vs. needs external action (data issue, source problem, tool problem) |
| Leave approval | Whether a team member's leave request can be accommodated given delivery commitments and coverage |
| Training scheduling | When to schedule training without disrupting delivery targets — who and when |

### What triggers immediate action (do not wait)
- Team member reports a data blocker or tool issue affecting production output
- Efficiency dropping below alert threshold across 2+ users simultaneously
- CRD (Customer Required Date) at risk — plan vs. actual deviation exceeding ±1%
- Reactive task volume from QA is high enough to affect planned production hours
- Unexpected absence that reduces capacity below the minimum required for the day's target
- Escalation from PM or stakeholder requiring same-day response
- ACI/reQC SLA item approaching the deadline

---

## 3. Work Allocation & Capacity Planning

### Weekly Capacity Planning Process

1. **Pull plan targets from project tracker** — CRD, scope estimates, hours per task type
2. **Map against available team capacity** — headcount × productive hours, minus planned leave, training, overhead
3. **Distribute work across team** — by workflow type, CMT certification level, and individual skill profile
4. **Create or update the weekly plan in PBI/Jira or Excel** — task assignments, daily targets per user
5. **Communicate plan to team and PM** — share adjusted plan if scope or capacity changes
6. **Track daily against plan** — log actual output at end of each day; flag deviations early

### Plan vs. Actual Tracking

The most universal KPI mentioned across all six interviews was **Plan vs. Actual Capacity** (target: ±1% deviation). This requires:

- Logging actual hours and output tasks each day
- Comparing against the committed production plan
- Identifying root causes when deviation exceeds threshold (unexpected reactive work, data blockers, skill gaps, absences)
- Proactively communicating any deviation expected to exceed threshold to PM

**Common sources of deviation:**
- Unplanned reactive tasks from QA pulling users off production
- Unexpected data issues causing rework or blocking progress
- Team member skills insufficient for assigned task type
- Tool or source availability problems
- Scope changes from PM mid-sprint

### Reactive vs. Proactive Split (by role level)

| Role | Proactive | Reactive | Primary Reactive Trigger |
|---|---|---|---|
| Team Lead — Bhishma / Source Prepping (Dhananjay) | ~70% | ~30% | Urgent reQC or PM escalation |
| Team Lead — ADAS/LM Basemap (Altaf) | ~60% | ~40% | Incident management, tool issues |
| Team Lead — TMC Products (Vikram) | ~70% | ~30% | Quarterly package delivery changes |
| Team Lead II — Safety Cameras/HD Orbis (Justyna) | ~50% | ~50% | ACI SLA items, reQC pipeline |
| Manager I — Multi-workflow (Joanna) | ~40% | ~60% | Multi-workflow exceptions, escalations |
| Manager II — Portfolio (Girish/Satish) | ~50% | ~50% | Cross-team escalations, managerial decisions |

---

## 4. Delivery & Pipeline Tracking

### Key Delivery Constructs

**CRD (Customer Required Date)** — The committed delivery date for a batch or project milestone. Operational Leads are responsible for tracking whether current production rates will meet CRD. If plan vs. actual deviation indicates CRD at risk, this must be escalated to PM immediately.

**Quarterly Package Delivery (TMC)** — Vikram's team delivers TMC data packages quarterly across 44 countries (EUR/NAM/SEA/OCE). Each package covers a 3-month scope; delivery rhythm is strict. Missing a quarterly package = high-severity delivery failure.

**OM Tracking** — Operations Management tracking of in-flight work; target 90% tracking completeness. Gaps in OM tracking = invisible work = inaccurate capacity and delivery projections.

**ACI SLA** — Alert/Change Item SLA, target <24 hours response. Any item breaching 24 hrs requires immediate escalation.

### Delivery Pipeline Health Check (Daily)

| Signal | Healthy State | Alert |
|---|---|---|
| Plan vs. Actual hours | Within ±1% of committed plan | >1% deviation for 2+ consecutive days |
| Task completion rate | On track for CRD | Behind plan by >5% with no recovery path |
| FTA rate | At or above target for all active workflows | Below alert threshold for 2+ users or 2+ days |
| Reactive task queue | Managed within the day | Growing backlog requiring dedicated reactive allocation |
| Blocker count | 0 open blockers | Any blocker >24 hrs without resolution |
| ACI/reQC SLA | 100% within SLA | Any item approaching or past SLA |

---

## 5. Metrics Monitoring & Interpretation

### Universal Metrics (all role levels)

| Metric | Target | Alert Threshold | Source | Frequency |
|---|---|---|---|---|
| User Efficiency | 100% | <85–90% (role-dependent) | PBI / Databricks | Daily |
| User FTA (First Time Acceptance) | 98–100% | <95% | PBI / Databricks | Daily |
| Plan vs. Actual Capacity | ±1% | >1% deviation | Excel / PBI | Daily |
| CMT (Competency Matrix) completion | 95% | <90% | HowNow / Jira | Monthly |
| Assessment Completion | 90% | <85% | HowNow | Monthly |
| Team Attendance | Per plan | Unexpected absence affecting delivery | Workday | Daily |

### Role-Specific Metrics

**Altaf Shaikh — ADAS/Lane Model Basemap (production rate benchmarks):**

| Process Type | Benchmark Rate |
|---|---|
| HDOrbis-ConflictSolving | 1.59 tasks/hr |
| HDOrbis-Create-GapFilling | 1.70 tasks/hr |
| LMOrbis-Create-RoadSurface | 5.94 tasks/hr |
| HDOrbis-Create-LegEditing | 12.23 tasks/hr |
| HDOrbis-Moderate-LegPositioning | 80 tasks/hr |

**Vikram Makhare — TMC Products (44 countries):**

| Metric | Target | Alert |
|---|---|---|
| FTA | 99% | <98% |
| Efficiency | 100% | <90% |
| CRD Rework / ReQC SLA | 95% | <90% |
| Yield | 85% | <80% |
| OM Tracking | 90% | <85% |
| COQ | ≤7% | >10% |
| COPQ | ≤0.1% | >0.2% |
| Capacity Deviation | ±1% | >1% |

**Justyna Bialecka — Safety Cameras / RM Lanes / HD Orbis:**

| Metric | Target | Alert |
|---|---|---|
| PQC (Production Quality Check) | 95% | <85% |
| Freshness | <4 years | Any record >4 years old |
| Additional Value Rate | 40% | <35% |
| DPA (Data Provider Accuracy) | >98% | <95% |
| ACI SLA | <24 hrs | Approaching 20 hrs |

**Dhananjay Uday Patil — Source Prepping (Bhishma team):**
- FTA: 100% (absolute — no tolerance)
- Production rate tracked per task type: Area, Street Name, APT, Logistics, Postal, Visualization, POI

**Joanna Pisiałek — Manager I (multi-workflow):**

| Metric | Target | Alert |
|---|---|---|
| Quality Score | ≥98% | <95% |
| On-Time Delivery | 100% | <95% |

**Girish Patil / Satish Satam — Manager II (portfolio):**

| Metric | Target | Alert |
|---|---|---|
| FTA | >95% | Significant deviation from baseline (also review if consistently >98% — may indicate sampling gap) |
| Efficiency | Individual baseline | Below baseline trend |
| CMT | 95% | <90% |
| Assessments | 90% | <85% |

### Reading the Metrics Correctly

**FTA interpretation nuances:**
- FTA >98% consistently can sometimes indicate under-sampling or lenient QC — not always a positive signal
- FTA dropping to 95% across multiple projects simultaneously suggests a systemic source data or tooling issue rather than an individual operator gap
- FTA dropping for one user while stable for others = individual skill or attention issue

**Efficiency interpretation nuances:**
- Efficiency below 85% for one day: investigate (leave overlap, data blocker, training)
- Efficiency below 85% for 3+ consecutive days: coaching conversation required
- Efficiency spike significantly above typical range: check for task type mismatch (user assigned to easier task type, inflating rate)

---

## 6. Team Management & Performance Coaching

### CMT (Competency Matrix Tracker)

All Operational Leads manage team skills using the CMT. Key rules:
- No team member should be assigned to a task type they are not CMT-certified for without explicit manager approval and supervised conditions
- CMT must be kept current — completion target 95% (alert: <90%)
- When adding a new workflow or task type to the team's scope, plan for CMT training lead time before production begins
- CMT assessments: 90% completion target; missed assessments are tracked as a portfolio metric at Manager II level

**CMT update triggers:**
- New team member joins
- New task type added to workflow scope
- Team member moves from one project to another
- Performance issue identified — assess whether CMT gap is contributing

### What Operational Leads Track for Each Team Member

| Dimension | How Tracked | Alert |
|---|---|---|
| Daily/weekly efficiency | PBI dashboard | Below individual baseline or threshold |
| FTA per project/process type | PBI / Databricks | Below 95% alert |
| CMT status and next assessment due | HowNow + Excel | Expired or missing certification |
| Learning hours | HowNow platform | Below target |
| Attendance and leave pattern | Workday | Frequent unplanned absence |
| Open coaching conversations | Excel / Jira | Unresolved conversation >7 days |

### Performance Conversation Triggers

- Efficiency below threshold for 3+ consecutive days
- FTA below alert level for a specific process type
- Missed CMT assessment deadline
- Behavioral concerns raised by peers or other leads
- Upcoming role change or promotion consideration

### Team Development Activities (consistently displaced by reactive work)

From all six interviews, these activities are consistently deprioritized under operational pressure:
- Coaching sessions on production technique improvements
- Knowledge-sharing sessions across team leads
- AI tool adoption and exploration time
- Process improvement analysis and documentation
- Gemba walks and floor-level observation

---

## 7. Reporting & Communication

### Recurring Reports

| Report | Frequency | Audience | Content | Tool Used |
|---|---|---|---|---|
| Daily production update | Daily | PM / Manager | Actuals vs. plan, blockers, attendance deviation | Teams message / PBI |
| Weekly capacity plan | Weekly | PM | Plan for next week: targets, headcount, risks | Excel / Jira |
| Monthly plan vs. actual summary | Monthly | PM / Manager | Hours, FTA, efficiency, scope delivered vs. committed | Excel / PBI |
| CMT status update | Monthly | Manager | Team certification status per task type | Excel / HowNow |
| Project status update | Per sprint/milestone | PM | Progress, risks, blockers, forecast vs. CRD | Confluence / Jira |
| Quarterly TMC package status | Quarterly | PM / Leadership | Country-level delivery status, FTA, yield, COQ | Excel / PBI |

### What Consumes Disproportionate Time (from all six interviews)

1. **Plan vs. Actual compilation** — pulling daily output from PBI/Jira, comparing to the Excel capacity plan, calculating deviation percentage. Done manually every day.
2. **Attendance tracking** — cross-referencing Workday, team tracker, and Teams messages to confirm actual attendance. No automated reconciliation.
3. **CMT status tracking** — combining HowNow learning data with Jira task assignments to confirm certification status. Fully manual.
4. **Efficiency trend compilation** — extracting user-level efficiency from IRIS/PBI dashboard and formatting it for PM or manager distribution.
5. **Project scope tracking** — when PM updates scope mid-sprint, re-calculating plan impact manually.
6. **Quarterly yield/FTA report (TMC)** — compiling FTA, yield, COQ, COPQ across 44 countries for quarterly reporting. Multi-hour manual exercise.

### Communication Best Practices (from interviews)

- **Proactive communication is universal expectation**: PMs and managers expect updates before they ask. Operational Leads who wait for the question are viewed as reactive.
- **Escalate with a recommended action**: Don't just flag a problem — arrive with at least one proposed resolution path.
- **Status updates should be brief and structured**: PM wants to know: status (green/amber/red), reason if not green, action being taken, date by which it will be resolved.
- **Separate factual status from risk assessment**: "We are at 87% of plan" is a fact. "This puts CRD at risk if the pattern continues" is an assessment. Both are needed but should be clearly labeled.

---

## 8. Issue Escalation & Incident Handling

### Escalation Decision Framework

| Situation | Action | Who to Inform |
|---|---|---|
| Single user efficiency drop (one day) | Monitor; investigate cause locally | No escalation needed today |
| Single user efficiency drop (3+ days) | Coaching conversation; investigate CMT/task fit | Inform manager if no improvement |
| FTA below alert for one user | Check task type; review recent errors; provide feedback | No escalation if isolated |
| FTA below alert across 2+ users | Systematic investigation; check source data, tooling, recent process changes | Inform PM and QA lead |
| CRD at risk (plan >1% behind) | Reassess daily targets; propose recovery plan | PM immediately |
| Blocker affecting >20% of team capacity | Document and escalate — do not absorb silently | PM and manager same day |
| Tool or source availability issue | Report to tech team; quantify output impact; adjust daily plan | PM same day |
| Reactive task volume >20% of daily capacity | Flag to PM; agree on reactive vs. planned production balance | PM |
| Team conflict or behavioral issue | Handle 1-on-1 first; involve manager if not resolved in 48 hours | Manager |
| Quality failure flagged by customer or QA | Immediate triage; initiate RCA; PM visibility | PM + QA lead same day |
| ACI SLA approaching 20-hour mark | Prioritize item; reassign if needed | Notify PM if not resolvable within SLA |

### Incident Management (ADAS/Lane Model workflows — Altaf Shaikh)

In ADAS/Lane Model Basemap workflows, incidents have a more formal handling process:

1. **Identify** — user reports an anomaly or QA flags a concern
2. **Triage** — Team Lead assesses severity and scope (isolated error vs. systematic issue)
3. **Contain** — stop further production on affected task type if systematic; isolate affected output
4. **Root Cause** — review recent process changes, source data updates, or tool changes
5. **Resolve** — apply fix; verify with QA
6. **Document** — log in Jira; update team on lesson learned
7. **Prevent** — update SOP or add QC check if pattern is likely to recur

---

## 9. Cross-Team & Stakeholder Coordination

### Key Relationships

| Stakeholder | Nature of Interaction | Frequency |
|---|---|---|
| Project Manager (PM) | Delivery status, plan vs. actual, scope changes, escalations | Daily |
| QA / Quality Lead | FTA data, reQC requests, sampling coordination, quality issues | Daily/Weekly |
| Other Team Leads | Capacity sharing, coverage during leave, cross-team task allocation | Weekly |
| Manager (up) | Performance updates, escalations beyond TL authority, strategic direction | Weekly |
| Tool/Platform team | Databricks, IRIS, OrbIT — tool issues, feature requests | As needed |
| HR / Workday | Leave approvals, attendance, onboarding | As needed |
| Source Data teams | Data quality issues, source gaps, data provider coordination | As needed |

### Managing Upward (PM and Manager)

**What PMs expect from Operational Leads:**
- Reliable daily/weekly status that matches actual output — no surprises at sprint end
- Proactive flagging of scope or capacity risks before they become misses
- Honest assessment of team capability and skill gaps when assigning new work
- Quick escalation with a proposed solution, not just a problem statement

**What managers expect:**
- Team health data: FTA, efficiency, CMT, attendance — consolidated, not in five different attachments
- Issues handled at TL level before requiring manager intervention
- Development conversations happening — not just task management
- Operational continuity even when key team members are absent

---

## 10. Tools & Systems Used Daily

| Tool | Purpose | Frequency | Pain Point |
|---|---|---|---|
| Power BI (IRIS / PPS dashboard) | Efficiency, FTA, task completion metrics | Daily | Requires manual export; no automatic alerts |
| Jira | Task management, reactive items, escalations, blocker tracking | Daily | Tickets require manual status update; no automatic priority alerts |
| Microsoft Teams | Communication, attendance confirmation, escalations | Daily | Escalations come via chat — not tracked systematically |
| Outlook | Formal communications, leave requests, stakeholder updates | Daily | Email triage consumes 20–30 mins/day |
| Workday | Attendance, leave management | Daily | No direct integration with capacity planning tools |
| Excel | Capacity planning, plan vs. actual tracking, CMT tracking | Daily/Weekly | Manual data entry; error-prone; not real-time |
| Confluence | Project documentation, SOPs, status pages | Weekly | Updates done manually; not linked to live data |
| HowNow | Learning management, CMT certification tracking | Weekly/Monthly | Not integrated with PBI or Jira; requires separate manual check |
| OrbIT / IRIS / SD / OSM | Production workflow tools (workflow-specific) | Daily | Tool-specific; no unified dashboard across systems |
| Databricks | Advanced metrics, deeper query-based analysis | As needed (Manager II) | Requires SQL skills; not accessible to all TLs directly |

---

## 11. Decision-Making Frameworks

### The Three Questions Before Any Major Decision

1. **Does this impact the CRD or delivery commitment?** If yes → involve PM.
2. **Does this require a skill or certification not confirmed in the CMT?** If yes → check CMT before assigning.
3. **Can this be resolved within my authority, or does it need my manager?** Define the boundary clearly before escalating.

### Prioritization Logic (when reactive and planned work compete)

1. **SLA-bound reactive items** (ACI, reQC with hard deadline) — always take priority
2. **CRD-risk planned items** — second priority; protect hours that directly affect the next delivery date
3. **Standard planned production** — third priority; adjust user allocation rather than stopping production
4. **Non-urgent improvement or documentation** — defer to end of day or next day

### Leave and Capacity Trade-off Logic

- If a team member on leave reduces daily capacity by >10%: flag to PM; negotiate plan adjustment before approving further leave
- If a team member requests leave on a CRD week: assess coverage; only approve if production target is achievable without them
- If multiple team members request leave simultaneously: stagger approval; communicate constraints respectfully

---

## 12. AI Co-Pilot Integration Points

### Where AI Creates the Most Value (from interviews)

**High-priority, immediately actionable:**

**1. Morning Ops Briefing**
Every Operational Lead described spending 20–45 minutes every morning checking Teams, Workday, PBI, Jira, and Excel separately before making any decisions. An AI agent that consolidates attendance (Workday), previous day's output (PBI), open reactive items (Jira), and plan vs. actual status (Excel) into a 5-minute brief would eliminate the most universal time drain in this role.

**2. Plan vs. Actual Auto-Update**
Currently: pull PBI data manually → paste into Excel capacity tracker → calculate deviation. An AI agent that reads PBI or Databricks output and updates the plan automatically, flagging deviations >1%, would save 15–30 minutes per day per Team Lead.

**3. Quarterly TMC Yield/FTA Report Auto-Generation**
Vikram's team compiles yield, FTA, COQ, COPQ metrics across 44 countries manually for quarterly reporting. An AI agent that pulls from Databricks, calculates trends, and generates the quarterly report draft would save multiple hours per reporting cycle.

**4. Email and Teams Triage Summary**
All managers (Joanna, Girish/Satish) spend significant time triaging Teams messages and emails. An AI summary of overnight/morning messages categorized as: "needs decision today / informational / can defer" would speed up morning triage substantially.

**5. Attendance + Capacity Impact Alert**
When Workday or Teams shows absences, an AI agent that automatically recalculates available production hours for the day and flags if CRD is at risk would remove a manual calculation that currently takes 10–15 minutes.

**Valuable but requires slightly more setup:**

**6. CMT Status Consolidation**
HowNow + Jira + Excel = three sources required to confirm who is certified for what. An AI agent that consolidates certification status and flags expired or missing certifications would prevent assignment errors and reduce monthly manual checking.

**7. Weekly PM Update Draft**
Based on the week's PBI data and Jira activity, auto-draft the PM update in a standard format. TL reviews and sends.

**8. Reactive Task Auto-Prioritization**
When multiple reQC or reactive items arrive on the same day, an AI agent that ranks them by SLA urgency and delivery impact — and suggests which users to reassign — reduces the manual prioritization overhead.

### AI Wishlist (verbatim from interviews)

- *"Morning summary: who's on leave today, what happened yesterday in terms of production, what's pending in Jira"*
- *"Auto-update my plan vs. actual when PBI data updates — I shouldn't have to copy it manually"*
- *"Yield report generated automatically for the quarterly TMC package — I just review and send it"*
- *"Summarize Teams messages overnight so I know what needs attention in the morning"*
- *"Alert me if any user's efficiency is dropping before I have to dig through the dashboard"*
- *"Tell me immediately when any ACI item is at risk of breaching the 24-hour SLA"*

---

## 13. What AI Should and Must Not Do

### AI CAN — Automate, Recommend, Alert

- Pull attendance data from Workday and calculate today's available production hours
- Compare previous day's PBI output against the Excel/Jira capacity plan and flag deviations >1%
- Alert when FTA or efficiency for any user crosses below the configured threshold
- Summarize overnight Teams messages and Outlook emails into action/informational/defer categories
- Draft weekly status updates (PM update format) based on the week's metrics data
- Generate quarterly or monthly report drafts from Databricks/PBI data (FTA, yield, COQ, COPQ)
- Compile CMT certification status across HowNow + Jira and flag gaps or expiries
- Recommend task allocation based on CMT certification, current efficiency, and workload balance
- Alert when ACI SLA items are approaching the 24-hour threshold
- Auto-generate yield/FTA trend tables for review before distribution
- Draft Confluence project status pages based on current Jira and PBI data
- Monitor Plan vs. Actual continuously and trigger alert when deviation exceeds ±1%

### AI MUST NOT — Without Human Review and Approval

- Commit to delivery dates or CRD on behalf of the team or PM
- Make performance decisions about team members (ratings, PIPs, promotions)
- Approve or deny leave requests (requires contextual judgment AI cannot fully assess)
- Send escalations to PM or leadership automatically
- Reassign users to different projects without TL/Manager approval
- Change production plans without manager or PM sign-off
- Communicate directly with customers or external stakeholders
- Make scope change decisions independently
- Remove or close Jira tickets or mark work as complete without human verification
- Assign users to task types not confirmed in CMT

---

## 14. Role-Level Differences

### Team Lead (13–36 direct reports)

**Focus:** Day-to-day production management for a specific workflow or product type. Direct task allocation. Hands-on with individual team member performance.

**Typical daily scope:**
- Manage 13–36 users across 1–3 workflow types
- Track daily output vs. plan — manually every day
- Handle reactive tasks and blockers within team authority
- Escalate only what cannot be resolved at TL level

**Biggest AI need:** Morning briefing (attendance + daily plan health + open blockers), plan vs. actual auto-update, alert when individual user metrics deviate.

### Team Lead II (13 direct + up to 40 broader)

**Focus:** Balances direct team management with coordination across a broader pool of operators. More complexity in reactive handling — ACI SLA items, DPA monitoring, multiple workflow coordination.

**Typical daily scope:**
- Manage both direct and indirect team members across multiple workflows
- Coordinate QC sampling and ACI processing
- Interface with QA lead and PM more frequently than standard TL
- Monitor DPA results and freshness metrics

**Biggest AI need:** ACI SLA alert, PQC and freshness tracking, consolidated CMT dashboard, efficiency view across direct + indirect reports.

### Manager I (~40 people, 2 Team Leads)

**Focus:** Manages Team Leads, not individual operators. Accountable for multi-product delivery across OCC location. More reactive than TL due to multi-workflow exception handling and escalations.

**Typical daily scope:**
- Review Team Lead status updates
- Handle exceptions that TLs escalate
- Coordinate with PM on scope, delivery, and staffing
- OCC-level capacity management across workflows

**Biggest AI need:** Cross-TL status roll-up, quality score and on-time delivery tracking, escalation triage, multi-workflow plan vs. actual comparison.

### Manager II (110–130 people, 6–7 Team Leads)

**Focus:** Strategic people management and cross-product delivery governance. Operates at the level of TL performance, not individual operator performance. Accountable for FTA, efficiency, CMT, assessment, and attendance as portfolio metrics.

**Typical daily scope:**
- Review TL-level dashboards and escalations
- Conduct 1:1s with Team Leads
- Manage hiring, onboarding, and offboarding decisions
- Interface with Senior PM and leadership on delivery commitments
- Drive multi-product FTA and efficiency targets across IRIS/OrbIT/SD/OSM

**Biggest AI need:** Manager-level dashboard (portfolio FTA, efficiency by TL, CMT completion, assessment tracking, attendance), automated weekly TL performance summary, escalation pattern detection across TLs.

---

## 15. Prompt Templates for AI Co-Pilot

### Morning Briefing Prompt
```
You are an Operational Lead briefing assistant for TomTom Maps Operations.

Pull the following data for today, {date}:
- Attendance: who is absent vs. plan (Workday)
- Previous day output vs. plan: total tasks completed, efficiency %, FTA %
- Open Jira reactive items: count and highest-priority ones
- Any users with efficiency below 85% or FTA below 95% in the last 2 days

Format the briefing as:
1. Today's team: [available headcount vs. plan]
2. Yesterday's performance: [green/amber/red per metric + key deviation]
3. Reactive queue: [count + top 3 items]
4. Users needing attention: [names + metric + trend]
5. Recommended focus for today: [1-2 sentences]
```

### Plan vs. Actual Check Prompt
```
Compare today's production output against the committed plan for project {project_name}.

Data:
- Committed plan: {plan_tasks} tasks for {plan_hours} hours
- Actual output: {actual_tasks} tasks in {actual_hours} hours
- FTA: {fta_pct}% (target: {fta_target}%)

Calculate:
1. Efficiency deviation: actual vs. plan (%)
2. FTA status: at target / below alert / critical
3. Projected CRD status at current rate
4. Recommended action if deviation >1%
```

### Weekly PM Update Draft Prompt
```
Draft a weekly production status update for PM {pm_name} for project {project_name}.

Week of: {week_dates}
Team: {team_name}, {headcount} operators

Include:
1. Summary line (green/amber/red + one sentence reason)
2. Key metrics: tasks delivered, FTA%, efficiency%, plan vs. actual%
3. Blockers this week: [list or "none"]
4. Next week outlook: expected capacity, targets, any risks
5. Any actions needed from PM side

Keep it under 200 words. Use bullet points.
```

### Quarterly TMC Report Draft Prompt
```
Generate the quarterly TMC delivery report for {quarter} across regions: EUR, NAM, SEA, OCE.

For each region, include:
- Countries covered
- Tasks delivered vs. target
- FTA: {fta}% (target: 99%, alert: <98%)
- Yield: {yield}% (target: 85%, alert: <80%)
- COQ: {coq}% (target: ≤7%, alert: >10%)
- COPQ: {copq}% (target: ≤0.1%, alert: >0.2%)
- Any CRD misses and root cause

Conclude with: portfolio status (on-track/at-risk), top 3 risks for next quarter, recommended actions.
```

### FTA or Efficiency Alert Investigation Prompt
```
{metric_name} for {user_name} on project {project_name} has dropped to {value}%
(target: {target}%, alert: {alert}%).

Investigate:
1. Duration of the decline: when did it start?
2. Pattern: all task types affected or specific type?
3. Comparison to team average: isolated or team-wide?
4. Recent changes: new task type? source data update? tool change? return from leave?
5. Recommended action: feedback conversation / task reassignment / CMT check / QA review

Output: structured investigation summary for TL coaching conversation.
```

### ACI SLA Monitoring Prompt
```
Check all open ACI items for team {team_name} as of {timestamp}.

For each item:
- Time open vs. 24-hour SLA
- Assignee
- Status

Flag any items:
- Past 24 hours → BREACH: escalate to PM immediately
- Between 20–24 hours → WARNING: reassign or expedite now
- Under 20 hours → OK: monitor

Output: briefing table for Team Lead with recommended action per item.
```

---

## 16. Appendix: Metrics Quick Reference

### Universal Thresholds (all role levels)

| Metric | Target | Alert | Action if Alert |
|---|---|---|---|
| User Efficiency | 100% | <85–90% | Investigate within 24hr; coaching if persistent >3 days |
| User FTA | 98–100% | <95% | Check task type fit; feedback; escalate if team-wide |
| Plan vs. Actual | ±1% | >1% for 2+ days | Recover plan or notify PM with updated forecast |
| CMT Completion | 95% | <90% | Identify gap; schedule training; do not assign uncertified work |
| Assessment Completion | 90% | <85% | Flag to manager; schedule overdue assessments |

### TMC-Specific Thresholds (Vikram Makhare's team)

| Metric | Target | Alert |
|---|---|---|
| FTA | 99% | <98% |
| Efficiency | 100% | <90% |
| CRD Rework ReQC SLA | 95% | <90% |
| Yield | 85% | <80% |
| OM Tracking | 90% | <85% |
| COQ | ≤7% | >10% |
| COPQ | ≤0.1% | >0.2% |

### Safety Cameras / HD Orbis (Justyna Bialecka's team)

| Metric | Target | Alert |
|---|---|---|
| PQC | 95% | <85% |
| Freshness | <4 years | Any record >4 years old |
| Additional Value | 40% | <35% |
| DPA Results | >98% | <95% |
| ACI SLA | <24 hrs | Approaching 20 hrs |

### Multi-Workflow Manager I (Joanna Pisiałek)

| Metric | Target | Alert |
|---|---|---|
| Quality Score | ≥98% | <95% |
| On-Time Delivery | 100% | <95% |

### Manager II Portfolio (Girish Patil / Satish Satam)

| Metric | Target | Alert |
|---|---|---|
| FTA | >95% | Significant deviation from baseline |
| CMT | 95% | <90% |
| Assessments | 90% | <85% |

---

*This skill profile is a living document. Update it when new workflows, metrics, or AI use cases are confirmed through implementation.*
