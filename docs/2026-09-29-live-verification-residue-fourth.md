# Live verification on the deployed URL, and the residue record

**Fourth, 2026-09-30.** Two fixes driven against `https://sairn.vercel.app`,
not read.

---

## Residue: NONE. No row was created, local or server.

**This is the first section on purpose.** The rule is that any row created is
recorded by table and id with the deletion SQL printed. Nothing was created, so
the honest record is a zero with the reasoning that makes it checkable:

| App | What was touched | Reached a server? | Restored |
|---|---|---|---|
| SAIRNbiz | `sb_cfg` in localStorage, written three times through the app's own `saveSettings()` | **No.** `sb_cfg` is absent from `SB_SYNCED` (`sairnbiz.html:5404`), which is the list `st()` syncs. It is a browser-local setting. | Yes — `sb_cfg` was `null` before and is `null` after, verified by reading it back |
| SAIRNbuild | `bld_settings` in localStorage, and `bld_jobs` **written with raw `localStorage.setItem`, deliberately never through `st()`** | **No.** `bld_jobs` IS in `BLD_SYNCED`, which is exactly why `st()` was avoided — the job was only the precondition of `openDrawModal`'s guard, not the thing under test | Yes — both keys restored to their prior values and re-read; `ZZ-DRIVE-JOB` is gone and `jobs()` is back to its 6 demo rows |

**So there is no residue SQL to run, and printing a DELETE that matches nothing
would be worse than printing none** — it reads as cleanup that happened.

**Three `ZZ-RETAINAGE-*` rows DO sit in `bld_draws` and they are NOT mine.**
`ZZ-RETAINAGE-VERIFY-20260921`, `ZZ-RETAINAGE-RACE-20260921` and
`ZZ-RETAINAGE-RACE2-20260921`, all stamped 2026-09-21, all `status: approved`,
all with `job_id: null`. They predate this session by nine days and belong to
whoever ran the retainage race probe. Reported rather than cleaned up: deleting
another session's evidence is not mine to do, and they are named here so the
next residue sweep does not have to rediscover them.

**No credential was entered.** The browser already held a live
`SB-TEST-2026` / `owner` session, verified by reading `sb_lic` and `sb_role`
before driving anything, so the PIN was never needed. It would not have been
typed in any case — that is a standing limit on a deployed host, not a
judgement about this licence.

---

## 1. SAIRNbiz — overtime threshold. **One half passed, one half FAILED.**

Deployed code confirmed carrying the fix before anything was driven:
`sbCfg.toString()` contains `hasOt`, so the `hasOwnProperty` form is live.

Driven through the app's own `saveSettings()` — setting `ss-ot`, dispatching
`input` and `change`, then calling the real save — and read back out of the
real chain `sbCfg → sbOtThreshold → sbOtThresholdNote`:

| Typed | Stored `ot` | `sbCfg().ot` | Threshold | Note |
|---|---|---|---|---|
| `0` | `"0"` | `"0"` | 40 | **`the recorded setting "0" is outside 1–168 and was NOT used`** ✅ |
| *(cleared)* | `""` | `""` | 40 | `Overtime is computed above 40 hours per week.` ❌ **silent** |
| `45` (control) | `"45"` | `"45"` | 45 | `…above 45 hours per week (set in Shop Settings, not the federal 40)` ✅ |

**The typed-0 half is fixed and live. The blank half was not, and the live run
is what found it.**

### Why the blank case is a real defect and not a nicety

`saveSettings()` stores `$('ss-ot').value` (`sairnbiz.html:5035`), so a cleared
box **persists as the empty string** — and `loadSettings()` puts it straight
back. The Shop Settings screen therefore shows an **empty** overtime box while
payroll computes at **40**. One stored setting, two answers on two screens.

That is the same shape as SAIRNbuild's 0% markup rendering as 18% on the bid
form, which is the other half of this same queue item.

**And this suite had excused it.** An earlier arm called a blank *"harmless for
the verdict"*. It is not harmless; it is the silence, one value over.

### Fixed, with the arms and an ablation

`sbOtThresholdNote()` now reports a saved-empty threshold in its own words —
**not** by reusing the out-of-range sentence, because `""` is not "outside
1–168" and a true refusal with a false reason sends the reader to check a
number they never typed. Two new arms, plus a control that reconstructs the
**pre-fix note** and requires it to *fail* to report a blank. Ablation driven:
removing the new branch takes exactly one arm red.

`ALL 12 OT-THRESHOLD COALESCE ASSERTIONS PASS`. All 5 script blocks
`node --check` clean.

**An ABSENT key is still not reported, and that survives by construction rather
than by a special case:** `sbCfg()` uses `hasOwnProperty`, so an absent `ot`
yields the *number* 40, which equals the threshold and is therefore not
rejected. Only a value somebody saved can be empty.


### Re-verified LIVE after the fix deployed

`f8acd128` on `origin/main`, `sbOtThresholdNote.toString()` on the deployed page
confirmed to contain `SAVED EMPTY` before anything was driven. Same licence,
same path through the app's own `saveSettings()`:

| Typed | Threshold | Note |
|---|---|---|
| *(cleared)* | 40 | `— the overtime threshold was SAVED EMPTY, so the federal 40 is being used; the Shop Settings box will look blank until a number is entered` ✅ |
| `0` | 40 | `— the recorded setting "0" is outside 1–168 and was NOT used` ✅ |
| `45` (control) | 45 | `(set in Shop Settings, not the federal 40)` ✅ |

`sb_cfg` restored to `null` and re-read. Still no residue.

---

## 2. SAIRNbuild — 0% markup and retainage. **PASSED, with a live ablation.**

Deployed code confirmed carrying both fixes first: `openBidModal.toString()`
contains `m==null?18:m` and `openDrawModal.toString()` contains `r==null?10:r`.

With `default_markup_pct: 0` and `default_retainage_pct: 0` stored, all three
screens were read on the live page:

| Screen | Field | Shows |
|---|---|---|
| Shop Settings | `set-markup` / `set-retainage` | **0% / 0%** |
| New Bid form | `bm-markup` | **"0"** |
| New Draw form | `drm-retpct` | **"0"** |
| Defaults edit | `dfm-markup` / `dfm-retainage` | **0 / 0** |

**Every consumer agrees with the settings screen.**

### The live ablation, which is what makes those four zeros mean anything

Evaluated against the *same stored settings* on the live page:

```
[ g.default_markup_pct    || 18,  ->  18     (PRE-FIX)
  (m==null?18:m)(markup)       ,  ->   0     (DEPLOYED)
  g.default_retainage_pct || 10,  ->  10     (PRE-FIX)
  (r==null?10:r)(retainage)    ]  ->   0     (DEPLOYED)
```

Without it, four zeros prove only that something renders 0 — not that the fix
is what made it so.

### One limit, stated

`openDrawModal` returns early when `jobs()` is empty, so the draw form could not
be reached until a job existed. The job was created with **raw
`localStorage.setItem`, never `st()`**, precisely because `bld_jobs` is in
`BLD_SYNCED` and `st()` would have written a real server row. The guard is not
what is under test; the prefill is. Stated because the alternative — quietly
creating a job and reporting a clean run — is the shape this record exists to
prevent.
