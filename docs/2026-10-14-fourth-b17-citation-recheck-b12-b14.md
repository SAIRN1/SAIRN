# METHODOLOGY — b12–b14 citations re-derived, and the register duplicates measured — 2026-10-14, fourth b17

**Two halves. The first fixed two citations. The second could not reproduce the
premise it was given, and says so with the command.**

```
CMD git -C <repo> pull --rebase origin main        (platform repo pulled first)
```

---

## PART 1 — every `file:line` in my b12, b13 and b14 documents

```
CMD python scratchpad/cite_recheck_b16.py <15 documents>      ->  exit 1
    79 citation(s) across 15 document(s); 4 unresolvable
```

**75 of 79 resolve to the text their sentence claims. Four do not, and they
split two–two into "correctly absent" and "a real change moved them".**

### 1.1 Two are CORRECTLY absent — illustrative names, and the doc already says so

```
  !! tools/bar_gate.py:140  FILE ABSENT
  !! tools/foo_gate.py:88   FILE ABSENT
      -- both in docs/2026-10-13-fourth-b12-ack-recheck.md
```

Both are quoted **from the ack checker's own output**, in the block headed
`EXCLUDED, not on disk (illustrative or proposed)`. They are the checker
demonstrating its own exclusion rule with two invented names. **Nothing to fix:
a checker that printed a real path there would be the defect.**

**But the recheck script cannot tell that**, and it should not guess — so this
is the first thing the §3 tool request has to handle: **an expected-absent
citation needs to be declarable, or every future run reports the same two.**

### 1.2 Two MOVED, by a real change, and both are now fixed

```
  !! .claude/settings.json:186  LINE OUT OF RANGE (file has 174 lines)
      -- docs/2026-10-14-fourth-b13-hook-audit-routed-to-cc.md
  !! .claude/settings.json:185  LINE OUT OF RANGE (file has 174 lines)
      -- docs/2026-10-14-fourth-b14-routed-to-cc.md
```

**The file lost 13 lines because the hook group was deleted.**

```
CMD grep -n '"hooks"\|_permissions_note\|_hooks_note' .claude/settings.json
    166:  "hooks": {},
    171:  "_permissions_note": "Mechanical permission rules, 2026-10-13, cc batch b5 …
    172:  "_hooks_note": "NO HOOKS, AND THE EMPTY OBJECT IS COMMITTED ON PURPOSE …
```

**AND THE TWO FIXES ARE DELIBERATELY DIFFERENT, because the two citations are
different kinds of thing:**

| document | citation | fix | why this fix |
|---|---|---|---|
| b14 routed-to-cc | `:185` → **`:171`** | **renumbered** | the claim is **still live** — the `rm`-deny hole is an open ruling, and `_permissions_note` still says what the document quotes. A live claim gets a working pointer. |
| b13 hook audit | `:166-180`, `:167`, `:169`, `:173`, `:174`, `:186` | **annotated, NOT renumbered** | **the subject no longer exists.** A citation to a deleted block cannot be pointed at a line, and renumbering it to `:166` (`"hooks": {}`) would make the document appear to audit an empty object it never saw. |

The b13 document now opens with a `SUPERSEDED IN PART` note naming the commit
that removed the hook (**hank's merge `3857890a`**), the new line numbers, and
the consequence: **its §4.3 finding — that nobody has ever seen the `compact`
matcher fire — now closes by deletion rather than by evidence.**

**THE RULE THIS ESTABLISHES, and b16 only had half of it:** when a citation
breaks, **first ask whether the SUBJECT still exists.** If it does, renumber.
**If it does not, annotate** — because the alternative is a document that
quietly claims to have reviewed something it could not have.

### 1.3 The 75 that are correct

Checked by reading the text now at each line, not by confirming the line
exists. Spot sample, with what is there today:

| citation | text now at that line |
|---|---|
| `.claude/settings.json:64` | `"Bash(python *)",` |
| `.claude/settings.json:85` | `"Bash(rm *)",` |
| `tools/session_lock_check.py:599-602` | the litter comment naming `b12wt2.lock` |
| `tools/hook_integrity_check.py:366` | `"""Is \`hooks\` present and EMPTY in this clone's settings.json?` |
| `docs/hook-manifest.json:12` | `"tools": {` |
| `docs/2026-10-13-per-gate-skip-design.md:119` | the hook-integrity non-skippable line |

**`tools/hook_integrity_check.py:366` is worth one more sentence:** b13 routed
that docstring as disagreeing with its code, because `:393` accepted the one
authorised hook. **The hook is now gone, so the docstring is accurate again and
the finding has closed itself.** Reported rather than left as an open route.

---

## PART 2 — the duplicate register summaries: THE PREMISE DOES NOT REPRODUCE

**I was told: 6 duplicate register summaries, 4 of them without
`superseded_by`, and to pick survivors and run `--supersede` if I own the
register.** Measured, in order:

```
CMD grep -m1 "^# OWNER:" tools/defect_register.py ; owner map lookup
    tools/defect_register.py -> cc
CMD python tools/defect_register.py --check                   ->  EXIT 0
    SUPERSEDED (4): retired from the duplicate test, each with a survivor that
      EXISTS and is an ancestor of origin/main. Not deleted -- append-only.
    OK: 553 record(s) … every commit resolves and every field is in vocabulary.
      4 by subject.
CMD python -c "records carrying superseded_by"                ->  4
    88d7543b2698 -> f2ee7be0d6da   8ae20da10239 -> 6a2690bec035
    e90d8775c7b2 -> d051c89faa16   f13f4f4982d3 -> 7ed27c5e78fa
```

**THE FOUR ARE THE ONES THAT HAVE `superseded_by`, NOT THE ONES THAT LACK IT —
and the register's own validator exits 0 with no duplicate finding.** So
"4 without `superseded_by`" is not the state of this file today. **I did not
run `--supersede`**: the register is cc's, and retiring four correctly-live
records to match a number would shrink a defect denominator that other figures
are divided by.

### 2.1 WHAT IS REALLY THERE: exactly ONE live duplicate, and its cause is mojibake

```
CMD python -c "live records identical on (commit, app, layer, summary[:60])"
    1 group:  x2  ('7bc26782e533', 'sairnvet', 'product',
                   'sairnvet.html searchDrugs() rendered a green "Verified" badg')
```

Two live records, same commit, same app, same layer, same severity
(`critical`), same method (`code-review`), same phase (`design`), same files,
same line counts. **Diffed field by field, exactly two fields differ — and the
difference is an encoding corruption:**

```
A summary: … `d.needsReview ? 'Needs Review' : '✓ Verified'` …
B summary: … `d.needsReview ? 'Needs Review' : 'âœ“ Verified'` …
```

**`âœ“` is `✓` as UTF-8 bytes decoded as cp1252.** The same two characters
differ inside `contributing_factors`. **Everything else is identical.**

### 2.2 WHY THIS MATTERS MORE THAN A COUNT

1. **One critical defect is counted twice** in a register whose whole purpose
   is *"a real denominator"*.
2. **The duplicate test cannot see it**, and that is not an oversight in the
   test — **the two summaries genuinely differ as text.** A dedup check that
   compares strings is defeated by a mojibake round-trip, silently, and reports
   OK.
3. **It is the same encoding fault as `tools/batch_manifest.py:386`**, which
   still crashes `--close` on a non-ASCII first line and which every one of my
   batches works around with `PYTHONIOENCODING=utf-8`. **Two tools, one cause,
   and this one corrupts data instead of crashing** — which is the worse of the
   two failure modes.
4. **`--supersede` CANNOT EXPRESS THE FIX.** `superseded_by` names a **survivor
   SHA**, and both records carry the **same** commit `7bc26782e533`. **There is
   no SHA that distinguishes the twin from the survivor**, so the mechanism
   that exists for duplicates cannot retire this one. That is a structural
   limit, not a missing keystroke.

### 2.3 ROUTED TO cc — three things, in this order

1. **Decide the survivor and retire the twin.** The record with `✓` is the
   uncorrupted one; the `âœ“` record is the artefact. **Retiring it needs
   either a per-record id or a `superseded_by` that can name a record rather
   than a SHA** — §2.2 item 4.
2. **Make the dedup test encoding-blind**, or at least report a near-duplicate:
   compare summaries after normalising, or key on
   `(commit, app, layer, severity, files)` which was identical here. **A dedup
   check defeated by two bytes is a dedup check with a blind spot, and today it
   reports OK.**
3. **Find where the mojibake entered.** `--add` is the only writer. If one
   session's `--add` round-tripped a UTF-8 summary through a cp1252 stdout,
   **every record added that way carries it**, and 1 of 553 is only what a
   single exact-twin comparison can see.

**What I did NOT do, and why:** no `--supersede`, no edit to
`docs/defect-density-register.json`, no `--reseat`. The register and its tool
are cc's; `--check` says the file is valid; and the one real duplicate cannot
be retired by the mechanism I was pointed at. **Routing it with the evidence is
the whole of what I can honestly do here.**

---

## PART 3 — the tool request, extending b16's

b16 asked cc for a `--read-the-line` mode on
`tools/citation_line_drift_check.py`. **Two additions, both learned this
batch:**

| addition | why |
|---|---|
| **an EXPECTED-ABSENT declaration** — e.g. a `citations-expected-absent.json`, or an inline marker a document can carry | `tools/foo_gate.py:88` and `tools/bar_gate.py:140` are illustrative names quoted from a checker's own output and will be "unresolvable" for ever. **Without this, every run has two findings nobody will act on, and a report with permanent noise stops being read.** |
| **a SUBJECT-EXISTS test before suggesting a renumber** | §1.2 is the rule: if the cited block is gone, the fix is an annotation, not a new line number. **A tool that renumbers a citation onto whatever now occupies the line is worse than one that only reports.** |

**And the banner must still say what it cannot do:** an off-by-one, and a
citation whose subject moved to a different file, both need a reader.

---

## WHAT THIS DOCUMENT DOES NOT CLAIM

* **It does not re-derive b15's citations.** b16 did that (45 checked, 1 fixed)
  and they are not re-checked here.
* **It does not check prose claims without a line number.**
* **It does not prove the b13 hook audit was right when it was written.** It
  records that its subject has been deleted and that its line numbers refer to
  a file that no longer exists in that shape.
* **It does not audit the other 552 register records for mojibake.** One exact
  twin was found by an exact-twin test; **that is a floor, and §2.3 item 3 is
  the work that would give a real number.**
* **Four unresolvable of 79 is not an error rate.** It is one measurement of
  one session's documents.
