# hank b11 — the captured red, the green, and the ablations

Every file here is a run's real stdout, written by the run and not retyped.
**The point of keeping the RED is that a green suite proves nothing about what
it would have caught**; the pair does.

| item | red | green | ablation |
|---|---|---|---|
| 1 — the MAR access grant | `b11-item1-red.log` — 8 passed / **16 failed** / 4 unproven | `b11-item1-green.log` — 28 / 0 / 0 | `b11-item1-ablation.log` — four layers, each alone |
| 2 — the SAIRNvet role matrix | `b11-item2-red.log` — 19 passed / **11 failed** | `b11-item2-green2.log` — 31 / 0 / 0 (30 before arm D1b) | `b11-item2-ablation.log` — three layers |
| 3 — AI provenance at the client | `b11-item3-red.log` — 10 passed / **7 failed** / 1 unproven | `b11-item3-green.log` — 18 / 0 / 0 | `b11-item3-ablation.log` — four changes |
| 4a — the three transports | `b11-item4-sweep-red.log` — 77 passed / **4 FAILED** | `b11-item4-sweep-green.log` — **ALL 81 ARMS PASS (15 apps)** | `b11-item4-ablation.log` — each guard alone |
| 4b — the third state | `b11-item4b-before-ablation.log` — a pure refactor printed **FAIL, exit 1** | `b11-item4b-after.log` — 15 passed, 0 COULD NOT RUN | `b11-item4b-ablation.log` — refactor → **exit 2**, deleted clause → **exit 1** |

`famgate2.log` is the one regression this batch leaves red and it is **routed,
not ignored**: `tests/sd_data_family_mar_gate.js` is 9 passed / 1 failed, and
the failing arm is C1, a SOURCE PIN requiring `ALF_FAMILY_READ_ROLES` inside
the `family_mar` gate — which item 1 deliberately removes. That arm and arm A9
of `tests/mar_billing_grant.test.js` **cannot both hold**; A9 is the spec this
batch was sent to satisfy. `tests/` is cody's, so the fix is routed.

`../b11_live_gate_probe.py` / `.out` is the post-push live verification:
**fail=0 couldnot=0**, seven arms, and it prints what it did NOT drive.
