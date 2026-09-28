# Authentication-shaped fields — the gap neither axis expresses, measured

**Written 2026-09-27 (Hank), closing the open gap note in
`docs/CRITICALITY-TIERS.md` §2.** That note says:

> authentication-shaped material — a policy number, an account number, a licence
> number joined to its carrier or issuer — is not commercial sensitivity at all.
> It is what a fraudulent claim or a call to the issuer needs.
> `mech_insurance_policies.policy_no` is the live example. **A tier is the wrong
> instrument for it:** the fix is not to raise a row's axis, it is to keep the
> field out of reads that do not need it, and neither axis of this register
> expresses that.

It was recorded as *a gap with an owner*. This is the scoping it was waiting for:
**how big is it, does it need its own axis or flag, and what changed as a
result.**

---

## 1. The measurement, which is what decides the remedy

**Ten distinct authentication-shaped field classes exist on this platform**, not
one — so the gap is systemic and `policy_no` was only the instance somebody
happened to be looking at:

| Class | Files naming it |
|---|---|
| insurance policy number (`policy_no`, `coi_policy_no`) | 11 |
| licence number (`licence_no` / `license_no`) | 8 |
| payer member id (`member_id`) | 12 |
| NPI | 7 |
| EIN / `tax_id` | 7 |
| slug / tenant key (`*_slug`) | 23 |
| DEA registration | 2 |
| SSN | 2 |
| payer id (`payer_id`, `primaryPayerId`) | 1 |
| VIN | 1 |

**But "a file names it" is not the thing that matters.** The harm is a field
leaving the server to somebody who does not need it, so the population that
counts is **READ column lists**. Measured over every `api/*.js` and
`api/_lib/*.js` — both literal `select=` strings and the named column-list
constants they are built from, because a literal-only scan sees three of four:

**Four read sites on the whole platform.**

| # | Site | Field(s) | Verdict |
|---|---|---|---|
| 1a | `api/sd-data.js:2090` `insCols` → `read` | `policy_no` | **Needed.** `sairnmechanical.html:3019` renders it in the insurance table. |
| 1b | same list → `readiness` | `policy_no` | **NOT needed — FIXED.** See §3. |
| 2 | `api/sd-data.js:7582` `subcontractors` read | `coi_policy_no`, `licence_no` | **Needed**, and already **A/A** for exactly this reason. |
| 3 | `api/sd-data.js:9315` `ENT_SELECT` | `tax_id` | **Needed.** `sairnroofing.html:3785` renders it. One inconsistency flagged in §4. |
| 4 | `api/sd-sub-data.js:53` `COMPLIANCE_COLUMNS` | `coi_policy_no`, `licence_no` | **Needed**, same row class as (2). |

---

## 2. The decision: no third axis, and no new scanner

**No third axis on `CRITICALITY-TIERS.md`.** The register's axes are
**row-level**; this is **field-level**. A row carrying one policy number among
eighteen columns is not "more confidential" — one field in it is
*differently dangerous*, and a letter on the row cannot say which field. Adding a
third axis would force a re-read of every registered row across the platform and
**would not change one line of code**, which is the definition of the wrong
instrument. §2's own sentence already reached this conclusion; the measurement
confirms it rather than revisiting it.

**And no new scanner either, which is the less obvious half.** The honest reason
is the number four. A checker that reports the same four known rows on every run
is the always-passing checker this repo has measured and named — `checkblocks.py`
always exited 0 and nothing noticed, *because a checker that always passes looks
exactly like a codebase that is always clean*. Worse, the set only changes when
somebody adds a column-list constant, which is a code review away from the rule.

**What replaces both:** the four sites are audited here, by name, with the
verdict and the consumer that justifies it; the one that was not justified is
fixed; and the rule is written where a fifth site would meet it — in
`CRITICALITY-TIERS.md` §2, next to the axes a new row is read against.

> **The counter-argument, named rather than omitted.** Four is today's number and
> a hand audit goes stale the moment a fifth read is written — which is item 8 of
> the cross-domain disciplines, *nothing announces the day a check stops testing
> anything*. The answer is not "trust the audit": it is that
> `tools/ghost_field_read_scan.py` already enumerates column-list constants as a
> side effect of its own job, so the measurement in §1 is **reproducible in one
> command** rather than being a number in prose. If the count grows past a
> handful, build the checker then — and that threshold is stated here so the
> decision is re-openable on evidence instead of by feel.

---

## 3. What actually changed

`api/sd-data.js`, the `mech_insurance_policies` branch. One column list became
two:

* `read` fetches `policy_no` — the insurance table renders it.
* `readiness` **does not**.

**`readiness` never returned it.** `coverageReadiness()` builds per-requirement
lines carrying `policy_id`, never `policy_no`; the column was fetched and
discarded. So this narrows what the surface carries **without changing a single
answer it gives** — which is why it was safe, and exactly why nothing would have
noticed a later edit putting it back.

**Both actions are open to ANY verified `sairnmechanical` session.** Only `write`
is management-gated. So `readiness` was the broader of the two carrying the
material.

Three arms in `api/sd-data-mech-insurance.test.js` hold it: `readiness` does not
fetch it, `read` still does (dropping it there would be a deleted feature, not a
fix), and a **control** that `readiness` still fetches every column the
comparison needs — so the change is a narrowing and not a broken select.

---

## 4. Two things recorded rather than decided

Both are product calls, and neither is mine to take.

**(a) `read` hands `policy_no` to a technician.** It returns the raw rows to
every authenticated role, because the insurance panel renders the number. Whether
a technician should see the company's policy numbers is a real question with a
real cost either way — withholding it means the panel shows a dash to most of
the shop. The field-level remedy §2 describes would be to withhold it by role in
the response rather than to stop storing or fetching it.

**(b) `rf_entities`' gate allows a third role its own refusal text excludes.**
The 403 reads *"Entity structure and consolidated figures are management-level
information"*, and the gate is
`!MANAGEMENT_ROLES[role] && !BROAD_READ_ROLES[role]` — where
`BROAD_READ_ROLES` is `owner, admin, estimator`. So an **estimator** reads the
firm's EIN past a message saying the information is management-level.
`MANAGEMENT_ROLES` is `owner, admin`. Either the message or the gate is wrong;
they cannot both be right, and which one to change is a decision about what an
estimator's job needs.

---

## 5. What this does not cover

* **`*_slug` — 23 files, and deliberately out of scope here.** A slug is a tenant
  key, not an issuer credential, and the register already handles the sharp case
  the right way: `dnt_settings` was moved **C→A** because `booking_slug` is *"the
  tenant key an unauthenticated public booking and COMPLAINT surface resolves
  by"*. That is a row-level exposure a row-level axis expresses correctly, which
  is the opposite of this gap.
* **`member_id` (12 files) and NPI (7).** Neither appears in any read column list
  measured in §1 — they live inside jsonb blobs, which this measurement cannot
  see, because a `select=data` fetches whatever the blob holds. **That is the
  real hole in §1 and it is stated rather than left as a clean number:** a
  blob-carried authentication-shaped field is invisible to a column-list audit
  by construction. Sizing that needs the blob-shape work `api/_lib/blob.js` began
  and is its own piece.
* **SSN and DEA.** Two files each, and neither is in a read list here. DEA in
  particular is a controlled-substance registration and would be the sharpest
  instance on the platform if it ever reached one.
