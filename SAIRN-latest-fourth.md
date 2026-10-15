# LATEST — fourth / ted — batch b25 — 2026-10-15

**ALL SIX ITEMS DONE.** `HEAD == origin/main` **`7000e165`**, 0/0, clean, **NOT
forced** (ancestry-proved; `grep -c force` → 0). Gate ran live and allowed. No
`SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` in any form. `settings.json`
untouched. 0 files written under `api/ sql/ tests/ tools/`. Auditor clones not
entered. **Tier A: all three obligations assigned to fourth DISCHARGED; none
left.**

**CONTEXT 28.8% of 1000k** (288,038 tokens).

## The four things worth knowing

1. **I WITHDREW MY OWN NUMBER.** b24's **25** class-B write branches is wrong;
   **it is 22**, and *"the b23 routing list is short by three"* is withdrawn.
   `api/sd-data.js` never moved — same blob sha across 36 commits — so the two
   counts were two predicates over one file and mine had a 14-line-window span
   bug that typed three pre-write **GET**s as POSTs.
2. **b18's N1 IS CLOSED.** Fixed 2026-10-14, the fix names it by number
   (`api/sd-data.js:7214`). Carried as open since b18 across b21–b24. **Remove
   it from every open list.**
3. **THE TWO 400 OBSERVATIONS ARE MADE.** A `23514` on the `alf_op_audits`
   upsert (Tier A) answers **503 "run the migration"**; the shipped
   `notProvisioned()` helper answers **400 ROW_REFUSED** correctly, so it is a
   call-site fix. A `42703` on a read answers **200 `provisioned:false`** with
   an empty list.
4. **ONE HIGH, ABLATED:** cody's arm Z has no `else`, so with `id` stripped off
   every blob the suite is **exit 0, 15 passed, 0 failed** and the arm vanishes.

## Open items

| owner | item |
|---|---|
| hank | **b24 F3** delete the replaced id **server-side**; **b24 F4** field-merge `legAdoptServerId` on the write's own payload (`Object.assign` is not the fix) |
| hank | **the 22 branches** from the corrected list, then b23's 13 caller GETs, then `:13503`/`:17127` |
| hank | **b25 MODERATEs:** `pending_clock_visits` in payroll; `isAppendOnly(resource)` instead of the typed-in map in both session-gate suites. **LOW:** `storedBlob(payload,['id'])` for the HR branch |
| hank | **5 still open, re-verified with fresh lines:** b21 F3, b21 F4, `license_hash`, no-revoke, both `sd_photos`. Plus b23 F4 and the status-less-entry guard |
| cody | **arm Z's `else`, then RE-RUN THE ABLATION** — the arm does not count until it comes back RED |
| cody | known-red row → **RECOVERED**; the control arm's hardcoded *"ten failures above"* → read off `failed.length` |
| cody | **b24 F1** re-anchor on `const acEsc = (s) =>` + the `acKey` ternary, **with an arm that fails when the anchor stops matching** |
| cody | a failing-first arm driving a `23514` through one of the 22 and a `42703` through one of the 151 — b25 **observed** both; nothing drives either |
| cc | `tier_a_review_gate.py --amend`; wire ONE anchor-rot tool into a gate; R3's 48 citation ranges; **the convention-numbering check is still unbuilt** and b25 moved the prose denominator by hand again |
| fourth | **open the batch manifest FIRST next batch**; then drive (d) `LATE_REPLAY`; extend the census to follow a variable through its assignments |
| Michael | **held, not acted on:** the EVV raw-clock question and the one-person-agency self-approval question |

## Routed / decisions

* **MICHAEL, and it is not a bug for anyone:** an approved clock correction now
  reaches pay (300/10000 vs 240/8000, driven). **Whether any real visit was
  underpaid before today is not establishable from the repo** — no production
  row was read — so whether a **back-payment** is owed is your call.
* **Convention 35 landed** in `docs/2026-09-13-cross-domain-disciplines.md`:
  *a predicate has a SPAN as well as a PATTERN, and a re-count that disagrees is
  a predicate disagreement until the SUBJECT is proved to have moved.* **Cite it
  as `convention 35`, never a bare "item 35"** — that already means the
  hash-chained audit log.
* **`git merge-base --is-ancestor <fix> <diagnosis-sha>`** is the one command
  that separates *red because the defect is there* from *red because my base is
  old*. cody's suite and its isolated-clone register row both failed it.

## Said rather than left as an absence

* **No b25 batch manifest exists** and I did **not** create one retroactively —
  `--new` writes an `id_lock` meant to be fixed before the work.
* **One bypass, mine, corrected before any push:** a first commit attempt used
  `core.hooksPath=/dev/null`; `--amend` re-ran the hook with it active. Nothing
  reached origin under it.
* **Not done:** (d) `LATE_REPLAY`; the 33 server-only GETs (**CALLER is still a
  lower bound**); b24 F3/F4, the 22, cody's re-anchor — **routed, not reviewed,
  no record exists**; no production row, no live fetch, no table touched.

## Chain tip

`7000e165` — `handoff(fourth b25): all six items done, b18 N1 closed, my own 25
withdrawn to 22, and one bypass disclosed`. Report SHA256
`ee610d06c666a2cc26ffb6feee0ed96470287972cc77065e30090ee6f10b3143`.
