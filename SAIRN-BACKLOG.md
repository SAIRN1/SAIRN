# SAIRN Backlog

Deferred items — not urgent, not forgotten. Pick up at a natural pause,
not mid-session. Each entry: what, why deferred, what "done" looks like.

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

## Rebuild graphify's knowledge graph, properly scoped

**Logged:** 2026-08-07

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
problem will recur otherwise. The `graphify` skill is set to `"off"` in
`.claude/settings.local.json`'s `skillOverrides` until this is done —
its current output shouldn't be treated as authoritative for duplicate-
feature checks in the meantime.
