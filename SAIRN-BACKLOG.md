# SAIRN Backlog

Deferred items — not urgent, not forgotten. Pick up at a natural pause,
not mid-session. Each entry: what, why deferred, what "done" looks like.

## SAIRNdental multi-location: read-side half, READY TO BUILD FIRST

**Logged:** 2026-08-24. **Write-side half already SHIPPED** — do not redo it.

**Status:** `location_id` is captured on every SAIRNdental write as of
2026-08-24 (`api/_lib/dnt-location.js`, wired into the generic
`DNT_RESOURCES` write, the `dnt_appointments` write, and
`api/sairndental/public-book.js`). Every row is attributable. A minimal
locations registry lives on `dnt_settings.data.locations[]`, validated
server-side. This half shipped alone because it is the **only** part with a
deadline: a charge, payment, AR entry or appointment written without a
location can never be attributed to one afterwards. Everything below costs
the same later as it does now, so it was deliberately held.

**Trigger:** build this the moment a second location is confirmed for a real
practice. Not before — building it against a guess risks the wrong shape.

**What is held, in build order, with costs already derived (2026-08-24
costing pass against the real schema — do not re-derive):**

1. **`dnt_settings` split, 1–2 days.** THE ONLY STRUCTURAL BLOCKER. Today
   `unique (license_hash, settings_id)` plus a globally-unique
   `booking_slug` means **one settings row and one public booking page per
   license**. A second location cannot have its own booking page, address or
   hours. Needs one settings row per location and a per-location slug, plus
   a real migration against live rows (check the diff shape first).
2. **`public-availability.js` location filter, included in the above.**
   Currently resolves slug -> `license_hash` and reads providers, hours and
   procedures **license-wide with no location filter**
   (`api/sairndental/public-availability.js:56-97`). The moment a second
   location exists this is a correctness bug, not a missing feature: a
   patient booking at one office is offered every provider in the group.
3. **Client location selector, 2–4 days.** `sairndental.html` is local-first:
   12 accessor functions read flat unpartitioned lists out of localStorage
   (`dnt_patients_list`, `dnt_appointments_list`, …) and **17 render
   functions** consume them. Needs a location filter through all of them and
   a decision on whether localStorage partitions per location or holds the
   union.
4. **Real `location_id` column + index on the financial tables, 0.5 day,
   deferrable.** Only needed when filtering moves server-side; jsonb is
   sufficient until then.

**What must NOT be built:** server-side cross-location aggregation for real
DSO scale. Dentrix holds ~90% of the top 50 DSOs; that tier is not winnable,
and building for it trades away the local-first simplicity that makes the
2–5 location band cheap to serve.

**Known ceiling, stated so nobody discovers it at location twelve:** the
local-first union works for roughly 2–5 locations. Beyond that it ships
every location's patients, charges and appointments into every front desk's
browser — a performance ceiling and a data-minimisation problem.

**Deliberately NOT changed, and why (so nobody "fixes" it):** the GiST
EXCLUDE constraints on `dnt_appointments` are already multi-location
correct. `dntap_no_operatory_overlap` keys on `operatory_id`, and an
operatory is a room at exactly one office, so location is implied.
`dntap_no_provider_overlap` is location-blind on purpose — a dentist cannot
be in two offices at once.

**Done looks like:** a two-location practice with two working public booking
pages, each offering only its own providers, and a location filter in the
staff app — verified with a real write and read-back at each location, not
just a clean deploy.

## SAIRNlaw AI Chain of Custody: one gap resolved, one remains open

**Logged:** 2026-08-13. **Gap 1 resolved:** 2026-08-13, same day, via the
"server-side capture" plan (`docs/superpowers/plans/2026-08-13-sairnlaw-ai-
chain-of-custody-server-side-capture.md`), commits `140b3aa..0ffb644`,
pushed to `main` at `d4f55be`, live-verified against `sairn.vercel.app`.

**What:** Found during the final whole-branch review of the AI Chain of
Custody (Phase 1) feature. Immutability (real DB-level `grant select,
insert`/`revoke update, delete`), role-gating (Owner/Attorney only for
review actions), server-derived identity (never client-supplied), and the
server-side state-machine verification gate were all genuinely real from
Phase 1 — independently re-verified, not just claimed. Two things were not
yet as solid as the feature's framing implied:

1. **RESOLVED — capture was client-reported, not proxy-observed.** The AI
   call (browser -> `PROXY`) and the log write (browser -> `api/law-auth.js`
   `ai_log`) used to be two separate, unlinked browser-originated requests,
   with the log write fire-and-forget. Closing the tab right after the AI
   answer rendered, or blocking/editing the log request specifically, used
   to produce a real AI interaction with no record — and symmetrically,
   nothing stopped a fabricated prompt/response pair from being logged that
   was never actually generated by the API. Fixed by moving the log write
   into the same server-side request that calls Claude (`ai_generate`,
   `api/law-auth.js`) — a response cannot reach the client without a real
   log entry already written, a write failure blocks the response instead
   of leaking the AI text, and `prompt`/`tools_used` are now derived
   server-side from the real `messages` sent to Claude (with a narrow
   client-supplied fallback only for the one call shape where the last turn
   isn't plain text), not trusted from an arbitrary client field. `ai_log`
   is removed entirely — no longer a valid action. Live-verified: `ai_log`
   returns 400 unrecognized-action; a real `ai_generate` call produces a
   genuine Anthropic response and a matching `ai_list` entry; a request with
   no derivable prompt is rejected (400) rather than logging blank.
2. **`matter_id` is still an unvalidated localStorage id.** `law_matters`
   (like all of SAIRNlaw's other 19 real resources) is client-only — the
   server accepts whatever `matter_id` string the client sends with no
   cross-check against a real, server-side matter record. The same id
   could resolve to different matters on different browsers under one
   license. "Matter-linked" today still means "linked to whatever the
   user's own browser believed the matter was," not independently verified.

**Why gap 2 is still deferred:** Closing it requires `law_matters` to
become server-backed first (the same much larger, already-logged,
not-yet-started SAIRNlaw server-sync gap this file already tracks
elsewhere for `law_trusttx` and friends) — a prerequisite this feature
can't unilaterally deliver.

**Done looks like (gap 2):** `matter_id` is validated server-side against
a real `law_matters` record once that resource is server-backed. Until it
lands, any external description of this feature should still say "logged
and matter-tagged by the user's own client" for matter linkage
specifically — but capture and prompt/response fidelity can now honestly
be described as server-observed.

## SAIRNlaw AI Chain of Custody: accepted nits (2026-08-13)

**Logged:** 2026-08-13. Found and explicitly ruled accept-and-document
during the same final whole-branch review — real, but none worth a code
change on their own right now.

**What:**
1. **`ai_list`'s derived-status window can go stale under high license-wide
   volume.** The listing fetches up to `limit` (max 1000) status-change
   events for the WHOLE license in one query to build every returned
   entry's status column. Past that combined volume, an older entry's real
   status event can fall outside the window and the entry displays as
   `Unreviewed` even if it was actually reviewed/rejected/used-in-filing.
   Symptom is cosmetic-but-confusing (a stale badge, or an older entry
   silently dropping off the visible queue) — genuinely safe because the
   window is a newest-first *prefix*: a missing status event can only ever
   under-report toward `Unreviewed`, never fabricate `Reviewed` or `Used in
   Filing`. The real enforcement gate (`ai_review`/`ai_reject`/
   `ai_used_in_filing`, `api/law-auth.js`) is independently, correctly
   scoped per-entry at the database level (fixed this same session after a
   Critical finding) and doesn't share this limitation. **Done looks
   like:** paginate `ai_list` or split its query into a real per-entry
   `detail->>'log_entry_id'` index-backed lookup instead of one shared
   license-wide window, once a firm's real usage approaches ~200 combined
   AI events (roughly the first heavy month of real use).
2. **Reject reason uses the browser's native `prompt()`** — the only
   `window.prompt()` call in the whole 3,240-line file; every other input
   in the app is a real field or modal. Works today, but is unavailable in
   some sandboxed/embedded contexts and is visually inconsistent with the
   rest of the app for something that becomes part of a legal record.
   **Done looks like:** a real modal matching the app's existing modal
   pattern (see `citatorfeedbackmodal` for a close analog already in this
   file), not a native browser prompt.
3. **Partially addressed 2026-08-13 — no volume cap on the audit table.**
   `ai_log` (unbounded) is gone; its replacement `ai_generate`
   (`api/law-auth.js`) now sits behind the same `is_demo`-style daily cap
   (`DEMO_DAILY_LIMIT`, currently 200/day) every other app's AI traffic
   already uses, applied per-instance the same way — so growth is now rate-
   bounded per day, not unbounded. Still not a real per-license row-count or
   retention policy (a firm generating 200 real AI interactions/day for a
   year still accumulates ~73,000 rows with no delete path), so this isn't
   fully closed. **Done looks like:** a deliberate per-license row-count or
   time-window retention policy, decided alongside whatever storage
   requirements the firm actually wants for a legal record (not an
   arbitrary technical limit imposed without that conversation) — the daily
   rate cap buys time for that conversation, it doesn't replace it.

**Why deferred:** All three are real but genuinely low-severity today
(server-side enforcement is independently safe regardless of #1; #2 and #3
are UX/scale polish, not correctness gaps) — worth a deliberate pass later,
not worth holding up a feature that answers a real, current, quantified
crisis (1,000+ sanctioned lawyers this year) over.

## StoneDesk procedural stone texture likely inflates canvas.toDataURL() PNG snapshots against an existing quota-risk pattern

**Logged:** 2026-08-13

**What:** Found during the final whole-branch review of the texture-only
stone visualization feature. `sdDrawSave()` (`stonedesk.html:3778-3790`,
a pre-existing, separate feature from the drawing-tool's own quote-save
path) snapshots the live canvas via `canvas.toDataURL('image/png')` and
stores up to 50 entries under a dedicated `sd_drawings` localStorage key
(same pattern as `sdDrawPrint()`, `stonedesk.html:3774`, though that one
isn't persisted). Before this feature, the canvas fill was a translucent
flat rect over a regular grid — PNG compresses that to nearly nothing.
The new procedural texture (dense anti-aliased speckle for Granite/
Engineered Quartz, bezier veining for Marble/Quartzite) is close to
incompressible visual noise by comparison — a real, not yet measured,
size increase per saved drawing, plausibly a 5-15x jump based on how PNG
compression works on structured-vs-noisy content. `sdDrawSave()`'s
`try{localStorage.setItem(...)}catch(e){}` swallows a quota failure
silently and unconditionally shows `"Saved: <jobName>"` regardless of
whether the write actually succeeded — the exact silent-failure pattern
this platform has been bitten by before (see the SAIRNdental photo-quota
entry below, structurally the same problem).

**Why deferred:** No real browser execution environment was available in
the reviewing session to actually measure `toDataURL()` output size
before vs. after texture, so no numbers exist to decide a fix from yet —
recommended action was "measure first," not "fix blind." A real fix
(surfacing the save failure honestly in `sdDrawSave()`'s status text,
and/or switching this specific export to `canvas.toDataURL('image/jpeg',
0.75)`, which compresses noisy/textured content dramatically better than
PNG and is already the established pattern elsewhere in this same file
for exactly this reason — see `stonedesk.html:19908` and other
`toDataURL('image/jpeg', quality)` call sites) is real but shouldn't be
built against a guessed number.

**Done looks like:** Real before/after `canvas.toDataURL('image/png').length`
measurements (with texture unset vs. a dense selection like Granite/Dark,
on a full-size shape, via a real browser session) confirm whether this is
actually a meaningful jump in practice — if so, `sdDrawSave()` either
switches to JPEG export or gets an honest save-failure toast (matching
`sdQuoteSaveHistory()`'s own already-fixed `saveOk` pattern,
`stonedesk.html:3427-3430`) instead of the current unconditional success
message.

## StoneDesk stone-texture visualization — accepted cosmetic nits (2026-08-13)

**Logged:** 2026-08-13. Both found and explicitly ruled accept-and-document
during the texture-only stone visualization feature's final whole-branch
review — real, but neither worth a code change on their own.

**What:**
1. `dcLoadDrawingState()` (the saved-quote restore path) redraws the
   canvas 3 times during a single restore instead of once —
   `dcSetStoneType()`/`dcSetColorTone()` each internally call
   `drawCTPreview()`, plus the function's own final explicit call.
   User-initiated, runs once, imperceptible (a few extra ~10ms renders).
   A suppress-redraw parameter on both setters would remove this but adds
   real API surface for zero user-facing benefit.
2. The stone texture "boils" (fully re-randomizes) on every mousemove
   while dragging a corner in Custom Draw mode, because the texture's
   seed includes the shape's bounding box and a live drag changes that
   box continuously — reads as TV static during the drag rather than a
   stone that visually stretches, resolving cleanly on mouseup. Preset-
   mode edge dragging is unaffected (it freezes a bitmap during the
   drag). A fix exists (seed on `stoneType+colorTone` only, dropping the
   shape-bounds component, so primitives stretch with the shape instead
   of re-rolling) but changes the visual character of every rendered
   texture (all sections of a multi-section shape would share one
   relative pattern layout instead of independent ones) — a real design
   tradeoff, not an obvious strict improvement, so not made unilaterally
   during a final-review fix pass.

**Why deferred:** Both are real but low-impact (transient/imperceptible),
and both proposed fixes trade away something (API surface, or a
different visual character) rather than being pure wins — worth a
deliberate decision, not folding into a review-driven fix wave.

**Done looks like:** A deliberate decision on each — accept as permanent
behavior, or make the specific tradeoff described above, made outside the
pressure of a final-review fix-and-ship pass.

## StoneDesk saved quote history doesn't capture the drawing tool's own state

**Logged:** 2026-08-13. **Resolved: 2026-08-13.**

**What:** Found during the final independent completeness check (4-scanner
sweep + silent-failure-sweep + adversarial review) on the full drawing
tool, after the chamfered-corners/raised-bar/canvas-zoom feature series.
`sdQuoteSaveHistory()` (`stonedesk.html:3405-3426`) persisted only
`{customer, project (material name), amount (final total), date,
status}` to `sd_quote_history`. No code path serialized `dcPoly` (the
drawn/edited shape), `dcCutouts` (sinks/cooktops/holes), `dcSeams`,
`dcRaisedBar`, or `dcChamferedCorners` — the saved `amount` was correct,
but nothing about *what was actually drawn* survived a save.

**Why deferred (at logging time):** A real fix was a genuine feature
decision, not a bug patch — what to serialize, where it lives, and
whether reopening a saved quote should re-render the canvas or only
display a static summary. Went through a full brainstorm → spec →
implementation-plan → subagent-driven-development cycle rather than
being improvised.

**Fixed:** `dcSnapshotDrawingState()`/`dcLoadDrawingState()` (mirror-image
capture/restore functions, `stonedesk.html`, near `printDrawCutSheet()`)
now capture the full drawing state — shape, dimensions, cutouts, seams,
chamfers, raised bar, Custom Draw mode + edge types + polygon-closed
state, and job-detail fields — as a new `drawingState` field on the
existing `sd_quote_history` entry (one storage key, no schema migration).
The History panel's `sdHistoryView()` (previously a toast stub) is now a
real modal with an itemized breakdown and a "Load into Drawing Tool"
button, gated by an unsaved-work confirm and disabled with an explanatory
note for quotes saved before this shipped. A final whole-branch review
caught and fixed a Critical bug the per-task reviews couldn't see (`sbNav`
navigating to the Drawing Tool panel AFTER the restore ran, which wiped
it via the panel's own default-shape init) plus three real Important
bugs (Custom-Draw-mode quotes silently pricing off leftover preset
dimensions on reload; restored seams not refreshing their list UI; a
full/blocked localStorage on save showing a false success toast) — see
`docs/superpowers/sdd/2026-08-13-stonedesk-saved-quote-drawing-state/progress.md`
for the full fix-wave detail. Shipped, live-verified against
`sairn.vercel.app/stonedesk` same day.

**Two narrow items intentionally NOT fixed, logged as their own entries
below** (both real, both accepted tradeoffs — not oversights): the
overwrite-confirm's false-positive rate, and `dcMode` not resetting to
`'preset'` on a same-session Custom-Draw-then-preset Load sequence.

## StoneDesk Load-into-Drawing-Tool overwrite confirm fires on a merely-opened Drawing Tool tab

**Logged:** 2026-08-13

**What:** Found during the final whole-branch review of the saved-quote-
drawing-state feature (see the resolved entry above). The "replace your
current drawing?" confirm before Load checks `gN('da-len') > 0` (among
other real-state checks) to decide whether the live canvas holds
unsaved work — but `initDrawPanel()` auto-seeds `da-len=96` the moment
the Drawing Tool tab is opened at all, whether or not the rep has drawn
anything. Practical effect: the confirm fires almost every time a rep
has ever visited the Drawing Tool tab this session, even with nothing
actually drawn — friction, not data loss (it errs toward asking, never
toward silently overwriting).

**Why deferred:** A real fix needs an actual "has the rep changed
anything since this shape was seeded" dirty flag, not a bigger pile of
heuristic checks on the same shape of problem — a real, separate, small
feature (a `dcDirty` flag set on any real edit, cleared on
load/save/clear), not a quick patch on the existing check.

**Done looks like:** The confirm only fires when the rep has actually
placed a point, changed a dimension from its seeded default, added a
cutout/seam/chamfer/bar, or otherwise made a real edit since the Drawing
Tool was last in a known-clean state — not merely for having opened the
tab.

## StoneDesk dcMode doesn't reset to 'preset' on a same-session Custom-Draw-then-preset quote Load

**Logged:** 2026-08-13

**What:** Found during the final whole-branch review's fix-wave
re-review for the saved-quote-drawing-state feature (see the resolved
entry above). `dcLoadDrawingState()`'s `dcMode` restore only handles the
`state.dcMode==='draw'` case (calls `setDCMode('draw')`) — by design, so
old snapshots with no `dcMode` field default to today's existing
`'preset'` behavior. But if, in the SAME session, a rep loads a
Custom-Draw-mode quote (live `dcMode` becomes `'draw'`) and then loads a
different, preset-mode quote right after without reloading the page,
live `dcMode` stays `'draw'` even though the newly-restored data is
preset-based — the draw-mode toolbar/UI doesn't switch back.

**Why deferred:** Narrow, same-session-only edge case (a full page
reload before the second Load sidesteps it entirely, since `dcMode`
defaults to `'preset'` on fresh load); found in a scoped fix-wave
re-review that correctly kept its own change minimal rather than
expanding scope reactively.

**Done looks like:** `dcLoadDrawingState()` explicitly sets `dcMode` to
`state.dcMode || 'preset'` (calling `setDCMode()` with whichever value)
rather than only ever handling the `'draw'` case, so the live mode always
matches whatever was actually saved, regardless of what mode the rep was
in immediately before clicking Load.

## SAIRNdental's new real-sync sweep can silently exhaust localStorage once photo-bearing bookings accumulate

**Logged:** 2026-08-11

**What:** Found during the final whole-branch review of the real
read/sync feature
(`docs/superpowers/plans/2026-08-11-sairndental-real-sync.md`).
`dntSyncFromServer()` pulls **all** `dnt_appointments` with no status
filter, date range, or limit. Self-scheduled appointments can carry up
to 3 photos as base64 data URLs (the guided photo-capture feature,
`~300KB` client-compressed each, `1.2MB` combined server cap —
`api/_lib/dental-photo-validation.js:13`). That's roughly 900KB per
photo-carrying booking, doubled again by localStorage's UTF-16 string
storage in practice — against a `~5MB` per-origin quota **shared with
every other SAIRN app on `sairn.vercel.app`** (StoneDesk already stores
slab photos in the same origin). A handful of photo-bearing bookings can
exhaust it. The failure is silent and self-reinforcing: `st()`
(`sairndental.html:482`) swallows `QuotaExceededError` in an empty
`catch(e){}`, the sync's own `changed` flag still gets set to `true`
(the local write attempt happened, whether or not it actually persisted
in memory-vs-disk terms — the render then runs off whatever `ld()`
+actually+ retrieved, which is stale once quota is hit), and the honest
success/failure toast added in this same feature's post-review fix wave
only detects a *read* failure, not a *local write* failure — so staff
still see "Refreshed from server." Once at quota, every other local
write in the app (`addPatient`, `setAppointmentStatus`) silently stops
persisting too, not just the sync sweep.

**Why deferred:** A real fix has two independent directions with real
tradeoffs (don't cache photo blobs locally at all vs. filter which
appointments the sweep pulls, e.g. by date range or status) that need
their own design pass, not a squeeze-in fix during a review pass for an
unrelated feature. Flagged with the real numbers rather than silently
shipped, per this platform's standing no-silent-failure discipline.

**Done looks like:** Either `st()` (or a wrapper around it) surfaces a
real, honest signal when a write doesn't actually persist — not just
swallowed — or the sync sweep and/or local photo storage is redesigned
to not accumulate unbounded blob data in a quota-limited, cross-app-
shared storage layer in the first place.

## SAIRN platform-wide: no app clears local data on a license/device re-key, and storage keys aren't license-scoped

**Logged:** 2026-08-11

**What:** Found during the same SAIRNdental real-sync review, but
confirmed as a platform-wide pattern, not specific to that app. Every
SAIRN app's login flow (checked: `sairndental.html`'s `gateGo()`,
`sairnbuild.html`, `sairnlaw.html`, `sairndesign.html`,
`sairnlegacy.html`, `sairncode.html`) writes a new license key to
`localStorage` via a bare `setItem`-style call without ever clearing any
of that app's `*_list`/`*_obj` data keys first, and none of those data
keys are scoped by license. Before any app had real read/sync, this only
meant a re-keyed device retained its own locally-created records
(stale, but confined to one practice's data). **SAIRNdental's new
real-sync sweep changes the consequence, not the root cause**: the first
`init()` under License A now pulls A's entire server-side dataset into
local storage, and a later login under License B on the same device
merges B's data on top of it — producing a single local cache mixing
two different practices' real patient records. For a HIPAA-adjacent app,
that's real cross-tenant PHI exposure on a shared/re-provisioned device,
not just stale demo clutter.

**Why deferred:** This is a root-cause platform architecture gap (no
license-scoped storage keys, no clear-on-relogin step) shared by all 13
apps, not something to patch in SAIRNdental alone — a single-app fix
would be misleading about the actual scope of the problem. Any app that
adds real sync next (following this same session's precedent) inherits
the identical exposure the moment it does.

**Done looks like:** A real, platform-wide decision and fix — either
every app's data keys get license-hash-scoped (e.g. `dnt_patients_list`
becomes keyed per license, not global to the origin), or every login
flow does a real clear of the previous license's local data before
writing the new one. Needs its own design pass given the number of apps
and existing local keys involved, not an incidental fix.

## SAIRNdental public-book.js misclassifies a real slot race as a generic 502, not 409 SLOT_TAKEN -- plus an orphaned patient record on that same failure

**Logged:** 2026-08-11

**What:** Live-reproduced during the photo-capture feature's Task 5
verification (not part of that feature -- pre-existing code, found
adjacent to it): submitting a booking for a slot that's already taken
returns `502 {"error":{"message":"Could not complete booking -- try
again"}}`, not the friendlier `409 SLOT_TAKEN` message
`public-book.js:114-116` is written to produce. `api/sd-data.js`'s own
separate `dnt_appointments` write handler (`api/sd-data.js:1835-1846`)
was already fixed for this exact bug class on 2026-08-11 (documented
in its own comment): a real Postgres `exclusion_violation` from the
`EXCLUDE` constraints can come back as HTTP 400, not 409, so a bare
`status === 409` check silently misses it. `public-book.js:114`
still only checks `insertRes.status === 409` and falls through to a
generic 502 for anything else — the same fix was never mirrored to
this second, independent insert code path. **The double-booking
protection itself still works** (verified: a real race against the
same slot did NOT create a duplicate appointment) — this is a
user-facing error-message bug, not a data-integrity bug. Secondary,
related consequence: patient matching/creation happens before the
appointment insert, so a raced booking still leaves behind a real,
orphaned `dnt_patients` row even though no appointment was created for
it — confirmed live (`PT-1786459097218-952`, "Curl Test 4 Slot Race").

**Why deferred:** Found while live-verifying the photo-capture
feature's own, unrelated changes
(`docs/superpowers/plans/2026-08-11-sairndental-photo-capture.md` Task
5) — orthogonal to that feature's scope, not folded into it. A real
fix belongs in its own pass: mirror `sd-data.js`'s body-inspection
approach into `public-book.js`'s insert-error handling, and decide
whether the orphaned-patient-on-failed-insert case needs a real fix
(e.g. don't create the patient row until the appointment insert
succeeds) or is an acceptable, self-limiting bit of clutter given this
platform's append-only, no-delete-API data model (see the next entry).

**Done looks like:** A slot-race booking attempt returns real `409
SLOT_TAKEN` from `public-book.js`, matching `sd-data.js`'s existing
body-inspection pattern; a documented decision (not silence) on
whether the orphaned-patient case needs its own fix.

## SAIRNdental (and platform-wide) has no delete capability via `api/sd-data.js` for any resource

**Logged:** 2026-08-11

**What:** `api/sd-data.js` supports only `read`/`write` actions for
every resource on every app — confirmed by grep, zero `delete` handler
exists anywhere in the file. This was already known/documented
implicitly in this codebase (`removePatient()`/`removeProcedureType()`
in `sairndental.html` are explicitly local-only, with comments
explaining why), but it became a real operational blocker during the
photo-capture feature's live verification: test data created against
the real `DNT-PINNACLE-2026` demo practice (patients
`PT-1786459014901-103`, `PT-1786459096578-942`,
`PT-1786459097218-952`; appointments `AP-1786459014994-702`,
`AP-1786459096666-870`) could not be cleaned up by any tool available
in this session — there is no API path to remove it, only a direct
Supabase dashboard delete, which requires Michael's manual action.

**Why deferred:** A real delete action (even an admin-only,
audit-logged one) is a genuine feature decision with real design
questions of its own (soft-delete vs. hard-delete, who's authorized,
whether it should exist at all given this platform's append-only-ledger
philosophy for financial resources specifically) — not something to
improvise as a side effect of one verification pass needing cleanup.

**Done looks like:** Either a real, deliberately-scoped delete/archive
capability is designed and added, or a documented, explicit decision
that test/demo data cleanup is permanently a manual Supabase-dashboard
task and every session's live-verification protocol says so plainly
(rather than each session rediscovering the same gap).

## SAIRNdental per-patient photo history panel

**Logged:** 2026-08-11

**What:** A real, standalone panel showing every photo on file for a
given patient as an ongoing visual record — independent of any single
appointment or booking request, something staff would open and browse
on its own (e.g. tracking how a condition has visually changed over
multiple visits), not just a thumbnail attached to one Pending Requests
row.

**Why deferred:** Surfaced while designing the guided photo-capture
feature for the public booking flow
(`docs/superpowers/specs/2026-08-11-sairndental-photo-capture-design.md`).
That feature deliberately scopes photos to a single booking request,
reviewed once via a thumbnail in the existing Pending Requests panel —
correct and sufficient for that pass, but a genuine per-patient photo
history is a bigger, independently valuable feature (its own data
model question: photos keyed to `patient_id` directly rather than
living inside one appointment's record, likely its own resource/table)
that shouldn't be folded into the booking-time feature silently.

**Done looks like:** A new panel (or section of the Patients panel)
that lists every photo ever captured for a selected patient, across
every appointment/booking, in one browsable view — not scattered across
individual appointment records with no aggregate way to see them
together.

## SAIRNbiz AP "Pay" button doesn't actually mark anything paid

**Logged:** 2026-08-10

**What:** `rAP()`'s bill row (`sairnbiz.html:1644`) renders a "Pay"
button: `onclick="toast('Marked paid')"`. It shows a success toast and
does nothing else — `sb_ap`'s `status`/`bal` fields are never updated.
A bill's `status` is set once at creation (`saveBill()`,
`sairnbiz.html:1467-1474`, via a dropdown defaulting to "Open") and can
never be changed afterward through any real UI action. Same shape as
the other silent-failure findings this platform has caught before: a
button that looks like it worked, shows a believable success message,
and changes nothing.

**Why deferred:** Surfaced while designing the cross-domain attention
digest (item 4 of the SAIRNbiz AI-native roadmap), which needed to know
whether AP `status` could be trusted as a live signal — it can't, for
this reason among others (see also `sb_train`'s missing edit path,
logged separately if not already). Wiring a real "mark this bill paid"
action (update `status`/`bal`, probably clear/reduce `bal` by the
payment amount, maybe log a payment date) is a real, separate,
self-contained fix — not something to bundle into a digest/validation
feature that has to treat the existing behavior as a known constraint
either way.

**Done looks like:** Clicking "Pay" on an AP bill actually updates that
bill's real `status` (to `Paid` or partially reduces `bal` for a partial
payment) and persists it, the same way `saveBill()`/`saveInv()` persist
new records — with an honest toast reflecting what actually happened,
not a fixed success string regardless of outcome.

## SAIRNbiz has no way to update a training cert's status at all

**Logged:** 2026-08-10

**What:** `sb_train` records (`emp`, `cert`, `exp`, `status`) are written
once by `seed()` and never touched again -- there is no edit/save
function anywhere in `sairnbiz.html` for the Training panel's records.
A cert seeded months ago as `status:'Active'` shows "Active" forever,
even after its real `exp` date has passed, because nothing ever writes
a new value. Surfaced while designing the cross-domain attention digest
(item 4 of the SAIRNbiz AI-native roadmap; see
`docs/superpowers/specs/2026-08-10-sairnbiz-attention-digest-design.md`
§1), which needed to know whether `sb_train.status` could be trusted as
a live signal -- it can't, for this reason.

**Why deferred:** The digest spec's fix works around this (compute
expiry from the real `exp` date, ignore the unreliable `status` label)
rather than fixing the underlying gap. Building a real cert edit path
(status changes, renewal date updates, maybe a renewal-reminder flow)
is a real, separate, self-contained feature -- not something to bundle
into a digest/read-only-computation feature.

**Done looks like:** A real edit function for `sb_train` records (at
minimum, updating `status` and `exp` on renewal) that persists the same
way `saveBill()`/`saveReview()` persist their records, so the Training
panel's own `status` field can eventually be trusted again instead of
permanently ignored in favor of date-based computation.

## SAIRNbiz budget "actual" spend never syncs with recorded expenses

**Logged:** 2026-08-10

**What:** `sb_bud`'s `actual` field (per-category spend against the
annual budget) is written exactly once, inside `seed()`. No
expense-entry path -- `saveExp()` or otherwise -- ever updates `sb_bud`.
A user can record real expenses all day and the Budget panel's
utilization percentages, and the cross-domain attention digest's budget
findings, never move from their seeded baseline. Surfaced during the
final review of the cross-domain attention digest (item 4 of the
SAIRNbiz AI-native roadmap), which disclosed this staleness in
`get_attention_digest`'s tool description but did not fix the
underlying gap (out of scope for that feature -- a read-only digest
over existing data, not a data-model fix).

**Why deferred:** Wiring real expense-to-budget sync (deciding how
`sb_exps` categories map to `sb_bud` categories, whether the mapping is
1:1 or needs a lookup table, and whether historical seeded `actual`
values should be zeroed or kept as a starting baseline) is a real,
separate data-model decision -- not something to bundle into a
disclosure fix.

**Done looks like:** Every `saveExp()` call updates the matching
`sb_bud` category's `actual` value (or a documented, deliberate mapping
decides how categories reconcile), so Budget panel utilization and the
attention digest's budget findings reflect real recorded expenses
instead of a permanently static seeded/manually-entered baseline.

## SAIRNbiz payroll runs are never actually recorded anywhere

**Logged:** 2026-08-10

**What:** `runPayroll()` (`sairnbiz.html:1503`) is a no-op toast —
clicking "Run Payroll" checks nothing, saves nothing, and no record of
the run (date, gross, tax, benefits, per-employee amounts) is ever
persisted. Separately, the Payroll panel's "YTD Payroll" KPI (`py-ytd`)
is not a real sum of historical runs — it's `rPay()` computing
`gross×13`, an extrapolation from the current period alone.

**Why deferred:** Surfaced while designing pre-payroll validation
(item 3 of the SAIRNbiz AI-native roadmap), which wanted to flag "a
number significantly off from last cycle" — there is no "last cycle"
data to compare against. Building real run-snapshot persistence
(a new `sb_payroll_runs` log, written on every real "Run Payroll") is
its own legitimate feature with its own real scope, not something to
build as a side effect of a smaller validation task.

**Done looks like:** Every "Run Payroll" click writes a real, timestamped
snapshot (gross/tax/benefits/total, employee count, maybe a per-employee
breakdown) to persistent storage. "YTD Payroll" sums real recorded runs
instead of extrapolating. A future "vs. last cycle" anomaly check
becomes possible once this exists.

## SAIRNbiz Benefits panel has no way to actually enroll anyone

**Logged:** 2026-08-10

**What:** `sairnbiz.html`'s Benefits panel reads `e.ben.health`,
`e.ben.dental`, `e.ben.k401`, and `e.ben.cost` in three places
(`sairnbiz.html:1615-1619`, `rBenKPIs()`) to compute enrolled-employee
counts and total benefits cost — but `e.ben` is **never written
anywhere in the file**. There is no benefits-enrollment save function.
`saveEmp()` only carries forward an existing employee's `.ben` if one
already happens to exist (`sairnbiz.html:1377`) — nothing ever creates
one in the first place. Every Benefits panel KPI (enrolled count, total
cost, per-plan breakdowns) is permanently `0`/empty for every employee,
in every install, with no error and no visible sign anything is missing
— it just looks like an app with no benefits enrolled yet.

**Why deferred:** Surfaced while designing pre-payroll validation
(item 3), which considered comparing rPay()'s flat `$520/employee`
payroll-benefits assumption against real enrolled cost — impossible
today since real enrolled cost is always `$0`. This is a real, separate,
larger gap (a whole missing enrollment CRUD flow — plan selection, cost
entry, dependent tracking, whatever the Benefits panel's UI actually
implies exists), not a quick fix alongside a validation feature.

**Done looks like:** A real save path that lets a user actually enroll
an employee in health/dental/401k and record a real cost, so
`rBenKPIs()`'s numbers reflect real data instead of being permanently
and invisibly zero. Worth a `sairn-silent-failure-sweep`-style pass
first to confirm this is the only panel in this state.

## SAIRNdesign invoicing needs a real server-side uniqueness constraint

**Logged:** 2026-08-09. **Resolved: 2026-08-10.**

**What:** `saveInvoice()`'s "already invoiced" check reads a local
snapshot of `invoices()` and, if no existing invoice references the
proposal, writes a new one. Zero race window on one device (no
`await` between read and write), but two staff on two different
devices/sessions could each pass the check before either's write has
synced, producing two invoices for the same approved proposal.

**Corrected sizing (2026-08-10):** originally grouped as "same
scope-class" as SAIRNlaw trust disbursement and SAIRNbuild server-sync
below — verified against live code that this was wrong. `sdn_invoices`
already has a working generic server route (unlike SAIRNlaw/SAIRNbuild,
which had none at all); this needed one `UNIQUE INDEX`, not a
from-scratch resource+schema build. Real scope: small-to-medium, one
migration + ~15 lines of server code + a client error-handling change.

**Fixed:** `api/sd-data.js`'s `sdn_invoices` write branch now maps a
Postgres 23505 unique_violation to a clean 409 `DUPLICATE_INVOICE`
response; `saveInvoice()` (`sairndesign.html`) rolls back its optimistic
local insert and shows the real rejection on that 409, instead of the
misleading "server sync failed" fallback. Both shipped and live-verified
2026-08-10 (`8d1f4d6`) — confirmed inert/no-regression against the live
endpoint.

**Migration run and independently verified, 2026-08-10:** Michael ran
`sql/sairndesign_invoice_uniqueness.sql` in Supabase's SQL editor (I
have no DB execution access from the Claude Code environment — no
`SUPABASE_URL`/service key, no `psql`, no `supabase` CLI, no Supabase
MCP tool, all confirmed this session — this step could not be done by
me). Two earlier behavioral retests after a premature "success" report
still showed 200/200 (no rejection) — not treated as fixed until a
real re-test confirmed it. Final re-test post-migration: first write
for a fresh `proposal_id` → 200; second write, same `proposal_id`,
different `invoice_id` → real 409 `DUPLICATE_INVOICE`; read-back
confirmed only one row persisted. No-regression check also passed:
updating an existing invoice's `status` in place (same `invoice_id`,
same `proposal_id`, e.g. `setInvoiceStatus()`'s path) still succeeds
normally. Test/scratch duplicate rows created during verification
(`PR-TEST`, `PR-VERIFY-1`, `PR-RETEST-1`, `PR-CHECK-1`, all on the
`SDN-PINNACLE-2026` demo license) were identified as synthetic before
deletion (never assumed) and are confirmed cleaned from the live table.

**Done looks like (achieved):** the invoice write goes through a server
route that rejects a second invoice for a proposal that already has
one, atomically — confirmed live, not assumed from a "migration ran"
report alone.

## SAIRNlaw trust disbursement needs a real server-side atomic check

**Logged:** 2026-08-09

**What:** `saveTrustTransaction()`'s disbursement balance check
(amount cannot exceed the client's trust balance) reads a local
snapshot via `clientLedgerBalance()` and, if it passes, writes the new
disbursement. This has zero race window on a single device/session
(no `await` between the read and the write) but cannot close a
cross-device race: two staff on two different sessions could each
read the same pre-disbursement balance, both pass the check
independently, and both write -- a real over-disbursement of client
trust funds, which is a bar-discipline / IOLTA compliance matter, not
just a data-integrity bug.

**Corrected sizing (2026-08-10):** this is genuinely the largest item
in this backlog after SAIRNbuild, not "same scope-class" as the
SAIRNlegacy/SAIRNdesign entries above (which is what this entry
originally said). Verified against live code: **`law_` has zero
entries anywhere in `api/sd-data.js`'s resource allowlist** — every
`sdnData('write','law_trusttx',...)` call 400s today, and the app
already honestly reports "server sync not yet enabled" (it isn't
silently lying about this one). There is no
`sql/sairnlaw_data_schema.sql` — only `_audit_log_schema.sql`,
`_citator_schema.sql`, and `_employee_auth_schema.sql` exist, none of
which cover business data. 19 real `law_*` resources exist client-side
(`clients`, `matters`, `trusttx`, `opaccounts`/`optx`, `deadlines`,
etc.) and **none** are wired server-side.

**Why deferred:** Needs the full resource+schema build first (same
shape as the SAIRNlegacy/SAIRNdesign/SAIRNgrounds/SAIRNscape/SAIRNcode/
SAIRNvet server-sync builds already done) — at minimum `law_trusttx`
plus whatever `law_clients`/`law_matters` reads the balance check needs
— *before* the atomic balance-check-and-write is even possible on top
of it. Two sequential real efforts, not one small patch. A genuine
multi-session build, correctly deferred, not attempted 2026-08-10.

**Done looks like:** `law_trusttx` (and its balance-check dependencies)
wired to real server persistence, the same honest await+check+toast
pattern every other server-synced resource on this platform uses, THEN
a real server-side atomic check-and-write on top that re-validates the
balance at write time and rejects the transaction if it would go
negative, with the client showing the real rejection reason.

**Progress:** step 1 (durable server persistence for `law_trusttx`/
`law_clients`/`law_matters`) shipped and live-verified 2026-08-16 —
`docs/superpowers/specs/2026-08-14-sairnlaw-trust-data-schema-design.md`,
commits `f79a2a9..ce81ccd`. Step 2 (the atomic check-and-write itself) is
in design as of 2026-08-16 —
`docs/superpowers/specs/2026-08-16-sairnlaw-trust-disbursement-atomic-check-design.md`.

## SAIRNlaw void-of-deposit can retroactively negative a client's balance

**Logged:** 2026-08-16, found while brainstorming step 2 of the trust
disbursement atomic check above. **Resolved: 2026-08-17/18** (step 3a),
`docs/superpowers/specs/2026-08-17-sairnlaw-deposit-void-balance-guard-design.md`,
commits `9cb1e82..38080e8`, live-verified against production (real
concurrency test — a simultaneous deposit-void and disbursement-create for
the same client, exactly one succeeded; a rigorous type-lying bypass
attempt on the routing gate, closed in the final-review fix wave, was also
proven closed live). **Scope note carried forward from the original "Done
looks like" below:** the shipped guard is client-level only (matches this
feature's existing client-level balance model everywhere else), not
per-`matter_id` as the original entry's wording could be read to imply —
that was never actually a separate requirement, just imprecise wording
here; not a gap.

**What:** The step-2 atomic check only guards Disbursement *creation*
(`law_check_and_insert_disbursement`) — voiding a transaction goes through
the plain, unguarded write path, same as every other void on this
platform. Concrete sequence: Deposit $500 (balance $500) → Disbursement
$500 (balance $0, correctly allowed) → someone later voids the *Deposit*
(a required-reason action, already possible today) → the client's
computed balance retroactively goes negative, with the $500 disbursement
now standing against zero real deposited funds. Nothing today or in step
2's design guards this.

**Why deferred:** Explicitly scoped out of step 2 during brainstorming —
a different failure mode (a single-actor, reason-required audit action,
not a concurrent multi-device race) from the cross-device over-disbursement
race step 2 exists to close. Folding it in would have doubled step 2's
design/implementation surface for a lower-frequency risk.

**Done looks like:** voiding a Deposit re-validates, server-side, that
every client_id/matter_id whose balance depends on that deposit stays
non-negative after the void — reusing the same advisory-lock pattern step
2 introduces (`pg_advisory_xact_lock` keyed on `license_hash:client_id`),
rejecting the void with a real reason if it would.

## SAIRNlaw law_check_and_insert_disbursement can return a null row on a cross-client trusttx_id collision

**Logged:** 2026-08-17, found during step 2's final-review fix-round
re-review (the retry-idempotency fix's own follow-up review).

**What:** `law_check_and_insert_disbursement`'s `on conflict (license_hash,
trusttx_id) do nothing` insert has no `client_id` in its conflict target.
The function's advisory lock (`pg_advisory_xact_lock(hashtext(license_hash
|| ':' || client_id))`) serializes two calls for the *same* client, so a
same-client retry always correctly finds the existing row first and
returns it. But if two calls for two *different* clients under the same
license somehow generate the exact same `trusttx_id`, the lock doesn't
serialize them (different lock keys) — the second to commit would hit
`on conflict do nothing`, insert zero rows, and `returning * into v_row`
would leave `v_row` all-NULL, returned with no error.

**Why deferred:** `trusttx_id` values are client-generated via
`newId('TR')` (`sairnlaw.html:1052`, timestamp + random suffix) —
a same-millisecond, same-random-draw collision across two different
clients is effectively unreachable in practice, a genuinely different
risk class from the retry-idempotency bug this same review round already
fixed (that one was guaranteed to hit on every legitimate retry). Matches
how every other practically-unreachable finding this session was handled
— logged, not chased into another fix round.

**Done looks like:** after the insert, if zero rows were affected (no row
in `v_row`), re-select the existing row by `(license_hash, trusttx_id)`
into `v_row` before the function's single `return v_row;` — mirroring the
existing-row branch's own behavior, so this path can never return a null
composite either.

## SAIRNlegacy merchandise reservation needs a real server-side lock

**Logged:** 2026-08-09. **Resolved: 2026-08-10.**

**Priority was highest in this backlog** — real risk of the same
physical casket/urn getting promised to two grieving families. Found by
the first full silent-failure-sweep + adversarial-review pass on
`sairnlegacy.html`.

**What was wrong:** `confirmReserve()` re-checked a unit's status
against `merchUnits()` — this device's own localStorage — not a server
round-trip, then wrote through a **blind upsert** (the generic
`leg_merch_units` route, which did already exist as of 2026-08-07 —
this entry's original "no server route yet" was stale by the time it
was re-checked 2026-08-10, corrected here rather than left standing).
Two staff on two different devices, each holding a stale local copy,
could both pass the check and both reserve the same physical unit.

**Corrected sizing (2026-08-10):** this entry originally said "same
scope-class as the SAIRNbuild server-sync gap" — wrong, once verified
against live code. The route already existed; the fix needed was a
narrow atomic-condition addition to it, **no schema migration**. Real
scope: small-to-medium, ~30 lines of server code + a client
error-handling change, not a from-scratch build.

**Fixed:** `api/sd-data.js`'s `leg_merch_units` write branch now uses a
conditional `PATCH` (`WHERE data->>status=eq.Available`) instead of a
blind upsert when `payload.status==='Reserved'` — 0 rows affected maps
to a real 409 `ALREADY_RESERVED`. `confirmReserve()`
(`sairnlegacy.html`) rolls back its optimistic local write and shows
the real rejection on that 409. Shipped and live-verified end-to-end
2026-08-10 (`8d1f4d6`): direct curl race test (first reservation 200,
second 409, server-side truth confirmed unchanged) and a real
browser-driven UI test through `confirmReserve()` itself (second
"device" correctly rejected and rolled back, first device's reservation
confirmed intact via a fresh server read). `releaseUnit()`/
`markUnitSold()` deliberately untouched — narrower scope than the
original "reservation lock" framing might imply, matching what was
actually reported and approved.

**Done looks like (achieved):** `confirmReserve()`'s actual reservation
write goes through a server route that atomically fails if another
reservation already landed first, and the honest failure message tells
staff to pick a different unit.

## SAIRNbuild has zero server-side backup for any real business data

**Logged:** 2026-08-09

**Priority: largest single item in this backlog** (the SAIRNlegacy
reservation-lock entry above held "highest priority" for urgency —
real risk to grieving families — until its 2026-08-10 fix; this entry
is now the largest by real scope, verified below). Found during the first full
sairn-silent-failure-sweep + sairn-adversarial-reviewer pass ever run
against `sairnbuild.html` (the sales-critical app) -- every other app
in the portfolio had already been through this pass.

**What:** `bldData()` (`sairnbuild.html`'s equivalent of `grdData()`/
`scpData()`, fully built and wired to `/api/sd-data` with a Bearer
license token) is only ever called for two things: reading SAIRNbiz's
employee roster, and reading/writing an anonymized shared-knowledge
word blob. **Jobs, Bids, Change Orders, Costs, Draws, Lien Waivers,
POs, Deliveries, Timesheets, Checks, Subs, Suppliers, Equipment,
Incidents, Documents, Reviews, Referrals -- the entire system of
record for a GC business -- persist through `st()` (localStorage)
only.** Confirmed against `SAIRNBUILD-SCOPE.md` §4, which explicitly
lists these resources as needing server-side extension work that was
never done, and an in-code comment (`saveDraw()` area) independently
confirming "Local-only for now, consistent with every other panel this
session." None of this is disclosed anywhere in the app's UI -- a user
has no way to know their data isn't backed up.

**Corrected count (2026-08-10):** this entry's "16+" undercounted --
a direct grep of `sairnbuild.html` for `ld('bld_...)` calls finds **36**
distinct resources (adds `change_orders`/`checks`/`comm_log`/`costs`/
`daily_logs`/`inspections`/`photo_analyses`/`pins`/`price_points`/
`punchlist`/`rfis`/`schedule_entries`/`selections`/`sub_bids`/
`submittals`/`toolbox_talks`/`warranty` on top of the 17 originally
named), confirming rather than shrinking the "real architecture
decision, not a bug fix" framing below. Same real scope-class as the
SAIRNlaw entry above (both need a from-scratch resource+schema build
before any atomicity work is even possible) -- **not** the same
scope-class as the SAIRNlegacy/SAIRNdesign entries above, which already
had working server routes and needed narrower additions. This
distinction (route-exists-needs-atomicity vs. route-doesn't-exist-at-
all) is the real sizing signal across all four of these entries, not a
single "same scope-class" grouping.

**Why deferred:** This is a real architecture decision -- wiring 36
resources to real server persistence, matching the pattern already
built for SAIRNgrounds/SAIRNscape/SAIRNcode/SAIRNvet/SAIRNlegacy/
SAIRNdesign -- not a bug fix. Same scope-class as the Vendor Ordering
Catalog build. Doing it rushed,
under a "just fix it tonight" framing, risks exactly the kind of
half-wired schema mismatch that's already been found and fixed
elsewhere in this portfolio (SAIRNgrounds/SAIRNscape sync merge bugs,
storage-key collisions). This needs its own scoping session: which
resources first, what the migration path is for existing localStorage-
only data already entered by real users, and whether the api/sd-data.js
resource-name collision risk (already a known, recurring bug class on
this platform) is checked before any route is added.

**What was fixed tonight instead (narrower, safe scope):** all 35
`save*()` functions now honestly report a local-storage write failure
(quota exceeded, private browsing) instead of showing "Saved" whether
or not the write actually succeeded. This does NOT address the
underlying gap above -- it only stops the app from lying about the
*local* save succeeding. The data is still nowhere but the browser
that entered it.

**Done looks like:** Every business-data resource in `sairnbuild.html`
round-trips through `bldData()`/`api/sd-data.js` the same way the other
four apps' resources do, with the same honest await+check+toast
pattern, and the UI discloses sync status somewhere a user can actually
see it -- not just a code comment.

## Rebuild graphify's knowledge graph, properly scoped — CLOSED 2026-08-24

**Logged:** 2026-08-07 · **Closed:** 2026-08-24

**What:** Re-run graphify against only `C:\Users\marsh\Documents\SAIRN`
(or wherever the live SAIRN app files actually live), at the current
commit, not the whole `C:\Users\marsh` git root.

**Why deferred:** Current graph (`graphify-out/graph.json`, built
2026-07-31 at commit `df84b21`, 84 commits stale as of this logging) is
unusable for its intended purpose — 91% of its 191,739 nodes are
unrelated `AppData\Local\Microsoft\Edge`/`Office` noise from an unscoped
directory walk, and it contains **zero** nodes for the actual live
`stonedesk.html`/`sairngrounds.html` files. Confirmed via two real
queries (`explain "grdData"`, `explain "sairngrounds.html"`) both
returning "no node matching."

**Done looks like:** A fresh `graphify .` run scoped to just the real
SAIRN app files, current commit, verified by querying a symbol that
exists in the current codebase (e.g. a function added this session) and
getting a real match back — not just "the command completed."

**Standing reminder:** re-run after any major merge, same staleness
problem will recur otherwise.

---

### RESOLUTION, 2026-08-24 — rebuilt, and the HTML half was a different bug

**Done.** Rebuilt scoped to `Documents\SAIRN-cody` at commit `acaa600`,
with `graphify` upgraded 0.9.31 → 0.9.48 (`uv tool install
"graphifyy[sql]==0.9.48"`). The `graphify` skill is now back **on** in
`skillOverrides`.

| | Old (2026-07-31) | New (2026-08-24) |
|---|---|---|
| Root | `C:\Users\marsh` | `Documents\SAIRN-cody` |
| Nodes | 191,739 (91% Edge/Office noise) | 1,906 (**0** noise) |
| graph.json | 456 MB | 2.7 MB |
| Commit | `df84b21` | `acaa600` |

Node sources: `.js` 923 · `.json` 520 · `.sql` 328 · `.py` 122 · `.cjs` 5.
The `.sql` and `.json` coverage is new — 0.9.31 emitted zero nodes for all
106 `.sql` files (missing `tree_sitter_sql`) and only 19 for `.json`.
Verified with real queries, not a clean exit code: `computeForFacility` →
`api/alf-alerts.js L131`; `hcbsCoverage` → `api/_lib/payer-routing.js L428`;
`alf_facility` → 3 nodes; `sairncare_employee_auth` → 2 nodes. God nodes are
the real auth spine (`validateLicenseKey` 31 edges, `verifySessionToken` 28,
`tokenFromRequest` 25), which is the strongest signal the graph is meaningful.

**KNOWN LIMITATION, permanent with this tool — the graph does NOT cover the
single-file HTML apps.** Zero nodes from any `.html` file, in either version.
This entry originally blamed the unscoped walk for that; it was wrong. There
are two independent causes and scoping only fixed one. The real cause:

```
graphify/detect.py:46
DOC_EXTENSIONS = {'.md', '.mdx', '.qmd', '.skill', '.txt', '.rst', '.html', '.yaml', '.yml'}
```

`.html` is classified as a **document, not code**, and `--code-only` skips
documents by design — every run reports "skipping 194 non-code file(s) (194
docs)", and the 16 SAIRN app files sit inside that 194. **No AST parser is
ever consulted for them.** Confirmed independently: `.html` appears in
neither code-extension map (`analyze.py:33-34`, `build.py:73-74`), and
grepping the whole installed package for `tree_sitter_html` returns nothing
— installing that parser does nothing, because graphify never imports it.

**Do not "fix" this by dropping `--code-only`.** That routes the files
through LLM *document* extraction: a 2 MB single-file application gets
treated as prose, producing doc-summary nodes instead of function/symbol
nodes, at real API cost, for strictly worse data. Decided against
explicitly, not overlooked.

**What this means in practice:** duplicate-feature checks, dead-code sweeps,
and any "where else does this exist" question **about panel code must not
rely on the graph** — panel code lives in the HTML apps and is invisible to
it. `tools/outline.py` already exists for exactly that job (structure/outline
extraction for `stonedesk.html` in place of a full re-read); use it there.
The graph is authoritative for `api/`, `agent/`, `scripts/`, `tools/`,
`tests/`, the seed JSON, and the full SQL schema — which is most of where
real bugs live, and it already earned its keep by surfacing `sendResendEmail`
as ambiguous across `api/alf-alerts.js` and `api/sairndental/send-reminder.js`
without being asked.

**Rebuild command:** `graphify extract <clone> --code-only --force --out <clone>`

**Left for Michael to delete** (blocked on permissions, both safe to remove):
`C:\Users\marsh\graphify-out.STALE-2026-07-31-unscoped` (481 MB) and
`Documents\SAIRN-cody\graphify-out.v0931` (1.3 MB).

## SAIRNdental pediatric guardian fields — `onPtDobChange()` not called at page init

**Logged:** 2026-08-13. Found during the final whole-branch review of the
pediatric guardian-fields feature (`docs/superpowers/plans/2026-08-13-
sairndental-pediatric-fields.md`, commits `78f3d25..c6ca92f`), flagged
Minor and explicitly deferred rather than fixed in that plan's fix wave.

**What:** `onPtDobChange()` (toggles the guardian field group's visibility
based on `pt-add-dob`'s current value) only fires on the input's own
`change` event. If a browser restores a previously-typed value into
`pt-add-dob` on page reload (Firefox notably does this for form fields),
the guardian group can stay in its static `style="display:none"` state
even though the restored DOB implies a minor — while `addPatient()`'s
save-time validation still correctly re-evaluates `isMinorPatient(dob)`
independently and will still block the save. Net effect: a confusing UX
(a validation error demanding guardian info for fields the user can't
see), not a data-integrity gap — the save-blocking gate itself is
unaffected and was independently verified correct.

**Why deferred:** Real but narrow (depends on specific browser
form-restore behavior on an uncommitted-then-abandoned add flow), and the
actual safety property (no minor patient record saves without guardian
info) holds regardless, since validation doesn't depend on the group's
visibility state.

**Done looks like:** Call `onPtDobChange()` once during the app's `init()`
sequence (guarded, since `pt-add-dob` exists unconditionally in this
single-file app) so a browser-restored DOB value is reflected in the
guardian group's visibility immediately on load, not only after the user
next touches the DOB field.

## SAIRNdental vendor/supply ordering — deferred items from the final whole-branch review

**Logged:** 2026-08-13. Found during the final whole-branch review of the
vendor/supply ordering feature (`docs/superpowers/plans/2026-08-13-
sairndental-vendor-ordering.md`, commits `874e34b..0533ea2`). All Critical/
Important findings from that review were fixed in the same session
(commit `0533ea2`) before push — these are the items the reviewer
explicitly separated out as real but smaller-scoped, not urgent enough to
hold up merge.

**What:**
1. **No pricing-rule listing/removal UI.** Vendor discounts, category
   discounts, and product overrides (`dnt_vendor_pricing_rules`) can be
   set via the Vendor Catalog panel's Negotiated Pricing card, but there's
   no way to see the full list of active rules or remove one — only
   overwrite it with a new value. A mistyped SKU override or a discount
   set for the wrong category has no undo path short of manually clearing
   `localStorage`.
2. **`mailto:` body can be silently truncated for a large cart.** Several
   mail clients cap `mailto:` URL length around ~2000 characters; a
   multi-item, multi-line purchase order can exceed that with no warning
   to the rep placing the order.
3. **Design spec's "savings" KPI was dropped at the plan-writing stage.**
   The original design spec (`docs/superpowers/specs/2026-08-13-
   sairndental-vendor-ordering-design.md`) listed "YTD spend, savings,
   active deals, low-stock count" for the Spend Report; the implementation
   plan only carried forward YTD spend, active deals, and low-stock count.
   Not an implementation bug — a real scope reduction that happened when
   the plan was written, flagged here so it isn't silently rediscovered
   as "missing" later without context.
4. **Minor perf nitpick, not correctness:** the "Active Deals" KPI's
   product-override filter (`vShowSpendReport()`) calls `vAllProducts()`
   once per override key instead of hoisting it outside the filter —
   `vAllProducts()` itself recomputes every product's `effectivePrice`
   across all 88 catalog items, so this is O(overrides × 88) instead of
   O(88). Only runs when the Spend Report modal opens; not user-visible
   at current catalog/rule-set sizes.

**Why deferred:** Items 1-2 are genuine gaps but larger in scope than a
same-session fix wave (a rule-management UI is a real feature; `mailto:`
length limits have no clean fix without redesigning the order-submission
flow, e.g. splitting into multiple emails or switching to a real backend
send path). Item 3 is a plan-authorship note, not a code defect. Item 4 is
harmless at current data volumes.

**Done looks like:** Item 1 — a small table under the Negotiated Pricing
card listing active vendor/category/product rules with a Remove button
per row. Item 2 — either split a large order into multiple `mailto:`
messages under the length cap, or (bigger lift) add a real
order-submission backend path. Item 3 — a deliberate decision either to
add a real "savings" computation (catalog price vs. effective price,
summed across order history) or to formally drop it from the design
spec's own stated scope. Item 4 — hoist `var all=vAllProducts();` once
before the `productOverrides` filter callback.

## StoneDesk Subcontractor Portal has no compliance layer — no COI, no insurance, no licence, no expiry

**Logged:** 2026-08-27, from the SAIRNmechanical worldwide competitive
research pass (`docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md`,
§5 Row 1). **Michael's call the same day: leave it alone for now** — real
gap, but StoneDesk is an existing shipped app and this was not that task's
scope. Logged as its own row rather than folded into the research
recommendation.

**Verified state, read directly from the file — not inferred:**
`stonedesk.html:28823-28827`, the entire subcontractor roster write payload is

```
sub_id, name, trade, phone, email, active
```

Plus ID+PIN portal login (`:31260`), job assignment (`:28913`), and the AI
field-progress photo inspector with a `sub` mode (`:34734`). A grep of the
whole file for insurance / COI / W-9 / licence / expiry fields **on the
subcontractor record returns nothing** — the four `insurance` hits in
`stonedesk.html` are SAIRNbiz cost inputs (`:4809`, `:20441`) and
SAIRNcare/senior document-reading prompts (`:16408`, `:18707`), all
unrelated to subcontractors.

**Why it matters:** subcontractor insurance-compliance tracking is a mature
external category — Certificial, MyCOI, TrustLayer, Jones, Billy,
SmartCompliance, CertFocus, BCS, Constrafor — where real-time expiry
monitoring and automated renewal alerts are table stakes, and BCS syncs with
Procore so tracking starts the moment a sub is added to a project.

**The honest nuance, which is why this is deferred and not urgent:** this is
a category-wide gap, not a StoneDesk-specific lapse. Fieldpoint — a real
commercial FSM product with a dedicated subcontractor-management page —
covers scheduling-board visibility, GPS, T&M/expense entry and payment
vouchers, and covers insurance/licence/compliance-document tracking **not at
all** (verified by fetching the page directly). Field Ascend's subcontractor
page likewise says nothing about certificates, licence tracking, expiry or
portals. So StoneDesk is not behind the field-service field here; it is
behind the *construction* field, which is where its subs actually come from.

**Contrast on record — SAIRNbuild is the reference implementation, and is
confirmed sound, no action needed:** `sairnbuild.html` subcontractor records
already carry `w9_on_file`, `coi_expiry`, `licence_no`, `licence_expiry`,
`prequal_status`, `financial_capacity`, `safety_record`,
`references_checked`, `bonding_capacity`, `current_backlog_pct`
(`:2455-2459`), plus company-level `insurance_carrier`,
`insurance_policy_no`, `insurance_expiry`. And it **enforces**, which is the
part the market only claims: `subComplianceIssue()` (`:6229`) flags COI or
licence within 30 days, the dashboard attention feed surfaces it on the
first screen after login (`:4400-4406`), "Eligible to Bid" requires **both**
prequalified **and** compliant (`:5139`), and award is hard-blocked at
`:3864` — *"Cannot award to … — not eligible to bid (…). Fix on the
Subcontractors panel first."*

**Why deferred:** whether compliance fields belong on a
countertop-fabrication sub roster is a product judgment call, not a research
finding. StoneDesk's subs are installers and fabricators, not licensed
trades pulling permits — the case for COI is strong, the case for licence
tracking is weaker, and nobody has made that call. Building it against a
guess risks the wrong shape.

**Done looks like:** an explicit decision, first — which of
{COI expiry, general-liability carrier/policy, W-9 on file, licence number
and expiry} StoneDesk's sub roster should actually carry. Then, if any are
adopted: the fields on the roster write payload, an expiry computation and
"Expiring Soon / Expired" badge reusing SAIRNbuild's 30-day shape rather
than a second implementation, and a decision on whether assignment is
**gated** on compliance the way SAIRNbuild gates award. The two hooks that
would be needed already exist — the `active` flag on the roster and the
single assignment path at `subxAssign` — so the gate has one place to live,
not several.

## A repo file can be written, reported as delivered, and never committed — the 2026-08-25 entry documented this failure mode without closing it

**Logged:** 2026-08-27, after it recurred. **This is a flag about a gap in our
own process, not about any app.**

**What happened, twice:**

1. **2026-08-21 → discovered 2026-08-25.** A 35 KB research spec existed only
   as an untracked file in the (now retired) `C:\Users\marsh\` checkout. It was
   invisible to all four clones and to a retirement plan whose Step 3 verified
   only *tracked* files against `origin/main` and reported a clean zero. Found
   by accident during an empty-directory pass, not by the plan.
2. **2026-08-27.** `docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md`
   — 1,259 lines, three research passes, reported to Michael as the deliverable
   and sent as a file — sat `??` untracked in `Documents\SAIRN-cc` through
   several turns. `SAIRN-BACKLOG.md`'s own StoneDesk row was ` M` uncommitted
   alongside it. **Caught only because Michael fetched the path himself and got
   a 404.** Nothing in the workflow raised it. Same directory, same class of
   file, six days later.

**Why the existing fix does not cover it — checked directly, not assumed:**

- `CLAUDE.md:58` — *"are **not written until committed in the same action** — a
  local-only handoff is invisible to every other clone."* The subject of that
  sentence is **handoffs**. A research spec is not a handoff.
- `sairn-session-handoff/SKILL.md:49,58,75` — the fullest statement of the rule,
  and every clause is handoff-scoped. Line 58 comes closest (*"Do not leave a
  local-only handoff and describe the handoff as written"*) and still says
  *handoff*.
- `sairn-guardian-v2/SKILL.md:1032` — the same sentence again, as a pointer into
  the handoff skill. Third restatement, same narrow scope.
- `sairn-precommit-gate` — triggers **"before every commit."** Structurally
  incapable of catching this: its trigger is the commit, and the commit is
  exactly what never happened.
- **Hooks (5 configured, all present at `C:/SAIRN/tools/`):**
  `html_script_check.py` (PostToolUse Write|Edit, HTML syntax),
  `redaction_check.py` (PreToolUse Write|Edit, secrets),
  `git_push_master_guard.py` (PreToolUse Bash),
  `deploy_verify_notify.py` (PostToolUse Bash),
  `session_lock_check.py` (SessionStart/UserPromptSubmit).
  **None of them looks at whether a file written into the repo ever reached a
  commit.**

**The precise shape of the gap:** the 2026-08-25 lesson was recorded in the
*deletion-safety* direction — "any future 'is it safe to delete this tree' check
must cover untracked paths too, not just `git ls-files`." That is the **read**
side. This recurrence was on the **write** side: authoring a deliverable and
never committing it. The write side was only ever addressed for one file type.

**A related third exposure, noted so it is not discovered separately later:**
the memory files written this session
(`~/.claude/projects/C--Users-marsh-Documents-SAIRN-cc/memory/`) live **outside
every clone** and are not version-controlled at all. The SAIRNmechanical
one-platform decision, the multi-trade contract/billing requirement and the
amended PE consolidator thesis currently exist only on this machine. That is by
design for the memory store, but it means "on the record" means two different
things depending on where a fact landed, and nobody has decided which facts
belong in which.

**Why deferred:** the fix is a mechanism decision, not a patch, and it should be
made deliberately rather than bolted on at the end of a research session. There
is more than one reasonable shape and they have different costs.

**Done looks like:** a decision between (at least) — (a) a `Stop`/session-end
hook that runs `git status --porcelain` in the clone and surfaces any untracked
or modified tracked-repo path before the session closes, which is cheap and
catches both directions; (b) widening the existing rule from "a handoff is not
written until committed" to "**any** repo deliverable is not delivered until
committed," and stating it in `CLAUDE.md` rather than only inside the handoff
skill; (c) both. Whichever is chosen, the test is that it would have fired on
2026-08-27 before Michael's 404 — a documented failure mode that can still recur
is not fixed.

## SAIRNmechanical platform spec — see `docs/superpowers/specs/2026-08-27-sairnmechanical-platform-spec.md`

**Logged:** 2026-08-27. **Pointer row — the spec itself is the document, this
exists so a future session finds it without already knowing to look.**

The operative spec for SAIRNmechanical. Not a research doc: it states
requirements and verdicts, and it is what a build or a review gets checked
against.

Carries: the **binding** multi-trade agreement/billing requirement (one
agreement spans multiple trades, per-trade line items, **trade on the line item
and never on the agreement header** — this fails *silently*, since a header-level
trade field looks correct for every single-trade customer and only surfaces on
the first multi-trade renewal, by which point it is a data migration); the
**trade-entitlement requirement** (unlock in place — no migration, no second
login, no new tenant — which must exist in the data model from the first table,
because retrofitting entitlement rewrites the authorisation surface rather than
adding a feature); the full A1–A7 / B1–B8 / Tier C pattern table with a
shared-vs-trade-gated verdict for each; all 21 gap rows with trade and region
frequency; and a prioritised **capability** list.

**The capability list is capability priority, NOT trade build order.** Build
order across the three trades stays deferred. The list also carries its own
caveat: gap frequency measures where competitors are weak, not what customers
need first, so table-stakes items are ranked in explicitly despite scoring low.

**Evidence and sourcing are deliberately NOT in the spec.** Every citation lives
in `docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md`,
and the spec points into it by section. If the two ever disagree, the research
doc holds the evidence and the spec holds the decision — reconcile explicitly
rather than silently picking one.

**§6 is written for a Guardian pass against a recovered `sairnmechanical.html`.**
Note before relying on it: as of 2026-08-27 that file exists on **neither** this
clone's working tree nor `origin/main`, while `sairn-guardian-v2`'s App File Map
asserts it and `api/claude.js` allowlists the `sairnmechanical` app_id. Any
recovered copy is local to whichever clone recovered it until pushed — confirm
which artefact is under review before trusting a finding about it.

**Done looks like:** nothing here — this row is a signpost. The spec's own change
discipline applies: amendments are decisions, recorded in the commit message, and
superseded requirements get marked superseded in place rather than deleted.

## SAIRNdental's public forms are live and receiving unsolicited traffic — rate-limited, but is that the right posture for a PHI-adjacent endpoint?

**Logged:** 2026-08-28, surfaced by the platform-wide demo-licence provenance
audit (`sql/platform_demo_licence_provenance_audit_2026-08-28.sql`). **Not
urgent. Nothing is broken and nothing leaked.** This is a posture question to
evaluate before real patients use these forms, not an incident.

**What was found.** One `dnt_complaints` row on `DNT-PINNACLE-2026`, classified
by Michael from `sql/sairndental_complaint_triage_2026-08-28.sql` as **scanner /
probe traffic**: no name, no email, no phone, and a zero-length first message
despite **six message entries** in the thread. Created **2026-08-12** — it
predates the 2026-08-27 session entirely. Nobody had ever looked at this table.

**The detail worth keeping:** six entries from a probe means the *reply* path
(`api/sairndental/public-complaint-thread.js`) was exercised repeatedly, not
just the submit path. So both public write paths have been reached by something
automated, unprompted, and nobody knew until a provenance audit looked.

**Row left in place** on Michael's call — not worth a delete for one probe entry.

**Current posture, read from the code rather than assumed:**
- `public-complaint-submit.js:43` — 5 submissions/hour/IP
- `public-book.js:43` — 5 booking attempts/hour/IP
- `public-complaint-thread.js` — 20 replies/hour/IP
- Backed by a real persistent Supabase-backed limiter with a hashed IP
  (`api/_lib/dental-public.js`), not an in-memory counter that resets per
  serverless invocation. That part is genuinely sound.

**The question to evaluate, which is not "add more rate limiting":** these
endpoints are unauthenticated by necessity — a patient self-booking or filing a
complaint has no credential, and cannot be given one. The limiter caps *volume
per IP*; it does not establish that a submitter is a real person, and a
distributed or rotating-IP probe is unaffected by any per-IP number. So the real
questions are (a) whether an unauthenticated form attached to a practice that
holds PHI wants a human-presence check at all, (b) whether anything should alert
when a thread accumulates messages with no matching appointment or patient, and
(c) whether probe rows should be reaped rather than accumulating unread — this
one sat for 16 days.

**Why deferred:** no real patients use these forms yet, and the answer is a
product/security judgment (adding friction to a patient-facing form has a real
cost), not a patch. Deciding it under time pressure with a prospect waiting
would be the wrong moment.

**Done looks like:** an explicit decision on (a)/(b)/(c) above, recorded, before
any real practice's booking page goes live to patients. If the decision is "rate
limiting is sufficient," that is a fine answer — but it should be a decision
someone made, not a default nobody examined. Note also that no other app on the
platform has an unauthenticated *write* endpoint into its own per-licence data
tables; SAIRNdental is the only one, so whatever is decided here does not
generalise and does not need to.

## `git_push_master_guard.py` blocks on TEXT ABOUT a push, not only on a push

**Logged:** 2026-08-28. **Low severity, silent, and it will recur.** Not a
security hole — the guard is over-eager, not under-eager. Logged because a
documented failure mode that can still recur is not fixed.

**What happened.** A `git commit` was blocked with *"this command pushes to the
stale 'master' branch. Repo default is 'main'."* The command pushed nothing. It
was a **commit**. Its message quoted the repo's own `permissions.deny` list
verbatim, and one of those entries is the literal rule string containing that
branch name next to the word push. The guard greps the whole Bash command
string, so any commit message, heredoc or inline text that merely *mentions* it
trips the check.

**It happened twice in a row while writing this very row**, which is as clear a
reproduction as the finding will ever get: once for the settings commit whose
message quoted the deny list, and again for the first attempt at this backlog
entry, whose text necessarily contains the same words.

**Why it matters more than it looks.** The block is correct-shaped and the
message is accurate about its own rule, so the natural reaction is to assume the
command really was unsafe and reword it — quietly losing whatever the message
said. It cost two retries here. The failure mode is a session hitting this while
writing an honest commit message about branch policy, concluding its command was
wrong, and editing the *content* rather than the *transport*.

**Workaround, which works and costs nothing:** write the message to a file
outside the repo and use `git commit -F <file>`, and append long prose to repo
files from a file rather than an inline heredoc. The guard then sees no matching
text in the command itself.

**Not fixed here, deliberately.** Narrowing the grep is a real judgment call: the
guard's bluntness is the reason it has never missed a genuine bad push, and a
cleverer matcher — parse the command, inspect only actual refspecs — is a
correctness risk in the one tool whose entire job is paranoia. Whoever picks it
up should decide whether a false positive every few weeks is worth trading for
parsing complexity in a guard.

**Done looks like:** either (a) an explicit recorded decision that the false
positive is acceptable, so the next session that hits it does not re-diagnose it
from scratch, or (b) a narrowed matcher inspecting only the push refspec, with a
test proving it still blocks a genuine push to the stale branch and no longer
blocks prose that mentions one.

**Related observation from the same hour — not a separate row, but worth seeing
together:** this surfaced during a *duplicated-work collision*. Another clone had
independently made the identical settings change while this one was writing it,
the second such collision in a single turn (the other being `sairnmechanical.html`'s
status). The clones share a remote but nothing announces intent.
`sairn-parallel-app-scaling` already documents that gap — *"nothing in the
existing set answers: is another clone building this right now?"* — so this is
another instance of a known finding, not a new one.

## Archive commit says 167 files; 168 landed — and the tag, not the commit, is what preserves the history

**Logged:** 2026-08-28 (CC), from the post-archive verification. **Trivial, no
action needed on the count itself.** Recorded because a count in a commit message
is a claim, and this one is off by one.

`39af4f5 archive: preserve the 167 files stranded on ...` archived **168** files.
`git ls-files archive/ | wc -l` → 168, and the commit's own `--stat` footer reads
*"168 files changed, 276874 insertions(+)"*. All 168 sit under
`archive/branch-lucid-ptolemy-b73vu0/`; none landed outside it. Nothing is
missing — the message undercounts what it did, which is the harmless direction.

**The part that is NOT trivial, verified while checking the count:** the archive
commit is an ordinary single-parent commit, so it preserves a **file snapshot
only**. The branch's actual history survives solely through the annotated tag
`archive/lucid-ptolemy-b73vu0` → `7d9b2d6`, which reaches **901 commits, every
one of them unreachable from `main`**. Deleting the source branch was safe
*because that tag exists*, and for no other reason. If the tag is ever pruned,
901 commits go with it and the snapshot on `main` is all that remains.

Two consequences worth knowing:
- The tag is **not fetched by default**. A clone that runs `git fetch origin
  main` will not see it and may reasonably conclude the history was lost. Run
  `git fetch origin tag archive/lucid-ptolemy-b73vu0` first.
- Content in the snapshot is byte-identical to the tagged history. The working
  tree copies are larger by exactly their line counts (1,230 / 170 / 43 bytes on
  `SKILL.md`, `license-manager.html`, `schema_license_keys.sql`) — pure CRLF
  conversion, not drift. Checked so nobody re-diagnoses a size mismatch later.

**Done looks like:** nothing, unless someone decides tag retention needs a
guarantee. If archive tags are ever considered prunable, this row is the reason
they are not.

## Trading bot: the historical data source is a decision to make BEFORE the backtest, not during it

**Logged:** 2026-08-28 (CC) for whoever builds it — **Cody owns this project**;
this row exists only so the point is on record rather than in a chat transcript.

**⚠ STATUS UPDATED 2026-08-29: THE BACKTEST HAS RUN and the live paper-trading
version is built.** Reported result: a flatten-at-close configuration profitable
across nine configs, +2.75% to +5.46% against SPY's +3.22% over the same window.
The build is blocked only on Alpaca keys reaching Cody's `.env`.

**What this row asked is therefore no longer a gate — but it is not confirmed
answered either, and that distinction is the point of leaving it here.** I have
not seen which data source the backtest used or at what granularity, and a
result of "+2.75% to +5.46%" is exactly as plausible whether the entry trigger
was detected from real intraday bars or silently approximated from daily ones.
If the source and granularity are already recorded somewhere, this row closes on
sight. If they are not, the number should be treated as unvalidated until they
are — not because anything looks wrong, but because a daily-only feed produces a
confident result for a strategy nobody specified.

The queued paper-trading bot's build order starts with "backtest the exact rules
against real historical data using backtrader." That step has an unstated
dependency: **backtrader has no built-in Alpaca feed**, and the strategy's scan
universe is ~3,000–5,000 actively traded US symbols.

So before any backtest code is written, someone has to decide where multi-year
daily (and possibly intraday) bars for thousands of symbols come from, and
confirm the licence permits it. Alpaca's own historical API is the obvious
candidate since the keys are already in hand, but its coverage, rate limits and
history depth need checking against the strategy's actual needs, not assumed —
the rules require a **200-day moving average** and **intraday** drawdown
detection, which are different data granularities with different costs.

**Why this belongs before the backtest rather than inside it:** the data decision
determines whether the backtest can even test the stated rules. An intraday
3–5% drop cannot be detected from daily bars alone, so a daily-only feed silently
changes the strategy being tested into a different one — and the backtest would
still produce plausible-looking numbers. That is the failure mode: not an error,
a confident result for rules nobody asked about.

**Done looks like:** a named data source, confirmed to cover the symbol universe,
the history depth, and BOTH granularities the rules need — recorded before the
first backtrader run, not inferred from whatever the first run happened to load.

## Nothing can tell you a live licence is running stale rules — `version` exists on every rule and is never bumped

**Logged:** 2026-08-28 (CC). **This is the general form of the LAW-PINNACLE
defect Hank is reloading right now**, and it is not specific to SAIRNlaw.

**The confirmed failure mode:** a rule is corrected in a seed file, the commit
lands, and the live licence keeps serving the old value indefinitely. It was
found on LAW-PINNACLE-2026 — the federal Rule 6(d) fix (`e1aa3f8`) and the
Florida exclusivity fix were in the repo but had never been loaded into the live
licence.

**Why it went undetected, which is the part worth fixing:** there is no way to
detect it. Every rule row carries a `version` field. **All 270 SAIRNlaw seed
rules are `version: 1`**, and `e1aa3f8` — which removed a three-day service
extension and therefore changed a computed legal deadline — **left `version` at
1**. Verified by diffing the seed at `e1aa3f8^` against the seed today:

```
frcp-12a1Ai-answer-after-service      version 1 -> 1 | service_extension PRESENT -> absent
frcp-12a2-united-states-official...   version 1 -> 1 | service_extension PRESENT -> absent
```

So a stale live row and a corrected seed row are **byte-distinguishable but not
version-distinguishable**. The only way to find drift is to diff whole jsonb
blobs across licences, which is precisely the manual exercise this session spent
the evening on to find two rows.

**The detector is half-built.** The field is already there, on every row, in
every seed, across every app that uses this pattern. It is simply never
incremented. Nothing else needs inventing — no new column, no migration, no
schema change.

**Scope, because it is not a SAIRNlaw problem:** the same seed-file →
per-licence-table shape covers `alf_compliance_rules`, `alf_payer_rules`
(SAIRNcare), `dnt_cred_rules` (SAIRNdental), `rf_cert_rules`,
`rf_contingency_rules` (SAIRNroofing) and `sc_anesthesia_base_units`
(SAIRNcode) — see `sql/platform_reference_rules_divergence_2026-08-28.sql`.
38 seed files exist in `sql/`; 13 changed in the three days to 2026-08-28. Every
one of those is a candidate for the same silent staleness, and no licence
anywhere records which seed generation it holds.

**Why this outranks reloading PINNACLE:** the reload fixes one licence once.
Without a staleness signal the same gap reopens the next time any rule is
corrected, and the next discovery will again be accidental. Tonight it was found
because someone happened to run a divergence audit; that is not a control.

**⚠ STATUS UPDATED 2026-08-29 — option (b) HAS BEEN BUILT, twice, independently.**
This row was written when nothing could detect the drift. Since then:
- `tools/sairn_build_load_gates.py` + `tools/sairnlaw_build_load_gate.py`
  generate read-only gates comparing every live row against the seed it came
  from, for **6 tables across 5 apps** — law_deadline_rules (270 rules),
  alf_compliance_rules (16), alf_payer_rules (6), dnt_cred_rules (6),
  rf_cert_rules (3), rf_contingency_rules (2). Proven retroactively: the
  SAIRNlaw gate independently named the same 7 stale rule ids the compute-diff
  found, by content comparison rather than by live computes.
- `api/legal-deadlines.js` `contentHash()` (another session) exposes the same
  idea as a live fingerprint endpoint — sha256/16 over the data blob with
  `authority.verified_by` removed, keys sorted.

So the answer landed as (b), not (a), and it did NOT require anyone to start
bumping `version`. That matters: (a) always depended on author discipline, and
an author who forgets reintroduces the blind spot silently. Content comparison
cannot be forgotten.

**WHAT IS STILL OPEN, narrower than the original row:**
1. `sc_anesthesia_base_units` (SAIRNcode) is the one reference table with NO
   gate, because it has **no seed file anywhere in the repo**. There is no
   declared state to compare a live licence against. That is a source-of-truth
   gap, not a tooling gap, and it is the remaining instance of this class.
2. Nobody runs the gates on a schedule. They exist and are proven; they are
   still invoked by a human deciding to invoke them. Tonight's defect was found
   by accident, and "someone remembers to run it" is only marginally better.
3. Whether to bump `version` anyway, as a cheap human-readable signal alongside
   the content check. Optional now rather than load-bearing.

**Original framing, retained because the reasoning still holds for anyone
weighing the three approaches:**

**Done looks like** — a decision between, at minimum:
- **(a) bump `version` on every corrective edit**, and add a check comparing the
  max seed version per jurisdiction against what each licence holds. Cheapest,
  uses what exists, but relies on discipline: an author who forgets to bump
  reintroduces the blind spot silently.
- **(b) a content hash per rule** stored alongside the row, computed at load.
  No discipline required and it cannot be forgotten, but it needs a load-time
  step that does not exist today.
- **(c) fold it into whatever shared-rules redesign follows the scoping work** —
  if rules stop being per-licence copies, staleness stops being possible for
  the shared set, and only genuinely per-customer rows keep the risk.

Whichever is chosen, the test is that it would have flagged LAW-PINNACLE before
a human went looking.
