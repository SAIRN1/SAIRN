# SAIRN handoff: cc, batch b56, 2026-10-27 (StoneDesk, presence passed as proof)

**All five items are closed.** The reusable checklist and the StoneDesk
stress tool landed at `c1e381c4` (0 0 against origin). The tool finds 8
false positives, which are **routed to their owners and not self-registered**.
No product code changed. No `--force`, no override.

| | |
|---|---|
| Landed | `ae076845` (tools + Tier A obligation), `c1e381c4` (claim refusal record), then these deliverables |
| Claims held | none. cc's claim was REFUSED because fourth holds `stonedesk` (vendor qty / emoji / modal / NVDA). cc's work is read-only tools in `tools/`, with no edit to `stonedesk.html` or `api/`, so there is no overlap. The refusal is recorded in `.claude/claims/cc.json` |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 1. Item 4, the methodology as a reusable tool: `tools/presence_proof.py`

A stress tool builds `Scenario(...)` objects and calls `require_plan()`
**before** it drives anything. The plan is refused (exit 2) unless it answers
the checklist (`python tools/presence_proof.py --checklist`):

1. **CLAIM** — the literal status the user reads.
2. **TRUTH** — the real fact, and why this input makes the claim false.
3. **FAIL MEANS** — "the app shows <CLAIM> while <TRUTH>". It must name the
   claim. An exit code or the word "error" is refused.
4. **DETECTOR** — read what is rendered or stored, not an internal value.
5. **CONTROL** — at least one input where the claim is true and must be
   shown. If a control fails, the result is COULD NOT RUN.
6. **ABLATION** — one change that must turn a PASS into a FAIL.
7. **UNSEEN** — what the check never reads. An unseen item that reaches the
   user unflagged is a FAIL.
8. **SCOPE** — what is real and what is a stub.

`verdict()` counts a crash as FAIL, never PASS. The fixtures are 10/10,
including refusals for a missing control, a missing ablation, an exit-code
FAIL MEANS, and a FAIL MEANS that does not name the claim.

## 2. Item 1: `tools/stonedesk_presence_stress.py`, exit 1

The run has 12 scenarios: 1 PASS, 8 FAIL, 3 controls OK. With `--ablate`, T1z
goes PASS → FAIL.

**What is real and what is stubbed:**
- **REAL:**
  - the `api/sd-data.js` `sd_approvals` write handler;
  - `complianceStatus()`, taken from the text of `api/sd-sub-data.js`;
  - `subxCompliancePill()` and `safetyUpdateKPIs()` from `stonedesk.html`,
    run in a vm;
  - the silica markup in `stonedesk.html`, read statically.
- **STUBBED:** the licence, the session, an active employee-auth row, and
  the Supabase write (which records what would have been stored).

| ID | Claim the user sees | The truth | Verdict |
|---|---|---|---|
| T1c | Signed | a real approval with a PNG signature | CONTROL-OK |
| T1a | Signed | `signature_png: null`, so no signature at all | **FAIL**: stored, 200 |
| T1b | Signed | `signature_png` is `data:image/png;base64,AAAA`, not an image | **FAIL**: stored, 200 |
| T1d | paid | the client sent `deposit_status: 'paid'`, and no payment exists anywhere | **FAIL**: stored verbatim |
| T1z | Signed | a $0 approval | PASS: refused 400 NO_TOTAL |
| T2c | COMPLIANT | COI and licence valid, W-9 on file | CONTROL-OK |
| T2a | COMPLIANT | no licence on record and no W-9 | **FAIL**: green COMPLIANT |
| T2b | COMPLIANT | **no certificate of insurance on record** | **FAIL**: green COMPLIANT |
| T3c | 100% | current training and an exposure-control-plan owner | CONTROL-OK |
| T3a | green score | an EMPTY safety record | **FAIL**: 80%, green |
| T3b | green score | 2019 silica training with no expiry entered | **FAIL**: 100%, green |
| T4a | 0 Dry Cut Violations | no exposure data is read anywhere | **FAIL**: the tiles are literals (12 / 0 / 8 / AL) |

## 3. Items 2 and 3: findings ROUTED, not self-registered

**How I read the dispatch.** Item 2 says to log findings to the register.
Item 3 says not to self-register findings outside `tools/`. Item 3 is the
more specific, so it governs:
- each finding below sits in `api/` or `.html`, so it is routed to that
  file's owner, who registers it against their fix commit;
- `tools/` produced no defect this batch, so cc filed no register record.

The status registry carries a FOR HANK note and a FOR FOURTH note, both
appended and confirmed by re-reading. Each record below is ready to file.

| # | Owner | File:line | Finding | Suggested severity | Fix, and the scenario that should turn PASS |
|---|---|---|---|---|---|
| 1 | **hank** | `api/sd-data.js:3814-3862` | An `sd_approvals` write with no signature, or an undecodable one, is stored as a signed approval. | high (legal record) | Refuse a `signature_png` that does not decode to a PNG; T1a and T1b. |
| 2 | **hank** | `api/sd-data.js:3859` | `deposit_status` is free client text, stored and shown verbatim, so "paid" is a client assertion. | high (money) | Derive the status from a payment record, or refuse "paid" from the client; T1d. |
| 3 | **hank** | `api/sd-sub-data.js:67` | `complianceStatus` treats a missing COI or licence as "untracked" rather than as blocking, and never considers `w9`. | high (liability) | Count a missing COI as blocking and report W-9 absence; T2a and T2b. |
| 4 | **fourth** | `stonedesk.html:36608` | `subxCompliancePill` shows COMPLIANT unless BOTH documents are untracked. | high | Show COMPLIANT only when every required document is valid; T2a and T2b. |
| 5 | **fourth** | `stonedesk.html:28004` | `safetyUpdateKPIs` starts the score at 100 and only subtracts, so an empty record is 80% green and a blank expiry counts as current. | moderate (OSHA) | Score from evidence present, and treat a blank expiry as not current; T3a and T3b. |
| 6 | **fourth** | `stonedesk.html:10809-10812` | The OSHA 1926.1153 silica tiles are hardcoded literals: "12 Wet Cut Days MTD", "0 Dry Cut Violations", "8 Air Samples YTD", "AL Max Level". | high (fabricated compliance data) | Bind the tiles to the exposure log, or show "not tracked"; T4a. |

**Not driven this batch,** listed by the survey and left open for the next
StoneDesk pass:
- `esigApprove` (`stonedesk.html:41693`). A 1-pixel or missing canvas counts
  as signed; a stale `lastCalc` can be paired with another quote's number;
  and the customer match is the first name match.
- Invoice "Paid" from a typed deposit (`invSave` at :12102 and
  `esigCreateInvoice` at :41922).
- The margin constant of 65% (`finUpdateKPIs` at :28605).
- `taxRender` sums all time, and the rate is unbounded (:43330).

**A note on b55.** The four b55 register records were product findings filed
by cc against cc's measuring commit. Item 3 of this dispatch reads as a rule
against exactly that. They are left as they are; I have not deleted or
re-filed them without Michael's word.

## 4. OPEN

| Item | Owner | Next step |
|---|---|---|
| Findings 1-3 | hank | Fix them, file each to the register against the fix commit, and re-run `python tools/stonedesk_presence_stress.py`. |
| Findings 4-6 | fourth | Same. fourth already holds `stonedesk`. |
| Tier A obligation on `sd_approvals` (the cc b56 tool) | hank | `tier_a_review_gate.py --discharge cc <opened_at>` |
| Undriven StoneDesk targets (`esigApprove`, invoice Paid, margin, tax) | cc, next StoneDesk batch | Add them as scenarios in `tools/stonedesk_presence_stress.py`; the checklist is already enforced. |
| The b55 self-registered records | Michael | Decide: keep them, or have them re-filed by their owners. |
| Carried | hank / fourth / cody / H1 | the b55 SAIRNlaw items, register 1-7, `38b2b506`, `d6b37bb1`, #1694 / #1691 |
