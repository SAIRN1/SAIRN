# SAIRN — Platform Session 3 Handoff

Written at natural stopping point (end of session), 2026-08-11.
Claims below are independently verified against the actual repo/live
site, not assumed from memory — same standard as prior sessions in
this series (Sessions 1-2). Naming convention note: this is
`SAIRN-PLATFORM-SESSION` because tonight's work spans multiple apps
(SAIRNdental, SAIRNcash), not one app's own numbered series — see
`sairn-session-handoff` skill for why the two series stay separate.

## 1. Verified current state

- `origin/main` HEAD: `73a190f4201a885de5ff00b1165c148ca7811459` — confirmed
  via `git rev-parse origin/main` and cross-checked against local
  `git rev-parse HEAD` (identical, nothing unpushed).
- Working tree: clean of any SAIRN app changes. Only `.claude/settings.json`
  shows modified (a local tooling config, unrelated to any app work,
  already in that state at session start — not something this session
  touched or needs to commit).
- `sairndental.html`, `sairndental-book.html`, `sairncash.html`: all
  live-verified byte-identical to their committed HEAD versions on
  `sairn.vercel.app` at time of last check tonight (confirmed via direct
  curl + diff for each, not assumed from a clean `git push` alone).

## 2. Commits this session, in order

**SAIRNdental fee-schedule + billing (earlier this session):**
- `3e8c95c`/`bf7cbef` — fee-schedule + checkout-balance design spec + plan
- `0d3dbaf` — fee-schedule/coverage lookup + charge/payment data layer
- `e0fdba8` — billing panel (charge/payment entry, complete-visit flow)

**SAIRNdental automated email reminders:**
- `36cd012`/`fc4f8b8` — design spec + implementation plan
- `5f0f6a8` — Practice Info settings fields + "no email on file" badge
- `7bfd71b` — reminder email copy module (pure) + tests
- `c5eb83b` — reminder window-selection logic (pure) + full boundary tests
- `d079e74` — send-reminder.js cron endpoint + auth-gate tests
- `e92a08f` — hourly Vercel Cron wiring
- `a132d75` — status update: Tasks 1-5 pushed, live-verified

**SAIRNdental guided photo-capture (public booking):**
- `86cfdb1` — logged deferred per-patient photo-history panel to backlog
- `2d59f55`/`3b170b1` — design spec + implementation plan
- `3996d6c` — pure photo-validation module (size/format + EXIF detector) + tests
- `6673c1b` — public-book.js validation wiring + tests
- `9e43b72` — guided photo-capture step on the public booking page
- `8ef0d05` — Pending Requests panel photo thumbnails + note
- `9983ebb` — logged 2 backlog items found during live verification
  (public-book.js 502-not-409 + orphaned-patient bug; platform-wide
  no-delete-API gap)

**SAIRNdental real read/sync (platform-critical fix):**
- `446bbb5`/`0629144` — design spec + implementation plan
- `fe36f10` — pre-flight plan fix (Refresh button element reference)
- `75eeff7` — `dntMergeById()` pure merge helper + Node-verified tests
- `6a132a3` — `dntSyncFromServer()` 10-resource sweep, wired to `init()`
- `0f1ea0d` — manual Refresh button on Pending Requests (full sweep)
- `9751646` — local-delete toast disclosure (reappear-on-sync risk)
- `0a6b2c0` — post-final-review fixes (honest failure toast, button
  recovery, comment/duration polish)
- `c5b1ff8` — logged 2 more backlog items (localStorage quota risk from
  photo-bearing appointments; platform-wide no-license-scoped-storage-keys
  gap, cross-tenant PHI mixing risk on device re-key)
- `4d0d3f6` — status update: implemented, reviewed, live

**SAIRNcash estimator panel finish (Task 3 of an earlier session's spec):**
- `c6bdb3a`/`aeef765` — design spec + implementation plan
- `aa75c03`/`88fb9a4` — profile sync + fix (Firebase `set()` requires
  `null`, not `undefined`, for an absent optional field)
- `217b37b`/`6d53d92` — `renderEstimator()` + quarterly deadline table +
  fix (missing `(Number(x)||0)` currency guard)
- `73a190f` — view-switch trigger

## 3. What was CORRECTED, not just added

- **The original SAIRNdental design assumed staff would see
  self-scheduled bookings without ever verifying the app could read
  server data at all.** It couldn't — confirmed live, a fresh browser
  session showed all-zero counts and "No pending requests" despite the
  server holding real data. This wasn't a photo-capture bug specifically;
  it was a platform-critical gap in the app's foundation that happened to
  surface while reviewing the photo-capture feature. Fixed this session
  (the real-sync work above), confirmed platform-wide investigation found
  this exact bug class exists nowhere else on SAIRN — 10 other apps have
  no comparable public-write surface at all, and the one that does
  (SAIRNcash's waitlist) never promised a staff-facing view.
- **The uncommitted `sairncash.html` diff sitting across several
  sessions was initially assessed as "orphaned, non-functional, unsafe
  to commit."** That assessment was correct for the diff in isolation
  (zero backing JS, a `saveProfile()` call to an undefined function) but
  incomplete — deeper investigation found Tasks 0/1/2/4 of an existing
  2026-08-10 spec (Firebase security scoping, the full deterministic
  tax-math engine, income/deduction entry, the AI's constrained role)
  were already implemented and live in production. The diff was the
  correct start of Task 3, not a fabricated dead end. Lesson: an
  uncommitted diff's own isolated state doesn't tell you what's already
  real elsewhere in the file — check before concluding "unfinished" means
  "unfounded."
- **A previously-reported `CRON_SECRET` value was flagged by the user as
  having "trailing x's that don't belong."** Never definitively
  root-caused (display artifact vs. genuine copy error) — regenerated a
  fresh value instead of debugging the first one, then live-verified the
  fresh one is the one actually active (confirmed via a real 401→working
  auth-gate test). Flagging that the *original* value's exact defect was
  never diagnosed, only worked around, in case that discrepancy matters
  later.

## 4. Open items, prioritized

1. **URGENT, live risk, not yet fixed: `dnt_appointments`'s DB-level
   64KB `CHECK` constraint (`dntap_data_size`,
   `sql/sairndental_data_schema.sql:80`) was never actually raised via a
   real migration, despite an explicit decision this session to do so**
   ("real SQL migration raising dnt_appointments' ceiling... don't
   degrade photo quality to fit an arbitrary pre-existing constraint").
   Confirmed via `git log` — zero SQL changes committed tonight. Photo
   capture (up to ~900KB per booking) and self-scheduling are BOTH now
   live in production. If that constraint is genuinely enforced on the
   live table (never empirically confirmed either way — my own live test
   used a tiny synthetic 3KB image that stayed under every ceiling), a
   real patient submitting a real phone photo could hit a hard DB
   rejection, losing their entire booking request (compounded by the
   separately-logged orphaned-patient-record bug on that same failure
   path). **This is the single most important thing to pick up next,
   before this reaches a real practice.**
2. **SAIRNcash Stripe integration confirmed NOT configured at all** —
   `api/sairncash/checkout.js` returns `{"error":"Stripe not
   configured"}` live, meaning `STRIPE_SECRET_KEY` and/or
   `STRIPE_PRICE_ID` are missing from Vercel. Per the user tonight, this
   is expected — Stripe setup was already planned for next week, not
   this session. The estimator panel finish work is complete and correct
   on the code side; its final live-subscriber regression test (Task 4
   Steps 3-7 of `docs/superpowers/plans/2026-08-11-sairncash-estimator-panel-finish.md`)
   is blocked on this exact prerequisite, same category as the earlier
   email-reminders DNS wait — a real external dependency, not a bug.
3. **Email reminders: `RESEND_FROM_ADDRESS` status last known as
   pending**, blocked on Namecheap DNS propagation for the Resend
   sending domain (reported mid-session as "up to 24-48h," not
   re-checked since — deliberately not re-tested tonight since a
   real check risks triggering a genuine email send if the window has
   since cleared and a real appointment happens to be due). Re-verify
   fresh next session before assuming either way.
4. **5 new backlog items logged tonight, all still open**, full detail
   in `SAIRN-BACKLOG.md`:
   - SAIRNdental `public-book.js` misclassifies a slot race as a generic
     502 instead of 409 `SLOT_TAKEN`, plus leaves an orphaned patient
     record on that same failure (double-booking protection itself
     still holds — data-integrity is fine, error messaging isn't).
   - Platform-wide: `api/sd-data.js` has zero delete capability for any
     resource on any app — confirmed by grep, not assumed.
   - SAIRNdental per-patient photo history panel (a real, bigger,
     deliberately-deferred future feature, distinct from booking-time
     photos).
   - SAIRNdental's new sync sweep can silently exhaust localStorage once
     photo-bearing bookings accumulate (`st()` swallows
     `QuotaExceededError`) — directly related to item 1 above; fixing
     item 1's DB ceiling doesn't fix this client-side risk, they're two
     different ceilings.
   - Platform-wide: no SAIRN app clears local data or scopes storage
     keys by license on a device re-key — confirmed across all 13 apps'
     login flows. Real sync (this session's new pattern, likely to be
     copied to other apps later) turns this from "stale clutter" into
     genuine cross-tenant data mixing risk.
5. **Live test data still sitting in the `DNT-PINNACLE-2026` demo
   account**, un-deletable (item above — no delete API exists anywhere
   on the platform): patients `PT-1786459014901-103`,
   `PT-1786459096578-942`, `PT-1786459097218-952`,
   `PT-1786463835086-618`, `PT-1786463915298-475`; appointments
   `AP-1786459014994-702`, `AP-1786459096666-870`,
   `AP-1786463835198-843`, `AP-1786463915333-379`. Needs a manual
   Supabase-dashboard deletion whenever someone has direct DB access —
   not urgent, cosmetic only.

## 5. Standard verification reminder for whoever reads this next

Verify main HEAD, verify branch, re-run relevant checks before trusting
any claim in this document — including this one. In particular:
re-confirm item 1 above (the DB constraint) empirically before assuming
it's still unaddressed — that's exactly the kind of claim that should be
checked fresh, not carried forward on faith.
