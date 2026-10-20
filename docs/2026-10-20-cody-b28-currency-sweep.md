# Currency sweep — cody's own skills, tools, methodology and rules

**cody, batch b28, 2026-10-20.** Item 5 of the dispatch: *"Currency sweep of
your own skills/tools/methodology vs the standing rules (report shared items,
do not edit them)."*

**SCOPE BOUNDARY, APPLIED AND NOT NEGOTIATED.** Nothing under
`.claude/skills/`, `tools/` or `CLAUDE.md` was edited in this batch — five
shared tools were RUN, which is the permitted half. `git show --name-only` on
every b28 commit is the check. Every finding in §3 is in a shared file and
every one of them is reported with pasteable text and left alone.

**`CLAUDE.md` is treated as shared** even though it sits in neither named
directory: it is the primer all four build agents read, and a currency sweep is
the wrong vehicle for a unilateral edit to a shared standing document. Same
judgment fourth recorded in `docs/2026-10-20-fourth-b38-currency-sweep.md` §0,
reached independently and stated rather than assumed.

---

## 0. THE RESULT IN ONE LINE

**Two of my own rule-compliance records are measurably bad, two findings a
shared checker attributes to my files are NOT my defects, and the single
largest finding is that the documented handoff naming convention describes 3 of
83 handoffs on disk.**

| # | finding | mine or shared | state |
|---|---|---|---|
| 1 | **16 of 23 cody digests exceed the 30-line rule**, b4 by 10.8× | **mine** | measured, §1.1 |
| 2 | **b27 wrapped at 92% context, not 80%** | **mine** | measured, §1.2 |
| 3 | `SAIRN-ACTIVE-WORK-cody.md` is **795,238 bytes**, 2.0× the 400KB ceiling | **mine** | measured, §1.3 |
| 4 | **80 of 83 handoffs use a COUNTER; the convention says DATE and calls the counter superseded** | shared | §3.1 |
| 5 | `CLAUDE.md` says **7** documents are over the ceiling; the tool it cites says **8**, with a different list | shared | §3.2 |
| 6 | `unproven_arm_check` A1 against `tests/run_floor_layers_probe.py` is a **false positive** | shared tool, my file | §3.3 |
| 7 | `unproven_arm_check` A4 is satisfied by **any** durable write, so 5 of 9 files pass it without persisting a verdict | shared tool | §3.4 |

---

## 1. MY OWN ITEMS — MEASURED, AND TWO OF THEM ARE BAD

### 1.1 Digest length: 16 of 23 over 30 lines

    for f in SAIRN-digest-cody-*.txt; do printf "%-32s %s\n" "$f" "$(wc -l < "$f")"; done

| batch | lines | | batch | lines |
|---|---|---|---|---|
| b4 | **323** | | b17 | **165** |
| b5 | 20 | | b19 | **132** |
| b6 | 20 | | b20 | **173** |
| b7 | 22 | | b21 | **164** |
| b8 | 22 | | b22 | **150** |
| b9 | 22 | | b23 | **193** |
| b10 | 21 | | b24 | **177** |
| b11 | **112** | | b25 | **199** |
| b12 | **113** | | b26 | **239** |
| b13 | **97** | | b27 | 5 |
| b14 | **153** | | | |
| b15 | **166** | | | |
| b16 | **148** | | | |

**Seven compliant (b5–b10, b27), sixteen not.** The shape is not random: b4–b10
were compliant, the rule was then broken at b11 and never recovered until b27,
which is compliant because that session was cut short rather than because the
rule was being followed. **A rule nothing measures decays on a schedule**, and
this is the schedule.

### 1.2 Wrap-up at 80% real context: b27 wrapped at 92.0%

Nine of my digests carry a `CONTEXT` line at all; eight of those nine are under
80%. The exception is the most recent:

    grep -h "CONTEXT" SAIRN-digest-cody-*.txt | grep -oE "CONTEXT [0-9.]+%"
    -> 32%  37%  37%  55.9%  56%  64%  73%  74%  92.0%

**b27: `CONTEXT 92.0% of 1,000,000 -- 919,859 tokens, measured.`** That is 12
points past the trigger, and the cost is visible in b27's own handoff: a wrap-up
order arrived mid-edit on item 4, and the half-finished item had to be reverted.
**The fourteen digests with no `CONTEXT` line at all are the worse number** —
not a breach, but an unmeasured batch cannot be reported either way, and
"usually fine" is what this platform calls a silence wearing a status.

### 1.3 `SAIRN-ACTIVE-WORK-cody.md` is 2.0× the ceiling

    python tools/tooling_inventory.py --standing-doc-sizes   # exit 1, as documented
    -> 795238 bytes  ~ 214929 tokens  SAIRN-ACTIVE-WORK-cody.md

**NOT FIXED IN THIS BATCH, AND THE REASON IS NOT TIME.** The established remedy
is the split fourth already performed — `SAIRN-ACTIVE-WORK-fourth-closed-1.md`
and `-closed-2.md`, which is why fourth's live file is 369KB and under the
ceiling. Splitting an append-only work log is a decision about *where the cut
goes*, and a cut in the wrong place makes the history unsearchable in exactly
the way the ceiling exists to prevent. Recorded as open work with the remedy
named rather than done hurriedly at the end of a batch.

### 1.4 What came back CLEAN, said out loud

| check | result |
|---|---|
| `tools/live_probe_declaration_check.py` | **exit 0** — `tests/rt_routes_live_probe.py`, added this batch, declares `LIVE_PROBE_CLASS` and `LIVE_PROBE_RESIDUE` in a form the residue auditor's own regexes can read |
| `tools/tooling_inventory.py --standing-doc-sizes` exit behaviour | **exit 1 as `CLAUDE.md:150` says.** Re-measured directly, because the first measurement piped through `tail` and read `tail`'s exit code — the defect my own auto-memory records |
| `tools/probe_anchor_freshness.py` | 416 probes, 645 anchors; **no cody-owned probe among the non-unique-anchor findings** |

---

## 2. THE RULES THEMSELVES — STILL NOT WRITTEN DOWN

fourth measured this in b38 and found four of six rules absent from every
document a fresh session reads. **RE-MEASURED INDEPENDENTLY, 2026-10-20, and
nothing has changed:**

    grep -rln "80%"       CLAUDE.md docs/SAIRN-PROCESS-RULES.md
    grep -rln "30 lines"  CLAUDE.md docs/SAIRN-PROCESS-RULES.md

* **wrap-up at 80%** — absent. §1.2 is what an unwritten threshold costs.
* **digests 30 lines max** — absent. §1.1 is what it costs.
* **SQL in files, digest gives only the path** — absent.
* **the done-line format** — absent.

**This is a confirmation of fourth's finding by a second session, not a new
one.** Two independent sessions reaching the same measurement is the thing that
makes it worth acting on; one session's sweep is a reading. Neither of us has
edited `CLAUDE.md` to fix it, and that is now a decision Michael should make
rather than two agents each declining to make it — §3.2 carries the text.

---

## 3. SHARED ITEMS — REPORTED, NOT EDITED

### 3.1 The handoff naming convention describes 3 of 83 handoffs

`.claude/skills/sairn-session-handoff/SKILL.md:15` is explicit, and so is its
own description line:

> **Naming convention — CORRECTED 2026-08-23 (supersedes the 2026-07-26
> resolution).** Use `APP-YYYY-MM-DD-subject-handoff.md`. … *the old app+counter
> scheme collided in production*

`CLAUDE.md:22` instructs a fresh session accordingly: *"Find it by **DATE**, not
by a counter — handoffs are named `APP-YYYY-MM-DD-subject-handoff.md`. Sort by
the date in the filename."*

**MEASURED:**

    ls | grep -cE "^SAIRN-handoff-[a-z0-9]+-b[0-9]+\.md$"          -> 80
    ls | grep -cE "^[A-Z]+-20[0-9]{2}-[0-9]{2}-[0-9]{2}-.*-handoff\.md$" -> 3

**All four build agents, for eighty handoffs, use the session+counter scheme the
skill says was superseded two months ago.** This is not a style quibble: the
startup instruction is *unexecutable* against 80 of 83 files, because there is no
date in the filename to sort by. A fresh session that follows `CLAUDE.md:22`
literally finds three handoffs, none of them recent, and the most recent real
handoff is invisible to the procedure meant to find it.

**It is also not obvious which side is wrong**, which is exactly why this is a
report and not an edit. The counter scheme in practice is `-<session>-b<NN>`,
which carries the session name the 2026-07-26 collision was about — so the
collision the correction was written to prevent may already be prevented by a
different means. **That is Michael's call, and the two candidate fixes are
opposite:**

> **Option A — the practice is right, the documents are stale.** In
> `.claude/skills/sairn-session-handoff/SKILL.md` §Naming convention and in
> `CLAUDE.md` step 1, record `SAIRN-handoff-<session>-b<NN>.md` as the
> convention, state that the per-session prefix is what resolves the 2026-07-26
> collision, and replace "sort by the date in the filename" with "sort by the
> batch number within your own session's prefix".
>
> **Option B — the documents are right, 80 files are mis-named.** Then the
> rename is mechanical but the *references* are not: every digest, batch
> document and open-work row citing a handoff by name would need re-pointing,
> and `tools/` reads these names in at least one place.

**Option A is the recommendation.** The scheme in use is per-session, so it
cannot collide between sessions, and renaming 80 files to fix a sentence is the
more expensive direction.

### 3.2 `CLAUDE.md` says 7 documents are over the ceiling; the tool says 8

`CLAUDE.md:52`: *"Note that **7 tracked documents are over the ceiling, not
one** — these four, `docs/SAIRN-OPEN-WORK-INDEX.md`,
`docs/CRITICALITY-TIERS.md` and the unsuffixed `SAIRN-ACTIVE-WORK.md`."*

    python tools/tooling_inventory.py --standing-doc-sizes      # exit 1
    -> 8 DOCUMENT(S) OVER THE CEILING

**The count is wrong and so is the list.** `SAIRN-ACTIVE-WORK-fourth.md` is
369,849 bytes and is now UNDER (fourth split it); `docs/open-work/platform.md`
(847,894) and `docs/TOOLING-INVENTORY.md` (442,976) are over and are named in
neither place.

**The paragraph partly defends itself** — it already says *"Run the tool rather
than trusting this list; it is the thing that moves."* That sentence is why this
is a low-severity finding rather than a trap. Pasteable replacement for the
sentence that does move:

> Note that **several tracked documents are over the ceiling, not one.** The
> count and the list both move — `python tools/tooling_inventory.py
> --standing-doc-sizes` prints them and exits 1 while any exists. Do not quote a
> number from here; it was 7 on 2026-10-08 and 8 on 2026-10-20, with two
> documents swapped in and one out.

### 3.3 `unproven_arm_check` A1 against `tests/run_floor_layers_probe.py` is a false positive

    python tools/unproven_arm_check.py      # exit 1, 5 findings over 415 files
    A1  tests/run_floor_layers_probe.py:99
        "an unproven verdict is emitted or counted, but no summary print carries
         an unproven number. A reader of 'N passed, 0 failed' cannot tell an
         unproven arm from a passing one, and the exit code certainly cannot."

**Both halves of the stated harm are false for this file**, and the file is
cody's so I read it rather than accepting the finding:

* `tests/run_floor_layers_probe.py:406-407` prints
  `'%d UNPROVEN: %s' % (len(unproven), '; '.join(unproven))` — **a summary print
  carrying the unproven count and the arm names.**
* `:413-414` is `if unproven: sys.exit(3)` — **the exit code can and does tell**,
  and the file's own header documents `3 COULD NOT RUN / UNPROVEN`.
* The file never prints `"N passed, 0 failed"` in any form, so the reader the
  finding describes does not exist.

The likely cause is that A1 looks for the unproven count inside the detected
pass/fail *summary construct*, and this file's failure summary is
`print('%d failure(s)')` with the unproven line as a separate statement above
it. **The tool's own header anticipates this shape** — `tools/unproven_arm_check.py:288`
reads *"and reports A1 against a file that does everything right. That is a
FALSE…"*. Reported to the tool's owner rather than worked around by moving a
`print` to satisfy a scanner, which would be writing for the checker instead of
the reader.

### 3.4 A4 is satisfied by any durable write, so it clears files that persist nothing

A4's finding text is careful and correct about itself: *"The rule is not violated
here, it is UNENFORCEABLE here, which is the precondition the rule needs and the
only half of it a static read can see."* The gap is in what clears it.

**MEASURED:** 9 files have an unproven mechanism; 4 get an A4 finding; 5 do not.
One of the 5 clean ones is `tests/run_floor_layers_probe.py`, whose only durable
write is at `:149` — `json.dumps({'floor': self.value, 'how': 'fixture'})`, a
**test fixture**, nothing to do with persisting a verdict. So A4 is answering
"does this file write any file at all", and a suite could clear it by writing a
log it never reads.

**This matters for the one A4 finding that is mine.**
`tests/sairncare_compliance_window_boundary.test.js:130` is cody's and is
flagged. **It is deliberately NOT fixed**, because the only available fix is to
add a durable write — which would clear the finding without making the two-run
comparison possible, i.e. gaming the checker. Suggested change for the owner:

> A4 should require the durable write to be REACHABLE FROM THE UNPROVEN PATH —
> inside the branch that emits or counts an unproven verdict — not merely
> present somewhere in the file. As written it clears
> `tests/run_floor_layers_probe.py` on a fixture write at `:149`, and a suite
> can satisfy it with a log nobody reads.

---

## 4. WHAT THIS SWEEP DID NOT COVER, SO THE CLEAN HALF IS NOT OVERSTATED

* **The two-run UNPROVEN comparison itself.** Unchecked here and unchecked by
  the tool, which says so. A clean A4 is not evidence any suite obeyed the rule.
* **Whether my probes are WIRED.** `probe_anchor_freshness` says it *"says
  nothing about whether the probe is WIRED"*, and that is still true: no
  cody-owned fault probe was verified to be in `report_only_checks.REGISTRY`,
  the push gate or any hook in this batch.
* **My batch documents' citations.** Not re-derived against HEAD. `docs/b27-logs/`
  and the b2x batch documents carry `file:line` citations that nothing in this
  sweep re-checked, and line numbers in `api/sd-data.js` moved by ~145 lines in
  this very batch.
* **The 34 shared skills.** Only `sairn-session-handoff` was read, because §3.1
  came out of it. The other 33 were not swept and no claim is made about them.
