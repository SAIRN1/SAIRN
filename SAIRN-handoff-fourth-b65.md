# HANDOFF — fourth / ted, batch b65, 2026-10-29

**READ THIS FILE ONLY.** It is the whole state.
- **Items 1, 2, 3 and 5 landed and were live-verified.** Item 4 landed for cash and for the mechanical quote.
- **Not built:** mechanical's job, invoice and inspection records (section 4).
- **No force.** The pushes used `push_retry`'s pure-base fast retry. That is a logged `--no-verify`, made only after the gate had passed on the same patch-ids; the rows are in `docs/BYPASS-LOG.jsonl`.
- Wrapped at 58.7% real context.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\b6e28c25-eaee-4611-aeb3-d94f0198d47f.jsonl`
**Scratchpad:** `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\b6e28c25-eaee-4611-aeb3-d94f0198d47f\scratchpad\`
- `live65_sen.py` and `live65_sv.py`: the two live drives.
- **`sv-audit-owner.pin`** and **`audit-cg-b65.pin`**: the PINs this batch created. Move them to your password manager and delete the files.

## 1. STATE

Every page below was fetched live and is **byte-identical** to local.

| item | sha | state |
|---|---|---|
| 1 EVV billing gate | `1e2934ed1` | **live-verified on real rows, 5/5** (section 2) |
| 2 grounds sale hours | `c741681e2` | fixed |
| 3 build `awardSubBid` | `0d6e6a473` | fixed; root cause found |
| 4 cash checkbox + 401(k) cap; mechanical quote client | `7b744bb14`, `25df11ed8` | fixed. **The mechanical job/invoice/inspection records are NOT built** (section 4) |
| 5 vet witness flow, live | `1d5862edf` (evidence) | **5/5 live on SV-AUDIT-2026** (section 3) |
| register | records for all four fixes, in one register commit | `--check` OK |

## 2. ITEM 1: the EVV billing gate

**Server (`api/sd-data.js`, the `sen_claims` write).** When a claim **moves to** submitted or paid, the server reads its visit. It refuses the move with **409 EVV_UNREVIEWED** while the visit carries `clock_flags` and no review of that exact flag set exists. Every could-not-tell answer refuses:

| situation | answer |
|---|---|
| the claim or visit cannot be read | 503 EVV_CHECK_FAILED |
| the visit is not on the server | 409 EVV_VISIT_MISSING |
| the claim names no visit | 409 EVV_UNVERIFIABLE |

A claim already at that status is not re-gated, so appeal edits on old paid claims still work.

**The review action.** `review_clock_flags` is a new `sen_visits` action: management only, note required. It stores `{flags, reviewed_by, reviewed_role, reviewed_at, note}`.
- **A flag that arrives later makes the visit unreviewed again.**
- The ordinary visit write cannot set or clear the review.
- The action is declared in `api/_resources/sairnsenior.js` and in `ACTION_CLASS`.

**Client (`sairnsenior.html`).**
- Billing has an **EVV Clock Flags** card: the flags, a note box and *Mark reviewed*.
- Ready to Bill marks flagged visits.
- A refused claim is **put back** on the device, instead of the device continuing to show it as paid.

**Tests.**
- `api/sen-evv-billing-gate.test.js`: 15/15 against the real handler; it fails against the unmodified `sd-data.js`.
- The related api and senior suites are green.

**LIVE on SEN-AUDIT-2026, real rows** (`docs/live-residue/2026-10-29-fourth-b65-sen-evv-gate-live.json`):
1. A caregiver clocked two visits 10 days late, and **the server wrote LATE_REPLAY** on both.
2. One visit was reviewed and one was not.
3. Moving each claim from draft to paid: **unreviewed → 409, and still `draft` in the database. Reviewed → 200, and `paid` in the database.**

## 3. ITEM 5: the vet witness flow, live on SV-AUDIT-2026

I bootstrapped `audit-owner`, then ran three arms (`docs/live-residue/2026-10-29-fourth-b65-sv-witness-live.json`):

| arm | request | result |
|---|---|---|
| A | write with no token | **403 WITNESS_REQUIRED**. This is the b63 inference, now measured |
| B | token for the exact record, then write | 200, and the row reads back |
| C | the same token replayed | **409 WITNESS_ALREADY_SPENT** |

This is exactly the request pair `svPushOne()` has sent since b64 (`tests/sairnvet_witness_token_client.js`).

**Not done:** adding `SV-AUDIT-2026` to `KNOWN_AUDIT_KEYS` in `tools/audit_licence.py`. That is cc's file; the measurement for it is the `check_license 200` in the evidence.

## 4. ITEM 4: root causes, and what was not built

| app | defect | root cause | fix |
|---|---|---|---|
| grounds | clearing a day's alcohol sale hours opened it all day | `saveMsbHours()` defaulted empty times to `00:00` / `23:59` | a cleared day is saved `closed:true`; a day with one time missing is refused |
| build | awarding a bid changed nothing | `66cf7b930`, an "honest toast" refactor: its hunk replaced `st()` with `var saved=st()` and **deleted the one line that set `awarded`** | that line restored |
| cash, 110% warning | the "AGI not recorded, 110% may apply" warning never showed | the hidden legacy checkbox was saved **unconditionally**, so every user who never answered got a manufactured "no" | the old answer is carried only if it exists; otherwise null |
| cash, Solo 401(k) | room shown above what was earned | the flat 24,500 deferral had no cap at earnings | capped at net SE earnings less half the SE tax |
| mechanical | a saved quote did not say who it was for | `saveQuote()` never put the client in the record | the client is stored |

All five are covered by `tests/fourth_b65_record_fixes.js` (13/13). **Every defect arm fails against the unfixed files.**

**NOT built: mechanical's job, invoice and inspection records.**
- **Root cause:** a deliberate placeholder, not a defect. `mechNotLive('Job entry')` and `mechNotLive('Invoice entry')` were never built, and no inspection record has ever existed.
- **Why not built here:** each needs a server branch, a SQL schema Michael runs, a resource declaration, UI and tests. That is three new record types, a product build and not a patch. I did not want to start it at the end of a five-item batch and leave it half-built.
- **Next step:** a dedicated batch. Start with the job record, because invoices and inspections both hang off it.

**Also not changed (not in the dispatch, and recorded in the register):** cash still reads a typed $0 prior-year tax as "not provided".

## 5. PROCESS NOTES

- **Claims.** The build, cash and mechanical claims were refused as `SAME WORK` as my own sairngrounds claim, matched on the phrase "files fix" from `fix FILES:`. That is a matcher false positive, **for cc**. The tool said to carry on under the claim already held, and I did. No other session held those apps.
- **I edited the four app files before their claims had published** (the claim run hit a dirty tree). I stashed the edits, published the claims and restored them. Nothing was committed before the claims landed.
- **Push.** One rebase conflict in the register, resolved with `tools/sairn_rebase_resolve.py`. Derived docs were regenerated.

## 6. OPEN, with the exact next step

1. **Mechanical job/invoice/inspection records:** a dedicated batch, job record first.
2. **Michael:** move the two PIN files into your password manager. Add `SV-AUDIT-2026` to `KNOWN_AUDIT_KEYS` (cc).
3. **cc:** the claim matcher's "files fix" self-match; the deny-hook `sh -n` false positive; and the b62/b63 items (orphan scrutiny rows, the install_git_hooks hook-fire, `--supersede`).
4. **Still open from the audits:**
   - vet's register is rewritten in place (append-only is a separate change);
   - build's WIP forecast has no writer;
   - build's lien waiver gates no payment (Michael decides);
   - grounds quote lines lose their text;
   - grounds has no pesticide record;
   - cash treats $0 as not provided.

## 7. CLAIMS

`fourth` held sairnsenior, sairngrounds and sairnvet. All three are released at wrap.
