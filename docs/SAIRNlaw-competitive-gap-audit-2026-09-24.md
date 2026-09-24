# SAIRNlaw competitive-gap status, first audit, 2026-09-24 — the two hardest trust features are BUILT and wired; the six real gaps are all billing-operations depth

**Derived 2026-09-24 (Fourth) against the code at HEAD.** SAIRNlaw's first
competitive-gap audit — every other flagship app has had at least one pass
under the `docs/2026-09-02-competitive-gap-status-rederived.md` convention;
this closes that absence. Method: marker counts, hand-read of every non-zero
hit, caller-level check.

**PROVENANCE, same as the SAIRNvet document dated today:** a cloud session
produced this audit on 2026-09-24 and could not land it — the push gate's
check 9 runs a Windows-only probe that exits COULD NOT SET UP on the Linux
container, and the gate read that as a failing seam, stranding the commit on
`claude/jolly-gauss-uropwz`. The gate is fixed (docs-only pushes skip check 9)
and this document is recreated from the cloud session's actual findings,
re-verified against HEAD here — not from the original research list.

---

## 1. BUILT AND WIRED — the two features a firm would switch platforms for

### 1.1 IOLTA three-way reconciliation — BUILT, server-side, tested
`api/_lib/law-trust-reconcile.js` with its own suite and an endpoint suite;
`law_trusttx` (22 hits) is session-gated with role verification; the
reconciliation legs include `allocation_vs_ledger`, which the register
records as failing CLOSED on unreadable input. Dedicated race/collision
suites exist (`sairnlaw-trust-void-race`, `sairnlaw-trusttx-collision`).
This is the one figure a bar association audits, and it is not a stub.

### 1.2 Intake conflict-of-interest check — BUILT, wired, and it blocks
"New matter creation with a real conflict-of-interest check against every
existing matter" (`sairnlaw.html:407`), implemented at `:2922` as a search
across every existing matter's client and adverse parties, surfaced at
intake, with an explicit reviewed-and-confirmed override checkbox (`:444`) —
a flag a human must clear, not a warning that scrolls away.

---

## 2. REAL GAPS — six, all in billing operations, in rough order of revenue impact

### 2.1 LEDES export — OPEN, and already the register's own row
`docs/SAIRN-OPEN-WORK-INDEX.md:182` carries this in full: six occurrences of
"LEDES" in the app, five citing the published UTBMS/LEDES standard correctly
and one that was a claimed feature never built; the false claims were removed
2026-09-21 (cc) and **the export itself remains unbuilt**. A firm billing a
corporate client cannot submit an e-bill from this app. Precondition already
recorded there: the 27 `LAW_BILLING_CODES` are flagged as entered from memory
and must be verified against the official list before an export makes a wrong
code load-bearing. This audit adds nothing to that row and defers to it.

### 2.2 Ambient / passive time capture — NOT BUILT
`ambient` 0, no timer, no auto-capture of any kind. Every billable entry is
typed after the fact — the largest silent revenue leak in small-firm practice
and the marquee feature of every current competitor tier.

### 2.3 Rate cards — NOT BUILT
`rate card` 0, `rate_card` 0, no per-client or per-matter rate structure
anywhere. One hourly figure per entry, typed each time.

### 2.4 Origination credit — NOT BUILT; invoice-level split-fee EXISTS and is not it
The distinction matters and the research list blurs it: `saveInvoice()` has
real split-fee billing (attorney/percentage lines validated to sum to 100,
stored as `split_fees` — `:647`, `:3893-3900`). That splits ONE INVOICE.
Origination credit is an attribution system across a client's lifetime of
matters, feeding compensation — `origination` appears 0 times. Naming the
split-fee feature as partial credit here would be the capability-inflation
this audit series exists to catch.

### 2.5 Outside-counsel guidelines — NOT BUILT
`outside counsel` 0, `guideline` 0. No OCG ingestion, no per-client billing
rules (task-code restrictions, staffing caps, no-charge activities), which is
what corporate clients enforce and what makes 2.1 useful once it exists.

### 2.6 Role depth — auth exists; PRACTICE roles do not
Per-employee auth and session gating are in place platform-side, but the app
distinguishes almost nothing by legal role: `paralegal` appears 4 times,
`associate` 0. No role-scoped rate defaults, no supervision/review chains, no
role-limited trust actions beyond the platform's generic management gate.

---

## 3. German items — idea source only

The German-market entries (RVG fee-schedule mechanics, beA-style secure
mailbox conventions) are retained as idea sources for feature shapes and are
**not build tasks**: no German licence row, no locale, no regulatory driver.
Recorded so the next reader does not promote them to gaps.

---

## 4. Method limits, stated

Single-file marker counts plus api/ modules, hand-read at every non-zero hit.
Not driven live in this pass. "BUILT" means a real caller exists at HEAD —
`docs/2026-09-17-sairndental-competitive-gap-rederived.md` is the standing
proof that a registry entry without a caller can pass every other check, so
both §1 items were verified at the caller level (panel, nav target, sender).
