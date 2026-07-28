---
name: sairn-client-facing-design
description: Visual design audit and polish standard for making any SAIRN app look professional and trustworthy to a paying B2B client — not just "on brand." Trigger this whenever a client, investor, or reviewer says an app "looks ugly," "unpolished," "cheap," or critiques colors/layout/typography in general terms; whenever building a new panel or page that a customer will see; and before any live demo or sales walkthrough. Companion to the general frontend-design skill — that one covers building distinctive new designs from scratch; this one covers auditing and fixing an EXISTING app so it reads as professional software a business would pay for, and is tuned specifically to SAIRN's one-brand-color-per-app system.
---

# SAIRN Client-Facing Design Standard

Built after a live reviewer's first reaction to SAIRNcode was "it's ugly, the colors, everything" — a vague critique that, when unpacked, usually has 3-4 concrete, fixable causes. This skill is the checklist for finding and fixing them, not a generic "make it prettier" pass.

## The #1 root cause of "the colors are ugly": one accent color used for EVERYTHING

SAIRN's app registry gives each app exactly one signature color (StoneDesk #16C762, SAIRNcode #F87171, SAIRNvet #7C3AED, etc.). That's correct as a *brand identity* decision — but it is a common, serious mistake to then use that SAME color for the logo, every badge, every button, every highlighted message bubble, and every accent throughout the whole interface. A single hue repeated everywhere with no variation reads as flat, monotonous, and yes — ugly — even though each individual element might be fine on its own. It also means nothing stands out, because everything is shouting the same color at once.

**The fix is a role-based palette, derived FROM the one brand color, not a replacement for it:**

- **Brand color** — used sparingly, for the 1-2 things that should actually draw the eye: the primary call-to-action button, maybe the logo mark. Not the whole logo lockup, not every badge, not every message bubble.
- **Neutrals** (a proper gray scale, not pure black/white) — carry the actual structure: body text, borders, card backgrounds, secondary buttons, most of the UI's real estate. This is usually 80%+ of what's on screen.
- **A darker/deeper shade of the brand color** (not a second unrelated hue) — for text-on-brand-color situations, hover states, or a secondary accent that still feels related to the identity.
- **Semantic colors, separate from the brand color** — success, warning, error states should use conventional green/amber/red regardless of what the brand color is. Do NOT force the brand color to also mean "success" if it happens to already be reddish or greenish — that creates confusing double meanings (is this red button an error, or just... the brand?).

**Concrete audit to run on any app getting this critique:**
```
grep -o "#[0-9A-Fa-f]\{6\}" <app>.html | sort | uniq -c | sort -rn
```
Look at the actual distribution. If one hex value (the brand color) appears dramatically more often than every neutral gray combined, that's the smoking gun — the palette has no hierarchy, it's one color everywhere.

## Second most common cause: no real typographic hierarchy

If every piece of text on a page is close to the same size and weight, the page has no visual hierarchy regardless of color — the eye doesn't know what to read first, which also reads as unpolished. Check:
- Is there a clear, deliberate size/weight jump between a page title, a section header, and body text — or is everything close to 14-16px regular weight?
- Is line-height tight and cramped, or does body text have room to breathe (1.4-1.6 line-height is typical for readable UI text)?
- Are labels/captions actually smaller and more muted than the content they're labeling, or the same size and color as everything else?

## Third: whitespace and density

B2B software that looks "cheap" often has elements crammed edge-to-edge with inconsistent gaps. Professional-feeling software has generous, CONSISTENT padding/margins — pick a spacing scale (e.g. 4/8/12/16/24/32px) and use only those values, not arbitrary ones per element. Inconsistent spacing between visually similar elements (e.g. one card has 12px padding, another has 18px) is subtly perceptible as "off" even when a client can't name why.

## Fourth: does every state get styled, or just the happy path?

A page that looks fine with content in it but shows a raw, unstyled empty state, a spinner-less loading state, or a red browser-default error message will feel unfinished the moment a client happens to hit one of those. Check hover states, disabled states, empty states, and error states specifically — these get skipped far more often than the main content view, and clients DO click around enough to find them.

## How to run this as an actual audit (not just theory)

1. **Get a real screenshot** of the specific page/panel being critiqued — don't guess from memory of what it "should" look like.
2. **Run the hex-color-frequency grep above** — confirms or rules out the #1 cause immediately, with data instead of opinion.
3. **Check the type scale** — list every font-size value used on that page; if there are only 1-2 distinct sizes, that's the hierarchy problem.
4. **Check spacing values** — same idea, list distinct padding/margin values used; more than ~5-6 different arbitrary values on one page usually means no real spacing system exists.
5. **Propose a specific, small token set** (per the frontend-design skill's format: 4-6 named hex values with explicit roles — brand/neutral-dark/neutral-mid/neutral-light/success/error) rather than a vague "redo the colors."
6. **Fix incrementally, one page/panel at a time**, verify it against the usual `node --check` / div-balance / nav-panel triad, and get a fresh screenshot to confirm the actual visual result before moving to the next panel — a described fix and an actually-rendered fix are not the same thing.

## What NOT to do

- Don't replace the app's signature brand color entirely just because a reviewer said "the colors are bad" — the fix is almost always usage/hierarchy, not identity. Changing StoneDesk's green or SAIRNcode's coral would break the established registry (see sairn-platform memory) for no real benefit.
- Don't apply a generic AI-design default palette (warm cream + terracotta, near-black + neon accent, newspaper hairlines) as a reflexive fix — see the frontend-design skill's calibration section. SAIRN's apps already have real brand identities; the fix is disciplined use of them, not a templated restyle.
- Don't fix "it looks ugly" with more decoration (gradients, shadows, extra icons). The far more common actual cause is exactly the opposite: too much of one color and not enough structural variation. Restraint, not addition, is usually the fix.
