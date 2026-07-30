# StoneDesk — Session 77 Handoff

Follow-up to the non-functional-button audit flagged in `EMERGENCY-HANDOFF.md`.
Audit findings were independently re-verified against the live file before
acting on any of them (line numbers, function-existence claims, blob hash
all checked directly) — one of the three findings turned out to be
described incorrectly and was corrected before fixing, not fixed blind.

## 1. Verified current state

- `main` HEAD (local and pushed): `d44a3d180a33bb50f7e553ddf6a2d1baa7bf53d1`
- Local checks re-run fresh at this HEAD: `checkblocks.py` 119/119,
  `div_balance_check.py` 4611/4611 balanced, `duplicate_global_check.py`
  685/0 duplicates.

## 2. Finding 1 — dead `tmplExport()` button: fixed, live-verified

Confirmed exactly as reported: the "Export" button in
`panel-templates` (L25720) called `tmplExport()`, which had zero
definitions anywhere in the file — a `ReferenceError` on click. Sibling
`tmplAdd()` (L29722) was real; this one wasn't.

Implemented as a real CSV export over `tmplRecords`
(`sd_template_records`), mirroring the existing `custExportCSV()`/
`warrExportCSV()` pattern: customer/job/date/tech/method/cncStatus/
dxfName/notes/createdAt columns, `showToast()` empty-list guard
(matching `tmplSave()`'s own existing `showToast` usage), success toast
on completion. Commit `5bfb0e9`.

Live-verified both paths: empty-state toasts "No template records to
export" with no error; with a real record present, a real
`data:text/csv` anchor is built and clicked, "Templates exported"
toasts. No residual test data left in `tmplRecords`.

## 3. Finding 2 — `photoExport()`: audit's framing was wrong, corrected before acting

The audit described this as "an Export button that does not export."
**That premise didn't hold on verification.** `grep -n "photoExport"`
returns exactly one hit in the whole file — the function definition
itself (L17388, pre-deletion). No `onclick="photoExport()"`, no caller
of any kind, anywhere. It was fully orphaned code, not a live UI
element with a misleading label. The real, working "Export" button in
the photo area calls a completely different function —
`sdPhotosExport()` (L4478/L4566) — a genuine CSV export over
`sdPhotos`, confirmed unaffected and still real after this session's
changes.

This distinction was surfaced explicitly before acting on the original
"relabel it" framing, since relabeling a function nothing calls would
have changed nothing visible. Once corrected, the call was: delete the
orphaned function. Done — commit `d44a3d1`, live-verified
(`typeof photoExport === 'undefined'` on the live deploy, `sdPhotosExport`
and `tmplExport` both confirmed still real/callable).

**Lesson for whoever reads this next:** an audit document's specific
claims (line numbers, "this function exists," "this is wired to a
button") are worth independently re-checking before acting, even when
the rest of the document verifies correctly — Finding 1's claims were
all exactly right; Finding 2's central premise (a live mislabeled
button) was not. Partial accuracy in a document doesn't make every
claim in it safe to act on without checking.

## 4. Deferred architecture list — StoneDesk is NOT "clean" (3 items, verified)

None of these are crashes. None are fixed. **Do not write "zero open
items" or "100%" for StoneDesk until these are fixed or explicitly
retired.** This list started as a 5-item claim from an incoming audit
document; 2 of the 5 were independently checked and found stale
(already fixed in earlier sessions), then a corrected 3-item version
was cross-checked line-by-line before being accepted here — see §4.4
for the method and what was dropped.

### 4.1 `panel-remnant` double-render

Two separate, both-live render functions: `sdRemnantRender()` (L22471,
targets `#rem-list`) and `remRender()` (L29116, targets a second
container `#rem-grid`, L22573). Both are called on panel show (L27917).
A second bug rides on the same duplication: the search/filter inputs'
`oninput`/`onchange` call only `remRender()`, so typing in the search
box updates the grid and leaves the table stale. Confirmed via direct
grep of all four locations, not assumed.

### 4.2 Three `stonedesk-demo` fallback sites

Exactly 3 occurrences (L12859, L21382, L21489), each an independent
fallback for an unset license key, each able to diverge from
`sdData()`'s identity resolution since they're three separate
expressions rather than one shared helper.

### 4.3 Parallel template modules

- `tmRecords` + `TM_KEY='sd_templates'`, raw `localStorage`
  (`tmLoad()`/`tmSave()`, lines ~6991-7008). Its own live UI —
  `tm-modal` (L6898) and `tm-detail-modal` (L6973) — confirmed real and
  referenced by actual open/close functions (L7012/7018/7197/7199), not
  orphaned; this module is a genuine second, functioning
  template-tracking system, not dead code.
- `tmplRecords` + `'sd_template_records'`, via `sdLoad()`/`sdStore()`
  (lines ~29721+, the module `tmplExport()` was added to in §2).

**Not fixed this session** — do not merge these keys/modules without
first checking which one the live `panel-templates` UI actually renders
from; the wrong merge direction would silently orphan real user data,
same risk class as every other storage-key collision fixed elsewhere
this session (StoneDesk and SAIRNbiz both).

### 4.4 Method note — what was dropped from the original 5-item claim, and why

Two items from the original claim were checked and found stale before
being accepted into this handoff:

- **"Duplicate `renderCustomers()` in panel-customers/panel-comms"** —
  closed, not current. An in-file comment (L1335-1339) documents that
  the early stub shadowing `renderCustomers()` was already deleted in
  an earlier session after a Playwright test against production proved
  it was dead code; one real definition remains (L17182).
  `duplicate_global_check.py` independently confirms 0 duplicate names.
  `renderComms()` was never duplicated either (defined once, L1340).
- **"panel-slabs carries 2 stale modals"** — misattribution, not a real
  item. `panel-slabs` spans L5310-5473 exactly (confirmed by reading
  its closing `</div>`); it contains zero modals. `slab-action-modal`
  (L5474) sits one line *outside* it and is live, referenced 14 times.
  The two modals actually meant were `tm-modal`/`tm-detail-modal` —
  real, but belonging to the `tm*` module, not `panel-slabs` — folded
  into item 4.3 above instead of standing alone.

Both drops came from a grep hit landing inside an explanatory comment,
or a DOM element being attributed to the wrong panel by proximity
rather than actual containment — the same failure mode as this
session's `photoExport()` correction in §3. **Bound the panel by its
real open/close tags, enumerate actual callers, and strip comments
before counting anything as a finding** — a rule now worth carrying
into every future StoneDesk audit, not just this one.

## 5. Standard verification reminder

Verify `main` HEAD and `origin/main` match, re-run the local checks in
§1, and live-verify against `sairn.vercel.app/stonedesk` before trusting
any specific claim above — including this one. In particular: this
session's push required a retry (first two attempts hit a client-side
timeout with no clear server-side failure; a third attempt with a
shorter internal timeout succeeded immediately) — if a push appears to
hang, retry once with `git push -v` before assuming something is
actually broken.
