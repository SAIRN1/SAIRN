# SAIRN handoff: cc, batch b57, 2026-10-27 (StoneDesk, presence passed as proof, part 2)

**All six items are closed.** The extended stress tool and the ROUTE
checklist item landed at `fc042cf0`, pushed as `b1d395d3..6bf998c6`. The
clone reads 0 0 against origin. No product code changed, nothing was
self-registered, no `--force`, no override.

| | |
|---|---|
| Landed | `fc042cf0` (tools), then these deliverables |
| Claims held | none. fourth holds `stonedesk`; cc's work is read-only tools in `tools/` |
| Context | 70.8% measured at the handoff (see the digest's CONTEXT line) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 1. Item 1

The four b55 SAIRNlaw records are kept as they are, per Michael. Nothing was
changed.

## 2. Items 2 and 3: 17 new scenarios, all under the checklist

`python tools/stonedesk_presence_stress.py --ablate` gives 29 scenarios:
1 PASS, 21 FAIL, 7 CONTROL-OK. With the $0 refusal compiled out, T1z goes
PASS → FAIL.

- Every new scenario names its CLAIM, TRUTH, an operational FAIL MEANS and a
  DETECTOR, plus a SITE.
- Each of the four new families has its own CONTROL.
- The checklist refused my own first plan, because X2's FAIL MEANS did not
  name its claim. I fixed the wording, not the rule.
- **Controls proved their worth while I was building it.** All four new
  controls first came back CONTROL-FAIL, because escapers were missing from
  the harness (`escHtml`, then `escAttrJs`, then `jsStr`). The run exits 2
  until they are loaded. They are now loaded from `stonedesk.html` itself and
  are not retyped.
- A crash counts as a FAIL. That matters for M3 below.

| ID | Claim | The truth | Result |
|---|---|---|---|
| E0 | Project Approved! | a drawn signature on the current quote | CONTROL-OK |
| E1 | Project Approved! | **there is no signature pad on the page** | FAIL: approved, `sigDataUrl` is "" |
| E2 | Project Approved! | one pixel at 1/255 alpha | FAIL: approved |
| E3 | Project Approved! | the screen shows Q-200 at $9,800; `lastCalc` holds $3,000 | FAIL: Q-200 is recorded at $3,000 |
| E4 | Project Approved! | two customers are named Maria Lopez | FAIL: the first is marked approved, with no choice offered |
| I0 | Paid | $5,000 invoice, $5,000 cheque | CONTROL-OK |
| I1 | Paid | a $6,000 cheque on a $5,000 invoice | FAIL: Paid with $0 balance, and no $1,000 credit anywhere |
| I2 | marked as Paid | the store write FAILED | FAIL: the "Invoice marked as Paid" toast still shows |
| I3 | Paid | a 50% deposit-REQUEST invoice | FAIL: saved as Paid, with a $6,200 payment taken from a leftover deposit field |
| M0 | 60% | full costs entered | CONTROL-OK |
| M1 | green | the slab cost is blank | FAIL: 90%, green |
| M2 | 65% | no costs recorded anywhere | FAIL: the margin KPI is a constant 65% |
| M3 | margin | `saveQuote` stores `total` as a NUMBER (`lastCalc.total`) | FAIL: a **TypeError**, so the Financial KPIs never render once any quote is saved |
| X0 | $100 | one entry this year | CONTROL-OK |
| X1 | YTD | a $900 entry from 2024 | FAIL: YTD shows $1,000 |
| X2 | Logged | a rate of 825 | FAIL: logged at 825% |
| X3 | 0 | $5,000 paid to an installer LLC | FAIL: the 1099 tile is a literal 0 |

**Three of these depend on a condition, and I say so.** E3 needs `lastCalc`
to be stale. I3 needs the deposit field to still hold a value. E2's
1/255-alpha pixel is a judgement call about what counts as a signature. Each
is a real path in the code. How often each happens is not measured.

The b56 rows are unchanged: T1a, T1b, T1d, T2a, T2b, T3a, T3b and T4a.

## 3. Item 4: ROUTED, never self-registered

**What was routed:**
- The tool prints a ROUTING table, with each owner read from the path
  manifest.
- It writes nothing to `docs/defect-density-register.json`, and neither did
  cc.

| Owner | Sites | Note |
|---|---|---|
| **fourth** (`*.html`) | E1 :41700, E2 :41701, E3 :41717, E4 :41785; I1 :12123, I2 :12157, I3 :41945; M1 :28624, M2 :28608, M3 :28607; X1 :43341, X2 :43323, X3 :43343 (all `stonedesk.html`); plus T2a/T2b :36608, T3a/T3b :28004/:28007, T4a :10809 from b56 | FOR FOURTH status note appended and confirmed |
| **hank** (`api/`) | T1a/T1b `api/sd-data.js:3862`, T1d :3859, T2a/T2b `api/sd-sub-data.js:67` (from b56, unchanged) | b56 FOR HANK note stands; Tier A obligation on `sd_approvals` still open |

**The fix each finding needs:**
- **E1/E2:** refuse to approve without a pad and a real stroke count.
- **E3:** take the total from the same quote as the quote number.
- **E4:** match the customer by id, not by name.
- **I1:** record the overpayment as a credit.
- **I2:** check `invSaveStore()`.
- **I3:** clear the deposit field when the form is pre-filled.
- **M1/M2:** compute margin from recorded costs and show "unknown" when they
  are missing.
- **M3:** coerce `q.total` to a string.
- **X1:** filter YTD to the current year.
- **X2:** bound the rate.
- **X3:** derive the 1099 count or show "not tracked".

## 4. Item 5: the rule is now enforced by default

The "route, never self-register" rule is now in `tools/presence_proof.py`:
- **Checklist item 9, ROUTE:** "a FAIL is routed to that file's owner and is
  NEVER self-registered".
- **`plan_problems()`** refuses a stress scenario with no SITE, which makes
  the run exit 2.
- **`route()` and `may_self_register()`** read the owner from
  `docs/sairn-path-manifest.json`. No list is kept in the tool.
- **The tool exits 2** if a FAIL routes to no owner.
- **`docs/TOOLING-INVENTORY.md`**, which is generated from PURPOSES, carries
  the rule in both tools' entries.
- **Fixtures, 16/16**, check that api/ goes to hank, .html to fourth and
  tests/ to cody, and that cc may not self-register an api/ finding.

## 5. OPEN

| Item | Owner | Next step |
|---|---|---|
| The 13 new `stonedesk.html` findings (E, I, M and X rows) | fourth | Fix them, starting with M3 (it breaks the KPI panel for every user with a saved quote) and E1/E2 (signing). Register each against your fix commit, then re-run the tool. |
| The b56 findings | hank / fourth | As in cc b56, section 3 |
| Tier A review of the stress tool (`sd_approvals`) | hank | `tier_a_review_gate.py --discharge cc <opened_at>` |
| Carried | hank / cody / H1 | the b55 SAIRNlaw items; `38b2b506`; `d6b37bb1`; #1694/#1691 |
