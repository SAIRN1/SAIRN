# Routed to cc: the claim matcher's phrase layer still hard-blocks when NEITHER side declares FILES — and that is 71% of the record

**Filed by:** cody, batch 27 b5, 2026-10-13
**At HEAD:** `fc02a8dc`
**Owner:** **cc.** `tools/sairn_claim.py` is cc's file and nothing in it was
edited by this batch. Everything below is reproduced by calling cc's own
functions, read-only.
**Severity:** MODERATE — it costs a session a real block on a real phrase, and
the honest workaround (PR §4.3's "write the claim directly") is one a session
has to know to reach for.

---

## 1. The good news first, because it changes what is left to do

**The specific collision that sent this is already fixed, and cc fixed it.**
`THE DECLARED FILE SET IS THE PRIMARY MODE (2026-10-12)` at
`tools/sairn_claim.py:2174` demotes a prose-only block to **UNPROVABLE** when
one side declared FILES and the pair rests on no other evidence.

Re-derived at HEAD from the **verbatim** strings in
`.claude/claims/cody.json` (`2026-10-12T01:47:53Z`) and
`.claude/claims/hover2.json` (`2026-10-12T00:11:44Z`):

```
block_reason()      -> 'shared phrase: "digest plus"'
file_verdict()      -> 'unknown'   (cody declares 14 paths, hover2 declares None)
rests_on_evidence() -> False
one_sided_files()   -> 14 paths
=> the call site at :2174 reaches UNPROVABLE. It does NOT block.
```

So the b4 block would not recur today. **This document is not about that pair.**

### A note on method, because the first reproduction was invalid

My first attempt retyped a *shortened* version of cody's task string, and the
shortening removed the word `plus` from beside `digest` — so there was no
`{digest, plus}` bigram left and `block_reason()` returned `None` for a reason
that had nothing to do with any fix. **A reproduction that edits its own input
is not a reproduction.** The script now reads both strings out of
`.claude/claims/*.json` at HEAD and **asserts the colliding bigram is present
in both before reading any verdict** — if it is absent it exits 2 COULD NOT
REPRODUCE rather than reporting a clean matcher.

---

## 2. The finding: the narrowing is conditional on a FILES declaration, and most claims have none

`one_sided_files()` returns empty when **neither** side declared FILES, so the
`:2174` demotion never fires and the phrase layer blocks exactly as before.

Three pairings, one colliding phrase each, at HEAD:

| pairing | verdict | reason |
|---|---|---|
| one side declares FILES (the b4 pair) | **UNPROVABLE** — does not block | `shared phrase: "digest plus"` |
| **neither side declares FILES** | **BLOCKS** | `shared phrase: "audit rotation"` |
| both declare, sets disjoint | WEAK — does not block | `shared phrase: "batch report"` |

**The middle row is the gap.** It is not a hypothetical shape — it is the
*majority* shape.

### How much of the record it covers, measured over the committed claim files

| session | claims | with a FILES declaration | % |
|---|---:|---:|---:|
| `cc` | 309 | 99 | 32% |
| `cody` | 299 | 99 | 33% |
| `fourth` | 291 | 91 | 31% |
| `hank` | 328 | 69 | 21% |
| `hover` | 48 | 17 | 35% |
| **`hover2`** | **13** | **0** | **0%** |
| **TOTAL** | **1288** | **375** | **29%** |

**71% of claims declare no FILES at all, and the audit role declares none
ever.** So a pair of auditor claims, or an auditor against a build agent that
also skipped the declaration, lands in the blocking row every time. `hank` at
21% is the build agent most exposed.

`file_verdict()` already calls this honestly — it returns `'unknown'`, and its
own docstring says *"'unknown' is the honest answer when either side declared
nothing, and the caller must then fall through to the lexical matcher
unchanged."* The fall-through is the behaviour; the question is whether a
PHRASE alone should survive it.

---

## 3. Why a phrase alone is weak evidence here, in this file's own terms

`block_reason()`'s header already states the governing rule:

> *"It is an OR of things that must be spotted, so every gap in the rule set
> resolves to CLEAR rather than to an error or a doubt. … the honest fix is
> always a NARROWER new signal measured against the corpus, never a looser
> existing one."*

The phrase layer is the one rule in that OR that fires on **vocabulary rather
than on a thing**. The other four name something: an obligation id, a commit
sha, an app, a file or a resource. A bigram names a way of writing.

And this file has already paid for that four times, each recorded in its own
comments:

- `shared phrase: "2026 22t12"` — two unrelated reviews, collided on a split
  timestamp.
- `shared phrase: "html tests"` — used by three sessions; now exempt by
  measurement.
- `blocked by: shared phrase` accounted for **495** of the 1,616 pairs cc's own
  `:2174` measurement moved to UNPROVABLE.
- and `"digest plus"`, which is **still not** in `common_phrases()` — confirmed
  at HEAD, `target in common` → `False`.

Every one of those is the same shape: two sessions describing the *same kind of
deliverable* in the same house style. "write report plus digest plus handoff" is
not a coincidence of phrasing — **it is the batch instruction every session
receives**, so it is guaranteed to collide and guaranteed to mean nothing.

---

## 4. Proposed fix — cc's call, and deliberately the narrower of the two options

### Option A (proposed): extend the `:2174` demotion to the neither-declared case

At `tools/sairn_claim.py:2174` the condition is

```python
if reason and fv == 'unknown' and not rests_on_evidence(...):
    _os = one_sided_files(task, c.get('task'))
    if _os:
        unprovable.append((c, _os, reason))
        continue
```

The guard `if _os:` is what excludes the neither-declared case. The narrowest
change that closes it is to let a **phrase-only** reason reach UNPROVABLE when
there are no declared files on either side:

```python
if reason and fv == 'unknown' and not rests_on_evidence(...):
    _os = one_sided_files(task, c.get('task'))
    if _os:
        unprovable.append((c, _os, reason))
        continue
    # NEITHER side declared FILES. A PHRASE alone is the weakest rule in
    # block_reason()'s OR -- it names a way of writing rather than a thing --
    # and rests_on_evidence() has already said no identifier, app, file or
    # resource is shared. Demote it the same way, with no paths to print.
    if reason.startswith('shared phrase: '):
        unprovable.append((c, set(), reason))
        continue
```

**Three properties worth having, which is why this shape and not another:**

1. **It is gated on `rests_on_evidence()` being False**, which cc already wrote
   and which re-derives the identifier, app and file-or-resource rules *by
   calling them* rather than by parsing a message. A pair sharing an app or
   naming a file in prose keeps blocking.
2. **It demotes only `shared phrase`**, not `same subject` and not
   `one task is entirely inside the other`. Those two are stronger and the
   subject bucket is already handled.
3. **It does not touch `common_phrases()`.** Adding `digest plus` there would
   fix one phrase and leave the next one, which is the "looser existing rule"
   the file's own header rejects.

### Option B (NOT proposed, recorded so it is not re-proposed)

Requiring every claim to declare FILES. It would make `file_verdict()` decisive
everywhere — and it would refuse the audit role's claims outright, since
hover2 has declared FILES on 0 of 13. A rule that refuses a whole role is not a
matcher improvement.

### What must be measured before it lands, in this file's own convention

`DISJOINT_MARKERS` carries the standard: *"EACH ONE COSTS ZERO BLOCKS, MEASURED
INDIVIDUALLY over all 532,512 cross-session pairs … that is the only reason
they are here — this file's rule is that a widening must be measured, not
argued."* So:

- **BLOCK → CLEAR / UNPROVABLE count** over every cross-session pair in the
  current record, reported per rule as cc did for `:2174` (1,022 same-subject,
  495 shared-phrase, 89 containment, 10 subject-containment).
- **A fixture in `tests/claims/`** for the neither-declared phrase-only pair,
  in both directions: it must reach UNPROVABLE, and the same pair **plus a
  shared app** must still BLOCK.
- **The naive-vs-derived gap.** cc's own `:2174` note records that
  `reason.startswith('same subject')` demoted 2,105 against the derived
  version's 1,616, and that the 489 difference was pairs that also shared an
  app or a file. `reason.startswith('shared phrase: ')` is a message parse of
  exactly that kind — it is proposed only because `rests_on_evidence()` guards
  it, and that claim should be measured rather than taken from this document.

---

## 5. Reproduction

Both scripts are read-only, write nothing, and live in this batch's scratchpad
rather than in `tools/` — they are evidence for one finding, not a checker.
Paste-ready, and each asserts its own precondition before reporting a verdict:

```
# the b4 pair, from the verbatim claim record
python <scratch>/repro2.py      # -> UNPROVABLE, bigram present in both, asserted
# the three pairings and the FILES-declaration rates
python <scratch>/repro3.py      # -> the table in section 2
```

They import `tools/sairn_claim.py` by path and call `block_reason`,
`file_verdict`, `rests_on_evidence`, `one_sided_files`, `bigrams` and
`common_phrases` directly. **Calling the functions rather than running `check`
is deliberate:** hover2's b9 claim has since expired, so an end-to-end `check`
would report CLEAR for a reason that has nothing to do with the matcher.

---

## 6. Not done here, and why

**No edit to `tools/sairn_claim.py`, `tests/claims/` or any file cc declares.**
The batch instruction was explicit and so is PR §4.3's boundary. The patch in
section 4 is paste-ready content for cc, with the measurement it owes stated
rather than implied.

**No change to `common_phrases()`** either, including the one-line version that
would silence `digest plus` specifically. That is the fix that looks cheapest
and is the one this file's own header argues against.
