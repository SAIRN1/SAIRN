# FIXTURE PRIORITY ROWS 26–50 — same method as rows 1–25 — 2026-10-14, fourth b15

**ROUTED TO cody (`tests/`) and cc (`tools/`).** Nothing outside `docs/` is
written here.

**Rows 1–25 are in `docs/2026-10-14-fourth-b14-fixture-priority-25.md`.** This
continues that list with the same scoring and the same tie-break, and the
continuation forced one honest change of population which is stated before the
table rather than after it.

```
CMD python scratchpad/priority_26_50_b15.py        -> exit 0
    candidates on a guarded path, not already in rows 1-25: 274
    of those, GUARD-OF-A-GUARD: 180
    BEYOND ROW 50: 249 more candidates score >= 4; 155 still guard-of-a-guard
```

## THE METHOD, AND THE ONE THING THAT CHANGED

**Unchanged:** band scoring (`+4` auth / `+4` audit-log / `+3` role-gate /
`+3` push, `+1` filename tie-break), a file scoring on **every** band it
matches, and the rule that **the score is a sort key, not a risk number**.

**Changed, because rows 1–25 exhausted a pool:** `--tools-only` found exactly
**21** `tools/` checkers scoring ≥ 4 and **zero more**. Rows 26–50 can therefore
only come from `tests/`. Row 3 of the rows-1–25 selection rule said the last
slots go to `tests/` files **whose subject is a guard rather than an app
feature** — and that rule is now **mechanical** instead of eyeballed:

> A `tests/` file is a **GUARD-OF-A-GUARD** when it lives under
> `tests/push_gate/`, **or** is named `run_<x>_probe` with a `tools/<x>.py`
> that exists, **or** names a `tools/` path in its source, **or** calls itself
> a control / sabotage / negative control.

**180 of the 274 remaining candidates qualify**, so rows 26–50 are all
guard-of-a-guard and no app-feature suite is pulled in ahead of one.

## THE SHAPE OF WHAT IS MISSING HERE IS DIFFERENT FROM ROWS 1–25, AND THAT IS THE FINDING

Rows 1–25 were mostly checkers with **no refusal arm anywhere**. Most of rows
26–50 are the opposite: files whose **whole subject** is a refusal — their own
docstrings say *"must REFUSE, not merely agree"*, *"the control for
`tools/schema_provisioning_check.py` — and it had none"*, *"a planted violation
must BLOCK, a clean push must be allowed"*.

**They refuse things. Nothing locks their own criteria.** A control whose
criteria are not locked is the ninth cross-domain discipline's exact subject: a
check that quietly stops testing anything, while its name and its exit code go
on saying it does. **So the fixture these 25 need is nearly always the same
shape, and it is a PAIR:**

* **the sabotage arm** — the subject, broken on purpose, must be REFUSED; and
* **the control arm** — the subject, correct, must PASS.

**One arm without the other is worthless in a specific way:** a sabotage-only
lock passes forever once the probe degrades to "always refuse", and a
control-only lock passes forever once it degrades to "always pass".

---

## ROWS 26–50

Owner from the committed `docs/tool-owner-map.json`, else `tests/` ⇒ cody.

| # | pts | file | owner | why it is a guard | the fixture it needs |
|---:|---:|---|---|---|---|
| 26 | 11 | `tests/run_restore_coherence_probe.js` | cody | calls itself a control | **No docstring at all** — the fixture is also its specification. Pair: an incoherent restore (rows restored out of order / a partial set) must be REFUSED; a coherent restore must PASS. |
| 27 | 11 | `tests/run_schema_provisioning_probe.py` | cody | names `tools/schema_provisioning_check.py` | Its own first line says *"the control … and it had none"*. Pair: a schema missing a required table must be REFUSED; a complete schema must PASS. **The irony is the point: a control written because something had none, with none of its own.** |
| 28 | 11 | `tests/sairncare_credential_export.js` | cody | calls itself a control | Pair: an export containing `pin_hash` or `pin_salt` must be REFUSED; a legitimate export of non-credential columns must PASS. |
| 29 | 11 | `tests/sairndental_ledger_export.js` | cody | calls itself a control | Pair: a ledger export whose totals do not reconcile must be REFUSED; a reconciling export must PASS. |
| 30 | 11 | `tests/sairnmechanical_credential_export.js` | cody | calls itself a control | Same pair as row 28, different app. **Three apps, one shape — a shared fixture helper is correct here and three copies are not.** |
| 31 | 10 | `tests/push_gate/refspec_and_override_probe.py` | cody | `push_gate/` dir | Pair: the two 2026-09-01 defects (a refspec diffed against the wrong base; an override honoured where it must not be) must each be CAUGHT; a clean push must be ALLOWED. |
| 32 | 10 | `tests/sql_preflight/run_probe.py` | cody | names `tools/sairn_sql_preflight.py` | Pair: SQL with the defect preflight exists for must be REFUSED; clean SQL must PASS. |
| 33 | 8 | `tests/alf_append_only_probe.py` | cody | calls itself a control | Pair: an UPDATE against an append-only ALF table must be REFUSED; an INSERT must PASS. |
| 34 | 8 | `tests/claims/run_own_claim_overlap_probe.py` | cody | names `tools/sabotage_control_check.py` | **The false-accusation arm is the one that matters:** an overlapping claim must be FLAGGED, and a non-overlapping one must NOT be. A claim checker that cries overlap is switched off in a day. |
| 35 | 8 | `tests/faults/sv_backup_write_faults.js` | cody | names `tools/write_path_fault_scan.py` | Pair: an injected write fault on the SAIRNvet backup path must be DETECTED; a healthy write must PASS. |
| 36 | 8 | `tests/push_gate/check2_and_check5_probe.py` | cody | `push_gate/` dir | Pair per check: a planted check-2 violation and a planted check-5 violation must each BLOCK **independently** — two arms, not one, or a single over-broad refusal reads as both working. |
| 37 | 8 | `tests/push_gate/check3_probe.py` | cody | `push_gate/` dir | Pair: a planted check-3 violation BLOCKS; a clean push passes. |
| 38 | 8 | `tests/push_gate/check7_probe.py` | cody | `push_gate/` dir | It already describes the pair in its docstring (*"a planted violation must BLOCK, a clean push must be allowed"*) — **the fixture is that description made executable in-file.** |
| 39 | 8 | `tests/push_gate/missing_checker_probe.py` | cody | `push_gate/` dir | Pair: a **missing** checker must make the gate REFUSE (fail closed, PR §1.11); every checker present must PASS. **This is the fail-closed rule's own probe and it has no lock.** |
| 40 | 8 | `tests/role_gate_loop_rule_probe.py` | cody | names `tools/role_gate_negative_coverage.py` | Pair: a loop-form role gate that **is** negatively covered must be CREDITED; one that is not must be FLAGGED. The crediting rule is the thing that can silently invert. |
| 41 | 8 | `tests/run_alf_read_order_sabotage_probe.py` | cody | calls itself a control | Pair: a read-order sabotage must be REFUSED; the correct read order must PASS. |
| 42 | 8 | `tests/run_export_coverage_probe.py` | **cc** | names `tools/export_coverage_check.py` | Pair: an export path with no coverage must be FLAGGED; a covered one must NOT be. |
| 43 | 8 | `tests/run_pra_event_tree_probe.py` | cody | probe for `tools/pra_event_tree.py` | Its docstring says the tree *"can be shown to DISCRIMINATE, and to refuse the nu…"* — **discrimination is exactly a two-sided lock**: the bad tree refused, the good tree accepted. |
| 44 | 8 | `tests/run_removal_path_probe.py` | **fourth** | names `tools/removal_path_check.py` | Pair: a removal path that leaves a row behind must be CAUGHT; a complete removal must PASS. **Mine.** |
| 45 | 8 | `tests/run_role_gate_invariants_probe.js` | cody | calls itself a control | Pair: a violated role-gate invariant must be REFUSED; a satisfied one must PASS. |
| 46 | 8 | `tests/run_role_gate_negative_coverage_probe.py` | cody | probe for `tools/role_gate_negative_coverage.py` | Its own docstring states both halves — *"must find a gate no test drives negatively, must NOT accuse one that is"*. **Both halves, in-file, or the second one rots first.** |
| 47 | 8 | `tests/run_service_role_gate_probe.py` | cody | names `tools/service_role_tier_a_gate_check.py` | **Pairs with row 1 of rows 1–25**, which is the same subject from the tool side. Do them together: the tool's fixture and its probe's fixture are one piece of work. |
| 48 | 8 | `tests/run_sv_session_gate_sabotage_probe.py` | **cc** | calls itself a control | Pair: a sabotaged SAIRNvet session gate must be REFUSED; the correct gate must PASS. |
| 49 | 8 | `tests/sairncare_fault_probe.py` | cody | calls itself a control | Pair, per suite: MAR, incident and pharmacy-review suites must each DENY a planted fault and ALLOW a clean one. **Three subjects in one file means three arms, not one.** |
| 50 | 8 | `tests/sairncash_entitlement_gate_probe.py` | **fourth** | calls itself a control | Pair: a forged entitlement must be REFUSED; a genuine one must PASS. **Mine.** |

### ORDER WITHIN THE 25, if whoever picks this up wants one

1. **Row 39** — the missing-checker probe. It is the fail-closed rule's own
   control, and if it has degraded, every other push-gate probe's verdict is
   worth less.
2. **Rows 46 and 40** — the negative-coverage crediting rules. These decide
   whether other gates get credited, so an inversion here is silent and wide.
3. **Row 47 with row 1** — one subject, two sides.
4. **Rows 28/29/30** — one shared helper, three apps, credentials in exports.
5. Everything else in table order.

### OWNERS

| owner | rows |
|---|---:|
| **cody** | 21 |
| **cc** | 2 (42, 48) |
| **fourth** | 2 (44, 50) — mine, open, **not written in this batch** |

**BEYOND ROW 50:** 249 more candidates score ≥ 4, **155 of them still
guard-of-a-guard**. Rows 51–75 should be chosen by re-running the scorer, not
by continuing this table downward.

---

## WHAT THIS LIST DOES NOT CLAIM

* **It does not say these 25 are broken.** It says nothing locks their
  criteria, so nobody would know if they became broken. That is the whole
  claim, and it is weaker than "wrong" and stronger than "untested".
* **It does not count arms.** A file with three subjects (row 49) is one row
  here and three arms of work.
* **It does not replace `tools/fixture_lock_check.py`** — specified in b13,
  built by nobody. Without it this list regrows.
* **The guard-of-a-guard test is text matching.** A probe that shells out to a
  tool through a variable is missed, and that makes this list shorter than the
  truth.
