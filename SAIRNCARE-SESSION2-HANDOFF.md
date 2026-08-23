# SAIRN — SAIRNCARE Session 2 Handoff (Cody)

Written 2026-08-23 at end of session. Every claim below was verified against
`git log` and the live deployment during this session, not recalled from memory.

---

## 0. READ THIS FIRST — a correction to the handoff request itself

This handoff was requested with the instruction to state that *"none of the four
Phase 0 items are built or decided — still waiting on Michael's direction"*, and
that the alf_facility client/registry/migration work is *"staged"* and should be
left untouched.

**Both of those are factually wrong as of this commit, and writing them down
would have been actively harmful** — it would tell the next session to rebuild
work that is already live in production on a healthcare app. Verified reality:

- **All five Phase 0 items are BUILT, pushed, and live-verified** (`a0edb17`).
- **Phases 1, 2 and 3 were also completed** after Phase 0 (`f29e5f9`, `d2c3a58`,
  `4ba885d`, `e496aca`).
- **The alf_facility work is not staged.** It was committed as `6336eb1`, and
  CC's own follow-up note `ca5b658` already corrected the record to say so
  ("Cody already committed it"). **The working tree is completely clean.**

The likely cause is that the request was framed from an early point in the
session, before Phase 0 shipped. Recording it here rather than silently
complying, because a handoff that understates completed state is the most
expensive kind of wrong document on this platform.

---

## 1. Verified current state

**Working tree: CLEAN.** `git status --short` returns nothing. Nothing staged,
nothing uncommitted, nothing half-finished.

**HEAD:** `1b48fc3` (merge), containing `d0655cf` as the last real work commit.
Everything below is pushed to `origin/main`.

### Commits this session, in order

| SHA | What |
|---|---|
| `6336eb1` | alf_facility facility profile + licensing jurisdiction (client + registry + migration) |
| `a0edb17` | **Phase 0** — care_level_history, ccrc_contract_type, alf_signals, invoice retroactivity fix |
| `f29e5f9` | **Phase 1** — payer/billing-routing engine (HCBS waiver + hospice/MA relatedness) |
| `d2c3a58` | **Phase 2** — compliance-rules engine (OH/IN/MI/PA) + staff credentialing |
| `4ba885d` | **Phase 3 items 1–4** — pharmacy eMAR, doc→charges, AI care plans, late-care alerting |
| `c955839` | Fix: alert cron returned 405 on every firing (Vercel crons issue GET, not POST) |
| `e496aca` | **Phase 3 item 5** — operational-audit layer |
| `bba1617` | Combined migration file (the 10 unrun migrations, one paste) |
| `e63e4b1` | Verification license seed (ALF-TEST-2026) |
| `d0655cf` | Six fixes from the visual review |

### Files
- `sairncare.html` — all phases + visual-review fixes. Committed, clean.
- `api/sd-data.js` — handler branches for every alf_ resource. Committed, clean.
- `api/_lib/{payer-routing,compliance-rules,med-schedule,care-charges,op-audit}.js` — pure engines.
- `api/{alf-pharmacy,alf-alerts}.js` — pharmacy intake + alerting endpoints.
- `api/_resources/sairncare.js` — 13 registered resources.
- `sql/sairncare_*.sql` + 2 seed JSONs.
- `tests/sairncare/*.js` — 18 suites, **327/327 passing**.

---

## 2. Phase 0 — the four design proposals AND what shipped for each

Recorded in full because the original design reasoning is still the best
explanation of *why* each is shaped the way it is. **All are built.**

### (1) Level-of-care mutability with history
**Design finding:** `care_level` was a flat jsonb string with exactly three
values (al1/al2/al3), set from one dropdown, overwritten in place, no history,
no transition record, and no independent-living / memory-care / skilled-nursing
values at all — so on-campus movement could not be represented. It also had a
live billing consequence: `generateInvoice()` read `careRateFor(r.care_level)` —
the *current* level — for a whole month, so a mid-month level change silently
re-billed the entire month at the new rate, and the stable-id upsert
(`INV-<resident>-<month>`) corrected the same row in place, leaving no trace of
the prior figure.

**Shipped:** `care_level_history` array on alf_clients; entries are
`{level, sub_tier, effective_date, changed_by, changed_at}` where level is
`independent_living | assisted_living | memory_care | skilled_nursing` and
`sub_tier` (al1/al2/al3) is meaningful only for assisted_living. **Management-only
write**, enforced server-side even against nursing's usual broad-edit authority.
**Append-only**, enforced by checking the incoming array is an unmodified prefix
of what is stored. `changed_by`/`changed_at` server-stamped (a test forges both
and asserts they are discarded). Legacy flat values migrate losslessly on read
with an honest `effective_date: null` rather than a fabricated date. `care_level`
remains as a derived flat field computed server-side from the last entry.

### (2) Facility state / jurisdiction as first-class
**Design finding:** no first-class attribute existed — only two disconnected
free-text stand-ins (a free-text incident deadline, and a 2-char HCBS field
reachable only when the Medicaid toggle was on), both living in `alf_facility`
which was **localStorage-only and never server-synced**, making a licensed
entity's legal fact device-local.

**Shipped:** `licensing_state` on a server-synced `alf_facility`, validated
server-side against the real 50-state + DC USPS list, normalised to uppercase,
non-empty invalid codes refused outright (empty allowed — not-yet-filled-in is a
real state). Keyed by `(license_hash, facility_id)` because a CCRC campus holds
more than one licence. Rate card redacted server-side for non-management, while
the non-financial half stays visible facility-wide.

### (3) CCRC contract type
**Design finding:** did not exist — zero matches for ccrc/lifecare/
fee-for-service/contract_type anywhere in the file.

**Shipped:** `ccrc_contract_type` on the resident record —
`not_ccrc` (default) | `lifecare` | `fee_for_service` | `modified` | `equity`,
validated server-side, invalid values refused (400) rather than stored.
**Disclosed judgment call:** no dedicated write gate was added; it follows the
same tier as other resident fields, unlike (1)'s management-only gate.

### (4) Passive monitoring
**Design finding:** no data model at all — zero matches for
fall_signal/motion/monitoring.

**Shipped:** `alf_signals`, a new append-only table
(`fall_detection | bed_exit | wandering_alert | activity_baseline`),
**deliberately with no `risk_score` column and no derived indicator of any
kind**, because no monitoring device or integration exists yet and inventing a
score from zero data is exactly the fabricated-KPI pattern. Reads return a real
`{have, need}` coverage contract computed live from actual rows. Write is
management-only for now (no real producer exists yet to justify wider access).
**No UI panel was built**, deliberately — a hand-entered "passive signal" would
misrepresent the feature, and an empty panel would be dormant code.

### (5) The invoice retroactivity bug — folded in as instructed
`careLevelSegmentsForMonth()` now walks every real day of the month, resolves
which history entry was in effect that day, and prorates per segment.
**Live-proven in production:** a resident on AL1 for 14 days then Memory Care for
17 billed **$4,916** — neither the AL1 rate ($3,600) nor Memory Care ($6,000),
but the correct day-weighted blend. `revision_history` + `care_level_breakdown`
on the invoice, surfaced through an Invoice Details view, so "no trace of the
prior figure" is genuinely fixed.

---

## 3. The single most important finding of the session

**Every "live-verified" claim made before 2026-08-23 was about deployment and
routing, never persistence — and 10 of 11 SAIRNcare tables did not exist.**

In `api/sd-data.js`, the resource-allowlist check is at **line 184**;
`INVALID_LICENSE` is at **line 226**. Probing with a bogus key returns
`INVALID_LICENSE` ~40 lines *before* any database call. It proves the resource
name is registered and nothing else.

There is **no generic fallback store**: every handler targets a literal
same-named table, with zero `bridge_data` references in `sd-data.js` and zero
`alf_` references in `bridge.js`. So until the migrations ran, resident records,
MAR and billing lived in one browser's localStorage and nowhere else. The app
degraded *honestly* about it (reads `provisioned:false`, writes 503
`NOT_PROVISIONED`, all 21 client write paths saying "saved on this device only")
— which is why this was a fixable gap and not a silent data-loss incident.

**Now resolved.** All 14 tables exist. A real write-then-independent-read test
passed: a record written in one request was returned in a separate request under
a freshly-issued token.

**Standing correction, adopted platform-wide:** say *"deployment verified"* for
reaching an endpoint with correct routing/gating; reserve *"live-verified"* for a
real write confirmed by an independent read. Flagged for the Guardian-lessons
update as **lesson seven**.

---

## 4. Credentials — on the record so they are not lost again

- **License:** `ALF-TEST-2026`
- **Owner:** `cody-verify` / PIN `472913`
- **Also created:** `cody-nursing`, `cody-med_aide`, `cody-billing` — same PIN

Login verified independently of bootstrap; a wrong PIN correctly returns
`INVALID_CREDENTIALS`, confirming the hash is real.

**Test data now lives in ALF-TEST-2026** (one resident, a medication order, an
administration, an ADL assessment, an activity, an op-audit record, OH+MI rules).
Fine to leave on a test licence — same call already made for LAW-TEST-2026.

---

## 5. Open items for the next session

1. **Scheduled alert email does not deliver.** In-app alerting works; the cron
   returns 503 `EMAIL_NOT_CONFIGURED`. The dental cron fails identically
   ("RESEND_API_KEY / RESEND_FROM_ADDRESS not fully set"). Supabase clearly
   works, so it is specifically the Resend vars not reaching Production.
   **Michael action item, not a code fix** — check they were saved to the
   Production environment and that a redeploy happened after.
2. **PA Personal Care Home (55 Pa. Code Ch. 2600) not seeded.** Deliberately —
   never verified against primary source. A PCH facility gets an honest
   `NO_RULE_FOR_CLASS` rather than ALR numbers silently applied. Still open.
3. **IN / MI / PA HCBS billing codes not seeded** — only OH and IN(payer) were
   verifiable. Coverage reports `{have:2, need:4}` and routing fails closed.
4. **`ALF_PHARMACY_SECRET` is set**, so the pharmacy endpoint is live; no real
   pharmacy integration is connected to it yet.
5. **Visual review is complete** (13 panels). All six findings found were fixed
   and pushed in `d0655cf`.

### Environment gotchas that cost real time
- **This repo has MIXED line endings.** `api/sd-data.js` is stored **CRLF** in
  the blob; `sairncare.html` is stored **LF**. `sed -i` on `sd-data.js` stripped
  CRLF file-wide and produced a 4011/3895 whole-file diff instead of a one-line
  change. **Check a file's own HEAD blob before any scripted edit, and never use
  `sed -i` on a shared file here.** Always check diff *shape* before committing.
- **Python on Windows defaults to cp1252.** A helper using `open(...,'w')`
  corrupted an em-dash into mojibake in the database. Always pass
  `encoding='utf-8'` explicitly. The app itself handles UTF-8 correctly — this
  was purely a seeding-script bug.
- **A backgrounded Chrome tab suspends both painting and network completion.**
  Screenshots time out and `fetch` hangs forever while JS still evaluates. This
  masqueraded as an app defect ("Load Rules doesn't fire") until a bare `fetch`
  reproduced it and it resolved the instant the tab became visible. Check
  `document.visibilityState` before diagnosing anything as an app bug.

---

## 6. Standard verification reminder

Re-verify `origin/main` HEAD, re-run `tests/sairncare/*.js` (expect 327/327), and
re-check the live endpoints before trusting any claim in this document —
including this one. Section 0 exists precisely because a confidently-stated but
stale claim about project state nearly got written into the permanent record.
