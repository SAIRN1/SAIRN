# StoneDesk innerHTML audit — findings, and what was closed

**Date:** 2026-09-01 · **Session:** CC
**Status:** attribute sweep and renderer escaping DONE and live-verified. One
class quantified and deliberately NOT fixed (see *Still open*).

`safeHTML` (Layer 2) is **still unwired, and the recommendation is that it stays
that way.** `escHtml` (L1766) is the house escaper, was already used at 144
sites, and is the better tool: safeHTML additionally escapes `/` and strips
`on\w+=`, which mangles element-text output for no gain.

## What was there

    innerHTML assignment sites                     470
      pure string literal                          175   no exposure
      already escaped                              144 -> 154   after this sweep
      interpolating something unescaped            151 -> 141

## Closed: 40 raw interpolations into HTML attributes

Attribute position only needs a `"` to break out; element-text needs a `<`. That
made this the sharp half. All 40 now route through `escHtml`. The two the
scanner still reports are inside the parked renderer's own body — one of two
in-function literal style strings, and a scheme-validated href.

**Live-verified on the deployed page**, against the real `renderMachines()` with
a hostile equipment name (`x" onmouseover="…" y="`):

| assertion | result |
|---|---|
| inputs rendered | 3 |
| injected `onmouseover` attribute | `null` |
| attributes present on the input | exactly `onchange,placeholder,value` |
| input value | the payload, **verbatim** — no double-escaping |

Two sites needed something other than `escHtml`, because escHtml is not a
universal answer:

- **`sairnEmptyState`'s `btnFn`** lands in an `onclick`. That is JS in an
  attribute: the HTML parser decodes entities *before* the JS parser runs, so
  `&#39;` becomes a real quote and still breaks out. It now accepts a bare
  identifier or emits no handler at all. (The function has zero callers. Fixed
  anyway — it was on the list.)
- **`renderMarkdown`'s `[text](url)`** had no scheme check, and escHtml leaves
  `:` alone. Non-`http(s)`/`mailto`/relative URLs now render as text.

## Closed: markdown renderers that did not escape

| Function | Escaped before? | Reachable? | Now |
|---|---|---|---|
| `formatMessage` (assistant chat bubble) | no | **yes** | escapes first |
| `sdMarkdown` (Stone Hub / pricing panels) | no | **yes** | escapes first |
| `renderMarkdown` (top-level, ~L24938) | yes | **yes** | unchanged |
| `renderMarkdownRich` (~L18897, was `window.renderMarkdown`) | no | **no** | escapes first, renamed, parked |

Layer 17 was never cover for this: `saSanitizeResponse` strips `<script>` and
`javascript:` and nothing else, so an `onerror=` in a model response reached the
DOM through the two reachable unescaped renderers.

**Correction to this document's first version.** It listed
`window.renderMarkdown` as an unescaped live path. It was unescaped and it was
**unreachable** — `function renderMarkdown(txt)` is a top-level declaration in a
later script block and overwrites the assignment, so all four call sites have
always resolved to the simpler renderer. Found by running the deployed page:
`window.renderMarkdown('[ok](https://example.com)')` returned its input
unchanged. A node probe that evaluated each renderer in isolation missed it,
because isolation is exactly what erases a name collision. This is the **third**
instance of that shadowing shape in this file, after the `saUnlock` stub and the
two privacy stubs a previous session fixed.

The rich renderer is renamed rather than deleted and its call sites are
deliberately **not** repointed — switching them would start rendering tables,
fenced code and links in the AI panels, which is a visible product change.

Verified by executing the real functions, both from the repo file and from the
file the CDN serves: 25 assertions — no `img`/`script` node survives an
injection fixture in any of the four, the payload shows as text, and
bold/italic/code/headers/lists/blockquote/table/fenced-code/paragraph breaks all
still render. `javascript:` link refused, relative link allowed, apostrophes
round-trip.

## Still open — quantified, not fixed

**115 interpolations land inside an `on*=` event-handler attribute.** This is a
distinct class, roughly 3× the size of the attribute class, and **`escHtml` does
not fix it** for the reason given above. Most carry internally-generated ids
(`'JC'+Date.now()`), which is why it has not bitten. The ones carrying free text
are worth a look first: `u.name` (~L34759), `vk` and `sku` in the vendor panels
(~L22833, ~L23001, imported from CSV). Two sites already hand-escape for JS,
which shows the shape was understood in places and not systematised.

**~25 sites assign a single variable** (`el.innerHTML = html`) built elsewhere.
The risk is wherever that variable was assembled; each needs following by hand.

**`c.vendorWebsite` in an `href`** is escaped now, but escHtml does not stop a
`javascript:` scheme. Not reachable today — the value comes from the in-file
`VENDORS` constant, not user input.

## Method, and what it does not cover

Scripts in the session scratchpad: a concatenation-aware RHS extractor, an
attribute-context matcher that also reports *which* attribute, an event-handler
matcher, and a node harness that extracts and executes the real renderers.

- The attribute and handler lists are direct textual matches and are reliable.
- The bucket counts are approximate — the RHS extractor mis-parses at least one
  site and over-runs the statement. Triage aid, not a census.
- Every "safe" claim about a data source was checked, and two were wrong on the
  first pass: `m.name`/`e.name` looked like stored XSS until `dbSaveBizData`
  turned out to be an empty stub (localStorage-only, self-XSS), and
  `window.renderMarkdown` looked like a live path until the browser said
  otherwise.
- No exploit was written against a third party. The breakout payloads set a
  local flag on a page loaded in this session and nothing else.
