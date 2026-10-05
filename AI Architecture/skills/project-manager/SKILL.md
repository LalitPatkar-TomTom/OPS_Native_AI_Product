# Project Manager - AI Native Operations

**Purpose:** Help Project Managers leverage AI agents to orchestrate delivery, manage risks and stakeholders, and convert business demand into executable plans across Maps Operations.

**When to use:** Any time a Project Manager needs to coordinate delivery, manage project risks, track dependencies, communicate with stakeholders, or document project activities.

---

## Role Context

You are a **Project Manager (Control Tower)** in Maps Operations at TomTom. Your responsibilities include:

- Orchestrate delivery across Ops, QA, BA, and Automated Data Production teams
- Convert demand from Product value streams into execution plans
- Manage project risks, dependencies, and change requests
- Coordinate stakeholders and maintain project documentation
- Track progress and report status to leadership

## AI Agent Integration

As a Project Manager, you are the orchestration hub working with ALL AI agents:

### Jira Agent (Primary Tool)
- **Ticket breakdown**: Convert CM tickets to OM deliverables per Ops unit
- **Lifecycle management**: Track tickets through workflow states
- **Risk tracking**: Log and monitor project risks and dependencies
- **Change requests**: Document scope changes and impact analysis
- **Sprint planning**: Capacity planning and sprint commitment

### Workflow Agent
- **Workpackage creation**: Generate Orbit workpackages from deliverables
- **Task assignment**: Coordinate with Ops Leads on task distribution
- **Progress monitoring**: Track execution across all operational units

### Email & Comms Agent
- **Stakeholder updates**: Regular status reports to Product and leadership
- **Escalations**: Alert decision-makers when intervention needed
- **Coordination**: Facilitate communication across Ops, QA, BA teams

### Calendar Agent
- **Meeting orchestration**: Sprint planning, standups, retrospectives, stakeholder reviews
- **Agenda management**: Prepare structured agendas with context
- **Action tracking**: Capture and follow up on meeting decisions

### Confluence Agent
- **Project documentation**: Charters, plans, closure reports, lessons learned
- **Status reporting**: Weekly/monthly project health summaries
- **Knowledge management**: SOPs, templates, retrospective findings

### Analytics & Reporting Agent
- **Earned value analysis**: Budget and schedule performance
- **Velocity tracking**: Historical and forecasted delivery rates
- **Risk analytics**: Probability and impact assessments
- **Executive reporting**: Portfolio-level views and KPI dashboards

---

## Common Tasks & Prompts

### Convert Demand into Execution Plan

**Task:** Translate Product requirements into executable delivery plan

**Prompt:**
```
I'm a Project Manager receiving new demand from Product value streams.

Requirements:
[Paste or describe Product request]

Using Jira Agent and Workflow Agent:
1. Create CM (Change Management) tickets for the initiative
2. Break down each CM ticket into OM (Operational) deliverables by unit
3. Generate Orbit workpackages for Ops Leads to assign
4. Identify dependencies on other teams or projects
5. Estimate timeline and resource requirements

Provide:
- Jira ticket structure
- Delivery timeline with milestones
- Dependency map
- Risk assessment (capacity, complexity, unknowns)
```

### Manage Sprint Planning

**Task:** Coordinate sprint commitments across operational units

**Prompt:**
```
Planning Sprint [number] for [dates].

Input:
- Product priorities: [list top priorities]
- Team capacity: [Ops units and available capacity]
- Carryover work: [incomplete items from last sprint]

Using Jira Agent:
1. Pull backlog items aligned with Product priorities
2. Size items against available capacity
3. Break into OM deliverables for each Ops unit
4. Flag any capacity risks or dependency blockers
5. Generate sprint commitment summary

Create sprint plan with:
- Committed deliverables by unit
- Stretch goals if capacity allows
- Risks to achieving sprint goals
- Stakeholder communication plan
```

### Track Project Risks

**Task:** Maintain risk register and mitigation strategies

**Prompt:**
```
Update project risk register for [project name]:

Current risks from:
- Ops Leads: Delivery blockers and capacity concerns
- Quality Leads: Quality issues impacting timeline
- BA: Data trends suggesting future problems

For each risk:
1. Categorize (scope, schedule, resource, quality, dependency)
2. Assess probability (low/medium/high)
3. Assess impact (low/medium/high)
4. Define mitigation strategy
5. Assign owner and track status

Log in Jira as risk tickets and summarize in Confluence.
Notify stakeholders via Email Agent for high-priority risks.
```

### Produce Status Reports

**Task:** Generate executive-level project status updates

**Prompt:**
```
Create weekly project status report for [project name]:

Pull data from:
- Jira Agent: Completed vs planned deliverables, sprint burndown
- Analytics Agent: Earned value metrics, forecast to completion
- Workflow Agent: Task completion rates, blocker status
- Quality: FTA and defect trends

Report structure:
1. Executive Summary (RAG status: Red/Amber/Green)
2. Key Milestones (completed this week, planned next week)
3. Metrics (velocity, burndown, quality)
4. Top Risks (with mitigation status)
5. Blockers Escalated (requiring stakeholder decision)
6. Recommendations (adjustments needed)

Format for Confluence and email distribution to stakeholders.
```

### Manage Change Requests

**Task:** Document and assess scope changes

**Prompt:**
```
Change request received from Product:
[Describe requested change]

Using Jira Agent and Analytics Agent:
1. Document current scope and commitments
2. Analyze impact on:
   - Timeline: Delivery date shifts
   - Resources: Additional capacity needed
   - Quality: Risk to FTA or rework
   - Dependencies: Impact on other projects
3. Estimate effort for the change
4. Propose options:
   - Accept with timeline extension
   - Accept with descoped items
   - Defer to next sprint/release
5. Draft change request document for stakeholder approval

Provide impact analysis and recommendation memo.
```

### Coordinate Cross-Functional Delivery

**Task:** Align Ops, QA, and BA on project execution

**Prompt:**
```
Project [name] requires coordination across:
- Ops Leads: Execute [specific deliverables]
- Quality Leads: Validate against [acceptance criteria]
- Business Analyst: Track [performance metrics]

Using Calendar Agent and Email Agent:
1. Schedule coordination meeting with agenda:
   - Review deliverables and acceptance criteria
   - Align on quality standards and review process
   - Define handoff workflow (Ops → QA → PM)
   - Establish communication cadence
2. Document workflow in Confluence
3. Set up automated status updates via Reporting Agent
4. Create Jira tickets for each team with linked dependencies

Provide meeting invite, agenda, and Confluence workflow doc.
```

---

## Workflow Patterns

### Planning Flow: Demand → Execution

Your core orchestration workflow:

**Product → PM (You) → Jira Agent + Workflow Agent → Execution**

1. **Receive** demand from Product value streams (scope, priorities, roadmap)
2. **Translate** via Jira Agent: Create CM tickets → Break into OM deliverables
3. **Distribute** via Workflow Agent: Create workpackages → Ops assigns tasks
4. **Monitor** execution via Jira, Workflow, and stakeholder sync

**Your role:** Orchestrator ensuring smooth flow from demand to delivery

**Prompt template:**
```
New demand: [Product request]
Convert to execution plan:
1. Jira CM tickets with deliverables per Ops unit
2. Workflow workpackages for task assignment
3. Timeline with milestones and dependencies
4. Stakeholder communication plan
```

### Quality Control Loop: Execution ↔ Quality ↔ PM

How you coordinate the quality feedback cycle:

**Ops → Quality → PM (You)**

Work executed → QA reviewed → Issues escalated to you for decision

**Your role:** Triage quality issues—what gets reworked, what gets accepted, what gets escalated to Product

**Prompt:**
```
Quality Lead flagged issues in Sprint [number]:
[List quality issues and affected deliverables]

For each issue:
1. Assess severity (blocks release / needs rework / acceptable)
2. Decide: Rework in current sprint / Move to backlog / Escalate to Product
3. Update Jira tickets with decision and revised timeline
4. Notify Ops Leads of rework assignments
5. Notify Product if release timeline impacted

Provide triage decisions and communication plan.
```

### Performance Insight Loop: Data → PM Decisions

How BA supports your decision-making:

**Ops/Quality → BA → PM (You)**

Operational data → BA analyzes → You receive insights to inform decisions

**Your role:** Request analysis, interpret insights, make informed decisions

**Prompt:**
```
Request analysis from Business Analyst:

Question: [Specific question you need answered]
Context: [Why you need this / what decision it informs]
Data sources: [Jira / Workflow / Analytics Agent]
Timeline: [When you need the answer]
Format: [Dashboard / Report / Recommendation memo]

Example: "Should we extend the sprint deadline or descope 2 deliverables?
Need velocity analysis and forecast to completion by EOD for stakeholder decision."
```

### Automated Issue Flow: AI-Driven Escalation

How AI agents proactively surface issues:

**Agent detects → Jira logs → Email notifies → You triage → Resolution coordinated**

**Your role:** Review automated alerts, prioritize, coordinate resolution across teams

**Prompt:**
```
Analytics Agent flagged issue: [Description]
Jira ticket auto-created: [Ticket ID]

Triage:
1. Is this a known issue or new pattern?
2. Which team owns resolution? (Ops / QA / Engineering / Product)
3. What's the urgency? (Immediate / This sprint / Backlog)
4. Who needs to be notified?

Assign owner, set priority, notify stakeholders via Email Agent.
```

---

## Integration with Other Roles

### With Product Value Streams
- Receive demand: Scope, priorities, roadmap expectations
- Deliver outcomes: Completed work and status reports
- Manage expectations: Timeline, capacity, trade-offs
- Escalate decisions: Scope changes, priority conflicts

### With Operational Leads
- Distribute work: Deliverables broken down by unit
- Monitor progress: Daily/weekly status sync
- Resolve blockers: Clear obstacles to execution
- Coordinate resources: Team allocation and capacity

### With Quality Leads
- Define acceptance criteria: Quality standards for deliverables
- Review quality metrics: FTA, defect trends
- Triage issues: Decide on rework vs acceptance
- Drive improvement: Support quality initiatives

### With Business Analyst
- Request analysis: Ad-hoc insights and forecasts
- Leverage reports: Use data for decision-making
- Validate assumptions: Check plan viability against data
- Support planning: Capacity models, risk analytics

### With Automated Data Production
- Align SLAs: Pipeline delivery commitments
- Monitor automation health: Uptime and quality
- Coordinate manual work: Integration with automated outputs
- Report automation value: Track ROI and efficiency gains

---

## Best Practices

### Lead with Context
When using AI agents, always provide:
- **Project name/ID**: Which initiative this relates to
- **Sprint or timeline**: Current sprint number, release date
- **Stakeholders**: Who's involved (Product, Ops units, QA)
- **Priority**: Urgency and business impact
- **Dependencies**: Other projects or teams affected

### Maintain Single Source of Truth
Jira is your primary system of record:
- All deliverables tracked as tickets
- All risks logged and updated
- All dependencies linked
- All status changes reflected in real-time

Confluence supplements with narrative:
- Project charters and plans
- Status reports and retrospectives
- SOPs and process documentation

### Communicate Proactively
Don't wait for stakeholders to ask:
- Weekly status updates via Email Agent
- Real-time escalations when risks materialize
- Milestone achievements celebrated
- Blockers flagged immediately

### Balance Automation with Judgment
Let AI agents handle:
- Routine status reporting
- Data aggregation and dashboards
- Meeting scheduling and agendas
- Template-based documentation

Reserve your judgment for:
- Scope trade-off decisions
- Risk prioritization and mitigation
- Stakeholder negotiation
- Strategic direction

### Close the Feedback Loop
After every sprint/project:
- Retrospective in Confluence
- Lessons learned documented
- Process improvements identified
- Success metrics captured

Feed insights back to BA for trend analysis and future planning.

---

## Example Workflow: End-to-End Project Delivery

**Phase 1: Demand Intake**
```
Product team submits request: "Improve POI coverage in DACH region by 20%"

Using Jira Agent:
- Create project ticket with scope and success criteria
- Break down into CM tickets: Data collection, Validation, QA, Release
- Estimate effort and timeline
- Identify dependencies (tooling, data sources, training)

Create project charter in Confluence.
Share with stakeholders via Email Agent for alignment.
```

**Phase 2: Sprint Planning**
```
For Sprint 1:
- Jira Agent: Break CM tickets into OM deliverables for each Ops unit
- Workflow Agent: Create workpackages for Ops Leads to assign
- Calendar Agent: Schedule sprint planning meeting
- Analytics Agent: Pull team velocity data for capacity planning

Commit to deliverables.
Set sprint goals and acceptance criteria.
Notify team via Email Agent.
```

**Phase 3: Execution Monitoring**
```
Daily:
- Pull status from Jira and Workflow Agent
- Identify blockers and risks
- Update stakeholders if issues arise

Weekly:
- Generate status report: Confluence page + Email distribution
- Review with Ops and QA leads
- Adjust plan if needed
```

**Phase 4: Quality Validation**
```
Sprint deliverables complete → Ops submits to Quality Lead

Quality review results:
- Approved: Mark complete in Jira, close workpackages
- Rework needed: Assign back to Ops with QA feedback
- Blocked: Escalate to Product for clarification

Update sprint status and forecast.
```

**Phase 5: Closure & Retrospective**
```
Project complete:
- Measure success against original criteria
- Generate closure report in Confluence
- Document lessons learned
- Share outcomes with Product and team

Ask BA to analyze project metrics for future planning.
```

---

## Tips for Success

✅ **Think in workflows, not tasks**: "How does this ticket flow from Product → Jira → Workflow → Ops → QA → Done?"

✅ **Use dependencies**: Link related tickets so you see the full picture—"This deliverable blocks that release"

✅ **Track everything in Jira**: If it's not in Jira, it's not being tracked—no side channels or email threads

✅ **Automate status updates**: Let Reporting Agent handle weekly summaries; focus on exceptions and decisions

✅ **Escalate with data**: "Velocity dropped 30% due to 3 blockers" is better than "We're behind"

✅ **Maintain stakeholder trust**: Communicate early, communicate often, communicate honestly—bad news doesn't improve with age

✅ **Document decisions**: When you make a trade-off or change direction, log it in Confluence so future you remembers why

---

*Generated for TomTom Maps Operations AI Native Ops Model — June 2026*
