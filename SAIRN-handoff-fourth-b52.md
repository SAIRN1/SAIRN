# HANDOFF — fourth / ted, batch b52, 2026-10-21

**READ THIS FILE ONLY.** It is the whole state. **Landed and live. No force,
no gate skip.** Wrapped at a safe point at **~65% real context**.

**THE ONE THING TO READ FIRST:** this batch's queue said the NVDA run had
completed. **It had not.**
- b51's script matched the window title "Chromium", but Playwright titles its
  window **"Google Chrome for Testing"**. So when Michael clicked the window,
  the script refused anyway. It also left NVDA running, still logging his
  other windows; I quit it this batch.
- The title match is fixed. The run was re-launched and **completed**:
  Michael clicked, 23 panels were driven, NVDA quit at the end.
- **Only the Dashboard panel was heard cleanly.** The machine was in use during
  the run, so for the other 22 panels NVDA read Edge, Supabase, the Command
  Prompt and Gmail. **`nvda_after.log` in the scratchpad contains that
  private-window speech; do not share it.**

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Scratchpad:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- `nvda_dental.py`: the NVDA run. It sends no OS input and refuses when the window is not in front.
- `a11y_dental.py`: the axe and keyboard pass. Set `A11Y_APP` to `sairndental`, `sairnlegacy` or `sairnfreedom`.
- `a11y_freedom_before.json`, `a11y_freedom_after.json`, `a11y_freedom_live.json`, `nvda_after.json`: results.

## 1. STATE

| item | sha (origin) | state |
|---|---|---|
| 1 NVDA readout + fix | `26f966694` | live; dental 15 arms, legacy 20 arms, emoji mutant killed in each |
| 2 SAIRNveterans (`sairnfreedom.html`) | `4dcd23a26` | live; axe 168 → 0; keyboard sidebar 0 → 28/28; 10 arms, 8/8 mutants |
| register / override / docs | through `79568896d` | landed; fourth holds 18 overrides |

## 2. WHAT NVDA ACTUALLY SAID (Dashboard, clean)

| | NVDA said | verdict |
|---|---|---|
| sidebar item focus | "Main navigation, complementary landmark, 📊Dashboard, button, **current page**" | b50 `aria-current` CONFIRMED. **New defect:** the emoji's name is read before the item's |
| Enter | "main landmark, **Dashboard, heading, level 2**" | b51 J1 CONFIRMED |

- **Fix concept:** the emoji icon is decoration, so it is hidden from the
  reader. `aria-hidden` is set on every `.sb .sico` at load, in sairndental
  (23 items) and SAIRNlegacy (27).
- **What axe and the accessibility tree had missed:** both passed this, so
  only listening found it.

## 3. SAIRNveterans = `sairnfreedom.html`

`sairnvet.html` is the veterinary app, so it is not this one.

**Before (live):**
- the **whole sidebar was `<div onclick>`**: no panel was reachable by keyboard;
- 168 axe nodes: 106 `label`, 62 `select-name`. Every field is written `<label>X</label><input id>` with no `for=`;
- Enter did nothing on the licence or PIN fields;
- no `aria-current`, and a panel change was silent.

**Fixes (one concept each):**
- the 28 sidebar items are now `<button>`s, with a CSS reset so they look the same;
- a load-time pass ties each label to the control that follows it;
- Enter submits the licence and PIN fields;
- `.ptitle` becomes a heading;
- `aria-current` marks the current item;
- `sfNav()` moves focus to the heading (J1). Access has no title, so it falls back to its first `h3`;
- the district file-import input is named.

**After (live):** 0 axe nodes, 28/28 sidebar items are buttons, and focus
lands on a heading on 28/28 panels.

## 4. OPEN

1. **A clean NVDA pass of the remaining 22 dental panels**, plus legacy and
   freedom. It needs about 4 minutes with **nobody using the machine**.
2. **Not mine:** `tests/sairnfreedom_segregation_of_duties.js` is red, and the
   same at HEAD.
3. **Not covered:**
   - modals;
   - fields that freedom renders later by script (the label pass runs at load only);
   - the other launch-wave apps.

## 5. CLAIMS

`fourth`: released at wrap. No SQL.
