# SAIRNbiz — Cross-Domain Attention Digest

**Status:** Design approved by Michael 2026-08-10. Not yet implemented —
no code written under this spec. This is item 4 of the 6-item AI-native
roadmap for SAIRNbiz, and the flagship item: the first feature that
genuinely reasons across HR (training, performance) and Accounting
(budget, AP) in one place, the specific capability the platform's
competitive research identified as unoccupied.

## 1. Problem

`rDash()`'s `#d-actions` widget (`sairnbiz.html:1354-1361`) already
attempts exactly this — overdue AR/AP, expiring certs, open hiring,
reviews due — but it's built entirely on stale, never-recomputed status
labels, and it's missing budget overages. Confirmed, not assumed:

- **No edit function exists for `sb_train` at all.** `status` (e.g.
  "Expiring Soon") is written once by `seed()` and never touched again —
  a cert seeded months ago as "Active" that has since actually expired
  will show "Active" forever.
- **The AP "Pay" button is a no-op.** `rAP()`'s bill row (`sairnbiz.html:1644`)
  renders `<button onclick="toast('Marked paid')">Pay</button>` — it
  shows a success toast and changes nothing. `status`/`bal` are frozen
  at whatever `saveBill()` (`sairnbiz.html:1467-1474`) set at creation.
  A bill overdue by two months but entered as "Open" never becomes
  "Overdue" in the data.
- **`sb_perf` review `status` never auto-flips to overdue either.**
  `saveReview()` (`sairnbiz.html:1428-1435`) writes whatever the form's
  status dropdown held at creation time; nothing recomputes it against
  `due` as time passes.

This spec fixes the widget to compute directly from real dates instead
of these labels, and adds the missing budget domain — rather than
building a second, parallel "what needs attention" surface that could
disagree with the first, the exact class of bug (two systems, one
question, two different answers) found and fixed repeatedly elsewhere
in this platform tonight.

## 2. Non-goals

- **No fix to the underlying stale-data causes.** The AP "Pay" button
  being fake, and there being no way to update a training cert's status
  at all, are real, separate bugs — logged to `SAIRN-BACKLOG.md`, not
  fixed here. This spec works around them (compute from dates, ignore
  the unreliable labels) rather than fixing them.
- **No cross-domain magnitude ranking.** Findings are grouped by domain
  (Budget → AP → Training → Performance) within each severity tier, not
  ranked against each other by some unified urgency score. Simpler, and
  matches the existing widget's own fixed domain ordering.
- **No new write capability, no new persistence.** Same platform-wide
  rule as every prior item.
- **`rDash()`'s KPI tiles, department breakdown, revenue trend, and
  activity feed are untouched** — only the `#d-actions` block
  (`sairnbiz.html:1354-1361`) is replaced. This is a deliberate, narrow
  exception to the "don't touch existing rendering functions" discipline
  from items 2-3: that block *is* the feature being fixed, not adjacent
  working code.

## 3. Severity model (two tiers, matching item 3's precedent)

| Domain | Source | CRITICAL | WARNING |
|---|---|---|---|
| Budget | `sb_bud`, `{cat, annual, actual}` | `actual/annual > 90%` (matches `rBud()`'s own "Over Budget" label, `sairnbiz.html:1676`) | `75–90%` (matches "Watch") |
| AP | `sb_ap`, `{vendor, inv, due, amt, bal, status}` | `due` date already passed AND `status !== 'Paid'` (computed from the real date, not the `status` field's "Overdue" value) | `due` within 14 days, not yet passed, `status !== 'Paid'` |
| Training | `sb_train`, `{emp, cert, exp, status}` | `exp` date already passed (computed from the real date, not `status`) | `exp` within 30 days |
| Performance | `sb_perf`, `{emp, type, due, status}` | `due` already passed AND `status !== 'Completed'` (computed from the real date, not `status`) | `due` within 14 days, `status !== 'Completed'` |

14-day AP/performance threshold matches this file's own existing
`rTax()` "Due Soon" pattern (`sairnbiz.html:1704`, `daysOut<14`). 30-day
training threshold is a real-world cert-renewal lead time, confirmed
with Michael — no existing precedent for certs specifically in this
file, so this one is a deliberate new number, not reused from elsewhere.

## 4. Architecture

**`checkAttentionItems()`** — new, pure, standalone function (same
architectural shape as item 3's `checkPayrollAnomalies()`): reads
`ld('sb_bud',[])`, `ld('sb_ap',[])`, `ld('sb_train',[])`,
`ld('sb_perf',[])` directly, no DOM access, no `rPay()`/`rBud()`/etc.
dependency. Returns an array of finding objects:
`{severity:'critical'|'warning', domain:'budget'|'ap'|'training'|'performance', subject, message}`.

**Two consumers:**
- **`rDash()`'s `#d-actions` block** (`sairnbiz.html:1354-1361`) —
  replaced to call `checkAttentionItems()` and render its findings
  instead of the current inline stale-status filtering. Grouped by
  domain within severity tier (all CRITICAL findings first, in Budget →
  AP → Training → Performance order, then all WARNING findings in the
  same domain order). Empty state ("Nothing needs attention") unchanged.
- **AI tool, `get_attention_digest`.** `sensitive:true` (owner-only —
  combines financial data already gated elsewhere with performance/PIP
  data not previously gated anywhere in this app; one consistent gate
  rather than a per-domain split). No arguments. `run()` calls
  `checkAttentionItems()` directly and returns
  `{critical_count, warning_count, findings}` — lets the assistant
  synthesize a real prioritized narrative on request, the actual
  "flagship" capability: reasoning across HR and Accounting data in one
  answer, grounded in real records, not a description of what it could
  theoretically check.

**No changes to `rPay()`, `rBud()`, `rAP()`, `rTrain()`, `rPerf()`,
`genReport()`, `sbExecuteTool()`, or `callAI()`.**

## 5. Testing

- **Stale-label independence test (primary):** seed a scenario where the
  stored `status` field and the real date actively disagree — e.g. a
  training cert with `status:'Active'` but `exp` in the past, an AP bill
  with `status:'Open'` but `due` months ago, a review with
  `status:'Scheduled'` but `due` last month. Confirm all three are
  correctly flagged CRITICAL despite their stored status saying
  otherwise — this is the entire point of the fix, and the one thing a
  naive "just port the old logic" implementation would get wrong.
- **Budget threshold test:** a budget category at exactly 90%/91%/75%/76%
  → confirm boundary behavior matches `rBud()`'s own existing
  `u>90`/`u>75` logic exactly (same operators, same exclusivity).
- **Clean-state test:** no anomalies across all four domains → confirm
  `#d-actions` shows "Nothing needs attention," matching current
  behavior, and the AI tool returns zero findings.
- **AI tool test:** ask the assistant for a full attention/status
  picture; confirm the answer synthesizes findings from more than one
  domain in a single coherent response when more than one domain has
  findings — this is the real test of "digest," not just "list." Verify
  a non-owner role gets the restricted-access message.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`)
  after every `sairnbiz.html` change.
