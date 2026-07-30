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

## Environment Requirement (added 2026-07-30)

This skill depends on the browser window actually being the real, focused, on-screen OS window — not just a tab that exists. Confirmed twice in one session (`STONEDESK-SESSION73-HANDOFF.md` §5) that when that precondition is silently false, the screenshot and resize APIs don't error clearly — they either fail opaquely or report success while doing nothing:

**Failure mode 1 — unfocused/wrong window.** The tracked tab had drifted to an unrelated window (in this case, the chat client's own tab, not the app under review). Signature: `window.outerWidth`/`outerHeight` read `0`. Screenshot failed outright (`Script injection timed out`), 4/4 attempts, until the tab was re-created and correctly targeted.

**Failure mode 2 — resize silently no-ops.** Even on a correctly-targeted, confirmed-non-maximized window (`outerWidth` reading a real, plausible value both before and after), `resize_window` reported success but `clientWidth` never moved — stuck at the pre-resize value across two separate attempts, one on a maximized window (a plausible cause) and one on a window already confirmed non-maximized (ruling that explanation out for the second case). Screenshot then failed with a *different*, CDP-level error (`Page.captureScreenshot timed out after 30000ms, renderer may be frozen`) — while a plain JS execution on the same tab succeeded immediately before and after, which rules out a genuinely frozen page and points at something environment-specific in the CDP/extension pairing itself.

**What this means in practice:** don't treat a clean tool-call return as proof the check actually ran. Before trusting any screenshot or resize result, verify `outerWidth`/`outerHeight`/`clientWidth` read real, non-zero, expected values first. If resize doesn't visibly change `clientWidth`, or screenshot fails more than twice with different error signatures, stop and log it as an environment gap rather than retrying indefinitely or silently substituting a different check and presenting it as equivalent coverage — a DOM/computed-style inspection can catch some of the same bugs (contrast math, missing elements) but is not the same check as an actual rendered-pixel review, and the gap should stay visible in whatever this pass reports.

## Method

1. Launch the app via Playwright (already established for functional verification).
2. Navigate to every panel/screen systematically — not a sample, all of them, same coverage discipline as everything else this project holds to.
3. Screenshot each one at a real viewport size (both desktop and mobile widths, given tonight's mobile POS work).
4. Review each screenshot directly (vision, not code) against the checklist below.
5. For anything interactive: actually click it, actually open the dropdown, actually hover the tooltip — confirm it does what it visually implies, not just that it looks right sitting still.

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

## Relationship to other skills

This does NOT replace Guardian or adversarial-reviewer — a panel can pass every code-level check and still look bad, and can look beautiful while hiding a fabricated number underneath. Run this as the final layer, after the code-level checks pass, not instead of them. This is specifically the "would a real stone shop owner feel confident using this" check — the one question none of the other skills actually answer, because none of them look at a screen.
