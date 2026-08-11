# SAIRNdental — Real Read/Sync Capability Design

**Status:** Implemented, reviewed, and live 2026-08-11. Commits
`75eeff7`..`0a6b2c0` (feature) + `c5b1ff8` (backlog logging). Live-verified
via the real `DNT-PINNACLE-2026` demo practice: a self-scheduled booking
submitted through the public booking page appeared correctly in a fresh
staff browser session's Pending Requests panel (the actual regression
test for the bug this spec exists to fix), the manual Refresh button
surfaced a booking created after page load without a reload, the
disclosed local-delete reappear-on-sync behavior was confirmed real, and
`dnt_settings`'s single-object handling populated real server values.
Final whole-branch review found 2 Important + several Minor issues;
directly actionable ones (honest failure toast on total sync failure,
button-recovery try/finally, comment/toast-duration polish) were fixed
in one review-driven pass and re-verified clean; two larger, genuinely
separate-scope issues (localStorage quota risk from unbounded
photo-bearing appointments; a platform-wide, pre-existing gap where no
SAIRN app clears local data or scopes storage keys by license, which
real sync turns into actual cross-tenant data-mixing risk on a re-keyed
device) were logged to `SAIRN-BACKLOG.md`, not silently shipped or
squeezed into this feature's fix wave.

**Confirmed platform-critical fix, not a minor addition.** `sairndental.html`
has zero `'read'` actions anywhere in its client-side code — every one of
its 11 `sdnData()` call sites passes `'write'`. Verified live: a fresh
browser session logged into the real `DNT-PINNACLE-2026` demo license shows
Patients/Providers/Procedure Types/Coverage Rules all `0` and Pending
Requests showing "No pending requests," despite the server genuinely
holding real records for all of these. Every panel in this app has only
ever rendered from its own browser's local `localStorage` cache — data
written from a different device (most importantly, a self-scheduled
booking from `sairndental-book.html`, which necessarily runs in a
different, unauthenticated browser context) has been invisible to staff
since the self-scheduling feature shipped. Confirmed platform-wide
investigation found this bug class exists nowhere else on SAIRN: 10 other
apps have no public/unauthenticated write surface at all (the pattern
can't occur), and the one that does (SAIRNcash's waitlist) never promised
a staff-facing view of that data in the first place. SAIRNdental is the
only app that built both halves of the pattern — a real anonymous-write
feature and a staff panel promising to show it — which is exactly why this
is the only place the gap causes real, silent harm.

## 0. Design questions, resolved

**Base pattern — reuse SAIRNgrounds/SAIRNscape's already-proven fix, not a
new invention.** Both apps hit this identical bug on 2026-08-06 ("a QC
reviewer on a different device would never pull down the crew's uploaded
photo") and shipped `grdSyncFromServer()`/`scpSyncFromServer()`
(`sairngrounds.html:1460`, `sairnscape.html`'s equivalent): loop over every
resource, `read` each from the server, merge into local storage by ID
(server wins on a matching ID, non-matching server records get appended),
re-render every affected panel. Real, live, working precedent — not a
green-field design.

**Trigger — load-once everywhere (matching the precedent exactly) + a
manual Refresh button specifically on Pending Requests.** The precedent's
own choice was a single sync inside `init()`, no periodic timer. That's
adopted as-is for every panel except Pending Requests, which is the one
panel this whole investigation is about — staff realistically leave the
app open across a shift, and a new self-scheduled booking sitting
unnoticed has real patient-facing consequences. A manual button (not a
background poller) was chosen over a `setInterval` re-sync: no ongoing
polling cost, no new timing/cleanup surface, puts the responsiveness
decision in staff's hands rather than guessing an interval.

**Refresh button scope — the full resource sweep, not a narrow
appointments-only sync.** `rPending()` looks up patient/provider/procedure
names from separately-synced resources (`dnt_patients`, `dnt_providers`,
`dnt_procedure_types`) to render a row. A narrow sync of only
`dnt_appointments` would show a new self-scheduled booking with
"(unknown patient)" if that patient record — itself also new, since
`public-book.js` creates it — hadn't been pulled down too. The button
re-runs the same full sweep used at load, not a resource-scoped variant.

**Local-delete behavior — kept as-is (local-only, no server delete), but
the toast now discloses the reappear risk.** `removePatient()`/
`removeProcedureType()` stay exactly as they are today (this platform has
no delete API anywhere, confirmed in `SAIRN-BACKLOG.md`) — but once real
sync exists, a re-sync after a local-only removal will pull that record
right back (the precedent's own disclosed limitation: no delete-
tombstones). Checked for a comparable existing UI disclosure to copy from
SAIRNgrounds/SAIRNscape first — found none: their only `remove*()`
functions (`removeDesignElement`, `removeCoursePoint`) delete an item
*within* an already-owned record being actively edited, not a whole
synced resource with no server-side removal at all, so there was nothing
to compare against. The toast text changes from "Patient removed on this
device" to explicitly disclose the reappear-on-sync possibility (exact
copy in §4).

**`dnt_charges`/`dnt_payments` merge safely under the same by-ID union
logic, confirmed by reading the code, not assumed.** Neither resource has
any edit path anywhere in `sairndental.html` — only `addChargeEntry()`/
`addPaymentEntry()` exist, no corresponding edit function. Genuinely
append-only, so there is no scenario where the merge could silently drop
a conflicting edit; a plain union by ID is safe.

**Not a reversal of the fee-schedule spec's "no live cross-device push
sync" decision.** That earlier non-goal
(`2026-08-11-sairndental-fee-schedule-balance-design.md` §3) ruled out
*push*-based real-time sync (the SAIRNcash/Firebase model) — a different,
larger thing than the refresh-on-load *pull* sync this spec adds. Stated
explicitly here so this doesn't read as a silent contradiction of a prior
decision.

**`dnt_settings` needs different merge handling than the other 12
resources.** It's stored locally as a single object (`dnt_settings_obj`,
`id:'default'`), not a list — the array-merge-by-ID logic used for every
other resource doesn't directly apply. The read endpoint still returns an
array (matching every other resource's shape), so the sync function takes
that array's one `id:'default'` element (if present) and replaces the
local settings object directly, rather than running it through the
list-merge helper.

## 1. Architecture

- **`dntMergeById(local, serverArr)`** — new pure helper, identical shape
  to `grdMergeById()` (`sairngrounds.html:1452`): returns a new array where
  every server record replaces its local counterpart on a matching `id`,
  and any server record with no local match is appended. Local-only
  records not present on the server (not yet synced, or seed/demo data)
  are preserved untouched.
- **`dntSyncFromServer()`** — new function, loops over all 13 resources
  (§2's table), calls `sdnData('read', resource)` for each, merges via
  `dntMergeById()` (or the settings-specific single-object handling for
  `dnt_settings`), stores the merged result back to the matching
  localStorage key, and — if anything actually changed — re-runs every
  panel's render function so new data appears immediately. A resource
  that fails to read (not provisioned, network error) is skipped; the
  sweep continues with the rest. Matches `sdnData()`'s existing
  `console.warn` on a failed call — no new failure-logging needed.
- **Called once from `init()`**, after the existing local `seed()`/render
  calls (matching the precedent's ordering — local state renders
  immediately, then gets overlaid with server state once the sync
  resolves, rather than blocking the initial render on a network call).
- **New manual Refresh control on the Pending Requests panel**, calling
  `dntSyncFromServer()` again on click (the identical full sweep, §0).

## 2. Resource sweep — all 13 `dnt_*` resources

| Resource | Local storage key | Merge handling |
|---|---|---|
| `dnt_patients` | `dnt_patients_list` | `dntMergeById` |
| `dnt_providers` | `dnt_providers_list` | `dntMergeById` |
| `dnt_operatories` | `dnt_operatories_list` | `dntMergeById` |
| `dnt_provider_hours` | `dnt_provider_hours_list` | `dntMergeById` |
| `dnt_procedure_types` | `dnt_procedures_list` | `dntMergeById` |
| `dnt_coverage_rules` | `dnt_coverage_list` | `dntMergeById` |
| `dnt_appointments` | `dnt_appointments_list` | `dntMergeById` |
| `dnt_charges` | `dnt_charges_list` | `dntMergeById` (confirmed safe, §0) |
| `dnt_payments` | `dnt_payments_list` | `dntMergeById` (confirmed safe, §0) |
| `dnt_denial` | `dnt_denial_list` | `dntMergeById` |
| `dnt_ar` | `dnt_ar_list` | `dntMergeById` |
| `dnt_revenue` | `dnt_revenue_list` | `dntMergeById` |
| `dnt_settings` | `dnt_settings_obj` | single-object replace (§0) |

Every panel's render function (`rPatients`, `rProviders`, `rOperatories`,
`rProviderHours`, `rProcedures`, `rCoverage`, `rAppointments`, `rPending`,
billing's charge/payment views, `rBookingSettings`) re-runs after a sweep
that changed anything, matching the precedent's `if(changed){...}` gate.

## 3. Known, accepted limitations (same as the precedent, not new to this fix)

- **No delete-tombstones.** A record removed locally (`removePatient()`
  etc.) can reappear on the next sync. Disclosed to staff via the updated
  toast (§4), not silently hidden. A real tombstone/delete system is
  separate, larger, deferred work (the platform-wide no-delete-API gap is
  already logged in `SAIRN-BACKLOG.md`).
- **No `updated_at`-based conflict resolution.** If the same record were
  somehow edited on two devices between syncs, the last sync to run wins
  outright — no merge-field-by-field, no conflict warning. Matches the
  precedent's own explicitly-accepted interim state.

## 4. Local-delete toast update

`removePatient()`'s toast changes from:
```
'Patient removed on this device'
```
to:
```
'Patient removed on this device -- may reappear if server data syncs again'
```
Same change applied to `removeProcedureType()`'s equivalent toast.

## 5. Testing

- `dntMergeById()`: hand-computed cases — a server record overwrites a
  matching local ID, a non-matching server record gets appended, a
  local-only record with no server counterpart survives untouched. Node
  harness test, pure function, no I/O.
- `dnt_settings`'s single-object handling: server returns one `default`
  record → local object replaced; server returns an empty array
  (unprovisioned or no settings saved yet) → local object untouched.
- Sweep-level: simulate one resource's read failing (e.g. `NOT_PROVISIONED`)
  and confirm the sweep continues through the remaining 12 resources
  rather than aborting.
- Manual/live verification (no automated browser test harness for this
  file, same as prior sairndental.html work): confirm a self-scheduled
  booking created via `sairndental-book.html` actually appears in the
  staff app's Pending Requests panel after a page load — the actual
  regression test for this entire fix, using the real live demo practice.
  Confirm the manual Refresh button surfaces a *new* self-scheduled
  booking created after the initial page load, without a full reload.
  Confirm `removePatient()` on a synced record, followed by a manual sync,
  reproduces the disclosed reappear behavior (proving §3's limitation is
  real and the toast in §4 is accurate, not just theoretical).
- Regression: confirm every existing panel still renders correctly for a
  license with zero server-side data (new/never-synced practice) — the
  sweep finding nothing must not clear out local seed/demo data or throw.

## 6. Non-goals (explicit scope cuts, this pass)

- No delete-tombstones / real delete system (§3) — separate, larger,
  already logged as its own backlog item.
- No `updated_at`-based conflict resolution (§3).
- No background/periodic polling anywhere, including Pending Requests
  (§0) — manual refresh only.
- No push-based real-time sync (Firebase-style) — this is a pull-based
  refresh, a different and smaller thing (§0).
- Not extended to any other SAIRN app in this pass — confirmed via a
  platform-wide check that no other app has this exact bug class (10 apps
  have no comparable public-write surface at all; SAIRNcash's waitlist
  never promised a staff view). If that changes for a future app, it gets
  its own assessment, not an assumption this fix should have covered it.
