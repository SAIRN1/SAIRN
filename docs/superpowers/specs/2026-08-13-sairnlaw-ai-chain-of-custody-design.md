# SAIRNlaw — AI Chain of Custody (Phase 1)

## Problem

Over 1,000 lawyers have been sanctioned this year for AI-generated fake citations reaching real filings. No competitor's practice-management software builds automatic, matter-linked AI interaction logging with a mandatory human-verification gate natively. This feature makes every AI interaction in SAIRNlaw a real, matter-linked, tamper-resistant record, and makes "I relied on this AI output in a filing" a deliberate, attributable, reviewed act — not an assumption.

**Prior art note:** "AI Chain of Custody" was previously built, twice (Phase 1 shell + Phase 2 full wiring), but only on an orphaned branch (`origin/claude/lucid-ptolemy-b73vu0`, June 2026) with no shared git history with the current app — built against an early static-demo prototype of SAIRNlaw, not the real, current 3147-line app with its real `law_*` data model and real `sendAI()` AI pipeline. Nothing from that branch is mergeable; its rough state-machine shape (unreviewed/reviewed/rejected, a policy editor, per-matter tab, filterable log with export) informed this design as reference only.

**Verified starting state (2026-08-13):**
- `sendAI()` (`sairnlaw.html:1530`) is the single, global entry point for every AI interaction in the app — one chat panel (`#achat`/`#ainp`), not embedded per-matter. Confirmed via grep: no second AI-call site exists.
- SAIRNlaw's `law_*` resources (`law_matters`, `law_clients`, `law_trusttx`, 16 others) are **localStorage-only today** — zero entries exist in `api/sd-data.js`'s server resource allowlist; every `sdnData('write','law_*',...)` call already 400s. Confirmed by direct grep of `api/sd-data.js`, not assumed from an old backlog note.
- No "mark as used in filing" concept, or any document-linkage concept for AI output, exists anywhere in the app today.
- `sendAI()` already has a real, twice-hardened citation-fabrication mitigation (`LAW_CITATION_RULE`, `sairnlaw.html:1544-1565`) — a system-prompt-level restriction forbidding the model from ever outputting a citable-reference-format string. This feature is a different, complementary mechanism (audit/review after the fact, not prevention at generation time) — it does not replace or need to modify that existing rule.

## Scope, decided during brainstorming

- **Real server-side persistence, not client-side-only, in this pass.** "Immutable" is a real technical claim central to this feature's value (and its patent-candidate status) — building it against localStorage-only storage, then calling it immutable, would be exactly the kind of overclaim this platform's decision-gate discipline exists to catch before it ships or gets described to anyone outside the team. A new server resource (`law_ai_log`) is part of this feature's scope, not deferred.
- **Required matter picker, not optional/after-the-fact tagging.** The chat panel gains a required "Matter" dropdown (default blank/"General"); Send stays disabled until it's set for anything not explicitly general/non-matter work. An authoritative, rep-confirmed link is what makes a chain-of-custody record hold up to scrutiny — an inferred or later-corrected link is weaker evidence.
- **The filing gate is a self-contained attestation on the log entry itself**, not integrated with the existing `law_matterdocs` document-tracking resource. A status field (`unreviewed` → `reviewed`/`rejected` → optionally `used_in_filing`) where the last transition is only enabled after human review — the attorney formally attesting they verified the output before relying on it. Matches the literal scope of the request; document-system integration is real future work, not this pass.
- **Two phases.** This spec covers Phase 1 only: server schema/API, auto-logging every `sendAI()` exchange, the matter picker, a review queue (approve/reject, reject requires a reason), and the filing-gate attestation — the actual chain-of-custody mechanism, fully real and shippable on its own. Phase 2 (separate future spec, not started): an admin policy editor (configurable logging modes, matching the orphan prototype's "3 modes" reference point) and the reporting layer (per-matter AI Activity tab, platform-wide filterable log, PDF/CSV export).

## Architecture

**Server:** New Supabase table `law_ai_log`, migration written this pass (SQL file, run manually by a human in Supabase's SQL editor — this session's Claude Code environment has no DB execution access, no `SUPABASE_URL`/service key, no `psql`, no `supabase` CLI, confirmed precedent from the SAIRNdesign/SAIRNlegacy builds). Real immutability, not an honor system: the table's own row-level policy/grants permit `INSERT` and `SELECT` only for the app's role — no `UPDATE`/`DELETE` grant exists at the database level, so even a compromised or buggy API layer cannot mutate a written entry. `api/sd-data.js` gains a `law_ai_log` allowlist entry supporting `read`/`write` (insert) actions only — no `update` verb is ever wired for this resource, a second, application-layer enforcement of the same rule (belt-and-suspenders, matching this platform's established security posture — see Guardian Check 28's own incident history for why a single enforcement layer isn't trusted alone). Every read/write verifies `expectedApp==='sairnlaw'` via `verifySessionToken(token, license_hash, 'sairnlaw')`.

**Row shape:** `{id, license_hash, matter_id (nullable, 'general' sentinel or a real law_matters id), attorney_id, prompt, response, tools_used (array of tool names, not full payloads), status ('unreviewed'|'reviewed'|'rejected'|'used_in_filing'), reviewed_by, reviewed_at, reject_reason (nullable, required when status='rejected'), used_in_filing_at, created_at}`.

**Client — capture:** `sendAI()` gains one instrumentation point, firing after a full exchange completes (both the tool-use turn and the follow-up turn, if a tool was called, or just the single turn if not) — writes one `law_ai_log` entry via `sdnData('write','law_ai_log',...)`. Captures the tool NAMES used (e.g. `['getMatterDeadlines']`), not full tool-call payloads — keeps entries lean while still recording whether a given response was grounded in a real firm-data lookup or general knowledge alone.

**Client — matter picker:** New required `<select>` on the `#achat` panel, populated from `law_matters` plus a `General` option. `sendAI()`'s existing `if(!q)return;` guard gains a matching `if(!matterPicked)return;` (with a visible prompt, not a silent no-op) for anything other than `General`.

**Client — review queue:** New panel listing every `unreviewed` entry (newest first), each showing prompt/response/matter/attorney/timestamp, with Approve and Reject actions. Reject opens a required short-text reason field before it commits.

**Client — filing gate:** A "Mark Used in Filing" action, rendered only on `reviewed` entries (never `unreviewed`/`rejected` — those don't show the button at all, not just a disabled one, so there's no confusing half-available state).

## Explicitly out of scope for this pass

- Admin policy editor (configurable logging modes) — Phase 2.
- Per-matter AI Activity tab, platform-wide filterable log, PDF/CSV export — Phase 2.
- Any integration with `law_matterdocs` (document tracking) — the filing gate is a standalone attestation, not a document-system block.
- Any change to `LAW_CITATION_RULE` or the existing citation-fabrication mitigation — this feature is additive/complementary, not a replacement.
- Retroactively logging any AI interaction that happened before this feature ships — no historical backfill.
- Any actual DB migration execution — the SQL is written and handed to a human to run, per this environment's confirmed lack of DB execution access.

## Edge cases

- **A rep tries to Send with no matter selected** (and it isn't "General"): blocked with a visible message, not a silent no-op — matches this platform's own repeatedly-learned lesson about silent-failure UX.
- **The server write fails** (network error, quota, auth issue): the AI response still displays to the rep in `#achat` (the conversation itself must not break because logging failed) — but the failure is surfaced honestly (a toast, not a false "logged" confirmation), matching the platform's established `saveOk`-style pattern rather than an empty `catch(e){}`.
- **A rejected entry**: cannot proceed to `used_in_filing` under any path — the UI never renders that action for a non-`reviewed` status, and the server route independently validates the same transition rule (never trust the UI alone to enforce a state machine).
- **General-matter entries**: still logged and still reviewable, just without a real matter link — legitimate (a general drafting-help question isn't matter-specific), not treated as an error state.

## Testing / verification plan

Real DB-backed verification, not localStorage simulation: after the human runs the migration, live-test a real `sendAI()` exchange, confirm the row lands in `law_ai_log` via a direct Supabase read, confirm a second SAIRNlaw license/session cannot read another license's entries (the `expectedApp`/license-scoping check, tested the same way the platform's own prior cross-app-collision incident was caught — don't just trust the code, verify live), confirm `UPDATE`/`DELETE` against the table genuinely fail at the database level (not just "the UI doesn't expose a button"), confirm the reject-reason requirement, confirm the filing-gate action is absent (not just disabled) on `unreviewed`/`rejected` entries, and confirm a Send with no matter selected is blocked with a real message.
