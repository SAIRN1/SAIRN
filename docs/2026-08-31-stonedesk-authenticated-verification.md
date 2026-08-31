# StoneDesk authenticated verification — all three open items closed, and a fourth unreachable feature found

Run against `sairn.vercel.app/stonedesk` in a real browser with a real session
(`SD-AUDIT-2026` / `sd-recovery-admin`, role `admin`), which is what the
`stonedesk_recovery_admin_seed.sql` credential exists for. Michael performed the
login; the PIN was never typed by me.

---

## (a) The three unreachable features — CONFIRMED, not predicted

Previously a prediction from source plus live HTTP. Now measured in the DOM:

| Trigger | exists | parent | parent display | visible |
|---|---|---|---|---|
| `sairn-doc-trigger` | yes | `sairn-intake-actions` | `none` | **false** |
| `sairn-compare-trigger` | yes | `sairn-intake-actions` | `none` | **false** |
| `sairn-cam-trigger` | yes | `sairn-intake-actions` | `none` | **false** |

`#sairn-intake-actions` has `childCount: 3` — exactly the three injected buttons
and nothing else. Document Upload + Analysis, Feature 9 Compare, and the
multi-modal camera path are unreachable. `#chatArea` likewise: `display: none`,
zero children.

## (b) Rendered-DOM assertion — CLOSED, zero findings

Drove all **64** `sbNav()` targets, asserting after each. **63 panels rendered
and were asserted; the 64th (`doc-scan`) is a `.page` not a `.panel`**, so it
plus the other two `.page` views were asserted separately.

**Zero panels contain literal markup as visible text.** 66 surfaces, no hits.

This reconciles the static sweep's disclosed blind spot: the assertion reads
rendered output, so markup built from variables would have been caught. It was
not, because there is none.

## (c) The six fetch fixes — CONFIRMED at the model level

I said earlier the browser tooling exposes URL/method/status but not request
bodies, so the post-injection body could not be observed. **The way around that
was to ask the model instead of reading the request.**

With a real session, prompted to report which injected markers appear in its
system prompt:

- **`RESPONSE STYLE` — PRESENT**, and it quoted the sentence verbatim:
  *"Provide thorough, comprehensive explanations. Include context, examples, and
  reasoning. Cover edge cases. The user wants to fully understand, not just get
  a quick answer."* That is `TONE_PROMPTS.detailed` word for word.
- **`LEARNED USER PREFERENCES` — PRESENT**
- `SESSION MEMORY` — ABSENT, correct: no session summary exists until three AI
  responses have been summarised.
- `SHARED COMPANY KNOWLEDGE` — ABSENT, correct: `buildSharedCompanyContext()`
  returns empty on this licence.

**Before the fix these were discarded.** The injection now reaches the model.
That is the product outcome, not just the mechanism.

## My first (c) test was invalid, and the control is what caught it

The plan was a behavioural A/B: set tone `simple`, ask a question, set tone
`expert`, ask the same question, compare. Results:

| Comparison | Jaccard word overlap |
|---|---|
| simple vs expert (different tone) | 0.455 |
| simple vs expert, second pair | 0.500 |
| **expert vs expert (CONTROL, same tone)** | **0.467** |

Same-tone variation was indistinguishable from cross-tone variation, so the test
could not support any conclusion. **The control existed only to measure
non-determinism, and it is the reason a null result was reported instead of
"the replies differed, so it works."**

**The root cause was my own error, not the app.** I wrote the tone to
`sairn_tone_stonedesk`, a key I invented. The module reads
`TONE_KEY = 'sairn_tone_prefs'`. Both runs therefore executed with the same
default, `detailed` — which is exactly what the model later quoted back.

Two lessons worth separating: a behavioural proxy can be swamped by model
non-determinism and needs a control to be worth anything; and a discriminating
probe (ask the model what it was told) beats an inference from writing style.

## NEW FINDING — the tone selector UI never builds

`buildToneBar()` opens with:

    if (document.getElementById('sairn-tone-bar')) return;

and `<div id="sairn-tone-bar" style="display:none"></div>` is one of the
eighteen placeholder stubs at `stonedesk.html:14496`. The guard sees the stub
and returns. Confirmed live on a fresh load: `display: none`, **0 children**.

**Consequence: a user has no way to change the response style.** `_currentTone`
is initialised as `localStorage.getItem(TONE_KEY) || 'detailed'`, nothing else
ever writes that key, so every request gets `detailed` forever. The feature is
implemented, wired to the proxy, and reaching the model — with a value the
customer can never choose.

This is the **fourth** confirmed unreachable feature and the **twelfth** casualty
of the stub block. It strengthens the case already made in
`docs/2026-08-30-stonedesk-placeholder-stub-audit.md`: renaming those eleven
colliding ids is the cheapest high-value change available, and it now un-hides
four features rather than three.

## Housekeeping

Every localStorage key the testing created (`__cody_turn1`, `__cody_turn2`,
`__cody_tone_backup`, `__cody_tonepref_backup`, `sairn_tone_stonedesk`) was
removed, and `sairn_tone_prefs` was restored to its prior state — absent.
Verified empty afterwards. Three AI calls plus one probe were spent on the
invalid A/B; that cost is on the method, not the app.

## Still open

- **Setting `sairn_tone_prefs` to a non-default value and confirming the model
  quotes that prompt instead.** The tab was closed before this last step; it
  needs a fresh login. Everything else in (c) is settled without it.
- The stub-id rename itself, which remains a decision rather than a task.
