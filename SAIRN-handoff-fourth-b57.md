# HANDOFF — fourth / ted, batch b57, 2026-10-22

**READ THIS FILE ONLY.** It is the whole state.

**Summary:**
- **F3 driven live through the deployed UI, on Michael's approval.** It passed. The residue is recorded, with removal in a SQL file.
- **15 modal / sub-view controls are named.** The change is live.
- **NVDA hears the ai heading clean.** aiquote was intermittently missed in this run (filed).
- **Emoji outside headings** is scoped as a separate backlog item.

Everything is landed and live, with no force and no gate skip. Wrapped at **~45% real context**.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Scratchpad:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- Scripts: `live_f3_b57.py` (the live drive), `names57.py` (live name check), `aq57.py` (aiquote focus trace).
- Results: `live_f3_b57.json`, `nvda_sd57.json`, `nvda_sd57.log`.
- **`nvda_sd57.log` holds speech from other windows. Do not share or upload it.**

## 1. STATE (all on origin; HEAD = origin/main at `e0f8b59a6` before the deliverables)

| item | sha | state |
|---|---|---|
| 1 live F3 drive + residue | `10e601502`, `7ea680c61` | done; residue enumerated; removal = `sql/zz_probe_residue_delete_b57_leg_f3.sql` |
| 2 modal control names | `09e810819` | live (bytes = origin 21:25Z); 14/14 named on the live page; slab-bind select names itself |
| 3 NVDA re-run | scratchpad | ai heading heard clean (raw log); aiquote missed once, see §3 |
| 4 emoji outside headings | — | decided: **separate backlog item**, see §4 |
| register / Tier A / re-seat | `a8ed1f41d`, `7ea680c61` | landed; Tier A obligation (slabs) assigned to hank |

## 2. LIVE F3 DRIVE (LEG-PINNACLE-2026 only; `live_f3_b57.py`)

**Setup:**
- The demo owner provisioned `b57-f3-apprentice` and `b57-f3-director` (random PINs, never printed or stored).
- It put `leg_cremations` on the home's countersign list.

**The drive:** stage, countersign and file were **CLICKED in the deployed sairnlegacy.html**, in two browser contexts. The reference passed between them in memory and was never printed.

| step | what the screen or API answered |
|---|---|
| apprentice Save | staged `CR-1792702765162-46`; 0 local rows |
| apprentice Countersign (own record) | "Only a licensed funeral director (Owner or Director) can countersign…" |
| director Look up | "Waiting for a countersignature. Prepared by b57-f3-apprentice (apprentice)" |
| director Countersign | "Countersigned. The person who prepared it can now file it." |
| apprentice Check | "Countersigned -- ready to file" |
| apprentice File | "Cremation record filed with its countersignature" |
| replay the same reference (API) | 409 COUNTERSIGN_ALREADY_SPENT |
| owner read-back | present |
| settings | restored to prior `[]`, re-read |
| credentials | both deactivated; roster `active=false` |

There were 0 page errors and 0 other writes blocked.

**Residue:**
- Enumeration: `docs/live-residue/2026-10-22-fourth-b57-leg-f3-ui-live.json`.
- Removal: **`sql/zz_probe_residue_delete_b57_leg_f3.sql`**. It covers 1 `leg_cremations` TEST row (attached to the seeded demo case CS-1), 1 spent token and 2 deactivated credentials, with the recoverability guard. Nothing was deleted.

## 3. NVDA (raw log `nvda_sd57.log`, this tree at the live URL, writes blocked)

- 201 steps captured, 0 refused; 266 utterances; 66 heading lines, **0 containing an emoji**.
- **The ai heading is heard clean:** `' StoneDesk AI Assistant', 'heading', 'level 2'`.
- **aiquote was NOT heard this run.** Focus ended on BODY.
  - It was heard in the b54, b55 and b56 runs.
  - A headless trace landed on its H2 3/3, including straight after `ai`.
  - So it is intermittent and not reproduced. Filed.

## 4. METHODOLOGY DECISION: emoji outside headings → SEPARATE backlog item

**Why it is separate:**
- In a heading, the emoji always sits beside words, so hiding it can never empty the name. That made one blanket rule safe.
- Outside headings, the emoji is often the whole name: icon-only buttons such as 🗑️, ✕ and 📋, or zones like "📄 Tap to photograph".
- A blanket `aria-hidden` there would turn named buttons into unnamed ones, which is the defect class this pass exists to remove.
- It therefore needs a per-control rule: hide the emoji only when words remain, otherwise write an `aria-label`. That is a different change, with its own verification (axe button-name, plus NVDA).

## 5. OPEN — exact next step for each

1. **Live residue removal (optional):** Michael runs `sql/zz_probe_residue_delete_b57_leg_f3.sql`, one section at a time, if the demo should not show the test record.
2. **aiquote heading intermittent:** re-run NVDA. If it misses again, trace what takes focus after `sbNav('aiquote')`, starting from its render hook.
3. **Emoji outside headings (backlog):** inventory the emoji-led controls; for icon-only ones write an `aria-label`, for the rest wrap the emoji in `aria-hidden`; verify with axe button-name and NVDA.
4. **Modals are named, but not axe-audited while open.** Next step: an axe pass that opens each modal.
5. **`npm ci` (b54):** still not run, because the permission prompt denied it.
6. **Tier A:** hank holds the obligations for b54 and b57. **Not mine:** `stonedesk_exec_msgs_gate`, `sairnlegacy_reservation_lock`.

## 6. CLAIMS

`fourth`: stonedesk and sairnlegacy released at wrap. SQL path: `sql/zz_probe_residue_delete_b57_leg_f3.sql`.
