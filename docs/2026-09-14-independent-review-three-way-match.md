# Independent review — the three-way match, both apps

**2026-09-14 (Hank).** Item 44 applied for real rather than designed: a review
by someone who did not write the code, on Tier A financial logic that until now
had only ever been read by its author.

**Subjects:** `57236fe9` (SAIRNbiz — purchase orders, goods receipts, and a bill
that cannot settle unmatched) and `2701afb8` (StoneDesk — a real PO sequence and
a join key on all three documents). Both by CC, both claims released.

**Method:** read the diffs, then **extract and run the shipped functions against
real amounts**. Reasoning about a money comparison is how a 38% accuracy figure
got fabricated on this platform once already; every claim below was executed.

---

## Finding 1 — the match refused CORRECT bills. **FIXED** (`a58af8ca`)

`sbThreeWayMatch` compared money with

    Math.abs(billAmt - recvVal) > SB_MATCH_TOLERANCE     // tolerance 0.00

with `recvVal` a floating-point sum of the receipts. Run against the shipped
function:

| PO | receipts | bill | float sum | verdict |
|---|---|---|---|---|
| $1,200.00 | $1,200.00 | $1,200.00 | 1200 | MATCHED |
| **$3,828.47** | **$1,870.93 + $1,957.54** | **$3,828.47** | 3828.4700000000003 | **REFUSED** |
| **$1,558.05** | **$286.15 + $1,271.90** | **$1,558.05** | 1558.0500000000002 | **REFUSED** |

**The message it printed is the sharpest part:**
`billed $3828.47 against $3828.47 actually received` — two identical figures and
a refusal, with nothing a person could correct.

A zero tolerance is the right policy and is kept; deciding money equality in
binary floating point is what was wrong. Registered as record 61, `high`,
`detection_method: independent-review`.

## Finding 2 — every bill entered before the gate is now unpayable. **NOT FIXED**

`sbPayBill` requires `b.matched` **and** a fresh match. A bill written before
`57236fe9` has no `po_num` and no `matched` field, so `sbThreeWayMatch('' , …)`
returns *"no purchase order number on this bill"* and **`b.matched` is
`undefined`**. Every pre-existing open payable therefore refuses settlement,
permanently, with a message naming a field that did not exist when the bill was
entered.

It fails closed, so nothing wrong is paid. But the only route past it is to
delete and re-enter the bill, which destroys the record it was protecting — and
"a refusal a person cannot act on is one they will route around" is CC's own
sentence.

**This is a product decision, not a defect to patch silently.** The options are
genuinely different: grandfather bills dated before the gate; require a one-time
PO to be attached; or leave it and accept the manual clean-up. **Left for
Michael or CC** rather than chosen here.

## Finding 3 — StoneDesk got the join key without the gate. **NOT FIXED, by design**

`2701afb8` adds `po_num` to StoneDesk receipts and bills and makes the sequence
real. It adds **no match gate**: `sdAPAdd` stores the field and nothing checks
it, and the PO number is optional on both documents. The commit is honest about
this — *"what it buys is that a bill which DOES answer a PO can be matched to
it"* — and optional is defensible there, since a utility bill never has a PO.

**Recorded because of the asymmetry, not as a criticism of the commit.** Two
apps on one platform now hold the same three documents at two different levels
of protection on money, and that is exactly the re-qualification question
disciplines §7 exists for: the pattern was proven in SAIRNbiz and *not*
propagated, which is as much a decision as propagating it would have been. It
should be a recorded answer, not an omission nobody wrote down.

## What was checked and found clean

Stated so the review is not read as only a list of complaints:

- **No XSS.** `toast()` uses `textContent`, and every rendered field goes
  through `H()`. Vendor names reach the refusal messages and are safe.
- **The PO sequence is correct in both apps.** Reserve-before-write, so a failed
  write burns a number and leaves a gap rather than a reuse; the floor is taken
  from both the counter and the existing rows, so a restored backup cannot
  collide; a failed reservation refuses instead of minting an unrecorded number.
- **The stored-verdict / live-verdict pair is right**, and the reasoning in the
  commit holds: requiring both means a change to any of the three documents can
  only make settlement harder.
- **The `ap-due` → `ap-due-date` fix in StoneDesk is a real defect correctly
  found** — a div answering for an input, invisible to
  `missing_dom_target_check.py` because the id exists and only the *kind* of
  element is wrong.
- **Over-receipt is refused**: two receipts of $1,200 against a $1,200 PO sum to
  $2,400 and the bill is held.

## Limits of this review

- **Read and executed, not deployed.** Nothing here was exercised against a live
  SAIRNbiz licence.
- **`sbRecvLog` accepts a receipt of value 0** — it fails closed (the bill is
  then refused against $0.00 received) and is inconsistent with `sbPOCreate`,
  which requires an amount. Noted, not raised as a finding.
- **A receipt with an empty vendor skips the vendor comparison.** Defensible —
  absent is not "differs" — but it is a leg of the match that a blank field
  turns off.
- **Concurrency was not assessed.** Both apps store to `localStorage`; two tabs
  raising a PO at once is outside what was tested here.
