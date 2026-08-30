---
name: sairn-visual-review
description: 'The missing layer — Guardian checks source code, adversarial-reviewer hunts logic bugs, neither actually LOOKS at the rendered app. This uses Playwright (already the standing functional-verification tool per project rules) to screenshot every panel, then reviews each image directly against a concrete checklist: color/contrast, brand consistency, interactive affordances (dropdowns, tooltips, hover/disabled states), empty-state handling, and actual click-through of every control. Trigger before calling any app "done," "world-class," or "polished."'
---

# SAIRN Visual Review

Everything else checks whether the code is correct. This checks whether a real person looking at the real screen would trust it, understand it, and enjoy using it. Different question, different method — this one requires actually seeing it, not reading it.

## Advanced Checks (added 2026-07-27)

**Outcome verification, not just appearance.** After clicking anything, confirm an OBSERVABLE change actually matches the stated intent — not just "didn't crash." This is the visual-layer version of tonight's `invDelete` bug: the button said "Delete," a confirm dialog appeared, but the item never actually left the list. A visual check that specifically asks "did the list actually shrink/change after this click, not just did the page stay alive" would have caught this before the code-level trace did.

**Real WCAG contrast ratios, not subjective judgment.** Compute actual contrast ratio (foreground vs. background) for text — 4.5:1 minimum for normal text, 3:1 for large text (18pt+) and UI components, per WCAG AA. "Looks readable to me" isn't a defensible standard for something called world-class; a number is.

**Screenshot-diff baseline.** Save each pass's screenshots as the new baseline. On the next visual-review pass, diff against the prior baseline — flag any panel whose appearance changed unexpectedly, even if that panel wasn't the one being worked on. Catches silent regressions from unrelated fixes, same spirit as `checkblocks.py`/`div_balance_check.py` for code.

**Loading-state / layout-shift check.** Does content flash, jump, or reflow while data loads? A KPI tile popping in after the page settles, shifting everything below it, reads as broken even if the final state is correct.

**Static severity-color mismatch (added 2026-07-29).** A KPI can be correctly computed and still visually lie: SAIRNbiz's Net Margin showed -40% in the same static green used for positive metrics, because the color class was hardcoded rather than conditional on the value. Check whether a metric's color/badge actually reflects good-vs-bad based on its real current value, or whether it's a fixed style that happens to look fine regardless of what number is shown. A severely negative metric reading as visually "fine" is a distinct, real finding — not a fabrication bug, a UI-honesty bug.

## Method

1. Launch the app via Playwright (already established for functional verification).
2. Navigate to every panel/screen systematically — not a sample, all of them, same coverage discipline as everything else this project holds to.
3. Screenshot each one at a real viewport size (both desktop and mobile widths, given tonight's mobile POS work).
4. Review each screenshot directly (vision, not code) against the checklist below.
5. **Run the rendered-DOM assertion below on each panel** before moving on — it catches what the eye reliably misses.
6. For anything interactive: actually click it, actually open the dropdown, actually hover the tooltip — confirm it does what it visually implies, not just that it looks right sitting still.

## Rendered-DOM Assertion: literal markup on screen (added 2026-08-30)

**Why this is here and not in a static scanner.** A 2026-08-30 platform sweep for
raw-HTML exposure ran six static checks across all 19 apps and came back clean,
but every one of them reads **string literals** — so markup whose tags arrive
through a variable is invisible to all of them:

    var tag = cond ? '<div>' : '<span>';
    el.innerHTML = tag + content + '</div>';

That blind spot cannot be closed by reading source, only by reading **output**.
This pass is already in the browser, already past the PIN gate, already on every
panel — so it is the cheapest place in the whole toolchain to close it, and no
new tool has to be built or kept in sync.

**Why an assertion and not the screenshot review.** Step 4 looks at these panels
by eye, and a literal `<div>` sitting in a paragraph of body text is exactly the
kind of thing eyes slide over — it reads as a typo, or as part of the content.
It is trivial to assert against the DOM and unreliable to catch visually. The
same is not true of the colour and layout checks, which is why those stay
visual.

Run in the page once each panel is visible:

```js
(() => {
  const TAG = /<\/?\s*(div|span|p|a|b|i|strong|em|ul|ol|li|table|thead|tbody|tr|td|th|h[1-6]|img|button|input|select|option|label|section|br)\b/i;
  // <code>/<pre>/<textarea> legitimately display markup AS text. Without this
  // the assertion cries wolf on any panel showing a snippet, and a checker that
  // over-reports gets ignored.
  const SKIP = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'CODE', 'PRE']);
  const hits = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    const el = n.parentElement;
    if (!el || SKIP.has(el.tagName)) continue;
    if (!TAG.test(n.nodeValue || '')) continue;
    // Only what a customer can actually SEE. StoneDesk carries a block of
    // display:none placeholder stubs; a hit inside one is not a defect.
    const visible = el.offsetParent !== null || getComputedStyle(el).position === 'fixed';
    if (!visible) continue;
    hits.push({
      where: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
             (el.className && typeof el.className === 'string' ? '.' + el.className.split(/\s+/)[0] : ''),
      text: (n.nodeValue || '').trim().slice(0, 140)
    });
  }
  return hits;
})()
```

**Expected result is `[]`.** Any entry is a real finding: markup that reached the
screen as text. Report it with the `where` selector and the offending text, same
standard as everything else here.

**Proven against a true positive before being written down**, because a checker
that has only ever returned clean is unproven, not proven — which is exactly the
criticism levelled at the static sweep this replaces. Run live on
`sairn.vercel.app/stonedesk` 2026-08-30:

| Probe | Expected | Result |
|---|---|---|
| Baseline, untouched page | `[]` | `[]` |
| Visible `<p>` whose tag was built by `['<','div',' class="x">'].join('')` | caught | **caught** |
| Same string inside `<code>` | ignored | **ignored** |
| Same string inside a `display:none` div | ignored | **ignored** |
| After probes removed | `[]` | `[]` |

The true-positive probe assembles its tag from an array join **on purpose** —
that is precisely the dynamic construction every literal-reading static scanner
is blind to, so the probe demonstrates the blind spot being closed rather than
just that the regex matches.

**Record it as a finding, do not throw.** The assertion returns hits rather than
raising, so one bad panel does not abort the sweep before the remaining panels
are covered.

**Honest limit, and it is the same one this whole skill has:** it only sees
panels the pass actually visits, in the states it actually puts them in. It
closes the static blind spot for exercised paths, not for the app.

## The Checklist, Per Panel

**Color and contrast**
- Text actually readable against its background — not just "not literally illegible," genuinely comfortable to read
- Matches the app's assigned brand color consistently (cross-check against `sairn-guardian-v2`'s App File Map — a panel drifting toward a different app's color, or an inconsistent shade of its own, is a real finding)
- No dark backgrounds (Guardian already checks this at the CSS-value level; this confirms it actually renders light, since a CSS variable can be correct and still render wrong through an override)

**Interactive affordances — does it look like what it is**
- Dropdowns look clickable before you click them (visual cue: chevron, border, cursor change) — not just functional once discovered
- Tooltips exist on anything non-obvious (a field with a non-standard format, an icon-only button, a status badge whose meaning isn't self-evident) and are actually readable when triggered
- Buttons look like buttons, disabled states look disabled, not just unstyled
- Hover states exist and communicate something real (not decorative-only)

**Empty and edge states**
- A panel with zero data shows a real empty state (a message, a call-to-action) — not a blank white box that looks broken
- Long text (a long customer name, a long address) doesn't overflow its container or get cut off illegibly
- Numbers with many digits (a large invoice total) still fit and read clearly

**Actual operation, not just appearance**
- Every dropdown, when clicked, actually opens and shows real options
- Every button, when clicked, actually does the thing it visually implies
- Forms actually submit and show real feedback (success, error, validation) — not a silent void

## Output Format

For each panel: PASS, or a specific finding with what was seen (not "looks off," but "the customer name field overflows its container at 40+ characters, cutting off the last few letters with no ellipsis or wrap"). Screenshots referenced by panel name, not just described from memory.

## Environment Requirement — browser must be visible/focused (added 2026-07-29)

Screenshot capture and viewport resize APIs can silently fail against a
background/unfocused/minimized browser window: `resize_window` may report
success while the OS never actually applies it (mobile viewport testing
showed `clientWidth` stuck at the old value despite a "successful" resize
call), and screenshot capture can time out at the CDP paint layer even
though the page's own JS is fully responsive (`document.title` reads
correctly while `Page.captureScreenshot` hangs). Two distinct failure
modes were seen from the same root cause in one session — that's a real
signal to stop retrying blind, not push through with more attempts.

**Before running any visual-review pass:** confirm the driven browser
window is actually visible and in focus on the screen, not minimized,
occluded, or on an inactive virtual desktop. If screenshot/resize calls
report success but the visible result doesn't match, this is very
likely the cause — ask for the window to be brought to focus rather
than retrying the same call repeatedly.

## Relationship to other skills

This does NOT replace Guardian or adversarial-reviewer — a panel can pass every code-level check and still look bad, and can look beautiful while hiding a fabricated number underneath. Run this as the final layer, after the code-level checks pass, not instead of them. This is specifically the "would a real stone shop owner feel confident using this" check — the one question none of the other skills actually answer, because none of them look at a screen.
