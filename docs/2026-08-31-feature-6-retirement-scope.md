# Retiring Feature 6 (Simplify + Explain) — scoped, not applied

**Not applied: `stonedesk.html` is claimed by CC** (`stonedesk security layers
wiring`, active). The claim tool refuses and says to flag it rather than
override, so this is the scope written up ready to apply — by CC inside his
existing claim, or by me once it clears.

**The headline: retiring it is behaviourally a no-op today**, and that is what
makes it the right first pick of the eight.

---

## The block itself is self-contained

`stonedesk.html` lines **17716–17881** — one `<script>`, 6466 bytes, 165 lines
of JS.

| | |
|---|---|
| Guard flags | `_saircSimplifyInstalled`, `_saircSimplifyHooked` — **0 references outside the block** |
| Element ids created | **none**, so no stub-collision interaction |
| CSS classes injected | `.sairn-response-actions`, `.sra-btn` — **0 references outside the block** |
| `window` exports | its own two flags, plus the `addMsg` wrapper |

## But it is NOT fully isolated — Real Personalization reads its buttons

This is the part a delete-the-block change would have missed. **Real
Personalization AI** listens for clicks on Feature 6's buttons by their *text*:

    :19937  if (text.includes('Simplify'))   { learned.simplifyUsed++; saveLearned(learned); }
    :19938  if (text.includes('Go Deeper'))  { learned.deeperUsed++;   saveLearned(learned); }

and those counters feed the context that actually reaches the model:

    :19724  if (learned.simplifyUsed > 2) lines.push('• Response preference: This user frequently uses Simplify — lead with plain language');
    :19725  if (learned.deeperUsed   > 2) lines.push('• Response preference: This user frequently uses Go Deeper — provide thorough depth');

**That matters because Personalization is live.** It was confirmed on 2026-08-31
to be reaching the model — the model reported `LEARNED USER PREFERENCES` present
in its system prompt. So this is live code depending on a dormant feature, not
dormant-to-dormant.

## Why it is still a no-op

Feature 6's buttons **have never rendered**. It hooks `window.addMsg`, which
nothing in the file defines, so its install guard returns early and the buttons
are never created. Nothing can ever have clicked them, so `simplifyUsed` and
`deeperUsed` have always been `0`, and those two context lines have never fired.

**Removing Feature 6 removes code that was already inert, and the two
personalization branches that fed off it were already unreachable.** There is no
behaviour to lose and no migration to write.

## The change, in full

1. Delete the Feature 6 `<script>` block, lines **17716–17881**.
2. Delete the two click-listener branches at **:19937–19938**.
3. Delete the two context-line branches at **:19724–19725**.
4. **Leave `simplifyUsed` / `deeperUsed` in the stored `learned` object.** They
   are harmless legacy keys, and stripping fields from a persisted model that
   real browsers already hold is a migration — disproportionate for two integers
   that are always zero.

**Order matters:** steps 2 and 3 are inside Real Personalization, whose
`window.fetch` patch is live. Do them as targeted line edits, not as a block
delete, and re-run `node --check` between each.

## Verification this needs

- `0a` — 126/126 inline blocks must still pass; the count drops to **125** once
  the Feature 6 block is gone, and that is the expected number, not a regression.
- Div balance unchanged (the block contains no markup).
- `tools/sairn_reachability_check.py` — the two `_saircSimplify*` flags should
  disappear from any output.
- In a browser: `LEARNED USER PREFERENCES` must still appear in the model's
  system prompt afterwards, by the same discriminating probe used on 2026-08-31.
  That is the real test — it proves the personalization edits did not break the
  live path.

## After this, seven remain

The other seven `addMsg` hooks are untouched. **Defining one base `addMsg` would
still revive all seven at once**, so that remains a separate decision and is not
made easier or harder by this change.
