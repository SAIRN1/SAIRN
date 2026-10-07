# Blameless postmortem — the count that was 11 too high

**Item 10, batch 14, 2026-10-07 (cc).** Blameless in the sense that matters: the
question is what let a wrong number reach a standing record, not who typed it.
I wrote the tool, the bug and the number, so there is nobody else to be blameless
about.

---

## 1. What was reported, and what was true

On 2026-10-06 I reported **55 permanently-absent citations** in
`docs/citation-absent-register.json` — a standing record other sessions were
meant to act on, with the orphans attributed per document and routed per owner.

The true figure was **44**. Eleven of the fifty-five **were never citations at
all.**

The register listed `1234abcd` from `SAIRN-ACTIVE-WORK-hank.md` as a
permanently-absent commit citation. `1234abcd` is a *documentation example* — it
is the illustrative literal **this tool's own comments use** when explaining what
a SHA looks like. The register was reporting a finding about a worked example.

## 2. The mechanism, in one sentence

`tools/doc_sha_reseat.py` had two modes over one population, and **the mode that
WROTE the standing record used the looser candidate rule.**

`--census` — read-only, prints a table — filtered out all-digit tokens, 12-hex
register record ids and the documentation literals, in a filter written **inline
in its own loop**.

`--register-absent` — which writes `docs/citation-absent-register.json` — did
not. It had its own loop and its own filter, and the two had diverged.

Both now call one `is_citation()`.

## 3. Five things that were true and did not stop it

Not a list of villains; a list of defences that were present and did not fire.

**(a) Both modes worked.** Neither crashed, neither printed a warning, and both
produced plausible output. The question that would have caught it is not *does my
mode work* but *does my mode agree with the one already there*, and nothing asked
it.

**(b) The tool had a criteria lock, and it locked the wrong function.** Twelve
fixtures, all green, all of them exercising `substitutions()` and `apply_subs()`
— the substitution machinery. **Not one touched the candidate rule.** So the
tool could demonstrate on every run that it substituted correctly, while being
wrong about what a citation *is*.

**(c) The second mode was added later.** `--census` came first and was careful.
`--register-absent` was added to do something adjacent, and it reimplemented the
filter rather than calling it — which is the normal way a second mode gets
written and is invisible in review, because both loops look correct and they are
forty lines apart.

**(d) The number went DOWN when it was fixed, which looks like regression.** 55 →
44. Anyone reviewing the diff sees a tool reporting *fewer* findings after a
change to its filter, and the innocent reading is that the filter got too tight.
The honest reading is the opposite and takes the 11 named tokens to establish.

**(e) It was found by READING THE OUTPUT, not the code.** `1234abcd` in a JSON
file is visibly not a SHA. In the source it is one more hex string in a loop that
looks like the loop next to it. The cheap test — open the artefact the writing
mode produced and read ten rows — is the one that worked, and it is not a test
anything runs.

## 4. What this cost

Eleven false findings in a routing table, attributed to **hank** and to
**fourth**. Not catastrophic, and the shape is: a repair tool with a **9%
false-candidate rate** publishing a work queue for other sessions, who had no
way to tell which rows were real without redoing the derivation.

The second cost is subtler and is the reason this postmortem exists at all: when
the two modes were reconciled the count moved, and **reporting that movement as
progress would have been the second defect.** The count did not get better; it
got *correct*, and the eleven were never real. That sentence had to be written
into the routing record on purpose.

## 5. THE SYSTEM-LEVEL FIX — one, inside an existing check

The fix is **not** another checker. It is the gap that let (b) happen: a tool can
hold a criteria lock that is entirely green while the function that decides what
the tool is *about* has no arm at all.

**Landed in `tools/doc_sha_reseat.py`'s own existing `--fixtures` lock, as
sixteen new arms — one per false-positive shape of `is_citation`, plus the true
positives, plus the known cost.** Commit `a9e9147b`.

    python tools/doc_sha_reseat.py --fixtures -> 0, 28/28   (was 12/12)

The arms, and each is a shape that returned **True** before the rule existed:

| must NOT be a citation | must still BE a citation |
|---|---|
| an all-digit run that is valid hex | 7, 8, 11 and 13-char prefixes |
| a 12-hex register RECORD ID | a full 40-char SHA |
| `1234abcd`, `deadbeef`, `abcdef0`, `0000000` | |
| `deadbeefcafe` | |
| an empty token, and `None` | |
| `1234ABCD` — upper case is still the literal | |

And one arm that is neither, and is the reason the set is honest:

> **a REAL 12-char SHA prefix is excluded TOO, and that is the known cost.**

The 12-character exclusion cannot tell a register record id from a 12-character
citation, and it chooses to lose the citation. That is a trade. It is now
asserted, so changing it will fail loudly rather than silently widening the rule.

**`CRITERIA_VERSION` was deliberately NOT bumped.** It stays `2026-10-06.1`,
because **no criterion changed** — the arms assert the behaviour the tool already
had. Bumping it would make every register already stamped with the old version
read as measured under superseded criteria, which is a worse falsehood than a
version that did not move. What changed is the lock's *coverage*.

### Why this is a system-level fix and not a local patch

The shared `is_citation()` function closed the *instance*. It did not close the
*class*, because nothing would have failed if someone had edited the shared rule
back out, or added a third mode with its own filter. **The arms are what make the
rule load-bearing.** A rule with no arm is a rule that can be removed silently,
which is precisely how the two modes diverged the first time.

## 6. The two methodology rules this produced

Written into `docs/handoff-cc-2026-10-07c.md` §5 and routed in
`docs/2026-10-06-cc-routed.md` §29. **`docs/METHODOLOGY.md` was not edited** —
it belongs to fourth and hank at this HEAD and item 10 says not to touch it.

* **Rule A** — a mode that writes uses the strictest candidate rule, and every
  mode must report the same count.
* **Rule B** — an unrecognised flag fails closed.

Rule A is the direct lesson. Rule B is from the same batch and the same family:
three tools were found whose default, on an argument they did not understand, was
to **write**.

## 7. What is still open

* **The count comparison is not mechanical.** Rule A says every mode must report
  the same count; today I compared them by hand (`--census` ABSENT 100 against
  `--register-absent` absent recorded 100). Nothing asserts it, and nothing would
  notice if they diverged again by a different route.
* **Only `is_citation` got arms.** No sweep asks, across the other tools, *which
  function decides what this tool is about, and does it have an arm?* That is the
  generalisation of §5 and it is not built.
* **The 12-char trade is asserted, not resolved.** A real 12-character citation
  is still lost. Resolving it needs a way to tell a record id from a SHA prefix,
  which is a data question, not a code one.
