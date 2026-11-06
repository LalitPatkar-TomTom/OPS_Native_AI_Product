# ADR-012: Every Jira key in a profile is checked

**Status:** Accepted · **Date:** 6 Nov 2026 · **Issue:** OSI-061 (reported by a project manager with OM and MCPET)

## Context
Since ADR-010 the Jira key comes from the profile's "Jira Key" column, but only the first Active row with a valid
key was used, and UC2 searched `project = KEY`. A manager with tickets in two projects had the second project
silently unchecked, and nothing said so.

## Decision
- `jira_projects` = the distinct keys of the Active rows of the "Jira Key" column, in table order. `jira_project`
  stays the first key (create-ticket links, old callers, logs).
- One search for all keys: `project in (K1, K2, ...)`; one key keeps the exact JQL it always had.
- With several keys each key is looked up first by the run's own route (MCP, then REST). A missing key is named in
  every email that shows Jira and logged as a WARNING; the other keys are still checked. Only when every key is
  missing does the run report "Jira not checked", as for one wrong key today. A lookup that cannot answer (Jira
  down) keeps the key, so an outage shows up as a failed search, not as a missing project.
- Profiles without a "Jira Key" column (before 3 Nov 2026) keep one key: their "Code" column mixes project codes
  that are not Jira projects (GDN, TMC, PCD), and taking all of them would flood users with "not found" warnings.

## Consequences
- One extra lookup per key per run, only for profiles with several keys.
- Labels read "OM, MCPET"; single-key emails are unchanged.
- Users who want more projects checked add a row per project with its Jira key in the profile form.
