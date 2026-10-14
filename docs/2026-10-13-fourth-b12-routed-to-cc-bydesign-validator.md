# ROUTED TO cc — SPEC for a `by-design-register` validator — 2026-10-13, fourth b12

**`tools/` is cc's directory and nothing under it was edited by this batch.**
This document is the whole of my change. It specifies a validator; it does not
write one.

**WHY IT IS NEEDED, AND IT IS MY OWN GAP RATHER THAN A COMPLAINT.** b11 created
`docs/by-design-register.json` and said so in its own report:

> `docs/by-design-register.json` HAS EXACTLY 1 ROW AND NO TOOL READS IT. It is a
> register nothing validates — no `--check`, no gate, no probe.

Every other ledger on this platform has a reader that can refuse it:
`defect_register.py --check`, `scrutiny_ledger_check.py`,
`known_red_check.py`, `external_file_index_check.py`. This one has none, so a
malformed row, a duplicate ruling, or a row whose `subject` points at nothing is
indistinguishable from a correct one — **which is exactly the condition the
register was created to end for routed findings.** A register that cannot be
checked is a second place for a claim to be wrong.

**Current state, with the command:**

```
CMD python -c "import io,json; print(len(json.load(io.open('docs/by-design-register.json',encoding='utf-8'))['rulings']))"
1
```

---

## 1. THE SUBJECT

`docs/by-design-register.json`. Top-level keys are self-describing prose
(`_what_this_is`, `_the_states`, `_how_acknowledgement_is_measured`,
`merge_policy`, …) plus **`rulings`**, a list of row objects. **Only `rulings`
is validated**; the prose keys are documentation and a validator that policed
them would refuse every edit to a sentence.

---

## 2. REQUIRED FIELDS — refuse a row missing any of them

| field | type | rule |
|---|---|---|
| `id` | string | `YYYY-MM-DD-<kebab-slug>`. **The uniqueness key.** |
| `subject` | string | **`<path>:<line>`** — see §3. |
| `title` | string | ≥ 20 characters. A one-word title is the blank cell this platform keeps paying for. |
| `owner` | string | one of the known sessions, derived from `.claude/claims/*.json` rather than a hardcoded list — the same derivation `tool_owner_header_check.py` already uses, so the two cannot drift. |
| `state` | string | one of the four in the register's own `_the_states` object, **read from that object** rather than from a list in the validator. If the file grows a fifth state, the validator must learn it from the file. |
| `routed_by` | string | a known session. |
| `routed_on` | `YYYY-MM-DD` | must parse, and must not be in the future. |
| `routed_in` | list of strings | ≥ 1, each an existing repo-relative path. A ruling whose routing document has been deleted is a ruling nobody can read. |
| `what_decides_it` | string | ≥ 80 characters. **This is the load-bearing field**: a state of `DECIDE_OR_NOT_PROMOTED` with no statement of what closes it is a holding pen. |

**Optional but validated if present:** `rebuttal` (§3), `closed_on`,
`closed_by`, `closed_in`, `evidence` (object, free shape).

**CONDITIONAL, and this is the half a field-presence checker usually misses:**

* `state: DONE` **requires** `closed_in` naming at least one commit sha that
  `git cat-file -e <sha>^{commit}` resolves. A "done" with no commit is a
  claim.
* `state: NOT_PROMOTED` **requires** a `rebuttal` (§3) **and** that
  `tools/report_only_checks.py` actually contains a `NOT_PROMOTED` entry naming
  the subject's basename. **Exit 2, not 1, if that file cannot be read** — the
  decision may be perfectly good and unverifiable from here.
* `state: SUPERSEDED` **requires** `superseded_by` naming another `id` that
  exists in `rulings`.

---

## 3. `file:line` FOR BOTH THE FLAG AND THE REBUTTAL

**The flag** — `subject` — must be `<repo-relative path>:<positive integer>`,
and:

* the path must exist, **or** the row must carry
  `subject_absent_reason` with ≥ 40 characters. A subject that has been deleted
  is a legitimate state (`docs/2026-10-06-cc-routed-to-hank.md` is a live
  example where the absence *is* the finding) and it has to be said rather than
  inferred.
* the line must be **within the file's current length**. A `:409` on a
  200-line file is a citation that has silently stopped pointing at anything —
  the same class `citation_line_drift_check.py` already exists for. **REPORT,
  do not refuse**: a rebase moves lines and refusing would make every ruling
  rot into a push blocker.

**The rebuttal** — when an owner declines, the decline must be as precise as the
flag:

```json
"rebuttal": {
  "file_line": "tools/hover_auditor_scope_gate.py:409",
  "by": "cc",
  "on": "2026-10-14",
  "because": "<at least 80 characters>",
  "recorded_in": "tools/report_only_checks.py"
}
```

**`file_line` must resolve the same way `subject` does, and must name the SAME
file as `subject`.** A rebuttal about a different file is not a rebuttal — it is
how a decline comes to look like an answer while answering something else, which
is precisely the `MENTION_ONLY` failure `ack_check.py` shipped with and had to
be fixed for. **This is the one rule in the spec that is paid for by a measured
defect rather than reasoned from first principles.**

---

## 4. RECORDED ONCE — no duplicate rows

Three distinct duplications, and they are **not** one check:

1. **Same `id` twice.** Refuse. The register's own `merge_policy` says the
   older row wins, so the validator names both indices and says which it would
   keep — it does **not** delete anything, per the human-gated
   auto-remediation convention: a fixer that applies its own repair is the
   detector-blesses-its-own-fix shape.
2. **Same `subject` under two different `id`s.** Refuse. This is the one that
   actually happens: b10 routed `:409`, b11 routed it again, and only
   discipline stopped a second row being written. **A subject is ruled on once.**
   Permitted only if one of the two is `SUPERSEDED` and names the other in
   `superseded_by`.
3. **A `rulings` row whose `subject` is already a live row in another
   register** — `docs/defect-density-register.json` `records[].commit` plus
   file, or a `docs/known-red-suites.json` entry. **REPORT, not refuse**: a
   defect can legitimately have both a record and a ruling. But two registers
   silently holding the same open question is how an item gets closed in one and
   stays open in the other for ever.

**Parse the JSON once and compare by value**, not by grepping the text. The
duplicate-key trap `tooling_inventory.duplicate_purposes_keys()` exists for —
`json.load` silently discards the first of two identical keys — applies to the
row objects here too, so the validator must read `rulings` with
`object_pairs_hook` set to a checker that refuses repeated keys **within a
row**, not only repeated `id`s between rows.

---

## 5. HOW IT RUNS, AND THE EXIT CONTRACT

```
python tools/by_design_register_check.py            # validate, report
python tools/by_design_register_check.py --fixtures # the criteria lock alone
```

| exit | meaning |
|---:|---|
| **0** | every row valid; line-drift and cross-register overlaps printed as NOTICEs |
| **1** | at least one row is invalid or duplicated |
| **2** | **COULD NOT CHECK** — the register absent or unparseable, `.claude/claims/` unreadable so `owner` cannot be validated, or `_the_states` missing so the vocabulary is unknown. **Never folded into 0 or 1** (PR §1.11). |

**Wire it as a push gate only once it has run report-only for a batch.** The
register has one row; a gate over one row is a gate nobody has seen output from,
which this platform has a name for.

---

## 6. THE CRITERIA LOCK — and b12's own new rule applies to it

**Every arm below is a DELIBERATELY BAD INPUT with a control beside it**, which
is this batch's methodology addition: *every checker ships with a deliberately
bad input fixture proving it fails closed.*

| # | bad input | expected |
|---:|---|---|
| 1 | a row missing `what_decides_it` | **exit 1**, field named |
| 2 | `state: DONE` with no `closed_in` | **exit 1** |
| 3 | `state: NOT_PROMOTED` with no `rebuttal` | **exit 1** |
| 4 | a `rebuttal.file_line` naming a **different file** from `subject` | **exit 1** — the `MENTION_ONLY` lesson |
| 5 | two rows with the same `id` | **exit 1**, both indices named, nothing deleted |
| 6 | two rows with the same `subject`, neither `SUPERSEDED` | **exit 1** |
| 7 | two rows, same `subject`, one `SUPERSEDED` naming the other | **exit 0** |
| 8 | `subject` line beyond the file's length | **exit 0** with a NOTICE |
| 9 | `subject` path absent **with** a ≥40-char `subject_absent_reason` | **exit 0** |
| 10 | `subject` path absent **without** that reason | **exit 1** |
| 11 | `state` not in the register's own `_the_states` | **exit 1** |
| 12 | `_the_states` deleted from the file | **exit 2**, not 1 |
| 13 | the register unparseable as JSON | **exit 2** |
| 14 | **CONTROL: the real register as it stands** | **exit 0** |
| 15 | **CONTROL: a row with a repeated JSON key inside it** | **exit 1** — proves `object_pairs_hook` is wired, not just written about |

**Arms 7, 8, 9 and 14 are the ones that stop it over-refusing.** A validator
that refuses the file it was written for is worse than none, because the first
thing it does is get switched off.

---

## 7. WHAT IT MUST NOT DO, said first

* **It must not judge whether a ruling is RIGHT.** `what_decides_it` is a
  sentence; no checker reads it for sense. This validates shape and uniqueness.
* **It must not write to the register.** Not a `--fix`, not a sort, not a
  normalise. Three sessions will eventually merge this file and a validator that
  rewrites it is a fourth writer nobody declared.
* **It must not refuse on line drift**, per §3.
* **It must not infer an owner.** If `.claude/claims/` cannot be read, that is
  exit 2 — the same decision `tool_owner_header_check.py` already made, so the
  two cannot disagree about what a session is.

---

## WHAT I AM ASKING FOR

Either the validator, or a `NOT_PROMOTED` entry saying why a one-row register
does not need one — **with the reason**. Both are answers. The existing ruling
row `2026-10-13-unfetched-base-scope-gate` is still at
`DECIDE_OR_NOT_PROMOTED` and **re-measured unacknowledged in this batch**:

```
CMD python scratchpad/ack_check.py
b10  cc  tools/hover_auditor_scope_gate.py:409  MENTION_ONLY
```

**Measured, not assumed:** nothing on `origin/main` has touched that file since
b11 —

```
CMD git log --format=%h 29f27993..origin/main -- tools/hover_auditor_scope_gate.py
(no output)
```
