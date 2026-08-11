# SAIRNdental — Session 1 Handoff

Written mid-session, stopped because Michael went to bed mid-brainstorm.
Claims below are independently verified against the actual repo (`git`
commands run directly this session), not assumed from memory.

**Naming note:** first handoff under a dedicated `SAIRNDENTAL-SESSION-N`
series (per `sairn-session-handoff`'s "per-app prefix, always" rule,
resolved 2026-07-26). Prior SAIRNdental work this same calendar session
(referral tracking, the RESOURCES-gate fix) was tracked via plan/spec
docs, not a session handoff — this is the first one for this app.

## 1. Verified current state

- `origin/main` HEAD: `4f76eda421794e90320b07b508e86eb47062c4cf` —
  confirmed via `git fetch origin main` + `git rev-parse origin/main`.
- Local HEAD matches exactly: `4f76eda421794e90320b07b508e86eb47062c4cf`.
  Nothing local is ahead or behind.
- Branch: `main`.
- Uncommitted: only `.claude/settings.json` (key-reordering + an
  `env.DISABLE_AUTOUPDATER` addition), present since before this
  session started and unrelated to SAIRNdental/the complaint feature —
  deliberately left uncommitted rather than bundled into an unrelated
  commit. No other uncommitted tracked changes.
- **No code was written or changed this session.** This was a pure
  design/brainstorm session for a new feature; nothing has been
  implemented yet.

## 2. Commits this session, in order

None. This session was 100% brainstorming (via `superpowers:brainstorming`)
for a new, not-yet-started feature. The referral-tracking feature and its
`RESOURCES`-gate fix (commits `4f76eda`, `46e0336`, `1112f99`, `67fdb2b`,
`88efcf1`) were completed and live-verified in this same conversation
*before* this handoff's session began — see the live-verification
transcript earlier in this conversation (dnt_referrals confirmed to
clear the RESOURCES gate on production, distinct from an invalid-resource
control case that still correctly 400s).

## 3. What was corrected, not just added

Nothing to correct this session — no prior claim was found to be wrong.
Note for the record: an earlier attempt this session to save brainstorm
progress via the auto-memory system (a `Write` to
`.claude/projects/.../memory/`) was rejected by Michael in favor of a
real, git-committed handoff file instead — this file is that correction
in practice, not just in instruction. Future sessions: for in-progress,
resumable design work on this project, prefer a committed
`*-HANDOFF.md` over the memory system.

## 4. Open items, prioritized

**Feature: anonymous-optional patient complaint form** (motivation: 96%
of patient complaints are about communication/service, not clinical
quality). Real scope: patient-facing form (message, optional name, no
phone/email required), routed privately to staff, must require/track a
real response from the practice owner/doctor — not a passive drop-box.

Brainstormed via `superpowers:brainstorming`, following the same
process as the just-shipped referral-tracking feature
(`docs/superpowers/specs/2026-08-11-sairndental-referral-tracking-design.md`).
**No spec file has been written yet** — brainstorming stopped before
reaching that step. Resume with `superpowers:brainstorming` next
session; do not restart the question sequence below from scratch.

**Decisions locked so far (confirmed by Michael via direct choice, not assumed):**

1. **Response delivery — thread-based, not internal-only and not
   email-based.** The owner's response posts into a conversation thread
   attached to the complaint itself. The patient sees it by returning
   via a private access-token link. This is independent of the
   email-reminder infrastructure (Resend), which isn't fully live yet
   (see `docs/superpowers/specs/2026-08-11-sairndental-email-reminders-design.md`)
   — confirmed buildable now without that dependency.
2. **Thread depth — open-ended back-and-forth**, not a single
   complaint + single response. Patient can reply after the owner
   responds; owner can reply again.
3. **Closing/reopening — owner-only close, patient-reply reopens.**
   Only the `owner` role (a real, existing PIN-gated role in
   `sairndental.html` — `DEFAULT_PINS`/`prole`/`dnt_role`, not new
   infrastructure) can mark a thread Resolved. If the patient posts
   another message on a Resolved thread, it automatically flips back to
   needing-response — prevents a thread from being closed and then
   silently ignored if the patient follows up.
4. **Visibility ("not silently ignorable" requirement) — a persistent
   nav badge count.** The "Complaints" nav entry always shows a count
   of threads currently needing an owner response. Michael explicitly
   chose this over the fuller alternative offered (a SAIRNbiz-style
   dashboard widget with aging/severity tiers, mirroring
   `checkAttentionItems()` — see
   `docs/superpowers/specs/2026-08-10-sairnbiz-attention-digest-design.md`)
   — that fuller pattern was **not** chosen; don't build it.
5. **Form fields — message + optional name only.** No optional
   "which visit/provider" field (was offered, explicitly not chosen),
   no phone/email required — matches the original request's scope
   exactly.

**Not yet resolved — the next question to ask when resuming:**

A real architectural gap was surfaced but not settled: patient replies
(via a new public, unauthenticated endpoint) and the owner's response
(via the authenticated staff app) both ultimately write to the same
thread record. Two options were presented; Michael stopped the session
("save where we are... going to bed") before picking one — **do not
assume the recommended option was implicitly chosen**:
  - (a, was recommended) Server-side read-then-append-write on both
    paths (a new small authenticated staff-response endpoint, not a
    reuse of the generic full-record-overwrite `sd-data.js` write
    path) — narrows but doesn't eliminate the race. Same accepted-risk
    class as this codebase's existing rate-limiter's documented
    read-then-write gap (`api/_lib/dental-public.js`'s own header).
  - (b) A real Postgres stored procedure for atomic array-append —
    eliminates the race, but would be the first stored procedure on
    this platform; likely over-engineering for this feature's actual
    traffic level.

**Architecture context gathered this session (valid, informal, not yet
in a written spec):**
- New resource: `dnt_complaints`, needs a real promoted `access_token`
  column (same treatment as `dnt_settings.booking_slug`) for fast
  public lookup.
- New public page, pattern-matched to `sairndental-book.html`, likely
  `sairndental-complaint.html`: `?slug=X` mode for new submissions
  (reusing the existing `dnt_settings.booking_slug`, no new per-practice
  slug needed) and `?token=Y` mode for viewing/replying to an existing
  thread.
- New unauthenticated endpoints under `api/sairndental/`, following
  `public-book.js`'s shape, reusing `checkAndIncrementRateLimit`/
  `resolveSlug` from `api/_lib/dental-public.js`.
- Staff side: new "Complaints" nav entry + panel in `sairndental.html`;
  add `dnt_complaints` to `DNT_SYNC_RESOURCES`
  (`sairndental.html:1281-1292`) and a new `RESOURCES` entry in
  `api/sd-data.js` — **double-check this new gate entry lands
  correctly**, since the identical class of bug (a resource missing
  from `api/sd-data.js`'s `RESOURCES` allowlist) was just found and
  fixed for `dnt_referrals` earlier this same session.

**After the open question is resolved:** write the design doc to
`docs/superpowers/specs/<date>-sairndental-complaint-design.md`, run
the spec self-review, get Michael's explicit approval on the written
spec, then invoke `superpowers:writing-plans` — no code before that
explicit go, per standing instruction.

## 5. Standard verification reminder for whoever reads this next

Verify main HEAD, verify branch, re-run `git fetch origin main` before
trusting any claim in this document — including this one. Re-check
`git ls-files | grep -i complaint` to confirm no file was created
between this handoff and the next session (none should exist yet).
