# SAIRNdental — Anonymous-Optional Patient Complaint Design

**Status:** Implemented and pushed to `main` 2026-08-12
(`docs/superpowers/plans/2026-08-12-sairndental-complaint.md`, 11 commits,
`42e7580..378a87c`, merged via subagent-driven-development: 9 tasks, each
independently task-reviewed, plus a final whole-branch review that found
and fixed 1 Critical (`vercel.json` had no route for the new public page —
would have 404'd in production) and 4 Important cross-file integration
gaps (`updated_at` never reaching the client so the panel's sort was
silently inert, a rate-limit bucket collision with the existing booking
endpoint, the nav badge not rendering at boot on a cached load, and zero
test coverage for the read-only-enforcement guarantee) — all fixed in one
fix wave, re-reviewed clean.

**Live-verified 2026-08-12** (`sairn.vercel.app`): the public page route
resolves (200, confirming the Critical fix landed), `dnt_complaints`
clears the `RESOURCES` allowlist gate, a write against it through the
generic `api/sd-data.js` path returns a real `400 READ_ONLY_RESOURCE`
(tested with the real `DNT-PINNACLE-2026` demo license, not just a bogus
token), reads degrade gracefully to `provisioned:false` rather than
crashing, and the public page's served HTML/JS contains zero license-key
references.

**Not yet live-verified — blocked on the SQL migration**
(`sql/sairndental_complaints_schema.sql` has not been run in Supabase;
confirmed live via the `provisioned:false` read above), honestly
reported, not glossed over: a real end-to-end submission creating a
genuine `dnt_complaints` row, the returned access-token thread
view/reply round-trip, the owner respond/resolve flow and its nav-badge
count change, the reopen-on-patient-reply state transition, and the
non-owner UI-gate check. Re-run
`docs/superpowers/plans/2026-08-12-sairndental-complaint.md` Task 10
Steps 6-9 once the migration has been run.

Brainstormed across two sessions (see `SAIRNDENTAL-SESSION1-HANDOFF.md`
for the mid-brainstorm stopping point) — all design questions below are
now resolved.

Real, evidence-backed motivation: 96% of patient complaints are about
communication/service, not clinical quality. Real scope: a patient-
facing form (message, optional name, no phone/email required), routed
privately to staff, that requires and tracks a real response from the
practice owner — not a passive drop-box. Checked `SAIRN-BACKLOG.md` and
every prior spec before starting: no existing match, genuinely new
scope.

## 0. Design questions, resolved

**Response delivery — thread-based, not internal-only, not email-based.**
The owner's response posts into a real conversation thread attached to
the complaint. The patient sees it by returning via a private access-
token link. Deliberately independent of the email-reminder
infrastructure (`docs/superpowers/specs/2026-08-11-sairndental-email-reminders-design.md`),
which isn't fully live yet (`CRON_SECRET`/`RESEND_FROM_ADDRESS` still
pending) — this feature has zero dependency on that infra.

**Token distribution and loss — no recovery path, disclosed.** The
access token is shown once, immediately after submission, as a link the
patient must save/bookmark. It is never tied to a phone number or email
(matching the "no phone/email required" scope), so **if the patient
loses it, there is no way to recover the thread** — the same honesty
standard as the real-sync feature's disclosed "no delete-tombstones"
gap, not silently glossed over.

**Thread depth — open-ended back-and-forth**, not a single complaint +
single response. The patient can reply after the owner responds; the
owner can reply again. Chosen over a simpler one-shot model because the
value here is a real conversation, not a ticket that gets stamped once
and forgotten.

**Closing/reopening — a single, uniform state rule.** Three statuses:
`New` (needs an owner response), `Awaiting Patient` (owner has replied,
nothing currently needed), `Resolved` (owner closed it). The rule that
governs all transitions: **any patient-authored message sets status to
`New`, regardless of the current status** — this covers both "patient
replies while Awaiting Patient" and "patient replies after Resolved"
(reopening it) with one rule, not two special cases. Only the `owner`
role can set status to `Resolved`.

**Owner-only responding/closing — reuses the existing PIN role gate,
UI-level, same trust boundary as the rest of this app.**
`sairndental.html` already has a real role concept (`DEFAULT_PINS =
{owner, frontdesk, provider}`, `prole` variable, `dnt_role` storage
key) — but it is a **client-side UI gate only**, not server-enforced;
no role travels with the Bearer license key anywhere in this app today.
This feature does not introduce a new gap by reusing that pattern, but
it's stated explicitly here rather than implied: the
`complaint-respond` endpoint (§2) is gated by the practice's license
key, same as every other authenticated write in this app — any staff
member holding that key can technically call it directly, exactly as
true for every other write endpoint. The owner-only restriction is a
real, visible UI restriction (matching how e.g. provider-role selection
is already UI-only), not a new server-side security boundary.

**Visibility ("not silently ignorable") — a persistent nav badge
count.** The "Complaints" nav entry always shows a count of threads
currently in `New` status, computed client-side from the locally-synced
array, the same way `rDash()`'s existing KPI tiles are computed. A
fuller SAIRNbiz-style dashboard widget with aging/severity tiers
(mirroring `checkAttentionItems()`,
`docs/superpowers/specs/2026-08-10-sairnbiz-attention-digest-design.md`)
was considered and explicitly not chosen — single-domain, single-
severity data doesn't need that machinery; the nav badge already
satisfies "visible on every screen, not a queue staff has to remember
to check."

**Form fields — message + optional name only.** No optional "which
visit/provider" field (considered, not chosen — the owner can ask for
that detail in the thread if actually needed), no photos (unlike the
booking form's optional photo upload — a complaint doesn't need visual
evidence the way a dental concern does), no phone/email. Matches the
original scope statement exactly.

**Concurrent-write race — server-side append on both paths, disclosed
residual gap, not a stored procedure.** Both the public reply endpoint
and the new authenticated staff-response endpoint perform their own
fresh read-then-append-write directly against the record — **the
client (staff app) never fetches the whole record, mutates it locally,
and writes the whole thing back**, which is how every other `dnt_*`
resource works today and exactly the pattern that would let a patient's
reply silently vanish under a staff overwrite. This narrows the race
to both a patient and the owner writing to the exact same record within
the same instant — genuinely rare for one owner plus occasional patient
replies, and the same class of accepted risk this codebase already
carries and discloses in `api/_lib/dental-public.js`'s rate limiter
(its own header: "can undercount by a request or two... acceptable for
abuse deterrence," not acceptable everywhere). A real fix (a Postgres
stored procedure for atomic array-append) would eliminate the race
entirely but would be this platform's first stored procedure ever —
judged as over-engineering relative to this feature's actual traffic.

## 1. Data model

New resource: `dnt_complaints`. Local storage key:
`dnt_complaints_list` (staff app, read-only sync — see §4).

**Deliberate deviation from the generic-jsonb-blob pattern, twice, both
reasoned:**

1. **`access_token` is a real, promoted, indexed column** (not buried
   in `data` jsonb) — same reasoning as `dnt_settings.booking_slug`:
   the public thread endpoint (§2) must resolve a token directly to a
   record without already knowing which practice it belongs to.
   Generated server-side at creation via `crypto.randomBytes(32).toString('hex')`
   (64 hex chars) — genuinely high entropy, unlike a human-typed booking
   slug, because this token *is* the capability secret, not a
   convenience shortcut.
2. **This resource is read-only through the generic `sd-data.js` write
   path — enforced, not just a client-side convention.** `RESOURCES`
   allowlists `dnt_complaints` for `action:'read'` only; a `write`
   request against it returns a clean `400` directing to the dedicated
   endpoint (§2). This exists specifically to prevent the exact bug
   class this design is built around (a full-record client overwrite
   racing a patient's reply) from ever being reintroduced later by a
   future change that reaches for the generic write path out of habit.

**Complete field whitelist:**

- `id` — string, generated server-side (`newId('COMP')`, matching this
  app's existing ID convention, generated in the submit endpoint since
  there is no authenticated client to generate it locally).
- `access_token` — string, promoted column, unique, server-generated,
  never regenerated.
- `patient_name` — string | `''`, optional, set once at creation.
- `status` — `'New'` | `'Awaiting Patient'` | `'Resolved'`, per §0's
  transition rule.
- `messages` — array of `{from:'patient'|'owner', text, at}` (ISO
  timestamp), append-only, mutated only via the two atomic endpoints in
  §2, never via a full-record client write.
- `created_at` — string (YYYY-MM-DD), set once at creation.
- `updated_at` — ISO timestamp, set on every append (message or status
  change) — the sort key the staff panel uses to surface active threads.

**No fee, phone, or email field of any kind** — not a legal constraint
like the referral feature's Anti-Kickback issue, simply matches the
scope statement exactly; nothing beyond this whitelist is added without
a fresh design pass.

## 2. Public + dedicated staff endpoints (new)

Same category as `public-book.js`/`public-availability.js` — genuinely
unauthenticated, no license key anywhere in these two files:

- **`api/sairndental/public-complaint-submit.js`** — `{slug, message,
  patient_name}` in. Rate-limited first (`checkAndIncrementRateLimit`,
  5 submissions/hour/IP, matching `public-book.js`'s own tuning).
  Requires `message` (non-empty, capped length — 4000 chars). Resolves
  `slug` → `license_hash` via `resolveSlug()` (§0/Gap 1 of the booking
  design — the existing, non-secret per-practice slug is reused here,
  no new per-practice identifier needed). Creates the `dnt_complaints`
  row with `status:'New'`, `messages:[{from:'patient', text:message,
  at:now}]`. Returns `{ok:true, token}`.
- **`api/sairndental/public-complaint-thread.js`** — `{token, reply?}`
  in. Looks up the record directly by `access_token` (no `license_hash`
  needed from the client — token secrecy alone is the isolation
  boundary, the standard shape for any capability-URL design). Returns
  `404 UNKNOWN_TOKEN` if not found — no further detail, no information
  leak about why. If `reply` is present: rate-limited
  (`checkAndIncrementRateLimit`, 20 replies/hour/IP — looser than
  submission since a real patient conversation may need several
  messages), non-empty and capped at the same 4000 chars as submission, appended via a fresh
  read-then-write against just this record (§0's race handling),
  `status` set to `'New'`. Always returns the current `{ok:true,
  status, patient_name, messages}` whether or not a reply was included
  — the same request shape serves both "load the thread" and "post a
  reply."

New authenticated (license-key gated, not part of the generic
`RESOURCES` dispatch) endpoint:

- **`api/sairndental/complaint-respond.js`** — `{complaint_id, action:
  'reply'|'resolve', text?}` in, Bearer license key required (same
  `Authorization` header convention as `sd-data.js`). Looks up the
  record by `complaint_id` **and** the caller's own `license_hash`
  together (never by `complaint_id` alone — a valid key must still only
  reach its own practice's records). `action:'reply'` requires
  non-empty `text`, appends `{from:'owner', text, at:now}`, sets status
  to `'Awaiting Patient'`. `action:'resolve'` sets status to
  `'Resolved'`, with `text` optional (a final closing message,
  appended if given). Same fresh read-then-write pattern as the public
  thread endpoint — this is the other half of §0's race handling.

## 3. Internal-app additions (staff side)

- **New "Complaints" nav entry**, label always shows the live `New`-status
  count (e.g. "Complaints (2)"), computed from `ld('dnt_complaints_list',[])`
  on every render/sync — the actual "not silently ignorable" mechanism.
- **New Complaints panel** — list of threads, `New` first, then
  `Awaiting Patient`, then `Resolved` (each group sorted by `updated_at`
  descending). Each row expands to the full message history
  (`from`/`text`/`at`), patient name or "Anonymous" if blank.
- **Respond controls, gated to `prole==='owner'`** (hidden/disabled for
  `frontdesk`/`provider`, matching this app's existing UI-only role
  convention, §0): a reply textarea + "Send Response" button
  (`action:'reply'`), and a separate "Mark Resolved" button
  (`action:'resolve'`) — both call `complaint-respond.js` directly, not
  `sdnData()`'s generic write path (§1's enforced read-only rule).
  Success re-syncs just this resource (or the full `dntSyncFromServer()`
  sweep) to reflect the update everywhere it's rendered; failure shows
  the existing honest-toast pattern ("Saved on this device only..." vs.
  a real failure), same as every other write in this app.

## 4. Sync integration

`dnt_complaints` added to `DNT_SYNC_RESOURCES`
(`sairndental.html:1281-1292`) as `['dnt_complaints','dnt_complaints_list']`,
using the existing `dntMergeById()` merge — read-only, matching §1's
enforced restriction (the staff app never calls `sdnData('write',
'dnt_complaints', ...)`, only `'read'`). New `complaints()` accessor
(`return ld('dnt_complaints_list',[]);`) and `rComplaints()` render
function, called from `nav()` and from `dntSyncFromServer()`'s existing
`if(changed){...}` re-render block alongside the other resources.

## 5. Error handling

- **Submit-form validation** — `message` required (non-empty, trimmed),
  `patient_name` genuinely optional, matching every other add-form's
  existing pattern (toast on missing required field).
- **Reply/respond failures** — network or server error on either the
  public thread endpoint or `complaint-respond.js` shows a real error
  message, never a false success — same standard as every other write
  in this app.
- **Unknown/expired token** — clean `404 UNKNOWN_TOKEN` on the public
  page, a plain "This link isn't valid — check that you copied it
  correctly" message, no stack trace or internal detail.
- **Rate-limited submission/reply** — real `429`, clean message
  ("Too many attempts — please call the office or try again later"),
  matching `public-book.js`'s existing tone.

## 6. Non-goals (explicit scope cuts, this pass)

- No email/SMS notification to the patient or the owner, in either
  direction — independent of the Resend infrastructure entirely (§0).
- No dashboard/attention-digest severity or aging widget — nav badge
  only (§0).
- No optional visit/provider field, no photo attachment (§0).
- No automated matching between `patient_name` and an existing
  `dnt_patients` record — free text only, never linked, consistent with
  the anonymous-optional requirement (a real patient link would leak
  identity into a feature explicitly designed to allow anonymity).
- No DB-level atomic append (stored procedure) — accepted, disclosed
  residual race instead (§0).
- No delete function for complaints or messages — append-only thread
  history, matching `dnt_charges`/`dnt_payments`/`dnt_referrals`'s
  existing append-only precedent.
- No server-side role enforcement beyond the practice's license key —
  owner-only is a UI convention, matching how role restrictions already
  work everywhere else in this app (§0).

## 7. Testing

- Submit-form validation: `message` required, `patient_name` optional,
  confirm anonymous submission (blank name) works end-to-end.
- Token thread view: valid token loads the thread; unknown/malformed
  token returns a clean `404` and a real UI error, not a crash.
- State-transition rule: a single regression test confirms all three
  real cases against the one rule in §0 — patient reply on `New` stays
  `New`; patient reply on `Awaiting Patient` flips to `New`; patient
  reply on `Resolved` flips to `New` (reopening) — one rule, three
  assertions, not three special-cased code paths.
- Owner-only UI gate: confirm `frontdesk`/`provider` roles cannot see
  or trigger the respond/resolve controls in the panel.
- Rate limiting: exceed the submit threshold from one IP, confirm a
  real `429`; confirm a different IP is unaffected; repeat for the
  reply threshold on `public-complaint-thread.js`.
- **Race-handling regression (the actual test for §0's core decision):**
  fire a patient reply and an owner reply at the same record in rapid
  succession; confirm the resulting `messages` array contains both
  entries (order may vary, presence must not) — the concrete
  regression test that a naive full-record-overwrite implementation
  would fail and this read-then-append design passes.
- Enforced read-only check: confirm a `write` action against
  `dnt_complaints` through `sd-data.js`'s generic path returns a clean
  `400`, not a silent success that bypasses §0's race handling.
- Field-whitelist regression: confirm the complete `dnt_complaints`
  record shape (client-side sync type and both new endpoints) contains
  exactly the fields in §1, nothing else.
- Sync integration: confirm `dnt_complaints` is included in
  `dntSyncFromServer()`'s sweep and a submitted complaint appears in a
  fresh staff browser session, using the same live regression method as
  the real-sync feature's own established test.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`,
  `duplicate_global_check.py`) after every `sairndental.html` change;
  `node --check` on every new/changed `.js` file; Push Protocol
  before/after push.
