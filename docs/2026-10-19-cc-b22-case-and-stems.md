# b22: two filters that silently selected the wrong set, one stale anchor, and the paragraph for the other three agents

**cc, 2026-10-19.** Four fixes and one piece of text. Each item's one-line
concept is stated before its implementation, per the methodology item.

Three of the four are the same defect shape wearing different clothes: **a
filter that quietly selected the wrong set and then reported a clean result
over it.** Worth naming once rather than three times — a selection that
narrows silently is indistinguishable from a selection that found nothing
wrong.

---

## Item 1 — the contrast baseline could not see five of its own products

**Concept:** *match the full filename stem with hyphens intact, so a sub-app is
a product; do not treat a hyphen as a reason to drop a file.*

`product_files()` read:

```python
if stem == "stonedesk" or (stem.startswith("sairn") and "-" not in stem):
```

The hyphen clause did not narrow the list to products — it removed the five
**sub-apps**: `sairndental-book`, `sairndental-complaint`,
`stonedesk-catalog`, `stonedesk-hr`, `stonedesk-intake`.

**Why that was not a cosmetic miscount.** `docs/wcag-contrast-baseline.json` is
generated from this list and the push gate runs on **every** changed `.html`.
So the baseline's universe was narrower than the gate's, and the two sub-apps
carrying debt denied any push that touched them on **pre-existing** findings,
with no route but a skip.

Now `is_product_stem()`, a **prefix rule rather than a list**, so a future
`sairnfoo-bar` is covered the day it is added rather than the day somebody
remembers:

```python
return stem == "stonedesk" or stem.startswith("stonedesk-") \
    or stem.startswith("sairn")
```

**Measured, before and after.** `--static --all` went from 17 files to **22**.
The 8 findings are all in the two dental sub-apps and all pre-existing:

| finding | ratio | need |
|---|---:|---:|
| `sairndental-book .btn` `#fff` on `var(--p)` | 2.77:1 | 4.5 |
| `sairndental-book .slot.picked` `#fff` on `var(--p)` | 2.77:1 | 4.5 |
| `sairndental-complaint .btn` `#fff` on `var(--p)` | 2.77:1 | 4.5 |
| `sairndental-book .slot:hover` `var(--pd)` on `var(--pt)` | 3.57:1 | 4.5 |
| `sairndental-book .msg.ok` `var(--pd)` on `var(--pt)` | 3.57:1 | 4.5 |
| `sairndental-complaint .msg.ok` `var(--pd)` on `var(--pt)` | 3.57:1 | 4.5 |
| `sairndental-book inline <button>` `#fff` on `var(--danger)` | 3.76:1 | 4.5 |
| `sairndental-book inline <button#bk-add-photo-btn>` `var(--pd)` on `#fff` | 4.10:1 | 4.5 |

**The gate after re-recording:** `sairndental-book` exit 0 with
`BASELINE DEBT STILL OUTSTANDING: 6`, `sairndental-complaint` exit 0 with 2,
`stonedesk-catalog` exit 0 with 0.

**AND THE RATCHET IS INTACT, which is the arm that matters.** A copy of
`sairndental-complaint.html` with a NEW below-AA rule planted
(`.cc-b22-ratchet` at 2.54:1) still **denies**, exit 1, while its 2 baselined
findings are accepted. Accepting debt did not loosen the gate.

### THE PLATFORM'S ACCEPTED CONTRAST DEBT GOES 0 → 8, AND NOTHING REGRESSED

Read this before concluding the baseline got worse. The file was at
`total: 0` when this batch started — fourth drove the 17 root products to zero
across b29–b33. The 8 are findings that **always existed** and that `--all`
could not see. The number going up is the instrument improving, not the
platform decaying. **Fixing them is the follow-up**, and fourth's b29 pattern
(darken the brand surface so `#fff` on `var(--p)` clears 4.5) is the known fix
for six of the eight.

### A provenance line that could not change, so it was wrong

`--baseline-write` wrote the literals `"written": "2026-10-19"` and
`"written_by": "fourth b30"`. **Every** re-record claimed fourth's b30
authorship, whoever ran it and whenever. Both are now derived — the date from
the local clock (not UTC: `tools/sairn_stale_snapshot_scan.py` exists because
UTC derivation dates an evening's work tomorrow), the author from the clone's
own identity marker, and `"unknown (this clone has no session-identity
marker)"` rather than a guess. A `files_scanned` list was added so the
baseline records its own universe — the thing that was wrong here.

Criteria lock **58/58**, up from 41/41. The new arms assert all five sub-apps
are products, all four root products still are, five non-products still are
not, a future `sairnfoo-bar` is, `stonedeskish` is not, and one **ablation**
arm that fails on the pre-fix expression.

---

## Item 2 — `--agent H1` skipped the nonce check and still printed CLEAN

**Concept:** *answer "is this agent selected?" in exactly one place,
case-insensitively, so the row filter and the nonce gate cannot disagree.*

H1's b63 finding, and the root cause is not the case-sensitivity itself — it is
that **one question had two answers a hundred lines apart**:

```python
labels = [... if BP.BOARD_TOKEN[l] in agents or l in agents]   # label OR token
nonce  = nonce if (agents and token in agents) else None       # token ONLY
```

`BOARD_TOKEN['H1']` is `'h1'`. So `--agent H1` matched the first expression on
the **label** and failed the second on the **token**: the row was checked, the
nonce was dropped, and the summary printed

> `CLEAN: ... and the nonce crossed both ends`

because that sentence was keyed on a nonce having been **supplied** rather than
**checked**. That substitution is what made the defect read as a verified pass.

Three changes:

1. **One expression, `selects(label, token, agents)`**, called by both sites,
   case-insensitive on both label and token, whitespace tolerated.
2. **The CLEAN summary's nonce clause now derives from `nonce_checked`**, a
   count, and names the number of rows. If a nonce was supplied and checked on
   nothing, it says so loudly and says it should be unreachable.
3. **An `--agent` matching nothing is `COULD NOT RUN`, exit 2**, naming the
   valid names in both forms. Before b22 it fell through to
   `0 FINDING(S) across 0 agent(s)` and then printed CLEAN at exit 0 — a
   verdict over an empty set, the same silent-skip family, found while fixing
   the first one. Driven: `--agent zzz` → exit 2.

### H1's negative control, made permanent, and ablated

The regression arms replace the live registry and Drive mount with a synthetic
H1 row and board, so the control runs on any clone, forever, with no network.

**The arm that matters is not "uppercase works" — it is that uppercase and
lowercase give the SAME ANSWER.** A fixture asserting only the uppercase
verdict would pass again the day the two expressions drift apart the other way.

**Ablation.** `selects()` reduced to the pre-b22 expression
(`return token in agents`) in an isolated copy: **36/42, six arms fail**,
including the headline one. The control has teeth.

**Driven live, with a nonce never written to any row:**

| invocation | exit | verdict |
|---|---:|---|
| `--agent H1 --nonce CC-B22-NONCE-NEVER-WRITTEN-CONTROL` | 1 | FINDING |
| `--agent h1 --nonce` (same) | 1 | FINDING |

Byte-identical output. Pre-fix, the first was a false CLEAN.

**And the positive direction on live data**, which is the half that proves the
tool is not just refusing everything: hover2's current row carries
`H2B63-9a2f84dd`, and `--agent H2` and `--agent h2` both return exit 0,
`CLEAN ... the nonce crossed both ends on 1 row(s)`.

### Two fixture arms that were vacuous, caught before they landed

`check()` compares `bool(got) == bool(want)`, so a **non-empty list is True
whatever is in it** — `check(name, [False, False], [False, False])` passes
without testing anything. Two arms were written that way in this batch and
rewritten as `all(...)` / `any(...)` booleans before commit. Noted because it
is discipline 8 arriving inside the fix for discipline 8.

---

## Item 3 — the preflight probe's injection anchor had gone stale

**Concept:** *inject at the LAST occurrence of the anchor, and refuse rather
than silently inject nothing if it is absent.*

`tests/run_push_gate_preflight_probe.py` was RED 3 of 13 (E1, E2, E3), every
failure reported as `RAISED SyntaxError` with no explanation, named as
UNVERIFIED in b21 and diagnosed but not fixed there.

Root cause, now fixed: `_drive()` did
`source.replace("if __name__ == '__main__':", inject, 1)`. That anchor occurs
**twice** in `tools/sairn_push_gate_hook.py` and the **first** is inside a
double-quoted string on a real code line —
`_src.rindex("if __name__ == '__main__':")`, part of the hook's own WIRING
selftest arm, **added after this probe was written**. A multi-line injection
landed inside that literal, left it unterminated, and `compile()` raised before
any arm could run.

**Measured, not read** — both expressions applied to the real hook source:

```
OLD replace(...,1)   SyntaxError: unterminated string literal (line 4849)
NEW rfind            compiles
anchor occurrences: 2
```

A **stale-anchor defect, discipline 8**: nothing announced the day the probe
stopped testing anything. The hook's own selftest already used `rindex` for
exactly this reason and the probe did not. The fix also **refuses** when the
anchor is absent, because an injection that silently does nothing would make
every arm below pass while judging an unmodified gate.

**13 passed, 0 failed.**

---

## Item 4 — re-driving H1's b61 claim found the verdict right and the REASON wrong

**Concept:** *re-run the original claim through the corrected tool and report
what it actually says, including when what it says is overstated.*

`--agent H1 --nonce H1-NONCE-1792420981`, both cases, exit 1, identical:
the nonce is **not** in H1's registry row.

**But that verdict's stated reason was false.** The old text said flatly:

> *the WRITE did not land -- this is a finding about `sairn_status.py`, not
> about the board.*

Measured: `H1-NONCE-1792420981` is absent from the row **and present on the
Drive mount** in `SAIRN-handoff-H1-b61.md` and `SAIRN-report-H1-b61.txt`. That
write landed. H1's row has simply moved on three batches (it now reads
`h1 b64: repro for cc, nonce intentionally absent from this task string`).

**A row holds one task string, so this check cannot distinguish "never
written" from "written and since superseded".** That is a could-not-tell about
*which*, so the finding now names both causes and prints the row's own
`updated` stamp, which is the one piece of evidence that separates them. Three
new arms lock it, one of them an ablation that fails on the pre-b22 wording.

**So the answer to item 4:** the bridge claim for b61 is **not re-verifiable**
— the row it was about has been overwritten, and no tool can recover a
superseded task string. What IS verified is the live bridge **now**, in both
directions, by the two tables in item 2. A verdict about b61 specifically would
need a nonce from b61's own row, which no longer exists.

Criteria lock **45/45**, up from 39/39.

---

## Item 5 — the paragraph to paste into hank, cody and fourth

Not run on their sessions. Handed over as text, below and in the handoff.
