# Before you narrow a gate: who calls it, and will they still get in?

**Written 2026-09-28 (Hank).** A standing convention, a tool, and the sweep that
produced both.

---

## 1. The near miss that is the whole argument

On 2026-09-27 `add_rule` and `add_holidays` were gated to an owner-or-attorney
session. They had been writable with a **licence key alone** — no employee
session at all — on the table every computed deadline reads from. The gate was
correct and overdue.

**And it would have broken seeding on all 48 jurisdictions.**
`tools/load_deadline_seed.py` sent the bearer key and nothing else, so every
write would have answered 401. It was caught by reading the loader before
pushing — which is **luck dressed as diligence**. Nothing asked the question. The
answer was one file away from being discovered by a failed seed load weeks later.

**The failure mode is unusually quiet.** A tightened gate does not break the
endpoint; it breaks a *caller*, somewhere else in the repo, that nobody edited.
The endpoint's own suite goes green. The caller's suite, if it has one, mocks the
transport and goes green too. The break surfaces the next time a human runs a
loader by hand.

## 2. The rule

> **Before narrowing any authorisation gate, enumerate every caller of the
> affected action and confirm each one still authenticates. Publish
> `checked / universe`. A caller that should remain unauthenticated is named
> individually, never skipped as a class.**

`tools/gate_caller_impact.py` decides it. Its control pair is
`tests/run_gate_caller_impact_probe.py`, both directions.

    python tools/gate_caller_impact.py --endpoint legal-deadlines --action add_rule
    python tools/gate_caller_impact.py --survey

## 3. The sweep — checked / universe

**818 / 818** candidate caller files under `tools/ tests/ scripts/ agent/
.github/`. Of those, **14** address a SAIRN endpoint and send an action literal:
**7 send a session**, **7 do not**.

**`add_rule` / `add_holidays` had exactly one caller in the repo** —
`load_deadline_seed.py` — and it now signs in. So the gate that motivated this
broke nothing else. *Checked, not assumed.*

### The seven key-only callers, each accounted for

| Caller | Action(s) | Verdict |
|---|---|---|
| `tools/alf_facility_role_gate_live_probe.py` | `login`, `read`, `write` | **REAL BUG — FIXED.** See §4. |
| `tools/stonedesk_storefront_live_check.py` | `catalog`, `view` | **Deliberate.** The public storefront; its own header calls it *"a public GET-shaped POST"* with a deliberately dead token. |
| `tools/audit_checkpoint_status.py` | `verify` | **Deliberate.** `api/audit-checkpoint` authenticates on a shared secret; it has no employee-session concept. |
| `tools/licence_recoverability_check.py` | `provisioner_health` | **Deliberate.** `api/provisioner-health.js` gates on the licence only — verified by reading it: 401 for `NO_LICENSE` and `INVALID_LICENSE`, no `verifySessionToken` anywhere. |
| `tools/sairn_load_state_check.py` | `fingerprint`, `rules_fingerprint` | **Deliberate.** Read-only fingerprints; `rules_status` was live-verified to answer without a session. It only *mentions* `add_rule` in a comment about server-side transforms. |
| `tools/cleanup_residue_check.py` | `read` | **Known ceiling, already recorded in the tool.** Its own header names `NO_SESSION` as *"the dominant ceiling"* and names the `RF_EMP`/`RF_PIN` convention as the path not taken; it maps `NO_SESSION` to an explanatory sentence rather than to a verdict. |
| `tools/schema_provisioning_check.py` | `read` | **Known ceiling, honest.** A 401 returns `REFUSED` with the status and code — a distinct third state, never folded into `MISSING`. It cannot do its job without a session and it says so. |

The last two are the honest middle case the tool's two buckets do not name:
*not deliberate, not broken — unable to do its job and saying so.* They are
`--expect-unauthenticated` today because the alternative is a permanent finding
nobody acts on, and **that is a weakness of this table, recorded here rather than
smoothed over.** Giving either a sign-in path would make a live checker
functional and is worth doing; it is not this change.

## 4. The bug the sweep found

`tools/alf_facility_role_gate_live_probe.py` set the session as
**`X-Session-Token`**. `api/_lib/auth.js`'s `tokenFromRequest()` reads
`req.headers['x-sd-auth']` and nothing else.

So **every request that probe has ever made carried a licence and no session.**
Every role got the identical no-session answer, and the role differentiation the
file exists to demonstrate was never exercised — on a gate whose own header
explains why it matters: *"A caregiver flipping OH to WV does not corrupt a
cosmetic field — it changes which staffing and training law the facility is
measured against."*

**Its CONTROL is what stopped it lying, and that is the argument for writing
one.** With no session, management gets 401 rather than "allowed", so the
`CONTROL — management must still be ALLOWED` section could not pass and the probe
reported **UNVERIFIED** — the third state — rather than a false clean. Without
that control the excluded roles would all have shown "refused" and the probe
would have published a role gate it never reached.

Fixed to `X-SD-Auth`, with the account written at the line.

## 5. What the tool cannot see

Stated as decisions, not omissions.

* **A caller outside this repo** — a cron in another clone, a curl in somebody's
  notes, a customer integration. **This is the largest gap** and is why the tool
  reports rather than gates.
* **A dynamically built action name** (`{"action": verb}`). The literal is the
  anchor.
* **Whether the session carries the right ROLE.** It answers *authenticates*, not
  *is authorised* — narrowing owner+attorney out of a paralegal caller passes
  here and still fails live.
* **An untracked file.** The universe is `git ls-files`, so a caller nobody
  committed is not yet a caller. Asserted by the control rather than left to be
  discovered.

## 6. And the tool committed a noise defect on its first run

`--survey` reported **49 "key-only callers" of an action called `store_true`** —
every argparse tool in the repo, because `ap.add_argument(..., action='store_true')`
matches the keyword-argument shape. A report that is mostly noise is a report
nobody runs, which is the same end state as no report. Two narrowings, both
stated rather than tuned until the number looked right: argparse's own vocabulary
is excluded by name, and `--survey` requires the file to address a SAIRN endpoint
at all. 49 → 7.
