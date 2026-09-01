# StoneDesk innerHTML audit — the scoped read Layer 2 was waiting on

**Date:** 2026-09-01 · **Session:** CC · **Status:** AUDIT ONLY. Nothing wired.
Michael asked for the audit first and for Layer 2 to stay unwired until he has read it.

## Why this had to be an audit and not a wire

`window.safeHTML` (stonedesk.html ~L2155) is a **value escaper**, not a document
filter. It escapes `/` and strips `on\w+=`, so applying it to a built HTML string
destroys the markup — every closing tag renders as visible text. It is only ever
correct around an untrusted value being interpolated *into* markup, which means
wiring it is a per-interpolation decision, not a per-call-site one. Getting it
wrong in the other direction is not harmless either: double-escaping shows a real
customer as `O&#x27;Brien` on their own invoice.

## What is actually there

    innerHTML assignment sites                                470
      pure string literal, nothing interpolated               175   no exposure
      already escaped (escHtml / safeHTML / subEsc)           144   correct today
      interpolate something unescaped                         151   the working set

`escHtml` (L1766) already exists and is already used at 144 sites. **Layer 2 is
not the missing piece — `escHtml` is the house escaper and the gap is coverage,
not capability.** safeHTML's extra `/` escaping and `on\w+=` stripping are worse
than escHtml for element-text position, not better.

## The sharp half: 40 raw interpolations inside an HTML attribute

Element-text position needs a `<` to do damage. **Attribute position only needs a
`"`** — one quote closes the attribute and the next token is a new attribute, which
is how `onerror=` gets in without the attacker typing a tag at all.

    interpolations landing inside attr="…"                     59
      escaped or provably numeric                              19
      RAW                                                      40

Of those 40, sorted by whether the value can actually be attacker-controlled:

**Verified NOT currently exploitable (reported so nobody re-derives it):**

| Site | Value | Why not |
|---|---|---|
| L20730, L20763, L20772-3 | `m.name`, `e.name` into `<input value="…">` | Equipment/employee names. I expected stored XSS here — they are serialised into `data._machines`/`_employees` and passed to `dbSaveBizData()`. **`dbSaveBizData` is an empty stub** (`if(!currentUser) return;` and nothing else), so this is localStorage-only and self-XSS. Low. |
| L22517 | `c.vendorWebsite` into `href="…"` | Comes from the in-file `VENDORS` constant, not user input. Note the author escaped `c.vendorName` on the same line and not the href — the shape is wrong even though the data is safe, and `escHtml` would not fix a `javascript:` href anyway. |
| L16478/81/83 | `MATERIALS`/`TIERS`/`PROJECTS` fields | In-file constants. |
| L9737, L21211, L22021, L34686 | `s` in `<option value="…">` | Fixed status lists. |
| L13867 | `c.fitReason` | Already hand-escaped with `.replace(/"/g,'&quot;')` — enough for double-quoted attribute context. |

**Plausibly reachable, needs a per-source decision before wiring:**

| Site | Value | Source |
|---|---|---|
| L6604 | `d.customer` into `title="…"` | Customer records, server-backed via `sdData()` — the strongest stored-XSS candidate in the file |
| L3119 | sub-portal photo url into `src="…"` | Server data |
| L27563, L32588, L32739 | `s.photo_base64` into `src="…"` | Server data |
| L9766 | `data.imageUrl` into `src="…"` | API response |
| L34384, L34512, L22680 | `r.depth`, `piMyRates[…]`, `disc` into `value="…"` | User-typed, stored locally |

## The other half: three markdown renderers that do not escape

This is separate from safeHTML and **safeHTML must not be applied here** — it
would destroy the markdown output.

| Function | Line | Escapes input? |
|---|---|---|
| `renderMarkdown` (function-scoped) | 24716 | **Yes** — `escHtml(txt)` first |
| `window.renderMarkdown` | 18696 | **No** — escapes only inside fenced code blocks |
| `formatMessage` | 10162 | **No** |
| `sdMarkdown` | 34112 | **No** |

Two different functions named `renderMarkdown` in one file, one safe and one not.

`formatMessage` renders the **assistant** bubble (the user's own bubble correctly
uses `textContent`). Layer 17 does sanitize Claude responses, but
`saSanitizeResponse` (L2472) strips only `<script>…</script>` and `javascript:`.
It does **not** strip event-handler attributes, so `<img src=x onerror=…>` in a
model response survives Layer 17 and reaches the DOM through all three unescaped
renderers. The fix belongs inside the renderers (escape first, then apply the
markdown replacements — exactly what L24716 already does), not at the call sites.

## Recommendation

1. **Escape the attribute-context sites**, using `escHtml`, not `safeHTML`. Start
   with the six server-backed rows above. ~40 edits, mechanical, low regression risk.
2. **Make the three renderers escape first**, the way L24716 already does. Three
   edits, and it closes the AI-response path that Layer 17 only half covers.
3. **Then decide what Layer 2 is for.** After 1 and 2, `safeHTML` has no remaining
   correct call site that `escHtml` does not already serve better. The honest
   options are to delete it or to redefine it as an alias for `escHtml` — leaving a
   second, subtly different escaper around is how the wrong one gets picked later.

## Method, and what it does not cover

Two scripts, in the session scratchpad: a concatenation-aware RHS extractor that
buckets each assignment, and a direct textual match for the three real shapes of
attribute interpolation (`="' +`, `='" +`, `="${`).

- The attribute-context list is a direct textual match and is reliable.
- The bucket counts are **approximate**. The RHS extractor mis-parsed at least one
  site (L13864) and over-ran the statement; the buckets are a triage aid, not a
  census.
- ~25 sites in the working set assign a single variable (`el.innerHTML = html`)
  built somewhere else. Those are **not resolved here** — the risk is wherever
  `html` was assembled, and each needs following by hand.
- No exploit was written or run. Everything above is reachability of a value into
  a context, not a demonstrated exploit.
