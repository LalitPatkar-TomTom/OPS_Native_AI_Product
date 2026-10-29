# Architecture decision records: OPS Native AI

Each record covers one decision: the context, what was decided, the consequences, and when to revisit
it. The decisions about the chat app (sign-in, MCP, LLM hosting) are in the OPSHUB repository
(`docs/adr/`). MCP-first applies to both products and is recorded there as ADR-002.

| # | Decision | Status |
|---|---|---|
| [001](001-deterministic-engine.md) | Deterministic engine: no LLM in the decision or send path | Accepted |
| [002](002-scheduled-job.md) | Azure Container Apps job on 4 IST slots: one run at a time, no automatic retry | Accepted |
| [003](003-owner-only-delivery.md) | Owner-only delivery through Microsoft Graph from a shared mailbox | Accepted |
| [004](004-profiles-as-configuration.md) | A personal SKILL.md profile per user is the configuration | Accepted |
| [005](005-sqlite-analytics.md) | Analytics in SQLite, copied in and out of the share for each run | Accepted, revisit before scale-out |
| [006](006-time-saved-criteria.md) | Time saved as fixed minutes per item, agreed and versioned | Accepted |
| [007](007-reported-week.md) | Which week each email reports, and when alerts trust this week | Accepted |
| [008](008-root-cause-driver-trees.md) | Root causes and actions as rule-based driver trees | Accepted |
