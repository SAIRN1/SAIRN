# THE FIRST 25 FIXTURES — the unfixtured checkers that guard auth, audit-log, role-gate or push — 2026-10-14, fourth b14

**ROUTED TO cc (`tools/`) and cody (`tests/`).** Nothing outside `docs/` is
written by this document.

**WHY A PRIORITY LIST AND NOT THE 616.** b13 measured **616 of 973 checkers
(63%) with no fail-closed fixture** and routed a spec for the gate that would
refuse new ones. A backlog of 616 is not an instruction anybody can act on; it
is a number people quote. This is the first 25, chosen by what the checker
guards rather than by how it is named.

```
CMD python scratchpad/unfixtured_b13.py                 -> exit 1
    1029 tracked .py/.js; LOCKED 208, LOCKED-BY-PROBE 149, HAPPY-PATH 6,
    NO-FIXTURE 610, NOT-A-CHECKER 56
    CHECKERS 973; WITHOUT A FAIL-CLOSED FIXTURE 616 (63%)
CMD python scratchpad/priority25_b14.py --tools-only    -> exit 0
    unfixtured population 616; of those, on a guarded path 21
CMD python scratchpad/priority25_b14.py                 -> exit 0
    (whole population) on a guarded path 299
```

## THE SELECTION RULE, stated before the list so it can be argued with

1. **Score by SUBJECT, not by name.** `+4` auth/credential/PIN/session/licence,
   `+4` audit-log/`event_type`/append-only, `+3` role-gate/grant/RLS/permission,
   `+3` push-gate/pre-commit/seed-gate, `+1` for `gate|check|guard` in the
   filename as a tie-break only. A file scores on **every** band it matches, so
   a push gate about roles outranks either alone.
2. **`tools/` first, and this is the load-bearing choice.** Scored over the
   whole population, **299 of the 616 touch a guarded path and 24 of the top 25
   are `tests/` files** — because a test suite *about* auth naturally contains
   every auth word. **That list would have routed 18 app-feature test suites to
   cody and called it hardening.** Restricted to `tools/`, exactly **21**
   qualify, and those are checkers whose own verdict gates something.
3. **The last 4 slots go to `tests/` files whose SUBJECT is a guard**, not an
   app feature: a push-gate check, an auth-sabotage negative control, an
   append-only discriminator, and an audit-checkpoint refusal probe. Each is a
   guard-of-a-guard, which is the same class as rows 1–21.
4. **THE SCORE IS A SORT KEY, NOT A RISK NUMBER.** It reads words in a path and
   a source. It does not know what the code does. Rows 1–10 are worth arguing
   about; the exact order of 18–25 is not.

---

## THE 25, in priority order

Owner from the committed `docs/tool-owner-map.json`; **`(unrecorded)` means the
map has no row and no claim has ever named the file**, which is 13 of the 21
`tools/` entries and a finding in its own right (see §ROUTING).

| # | pts | checker | owner | the fixture it needs — a bad input it must REFUSE |
|---:|---:|---|---|---|
| 1 | 12 | `tools/service_role_tier_a_gate_check.py` | cody | A module that holds the RLS-bypassing service-role key **and** writes a Tier A resource **with no gate between them** → must exit non-zero and name the module. Control: the same module with the gate present → exit 0. |
| 2 | 10 | `tools/fail_open_scan.py` | cc | A gate that `print`s a success line on an exception path → must be reported. **Control arm matters more here than anywhere:** a gate that exits 2 on the same path must NOT be reported. A fail-open scanner that cannot tell 2 from 0 is the defect it hunts. |
| 3 | 8 | `tools/cleanup_residue_check.py` | **(unrecorded)** | A fixture tree where a row the cleanup file exists to delete **still exists** → refuse. Control: the row absent → pass. |
| 4 | 8 | `tools/licence_recoverability_check.py` | **(unrecorded)** | A licence in the **unrecoverable-credential** state (no active admin, per `PROVISIONING_ROLES`) → refuse, naming the licence. Control: a licence with exactly one active admin → pass. **This is PR §3.4's guard; two end states are safe and only two.** |
| 5 | 8 | `tools/mech_panels_live_check.py` | **(unrecorded)** | `--static` mode against a panel that reads a table it never writes → refuse. Control: a panel doing both → pass. **Must also prove network-absent is exit 2, not exit 0.** |
| 6 | 7 | `tools/audit_licence.py` | **(unrecorded)** | `require_audit_licence()` with **no audit licence configured** → the caller must not run. The bad input is the absent licence; the arm asserts the probe refuses rather than writing. |
| 7 | 7 | `tools/bare_run_writers.py` | cody | A tool whose bare run writes and is **not** on the declared list → refuse. Control: a declared writer → pass. |
| 8 | 7 | `tools/hover_self_health_shim.py` | **(unrecorded)** | A marker naming **another** clone → must refuse to run that clone's hook. **It always exits 0 by design (SessionStart), so the fixture must assert on what it DID, not on the exit code** — the one row here where exit code is the wrong assertion. |
| 9 | 7 | `tools/reservation_lock_invariants.js` | **(unrecorded)** | Two reservations holding the same slot → invariant violated, non-zero. Control: adjacent non-overlapping slots → pass. **No docstring at all in this file;** the fixture is also its specification. |
| 10 | 5 | `tools/leg_session_gate_live_probe.py` | **(unrecorded)** | A stubbed endpoint answering **200 without a session** → refuse. And the one that matters: **endpoint unreachable → exit 2, never 0.** |
| 11 | 5 | `tools/text_gate_literal_sweep.py` | **fourth** | A gate whose text match is satisfied by the token inside a **comment** → reported. **I have already paid for this one:** b13's own A1 fixture named the token it was built to lack and passed where it had to refuse. Mine to write. |
| 12 | 5 | `tools/tier_a_bypass_check.py` | **(unrecorded)** | External input reaching a Tier A resource **past** its verification path → refuse, naming both ends. Control: the same input through the verified path → pass. |
| 13 | 4 | `tools/accepted_risk_scan.py` | **(unrecorded)** | A risk acceptance that exists **only** in a comment → reported. Control: the same acceptance present in the register → not reported. |
| 14 | 4 | `tools/clone_health_check.py` | cody | **HAPPY-PATH, not NO-FIXTURE** — it has a fixture arm and no arm expecting a refusal. Add: a clone with a detached HEAD / missing claim file → non-zero. |
| 15 | 4 | `tools/hover_eqa_escalation.py` | **(unrecorded)** | A checkpoint whose date is **past the overdue threshold** → refuse. Control: one inside the window → pass. **Asked from outside the hover clone, so the absent-clone case must be exit 2.** |
| 16 | 4 | `tools/law_billing_code_trim_live_probe.py` | hank | A stubbed response with an **untrimmed** billing code → refuse. Plus: unreachable endpoint → exit 2. |
| 17 | 4 | `tools/resource_reachability_check.py` | **(unrecorded)** | A registered resource **no client names** → reported. Control: a resource named by one client → not reported. |
| 18 | 4 | `tools/sairn_dead_function_sweep.py` | cody | A function nothing references → reported. Control: one referenced only through a string dispatch table → **not** reported (the false-positive direction that would make this tool deleted). |
| 19 | 4 | `tools/sairn_reachability_probe.py` | cody | A mechanism defined and correct but **never called** → reported. Control: one called from exactly one place → not reported. |
| 20 | 4 | `tools/sairn_self_state.py` | **(unrecorded)** | A claim file that is **unparseable** → exit 2 (COULD NOT DERIVE), never a confident state. Control: a valid claim → the derived state. |
| 21 | 4 | `tools/second_pass_coverage_scan.py` | **(unrecorded)** | A flow tested only on its first attempt → reported. Control: a flow with a retry arm → not reported. |
| 22 | 12 | `tests/audit_checkpoint_probe.py` | cody | It already asserts a REFUSAL and names *"a PROVEN escape"* — the missing arm is the escape itself as a fixture: the input that gets past `api/audit-checkpoint.test.js` must make **this** probe fail. |
| 23 | 11 | `tests/push_gate/check11_probe.py` | cody | A raw control byte in the outgoing content → check 11 must refuse. Control: the same content with the byte removed → pass. |
| 24 | 11 | `tests/run_append_only_read_order_probe.py` | cody | Its own docstring says the scan *"must REFUSE and must DISCRIMINATE"* — the fixture is the pair: a genuinely out-of-order read (refuse) **and** an in-order read that merely looks similar (pass). |
| 25 | 11 | `tests/run_sd_auth_last_admin_sabotage_probe.py` | cody | It is a negative control for the last-admin rule; the arm it lacks is the **deactivation of the final admin** succeeding → the probe must fail. |

**BEYOND THESE 25, AND NOT DROPPED SILENTLY:** `--tools-only` found **0** more
`tools/` entries scoring ≥ 4, and the whole-population run found **274** more
(almost all `tests/` files about app features). The next 25 should be chosen by
re-running the scorer, not by continuing this list downward.

---

## ROUTING

### cc — `tools/`, 21 rows

* **Rows 2, 3, 4, 5, 6, 8, 9, 10, 12, 13, 15, 17, 20, 21** — `tools/` entries
  with **no recorded owner** (13 of them) plus `fail_open_scan.py`. By
  directory, `tools/` is cc's; by the owner map these have nobody.
* **ROW 4 FIRST, THEN ROW 2, THEN ROW 12.** Not by score:
  `licence_recoverability_check.py` guards the credential state a real licence
  (`RF-PINNACLE-2026`) actually entered; `fail_open_scan.py` is the one whose
  failure mode is the defect class b12 and b13 were both about; and
  `tier_a_bypass_check.py` guards the tier where a wrong answer reaches a
  person.
* **THE OWNERLESS 13 ARE A FINDING, NOT A ROUTING CONVENIENCE.** `(unrecorded)`
  means the owner map has no row and no claim has ever named the file. A fixture
  written by whoever happens to pick it up is a fixture nobody answers for.
  **Either claim them or record them as platform-owned** — one line each in the
  owner map's source of truth.

### cody — `tests/` and the 5 tool rows the map assigns to cody

* **Rows 22, 23, 24, 25** — the four guard-of-a-guard probes. **Row 22 first:**
  its own docstring already claims a proven escape exists, so the fixture is
  known and unwritten.
* **Rows 1, 7, 14, 18, 19** — `tools/` files the owner map attributes to cody.
  **Row 1 is the highest-scoring entry in the whole `tools/` population** and
  its subject is the RLS-bypassing key next to a Tier A write.
* **Row 14 is the only HAPPY-PATH entry in the 25** — it already prints a
  criteria-lock line, so a reader believes it is tested. That makes it sharper
  than a NO-FIXTURE row of the same score.

### fourth — row 11, mine

`tools/text_gate_literal_sweep.py` is the one entry I own, and the fixture it
needs is the exact defect my own b13 bad-input arm shipped with: a token
satisfied by a comment. **Not written in this batch** — this batch writes under
`docs/` only — and recorded here as my own open item rather than routed.

---

## WHAT THIS LIST DOES NOT CLAIM

* **It does not say these 25 are wrong.** None has ever been shown to refuse
  anything; that is the entire claim, unchanged from b13.
* **It does not say 25 is the right number.** It is the number that fits one
  readable page and one batch of work per owner.
* **It does not replace the gate.** `tools/fixture_lock_check.py`
  (`docs/2026-10-14-fourth-b13-unfixtured-checkers-routed-to-cc.md`) is what
  stops the backlog growing; this list only shortens it.
* **The scorer is text matching.** A checker that guards auth without using any
  of the words is missed, and that direction makes this list shorter than the
  truth.
