# SAIRNbiz preview check — 2026-09-29 (CC)

**Driven live against `https://sairn.vercel.app/sairnbiz.html` with real clicks.
No source was read to reach any verdict below; every claim is a thing that
happened on screen or an HTTP response that came back.**

---

## READ THIS FIRST — two blockers for tomorrow

### 1. `SB-PINNACLE-2026` / `60417293` DOES NOT WORK. She cannot sign in.

Driven twice against `POST /api/sb-auth`:

```
SB-PINNACLE-2026  login     -> 401  {"code":"INVALID_CREDENTIALS","message":"Incorrect employee ID or PIN"}
SB-PINNACLE-2026  bootstrap -> 409  {"code":"ALREADY_PROVISIONED"}
```

`bootstrap` being 409 means **there is no self-serve way back in.** The route
that mints a first Owner is closed on that licence.

This is not new and it is already written down: `docs/2026-09-03-demo-credentials.md`
row 45 carries that PIN struck through and marked **DEAD 2026-09-25**, with the
same 401 recorded in its own verification table. Nothing has changed it since.

**WHAT WORKS RIGHT NOW, driven:**

```
SB-TEST-2026  /  sairn-demo-owner  /  84350271   -> 200, role owner, token issued
```

**So tomorrow, pick one:**

* **(a) Use `SB-TEST-2026`.** Nothing else changes; it is the same app and the
  same demo company (Pinnacle Stone & Design). This is the zero-risk option and
  it is what this whole check was run on.
* **(b) Reset the PIN on `SB-PINNACLE-2026` in SQL before she arrives.** That
  needs the hash the auth endpoint expects; it is not derivable from outside and
  is not guessed at here.

### 2. NOTHING SHE TYPES WILL REACH THE SERVER. It lives in her browser only.

This is the one that matters. Every record entered in this session was accepted,
confirmed on screen, and survived a reload — **and none of it is on the server.**

Driven directly against `POST /api/sd-data` with a real owner session, after a
full sign-out/sign-in cycle:

| collection | in her browser | on the server |
|---|---|---|
| `sb_po` purchase orders | 1 | **0** |
| `sb_recv` goods receipts | 1 | **0** |
| `sb_invs` invoices | 7 | **0** |
| `sb_exps` expenses | 10 | **0** |
| `sb_vends` vendors | 7 | **0** |
| `sb_ts` timesheets | 1 | **0** |
| `sb_payruns` payroll runs | 1 | **0** |
| `sb_ap` bills | 7 | **5** |

`sb_ap` reads 5 because those five arrived **from** the seed. The two bills
entered tonight did not go back.

**PROVED AT THE NETWORK, not inferred.** Saving an expense makes exactly one
request:

```
POST /api/ledger   -> 503
```

There is **no `POST /api/sd-data`** on the save path at all. Signing in makes
fourteen `sd-data` calls, all 200 — those are the hydrate **reads**. The push
half never runs.

**AND THE ONE INDICATOR SHE COULD CHECK SAYS EVERYTHING IS FINE.** The app's own
sync state reads `sb_sync = "9/29/2026, 8:58:25 AM"` and `sb_sync_stale = false`,
and its bookkeeping (`sb_synced_ids`) lists six invoice ids as synced that the
server has never seen.

**Consequence for tomorrow:** she spends the evening entering clients, employees
and numbers. If that browser is cleared, or she opens the app on any other
machine, **all of it is gone**, and nothing warned her.

**What to tell her, in one sentence:** *"Tonight's work lives in this browser —
don't clear it, don't switch machines, and we'll export to CSV before you
finish."* Every panel has a working **Export CSV** button; that is the honest
belt-and-braces and it was not tested for content here.

---

## Tables present and missing

`tools/sairn_load_state_check.py --app sairnbiz` **cannot answer this** — it
refuses `sairnbiz` outright (`invalid choice: 'sairnbiz'`; it accepts only
sairnlaw, sairncare, sairndental, sairnroofing). It is also the wrong instrument:
it compares *reference-seed content* against repo JSON, not table existence.
Recorded rather than worked around.

Answered instead by reading every `sb_*` resource through `POST /api/sd-data`
with a real session — the same path the app uses, so it is the same answer she
will get:

**PRESENT (12):** `sb_invs` `sb_exps` `sb_ap` `sb_vends` `sb_payruns` `sb_train`
`sb_perf` `sb_hire` `sb_bud` `sb_po` `sb_recv` `sb_ts`

**MISSING (1):** `sb_incidents` — answers `provisioned: false`.

Tonight's two migrations both landed: `sb_ts`, `sb_po` and `sb_recv` all exist.

`sb_incidents` is defined in `sql/sairnbiz_data_schema.sql:246` and that file is
`create table if not exists` throughout, so **re-running it is safe and creates
the missing table.** Until then the OSHA incident panel has no server table.

**Note the 14th collection: `sb_emps` (the employee roster) is not a server
resource at all.** `/api/sd-data` rejects it by name. The roster is
device-only by design, not by failure — but the consequence is the same as
blocker 2 and it applies even if blocker 2 is fixed.

---

## What was driven, and what happened

### Employees — WORKS
Added **Dana Whitfield**, Estimator, $31.25/hr, start 03/02/2026. Toast
*"Saved – Dana Whitfield"*. Four KPIs moved together and correctly: TOTAL 8→9,
FULL TIME 7→8, AVG TENURE 5.9→5.3 yrs, AVG HOURLY RATE $22.31→$23.31.
Survived a reload.

### Timesheets — WORKS, and this panel is the best-behaved in the app
Entered 9/9/9/9/8 for Marcus Thompson. TOTAL HOURS **44**, OVERTIME **4**,
LABOR COST **$1,311**.

Checked the arithmetic: 40 × $28.50 = $1,140, plus 4 × $28.50 × 1.5 = $171,
total **$1,311**. Correct, including the 1.5× overtime multiplier.

Two things this panel does that the rest of the app should copy:

* **empty state is `--`, not `0`**, with the reason on screen: *"the figures
  above stay -- rather than 0, because nobody has said anyone worked zero."*
* **coverage is disclosed**: *"1 of 9 active employees have hours recorded. The
  other 8 are excluded from all three figures above."*

### Payroll — the "no payment" requirement is MET, with one real defect

**Met, and prominently.** The run history header reads *"**No payment is sent
from this app** — process the run through your bank or payroll provider"*, the
run is badged **"Calculation only"**, every row's status is **"Gross only"**,
and net pay reads **"needs a W-4"** rather than a number. The panel also states
that federal and state withholding are not computed. This is exactly right for
an accountant to look at.

**DEFECT — payroll ignores the timesheet.** Marcus Thompson shows **80 hours**
in payroll, the same flat figure as everybody else, immediately after a
timesheet recording **44 hours** for the week. Every full-timer is 80; the one
part-timer is 32. Payroll uses a scheduled/assumed number, and the disclosure
paragraph — which is otherwise unusually candid — **does not say so.** An
accounting professional will enter timesheets, run payroll, and reasonably
expect the two to be connected.

Run recorded: Sep 29 2026, 9 employees, gross $15,988, total $19,274.

### Purchase order → goods receipt → matched bill — WORKS, end to end

1. Raised **PO-2026-001**, Cleveland Stone Supply, $4,800. Row: RECEIVED `none`,
   BILLED `--`, status **Open**.
2. Logged a receipt of $4,800 against it. RECEIVED → $4,800, status **Received**.
3. Entered bill **CSS-7788** for $4,800 quoting PO-2026-001. Status **Open**
   (not held), and the PO's BILLED became $4,800.
4. Clicked **Pay**. Balance $4,800 → **$0**, status **Paid**, "Paid Sep 29, 2026".

**The matched bill settles.** The receipt form also states the control in plain
words: *"Enter what ACTUALLY arrived, independently of the PO. Two figures that
were typed separately are the whole point of the match — copying the PO amount
across defeats it."*

### Bill with no PO — WORKS, and the message is genuinely actionable

Entered **MSS-9001**, Midwest Stone Supply, $640, no PO. Recorded, status
**Held**, TOTAL OWED moved $22,830 → $23,470.

Clicking **Pay** on it refuses:

> **NOT PAID – Midwest Stone Supply $640: no purchase order number on this bill.
> Correct the PO, the receipt or the bill, then try again.**

Balance unchanged, still Held. A non-technical person can act on that sentence
without help. This requirement is fully met.

*Minor:* the Held row still shows a **Pay** button rather than a disabled or
relabelled one, so the refusal is discovered by clicking. The message is good
enough that this is a polish item, not a trap.

### Vendor, invoice, expense — ALL WORK, and every KPI moved correctly

* **Vendor** Cleveland Stone Supply: TOTAL VENDORS 6→7, W-9 ON FILE 5→6.
* **Invoice** Westlake Interiors LLC $7,250 (Draft): TOTAL OUTSTANDING
  $25,480→$32,730 (+7,250), the Draft line $9,640→$16,890 (+7,250), the coverage
  note *"from 6 invoices on record"*→*"from 7"*, and Kitchen Countertops (2)→(3).
  The four status figures sum exactly to the headline.
* **Expense** $915: THIS MONTH $0→$915, TOTAL RECORDED $12,484→$13,399, TAX
  DEDUCTIBLE likewise, LARGEST CATEGORY `--`→Materials.
* **Dashboard**: ACTIVE EMPLOYEES 8→9, PAYROLL/MONTH $13,488→$15,988, OPEN
  INVOICES 4→5 / $32,730 outstanding, Fabrication headcount 4→5.

**No fabricated figure was found in any KPI driven.** Every number that moved,
moved by the amount entered, and the sub-labels moved with the values — the
failure mode where a card is blanked and "4 in progress" survives beside it does
not occur here.

### Empty states — GOOD

With nothing recorded, panels show blanks and say why, rather than inventing
zeros: timesheets `--` with the sentence quoted above; *"No purchase orders
raised"*; *"No payroll runs recorded yet. Running payroll records the
calculation here."*; LARGEST CATEGORY `--`.

*One inconsistency:* on the Expenses panel, THIS MONTH shows **`$0`** while
LARGEST CATEGORY, describing the same empty month, shows **`--`**. Two cards a
few pixels apart disagree about whether an empty month is zero or unknown.

---

## Every defect found

| # | Severity | Defect |
|---|---|---|
| 1 | **BLOCKER** | `SB-PINNACLE-2026` / `60417293` is dead (401), and `bootstrap` returns 409 so there is no self-serve recovery. Already recorded as DEAD 2026-09-25. **Use `SB-TEST-2026` / `84350271`.** |
| 2 | **BLOCKER** | Nothing entered reaches the server. Save issues only `POST /api/ledger` (503); there is no `POST /api/sd-data` on the save path. 7 of 8 driven collections are 0 rows server-side. The sync indicator says fresh and the local bookkeeping lists rows the server never had. |
| 3 | HIGH | `sb_incidents` is not provisioned (`provisioned: false`). Fix: re-run `sql/sairnbiz_data_schema.sql` — it is `create table if not exists` throughout. |
| 4 | HIGH | `/api/ledger` answers **503** on every save. The toast is honest — *"SAVED HERE, NOT IN THE LEDGER: the ledger is not set up yet — run sql/ledger_schema.sql in Supabase first"* — but it names a SQL file, which is the right message for Michael and meaningless to her. It fires on every single save. |
| 5 | HIGH | **Payroll ignores recorded timesheet hours.** 80 h flat for every full-timer immediately after a 44 h timesheet, and the disclosure paragraph does not mention that hours are assumed. |
| 6 | MODERATE | **The three-way match can be made unreachable.** PO and goods-receipt vendor fields are FREE TEXT; the bill vendor is a **dropdown restricted to registered vendors**. Raise a PO against a vendor who is not on the vendor list and the matching bill cannot be entered at all. Add the vendor first, or make the PO vendor a dropdown too. |
| 7 | MODERATE | **Revenue Trend YTD is wrong.** It shows Apr 2026 $0, May 2026 $18,520, Aug 2026 $0 — while invoices dated **Jun 1** and **Jun 5** exist in the same app. June and July are missing from a chart labelled YTD. |
| 8 | LOW | Reloading the page forces a full re-login with an 8-digit PIN. Defensible security, but she should be told, because she will reload. |
| 9 | LOW | Empty-month inconsistency: Expenses THIS MONTH `$0` beside LARGEST CATEGORY `--`. |
| 10 | LOW | A **Held** bill still offers a **Pay** button; the refusal is only discovered by clicking it. |
| 11 | LOW | Two different "biggest vendor" answers on two pages — AP says *Midwest Stone Supply (by balance)*, Vendors says *Erie Insurance (by spend)*. Each states its basis, so it is honest, but it will be asked about. |
| 12 | NOT A DEFECT | The login form appearing pre-filled with `sairn-demo-owner` is **Chrome's saved-password autofill on this machine**, not the app. There is no `value` attribute on either field. She will see empty fields. |

**Nothing was fixed in code by this check.** Defects 1–4 are database and
credential state, which only Michael can change; 5–7 are behaviour changes in
`sairnbiz.html` that need their own regression tests and a review obligation,
and shipping them untested hours before an outside professional uses the app is
the worse risk. They are recorded here and in the open-work index.

---

## Resetting `SB-PINNACLE-2026` after she has finished

**Michael runs this. Nothing below was executed.**

Note first: **if blocker 2 is still open, there is nothing server-side to
reset** — her work will be in her browser, and clearing it is
`localStorage.clear()` on her machine, not SQL. The block below is what to run
once the data actually syncs, and it is correct to keep either way.

Every table is scoped by `license_hash`, which is a **hash of the licence key,
never the key itself**. Resolve it once, then reuse it.

### Step 1 — SELECT. Confirm the scope and see what is there.

```sql
-- Resolve the hash for THIS licence only, and look at it before deleting anything.
with lic as (
  select license_hash
  from public.license_keys
  where key = 'SB-PINNACLE-2026'
)
select 'sb_invs' as tbl, count(*) from public.sb_invs      where license_hash in (select license_hash from lic)
union all select 'sb_exps',     count(*) from public.sb_exps      where license_hash in (select license_hash from lic)
union all select 'sb_ap',       count(*) from public.sb_ap        where license_hash in (select license_hash from lic)
union all select 'sb_vends',    count(*) from public.sb_vends     where license_hash in (select license_hash from lic)
union all select 'sb_payruns',  count(*) from public.sb_payruns   where license_hash in (select license_hash from lic)
union all select 'sb_train',    count(*) from public.sb_train     where license_hash in (select license_hash from lic)
union all select 'sb_perf',     count(*) from public.sb_perf      where license_hash in (select license_hash from lic)
union all select 'sb_hire',     count(*) from public.sb_hire      where license_hash in (select license_hash from lic)
union all select 'sb_bud',      count(*) from public.sb_bud       where license_hash in (select license_hash from lic)
union all select 'sb_po',       count(*) from public.sb_po        where license_hash in (select license_hash from lic)
union all select 'sb_recv',     count(*) from public.sb_recv      where license_hash in (select license_hash from lic)
union all select 'sb_ts',       count(*) from public.sb_ts        where license_hash in (select license_hash from lic)
order by 1;
```

**If `license_keys` returns no row for that key, STOP.** `license_hash in
(select ...)` over an empty set deletes nothing, which is safe — but it also
means the delete below would silently do nothing and read as success. Confirm
step 1 returns a hash before running step 2.

`sb_incidents` is deliberately absent from these lists: the table does not exist
yet. Add it to both once `sql/sairnbiz_data_schema.sql` has been re-run.

### Step 2 — DELETE. One licence, one statement per table.

```sql
-- SCOPED TO SB-PINNACLE-2026 ONLY. Run inside a transaction so a wrong count
-- can be rolled back before it is committed.
begin;

with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_invs     where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_exps     where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_ap       where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_vends    where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_payruns  where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_train    where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_perf     where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_hire     where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_bud      where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_po       where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_recv     where license_hash in (select license_hash from lic);
with lic as (select license_hash from public.license_keys where key = 'SB-PINNACLE-2026')
delete from public.sb_ts       where license_hash in (select license_hash from lic);

-- READ THE ROW COUNTS ABOVE BEFORE THIS LINE.
-- rollback;   -- if anything looks wrong
commit;
```

**The employee roster is NOT in this block, and that is deliberate.** `sb_emps`
is not a server table — `/api/sd-data` rejects the name. Employees live in the
browser, so resetting them is done on her machine, not here.

**The demo seed is not re-inserted by this block either.** The seed that put the
5 bills, 6 invoices, 6 training records and 10 budget lines there is a separate
file; deleting without re-seeding leaves a correctly empty app, not a broken
one. Re-seed only if the next demo needs the sample data back.

### Step 3 — CONFIRM. Re-run step 1.

Every count should be `0`. If any is not, the delete did not cover that table
and the reason needs finding before the next demo — do not re-run and hope.

---

## What this check did NOT cover

Stated so nobody reads a clean line as a clean app.

* **Benefits, Performance, Training, Hiring, Budget, Tax & Compliance, Reports,
  Accounts Receivable, AI Assistant, Settings** were not driven at all.
* **Export CSV** was not opened on any panel; the recommendation to export as a
  backstop rests on the button existing, not on its contents being checked.
* **Print** was not exercised.
* Everything was driven on **`SB-TEST-2026`**, because `SB-PINNACLE-2026` could
  not be signed into. Table provisioning is global so that answer transfers
  exactly; row counts and demo content do not.
* The browser console was not swept for errors beyond the network layer.
* No mobile or narrow-viewport check was done.


---

# RE-RUN 2026-09-30 (CC) — THREE OF THE FOUR BLOCKERS' CAUSES WERE FIXED, AND **BLOCKER 2'S ROOT CAUSE ABOVE IS WRONG**

**VERDICT: NOT CLEAN, but no longer blocked on the app.** The two remaining
blockers are both SQL runs only Michael can do, and the four anchored code
findings are fixed, deployed and verified on the live build.

## The correction that matters

**Blocker 2 above says the save path issues `POST /api/ledger` and concluded
nothing reaches the server. That diagnosis was wrong.**

`sbBackupFetch()` has always posted to `DATA_API = /api/sd-data`. What actually
happened: `sbHydrateAll()` reads all **thirteen** `SB_SYNCED` resources at
sign-in; `sb_incidents` answers `provisioned: false` because its table was never
created; `sbReportHydrate()` set **one global boolean** (`sbBackupUnavailable`);
and `sbSyncCollection()` then returned early on it **for every resource for the
rest of the session.**

**One missing table silenced twelve present ones, before the user typed
anything** — which is why every record was accepted, confirmed on screen, survived
a reload, and existed only in that browser while `sb_sync_stale` read `false`.
`/api/ledger`'s 503 is a separate second-order GL posting and is orthogonal to it.

**PROVED BY A WRITE, which is the only thing that could settle it.** Driven
2026-09-30 on `SB-TEST-2026` with a real owner session:

```
sb_po         BEFORE 0 rows  ->  WRITE 200  ->  AFTER 1 row
sb_incidents  BEFORE 0 rows  ->  WRITE 503 NOT_PROVISIONED  ->  AFTER 0 rows
```

The endpoint was never the problem. One residue row was created and is enumerated
with its removal SQL in `docs/live-residue/2026-09-30-sairnbiz-sync-proof.json`.

## What is fixed, deployed and verified

All four anchored findings, in `sairnbiz.html`, with
`tests/sairnbiz_preview_fixes.js` (23 arms, landed at 14 failed / 5 passed).
Every marker confirmed present in the build `https://sairn.vercel.app/sairnbiz.html`
actually serves:

| # | was | now |
|---|---|---|
| **2 / 4** | one global latch disabled all 13 collections | per-resource latch; the global flag means *every* resource unprovisioned; the warning names the affected tables and the total |
| **5** | `sbWeeklyHours` returned a flat 40/16 — Marcus 80 h after a 44 h timesheet | reads the **most recent recorded week**; a recorded zero stands; the payroll row renders **(scheduled)** when the figure is assumed |
| **6** | PO and receipt vendors free text, bill vendor a restricted select | all three are the same select, filled by **one** function, refreshed on AP paint, vendor change and bill-modal open |
| **9** | Expenses `THIS MONTH` `$0` beside `LARGEST CATEGORY` `--` | one `sbEmptyOr`/`SB_NO_DATA` helper, and the **shipped markup** changed too — it read `$0` before any code ran |

## Still not clean, and neither is mine to fix

| what | evidence | who |
|---|---|---|
| **`sb_incidents` is still unprovisioned** | re-read 2026-09-30: `provisioned: false`; a write answers 503 | **Michael** — re-run `sql/sairnbiz_data_schema.sql`, `create table if not exists` throughout |
| **`/api/ledger` still 503s on every save** | unchanged | **Michael** — run `sql/ledger_schema.sql` |

**This clone cannot do either.** No `SUPABASE_URL`, no service-role key, no
`DATABASE_URL`, no `psql`, and `/api/sd-data` has no DDL path — checked, not
assumed. Until `sb_incidents` exists, the OSHA incident panel has no server table;
every other collection now backs up normally, which it did not before.

## Credentials, re-verified 2026-09-30

`SB-TEST-2026` / `sairn-demo-owner` / `84350271` → **200, role owner, token
issued.** `SB-PINNACLE-2026` was not touched — its PIN is Michael's to restore.

## What this re-run did NOT do

**It did not re-drive the click-through.** The verification above is a live
credential check, a live per-resource read of all thirteen, a live write in both
directions, and a byte check of the deployed file. **Nobody clicked through the
panels again**, so findings 7, 8, 10 and 11 — the revenue-trend chart, the
re-login on reload, the Pay button on a held bill, the two biggest-vendor answers
— are **unretested since 2026-09-29** and are not claimed fixed. Finding 7's
mechanism was confirmed by reading `sairnbiz.html:2261`: the chart sums `i.paid`,
so it is a **cash-received** chart under a *Revenue* label. That is a sharper
statement than the original and it is still not a driven one.

---

# RE-RUN 2026-09-30, SECOND PASS (CC) — EVERY FINDING RE-DRIVEN, AND ONE NEW ONE

**VERDICT: NOT CLEAN — but for one newly-found reason, not for any of the
twelve above.** All four residual findings (7, 8, 10, 11) are fixed, deployed
and driven. Both SQL blockers are gone: `sb_incidents` is provisioned and
`/api/ledger` accepts a post. What is left is a **13th finding, found by this
re-run**, and it is not fixed.

Everything below happened on screen or came back from an HTTP request against
`https://sairn.vercel.app` on `SB-TEST-2026`. The deployed file was confirmed
byte-identical to `main` before anything was driven.

## The four residual findings, each driven

### 7 — the mechanism in the original row is WRONG, and the correction matters

The row says *"June and July are missing from a chart labelled YTD."*
**June was never missing. It was labelled "May".**

`new Date(m+'-01')` is a **date-only** string, parsed as **UTC midnight** by
ECMA-262 21.4.3.2, then rendered in the **local** zone. In America/New_York
(-4) that instant is 20:00 on the last day of the previous month, so every
month drew one behind. Driven before the fix: `['2026-05','2026-06','2026-09']`
rendered `['Apr 2026','May 2026','Aug 2026']`.

**It is silent and it is directional.** Every zone west of Greenwich is wrong;
UTC and everything east is right. Nothing errors. And the **value beside the
label was correct the whole time**, which is why the original read the shifted
months as missing data rather than as mislabelled rows — there was no reason to
doubt a row whose number was right.

**Driven after the fix, same zone (America/New_York, offset 240):**

| chart | before | after | the invoices behind it |
|---|---|---|---|
| dashboard | Apr $0 / **May $18,520** / Aug $0 | May 2026 $0 / **Jun 2026 $18,520** / Sep 2026 $0 | June collected 8,420+6,000+4,100 = **18,520** |
| P&L | — | May 2026 $5,200 / **Jun 2026 $38,800** / Sep 2026 $7,250 | June invoiced 8,420+3,890+12,750+4,100+9,640 = **38,800** |

Both now agree with the invoice dates exactly.

**And the two charts were summing different things under near-identical
titles.** The dashboard summed `i.paid` under *"Revenue Trend YTD"*; the P&L
summed `i.amt` under *"Monthly Revenue Trend"*. **Relabelled, not re-summed:**
*"Cash Collected by Month"* and *"Invoiced Revenue by Month"*. Changing the
dashboard's math to invoice value would have made it disagree with the cash KPI
directly above it and duplicated a chart the P&L already carries. The KPI
itself read *"Monthly Revenue / vs last month"* over every invoice ever paid —
neither monthly nor a comparison — and now reads *"Cash Collected / All
invoices, to date"*.

### 8 — it was never security, and this doc's "defensible" is withdrawn

Driven: signed in, reloaded. **The PIN gate came up while the session was still
live in every respect.**

```
sb_session_token   still present, 339 chars
sb_session_role    still "owner"
that same token on POST /api/sd-data   ->  HTTP 200, 5 rows
```

`sessionStorage` is cleared when the **tab** closes, not when the page reloads.
Nothing had been discarded, `sbBackupFetch()` went on using the credential
while the screen said signed out, and retyping the PIN minted a **second**
session for a user who already held one. `sbApplyLoggedIn()` was simply
unreachable from boot.

**Fixed by restoring, server-checked.** Clearing would have been theatre — the
token is a signed 12-hour bearer, so deleting the browser's copy does not
revoke it. `sbRestoreSession()` asks `/api/sd-data` and believes only the
answer. The probe was checked in both directions before being relied on:

```
real token         -> 200
garbage token      -> 401 NO_SESSION
empty token        -> 401 NO_SESSION
tampered signature -> 401 NO_SESSION
```

**Driven end to end on the deployed build:**

| | result |
|---|---|
| reload with a valid session | app opens on the dashboard, header reads **Owner**, no PIN |
| reload with a tampered signature | **PIN gate**, and all three session keys cleared |

**Three answers, not two.** 401/403 refuses and clears; 2xx or 503 accepts (the
auth check runs before the provisioning check — driven); **anything else is
could-not-tell**, so the gate stays up and nothing is cleared. Folding a 500 or
an offline moment into "refused" would sign a user out of a good session and
destroy the token that would have proved it.

### 10 — the held bill says why before it is clicked

The refusal text was already good; what was wrong is that the row gave no sign
the button would refuse. The same two conditions `sbPayBill` uses are now
evaluated at paint time.

**Driven, every row of the AP table on the live build:**

```
Midwest Stone Supply   Open      Pay DISABLED   no purchase order number on this bill
Surface Solutions Inc  Open      Pay DISABLED   no purchase order number on this bill
Erie Insurance         Paid      no button      Paid --
Tooling Pros           Overdue   Pay DISABLED   no purchase order number on this bill
Eagle Plumbing Co      Open      Pay DISABLED   no purchase order number on this bill
Midwest Stone Supply   Held      Pay DISABLED   no purchase order number on this bill
Cleveland Stone Supply Paid      no button      Paid Sep 29, 2026
```

**SAY THIS OUT LOUD BEFORE THE DEMO: five of seven rows now show a disabled Pay
button.** That is not a regression — every one of those bills would have been
refused on click, because the seed bills carry no PO number. The screen now
says so instead of the user finding out. It is a visible change and it makes
the demo data look more blocked than it did.

**The enabled path is reachable and was proved, not assumed.** The one bill
with a real PO and receipt (CSS-7788 against PO-2026-001) returns `{ok:true}`
from a live three-way match and `{payable:true}` when its status is put back to
Open — so the gate has not locked everything out.

### 11 — they are different questions, AND one of them was also wrong on its own terms

Both panels were driven. They answer genuinely different questions and the
sub-labels now say which:

| | was | now | live answer |
|---|---|---|---|
| AP | Largest Vendor / *By balance* | Largest Vendor / **Most owed right now** | Midwest Stone Supply |
| Vendors | Top Vendor / *By spend* | Top Vendor / **Most paid this year** | Cleveland Stone Supply |

The sets are near-disjoint by construction: a paid bill has zero balance and
cannot appear in the first; an unpaid bill contributes nothing to the second.
Live data — balances Midwest 13,040 / Surface 8,200 / Eagle 1,850 / Tooling
380; paid-this-year Cleveland 4,800 / Erie 1,140. Two different answers is
correct.

**But AP's was also wrong on its own terms.** It sorted **bills** and took the
top row's vendor, so a vendor owed three $1,000 bills lost to a vendor owed one
$2,500 bill, under a label reading *vendor*. On today's data the same vendor
wins either way ($12,400 largest single bill, $13,040 largest total), which is
why only a fixture found it. Now aggregated by vendor, with the same name
normalisation the Vendors panel uses, unnamed vendors dropped rather than
pooled into a blank bucket that can win the card, and ties broken by name so
two renders cannot disagree.

## The rest of the twelve, re-checked against production

| # | state | evidence, 2026-09-30 |
|---|---|---|
| 1 | **STANDS — Michael's** | `SB-PINNACLE-2026` login **401 INVALID_CREDENTIALS**, bootstrap **409 ALREADY_PROVISIONED**. Unchanged. `SB-TEST-2026` / `sairn-demo-owner` / `84350271` gives **200, owner, token issued**. |
| 2 | **RESOLVED** | All 13 resources **HTTP 200, `provisioned: true`**. In the live page `sbBackupUnavailable=false`, `sbUnprovisioned={}`. A write through the app's own `sbBackupFetch` landed: server `sb_ap` **5 rows to 7**. See finding 13 for the half that is not resolved. |
| 3 | **RESOLVED** | `sb_incidents` reads **200, `provisioned: true`** (was `false`). |
| 4 | **RESOLVED** | `/api/ledger` `post` gives **200**, and the identical entry re-posted gives **409 ALREADY_POSTED** naming it, which is the read-back. `chart` and `validate` are NOT evidence — neither touches the store, so both answer 200 whether or not the table exists. One probe entry is enumerated with its removal SQL in `docs/live-residue/2026-09-30-sairnbiz-ledger-probe.json`. |
| 5 | **RESOLVED** | `sbWeeklyHours(Marcus Thompson)` returns **44** against the recorded timesheet (was a flat 80). |
| 6 | **RESOLVED** | `#popvendor`, `#rcvvendor` and `#blvendor` are all **SELECT, 7 options each** (two were free text). |
| 7 | **RESOLVED** | above |
| 8 | **RESOLVED** | above |
| 9 | **RESOLVED** | Driven on a genuinely empty month: THIS MONTH `--`, TOTAL RECORDED `--`, LARGEST CATEGORY `--`. The shipped markup defaults to `--` too, so it is right before any code runs. |
| 10 | **RESOLVED** | above |
| 11 | **RESOLVED** | above |
| 12 | **still not a defect** | The login screen came up pre-filled with `owner` on this machine. Chrome's saved-password autofill; there is no `value` attribute on either field. |

## 13 — NEW, NOT FIXED: a record entered while the sync was latched is stranded forever

**Found by this re-run, and it is the unfinished half of blocker 2.**

`sbSyncCollection(key, next, prev)` decides what to push by diffing `next`
against **`prev` — the value as it was immediately before that one save**. A
record whose change already happened, while the latch was armed, is never
offered again. Re-saving the collection pushes **nothing**, because nothing
about it changed.

Driven: the two bills entered on 2026-09-29 (`MSS-9001`, `CSS-7788`) were on
the device and **not** on the server. `sb_synced_ids.sb_ap` listed exactly the
five that were, and correctly did not list those two — **so the app knows they
were never pushed, and nothing reads that to decide what to send.** A full
re-save left the server at 5 rows. They only landed when this session called
`sbBackupFetch('write', ...)` on them by hand, after which the server read 7.

**Consequence.** Every record entered on any device during the latched window
is on that device only, permanently, while `sb_sync_stale` reads `false`. That
is the original blocker-2 symptom surviving its own fix, for the back
catalogue. Records entered **from now on** sync normally — that half is fixed
and proved above.

**The fix is not made here** because it is a new change to the sync layer that
needs its own review rather than being folded into a findings sweep. The shape:
on hydrate, push any local record whose id is absent from `sb_synced_ids`,
once, and mark it. Recorded in the defect register with that as a planned
action.

## What this re-run did NOT do

* **Benefits, Performance, Training, Hiring, Budget, Tax & Compliance, Reports,
  Accounts Receivable, AI Assistant and Settings were still not driven.** The
  original check did not cover them and neither does this one.
* **Export CSV and Print were still not exercised.**
* Everything ran on **`SB-TEST-2026`**. `SB-PINNACLE-2026` was not signed into
  and not touched.
* No mobile or narrow-viewport check.
* The console was not swept beyond what the driven steps produced.
* **How many other records are stranded by finding 13 is not known.** It was
  measured on `sb_ap` only, on one device. The other twelve collections, and
  any other device, were not counted.
