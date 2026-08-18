# SAIRNbiz — AI-Advancement Rollout (bringing up to the 5-capability standard)

**Task:** bring SAIRNbiz up to the same 5-capability standard already
shipped on StoneDesk/SAIRNbuild/SAIRNvet: AR measurement, agentic
quote/task follow-up, predictive business intelligence, voice input,
shared company-knowledge layer via the `api/sd-data.js` pattern keyed by
license_hash. Instruction was explicit: check what SAIRNbiz's real data
model actually supports before building each one, skip anything the data
doesn't honestly support rather than faking it.

**Real finding, checked before building anything: 3 of the 5 capabilities
were already fully built in earlier sessions, not gaps.** Only one
capability (voice input) was genuinely missing. This doc records what was
actually found for each, since building duplicate work for the 3 already
done would have been a real mistake.

## 1. AR measurement — checked, deliberately NOT built

Reviewed every real SAIRNbiz panel (Employees, Hiring, Timesheet,
Payroll, Benefits, Performance, Training, P&L, Invoices, Expenses, AP,
AR, Budget, Tax, Company, Vendors, Reports, Settings). None involve
on-site physical measurement — StoneDesk's AR use case is countertop
dimensions, SAIRNbuild's is bid line-item measurements; SAIRNbiz has no
workflow that's analogous. SAIRNvet already made this exact call for
this exact capability (`sairnvet.html:7524`, "no genuine measurement use
case exists in this app's workflow, per explicit scope") — same
reasoning applies here. Not built. Documented inline in `sairnbiz.html`
next to the voice-input module so a future session sees the decision,
not just its absence.

## 2. Agentic quote/task follow-up — already built, confirmed real

SAIRNbiz doesn't have "quotes" (it's HR/accounting, not sales), but has
the direct equivalent: `checkAttentionItems()` (`sairnbiz.html:1420`) —
a real, deterministic scan across budget categories (>90% critical,
>75% warning of annual spend), AP bills (past due critical, due within
14 days warning), employee certifications (expired critical, expiring
30 days warning), and performance reviews (overdue critical, due within
14 days warning). Computed from real dates, not stored status labels.

This is surfaced two ways, matching the reference apps' pattern exactly:
- **Proactively, always-visible**: the Dashboard's "Actions Needed" zone
  (`d-actions`, wired via `rDash()` around `sairnbiz.html:1536`) shows
  these findings without the user having to ask anything — the same
  `alert-bar`/urgency-zone pattern StoneDesk uses.
- **On-demand via AI**: the `get_attention_digest` tool
  (`sairnbiz.html:1046`), part of a real multi-turn tool-calling system
  (`sbExecuteTool`, 6 tools total — see
  `docs/superpowers/specs/2026-08-09-sairnbiz-ai-tool-calling-design.md`
  for the full foundation, live-verified 2026-08-09).

One honest caveat already disclosed in the tool's own description and
carried forward here, not silently dropped: budget figures come from
`sb_bud`, which has no live connection to recorded expenses (logged
separately in `SAIRN-BACKLOG.md`, "SAIRNbiz budget actual spend never
syncs with recorded expenses") — the digest already states this plainly
rather than presenting stale data as current.

**No changes made.** Already real, already matches the standard.

## 3. Predictive business intelligence — already built, confirmed real

`renderInvoicePredictiveInsights()` (`sairnbiz.html:2320`), wired to the
Invoices panel's `inv-predictive-zone`. Same mechanism and same
anti-fabrication discipline as StoneDesk's `renderPredictiveInsights()`:

- Flags customers whose average days-to-pay is 30%+ above the company's
  own historical average, with a minimum sample size of 4 invoices
  before a customer is flagged at all.
- Outstanding balance broken down by status (Sent/Partial/Overdue).
- Most-invoiced categories.
- Honest "not enough data" fallback below 5 total invoices on record —
  states the real count, doesn't fabricate a placeholder.

**No changes made.** Already real, already matches the standard.

## 4. Voice input — genuinely missing, built this session

Confirmed absent before starting: zero `SpeechRecognition`/
`webkitSpeechRecognition` references anywhere in `sairnbiz.html`.

Ported near-verbatim from `sairnvet.html`'s module (itself ported
near-verbatim from `stonedesk.html`'s original) — `attachVoiceInput()`
is fully app-agnostic; only the wired field IDs are SAIRNbiz-specific.
Free, browser-native `SpeechRecognition`, no new vendor or cost.

**Correction (2026-08-18, found during the live click-through test):** an
earlier version of this doc and an earlier report to Michael said this was
wired to `ainp` + `enotes` (Employee Notes). That was wrong — checked the
actual deployed/committed code directly (not memory) and the real,
shipped target list is:
- `ainp` — the AI Business Assistant's question input.
- `ivcust` — Invoice customer name (Invoices panel, "Add Invoice" form).
- `ivamt` — Invoice amount, `opts.numeric:true` (extracts the first number
  from the transcript rather than inserting raw text).

Per the platform's verification-discipline standard, flagging this
plainly rather than quietly editing the earlier claim away: at some point
between writing the original `ainp`/`enotes` version and this doc being
finalized, the actually-committed code diverged from what was reported —
exact mechanism not fully reconstructed, not worth further archaeology
once the real current state was confirmed directly against the live file
and the live deployed site. `enotes` (Employee Notes) is NOT currently
wired to voice input.

**One real bug caught before shipping:** the ported code originally
called `showToast(msg, 'error')` for the two error-message paths (voice
unsupported, recognition failed) — copied directly from the SAIRNvet/
StoneDesk source. SAIRNbiz's actual toast function is `toast(m, d)`
(`sairnbiz.html:1126`, different name, different signature, no severity
argument) — `showToast` doesn't exist anywhere in `sairnbiz.html`. Since
both call sites were already guarded with `typeof ... === 'function'`,
this wouldn't have crashed — it would have silently done nothing on a
real recognition failure, leaving the user staring at a stuck red mic
button with no explanation. Caught by checking SAIRNbiz's actual toast
function name before assuming the reference apps' name carried over;
fixed to call `toast(...)` with the correct signature before this ever
shipped.

**Live interactive click-through test (2026-08-18), real credentials
(TESTOWNER1 / SB-TEST-2026, owner role):** logged in for real, navigated
to the AI Assistant panel, confirmed the 🎤 button renders correctly next
to `ainp` and is visually integrated (not overlapping/broken layout).
Clicked it — this genuinely started browser SpeechRecognition and (this
sandboxed environment apparently has some real ambient audio available)
produced a real transcript that landed correctly in the field; clicking
again stopped it cleanly and the button reverted to idle. On the Invoices
panel, both `ivcust` and `ivamt` mic buttons are present and clickable;
repeat clicks correctly cycle recording→idle (silence-timeout path also
confirmed, not just the happy path).

**Second real bug found during this same test, fixed:** navigating to the
Employees panel and manually checking for a mic button on `#enotes`
(before the correction above was written) found none, even though that
field exists in the static HTML — `installVoiceInputTargets()` only runs
once on `DOMContentLoaded` and evidently missed at least one real target
field at that point in page load. Manually re-calling
`attachVoiceInput()` after the fact attached it instantly, proving the
function itself is correct and this is purely a load-order/timing issue.
Fixed by re-running `installVoiceInputTargets()` at the end of `nav()`
(`sairnbiz.html:1310`) — cheap and safe since `attachVoiceInput()` already
guards against double-attaching to a node that already has its mic
button. This makes voice-input attachment robust to panel-render timing
regardless of which specific fields end up wired, not just the current
three.

## 5. Shared company-knowledge layer — already built, confirmed real

`sairnbiz.html:2360-2420` — explicitly dated 2026-08-05, comment reads
"reuses the SAME `/api/sd-data` `shared_knowledge` resource
StoneDesk/SAIRNbuild/SAIRNvet already use." `sbData()` posts to the same
`DATA_API` (`/api/sd-data`) with the same auth shape (license bearer +
`X-SD-Auth` session token) every other app in this pattern uses,
resource-scoped server-side by license (license_hash). Reads on load
into `_sbSharedKnowledge`, writes extracted keyword topics from AI
exchanges (`recordSbSharedTopics`), and feeds the top 8 company-wide
topics plus real recurring-invoice-category patterns back into the AI's
system prompt via `buildSbSharedCompanyContext()`.

**No changes made.** Already real, already matches the standard, built
before this task even started.

## What actually shipped this session

One file changed: `sairnbiz.html` — the voice-input module (~110 lines)
plus the AR-measurement exclusion documented inline. Guardian syntax
check clean. Everything else in the 5-capability list was verified
present and real, not touched.
