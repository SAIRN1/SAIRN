# HANDOFF — fourth / ted, batch b50, 2026-10-21

**READ THIS FILE ONLY.** It is the whole state. **The fix is landed and live.
No force, no gate skip.** Wrapped at a safe point at **~51% real context**.

**THE ONE THING TO READ FIRST: this was NOT an NVDA pass.**
- NVDA is not installed on this machine, and neither is a driver for it
  (guidepup).
- Installing it needs an elevated prompt and changes NVDA settings, so it waits
  for Michael's yes.
- What ran instead:
  - Chromium's accessibility tree (the tree NVDA reads);
  - axe-core 4.10.2, scoped to WCAG 2.0 / 2.1 / 2.2 A and AA;
  - real keyboard events.
- The run used a real keyboard sign-in on DNT-PINNACLE-2026. Every write was
  blocked, and none was attempted.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Scratchpad:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- `a11y_dental.py [base] [out.json]`: the pass. Set `A11Y_LOCAL_HTML` to drive a local tree at the live URL.
- `a11y_before.json`, `a11y_after.json`, `a11y_live_after.json`: the full per-panel results (tree, axe, tab walk).
- `axe_dl/`: the pinned axe-core.

## 1. STATE

| item | sha (origin) | state |
|---|---|---|
| a11y fixes + `tests/sairndental_a11y_pass.js` | `01aaa9988` | live; 10 arms, 8/8 mutants |
| register record | re-seated to `01aaa9988` | landed |
| override, `tests/sairndental_a11y_pass.js` (fourth holds 16) | in the b50 gate commits | landed |
| live after-pass | — | 0 axe nodes on 23/23 panels |

## 2. FINDINGS → FIXES

What NVDA would read, before → after:

| # | finding | before | after |
|---|---|---|---|
| 1 | Panel headings | 0 of 23 panels had a heading, so H-key navigation found nothing | `.ptitle` gets `role=heading` `aria-level=2` at load; 23/23 |
| 2 | Current page | the current sidebar item had no `aria-current`, so it was not announced as current | `nav()` moves `aria-current="page"`, and Dashboard is marked in the markup |
| 3 | Vendor Catalog | 20 quantity boxes were read as a bare "spin button 0" (axe `label`, critical) | each is named "Quantity of &lt;product&gt;" |
| 4 | Complaints QR | an image with no alt (axe `image-alt`, critical), plus a twin canvas | alt names the link it encodes; the canvas is `aria-hidden` |
| 5 | Insurance Capture drop zone | a mouse-only `div` in front of a `display:none` file input, so keyboard users could not add a card photo | `role=button` `tabindex=0` with Enter/Space; live, Tab reaches it and Enter opens the file chooser |

**Confirmed fine:** every one of the 23 panels announces on navigation; the
sign-in screens are labelled; tables have column headers; axe found no
contrast violation.

## 3. NEEDS PRODUCT JUDGMENT (filed, not guessed)

- **J1. No skip link, and focus stays on the sidebar after navigation.** A
  keyboard user tabs through every remaining sidebar item (up to 21) to reach
  the panel's content. The options are to add a skip-to-content link, or to
  move focus to the panel heading on navigation. b37 deliberately chose
  "announce, don't move focus".
- **J2. Generic button names in table rows** ("Compare", "Add", "Remove"):
  - NVDA reads them with row context, and axe does not flag them;
  - naming them per row ("Add Nitrile gloves") is a style choice.
- **J3. A real NVDA run** needs NVDA installed (elevated) and a driver.

## 4. NOT COVERED

- Modals were not opened.
- Only sairndental was passed; the other apps were not.
- The register validator reports a pre-existing problem that is not mine:
  `ce15ddaa6a3c`, a cody b27 record whose commit is not in the repo.

## 5. CLAIMS

`fourth`: released at wrap. No SQL.
