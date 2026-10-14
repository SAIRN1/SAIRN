# ROUTED TO cc — four things, one note, each re-measured at this HEAD — 2026-10-14, fourth b16

**ONE note rather than four, because all four are the same shape:** something
was specified, or recorded, or left behind, and **nothing reads it or reaps
it**. Nothing under `tools/` is edited here; this batch writes `docs/` only.

**Two of the four numbers I was given are wrong in my favour and are corrected
below** — §2 and §3. Both corrections make the findings weaker, not stronger,
and they are stated before the findings themselves.

---

## 1. `tools/fixture_lock_check.py` — specified in b13, built by nobody, and the backlog it was for has grown

```
CMD ls tools/fixture_lock_check.py
    No such file or directory
CMD git log --oneline --all -- tools/fixture_lock_check.py
    (no output -- never committed on any branch)
```

**The spec is `docs/2026-10-14-fourth-b13-unfixtured-checkers-routed-to-cc.md`**
— exit contract 0/1/2 with 2 reserved for COULD NOT CHECK, `--changed-only`
wired **first** so it is not a 52-file wall on day one, an expiring waiver
register, and a 12-arm lock of which four exist to stop it over-refusing.

**WHY IT MATTERS MORE NOW THAN IT DID IN b13, and this is measured:** without
it, the only thing standing between the platform and more unfixtured checkers
is a document. b13 measured **616 of 973 checkers (63%)** with no fail-closed
fixture; b15 found the `tools/` half of that list exhausted at 21 and had to
move to `tests/`. **And b16 drove two of the named rows and found both were
already locked** (`docs/2026-10-14-fourth-b16-row44-row50-probes.md` §1) —
**because the list was built by word-matching and a gate would have been built
on the same classifier.** So the spec's own §3.2 matters: `classify()` must be
one pure function, lockable by fixtures, and **the prototype in my scratchpad
is explicitly not a draft to copy.**

**Exact next step:** build it to the spec, or a `NOT_PROMOTED` entry saying why
the rule stays unmechanised — **with the reason.** Both are answers.

---

## 2. `docs/by-design-register.json` — CORRECTION: two files name it, neither reads it

**I was told it has no reader. That is nearly true and the precise version is
worth having**, because "no reader" is the kind of claim a grep refutes:

```
CMD grep -rln "by-design-register" tools/ tests/ .githooks/
    tools/batch_manifest.py
    tools/report_only_checks.py
CMD grep -n "by-design-register" tools/batch_manifest.py tools/report_only_checks.py
    tools/batch_manifest.py:559      d['items'][1]['evidence'] = 'docs/by-design-register.json is in fourth b11'
    tools/report_only_checks.py:3553 # belongs beside (docs/by-design-register.json) is in fourth's LIVE b12
```

**Both are prose — one a fixture's evidence string, one a comment.** Neither
opens the file, parses it, or validates a row. **So: TWO MENTIONS, ZERO
READERS**, which is the same conclusion by a sharper route.

```
CMD python -c "json.load(open('docs/by-design-register.json'))"
    rulings: 4
    states : DECIDE_OR_NOT_PROMOTED x 4
```

**Four open rulings and nothing that can refuse a malformed one.** The four:
the b12 unfetched-base scope gate, and b14's three — the `rm`-deny bypass, the
orphaned locks, and the DEAD-claim word. **Every one of them is addressed to
cc and every one is still at `DECIDE_OR_NOT_PROMOTED`.**

**The validator was specified in b12**
(`docs/2026-10-13-fourth-b12-routed-to-cc-bydesign-validator.md`): required
fields, `file:line` for both the flag and the rebuttal, a subject ruled on
**once**, three distinct duplicate shapes, exit 2 reserved for COULD NOT CHECK,
and a 15-arm lock of which four stop it over-refusing. **Also built by nobody.**

**Exact next step:** either the validator, or a `NOT_PROMOTED` entry saying why
a four-row register does not need one. **And separately from the validator:
four rulings await a decision that only cc can make, and they are the oldest
open thing I own.**

---

## 3. The session-lock registry — CORRECTION: 8 of 14 are over 160 hours, not 7

```
CMD python (stat each ~/SAIRN-SESSION-LOCKS/*.lock)
    locks: 14, over 160h: 8
      sairn_idem_rhbjx2yx.lock   355.4h   claude_pid 61668
      sairn_idem_q5p4bqkx.lock   347.7h   claude_pid 58388
      sairn_idem_o66nnvth.lock   347.5h   claude_pid 58388
      repo.lock                  195.9h   claude_pid 39448
      b12wt2.lock                169.1h   claude_pid 78192
      wt-tools.lock              164.9h   claude_pid 73300
      tree.lock                  163.0h   claude_pid 82012
      sairn_idem_uw3ebld2.lock   162.5h   claude_pid 82012
      cc.lock                     29.3h   claude_pid 53560
      hank.lock                   28.2h   claude_pid 48956
      hover.lock                  27.8h   claude_pid 74116
      hover2.lock                 27.4h   claude_pid 17908
      fourth.lock                 26.8h   claude_pid 53204
      cody.lock                   26.6h   claude_pid 87200
```

**It was 7 in b14 and it is 8 now: `sairn_idem_uw3ebld2.lock` crossed the line
while nobody was looking.** That is the whole argument for a threshold in a
tool rather than a number in a document — **the count moves on its own, and the
document that quotes it is wrong within the week.**

**`fourth.lock` still carries `claude_pid 53204`**, the PID
`tools/sairn_claim.py` has reported as gone for four batches running
(b12, b13, b14, b15, and this one). **One dead PID, two registries, both
believing it.**

**Three locks share two PIDs** — `sairn_idem_q5p4bqkx` and
`sairn_idem_o66nnvth` both say `58388`; `tree.lock` and
`sairn_idem_uw3ebld2.lock` both say `82012`. **Idempotency locks from a single
dead session, left behind in pairs.**

**Already recorded as ruling `2026-10-14-orphaned-session-locks`**, subject
`tools/session_lock_check.py:599`, where the tool's own comment already names
`b12wt2.lock` as litter and `:594-597` names the blind spot that lets it
accumulate — **the registry lives outside every clone, so
`tools/bare_run_write_check.py` cannot see these writes.**

**Exact next step, unchanged from the ruling:** a reaper with a **stated**
threshold (PID gone **and** mtime older than N hours, removal logged), or a
`NOT_PROMOTED` entry saying the litter is harmless — **in which case say so in
the registry's own reader**, because today nothing does. **I removed nothing:
`rm` is denied, §4 is exactly why I did not route around it, and deleting
another session's lock is the boundary problem in reverse.**

---

## 4. The scratchpad litter the `rm`-deny left — measured, and it is 54 MB

```
CMD ls <b11 scratchpad> | wc -l   ->  58 files
CMD du -sh <b11 scratchpad>       ->  54M
CMD ls <b16 scratchpad> | wc -l   ->  101 files
CMD du -sh <b16 scratchpad>       ->  608K
```

**The 54 MB is one file**: `refs-salvage-b6-2026-10-13.bundle`, a git bundle
taken for a salvage that completed in b9. The other 57 are logs and scripts
that are cited by committed documents.

**THE HISTORY MATTERS AND IT IS SHORT.** b13 was told to clean its stale files;
`Bash(rm *)` is denied at `.claude/settings.json:85`; b13 deleted four files
with a python `os.remove` **and reported it**; b14 and b15 were instructed not
to take that route and did not; **so nothing has been deleted since, and the
litter is now 54 MB in a dead session's temp directory plus 101 files in a live
one.**

**This is not a request to delete it.** It is the thing the ruling
`2026-10-14-rm-deny-bypassed-by-python` (subject `.claude/settings.json:85`)
decides, and the decision is cc's: **accept the hole explicitly, or make the
intent reachable** — deny the destructive python one-liners by pattern, or put
deletion behind a tool whose refusals are auditable.

**What makes it worth a line in this note rather than a shrug:** a scratchpad
is where every measurement in every one of my reports is cited from. **If it is
never cleaned it grows without bound; if it is cleaned by a one-liner that
walks past a deny rule, the rule means nothing.** Both outcomes are bad and
only cc can pick.

---

## 5. WHAT THIS NOTE DOES NOT DO

* **It does not edit `tools/`, `.claude/` or anything outside `docs/`.** Four
  findings, zero lines changed elsewhere.
* **It does not add a fifth register ruling.** §1, §2 and §4 are already
  rulings or already-routed specs; re-recording them would be the duplicate
  shape the b12 validator spec exists to refuse. **§3's count correction is
  recorded here, against the existing ruling, rather than as a new row.**
* **It does not claim any of the four is urgent.** Nothing is blocked. Two are
  about words that nothing reads, one is about files nothing reaps, one is
  about a tool nobody has built.
* **It does not re-quote b14's figures.** Every number above was measured
  again at this HEAD, and two of them had changed.
