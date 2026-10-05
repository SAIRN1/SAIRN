# Hank inventory — batch 5, 2026-10-05

---

## 0. Premise log (item 11 methodology)

| Item | Premise at HEAD |
|---|---|
| 1 `sd_email_threats` | **HELD** — `stonedesk.html:38297`, live, and it was **three** defects not one |
| 2 `sairncash` tiering | **FALSE AS STATED** — the zero is deliberate and the register would refuse rows; tiered in the venue that permits it |
| 3 #745 | **HELD** — 8 applied, 1 of the auditor's own corrections wrong, 1 it never mentioned |
| 4 177 DRIFTED | **HELD** but **not drivable to zero** — see §3 |
| 5 rows 82/845 | **STILL OWED** — delivered a third time, now as its own file |
| 6 register claim | **RELEASED** — cc rotated off `CRITICALITY-TIERS.md`; applied |
| 7 ordering | **FOUND AND FIXED** — the push gate reaches 1 of 45 deny sites |

---

## 1. Landed, with shas

| What | Sha | Verified by |
|---|---|---|
| `sd_email_threats` rating reads the **stated** verdict, with a third state | `12781a73` | `tests/stonedesk_email_threat_rating.js` **15/0**, executing the real extracted function; `checkblocks.py` 131 blocks 0 failed; **live** HTTP 200 via `SD-AUDIT-2026` |
| 33 citation repoints applied; `sairncash`'s 4 device-local keys tiered | `b012b03b` | `criticality_tier_check` PROBLEMS:0 (391/391); `stored_data_criticality_check` PROBLEMS:0, 6 rows; `md_table_check` 0 malformed |
| Push-gate `--preflight`: every check, not just the first | *(this push)* | `tests/run_push_gate_preflight_probe.py` **9/0** |

---

## 2. Item 1 — the live call found two shapes I had not imagined

The fix parses the model's **stated** rating instead of substring-scanning, and
returns `null` when it cannot read one. Then I drove the real deployed
`/api/claude` with the documented `SD-AUDIT-2026` licence (a bare request got
401 `NO_LICENSE` first — recorded as UNVERIFIED, not as a failure):

    ### RISK RATING: <green circle> LOW
    ### RISK RATING: <yellow circle> LOW-MEDIUM

**An emoji between the label and the value, both times. A compound rating
outside the four options, once.** My fixture set had neither — every string in
it was one I invented. My original gap pattern rejected both and fell through
to the third state: honest, but needless on what is evidently the ordinary
shape. The gap is now "up to 12 non-letter characters", stopping at sentence
punctuation so it cannot borrow a level from the next clause.

**NEGATIVE RESULT, reported as one:** the captured live response does **not**
reproduce the defect. `critical`/`high`/`medium` appear **zero** times in the
full body, so the old expression also returned Low. The live call proves the fix
parses real output; it is not a live reproduction. Arm F2 says exactly that
rather than implying evidence I do not have.

**Two arms caught me**, both recorded in the file: A1 asserted "this is not a
high risk message" should rate Low — it returns `null` and `null` is right,
because ruling out one level is not stating another. And E1 asserted the old
expression was gone and **failed on my own comment quoting it** — the second
time I have committed that inside a control, one batch after the first.

---

## 3. Item 4 — the 170 remaining is NOT a backlog

Before: SOUND 213 / DRIFTED 177. After 33 repoints: **SOUND 220 / DRIFTED 170.**

**Only 7 of 33 moved a citation into the SOUND window**, and that is a fact
about the tool. It calls a citation SOUND only within 40 lines of an
`st()`/`setItem()` write; most of what these cells cite is comments, function
declarations, render lines and seeds.

**`sd_` got WORSE by that metric — SOUND 13 → 11 — and the repoints are
right.** `sd_comms`' three citations now land on the three real
`var d=commsEnsureIds();` call sites, exactly as the auditor derived, 55–122
lines from the single write. The **old** lines were nearer that write *by
accident* and scored SOUND. **The tool scored three wrong citations above three
right ones.**

So item 4 cannot be driven to zero, and anybody treating 170 as a work list
will repoint correct cells to make a number move. What the number is good for
is *surfacing candidates*; the verdict needs the cell's prose every time.

---

## 4. Item 7 — the push gate reaches 1 of 45 deny sites

**Found by being bitten three times in one session.** One batch was refused for
stale generated documents → fixed → re-pushed → refused for a missing
register-feed trailer → fixed → re-pushed → refused for an unrecorded Tier A
obligation. **Three full rebase-regenerate-retry cycles against a branch five
clones push to, to learn three facts that were all true at the same moment.**

`deny()` calls `sys.exit(1)`; there are **45** deny sites. Every check after the
first is "in the file" and never executes. Same shape as the registry tail and
as the probe whose arms I moved to the front last batch.

**`--preflight` runs all of them and reports all findings.** The enforcing path
is untouched — `COLLECT` is `False` at import and arm P1 is deliberately the
dumbest arm in the probe, because a reporting mode that quietly stopped the real
gate blocking would be worse than no mode.

**And it caught my own inversion:** the first version treated any `SystemExit`
as a crash. `main()` ends by exiting 0 to *allow* a push, so a **completed**
sweep raised it — and preflight reported a full sweep as partial, the exact
opposite of the error it exists to prevent. Arm P5 pins it.

I used it immediately: it told me `MASTER-PLAN.md` and `traceability-matrix.md`
were both stale **in one pass**, before I tried to push.

---

## 5. Gaps

| # | Gap | Severity |
|---|---|---|
| **1** | **`sairncash_usage`: the bar fills toward 200 and nothing enforces it** | **MODERATE**, new |
| **2** | 170 DRIFTED citations need per-cell prose reads; ~150 unread | **MODERATE** |
| **3** | Rows 82/845 owed to cc across **three** rounds | **MODERATE** |
| **4** | `sd_email_threats` `type` still uses `includes('phish')` | **LOW** |
| **5** | The cp1252 precondition: 237 tools | **MODERATE** (carried) |

### 1. A limit that is not a limit — MODERATE, new

`sairncash.html:1001` renders `Math.min((todayCount/200)*100,100)` as a filling
bar. **`grep` for any comparison of `todayCount` against a limit returns
nothing.** The 200 is a denominator in a progress bar, not a cap. A user
watching it fill would reasonably believe a limit exists; none does. Tiered C/C
because clearing the key buys nothing — the AI spend is gated server-side — so
this is a **product** question, not a security one, and it surfaced only because
tiering forced someone to say what the key is for.

### 3. Three deliveries, still unapplied — MODERATE

Now `docs/FOR-CC-rows-82-845-hank.md`, its own file, named for the holder.
**Row 82 is mine and it is live and unassigned, asking a reader to build
something that shipped `b66b1ac9` six days ago.** The file says plainly that a
fourth copy in a fourth document is not communication, and offers the
alternative.

---

## 6. What I will not claim

* **The rendered amber banner has not been seen in a browser by me.** The
  parsing is proven live; the UI state is pinned at source by arm E3.
* **The `sd_email_threats` `type` field is unchanged** — `includes('phish')`,
  same class of test, lower stakes, named rather than folded in.
* **I did not read the prose of the ~150 remaining drifted cells.**
* **Preflight is not a promise.** Its own clean output says so: it runs the
  checks as they are, and a check needing state a real push creates can still
  refuse later.
* **`sairncash`'s four tiers are my reads.** The B on `_sub` rests on the
  server-side verification in `api/sairncash/ai.js` being real; I read the
  comment asserting it and did not drive that endpoint.
* **The 33 repoints are correct citations, not improved tool scores.** 26 of
  them will be reported DRIFTED for ever and that is the tool's definition.
