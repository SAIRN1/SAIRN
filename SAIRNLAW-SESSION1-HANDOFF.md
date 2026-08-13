# SAIRNLAW — Session 1 Handoff

Written 2026-08-13. First SAIRNlaw-specific session handoff in this
repo — no prior `SAIRNLAW-SESSION-N-HANDOFF.md` series exists (confirmed
by directory search before choosing this filename, per this project's own
per-app-prefix naming convention). Claims below are independently
re-verified against the actual repo and live site, not carried forward
from any earlier report.

## 1. Verified current state

- `origin/main` HEAD: `536535e` — confirmed via `git ls-remote origin main`.
- Live site (`sairn.vercel.app/sairnlaw`) content hash matches HEAD's
  `sairnlaw.html` exactly (SHA-256, CRLF-normalized, matched 15s
  post-push). `api/law-auth.js` smoke-tested live with an unauthenticated
  request — clean `401 NO_LICENSE` response, confirming the deploy
  succeeded and the new code didn't break the endpoint.
- `node --check` clean on `api/law-auth.js` and `api/_lib/audit.js`.
  `python tools/checkblocks.py sairnlaw.html`: `TOTAL_BLOCKS:1`,
  `FAILED_BLOCKS:0`.
- **The SQL migration has NOT been run.** `sql/sairnlaw_ai_chain_of_custody.sql`
  is written and committed but requires a human to run it in Supabase's
  SQL editor (this session's environment has no `SUPABASE_URL`/service
  key, no `psql`, no `supabase` CLI — confirmed precedent from every
  other SAIRN app's server-schema build this platform has done). See
  Section 4, item 1 — this is the single most important open item.

## 2. What shipped: SAIRNlaw AI Chain of Custody (Phase 1)

Every AI interaction in SAIRNlaw (`sendAI()`) is now logged as a real,
server-side, database-immutable, matter-linked audit record, with a
mandatory human-verification gate (Owner/Attorney only, `paralegal`
blocked) before any AI output can be attested as "used in a filing."
Answers a real, current, quantified crisis: 1,000+ lawyers sanctioned
this year for AI-generated fake citations reaching real filings.

Full cycle: brainstorm (5 real design questions, including discovering
and ruling on a prior orphaned/abandoned attempt at this same feature
name on a disconnected branch — see Section 3) → spec → implementation
plan → subagent-driven-development (6 tasks) → final whole-branch review
→ fix wave → push → live-verify.

**Architecture, notably NOT what the design spec originally called for:**
found during planning that `sql/sairnlaw_audit_log_schema.sql` and
`api/law-auth.js`'s existing `audit_read` action (built 2026-08-08,
already live) already implement exactly the real, database-enforced
immutable audit log this feature needed. Building a new `law_ai_log`
table and a new API file — the spec's literal wording — would have
duplicated that infrastructure rather than adding to it. This plan
instead extends the existing table (4 new event types) and the existing
endpoint (5 new actions), reusing its already-audited `writeAuditLog()`
helper, license/session verification, and PostgREST plumbing verbatim.
Disclosed explicitly in the plan's Global Constraints, not silently
substituted for the spec.

## 3. What was CORRECTED, not just added

- **A real prior attempt at this exact feature was found and ruled on
  before design work started.** Git history showed "AI Chain of Custody
  Phase 1/2" commits from June 17, 2026 — but on a branch
  (`origin/claude/lucid-ptolemy-b73vu0`) with no shared git history with
  `origin/main`, built against a static-demo prototype of SAIRNlaw with
  hardcoded fake data and no real data layer. Nothing from it was
  mergeable. Per the user's explicit direction, its rough state-machine
  shape (unreviewed/reviewed/rejected, a gate-banner pattern, a policy
  editor, per-matter tab with export) was used as design inspiration
  only — zero code carried over.
- **Task 3's per-task review caught a real Critical bug in the plan's own
  code**, not an implementer deviation: `aiCurrentStatus()` (the function
  deciding whether a review/reject/mark-used-in-filing transition is
  currently valid) originally queried the 200 most-recent status-change
  events for the WHOLE license and filtered client-side for the target
  entry. Under realistic volume, an older entry's real status event could
  age out of that shared window and misread as `unreviewed` — letting a
  previously-rejected entry proceed all the way to `used_in_filing`. Fixed
  to a real database-level `detail->>log_entry_id=eq.` filter, scoped to
  exactly one entry, immune to license-wide volume.
- **The final whole-branch review caught a Critical bug invisible to every
  per-task review**, spanning two files: `writeAuditLog()`
  (`api/_lib/audit.js`) never checked whether its write actually
  succeeded — it always resolved as if it had. Every AI action
  (`ai_log`/`ai_review`/`ai_reject`/`ai_used_in_filing`) then
  unconditionally responded `{ok:true}` regardless of whether a row was
  actually written. Concretely: until the migration runs (see Section 1),
  every one of these actions WILL fail to write — and before this fix,
  would have silently told the client it succeeded. An attorney clicking
  "Mark Used in Filing" would have seen "Marked used in filing" with
  nothing in the record. Fixed: `writeAuditLog()` now returns a real
  `true`/`false`; all four AI actions check it and respond with a real
  502 `LOG_WRITE_FAILED` error on failure instead of a false `{ok:true}`.
  Existing non-AI callers (login/MFA/citator events, which intentionally
  want best-effort logging that never blocks the real action) are
  unaffected — confirmed all 16 of them still ignore the return value.
  **Practical consequence right now:** until the migration runs, the
  feature will visibly, honestly NOT work (a clear error) rather than
  silently seem to work while doing nothing — this fix is exactly what
  makes today's not-yet-migrated state safe to have shipped ahead of the
  migration, rather than dangerous.
- Same final review also fixed: a privileged-text leak (the pre-existing,
  unrelated general Security & Audit page's `audit_read` action had no
  event-type filter, so it would have started returning raw AI
  prompt/response text — potentially privileged client-matter content —
  once `ai_log` began writing rows); an unguarded null-dereference that
  could 502 the entire review queue on one malformed row; matter
  attribution captured at the wrong time (after the AI round-trip
  resolved, not when the request was actually sent — a rep changing the
  matter dropdown mid-generation would have silently misattributed the
  record); an unbounded `ai_list` response with no truncation or
  completeness disclosure (~8MB worst case against Vercel's ~4.5MB
  ceiling); one undefined CSS variable (silently losing the "Reviewed"
  badge's color); one variable-name shadowing a global function; one SQL
  comment overclaiming a correction/reopen capability that doesn't
  actually exist in the shipped state machine.
- Two honest, disclosed gaps between the feature's framing and what's
  actually delivered — NOT fixed this pass, logged to `SAIRN-BACKLOG.md`
  with full reasoning: (1) AI-interaction capture is client-reported
  (browser calls the AI proxy, then separately and un-atomically calls
  the log endpoint) — not server/proxy-observed; a closed tab or a
  blocked second request produces an unlogged interaction. (2)
  `matter_id` is an unvalidated localStorage id — SAIRNlaw's `law_matters`
  isn't server-backed yet (same platform-wide gap already tracked for
  `law_trusttx` and 17 other resources), so the server can't verify a
  submitted matter link is real.

## 4. Open items, prioritized

1. **Run `sql/sairnlaw_ai_chain_of_custody.sql` in Supabase's SQL editor.**
   Nothing in this feature can actually write a row until this happens —
   every AI action will return a real, honest `502 LOG_WRITE_FAILED`
   until then (safe, not silent — see Section 3). This is the single
   blocking step before any live functional verification is possible.
2. **After the migration runs, complete the DB-backed verification this
   session's environment could not perform** (no Supabase execution
   access): confirm a real `sendAI()` exchange writes a row; confirm
   license-hash scoping (a second license cannot read the first's
   entries); confirm `UPDATE`/`DELETE` against `sairnlaw_audit_log`
   genuinely fail at the database level, not just "the UI has no button"
   for it; confirm the full `unreviewed → reviewed → used_in_filing` and
   `unreviewed → rejected` flows end-to-end through the real UI with a
   real Owner/Attorney session; confirm a `paralegal` session gets 403
   from every review-workflow action.
3. Two real, disclosed gaps in `SAIRN-BACKLOG.md` (Section 3, last
   bullet) — client-reported capture, unvalidated matter linkage — both
   explicitly Phase 2 scope, not oversights.
4. Phase 2 (separate future spec, not started): admin policy editor
   (configurable logging modes), per-matter AI Activity tab,
   platform-wide filterable log, PDF/CSV export.
5. Three accepted, documented nits in `SAIRN-BACKLOG.md`: `ai_list`'s
   status-derivation staleness under high license-wide volume (safe by a
   real newest-first-prefix argument, not just asserted); native
   `prompt()` for reject reasons (only one in the file); no volume cap on
   `ai_log`.
6. This plan's SDD workspace
   (`.superpowers/sdd/2026-08-13-sairnlaw-ai-chain-of-custody/`) should
   be cleaned up per `subagent-driven-development`'s Finish step.
7. Worktree branch (`worktree-stonedesk-chamfered-corners`) has now
   carried StoneDesk features across five generations plus this SAIRNlaw
   feature — same open naming-drift item carried from prior sessions,
   still not acted on. Given this session crossed apps, consider whether
   a fresh, correctly-named worktree makes sense for whichever app is
   touched next.

## 5. Standard verification reminder for whoever reads this next

Verify `origin/main` HEAD, the live site's hash (normalizing line endings
before comparing), and — critically for this feature specifically —
whether the SQL migration has actually been run yet, before trusting any
claim about this feature actually working end-to-end. Everything in this
document is honest about that gate not yet being cleared; don't let a
future summary silently drop that caveat.
