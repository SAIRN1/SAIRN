# HANDOFF — fourth / ted, batch b35, 2026-10-19

**READ THIS FILE ONLY.** It is the whole state.

**Written BEFORE the report, which is the standing instruction.**

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **THE `sd_field_stops` CONTRADICTION IS RESOLVED AND ONLY ONE ROW MOVED.**
   The deciding test was written into the register in b34 *before* the read, so
   the answer could not be fitted to the result. §3.
2. **THE SEVEN `shared.js` RESOURCES ARE TIERED — AND `employees` IS A/A
   BECAUSE THE CODE ALREADY SAID SO.** `api/sd-data.js` has carried a per-role
   gate stripping `hourly_rate` for months. The register was the only place
   that did not know. §4.
3. **THE TIER-CHECKER GAP FAILS OPEN IN *BOTH* DIRECTIONS, which is worse than
   b34 recorded.** It never demanded a row for the seven, **and it rejects the
   rows as orphans once written**. Routed to cc, **not applied**, and the fix's
   effect was **measured in a worktree**, not asserted. §5.
4. **ALL FOUR ROUTE CONSUMERS ARE STILL UNREACHABLE AT RUNTIME.**
   `api/sd-data.js`'s handler branch is still unapplied and the schema has
   still never been run. §7.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\7114877e-14ff-4635-8129-799b043ea778.jsonl`
(same session as b33/b34 — a continuation)

**Working files:**
`…\7114877e-14ff-4635-8129-799b043ea778\scratchpad\b35\`
— `simulate_cc_fix.py` (the worktree measurement of §5),
`add_shared_rows.py`, `httpd.log`.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind — PUSHED AND LANDED** | `git rev-list --left-right --count origin/main...HEAD` |
| the two b35 commits | `321128d8` the work · `9d70a20b` the headline re-derived on the merge | `git log --oneline origin/main` |
| both confirmed on origin | pass `merge-base --is-ancestor` | — |
| **files my commits touch** | **exactly five** — two docs, the manifest, `sairnroofing.html`, `sairnscape.html` | `git show --name-only --format="" 321128d8 9d70a20b \| sort -u` |
| **`api/sd-data.js` / `tools/`** | **0 — NOT TOUCHED** | same command, `\| grep -cE 'api/sd-data\.js\|^tools/'` |
| uncommitted | **none** (after the manifest commit below) | `git status --porcelain` |
| `git stash` | **0** | `git stash list` |
| force push | **none** | — |
| overrides | **none, any form** | — |
| `.claude/settings.json`, `.githooks/` | **not touched** | — |
| auditor clones | **not entered** | — |
| temporary worktree | created for §5's measurement, **removed** | `git worktree list` |
| b35 manifest | `--items 6`; **6 done** | `batch_manifest.py --check --agent fourth --batch b35` |

### A measurement I got wrong and corrected, recorded rather than replaced

My first attempt at the "did I touch `api/sd-data.js`" evidence used a **commit
range** (`6a48a4e9..9d70a20b`) and answered **1**. That was wrong. The range
spanned other sessions' commits, and the hit was **cody's own `1c9ad7cf`**
touching their own claimed file.

**A range measurement answers *"did anybody touch this file in this window"*,
not *"did I touch it"*.** The correct command scopes to my own commits and
answers **0**. Both the wrong attempt and the correction are in the manifest
evidence for item 6, because a corrected number with no record of the
correction is how the next person makes the same mistake.

---

## 2. CLAIMS HELD

**`fourth` holds one claim**, declaring exactly the files touched:
`docs/CRITICALITY-TIERS.md`, `stonedesk.html`, `sairnscape.html`,
`sairnroofing.html`, the b35 doc, the manifest, and the three deliverables.
**Released LAST, after the push.**

**`stonedesk.html` was claimed and NOT modified** — the read for §3 was a read.
hank's own b21 claim string carries `NOT-stonedesk.html-fourth-holds-it`, so
that deferral is honoured in both directions.

**Other active claims when this was written:** cody on `platform`
(`api/sd-data.js` — still held, see §7), hank on `hank` (`api/bridge.js`, which
is **my routed b34 item, now picked up**), hover2 on `hover2`.

---

## 3. ITEM 1 — THE CONTRADICTION, RESOLVED

### The deciding test, quoted from the register as it was written in b34

> **Is a stored stop joined to a NAMED person?** If yes it moves. If the stop
> carries no assignee at all, B is right — and then `rt_stops` is the first
> time that join exists in StoneDesk's data.

### The answer: yes, twice over

`fmSaveStop()` (`stonedesk.html:12879`) **refuses to save** without all three —
*"Person, address, and date are required"* — and defaults `person` from
`currentUser.name`. The stored row is
`{id, person, type, date, time, address, customer, notes, status, createdAt}`,
where `customer` is a free-text **"Customer name"** input (`:8446`).

**And it leaves the device:** `sd_field_stops` is in `SD_SYNCED` (`:2035`). A
local-only reading would have missed that half.

So the row carries **a named employee, a named customer, a street address, a
date and a time** — **strictly more than `rt_stops`**, which has no
customer-name field at all.

### Only one row moved

**`sd_field_stops`: B → A on confidentiality. `rt_stops`: re-read, stands at
A/A.** Integrity on `sd_field_stops` stays **B** — a lost stop costs a re-entry
— so the A is the confidentiality axis alone.

**Correcting both to match would have been the retier-by-analogy the gaps
bullet existed to refuse.** The old cell was not dishonest; it said of itself
*"Classified by the stated B rule rather than individually read."* It was
honest that it had no evidence. The contradiction is what forced the read.

---

## 4. ITEM 2 — THE SEVEN, READ AT THEIR WRITE SITES

| resource | Tier | Conf. | deciding fact |
|---|---|---|---|
| `profile` | B | B | the shop's description of itself; nothing about a person |
| `memory` | B | B | redacted on write — `memory` **is** in `AI_SCANNED_TEXT` (`ai-scan-redaction.js:84`) |
| **`employees`** | **A** | **A** | compensation, **and a money path across an app boundary** |
| `slabs` | **A** | B | **a documented incident** — the third limb of the A rule |
| `render_usage` | B | B | an integer per shop per month |
| `shared_knowledge` | B | B | a word list; *"Never raw message text"* |
| **`employee_profile`** | **A** | **A** | a manager's written assessment of a named employee |

**Both rows flagged in advance as *not obviously B* moved.**

**`employees` — the sharpest part is that the code already knew.**
`api/sd-data.js:2478` carries a comment that **predates the row**: the resource
carries `hourly_rate`, Sales and Install are refused outright, a Manager gets
the rate **stripped**, only an Owner sees pay. Nobody builds a per-role
field-stripping gate for Tier B data. **And the integrity half crosses an app
boundary:** `stonedesk.html:43148` averages `hourly_rate` into a labour rate
upstream of what a job is quoted at — SAIRNbiz's roster, StoneDesk's costing.

**`employee_profile` — the READ gate is the evidence.** `:3731` refuses
`payload.all` outside Owner/Manager and otherwise serves only the caller's own
profile, **derived server-side from the session token, never from a
client-supplied `employee_id`**. An app does not do that unless the row is
about a person.

**One row keeps an open question rather than rounding it off:** `memory`'s B
rests on `redactDocumentText()` normally returning `complete: true`, and
**nobody has measured how often it returns `false`**. Written into the row.

### Two of my own errors, both caught by guards, both kept

1. **`COMPUTED TIER MISMATCH`** — I first typed `employee_profile` Tier **B**
   beside Confidentiality **A**. The Tier is **derived** as the worse of the
   two, never hand-entered. The checker refused it. That refusal is written
   into the row itself, because a hand-entered Tier is exactly how a Tier A row
   ships reading B.
2. **The pipe-count guard** — my own assertion caught `data: emp.data || emp`
   putting **two literal pipes** inside a table cell, which would have broken
   the row structure. Escaped as `&#124;&#124;`.

---

## 5. ITEM 3 — ROUTED TO cc, AND THE FIX WAS *MEASURED*

**NOT APPLIED. `tools/` was not touched.**

### The gap fails open in BOTH directions — worse than b34 recorded

`apps_with_registries()` skips `shared.js` by name
(`if app in ('index', 'shared')`). `index.js` belongs there — it is the merger.
**`shared.js` does not** — it is a registry with seven real resources.

1. **It never demanded a row** for any of the seven, including `employees`,
   Tier A on both axes.
2. **It rejects the rows as orphans once written** — writing them raised **7
   `NOT A RESOURCE`** findings plus one `GONE` for the rollup line.

**So the register could not be made correct without the fix.** That is what
makes this a blocker rather than a tidy-up, and it is the half b34 did not see.

### The fix, and its measured effect

```python
    if app == 'index':
        continue
```

Simulated in an **isolated worktree** over the b35 register
(`scratchpad/b35/simulate_cc_fix.py`), diffing findings before and after:

```
BEFORE   APPS_WITH_REGISTRIES 18   RESOURCES_REGISTERED 394   PROBLEMS 11
AFTER    APPS_WITH_REGISTRIES 19   RESOURCES_REGISTERED 401   PROBLEMS  3
CLEARED 8   (1 GONE + all 7 NOT A RESOURCE)
INTRODUCED 0
```

**The `### shared` section and its rollup line are already written**, so cc's
one line lands on a consistent register rather than on seven fresh findings.

**Two things named for cc to decide rather than assumed:** whether `routes`
staying its own registry file is now a choice rather than a workaround, and
whether the skip should be a property a file declares rather than a hard-coded
name list that goes stale.

---

## 6. ITEMS 4 AND 5 — CONSUMERS THREE AND FOUR

**The point is not that there are more. It is that each shape differs and the
module did not change.**

| | assignee | address lives on | storage |
|---|---|---|---|
| StoneDesk (b34) | `person` on the stop | **the stop itself** | localStorage |
| SAIRNgrounds (b34) | `crew` string | the **property** | localStorage |
| **SAIRNscape (b35)** | `crew` string | the **customer** | localStorage |
| **SAIRNroofing (b35)** | **`crew` ARRAY** | the **job** | **server-first** |

**SAIRNroofing is the one that actually tested the seam.** `crew` is an array,
so **there is no single assignee on the record at all** — the ordering unit
becomes one named person across the days they appear on, which is the right
unit regardless since a route is driven by a person. And it is the first
**server-first** consumer: `rfSchedule` arrives from the server with role-scoped
visibility already applied, so the card reads the in-memory list rather than
issuing a second query that could return a different set.

**Both driven in a real browser, every answer path:**

| path | SAIRNscape | SAIRNroofing |
|---|---|---|
| `unavailable` | names the reason, schedule unchanged | same |
| `drive-matrix` | reordered, *"saves about 8 min"* | reordered, *"saves about 11 min"* |
| **`saved_seconds: null`** | **"drive-time saving not computed"** | same — **never "0 min"** |
| `great-circle` | labelled with the drive-time reason | labelled |
| no answer | *"Nothing was changed"* | *"did not run — Not signed in"* |
| order length ≠ stops sent | — | **refused, schedule unchanged** |

**Exclusion path confirmed in both:** a visit whose customer (scape) or job
(roofing) has no address is **listed by name as excluded**, never dropped.
**Roofing's crew-array flattening confirmed:** `['Ana Reyes','Tom Cole']` and
`['Ana Reyes']` across three days produced exactly **two** picker entries,
deduped and sorted.

`checkblocks`: **scape 7/0**, **roofing 3/0**, **stonedesk 131/0**.
`node api/_lib/routes.test.js` → **56 passed, 0 failed**.

---

## 7. WHAT IS OPEN, AND THE EXACT NEXT STEP

1. **`api/sd-data.js`'s `rt_routes` handler branch — still unapplied.** cody
   holds that file and pushed to it during this batch (`1c9ad7cf`). The branch
   and its `extraActions` line are pasteable in
   `docs/2026-10-19-fourth-b34-routing-phase1.md` §3. **Until it lands, all
   four consumers are unreachable at runtime.**
2. **`sql/rt_routes_schema.sql` — still never run.** Michael's, in the Supabase
   SQL editor. Neither table exists.
3. **cc:** the one-line checker fix (§5), and the Tier A review obligation on
   `rt_routes`/`rt_stops` opened in b34, still undischarged.
4. **SAIRNmechanical** — queued for the next batch, as instructed. Its shape is
   not yet read.
5. **Tier checker PROBLEMS is 14** and **none of the 14 is a fourth row stating
   a wrong tier**: 8 are the single `shared.js` cause (§5), 3 are cody's open
   `leg_clergy` rollup, 2 are pre-existing `sairnscape` drifts, 1 is
   pre-existing `sen_period_closings`.
6. **`memory`'s redaction completeness rate** (§4) — unmeasured, and the one
   thing that would move that row.

---

## 8. WHAT b35 PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:**

* `sd_field_stops` carries person + customer + address + date + time and syncs
  to the server — read at the write site, not inferred.
* All seven `shared.js` resources read at their own write sites; `employees`
  and `employee_profile` both moved off B.
* cc's one-line fix clears **8** findings and introduces **0** — measured in an
  isolated worktree, not asserted.
* Both new consumers behave correctly across every answer path in a real
  browser, including `saved_seconds: null` claiming nothing.
* Roofing's array-crew flattening and its bad-order-length refusal.
* My commits touch five files; `api/sd-data.js` and `tools/` are **0**.

**LEFT UNPROVEN, and none of it is recorded as checked:**

* **Nothing live.** Unchanged from b34 and for the same measured reason: the
  licence gate answers 401 ahead of resource dispatch, so a probe cannot tell a
  registered resource from a nonsense one.
* **The schema has never been run.** Neither `rt_routes` nor `rt_stops` exists.
* **All four consumers are unreachable at runtime** until the handler branch
  lands. The browser evidence used a **stubbed transport** — it proves the
  client handling, not the round trip.
* **`memory`'s redaction completeness is unmeasured.**
* **The seven new rows are correct but unverifiable by the checker** until §5
  lands — it currently calls them orphans.
* **No keyboard, focus-order or screen-reader pass**, in any app, ever.
