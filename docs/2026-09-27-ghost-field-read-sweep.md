# A branch gated on a field name nothing sets — the sweep

**Run 2026-09-27 (Hank).** Michael's dispatch: *"sweep for other branches gated
on a field name that exists nowhere in the payload — same shape as WV's
unreachable-message branch, the 3rd self-caught instance of this class in one
day."*

This is the second decidable member of the family
`docs/2026-09-26-ghost-failure-path-sweep.md` opened. That document found three
instances of *a verdict whose two outcomes are computed from something that
cannot differ*, decided only the first mechanically
(`tools/unreachable_failure_path_scan.py`), and named the other two as gaps.
**This closes a different one**, and the tool is
`tools/ghost_field_read_scan.py`.

---

## 1. The rule, stated so somebody can disagree with it

A finding is a property read `x.FIELD` that

1. **gates something** — it is inside an `if`/`while` condition, a ternary test,
   a `&&`/`||` operand, or under a `!`. A ghost read in a plain expression puts
   `undefined` into a value, which usually shows. A ghost read in a gate
   produces a branch that never runs, which does not;
2. is **not** a JavaScript or DOM property (`--list-builtins` prints the whole
   exclusion list, because an exclusion nobody can read is a place to hide a
   real field);
3. is **never written, never a key and never quoted anywhere in the repo** — not
   `x.FIELD =`, not `FIELD:`, not a destructured binding, not `'FIELD'` in any
   string, not a key in any tracked `.json`, `.sql` or `.csv`, and not a
   `const`/`let`/`var`/`function` declaration of that name.

Condition 3 is what makes a zero worth anything: a name that is read, never
written, never quoted, and is not a builtin **cannot have a value**.

### What it cannot see, so the gap is a decision

* A field written under a **computed key** (`row[k] = v`, `Object.assign(out,
  m)`). Then a real field looks like a ghost. This is the false-positive
  direction, which is why every finding prints its line and why the tool is
  report-only rather than a push gate.
* A field written somewhere and read **on the wrong object** — the
  `payload.check` vs `payload.requirement_type` case, member (2) of the earlier
  sweep. `check` is a real key elsewhere, so condition 3 clears it. Still
  undecided, still worth building.
* A **misspelling that collides** with an unrelated real name. Cleared by
  condition 3 and invisible to this tool.

---

## 2. The tool committed the defect it was built to catch, within the hour

Recorded first, because it is the cheapest evidence that this class is nobody
else's mistake.

The spelled universe was read from **raw text including comments**, and `*.md`
was in the source list. So the moment the fix below was written with an arm
saying *"`rfDeliveredHoursFor` must not read `actual_start`"*, the string
`actual_start` existed in a comment — **and the scan went silent about
`actual_start` for ever.** Writing the regression test for a dead field name
disabled the standing detector for that same name.

That is PR §1.1, *a check that stopped checking*, committed by a tool whose
entire subject is a condition that cannot fire.

**It was caught by the control, not by review.** `MUTATION 1` restores the real
shipped pre-fix body into the real `sairnsenior.html` and demands the scan name
`actual_start`; it did not. The spelled universe now comes from **code and data
and never from prose** — comments stripped from `.js`/`.html`/`.py`, strings
kept (a string key is a real spelling), and `.md` excluded outright. The cost is
that a field defined *only* in a markdown spec reads as a ghost; that is the safe
direction and it is in the tool's header rather than left to be discovered.

---

## 3. The result

    python tools/ghost_field_read_scan.py

**665 files scanned for gates, 42k distinct field spellings, three buckets.**
The buckets exist because *"no client sends this yet"* and *"this gate reads the
wrong field"* are not the same finding and a single list makes both harder to
read.

| Bucket | Count | What it means |
|---|---|---|
| **FINDINGS** | 40 | A gate whose field is unspelled anywhere. Triaged in §5. |
| **Declared third-party contracts** | 61 reads | A field owned by somebody else's API — it *cannot* be spelled here. Each declaration names the owning contract, and **a declaration that matches nothing is reported**, so the list cannot rot silently. |
| **Request fields no caller sends** | 2 | `payload.X` / `body.X` in an `api/` handler. Usually dormancy. |

---

## 4. Three confirmed, all fixed in this change

### 4.1 `api/_lib/compliance-rules.js` — the window that counted everything

**Shipped this morning, in my own item-4 change, and found by this scan hours
later.**

`hoursInWindow()`'s `facility_training_year` branch read
`from = trainingYearStart || null` and fell through. `trainingYearStart` is
`opts.facility_training_year_start` — a name that is not written, keyed or quoted
anywhere, and that `api/sd-data.js` does not accept. The per-record filter below
it is `if (from && ...)`, so **a null `from` skipped the date filter entirely and
every training record in the table counted** — a 2019 certificate satisfying a
2026 annual requirement.

**That is the over-counting direction**: it reports a staff member with a real
shortfall as compliant. And the path was reachable, not theoretical — the
endpoint *accepts* `annual_window: 'facility_training_year'` and validates it as
a known window.

**Fixed** to fail closed in the shape `NO_HIRE_DATE` already had twenty lines up:
`window_error: 'NO_TRAINING_YEAR_START'`, no hours counted, verdict `null`
rather than `true`. Until some surface supplies a facility training year this
window is unavailable **and says so**. Five arms, section 4e of
`api/_lib/compliance-rules-staff-join.test.js`, including both control
directions (with a start date supplied, the same ancient record is excluded by
the *date*; a record inside the window *is* counted).

### 4.2 `sairnsenior.html` — `0.0 h` for every referral source, always

`rfDeliveredHoursFor(clientId)` read `v.actual_start` and `v.actual_end`. A
`sen_visits` row has no such fields — the clock is `clock_in_at` /
`clock_out_at`, which the authorisation burn-down (~:2540), the visit card
(~:2964) and `visitHours()` (~:3925) all use correctly. **The guard was true for
every visit ever recorded and the function returned 0 for every client.**

**Why the zero was worse than a blank.** The renderer already distinguishes
them: `p.linked ? p.hours.toFixed(1)+' h' : '--'`. An *unlinked* source
correctly shows `--`. A *linked* one showed `0.0 h` — which reads as *"we
looked, and this source's clients received no care"* — against real clocked
visits. The fabricated-KPI shape reached through a field name rather than a
hardcoded number, so Guardian's fabrication check could not see it.

**The comment above the function was already the specification** and the code
disagreed with it: *"reuses the same only-count-what-was-actually-clocked rule
the authorisation burn-down uses"* was true of the intent and false of the field
names. It now really does reuse it, by calling `visitHours()` rather than
carrying a third copy — that function's own header says it exists so *"a claim
and an insufficient-hours finding must never silently diverge on this
arithmetic"*, and this was the divergence it was written to prevent, one caller
along. Same script block, checked rather than assumed.

**And the fix's first version introduced a second defect, caught by its own
suite on the first run.** The old code ended `if(isFinite(ms)&&ms>0)`;
`visitHours()` has no such guard, so a row whose `clock_out_at` precedes its
`clock_in_at` returns a negative and would have **silently cancelled a real
visit's hours** out of the source total. Arm B6 caught it. The positive guard is
kept at the call site.

> **Flagged, not fixed:** `visitHours()` itself has no non-negative guard and
> `generateClaim()` bills `hoursBilled = visitHours(v)` straight off it, while
> the burn-down at ~:2540 *does* guard. The three consumers do not agree.
> `api/_lib/sen-evv-clock.js` refuses `CLOCK_OUT_BEFORE_IN`, so the server
> cannot store such a row **through that path** — local rows predating the
> module are not covered. Changing `visitHours()` touches claim generation and
> is its own change.

### 4.3 `api/sd-data.js` — a money reconciliation against nothing

`derive_charges` read `invRows[0].data.charge_lines` to compare freshly derived
charges against the invoice already on file. **No write path on this platform
stores that key.** `sairncare.html` writes `month`, `room_board_amount`,
`care_amount`, `private_total`, `hcbs_claim_amount`, `care_level_breakdown` and
`revision_history` — and no per-event lines at all.

So `priorLines` was always `[]`, and `reconcileAgainstInvoice(derived, [])`
answers: **every derived line ADDED, nothing removed, nothing changed,
`net_change` = the entire amount** — with `invoice_exists: true` beside it, which
is what made the figure look like a comparison. On the view this branch's own
comment calls *"the audit trail that replaces the manual reconciliation"*.

**The argument for this fix was already written directly above it**, one case
over: the 2026-09-04 fix for an *unreadable* invoice says *"this fell back to
[], so the reconciliation reported EVERY derived line as new … Somebody
regenerates on the strength of that."* The read below it then did exactly that
for an invoice that was read perfectly well.

**Fixed as a third state, not a better guess:** `reconciliation_vs_invoice:
null` plus `reconciliation_unavailable: 'PRIOR_INVOICE_HAS_NO_CHARGE_LINES'` and
a sentence saying why. **And the client half too, deliberately** — the renderer
guards on `invoice_exists && rv`, so a null would have replaced a wrong figure
with *silence*, leaving the same person to make the same decision with no more
information. `sairncare.html` now renders the reason.

> **This one is still an open FINDING in the scan and must stay that way.** The
> fix made the impossible comparison honest; it did not make `charge_lines`
> exist, so the capability check still cannot pass. The control probe asserts
> the scan **does** report it — an arm demanding silence there could only be
> satisfied by hiding a true finding. It clears when the invoice write path
> stores line detail, which is the real follow-up.

---

## 5. The remaining 40, triaged

**No row below is fixed here.** Each is a real unspelled gate; most are
harmless, and the three that are not are named as such. Fixing nine findings in
a 2MB file is its own change with its own verification.

### Alias fallbacks that can never fire — inert, not harmful

The read is the *second* operand of a `||` chain whose first operand is the real
field. The code works; the fallback is dead weight and a reader may believe a
second spelling is supported.

| Where | Read |
|---|---|
| `api/alf-alerts.js:143` | `d.medication_id \|\| d.med_id` |
| `api/sd-data.js:7878`, `:8199` | `[d.contract_value, d.total, d.amount, d.quote_total]` |
| `api/sd-data.js:10290` | `d.attendees \|\| d.attendee_ids` |
| `api/_lib/deadline-engine.js:5110` | `tdr.expiry_label \|\| 'a ' + WEEKDAY_NAMES[…]` |
| `tools/invariant_registry.js:191` | `w.retainage_accrued \|\| w.retainage_held \|\| 0` |
| `api/sd-data.js:12116` | `req.headers['x-sv-witness'] \|\| body.witness_token` (request bucket) |

### An injected hook nothing wires

`api/_lib/job-risk.js:190` — `job.supplier || (ctx.defaultSupplierFor ? ctx.defaultSupplierFor(job) : '')`.
No caller supplies `defaultSupplierFor`, so the ternary always yields `''`. An
extension point with no extender; the same shape as an engine with no caller.

### A dead parameter on an accounting function

`api/_lib/ledger.js:361` — `entry_date: isDate(input.reversal_date) ? input.reversal_date : today`.
Nothing can pass `reversal_date`, so **every reversal is dated today**. Dating a
reversal today is defensible accounting; the finding is that the function's
signature promises a capability it does not have. Worth a decision, not urgent.

### Worth reading before dismissing

| Where | Read | Why it is not obviously inert |
|---|---|---|
| `api/_lib/deadline-engine.js:4677`, `:4689` | `e.disposition_date` | `undisposed = qualifying.filter(e => !toUTC(e.disposition_date))` — so **every qualifying event is "undisposed"**, and `dispositions` is an array of `undefined`. Not an alias fallback. Needs its own look. |
| `stonedesk.html:41397-8` | `r.loan_type`, `r.interest_rate` | Two reads on the same two lines, in a financing calculation. |
| `stonedesk.html:12328` | `j.installDate` | |
| `stonedesk.html:29809` | `q.projectAddress` | |
| `stonedesk.html:34909`, `:35180`, `:36805` | `x.referred`, `x.lastService`, `x.nextService`, `x.course` | Four CRM/service fields in one app. |
| `stonedesk.html:12765` | `data.imageUrl` | |
| `stonedesk-hr.html:273` | `date.Great` | Almost certainly a parse artefact; listed rather than dropped. |

### Test-harness option flags that cannot be enabled — SETTLED 2026-09-27

A fault-injection or stub option that **no caller ever passes**, so that arm of
the harness can never run. This is the fault-probe equivalent of the class: a
sabotage that cannot be applied looks exactly like one that was applied and
caught.

**All nine are now settled.** Six were real uncovered failure modes and are
**driven**; three are scaffolding and carry a **verdict comment at the knob**, so
the next reader — and the next scan run — sees the decision in place rather than
re-deriving it. Nothing was deleted: deleting a knob deletes the record that the
case was considered.

| Knob | Verdict | What was done |
|---|---|---|
| `tests/template_migration_orphaning.js` `opts.rawOk` | **real, safe direction** | The 2026-09-04 fix checked `tmSave()` and left `stRaw(FLAG,'1')` on the very next line unchecked. Fails safe (no flag → retry, and `have[id]` makes the retry harmless) and the code *says* so — now 5 arms assert it instead of a comment, including that the retry is idempotent and that no error is shown for a failure with no user-visible consequence. |
| `tests/sd_data_unconfirmed_write_review_probe.js` `opts.patchStatus` | **real gap in a review** | The review answered "is 404 right for a zero-row PATCH" and never asked what happens when the PATCH is **refused**. Added as QUESTION 1b: a refused PATCH is a *third* answer (502, upstream body logged), not a reuse of 404 or of `WRITE_UNCONFIRMED`. Named dependency recorded: the refusal's 502 carries no `code` where `WRITE_UNCONFIRMED`'s does. |
| `tests/faults/grd_write_faults.js` `opts.noGps` | **real, and the worst place for it** | A fault probe with an uninjected fault. `addCoursePoint`'s *first* guard — no GPS fix, refuse outright — was never driven. 2 arms: the refusal is the last thing the user sees, and nothing is appended to the zone, pushed, or re-rendered. |
| `tests/run_sairnlaw_rate_limit_probe.js` `o.racyStatus` | **real, and the one case the file's own standard demanded** | Section D covers every way the *RPC* can fail; this is the layer below — RPC gone **and** the fallback's own window read failing. Measured: it **throws**, `wexLookup` does not catch, and `api/legal-reference.js`'s outer catch turns it into 502. Fail-closed, so **no request reaches Cornell**. 4 arms assert "never proceeds" rather than a particular shape, plus the paired positive. *Flagged, not fixed:* the throw escapes the `{ok:false, code}` vocabulary every other branch of `api/_lib/wex.js` maintains. |
| `api/sd-data-alf-training-join.test.js` `opts.rulesStatus` | **real, third read in the branch** | `credStatus: 404` and an absent roster were driven and argue the same point; the **rules** table — whose absence produces the most convincing wrong answer, "no requirement to compare against" — was not. 3 arms (404, 500, control). |
| `api/sd-data-family-contacts.test.js` `opts.marStatus` | **real, other half of a driven case** | `marNonArray` (the page parsed, wrong shape) was driven; a page the store **refused** was not. 2 arms: a mid-pagination refusal must not serve the pages that already arrived. |
| `tests/failsafe/failsafekit.js` `o.employeeLookupFails` | **covered elsewhere — kept** | The fail-closed behaviour it would drive is asserted four times in `api/sv-witness.test.js` as `WITNESS_CHECK_FAILED` (503), through that endpoint's own harness. This file's arms are about *interruption*; a second copy of an existing assertion is a second thing to drift. Verdict written at the knob. |
| `tests/sairnscape_memory.js` `opts.cloudBody` | **unbuildable, not untested — kept** | Only `cloudDead: true` is ever passed because **`api/memory-cloud` does not exist**. The resolve branch is a placeholder for an endpoint nobody has written. Kept so the shape is ready; the verdict is written at the knob **because a reader seeing a cloud branch in a passing suite would reasonably believe the cloud path is covered, and it is not — it does not run.** |
| `tests/sairnbiz_timesheet_hours.js` `opts.noRender` | **cosmetic — kept** | The only one of the nine that guards nothing a failure mode depends on; skipping the initial render just saves work. No arm to add. Verdict at the knob. |

#### And settling them found three suites red on `main`

Running each suite in order to judge its knob is what surfaced these. None was
caused by this change, each was confirmed pre-existing by stashing, and all three
are now green.

1. **`tests/sairnbiz_timesheet_hours.js` was 46 arms red** with
   `ReferenceError: sbOtThreshold is not defined`. The configurable overtime
   threshold landed 2026-09-26 and this suite's hand-kept `fnBody(...)`
   extraction list was not updated, so **46 of 63 arms failed on a correct
   file** — the sixth recorded instance of that class. Repaired by extracting
   the three real functions (`sbCfg`, `sbOtThreshold`, `sbOtThresholdNote`),
   not stubs: the threshold decides a money figure, and a stub would test the
   harness's opinion of it.
2. **Then six of those arms failed for a second reason, and the instrument was
   wrong rather than the code.** `callHandler` counted the *first* fetch as the
   auth read and every later one as a write. That held until a second read
   appeared ahead of the write — the single-entry-point active-credential
   re-check — after which every refusal arm reported `reached storage before
   being refused` against a handler that had refused correctly and written
   nothing. `wrote` is now decided by the **method**, which is a property of the
   handler; ordering never was.
3. **`tests/sairnscape_memory.js` had one arm red against correct code.** It
   read `html.slice(at, at + 1200)` to find a line that really is present — but
   `scpData` grew a 35-line comment block on 2026-09-21 and pushed the line past
   character 1200. A fixed character count is a guess about how long a function
   will stay; the closing brace is the fact. Now brace-matched.

#### One product tension surfaced, flagged and NOT settled by me

`tests/sairnbiz_timesheet_hours.js`'s "a clean week carries no note" arm went
false because `rTS()` now **appends** `sbOtThresholdNote()` to `ts-note`
unconditionally. That was deliberate and says so in place — *"a configurable
number that silently changes a money figure"* must always be visible. But this
arm's own comment argues the opposite for the same element: *"a disclosure that
is always on stops being read."* **Both arguments are reasonable and they now
share one element**, so the exclusion sentence arrives appended to a sentence the
reader has learned to skip. The arm was repaired to assert its real property (no
exclusion sentence on a clean week) and the tension is recorded there. It is a
product decision, not a test fix.

### Request fields no caller sends — dormancy

`api/sd-data.js:1670` — `observeReceipt(row, payload.ordered_at, payload.received_at)`
on `sd_supplier_lead_times`. `observeReceipt` returns `applied: false` without
both dates, so the endpoint would answer **400 BAD_OBSERVATION** on every call.
But the name is self-consistent inside that handler — its own comment documents
*"observe — a REAL receipt (ordered_at, received_at)"* — and the real finding is
that **nothing in any app calls `mode: 'observe'` at all**. Dormancy, not a
wrong field, which is why the tool reports it in a separate bucket.

---

## 6. The control, and what a pass does not mean

`tests/run_ghost_field_read_probe.py` — `CONTROLS_FOR =
['tools/ghost_field_read_scan.py']`, both directions.

**MUTATION 1 restores the real shipped pre-fix `rfDeliveredHoursFor` body into
the real `sairnsenior.html`** and demands the scan name `actual_start` *and* the
file. **MUTATION 2 is labelled SYNTHETIC in its own output**, because the
`facility_training_year_start` and `unmapped_requirements_pending` shapes were
both caught in session and never reached a commit — `git log -S` finds the
latter only inside two commit *messages* describing it. A fixture's provenance
is stated rather than implied.

Both files are restored and compared **byte-identical**, the finding count is
asserted back to its baseline, and a missing anchor is reported as
`ANCHOR NOT FOUND … this mutation did NOT run` rather than passing.

**A pass means the scan reports the shape it claims to report and is silent on
the shipped tree.** It does not mean the scan finds every wrong-field gate — the
tool's header names the two members of the family it cannot decide, and no
control can close a gap the tool does not attempt.
