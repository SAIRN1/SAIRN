---
name: sairn-visual-review
description: 'The missing layer — Guardian checks source code, adversarial-reviewer hunts logic bugs, neither actually LOOKS at the rendered app. This uses Playwright (already the standing functional-verification tool per project rules) to screenshot every panel, then reviews each image directly against a concrete checklist: color/contrast, brand consistency, interactive affordances (dropdowns, tooltips, hover/disabled states), empty-state handling, and actual click-through of every control. Trigger before calling any app "done," "world-class," or "polished."'
---

# SAIRN Visual Review

Everything else checks whether the code is correct. This checks whether a real person looking at the real screen would trust it, understand it, and enjoy using it. Different question, different method — this one requires actually seeing it, not reading it.

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
