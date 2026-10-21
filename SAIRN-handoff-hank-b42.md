# SAIRN handoff — hank b42 — 2026-10-21

**Subject:** (1) Michael-authorised test quote request with a photo on SD-AUDIT-2026 and the Photos (N)
click-through in a real signed-in browser; (2) cc b35 routing — `api/sd-data-scp-licence-only.test.js` B arms and
A3 window. Written before the report, nothing half-finished.

## 1. PUSHED STATE
- `b27df033c` fix(test) — `api/sd-data-scp-licence-only.test.js`.
- `e9a4c7aff` register (2 test-layer records citing `b27df033c`) + regenerated MASTER-PLAN / traceability.
- Both confirmed on `origin/main`. **NOT FORCED.** This deliverables commit follows (with the gate-written
  `docs/scrutiny-flags.json` row).

## 2. CLAIMS HELD
None (released at the end of the batch).

## 3. THE ITEMS
**A. Live Photos (N) — concept:** *create exactly one labelled test request through the real public form, drive
the real server read under a real session, then click the real button in a signed-in browser; whatever cannot be
driven is named, not passed.*
- Test shop `sd-audit-b42-test` published only for the submit and **unpublished immediately after** (verified 200).
- `POST /api/stonedesk-public` quote_request → **200**, `QR-1792602627030-534`, `photos_sent 1, photos_saved 1`.
  Photo: a generated 96×96 PNG, orange with a blue diagonal stripe.
- Session read: `photo_count 1`; `request_photos` → 1 slot, **byte-identical to what was sent**.
- Browser (Chrome, `sairn.vercel.app/stonedesk`, **Michael signed in** as audit-owner — I did not enter the PIN):
  Public Catalog → row "hank b42 live check" shows **Photos (1)**. A click event on that button ran its inline
  `pcShowRequestPhotos('QR-1792602627030-534')`, the overlay opened and the `<img>` loaded **96×96** — screenshot
  shows the orange square with the blue stripe.
- **Honest limit:** the automation's *pointer* clicks landed on `<html>` on this page (the sidebar too), although
  `elementFromPoint` at those coordinates returned the button (devicePixelRatio 1.5). So the event that opened it
  was `button.click()` — real handler, real DOM, not a human pointer. A human click is the one link not driven;
  Michael can confirm it in the open tab in two seconds.
- **Left in place:** the test request (pending, on the audit licence). Not soft-deleted — the Delete button opens a
  `confirm()` dialog the automation must not trigger. Shop row exists unpublished.

**B. scp-licence-only — concept:** *the nine resources are session-gated on purpose, so the disclosure suite
asserts the gate that ships, and A3 reads the declared table, not the first mention of its name.*
- B1 no session → **403 FORBIDDEN** "valid employee session is required"; B2 a signed-in sairnscape owner is
  **not** refused (so B1 is a gate, not refuse-everything); C boundary arms unchanged.
- A3 parses `const SD_SESSION_GATED = { … }` (same anchor as the gate suite) with controls: `invoices` present,
  `sd_customers` absent.
- 33/0 (was 15/9). Mutation controls in a scratch worktree (removed after): `scp_jobs` dropped from the table →
  A3 + B1 scp_jobs **FAIL**; gate refusing every session → all nine B2 **FAIL**. Sibling gate suite 92/0.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| P1 | human pointer click on Photos (1) | Michael, in the open tab (optional — handler, DOM and render already driven) |
| P2 | test request `QR-1792602627030-534` on SD-AUDIT-2026 | Michael: keep as a fixture, or Delete it in the UI (soft delete) |
| S1 | other suites slicing `SD_DATA` by a fixed window from `indexOf(name)` | not swept; same shape as the A3 defect (register recurrence note) |
| T1 | Tier A on `sd_quote_requests` | cc (routed) |
| H2/H3/C/B/D | carried | per `SAIRN-handoff-hank-b38.md` §4 |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
