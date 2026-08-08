# Roadmap — from Phase 0 to a CALL → AGENT → TEAM → ORGANIZATION product

**Target scenario:** ~100 sales agents, 10 teams of ~10, 10 managers, one
organization. Every call attributed to a lead. Conversion measured at both
call level and lead level, in a shape a real CRM would recognize.

**Where this repo actually is today, honestly (updated 2026-08-08):** a
working Phase 0 pipeline (F1–F4 + score/sentiment/objections/compliance/
coaching per call), a real roster (Team/Agent) and Lead entity (Phase A),
lead-level conversion (C1), and now Team and Organization rollups (Phase
B) on top of the same aggregation engine the Agent layer already used.
CALL, AGENT, TEAM, and ORGANIZATION are all real, navigable levels now —
Organization → Team → Agent is one tab with click-to-drill-down rows, and
Agent → Call was already there. Nothing here is "finished" at 100-agent
scale yet (see Phase D for the storage/scale gap); this document is the
gap, broken into shippable phases.

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

**Partial mitigation shipped (2026-08-08): Groq as an opt-in extraction
provider** (`EXTRACTION_PROVIDER=groq`) — see README.md "Groq extraction"
for the full writeup. It moves the daily-quota wall much higher without
attaching billing, at the cost of open-weight (Llama) extraction quality
instead of Gemini's — not yet precision-measured, and not a substitute for
F3 (paid-tier usage with real cost monitoring) once actual production
volume is in play.

---

## Phase A — Identity & lead data model (foundation)

**Status: A1–A6 done.** A6 was first marked "skipped, turned out
unnecessary" because `server/data/calls/` was empty in the dev sandbox
when A1–A5 shipped — that assumption broke almost immediately in a real
deployment with real historical calls (`GET /api/calls` 500ing with
`agent_id`/`lead_id` "Field required" on every pre-Phase-A record). Fixed
same-day: see the A6 row below.

Nothing below this is buildable without it: TEAM and ORGANIZATION rollups
need a real roster, and lead-level conversion needs a lead entity that
outlives any single call.

| # | Line item | Why | Size | Status |
|---|---|---|---|---|
| A1 | `Team` / `Agent` roster entities, replacing free-text `agent_name` | An org has 10 teams of ~10 agents under 10 managers — that's structure, not a string field. `Team.manager_agent_id`, `Agent.team_id`. | M | **Done** — no `Organization` entity built; nothing needs one until Phase B |
| A2 | `Lead` entity: `lead_id`, contact reference, source, `assigned_agent_id`, current stage, created_at | A lead gets called multiple times before it converts. Right now each call's manual outcome tag *is* the only outcome record — there's no entity for "this prospect" that outlives one call. | M | **Done** |
| A3 | Lead stage history (audit log: stage, changed_by, changed_at) | Conversion analytics needs "when did this lead reach won," not just "what's the latest tag." Also the only way to catch/audit a manager overwriting an outcome. | S | **Done** — `changed_by` is optional free text for now; real attribution needs Phase E auth |
| A4 | `CallRecord.lead_id` (required) + `CallRecord.agent_id` (FK, not free text) | Every call attributed to a lead — this is explicitly what was asked for. | S | **Done**, revised same day — `agent_id` is still validated against the roster (400 if unknown), but `lead_id` turned out better as auto-provisioned than gatekept: `lead_storage.get_or_create` makes any caller-chosen id a real `Lead` on first use rather than requiring `POST /api/leads` first. See README "Roster & leads" addendum. |
| A5 | Move `CallOutcome` from call-level to lead-level | A lead with 5 calls before winning is **one** conversion, not a coin-flip over which call "owns" the won tag. Current call-level `outcome` field gets deprecated in favor of `Lead.stage`. | M | **Done** — `POST /api/calls/{id}/outcome` removed, replaced by `POST /api/leads/{id}/stage` |
| A6 | Migration path for existing filesystem data (backfill agent roster + synthetic leads from history) | Don't discard the calls already in `server/data/`. | S | **Done** — `server/scripts/migrate_legacy_calls.py`. Also hardened `storage.list_all()` to skip (not crash on) any record it can't validate, logging which file and pointing at the migration script — one bad or pre-migration record no longer takes down `GET /api/calls` for everyone. |

**Decided rather than left open:** a lead maps 1:1 to whatever the manager
decides to create via `POST /api/leads` — the app doesn't enforce phone
number as a dedup key, so re-engaging the same person as a second Lead is
possible and not prevented. That's a real gap (nothing stops accidental
duplicate leads for the same prospect), noted rather than solved — dedup-
by-phone would be a reasonable Phase C addition once C5's lead UI exists to
surface "did you mean this existing lead" at creation time.

**Two things shipped beyond the original A1–A5 scope, because they fell out
of the roster naturally:**
- **Team benchmarks now compare against real teammates**, not "every other
  agent in the org." `agent_performance.py`'s team-benchmark logic used to
  treat every other agent as a stand-in for "team" because no real Team
  concept existed; now that one does, an agent with no team (or no
  teammates with data yet) gets an explicit note instead of a number
  quietly computed from the wrong population.
- **Upload/outcome UX**: `UploadPanel` now has a real roster dropdown
  (`agent_id`) instead of free text, and `CallDetail`'s outcome control
  became `LeadPanel`, which edits the lead's stage while reviewing any of
  its calls.

---

## Phase B — Team & Organization rollups (the hierarchy itself)

**Status: done (2026-08-08).** Directly extended the pattern
`app/agent_performance.py` already established — same math, one and two
levels up, via a new population-agnostic shared engine
(`app/performance_metrics.py`) that `agent_performance.py`,
`team_performance.py`, and `org_performance.py` all call with a
pre-filtered slice of calls. Verified with 25 new backend tests (the
shared engine directly, team pooling/leaderboard/benchmark isolation, org
pooling/leaderboard, and the two new router endpoints — 133 passing total)
plus a live browser pass: real seeded roster (10 teams/100 agents), two
synthetic calls on two different teams, a lead tagged to WON, and the full
Organization → Team → Agent click-through confirmed in a running
frontend, including a real bug caught and fixed in that pass (see below).

| # | Line item | Why | Size | Status |
|---|---|---|---|---|
| B1 | `app/team_performance.py` — aggregate a manager's ~10 agents' rollups into one team report, with agent-vs-agent leaderboard inside the team | This is the "TEAM" layer. Reuses `AgentPerformanceReport` math, doesn't reinvent it. | M | **Done** |
| B2 | `app/org_performance.py` — aggregate all 10 teams into one org report, with team-vs-team leaderboard | This is the "ORGANIZATION" layer — "what's affecting sales performance across the business" (the analytics doc's own section 23 framing, which this repo already quoted when it built the agent layer). | M | **Done** |
| B3 | `GET /api/teams/{id}/performance`, `GET /api/organization/performance` | API surface for B1/B2. (`GET /api/teams` already existed from Phase A.) | S | **Done** |
| B4 | Drill-down navigation: Org dashboard → click a team → Team dashboard → click an agent → Agent dashboard → click a call → Call detail | The hierarchy should be *navigable*, not four disconnected pages. This is the actual "CALL → AGENT → TEAM → ORGANIZATION" ask. | M | **Done** — one Organization tab with in-place team drill-down (leaderboard row click), handing off to the existing Agent Performance tab (agent row click) pre-selected to that agent; Agent → Call was already navigable via the Calls tab. |
| B5 | Team/org dashboards reuse the agent dashboard's panel components (score breakdown, funnel, sentiment, etc.) at the aggregate level | Consistency, and avoids rebuilding 7 panel components 3 more times. | M | **Done** — all 7 panels genericized with optional `title`/`benchmarkTitle` props (defaults unchanged, so the Agent Performance tab needed no changes) and reused as-is by the new `OrganizationPage`; only a new `LeaderboardPanel` component was net-new. |

**Bug caught during live verification, not by tests:** switching levels
(org → team, or team → org) triggers a React re-render with the *new*
`teamId` but the *old*, differently-shaped report (`agent_leaderboard` vs.
`team_leaderboard`) before the refetch lands — `LeaderboardPanel` crashed
reading `.length` off the wrong field, taking down the whole page. Fixed
by setting `loading` synchronously in the same click handler that changes
`teamId`, so that inconsistent-shape render never happens
(`frontend/src/components/OrganizationPage.js`'s `selectTeam`). None of
the 133 backend tests could
have caught this — it's a frontend state-sequencing bug — which is exactly
why this phase's browser pass drove the actual click-through instead of
just checking the API responses.

---

## Phase C — CRM-grade lead & conversion metrics

**Status: C1 and C5 done (2026-08-08). C1 was reconciled directly into the
rollup rather than left as a parallel number (that covers what C7 asked for
too — see below). C2–C4 and C6 still open.**

This is where "conversion suitable for CRM" actually gets built — the
old agent-performance conversion numbers were a call-level proxy
(`won-tagged calls / calls analyzed`), not a real lead funnel.

| # | Line item | Why | Size | Status |
|---|---|---|---|---|
| C1 | **Lead-level conversion rate**: distinct leads reaching WON ÷ distinct leads touched in period | The doc-correct definition. The old number could overcount or undercount depending on how many calls a lead took. | S (after Phase A) | **Done** — with a real correctness property tests actually check: a lead currently *sitting* at "won" only counts toward `conversion_rate_pct` if its `stage_history` shows it *transitioning* to won inside the queried period, not merely being won by the time someone looks. A lead that converted in June doesn't retroactively inflate August's number. |
| C2 | **Call-level conversion context**: calls-per-lead distribution, avg calls-to-close, avg days-to-close | "How many touches does it take" — a real sales-ops question this repo can't currently answer at all. | M | Open |
| C3 | Lost-reason taxonomy on `Lead` (not free text) + lost-reason breakdown in reports | Doc section 17 ("reasons customers reject the product") — currently nothing captures *why* a lead was lost. | S |
| C4 | Lead source/channel field + conversion-by-source breakdown | Needed to answer "which lead source converts" — table stakes for a CRM-adjacent tool. | S |
| C5 | Lead pipeline view (Kanban: untagged → qualified → demo → proposal → won/lost) | Replaces the current single-call dropdown outcome form with something that reads like a CRM, not a survey field. | L | **Done** — required no backend changes at all: `GET /api/leads` (with `assigned_agent_id`/`stage`/`q` filters) and `POST /api/leads/{id}/stage` already covered everything the board needs, since the backend places no restriction on which stage a lead can move to from which. New `LeadPipelinePage`/`LeadCard` components: drag-and-drop between columns as the primary interaction, plus prev/next arrow buttons on every card as a keyboard/touch-accessible fallback that writes through the same code path, not a separate one. Dropping (or arrow-moving) a lead into Won without an existing deal size opens a small inline modal to capture it (skippable) rather than silently leaving revenue unset. |
| C6 | Lead detail page: full call history + stage-change audit trail + reassignment history | The "one lead, many calls" view — currently there is no way to see a lead's whole story in one place. | M |
| C7 | Reconcile agent/team/org rollups to consume lead-level conversion (Phase C1), not the call-level outcome tag they use today | Keeps the numbers internally consistent bottom-to-top instead of two different "conversion rate" definitions coexisting. | M | **Done as part of C1** — `agent_performance.py`'s `ConversionAgg` and `ClosingAgg` were rewritten together, not layered; `ClosingAgg` deliberately stayed a current-stage *snapshot* (distinct from `ConversionAgg`'s period-scoped transition count) rather than being collapsed into one number, since they answer different questions — see both classes' docstrings in `schemas.py`. |

**C5 verification.** No new backend tests needed — `GET /api/leads` and
`POST /api/leads/{id}/stage` were already covered by `test_leads_router.py`
from Phase A, and this feature added no new endpoints. Live-verified
instead: real leads created through the actual API across two agents on
different teams, spread across four stages including one already Won, then
driven through the actual running frontend with Playwright — dragged a
card from Untagged into Qualified, used the arrow-button fallback to move
a card from Qualified to Demo booked, dragged a card into Won (confirmed
the deal-size modal appears, filled it, confirmed the column's running
total updated correctly to the sum of both Won deals), and confirmed the
agent filter and name/phone search both narrow the board correctly — zero
console errors throughout. Seeded leads cleaned out of `server/data/`
afterward, same discipline as every other live pass in this document.

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

**First slice shipped (2026-08-08):** A1–A5 + C1 (lead entity, roster,
lead-level conversion) — verified with 42 new/updated backend tests
(roster storage, lead storage, the rewritten aggregation module, and the
new roster/lead routers) plus a live browser pass: real teams, agents, and
leads created through the actual API, calls attributed to them, and the
Agent Performance dashboard confirmed showing genuinely different
teammate-only benchmarks for two agents on different teams.

**Second slice shipped (2026-08-08):** Phase B (Team & Org rollups) — the
direct extension of `agent_performance.py` deferred so the Phase A
foundation could land first. See the Phase B section above for the full
verification writeup.

**Third slice shipped (2026-08-08):** C5 (Kanban lead pipeline), taken out
of its originally-suggested order (after C2–C4/C6) at explicit request,
since it's the most visibly CRM-like piece and needed zero backend changes
to build. See the Phase C section above for the full verification writeup.
**Next up: C2, C3, C4, C6** (call-level conversion context, lost-reason
taxonomy, lead source/channel, and the lead detail page) — the remaining
Phase C line items, none of which block each other or C5.
