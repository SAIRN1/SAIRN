# StoneDesk innerHTML audit — findings, and what was closed

**Date:** 2026-09-01 · **Session:** CC
**Status:** attribute sweep, renderer escaping and the event-handler sweep all
DONE and live-verified. The markdown call sites are repointed; see why that
changes nothing yet.

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

## Closed: 115 interpolations inside on*= event-handler attributes

`escHtml` is the wrong tool here, and saying so was the point of listing this
class separately. The browser decodes HTML entities in an attribute **before**
the JS parser runs, so `&#39;` becomes a real quote and closes the JS string
exactly as an unescaped one would.

Two helpers now sit beside `escHtml`: `jsStr` (JS-string-literal escaping) and
`escAttrJs = escHtml(jsStr(v))`. **The order is load-bearing** — `jsStr` first,
`escHtml` second — and reversing it produces source that *looks* escaped and
is not. Backslash before quote inside `jsStr`, for the same class of reason.

The 115 decompose as:

| count | shape | fix |
|---|---|---|
| 76 | interpolated into a **quoted** JS string argument | wrapped in `escAttrJs` |
| 23 | emitted as a **bare JS token** | **quoted and** escaped |
| 5 | carrying the wrong escaper | hand-fixed |
| 28 | loop index, boolean, or a pre-validated identifier | left bare, on purpose |

### The 23 bare-token sites were a live bug, not a latent one

Every id in this file is `'C' + Date.now()` — a string beginning with a letter.
So `onclick="custOpenDetail(' + c.id + ')"` emitted

    custOpenDetail(C1788268235253)

and the handler threw `ReferenceError`. **Proven in the browser on the deployed
build before touching it**: rendered a probe customer, read the emitted
attribute, evaluated it. Customer cards, vendor discount save, override remove,
comms pin/reply/delete, safety training delete, nesting load and finance job
delete were all dead controls. Every callee compares with `===` against a `.id`
or uses it as an object key, so a quoted string is what they always wanted.
`escAttrJs` alone could not have fixed these — a bare token needs no quote
character to break out of.

### And quoting broke one thing, which is why each site needed checking

**Quote history is the only numeric-id data set in the file** (seed rows
`id:1..8`, new rows `id:Date.now()`). `sdHistoryView('1')` met `q.id === id` as
`1 === '1'`, found nothing, and the View button went dead — the exact shape the
sweep was removing, reintroduced by the sweep. Caught by reading the emitted
attribute on the live page. Fixed by making the three quote-history lookups
`String()===String()` rather than by dropping the quote: the quote is what
closes the injection. Every other callee's id generator was read to check for
the same hazard; all string.

**Live-verified after deploy:** 35 such controls rendered, **35 with a quoted
first argument, 0 bare**; `custOpenDetail` clicked with a normal id opens the
detail with no error; clicked with `z'); window.__H1=1; ('` it does **not**
execute, resolves the payload as data, and raises no parse error;
`sdHistoryView('1')` populates the detail again.

## The markdown repoint, and why it changes nothing yet

The four AI-chat-area call sites now name `renderMarkdownRich`. Verifying that
on the live page showed **all four are unreachable**:

- the three streaming sites live inside `installStreamingHook()`, which has
  exactly one occurrence in the file — its own definition. Nothing calls it.
  `window.sendMessage` is assigned four times over and the live one references
  no markdown renderer at all.
- the `addMsg` interception is guarded on `typeof window.addMsg === 'function'`,
  false on the live page, so `installMarkdownHook()` bails and its polling retry
  never fires.

Markdown in the AI chat still goes through `formatMessage()`, which now escapes.
The rich renderer is verified safe and full-featured for whenever the hooks are
switched on: against a hostile fixture it renders `h1`, `table`, `ul`,
`blockquote`, `pre`, `code` and a safe link, creates **no** `img` or `script`
node, refuses a `javascript:` href, and shows the payload as text.

**Before anyone switches those hooks on:** the rich renderer hardcodes `#F0F0FF`
for headings and bold and `rgba(240,240,255,0.8)` for list text — written for a
dark surface. `.msg-bubble` is `background:#FFFFFF; color:#1A1410`. Wiring it as
written paints near-white text on white. Move its colours to theme variables
first. That is a design change, not a security one.

## Still open

**~25 sites assign a single variable** (`el.innerHTML = html`) built elsewhere.
The risk is wherever that variable was assembled; each needs following by hand.

**`c.vendorWebsite` in an `href`** is escaped, but escHtml does not stop a
`javascript:` scheme. Not reachable today — the value comes from the in-file
`VENDORS` constant.

**One residual scanner finding is a false positive.** The
`document.getElementById('neg-price-…')` argument in the vendor panel is inside
a JS string opened earlier in the same literal, so the tool's two-character
lookbehind reads it as a bare token. It is already `escAttrJs`-wrapped and
correct.

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
