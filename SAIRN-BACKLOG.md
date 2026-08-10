# SAIRN Backlog

Deferred items — not urgent, not forgotten. Pick up at a natural pause,
not mid-session. Each entry: what, why deferred, what "done" looks like.

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

**Logged:** 2026-08-09

**What:** `saveInvoice()`'s "already invoiced" check reads a local
snapshot of `invoices()` and, if no existing invoice references the
proposal, writes a new one. Zero race window on one device (no
`await` between read and write), but two staff on two different
devices/sessions could each pass the check before either's write has
synced, producing two invoices for the same approved proposal.

**Why deferred:** Needs a real server-side unique constraint on
`proposal_id` for the `sdn_invoices` resource (or an upsert-by-
proposal-id write), same scope-class as the other server-sync/
atomicity gaps in this backlog.

**Done looks like:** The invoice write goes through a server route
that rejects a second invoice for a proposal that already has one,
atomically, rather than relying on a client-side pre-check.

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

**Why deferred:** Needs a real server-side atomic check-and-write on
the trust-transaction resource (reject the write if the balance would
go negative as of the moment the server actually processes it, not as
of when the client last read it) -- same scope-class as the SAIRNlegacy
reservation lock and SAIRNbuild server-sync gaps above, not a quick
patch.

**Done looks like:** The disbursement write goes through a server
route that atomically re-validates the balance at write time and
rejects the transaction if it would go negative, with the client
showing the real rejection reason -- not just a client-side pre-check
with an honest limitation comment bolted on.

## SAIRNlegacy merchandise reservation needs a real server-side lock

**Logged:** 2026-08-09

**Priority: highest in this backlog** — real risk of the same physical
casket/urn getting promised to two grieving families. Found by the
first full silent-failure-sweep + adversarial-review pass on
`sairnlegacy.html`.

**What:** `confirmReserve()` (merchandise reservation, the "moat" panel)
re-checks a unit's status right before reserving it, but that check
reads `merchUnits()` -- this device's own localStorage -- not a server
round-trip. `leg_` resources have no server route yet. Two staff on two
different devices, each holding a stale local copy, can both pass the
check and both reserve the same physical unit. The panel's own UI text
and an in-code comment both claimed this was "checked server-side" --
corrected tonight to describe what actually happens (same-device
safeguard only), but the underlying gap is unfixed.

**Why deferred:** Needs a real server-side atomic check-and-set
(reserve only succeeds if the row is still `Available` at write time),
which means `leg_merch_units` needs a real `api/sd-data.js` route with
that semantics built in -- not a quick patch, same scope-class as the
SAIRNbuild server-sync gap above.

**Done looks like:** `confirmReserve()`'s actual reservation write goes
through a server route that atomically fails if another reservation
already landed first, and the honest failure message tells staff to
pick a different unit -- not just a local-storage re-check with an
honest disclaimer bolted on.

## SAIRNbuild has zero server-side backup for any real business data

**Logged:** 2026-08-09

**Priority: highest in this backlog.** Found during the first full
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

**Why deferred:** This is a real architecture decision -- wiring 16+
resources to real server persistence, matching the pattern already
built for SAIRNgrounds/SAIRNscape/SAIRNcode/SAIRNvet -- not a bug fix.
Same scope-class as the Vendor Ordering Catalog build. Doing it rushed,
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
