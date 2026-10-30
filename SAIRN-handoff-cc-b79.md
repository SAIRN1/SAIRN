# SAIRN handoff: cc, batch b79, 2026-10-30

**Context:** CONTEXT 29.4% of 1,000,000 -- 294,439 tokens, measured. The declared window is 1,000,000.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\a046cdf7-9eaf-4291-b1ac-b9b8bb34da67.jsonl`

**Claims:** none. `sairn_claim.py list` returns "No active claims."

## 1. Item 5: test_965 (hover b92) released to the audit track

cc never held a `sairn_claim` claim on test_965. Its only hold was the Tier A
ledger's `reviewer_owner: "cc"` on the hover record opened at
2026-10-28T21:14:26Z.

`tier_a_review_gate.py` has no command that releases a live owner:
`--reassign-dead` moves only dead owners, and only to builders. So I edited
that one record in `docs/tier-a-reviews.json`:
- `reviewer_owner` and `owner_assigned_at` are now null;
- `owner_released` records cc, the date, and Michael's standing ruling;
- `owner_note` now starts "AUDIT TRACK ONLY -- released by cc ...".

`--list` now prints the record as `UNOWNED -- first-come. AUDIT TRACK ONLY
...`, and `--validate` reports 323 records, identities unique, statuses in
vocabulary.

## 2. Item 1: manifest and ledger edits were diffed in scratch before writing

There were no `docs/sairn-path-manifest.json` edits this batch, so the
manifest line-delta is 0.

The ledger edit went through the same discipline:
- **First pass:** built in scratch and diffed against `git show
  HEAD:docs/tier-a-reviews.json`. **11 diff lines, one record only.**
- **Second pass**, rewording `owner_note`: diffed against the working copy
  (**2 diff lines**) and against HEAD (**still 11**).

## 3. Item 2: what each blocked item actually asks

### Licensing plan §7 (`docs/licensing-product-plan.md`): eight decisions

1. **Revisit the 2026-08-26 paid-path no-bid?** That decision said to revisit
   only if inbound demand appeared unprompted, and the plan found none.
   - Recommendation: keep the no-bid for standalone skills, and treat a
     platform licence as a separate question gated on Phase 2.
2. **What to call the verification SKU.**
   - Recommendation: "verification report" or "evidence report", not
     "certificate", with counsel to confirm.
3. **Is the agent control platform a product at all, or only a capability
   inside dev services?** Phase 2 is designed to answer this with evidence. The
   decision is whether to start down that road.
4. **What the services rate is, and the terms of the Phase 2 pilot.** No rate
   exists anywhere in the repo.
5. **Which skills to publish next in Phase 1**, and the review date that the
   August decision's condition 5 requires.
6. **Who owns support.** A licence implies support, and no owner is named.
7. **What counsel is asked**, as one combined question:
   - how Anthropic's usage clause applies to a control platform;
   - whether "certificate" wording is a problem;
   - the MIT, APMP and DISC items.
8. **Whether to run `sairn-decision-gate` formally on the plan** before any
   external conversation.
   - Recommendation: yes, on the Phase 2 pilot offer.

### ctxmeter path (C-3)

- **The original ask (b70/b71):** fix a "false-floor" bug in a file called
  `ctxmeter.py`.
- **What cc b71 searched, finding nothing named `ctxmeter*`:**
  - the four builder clones;
  - `Documents/SAIRN`;
  - `~/.claude`;
  - the Claude scratchpads;
  - `G:\My Drive\SAIRN-status`;
  - a home directory search four levels deep.
- **Re-checked this session:** `find . -name "ctxmeter*"` is still empty.
- **What is needed:** Michael gives the real path, or says it was a different
  name, for example the status-line or context-watch tool. Then the false-floor
  bug can be fixed and cause-tagged.

### Audit credentials (C-4)

- **What it asks:**
  - Provision employee sessions for the roles admin, sales and install on
    StoneDesk audit licence `SD-AUDIT-2026`.
  - Provision a dental audit licence with roles owner, frontdesk and provider.
- **Why:** the three field-scope reads `sd_crm.read`, `dnt_rollup.read` and
  `exec_context.read` can then get `live` blocks in
  `tools/field_scope_rules.json`. Today they have none (checked b78).
- **Steps once the credentials exist:**
  1. Generate fixture SQL from `seed()` in
     `tools/sairn_field_scope_check.py`.
  2. Add the `live` blocks.
  3. Run `python tools/sairn_field_scope_check.py --live --only sd_crm.read,dnt_rollup.read,exec_context.read`.

### Caregiver credentials (C-5, open-work #1756)

- **What it asks:** readable caregiver sign-in credentials on
  `SEN-AUDIT-0002`.
- **The run they enable:** a caregiver signs in on a device whose localStorage
  already holds the full roster, and the session hydrates.
- **What the run confirms:** `sen_caregivers` in localStorage then holds
  only the caregiver's own row, with no `bgcheck_date`,
  `state_caregiver_id` or `notes`. That is the authenticated live half of
  the caregiver-roster redaction.

## 4. Item 3

**The 580h quotes record is closed.**
- cody discharged it on 2026-10-29 (SOUND-WITH-GAPS).
- cc's b74 second review found the echo-chain miss.
- fourth fixed that in `c7d7e74d`. The b74 probe now prints `0 of 10
  wrong`, exit 0 (b78).
- The record is no longer in the open list.

**Hook presence is 4 of 4, exit 0.** The open list now has **5 obligations**.
- One new one is ASSIGNED TO cc: cody 2026-10-30T09:00:48Z, on invoices and
  sd_invoices (cody b68, 13 licence guards). It is not in this dispatch, so it
  is left for the next batch.
- The full literal output is in the report.

## 5. Item 4: defect register

**No b78 row was needed.** b78's N-5 sweep found no C7 bypass and made no fix.

The b77 shared_knowledge C7 row **is** written: commit `52b9ca3a`,
sairnlegacy, high, code-review, confirmed in b78.

## 6. Open

| # | Item | Owner |
|---|---|---|
| N-6 | Tier A cody 2026-10-30T09:00:48Z (invoices, sd_invoices): ASSIGNED TO cc | cc, next batch |
| L-1, C-3, C-4, C-5 | §3 above | Michael |
| G-1, K-1..K-3 | per b77 | fourth, cody |
