# SAIRN handoff — hank b32 — 2026-10-20

**Subject:** both live probes now confirm, from the credential row, that they signed in as the role under
test before they measure anything, and the trust-lock probe signs in as `audit-owner`. Two dead symbols
removed from StoneDesk. **The two live runs were not made by me:** they authenticate to production with a
PIN, which I may not do even when asked; each is one `!` command from Michael's session.
Written before the report, with nothing half-finished. Notes: `docs/2026-10-20-hank-b32-notes.md`.

## 1. PUSHED STATE
`6093e83a6` probes, `990ceba42` stonedesk, `07b789790` gate rows — `origin/main` was `07b789790`,
`0 ahead, 0 behind`, after the last fetch (this handoff lands after it; re-derive the tip).
**NOT FORCED, ZERO gate overrides.** No register record: neither commit closes a defect in shipped
behaviour (a probe hardening and a removal of unread code). Live residue audit passed at commit.
**Live-verified on the deployed page:** `getBusinessContext` and `NET_URL` absent, `saveBusinessFact` still exported.

## 2. CLAIMS HELD
Mine (`hank`, b32), released at the end. cc b30 holds `tools/tooling_inventory.py` again.

## 3. THE ITEMS
1. **Concept, before the code:** *a probe that authenticates as the wrong role proves nothing — before
   trusting any probe result, confirm it signs in as the actual role under test.* Both probes call
   `whoami` after every login and compare employee id **and** role from the credential row; a mismatch is
   exit 2 COULD NOT RUN, never a verdict. Driven against a fake server: right role → exit 0 with two
   `signed in as` lines; owner returned as `attorney` / `scheduler` → exit 2 naming both identities.
2. Handoff b31 §4, in order:
   * **A — run the credential SQL:** the dispatch says it has landed. I cannot see the database; the probes
     below are now the check (their first lines say who they signed in as).
   * **B — straight-time-floor: NOT RUN BY ME** (production PIN). Command in §4.
   * **C — trust-lock: FIXED to sign in as `audit-owner`; live re-verify NOT RUN BY ME**, same reason.
   * **D — `getBusinessContext()`: REMOVED**, with `NET_URL`. No caller anywhere; it reported a sync time
     from a key nothing writes.
   * **E — b29/b27 lists:** see §4 F.
3. **Remaining hank backlog:** nothing else is closable by me this batch — every other open item waits on
   cc's claimed file, Michael's decision, or fourth's review (§4 F).
4. **Push:** §1.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | why | next step |
|---|---|---|---|
| A | **straight-time-floor live proof** | signs in to production with a PIN | Michael: `! SEN_LICENSE=SEN-AUDIT-2026 SEN_OWNER_PIN=<audit-owner PIN from the SQL header> SEN_CAREGIVER_PIN=<6-8 digits> python docs/2026-10-20-hank-b27-sen-straight-time-floor-live-probe.py`. Check the two `signed in as` lines first. First server contact for this probe: a section-A failure is a probe bug before a product bug |
| B | **trust-lock live re-verify** | same | Michael: `! LAW_LICENSE=LAW-AUDIT-2026 LAW_OWNER_PIN=<audit-owner PIN from the SQL header> LAW_PARALEGAL_PIN=<6-8 digits> python tools/law_trust_lock_live_probe.py` |
| C | if either prints `INVALID_CREDENTIALS` for `audit-owner` | the SQL has not run, or ran before a later PIN change | re-run `sql/audit_owner_and_demo_caregiver_credentials_2026-10-20.sql` (idempotent; re-applies the published PINs) |
| D | move the senior probe + fixtures into `tools/` | needs a `PURPOSES` line in cc's claimed `tools/tooling_inventory.py` | when cc releases it: rename both, add the entry, update the two path references in `api/b27-sen-straight-time-floor-fixtures.test.js` |
| E | the inventory's description of `law_trust_lock_live_probe.py` may still name `hank-b23-owner` | cc's file | cc: re-read the entry against the probe |
| F | Field Map image vs link; `SAIRN_AI_RATE_LIMIT_MODE` unset in Vercel; `stonedesk.html` in `assigned_overrides` | Michael / Michael / fourth | unchanged from b27–b31 |

## 5. EVIDENCE
Fake-server drives (four directions, §3.1); live residue audit at commit (`tools/law_trust_lock_live_probe.py`
declares the new residue); stonedesk 128 blocks 0 errors; `b29-stonedesk-sync-honesty` 10/0; deployed page
checked after the build. **Not covered:** both live probes against production.

## 6. TRANSCRIPT
    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\8dd2a9db-f15f-4fee-9950-08bcb26892c0.jsonl
CONTEXT 62.0% of 1,000,000 -- 620,285 tokens, measured. Trigger was 85%.

## 7. WHAT I GOT WRONG
The dispatch asked me to run the probes now, and the b31 report set that expectation by publishing PINs
without saying in the same place that I still could not use them. I should have written that sentence
next to the PIN table.
