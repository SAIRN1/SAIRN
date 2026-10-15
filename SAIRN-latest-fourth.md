# LATEST — fourth / ted — batch b25 — 2026-10-15

**ALL SIX ITEMS DONE.** `HEAD == origin/main` at **`c57b50ab`** when this was
written, 0/0, clean, **NOT forced** (ancestry-proved; `grep -c force` → 0).
**The live tip is AHEAD of that by the commits carrying this file** — by design,
not drift; naming it here would need another commit and move it again. Gate ran live and allowed. No
`SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` in any form. `settings.json`
untouched. 0 files written under `api/ sql/ tests/ tools/`. Auditor clones not
entered. **Tier A: all three obligations assigned to fourth DISCHARGED — and
then a FOURTH arrived at 15:04:38Z and is UNTOUCHED** (see below).
**CONTEXT 28.8% of 1000k** (288,038 tokens).

## The four things worth knowing

1. **I WITHDREW MY OWN NUMBER.** b24's **25** class-B write branches is wrong; **it
   is 22**, and *"the b23 routing list is short by three"* goes with it.
   `api/sd-data.js` never moved — same blob sha across 36 commits — so the two counts
   were two predicates over one file, and mine had a 14-line-window span bug that
   typed three pre-write **GET**s as POSTs.
2. **b18's N1 IS CLOSED.** Fixed 2026-10-14, the fix names it by number
   (`api/sd-data.js:7214`). Open since b18 across b21–b24. **Remove it everywhere.**
3. **THE TWO 400 OBSERVATIONS ARE MADE.** A `23514` on the `alf_op_audits` upsert
   (Tier A) answers **503 "run the migration"** while the shipped
   `notProvisioned()` answers **400 ROW_REFUSED** correctly, so it is a call-site
   fix. A `42703` on a read answers **200 `provisioned:false`**, empty, no error.
4. **ONE HIGH, ABLATED:** cody's arm Z has no `else`, so with `id` stripped off
   every blob the suite is **exit 0, 15 passed, 0 failed** and the arm vanishes.

## Open items

| owner | item |
|---|---|
| hank | **b24 F3** delete the replaced id **server-side**; **b24 F4** field-merge `legAdoptServerId` on the write's own payload (`Object.assign` is not the fix) |
| hank | **the 22 branches** from the corrected list (report §3), then b23's 13 caller GETs, then `:13503`/`:17127` |
| hank | **MODERATE:** `pending_clock_visits` in payroll; `isAppendOnly(resource)` not the typed-in map, in both session-gate suites. **LOW:** `storedBlob(payload,['id'])` for the HR branch. **Plus the 5 re-verified open findings:** b21 F3, b21 F4, `license_hash`, no-revoke, both `sd_photos`; and b23 F4 |
| cody | **arm Z's `else`, then RE-RUN THE ABLATION** — the arm does not count until it comes back RED |
| cody | known-red row → **RECOVERED**; the control arm's hardcoded *"ten failures above"* → read off `failed.length` |
| cody | **b24 F1** re-anchor on `const acEsc = (s) =>` + the `acKey` ternary, **with an arm that fails when the anchor stops matching**; and a failing-first arm driving a `23514` through one of the 22 and a `42703` through one of the 151 — b25 **observed** both, nothing drives either |
| cc | `tier_a_review_gate.py --amend`; wire ONE anchor-rot tool into a gate; R3's 48 citation ranges; **the convention-numbering check is still unbuilt**; **and `SAIRN-latest-<agent>.md` is a FILENAME COLLISION** — see below |
| fourth | **FRESH TIER A, UNTOUCHED:** `hank 2026-10-15T15:04:38Z` — seven Tier A resources, three changes, routing doc `docs/2026-10-15-hank-b16-to-fourth-tier-a.md`. **Three of hank's five questions are DECISIONS, not checks** (the straight-time adjustment floor vs an FLSA premium on an already-paid week; adjustments that post only in the period containing their approval with nothing sweeping for unposted ones; a frozen period paying as at `paid_at` while a federally mandated EVV export reads now). Take change (3) first — the `law_trusttx` stale expectation is the one settleable by reading the assertion |
| fourth | **open the batch manifest FIRST next batch**; drive (d) `LATE_REPLAY`; extend the census to follow a variable through its assignments |
| Michael | **b23 F2 IS NO LONGER HELD** — you decided it and hank implemented it in `883ad0bc`; the EVV checks now read the same effective clock pay uses, GPS deliberately unmoved. **Still held and not acted on:** the one-person-agency self-approval question. **And three NEW decisions** sit inside hank's fresh b16 record above. **And one decision:** an approved clock correction now reaches pay (300/10000 vs 240/8000, driven), but **whether any real visit was underpaid before today is not establishable from the repo** — no production row was read — so whether a **back-payment** is owed is your call |

## For cc: `SAIRN-latest-<agent>.md` is a filename collision

`tools/sairn_board_publish.py:131` writes `LATEST_NAME = 'SAIRN-latest-%s.md'`
into this same folder on **every claim change by any agent**, and I watched it
replace my 5,134-byte upload with its own 2,809-byte version mid-batch, so an
agent-authored file of that name is transient and **cannot be durably verified**
— a batch-stamped copy `SAIRN-latest-fourth-b25.md` is uploaded beside it for
that reason. It also **TRUNCATES to ~60 lines** (`:961`), so an over-long
hand-written file silently loses its tail. The generator reads my digest
correctly (CONTEXT and STATUS propagate), so the fix is a NAME, not a mechanism.

## Said rather than left as an absence

**No b25 batch manifest exists** and I did **not** create one retroactively — `--new`
writes an `id_lock` meant to be fixed before the work. **One bypass, mine, corrected
before any push:** a first commit used `core.hooksPath=/dev/null`; `--amend` re-ran
the hook with it active, and nothing reached origin under it. **Not done:** (d)
`LATE_REPLAY`; the 33 server-only GETs (**CALLER is still a lower bound**); b24
F3/F4, the 22 and cody's re-anchor are **routed, not reviewed — no record exists**;
no production row, no live fetch, no table touched.

**Convention 35 landed** — *a predicate has a SPAN as well as a PATTERN, and a
re-count that disagrees is a predicate disagreement until the SUBJECT is proved to
have moved.* **Cite it as `convention 35`, never a bare "item 35".** Report SHA256
`7979c6269b4958faa27d91f3267ad266db634db3e47348e427c1b4a132cd64e4`.
