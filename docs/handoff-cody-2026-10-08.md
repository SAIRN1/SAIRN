# cody — handoff, 2026-10-08 (batch 26 / b3)

**Claim:** `cody / Tooling`, batch 26, taken at HEAD `3f67fc16`.
**Written and committed per item.** Every premise re-derived at pickup from
`sairn_claim.py` (the registry) and from `origin/main`.

`sairn-guardian-v2` was **not loaded**: no item edits an app file.

---

## item 1 — DONE. Resume confirmed, and two premises change at pickup.

```
command : git fetch; git rev-parse HEAD; git merge-base --is-ancestor 3f67fc16 origin/main
date    : 2026-10-08
HEAD at pickup  3f67fc162ebfee72574aa575648464b1c4796c38   <- exactly as the item says
3f67fc16 is an ancestor of origin/main : rc 0
origin/main at pickup 3c6a1749 (1 commit ahead of my HEAD; rebased cleanly, rc 0)
```

`docs/handoff-cody-2026-10-07c.md` read; its six open items are the spine of this
batch.

**THE REGISTRY HAS NO ACTIVE CLAIMS AT ALL.** `sairn_claim.py list` prints
`No active claims.` — cc, fourth, hank and hover2 have all released. Two item
premises change on that:

- **item 3's target is FREE.** `docs/tier-a-reviews.json` was cc's when batch 25
  routed the reseat; it is declared by nobody now, so this batch **reseats**
  rather than routes.
- **item 5's gate is ownership, not the claim.** With no live claim,
  `docs/scrutiny-flags.json` is claimed by nobody — so "exclusively cc's" has to
  be decided on **durable** ownership, which is what item 5 is checked against
  below.

**AND ONE COUNT IN THE ITEM LIST IS WRONG:** item 5 says *4* parked stashes.
`git stash list` shows **seven**, all batch-25 gate rows. Named here rather than
quietly worked around.

## item 3 — DONE. The reseat path reaches `reviewed` records, and 4aa33b4565dd is reseated.

### What was actually wrong, and it was bigger than one record

`reseat_shas()` opened with
`rows = [r for r in records if r.get('status') == 'open']` and **nothing said
so**. A reviewed record with an orphaned sha was not refused, not listed, not
counted — **absent**.

**THE DISCLOSURE IS WHAT MADE THE SIZE VISIBLE.** Default mode now prints the
reviewed population either way, and the first run of it reported:

```
command : python tools/tier_a_review_gate.py --reseat-shas
commit  : 3f67fc16 + this change        date: 2026-10-08
  population                   : open only (default)
  records examined: 22
  REVIEWED records carrying a sha: 72 -- NOT examined in this mode
    of those, 32 are NOT reachable from origin/main and so are dangling
    RE-RUN WITH --include-reviewed TO EXAMINE THEM. Until then this run says
    nothing about them, which is not the same as saying they are fine.
```

**72 reviewed records carry a sha and 32 of them are dangling.** One record was
the symptom; thirty-two is the finding, and none of it was visible before.

### Three changes, and the default population is deliberately unchanged

1. **The disclosure**, printed whether or not the flag is used — because without
   it a default run is indistinguishable from one where no reviewed record has a
   problem.
2. **`--include-reviewed`** widens the population and says it did. The walk
   window is recomputed from the widened set: an index built from the open set
   alone cannot contain a reviewed record's survivor, and the record would then
   be refused for *"nothing matched"* rather than reseated.
3. **`--only <opened_at>`**, because `--write` repoints **every** fixable record
   in one keystroke — **11 of them across four sessions** at this HEAD.
   Reseating another session's record is editing their finding.

**The default count did not move: 22 open records before and after.** Widening it
silently would change the meaning of every figure this tool has printed.

### The reseat itself — one record, and three methods agree on the survivor

```
command : python tools/tier_a_review_gate.py --reseat-shas --include-reviewed \
            --only 2026-10-06T22:18:54Z --write
EXIT 0 : "RESEATED 1 record(s) on a strong basis, 0 on the WEAK basis, 0 refused."
diff   : docs/tier-a-reviews.json  5 insertions / 2 deletions -- ONE record
  - "opened_at_sha": "4aa33b4565ddceeaac1081997f1d379d05b9de47"
  + "opened_at_sha": "27de70bee07a208ab6aa1c7e424ca65643d30719"
  + "opened_at_sha_was": "4aa33b4565ddceeaac1081997f1d379d05b9de47"
  + "opened_at_sha_reseated": true
  + "opened_at_sha_reseat_basis": "SUBJECT TWIN"
git merge-base --is-ancestor 27de70bee07a origin/main -> rc 0   REACHABLE
```

**THE SURVIVOR WAS ESTABLISHED THREE INDEPENDENT WAYS and they agree:** cc's
file-history recovery, my own `git log --diff-filter=A -- tools/ledger_append.py`
in batch 25, and now the tool's own `SUBJECT TWIN` match. The old sha is kept in
`opened_at_sha_was`, so the reseat is reversible and visible rather than a silent
overwrite.

### The fixture, and which arm fails first

**12 new arms.** The **fail-first** one is the *disclosure* arm: it asserts the
default run prints the reviewed count, and pre-fix there is no such line — a red
arm with a real message. The `--include-reviewed` arms cannot fail that way
(the keyword does not exist pre-fix and would raise `TypeError`), and **the probe
says so in a comment** rather than leaving a reader to find out.

**The refusal halves are arms too**, because the likely mistake with `--only` is
a mistyped timestamp:

```
--only matching nothing            -> EXIT 2, "matches no record", nothing written
--only on a reviewed record without --include-reviewed
                                   -> EXIT 2, and it NAMES the flag that would find it
```

A selector that matches nothing and prints *"0 reseated"* as success is how that
typo becomes *"already fine"*.

```
python tests/run_tier_a_review_gate_probe.py -> EXIT 0, ALL ARMS PASS, 242 ok
2 runs, first EXIT 0 each time.
```

## item 4 — DONE. The row is **CLOSED as not needed**, with the reasoning measured, plus one change that costs no new noise.

### Why there is no new check, and it is not a judgement call

```
command : scratchpad/b26/i4_measure.py over every `python tools/...` /
          `node tests/...` command line in docs/*.md
commit  : f7bab1b0        date: 2026-10-08
corpus  : 398 command lines, 107 distinct
  already flagged by the EXISTING rules : 0
  already route through capture_exit.py : 1
  judged attributable, no status file   : 106
A STANDALONE BACKGROUNDING WARNING WOULD BE NEW OUTPUT ON 106 OF 107 (99%).
```

And the hook fires on **every** Bash call, not only documented ones, so 99% is a
**floor** on the live rate rather than an estimate of it.

**THREE REASONS, IN ORDER OF WEIGHT:**

1. **IT IS OUTSIDE THE TOOL'S INPUT.** This tool reads command **text**. Whether
   a run is backgrounded is decided by the harness **after** the text exists.
   `grep -cin background tools/exit_status_attributable.py` → **0**, and that is
   correct rather than an omission: the signal is not in its input.
2. **THE GAP IS ALREADY CLOSED BY ANOTHER TOOL, and that tool says so.**
   `tools/capture_exit.py`'s own docstring reads: *"That advice is CORRECT and
   `tools/exit_status_attributable.py` is right to give it. IT STOPS BEING
   CORRECT THE MOMENT THE RUN IS BACKGROUNDED."* The division of labour is
   recorded; what was missing was a **pointer**, not a checker.
3. **A 99% FIRING RATE IS HOW A HOOK GETS SWITCHED OFF**, and a disabled hook
   protects nothing. That is this platform's own stated failure mode, and it
   would trade a real warning for a wall of text.

### The one change made instead — zero new firings

The existing warning now ends with:

> *AND IF THIS RUN MAY BE BACKGROUNDED, `$?` will be the wrapper's and not the
> program's: use `python tools/capture_exit.py --status <file> -- <command>` and
> read the status FILE.*

**It rides on a warning that was already firing**, so it adds words to an
existing message and **no new messages**. Verified by driving the hook:

```
echo '{"tool_name":"Bash","tool_input":{"command":"python tools/metamorphic_check.py | tail -5"}}' \
  | python tools/exit_status_attributable.py --hook
  -> names "capture_exit.py --status" and "read the status FILE", 775 bytes
python tools/exit_status_attributable.py --selftest -> EXIT 0, 40 ok, 0 FAIL
```

**ROW CLOSED.** `docs/2026-10-08-cody-b26-routed.md` records the close so the
routing table in `docs/2026-10-06-cody-routed.md` is no longer pointing at
unfinished work — which was the actual complaint: a row with no body.

## item 5 — DONE as a decision: **NOT TOUCHED.** `docs/scrutiny-flags.json` is exclusively cc's.

The item says to act only if the file is **not** exclusively cc's per the claim
rules. With **no live claim anywhere**, "the claim rules" cannot answer it — so
**durable** ownership was read instead, and it is unambiguous:

```
docs/tool-owner-map.json : tools/exit_status_attributable.py -> owner cc,
                           basis OWNER_LINE          <- the strongest basis it records
line 1 of that file      : # OWNER: cc
the only writer of docs/scrutiny-flags.json : tools/exit_status_attributable.py
                           (grep -rln over tools/ and .githooks/)
tests/run_scrutiny_flag_probe.py -> owner cc
```

**So the data file is cc's because its writer is, and the companion probe is too.
Left named for cc. Nothing popped, nothing dropped, nothing committed.**

### The seven stashes, itemised for cc

The item says four; there are **seven**, and **every one touches that file and
nothing else** (`git stash show --name-only`, all seven):

| stash | lines added | message |
|---|---|---|
| `stash@{0}` | 200 | `b25 FINAL: gate rows in cc's docs/scrutiny-flags.json -- parked and reported` |
| `stash@{1}` | 200 | `b25 gate rows r2` |
| `stash@{2}` | 200 | `b25 gate rows r1` |
| `stash@{3}` | 58 | `b25 gate rows (cc's file)` |
| `stash@{4}` | 58 | `b25 gate rows r1` |
| `stash@{5}` | 58 | `b25 gate rows round 1` |
| `stash@{6}` | 84 | `b25: scrutiny rows the gate wrote into CC'S file` |

**THEY ARE LARGELY REDUNDANT AND cc SHOULD PROBABLY DROP THEM, which is a
recommendation and not an action.** The push gate re-writes these rows on every
blocked attempt, so the later stashes are supersets of the earlier ones, and at
least some rows are already committed — the spot check shows `149874f1` is an
ancestor of `origin/main` (rc 0) and `13b7d297` is not even an object in this
clone. The committed file already carries **102 flag rows**.

**WHY I AM NOT DROPPING THEM MYSELF:** `git stash drop` is irreversible once the
reflog expires, and the judgement about whether any row is unique belongs to the
file's owner. The cost of leaving them is seven entries in my own stash list; the
cost of being wrong is losing a scrutiny record nobody can reconstruct.

**NEXT STEP for cc:** `git stash show -p stash@{0}` in `Documents/SAIRN-cody`,
keep anything not already in the committed 102, then `git stash drop` the rest.
I will drop them on one word from cc or chat.

## item 6 — DONE. 64 scripts outside git: **6 committed, 58 registered.** Two loose docs rescued.

```
command : tools/scratch-archive/inventory2.py then scratchpad/b26/build_index.py
commit  : 22202012 + this change        date: 2026-10-08
-> docs/external-files-index.json : 6 directories, 4 loose home files, 64 scripts
```

### The first count was wrong in the inflating direction, and the correction is the point

```
pass 1 : 2,521 "code files across all scratchpads"
         -- 2,140 of them in ONE session. Reading three of the paths showed what
            they are: COPIES OF THE REPO'S OWN api/ AND tests/ TREES inside the
            fa12/ and fa14/ firebase-admin sandboxes from batch 20.
pass 2 : prune sandbox dirs by name  -> 376
         subtract the 311 whose basename is ALREADY a tracked repo file (copies of
         tools/ inside sandbox dirs)  -> 65, newest-per-name 64
```

**A count that includes a copy of the thing it is meant to be distinguished from
is not a measurement.** Both numbers are in the index so the correction is
visible rather than replaced.

### The admission rule, fixed before the sorting

A script is **committed** only if **both** hold: it is named in a committed
document, **and** that mention is an **open NEXT STEP** rather than a record of
something done.

```
authored outside git                      : 64
cited by name in some committed document  : 26
meeting BOTH conditions -> committed       :  6
```

**Committed to `tools/scratch-archive/`** with a README stating they are archived
one-shots and not supported tools: `childwatch.py` (the fixed watcher, never yet
run against a full suite), `launch_suite.ps1` (the only launch shape that has
produced a completed run), `triage86.py`, `analyse_times.py`,
`prove_childwatch.py`, `inventory2.py`.

**Not wired into any suite or gate, deliberately** — `run_all_tests.py` discovers
`tests/`, so nothing there can fail a suite or be mistaken for a check.

**Five of the 26 citations were NAME COLLISIONS and were excluded by reading
them:** `inventory.py` (cited in `.claude/agents/*.md`, a different thing),
`run.sh`, `triage.py` and `guard.py` (cc's and the hover auditor's), and
`cc_basis_probe.py` (my copy of cc's file). Committing on a basename match would
have pulled in four other sessions' work.

### Two loose files rescued from the home directory

`CLAUDE.md` says handoffs live only in a real clone and **never** in
`C:\Users\marsh\`. Two were sitting there, in the repo **nowhere**, neither
byte-identical nor present in `docs/` history:

```
docs/archive-from-home/SAIRN-SESSION66-HANDOFF.md                        10,881 b  sha256-16 48caa52d86256fac
docs/archive-from-home/OLD-uncommitted-sairnlaw-trust-disbursement-2026-08-18.md  12,404 b  sha256-16 1363d3c182644bf6
```

**Copied verbatim — no header added, no content altered.** They are not mine and
the provenance belongs in the commit message and the index, not inside somebody
else's document. The two `*_live_check.html` files are **generated app snapshots**
whose first lines *do* appear in docs history: registered, not committed.

### The directories, with their volatility

| path | role | volatility |
|---|---|---|
| 4 session scratchpads under `%TEMP%\claude\…SAIRN-cody` | transcript + working files | **HIGH** — cleared without warning |
| `~\SAIRN-SESSION-LOCKS` | shared status registry, outside every clone | MEDIUM |
| `G:\My Drive\SAIRN-status` | the reports Michael reads | LOW — synced off-machine |

**The index is DERIVED and says so**, with the regeneration command in its own
header: a hand-maintained index of files that move is exactly the drift this
platform keeps paying for.

## item 7 — DONE in parts, and **two sub-items were already satisfied by somebody else**.

### (a)+(b) settings — ALREADY CORRECT, so nothing was merged

```
command : read ~/.claude/settings.json (backed up first to
          settings.json.bak-b26-20261008T141329Z and to scratchpad)
BEFORE sha256 9894b829333e0749cc0b64d1, 9,063 bytes, 12 top-level keys
  autoCompactWindow           = 150000      <- the value the item asks for
  env.BASH_MAX_OUTPUT_LENGTH  = '10000'     <- the value the item asks for
```

**Both targets were already present and already correct**, so **nothing was
written** — a merge that changes nothing still risks the key-loss this file
suffered on 2026-10-07, when `model` vanished from it during an unrelated edit.
Also present and not mine: `autoCompactEnabled = false`,
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = '75'`.

**QUESTION FOR MICHAEL:** `autoCompactWindow = 150000` sits beside
`autoCompactEnabled = false`. If auto-compaction is off, does the window do
anything? One of the two is probably not what you intended, and I did not guess.

### (c) version — `claude --version` → **2.1.222 (Claude Code)**, exit 0

### (d) `/context` and `/mcp` — I CANNOT INVOKE THEM. Asked, not estimated.

Both are **client-side commands**; a model turn has no tool for either. This is
the third batch in which that is true, and inventing a breakdown would be the
fabricated-KPI shape Check 0b exists for. **ASK: run `/context` and `/mcp` and
paste the output.**

**AND THE SERVERS CANNOT BE DISABLED FROM A FILE — measured, not assumed:**

```
.mcp.json                                    : does not exist (repo or ~/.claude)
mcpServers / disabledMcpjsonServers in either settings.json : absent
~/.claude.json                               : only claudeAiMcpEverConnected, a LIST
```

The integrations are **account-level**, so `/mcp` in the client is the only lever.
What I can give you is the evidence, so each decision is one click:

```
command : scratchpad/b26/usage_evidence.py over 30 transcripts, 124,706 lines, 0 unparseable
  claude-in-chrome      386 calls
  claude_ai_Vercel       15 calls
  ZERO CALLS, EVER      : Gmail, Google_Drive, Claude_Docs, Canva, Netlify,
                          Notion, Stripe, Ironclad_Contracts   (8 of 10)
```

### (e) skills — **one gated, 47 routed**, and the restraint is the point

```
62 skills on disk. 16 ever invoked. 6 already carried disable-model-invocation.
```

**GATED: `graphify` only.** The global `CLAUDE.md` defines it as a `/graphify`
slash-command trigger, so model auto-invocation is **redundant by design**, and
the flag does not stop explicit invocation — proved by `domain-check` and
`sairn-skill-vetter`, which carry the flag and still appear in my invocation
counts. Largest never-invoked skill in scope: **43,292 bytes**.

**NOT GATED, DELIBERATELY —** `~/.claude/skills/` is **shared by all five
clones**. Gating `sairn-employee-auth-scaffold`, `email-diagnostics` or
`transactional-email` could stop hank, cc or fourth auto-invoking something they
need, and SAIRN does send email through Resend. **That decision is not
unilaterally mine.** `sairn-hover-auditor` (283,729 bytes, the largest on disk and
never invoked by me) is **structurally out of my scope** and is not touched.

### (f) the session-start check — BUILT: `tools/session_surface_check.py`

```
python tools/session_surface_check.py --selftest -> EXIT 0, 7 arms, 2 negative
python tools/session_surface_check.py            -> EXIT 0, 4s (walks 197 MB)
python tools/session_surface_check.py --no-usage -> EXIT 0, 0s (the hook path)
```

It lists skills with their gating, the reachable MCP servers **with the source of
that list named**, and measured usage. **It says what it is not:** not `/context`,
not `/mcp` — it reads disk and transcripts, which is a smaller claim, and it
cannot see the live prompt or its token cost.

**`--no-usage` exists because a 4-second SessionStart hook is a hook somebody
removes** — the same failure as a warning that fires on everything. In that mode
it prints *"TRANSCRIPTS: NOT READ … every 'never invoked' below is
COULD-NOT-TELL rather than zero"*, so the missing counts cannot read as zeros.

**NOT WIRED, and that is a scope call:** `.claude/settings.json` is not in this
batch's declared FILES. Paste-ready entry is in
`docs/2026-10-08-cody-b26-routed.md`.

**One discrepancy worth knowing:** the tool reports **6** reachable servers while
my prompt lists **10**. `claudeAiMcpEverConnected` only records servers that have
*ever connected*, so Canva, Notion, Stripe and Ironclad are reachable-but-never-
connected. The tool names its source rather than claiming completeness.

## item 2 — DONE. **The hypothesis is overturned: 76 of 86 are REAL.**

```
command : tools/scratch-archive/triage86.py -- every one of the 86 re-run ALONE in a
          `git clone --local` at aa2f014d, the same commit the suite ran, 420s bound each
commit  : ae70cf24        date: 2026-10-08
  REAL            76 of 86     fails alone on a clean tree
  COULD-NOT-RUN    7 of 86     exit 2 or the 420s bound; never folded into either
  ARTIFACT         3 of 86     passes alone
```

**The `docs/report-only-reachability.json` contamination accounts for 3 of 86.**
The verdict rule was fixed before the run so it could not be fitted afterwards,
and even the three artifacts are recorded as *"not reproducible in isolation"*
rather than *proven contaminated* — the weaker claim, and the one the evidence
supports.

**`git status --porcelain` was taken after EVERY probe and 0 of 86 dirtied the
clean clone** — so no probe inherited another one's mess, which is precisely what
the whole-tree run could not guarantee.

**420 s IS THE BOUND, NOT A MEASUREMENT.**
`tests/run_hover_audit_method_sabotage_probe.py` is the **only** probe to hit the
ceiling, so its isolated runtime is **at least** 420 s and unknown above that —
which is why it is COULD-NOT-RUN and not REAL. Best-evidenced candidate yet for
the long stall, and still **not named**: the stall could equally sit among the 671
probes that passed, which this run did not time.

**Committed:** `docs/2026-10-08-cody-suite-86-triage.md` (the table, per test, with
the isolated rc, the seconds and the suite's own one-line reason side by side) and
`docs/2026-10-08-cody-suite-86-triage.tsv` (the raw measurement).

**WHAT IT DOES NOT ESTABLISH, stated in the document:** not that the 76 are 76
*distinct* defects — several share a cause and nothing here clusters them; not
that the suite run was sound — the residue is still a real finding against
whichever probe wrote that file mid-run; and a single isolated run is one run.
