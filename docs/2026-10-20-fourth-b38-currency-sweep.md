# Currency sweep — fourth's own skills, tools, methodology and rules

**fourth / ted, batch b38.** Started 2026-10-19, written 2026-10-20 — **the
batch spans the date boundary, and new files in it are dated by the day they
were written rather than the day the batch opened**, because a handoff is found
by the date in its filename.

**THE SIX STANDING RULES SWEPT, as named in the dispatch:** silent mode;
wrap-up at 80% real context; digests 30 lines max; SQL in files; the done-line
format; builder/auditor separation.

**SCOPE BOUNDARY, APPLIED AND NOT NEGOTIATED.** The dispatch said *fix only
your own items; for anything shared (under `~/.claude`, or `tools/`), REPORT it
and never edit it.* **Nothing under `~/.claude`, `.claude/skills/` or `tools/`
was edited in this batch** — `git show --name-only` on every b38 commit is the
check. Four findings below are in shared files and all four are reported with
pasteable text and left alone.

**I also treated `CLAUDE.md` as shared and did not edit it**, even though it is
in neither named directory. It is the primer all four build agents read, the
dispatch said *your own* items, and a currency sweep is the wrong vehicle for a
unilateral change to a shared standing document. That is a judgment call and it
is stated rather than silently made — §5.1 carries the pasteable text.

---

## 0. THE RESULT IN ONE LINE

**FOUR OF THE SIX RULES ARE NOT WRITTEN DOWN ANYWHERE A FRESH SESSION READS,
and my own b36 breached two of them — measured, not recalled.**

| rule | written down? | fourth compliant? |
|---|---|---|
| silent mode | **YES** — `CLAUDE.md` *"Response style"* | **yes** |
| builder/auditor separation | **YES** — `CLAUDE.md` + `docs/2026-09-15-hover-auditor-separation-enforcement.md` | **yes**, 0 commits touch the auditor tree |
| **wrap-up at 80% real context** | **NO** | **NO — b36 wrapped at 83.5%** |
| **digests 30 lines max** | **NO** | **NO — 8 of 8 of my digests exceed it, b36 by 10×** |
| **SQL in files, digest gives only the path** | **NO** | **NO — b36's digest embedded the file verbatim** |
| **the done-line format** | **NO** | **yes**, b37's final message was `done b37 <id>` |

---

## 1. WHERE THE FOUR UNWRITTEN RULES ARE *NOT*

Searched, with the patterns, so the absence is falsifiable rather than asserted:

    grep -rln "80%"                 CLAUDE.md docs/SAIRN-PROCESS-RULES.md \
                                    docs/2026-09-13-cross-domain-disciplines.md
    grep -rln "30 lines"            (same three)
    grep -rln "wrap up at|wrap-up at"   (same three)
    grep -rln "done b[0-9]|done-line"   (same three)

* **`CLAUDE.md`** — no match for any of the four.
* **`docs/SAIRN-PROCESS-RULES.md`** — the one `30 lines` hit is *"1,230 lines
  of it were on an unmerged branch"*, a coincidence. No threshold, no digest
  shape, no done-line.
* **`docs/2026-09-13-cross-domain-disciplines.md`** — no match.
* **`.claude/skills/` (34 skills)** — the only `80%` outside the auditor tree is
  `sairn-client-facing-design/SKILL.md`: *"usually 80%+ of what's on screen"*,
  about neutral colours. Unrelated.

**AND THE ONE SKILL WHOSE WHOLE JOB THIS IS SAYS NOTHING ABOUT ANY OF IT.**
`.claude/skills/sairn-session-handoff/SKILL.md` has 17 headings and **no
section on the digest at all** — not its length, not its sections, not that SQL
belongs in a file. Its `## When to write one` reads:

> *"Proactively, before capacity runs low — never wait for a hard cutoff."*

**No number.** That is a rule enforced by remembering, which is the exact shape
`docs/tier-a-reviews.json`'s own header objects to in a different domain:
*"which is a rule enforced by remembering."*

**THE 80% FIGURE DOES EXIST IN WRITING — ON THE AUDITORS' SIDE ONLY.**
`.claude/skills/sairn-hover-auditor/` carries it, and hover2's live status row
cites an *"80% wrap-up threshold"*. **So the auditors have a written threshold
and the four build agents do not.** That asymmetry is not the separation
boundary working; it is one half of the platform having written down a rule the
other half is also expected to follow.

---

## 2. MY OWN BREACHES, MEASURED

### 2.1 The 80% wrap-up — b36 ran past it

`CONTEXT` lines from my own digests, which is the per-batch record:

| batch | context at wrap |
|---|---|
| b33 | 31.9% |
| b34 | 53.2% |
| b35 | 69.3% |
| **b36** | **83.5% — PAST THE THRESHOLD** |
| b37 | 30.5% (a new session) |

**One breach in five, and b36 is also the batch that was wrapped up on
instruction** — i.e. the wrap was triggered by Michael noticing, not by me
watching a number. That is the failure mode of an unwritten threshold exactly:
it holds until the one time it matters.

### 2.2 Digests 30 lines max — 8 of 8 over, and the trend is the wrong way

    for f in SAIRN-digest-fourth-b3*.txt; do wc -l < $f; done

| b30 | b31 | b32 | b33 | b34 | b35 | b36 | b37 |
|---|---|---|---|---|---|---|---|
| 103 | 111 | 88 | 156 | 151 | 125 | **319** | 209 |

**Every one exceeds 30. b36 exceeds it by more than ten times.** And across the
platform only one agent is currently compliant:

| newest digest | lines |
|---|---|
| `SAIRN-digest-cc-b24.txt` | **10 — compliant** |
| `SAIRN-digest-hank-b22.txt` | 47 |
| `SAIRN-digest-fourth-b37.txt` | 209 |
| `SAIRN-digest-cody-b26.txt` | 239 |

**FIXED FOR b38 BY CONSTRUCTION:** this batch's digest is written to the cap.
That is a fix to my own practice, which is the only part of this finding inside
my scope.

### 2.3 SQL in files, digest gives only the path — b36 breached it

`grep -c "create table" SAIRN-digest-fourth-b36.txt` → **3**. The b36 digest
carried `sql/rt_routes_schema.sql` **verbatim**, 8,777 bytes, inside the digest
— which is both the length breach above and a second copy of a file that then
went stale the same day the constraint was dropped. **b37's digest is 0** and
says so explicitly: *"a second copy is a second thing to go stale."*

**So the rule was already learned once, in prose, in one digest, and nowhere
that would make it hold.** Which is the finding in §1 restated as a cost.

### 2.4 The two rules I am compliant with, checked rather than assumed

* **Silent mode** — `CLAUDE.md`'s *"Response style"* covers it under different
  words: *"No narration before or after actions."* Nothing to fix.
* **Builder/auditor separation** — **0 of b38's commits touch
  `.claude/skills/sairn-hover-auditor/`**, by `git show --name-only` per
  commit. **`tools/hover_separation_audit.py` was deliberately NOT RUN**:
  `CLAUDE.md` says a build agent must not reach into that clone *"including to
  arm those gates"*, and a read that walks the auditor's tree is the same
  boundary running the other way. The absence of commits is the check a build
  agent is entitled to make about itself.

---

## 3. A METHOD ERROR I MADE AND CAUGHT INSIDE THIS SWEEP

I measured `tools/tooling_inventory.py --standing-doc-sizes` as **exit 0** and
was about to report that its documented fail-closed behaviour was broken.

**It was my measurement.** I had written

    python tools/tooling_inventory.py --standing-doc-sizes 2>&1 | tail -14; echo "exit=$?"

and `$?` after a pipeline is **`tail`'s** status, not python's. Re-measured:

    python tools/tooling_inventory.py --standing-doc-sizes > /dev/null 2>&1; echo $?
    # -> 1

**The tool is correct and exits 1 as documented.** Recorded because a sweep
that reports a tool as broken on a pipeline artefact does more damage than the
staleness it was looking for, and because this is the same class as
`sairn-context-budget`'s rule about piping output through `head`/`tail`.

---

## 4. ONE STALE FIGURE IN A SHARED FILE — REPORTED, NOT EDITED

`CLAUDE.md:52` says **7** standing documents are over the ceiling and names a
set. The tool says **8**, and the set has changed:

    python tools/tooling_inventory.py --standing-doc-sizes

| in CLAUDE.md's list | now over the ceiling |
|---|---|
| the four `SAIRN-ACTIVE-WORK-*` | **only three** — `SAIRN-ACTIVE-WORK-fourth.md` has dropped off, having been split into `-closed-1` / `-closed-2` |
| `docs/SAIRN-OPEN-WORK-INDEX.md` | yes, **2,406,402 bytes** |
| `docs/CRITICALITY-TIERS.md` | yes, **523,683 bytes** |
| `SAIRN-ACTIVE-WORK.md` (unsuffixed) | yes |
| — | **`docs/open-work/platform.md`, 847,894 bytes — NOT IN THE LIST AT ALL** |
| — | **`docs/TOOLING-INVENTORY.md`, 441,973 bytes — NOT IN THE LIST** |

**THE PARAGRAPH IS SELF-DEFENDING AND THAT IS WHY THIS IS LOW SEVERITY**: it
already says *"Run the tool rather than trusting this list; it is the thing
that moves."* A reader who follows the instruction gets the right answer. The
number is still wrong, and the two unlisted documents are the ones a reader
would not think to be careful with.

---

## 5. WHAT SOMEBODY ELSE HAS TO DO — PASTEABLE, NOT DESCRIBED

### 5.1 `CLAUDE.md` — a section that does not exist yet

Four of six rules have no home. Suggested text, for whoever owns the primer:

```markdown
## Batch deliverables — the shape, not just the existence

- **Wrap up at 80% of real context.** Measured, not estimated:
  `python tools/context_verify.py --digest-line`. 80% is a WRAP-UP trigger,
  not a hard cutoff — the handoff has to fit inside the remaining 20%.
- **The digest is 30 lines maximum.** It is a routing document, not a second
  report. If it does not fit, the content belongs in the report.
- **SQL goes in `sql/<name>.sql`. The digest gives the PATH ONLY.** A digest
  that embeds a schema is a second copy, and the second copy is the one that
  goes stale.
- **The final chat message is exactly `done b<n> <Drive file id of the
  digest>`** and nothing else.

Each of these was followed for months by remembering, and each was breached the
first time a batch got long. Do not re-derive the numbers from a handoff; this
is the source.
```

### 5.2 `.claude/skills/sairn-session-handoff/SKILL.md` — the missing half

That skill covers the handoff and **not the report or the digest**, which are
two of the three deliverables it is invoked for. It needs a `## The digest`
section carrying the 30-line cap, the SQL-path rule and the done-line, and its
`## When to write one` needs the 80% figure instead of *"before capacity runs
low."* **Shared file — not edited here.**

### 5.3 Nothing enforces any of it, and building the enforcement is in `tools/`

`grep -rn "digest" tools/*.py` reaches 10+ tools; **none measures a digest's
length.** `tools/drive_upload_verify.py` checks a digest's NAME, FIRST LINE,
BYTES and SHA256 — four real checks, and **not one of them would notice a
319-line digest.** A `--max-lines 30` arm there is the natural home.

**I did not build it, and the reason is the scope boundary rather than
difficulty.** Flagging it as the cheapest available fix for the whole class:
the rule stops depending on memory the moment one gate reads it.

---

## 6. WHAT THIS SWEEP DID NOT ESTABLISH

* **It swept six named rules, not every rule.** The dispatch named them; there
  may be others equally unwritten and this file makes no claim about them.
* **No skill was read end-to-end.** The 34 skills were searched by pattern for
  the six rules. A skill could contradict one of them in words my patterns did
  not match.
* **The compliance figures for cc, cody and hank are LINE COUNTS of their
  newest digest and nothing more.** I did not read their content and I am not
  reporting them as non-compliant agents — a long digest may be deliberate, and
  the rule may have reached them later than it reached me.
* **`tools/hover_separation_audit.py` was not run**, by choice. My separation
  claim rests on my own commits' file lists, which is weaker than that tool and
  is the strongest thing a build agent should be reaching for.
* **Nothing was fixed outside my own practice.** The b38 digest is written to
  the cap; the four shared-file findings are reported and untouched.
