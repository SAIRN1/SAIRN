# SAIRN handoff: cc, batch b55, 2026-10-23 (SAIRNlaw)

**All six items are closed.** Three tools are built and each was run against
the real code. Four register records are filed under one named pattern. No
product code changed. No `--force`, no override. The clone reads 0 0 against
origin.

| | |
|---|---|
| Landed | `1eab8820` (three tools), `bb415802` (four register records), then OWNER lines + the Tier A obligation, pushed `c3bcc21a..43990904`, then these deliverables |
| Claims held | `sairnlaw` (cc), released at the end of this batch |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 1. Item 4 first: what already existed (reuse, not duplication)

A read-only survey was run before any tool was written.

- **Citator:** PARTIAL.
  - `api/legal-citator.js` `verify` (CourtListener plus `cl_case_cache`) is
    real.
  - **No test drove `verify`.** `tests/run_citator_freshness_probe.py` says
    the file "has no test harness".
  - The client side has `mtExtractCitations`, `mtVerifyCitations` and
    `lawCiteGuard`.
  - **The new tool drives these real functions; it does not reimplement
    them.**
- **Deadline rules:** EXIST. The engine is in `api/_lib/deadline-engine.js`.
  There are 39 `deadline-*.test.js` files and 47 seed files.
  - Nothing listed coverage per jurisdiction.
  - The new tool reads the existing tests and seeds. It adds no test.
- **IOLTA reconcile:** EXISTS. `reconcileTrustLedger()` has 33 unit arms, a
  mutation probe and a wiring probe.
  - The new tool reuses the real function and the real label table, and adds
    adversarial scenarios the existing suite does not have.

## 2. Item 1: `tools/sairnlaw_citator_stress.py`. Exit 1, 4 PASS / 8 FAIL / control OK

**What is real and what is a fixture:**
- **Real:** the `api/legal-citator.js` verify handler.
- **Real:** `sairnlaw.html`'s `MT_CITE_PATTERNS`, `mtExtractCitations`,
  `mtVerifyCitations` and `lawCiteGuard`. They are extracted by signature,
  refused if found twice, and run in a vm, with `citatorFetch` wired to the
  real handler.
- **Fixture:** CourtListener's answers (`UPSTREAM`).
- **Stubbed:** licence, audit and an empty cache.

**The full corpus and every verdict is in the report**, with its input text,
extraction and state. In summary:

- **PASS (4).** These are flagged `not_found`:
  - Varghese, 925 F.3d 1339;
  - Petersen, 905 F. Supp. 2d 121;
  - 999 U.S. 9999;
  - an off-by-one page, 347 U.S. 484.
- **FAIL (8):**
  - **Wrong court**, Brady 373 U.S. 83 (9th Cir.): VERIFIED.
  - **Wrong case name**, Roe v. Smith, 410 U.S. 113: VERIFIED as Roe v. Wade.
  - **Invented holding**, Miranda 384 U.S. 436: VERIFIED.
  - **Never extracted, so never shown:**
    - Shaboon v. Egyptair, 2013 IL App (1st) 111279-U (a public-domain
      citation);
    - Martinez v. Delta, 2019 WL 4639462 (a Westlaw citation);
    - Durden v. KLM (a bare case name).
  - **Seventh in a draft:** extracted, then dropped. `slice(0,6)` keeps six,
    and the guard prints `checked.length`.
  - **X1 substring collision**, a direct API call: the fabricated `47 U.S.
    483` comes back VERIFIED as Brown v. Board, and the real Brown cite comes
    back `not_found` (`legal-citator.js:285-287`).
- **Control:** a correct Brady citation is VERIFIED.
- **Ablation:** with the fixture changed so the upstream resolves Varghese,
  F1 turns red.

## 3. Item 2: `tools/sairnlaw_deadline_coverage_gap.py`. Exit 1, 37 of 39 jurisdictions have a gap

- **NO ISOLATION test:** in, mi, pa (oldest seeds, 2026-08-22), il, ca, ny,
  tx.
- **INCIDENTAL ONLY:** oh (one arm in the Mississippi suite) and ga (one arm
  in the West Virginia suite).
- **NO MUTATION / sabotage arm:** 37 of the 39. Only me
  (`deadline-maine.test.js`) and us-federal (`tests/sairnlaw_retrigger.js`)
  are covered both ways.
- **The table is ordered oldest-untested first,** by the first commit of each
  jurisdiction's seed. It is in the report.
- **Rules:**
  - Isolation needs a test that requires the real engine, reads the
    jurisdiction's own seed by name, and is named for the state.
  - A `readdirSync` suite counts as cross-cutting, not isolation.
  - The criteria lock is 8/8.

## 4. Item 3: `tools/sairnlaw_iolta_reconcile_stress.py`. Exit 1, 7 PASS / 2 FAIL / control OK

**Surfaced (7):**
- one-cent bank short;
- an unrecorded $500 at the bank;
- the device total one cent off;
- a disbursement keyed as a deposit;
- an unreadable amount;
- an undated row (PARTIAL);
- a misallocation that drives a client NEGATIVE. That one is AGREES, but the
  dashboard paints a Trust Alert.

**Silently reconciled, shown as "Reconciled" (2):**
- **M5:** a $40 TRUST SHORTFALL parked as a deposit in transit 91 days old.
  Client B is credited 540; 1340 is owed against 1300 in the bank. Outstanding
  items have no age limit.
- **M6:** a $200 disbursement for client A charged to client B, with the
  totals unchanged. The client leg is derived from the same rows (the code
  itself labels it structural), and the device leg compares a total only.

**Tier A:** the tool names `law_trust_reconcile`, so the push gate required
an obligation. It is recorded and **assigned to hank**.

## 5. Item 5: methodology, the named pattern

**PRESENCE PASSED AS PROOF.** A check confirms that a thing EXISTS and the
app reports that as the thing being RIGHT. All three items show it:
- a case exists at this cite, so the citation is called "verified";
- the totals match, so the books are called "Reconciled";
- a test file exists for a state, so the state is treated as covered, though
  the test has never been seen to fail.

Four records are in `docs/defect-density-register.json`. They are filed
against the measuring commit `1eab8820`, which has precedent in
`877191ec5d09` and `25814d5521fa`. All four are OPEN:

| Record | Layer / severity | Owner(s) |
|---|---|---|
| Citator existence-only, plus extraction blind spots, plus the 7th citation dropped | product / high | hank (api), fourth (html) |
| Citator key-matching substring transfer (X1) | product / moderate | hank |
| IOLTA M5 / M6 silent reconcile | product / high | hank (api/_lib), fourth (html) |
| Deadline rules: 37/39 with no mutation arm, 9 with no dedicated isolation | test / moderate | cody (tests), hank (api/_lib) |

`defect_register.py --check` passes; the register holds 734 records.

## 6. OPEN, with the exact next step

| Item | Owner | Next step |
|---|---|---|
| Citator: verified means "exists" | hank + fourth | Compare the claimed case name and court with the resolved cluster, and add a `mismatch` state that is never "verified". Show every extracted citation, not the first six. Flag WL, public-domain and bare-name shapes as unchecked. Then re-run the stress tool: A1-A3, A5 and F3-F5 should PASS. |
| Citator X1 | hank | Match on the normalised reporter cite only, one result per key, and never overwrite a different key. Then X1 should PASS. |
| IOLTA M5 / M6 | hank + fourth | Add an age threshold for deposits in transit, reported as its own discrepancy. Give the reconciler an independent per-client record. Then M5 and M6 should PASS. |
| Deadline coverage | cody + hank | Add a one-rule mutation probe per jurisdiction, oldest first: oh, in, mi, pa, il, ca, ga, ny, tx. Add dedicated suites for the 9. |
| Tier A review of the IOLTA stress tool | hank | Discharge it with `tier_a_review_gate.py --discharge cc <opened_at>`. |
| Carried | H1 / fourth / hank / cody | #1694 and #1691; register 1-7 and the b49 gaps; `38b2b506`; `d6b37bb1` |
