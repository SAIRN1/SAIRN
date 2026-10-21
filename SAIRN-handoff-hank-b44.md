# SAIRN handoff — hank b44 — 2026-10-21

**Subject:** cc b38's gap in my b40 request-photo overlay — make both barriers real and tested, add a keyboard
close. Fixed, pushed, live. Written before the report, nothing half-finished.

## 1. PUSHED STATE
- `2fe89f267` fix(stonedesk) — `stonedesk.html`, `api/stonedesk-public.js`,
  `api/b40-stonedesk-style-profile-request-photos.test.js`.
- `8a02bc03f` register record + Tier A obligation (both cite `2fe89f267`, checked on `origin/main`) +
  regenerated MASTER-PLAN / traceability.
- Both confirmed ancestors of `origin/main`. **NOT FORCED.** This deliverables commit follows.
- **Live:** `https://sairn.vercel.app/stonedesk` (sairn_http, no-cache) carries `PC_PHOTO_RX` (whole-value),
  `aria-modal`, and the Escape handler — code presence. The intake change is in the same deploy; it was not
  driven live (that needs a published shop and a write).

## 2. CLAIMS HELD
None (released at the end of the batch).

## 3. THE ITEM
**Concept, before the fix:** *a photo value is safe only if the WHOLE value is a base64 image data URL — check that
shape where it is stored and where it is rendered, keep escaping as a second independent barrier, and give each
barrier an arm that goes red when only that barrier is removed.*

- **Intake** (`api/stonedesk-public.js`): prefix test → whole-value
  `^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/]+={0,2}$`. Base64 has no quote, `<` or `&`.
- **Overlay** (`stonedesk.html` `pcShowRequestPhotos`): same regex as `PC_PHOTO_RX` (rows stored before b44 were
  prefix-checked); `pcHtml` kept on `src` and `alt`; `role=dialog`, `aria-modal`, focus moves in, **Escape** or
  click closes, focus returns to the opener, listener removed.
- **Tests** (27/0; **16/11 on the pre-b44 source**): C1 quote breakout not rendered · C2 svg+xml/text/html not
  rendered · C3 filter alone (src escaping removed) · C4 escaping alone (filter widened) · C5 hostile slot escaped ·
  C6 non-string values · C7 intake regex == overlay regex · **C8 the intake handler itself, driven** (400
  INVALID_PHOTO, nothing written; a valid photo → 200 and written) · D1–D3 dialog, Escape, other key/click ·
  **M1–M5** apply cc's three mutants + no-keydown + prefix-only intake to the real source and require red.
- Regression: syntax 132/0; b28-photo-cap, stonedesk-public, stonedesk-track, intake_link, public_catalog exit 0.
  **Pre-existing, unchanged at HEAD (not mine):** `tests/intake_form_public_surface.js` 17/1 (live-snapshot arm),
  `tests/stonedesk_exec_msgs_gate.js` 9/4.

**Push:** eight attempts lost ref races (origin moved ~1/min, mostly claim commits, while the >2-min pre-push
gate ran). Each retry rebased, let the post-rewrite hook re-seat the register, re-seated the Tier A
`opened_at_sha` (which that hook does not cover) and amended only the bookkeeping commit. `tools/push_retry.py`
was tried first and stopped: its own `git push` has a 120 s timeout, shorter than the gate.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| T1 | Tier A review of `2fe89f267` on `sd_quote_requests` | cc — attack legitimate uploads the stricter intake might refuse, regex cost on 1.4M chars, the C8 harness |
| P1 | `tools/push_retry.py` push timeout (120 s) < gate runtime | cc (tools/ owner) |
| P2 | post-rewrite hook re-seats the register but not `docs/tier-a-reviews.json` `opened_at_sha` | cc / whoever owns `doc_sha_reseat.py` |
| S2 | other public photo intakes (e.g. SAIRNdental public-book) may be prefix-only | not swept |
| H2/H3/C/B/D | carried | Michael (b43 §3) |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
