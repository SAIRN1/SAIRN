# SAIRN handoff — cody b32 (2026-10-20)

Six queue items. **One was new work, one was already done, two were already
landed in b27, and two are process items.** The queue read like a replay of the
b27 list; each item was checked against the repo before anything was written.

| Item | State |
|---|---|
| 1. rf_invoices\|write cap at 294,912 "make it real" | **ALREADY REAL since b31 (`c79d4e59b`)** — no change; see §1 for W3 |
| 2. rf_jobs projection flip | **DONE** — both projections, 7-arm test, 3 red under ablation |
| 3. rt_routes handler branch + extraActions line | **ALREADY LANDED b27 (`864e6b764`), live-verified b28** — no change |
| 4. leg_settings 5th arg | **ALREADY LANDED b27** (`decide(…, legGrants, legHome)`) — no change |
| 5. state the concept before code | **DONE** — in the test header and the code comment |
| 6. push | see report for the verified remote state |

## 1. Item 1 — nothing to implement, and why W3 was NOT flipped

`PAYLOAD_CAP_BY_ACTION['rf_invoices|write'] = RF_INVOICE_WRITE_CAP_BYTES`
(262144 + 32768 = **294912**) is in `api/sd-data.js` since b31, pushed and read
back from the remote. Arms W1 (256000-byte write passes) and W2 (307200 → 413
naming `rf_invoices/write` and 294912) are the write-path arms and are green
(`api/b30-cap-per-action.test.js` 22/0).

**W3 is the arm that pins `issue` at 65536 and it stays as it is.** The
"one-line inversion" in my b31 report applied only to the *other* decision
(a per-resource cap). With write-not-issue confirmed, W3 is already the correct
arm — flipping it to the write path would assert write is capped at 65536 and
contradict W1/W2. If this reading is wrong, say so.

**Not live-verified:** no `SD_LICENSE`/`SD_OWNER_PIN` in this environment, so no
real request was sent to the deployed endpoint. The proof is the mocked
dispatcher arms plus the remote tree read-back.

## 2. Item 2 — the concept, the change, the proof

**CONCEPT:** a projection that tells the client who a job is assigned to and
which branch owns it must apply the authoritative columns **last**, so the
server's value wins by construction and not only because a strip list on the
write path happens to keep a competing blob copy from existing.

Source: `docs/2026-10-19-fourth-b37-tier-a-review.md` §7.1. `Object.assign`
lets the later source win; both `rf_jobs` projections put the blob last.

- read: `Object.assign({}, r.data || {}, { id, job_class, assigned_employee_id, location_id })`
- write response: `Object.assign({}, jobData, { id, job_class, assigned_employee_id, location_id })`
- **No behaviour change today** — `storedBlob`'s strip list means no stored row
  carries a blob copy (fourth measured the history: no window).
- `api/b32-rf-jobs-projection.test.js` (7/0): **R1** a blob carrying tampered
  copies of all four keys does not override the columns; **R2** control — normal
  blob fields still flow; **W1** runs the real write handler from a temporary
  copy of `sd-data.js` with the strip list **emptied** (the condition the review
  named) and asserts the response still carries the server-resolved `job_class`
  (`residential`, not the payload's `EVIL-CLASS`); **S1** structure. The temp
  copy is deleted in a `finally`.
- **Ablation:** restoring the old order turns R1, W1 and S1 red (4/3); restored,
  7/0.

**What this does not cover:** the same inverted order may exist in other
branches (`rf_*` or elsewhere); fourth's review only checked `rf_claims` (safe)
and `rf_jobs`. I did not sweep for it.

## 3. Items 3 and 4 — verified present, not re-done

- **rt_routes:** branch at `api/sd-data.js` (`resource === 'rt_routes' || 'rt_stops'`),
  `extraActions` line `rt_routes: ['upsert', 'reorder', 'optimize']` in
  `api/_resources/routes.js:74`; b27 handoff §1 item 1 FINISHED, b28 live probe
  closed it. Caps for its verbs are b30's.
- **leg_settings fifth argument:** `api/sd-data.js` ~17064 calls
  `legRoles.decide(resource, legSess.role, action, legGrants, legHome)`.
  `api/b27-leg-settings.test.js` 18/0, `api/b22-funeral-f1-f2-f3-wiring.test.js` 23/0.
- If the queue meant a **different** rt_routes/leg_settings task, I do not know
  what it is — send the text.

## 4. Gates this batch

- **Path scope:** `api/b32-rf-jobs-projection.test.js` is a new file in hank's
  `api/`. Declared in `docs/sairn-path-manifest.json` `assigned_overrides`
  with b31's list **replaced** (six paths dropped, two kept), reason beside it.
- **Tier A:** `rf_jobs` obligation OPENED and **assigned to cc**.
- **Claim:** the claim was committed but `sairn_claim.py` could not publish it
  (dirty tree from the gate's write-back blocked its rebase). It ships with the
  push; verify with `python tools/sairn_claim.py list`.

## 5. Verification (run this batch)

```
EXIT=0  node api/b32-rf-jobs-projection.test.js                7/0
EXIT=0  node api/b30-cap-per-action.test.js                    22/0
EXIT=0  node api/_resources/extra-actions.test.js              48/0
EXIT=0  node api/b27-leg-settings.test.js                      18/0
EXIT=0  node api/b22-funeral-f1-f2-f3-wiring.test.js           23/0
EXIT=0  node api/sd-data-cross-tenant-dispatchers.test.js      418/0
EXIT=0  eight further rf_jobs-touching suites                  all green, identical to HEAD (stash differential)
EXIT=0  node --check api/sd-data.js
```

## 6. Next

- Consider a sweep for other `Object.assign(<columns>, <blob>)` projections on
  Tier A rows (§2 limit).
- H1 #1613/#1614 remains **HELD** for H1's own report (per Michael).
- cc: discharge the `rf_jobs` obligation (and the b31 `sc_claims`/`sc_dme` one).
