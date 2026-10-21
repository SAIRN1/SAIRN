# HANDOFF — fourth / ted, batch b51, 2026-10-21

**READ THIS FILE ONLY.** It is the whole state. **J1 and the SAIRNlegacy pass
are landed and live. No force, no gate skip. The real NVDA run did NOT
happen.** Wrapped at a safe point at **~58% real context**.

**THE ONE THING TO READ FIRST: the NVDA run, and an incident.**
- **Attempt 1** drove NVDA with real OS keystrokes (`SendInput`). Chromium
  never held the foreground, so the keystrokes reached Michael's other windows.
  NVDA's log shows focus on:
  - the Start button;
  - the Wi-Fi quick-setting;
  - the Claude app, including its "Send message" button.
  Whether an Enter actually sent or toggled anything is **unknown**. Michael
  was told in-session.
- **Attempt 2** was the fixed script. It sends **no OS input at all**: keys go
  to the page over CDP. Windows will not give a background process the
  foreground without input, so the script waits for one human click on the
  Chromium window and refuses otherwise. **Nobody clicked within 5 minutes, so
  it refused. NVDA has quit.**
- **To run it:**
  `python <scratchpad>\nvda_dental.py after C:\Users\marsh\Documents\SAIRN-fourth\sairndental.html`
  Then click the "SAIRNdental" Chromium window once and leave the machine for
  about 4 minutes. The speech log lands in `nvda_after.log` and `nvda_after.json`.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Scratchpad:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- `nvda_dental.py`: the NVDA run.
- `a11y_dental.py`: axe and keyboard. Set `A11Y_APP=sairnlegacy` for SAIRNlegacy, and `A11Y_LOCAL_HTML` to test a local tree at the live URL.
- `a11y_legacy_before.json`, `a11y_legacy_after.json`, `a11y_legacy_live.json`, `a11y_j1.json`, `a11y_dental_live51.json`: results.
- `nvda_before.log`: attempt 1. It contains speech from other windows on Michael's desktop.

## 1. STATE

| item | sha (origin) | state |
|---|---|---|
| 2 real NVDA run | — | **NOT RUN.** Refused safely, no click; the script is ready |
| 3 J1, sairndental | `0b6ddaaa9` | live. Focus goes to the heading on 23/23 panels, and the first Tab enters the panel. 14 arms; 4 J1 mutants killed |
| 4 SAIRNlegacy pass + fixes | `dada3f33a` | live. axe 88 → 0 nodes, headings 0 → 27/27, aria-current, focus-to-heading 27/27, chips are buttons. 19 arms; 7/7 mutants |
| register / overrides / docs | `8a07b196b`, re-seated | override added for `tests/sairnlegacy_a11y_pass.js`; fourth now holds 17 |

## 2. CONCEPTS

- **J1:** `nav()` moves focus to the new panel's heading (`tabindex=-1`). The
  live region is kept only as a fallback for a panel with no title, so the
  panel name is not spoken twice.
- **SAIRNlegacy:**
  - the 11px KPI captions use `#15803D` / `#B91C1C`. These were 2.3:1 and 3.8:1; the `--ok` and `--danger` colours stay for icons.
  - 10 labels are tied to their controls with `for=`;
  - each GPL price input is named "Price for &lt;service&gt;";
  - the AI prompt chips are now `<button>`s;
  - panel headings and `aria-current` work as in sairndental;
  - J1 is applied here as well, because a panel change was otherwise completely silent to a screen reader. **This extends Michael's sairndental decision; flag it if it should not carry over.**

## 3. OPEN

1. **The real NVDA run:** one click from Michael, see above.
2. **Not mine:** `tests/sairnlegacy_reservation_lock.js` is red, and fails the same way at HEAD.
3. **Not covered:** modals in both apps; the other launch-wave apps.

## 4. CLAIMS

`fourth`: released at wrap. No SQL.
