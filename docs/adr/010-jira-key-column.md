# ADR-010: The Jira key is read from the profile's "Jira Key" column

**Status:** Accepted, 3 Nov 2026. Issues OSI-001 / OSI-002. Related: OPS Hub ADR-008.

## Context
The Jira project key came from the first Active row of the profile's Active Projects table, second column
("Code"). Users filled that column with planning IDs and names, so "Geocoding", "QA" and similar were used
as Jira keys (five profiles on 2 Nov). The OPS Hub form now writes separate columns:
`| Activity / Project | Planning ID | Jira Key | Role on Project | Status |`.

## Decision
- When a table has a "Jira Key" column, the key is the first Active row's value that looks like a key
  (2–10 capitals or digits, any case typed); "—" and other values are skipped. The old pattern is not
  tried on such a table, so a planning ID is never taken for a key.
- Profiles made before keep the old reading, then "Project Keys monitored", then "Jira project key".
- Checked on all 48 profile files on the laptop: the old and new readers give the same result for every one.

## Consequences
Existing profiles behave exactly as before. A profile saved with the new form gets its key from the
column the user filled in for it, and the form has already checked that the key exists (OPS Hub ADR-008).
