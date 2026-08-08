# Roadmap — from Phase 0 to a CALL → AGENT → TEAM → ORGANIZATION product

**Target scenario:** ~100 sales agents, 10 teams of ~10, 10 managers, one
organization. Every call attributed to a lead. Conversion measured at both
call level and lead level, in a shape a real CRM would recognize.

**Where this repo actually is today, honestly:** a working Phase 0 pipeline
(F1–F4 + score/sentiment/objections/compliance/coaching per call) plus an
Agent-level rollup layer added on top. That's CALL and AGENT. TEAM and
ORGANIZATION don't exist — there's no team/manager/org concept at all.
Leads don't exist either — a call is attributed to a free-text agent name
and, optionally, a manually-tagged outcome on that one call. Nothing here
is "finished" at 100-agent scale yet; this document is the gap, broken into
shippable phases.

---

## The one blocker that isn't a code task

**The Gemini free tier caps out at 20 requests/day, total, for the whole
API key.** At 100 agents doing even 10 calls a day each, that's ~1,000
extraction calls needed daily — roughly 50x the free tier's entire daily
allowance. Every phase below assumes a paid Gemini tier (or a
self-hosted/open-weight alternative) is in place before "100 agents" is
anything but a demo with synthetic data. This is a budget/procurement line
item, not an engineering one, and it blocks Phase 3 in practice even though
it doesn't block the code.

---

## Phase A — Identity & lead data model (foundation)

Nothing below this is buildable without it: TEAM and ORGANIZATION rollups
need a real roster, and lead-level conversion needs a lead entity that
outlives any single call.

| # | Line item | Why | Size |
|---|---|---|---|
| A1 | `Organization` / `Team` / `Agent` roster entities, replacing free-text `agent_name` | An org has 10 teams of ~10 agents under 10 managers — that's structure, not a string field. `Team.manager_id`, `Agent.team_id`. | M |
| A2 | `Lead` entity: `lead_id`, contact reference, source, `assigned_agent_id`, current stage, created_at | A lead gets called multiple times before it converts. Right now each call's manual outcome tag *is* the only outcome record — there's no entity for "this prospect" that outlives one call. | M |
| A3 | Lead stage history (audit log: stage, changed_by, changed_at) | Conversion analytics needs "when did this lead reach won," not just "what's the latest tag." Also the only way to catch/audit a manager overwriting an outcome. | S |
| A4 | `CallRecord.lead_id` (required) + `CallRecord.agent_id` (FK, not free text) | Every call attributed to a lead — this is explicitly what was asked for. | S |
| A5 | Move `CallOutcome` from call-level to lead-level | A lead with 5 calls before winning is **one** conversion, not a coin-flip over which call "owns" the won tag. Current call-level `outcome` field gets deprecated in favor of `Lead.stage`. | M |
| A6 | Migration path for existing filesystem data (backfill agent roster + synthetic leads from history) | Don't discard the calls already in `server/data/`. | S |

**Open question to settle before A2:** does a lead map 1:1 to a phone
number, or can the same person have multiple leads (e.g., re-engaging after
6 months)? Real CRMs disagree on this; needs a decision, not a guess.

---

## Phase B — Team & Organization rollups (the hierarchy itself)

Directly extends the pattern `app/agent_performance.py` already
established — same math, one and two levels up.

| # | Line item | Why | Size |
|---|---|---|---|
| B1 | `app/team_performance.py` — aggregate a manager's ~10 agents' rollups into one team report, with agent-vs-agent leaderboard inside the team | This is the "TEAM" layer. Reuses `AgentPerformanceReport` math, doesn't reinvent it. | M |
| B2 | `app/org_performance.py` — aggregate all 10 teams into one org report, with team-vs-team leaderboard | This is the "ORGANIZATION" layer — "what's affecting sales performance across the business" (the analytics doc's own section 23 framing, which this repo already quoted when it built the agent layer). | M |
| B3 | `GET /api/teams`, `GET /api/teams/{id}/performance`, `GET /api/organization/performance` | API surface for B1/B2. | S |
| B4 | Drill-down navigation: Org dashboard → click a team → Team dashboard → click an agent → Agent dashboard → click a call → Call detail | The hierarchy should be *navigable*, not four disconnected pages. This is the actual "CALL → AGENT → TEAM → ORGANIZATION" ask. | M |
| B5 | Team/org dashboards reuse the agent dashboard's panel components (score breakdown, funnel, sentiment, etc.) at the aggregate level | Consistency, and avoids rebuilding 7 panel components 3 more times. | M |

---

## Phase C — CRM-grade lead & conversion metrics

This is where "conversion suitable for CRM" actually gets built — the
current agent-performance conversion numbers are a call-level proxy
(`won-tagged calls / calls analyzed`), not a real lead funnel.

| # | Line item | Why | Size |
|---|---|---|---|
| C1 | **Lead-level conversion rate**: distinct leads reaching WON ÷ distinct leads created (or qualified) in period | The doc-correct definition. Today's number can overcount or undercount depending on how many calls a lead took. | S (after Phase A) |
| C2 | **Call-level conversion context**: calls-per-lead distribution, avg calls-to-close, avg days-to-close | "How many touches does it take" — a real sales-ops question this repo can't currently answer at all. | M |
| C3 | Lost-reason taxonomy on `Lead` (not free text) + lost-reason breakdown in reports | Doc section 17 ("reasons customers reject the product") — currently nothing captures *why* a lead was lost. | S |
| C4 | Lead source/channel field + conversion-by-source breakdown | Needed to answer "which lead source converts" — table stakes for a CRM-adjacent tool. | S |
| C5 | Lead pipeline view (Kanban: untagged → qualified → demo → proposal → won/lost) | Replaces the current single-call dropdown outcome form with something that reads like a CRM, not a survey field. | L |
| C6 | Lead detail page: full call history + stage-change audit trail + reassignment history | The "one lead, many calls" view — currently there is no way to see a lead's whole story in one place. | M |
| C7 | Reconcile agent/team/org rollups to consume lead-level conversion (Phase C1), not the call-level outcome tag they use today | Keeps the numbers internally consistent bottom-to-top instead of two different "conversion rate" definitions coexisting. | M |

---

## Phase D — Storage & scale (Postgres migration)

Filesystem JSON with a full-directory glob scan on every request is a
Phase 0 decision that was correct for 6 mock calls and is wrong for
~100 agents generating ongoing call volume — this was flagged as a
scope-discipline choice in the PRD (section 8) for a *handful* of design
partners, not this scenario.

| # | Line item | Why | Size |
|---|---|---|---|
| D1 | Postgres schema for Organization/Team/Agent/Lead/Call (+ migrations, Alembic) | Relational joins (team → agents → calls → leads) are what this data actually is; a document store per call stops making sense once you need "all calls for team X in date range Y." | L |
| D2 | Replace `storage.list_all()` full-scan with indexed queries (by agent, team, date range, lead) | At 100 agents × ~20 calls/day, that's ~2,000 records/day, ~60k/month — a full-directory scan per dashboard load degrades fast. | M |
| D3 | Materialized/cached rollups (recomputed on a schedule or on-write, not live full-scan on every dashboard load) | Org-level aggregation over 60k+ calls/month should not be O(n) on every page view. | M |
| D4 | Background job queue for the ASR+extraction pipeline (replace in-process `BackgroundTasks`), with retry/backoff and concurrency matched to the LLM provider's rate limits | `BackgroundTasks` has no persistence across restarts and no retry — fine for a demo, not for 1,000+ calls/day feeding a rate-limited API. | M |

---

## Phase E — Access control

A product with 10 managers who each own a team needs actual scoping, not
"everyone sees everything" (today's state).

| # | Line item | Why | Size |
|---|---|---|---|
| E1 | Auth (login) | There is currently none. | M |
| E2 | Roles: Agent (own calls only), Manager (own team), Org Admin (everything) | Matches the org structure from Phase A. | M |
| E3 | Scope every API route by role | Otherwise E1/E2 are decorative. | M |

*Multi-tenant SaaS (multiple separate orgs on shared infra) is explicitly
further out — this phase is single-org role scoping, matching the PRD's
one-brokerage-per-deployment ICP. Don't build multi-tenant auth unless the
business model actually needs it.*

---

## Phase F — Productionization polish

| # | Line item | Why | Size |
|---|---|---|---|
| F1 | Alerts (analytics doc section 27: high-value objection, poor closing, compliance risk, competitor spike) | Currently nothing pushes anything — a manager has to open the dashboard to find out. | M |
| F2 | Exportable reports (CSV/PDF) for team/org dashboards | Managers reporting up to execs need something to attach to an email. | S |
| F3 | Paid-tier Gemini (or self-hosted alternative) usage, with cost monitoring | See the blocker at the top — this is a prerequisite for Phase 3+ operating for real, not a nice-to-have. | — (procurement) |
| F4 | ASR path validated at volume; re-confirm the faster-whisper-vs-Deepgram cost crossover from PRD section 7 against real 100-agent volume | PRD section 7 already flags ~20,000 calls/month as the point self-hosting starts winning — 100 agents × 20 calls/day × 22 days ≈ 44,000 calls/month is past that line, so this isn't hypothetical. | S |

---

## Suggested sequencing

Phase A blocks B and C outright (no team/org rollups without a roster, no
lead conversion without leads). D can start in parallel with A once the
schema is drafted, since migrating storage doesn't depend on the
aggregation logic being finished. E can happen any time after A (roles need
the roster). F is genuinely last — it's polish on top of a system that
needs to already work.

```
A (identity + leads)
├─▶ B (team + org rollups)
├─▶ C (CRM-grade lead metrics)
└─▶ E (access control)
A ─▶ D (storage/scale, can start once A's schema is drafted)
B, C, D, E ─▶ F (polish)
```

**Recommended first slice:** A1–A5 + C1 (lead entity, roster, lead-level
conversion) — the smallest change that makes "conversion suitable for CRM"
literally true, and unblocks everything else. Team/org rollups (B) are the
next highest-leverage step once that lands, since they're a direct
extension of code that already exists and works.
