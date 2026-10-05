# Hank inventory — 2026-10-05

**Item 6.** Everything re-derived at HEAD (`e40f15fd` at session start) before
it was written. Predecessor: `docs/2026-10-04-inventory-hank.md`.

**`cc` IS LIVE AND HOLDS THREE OF THE FILES THIS DOC WOULD OTHERWISE EDIT** —
`docs/SAIRN-OPEN-WORK-INDEX.md`, `docs/defect-density-register.json` and
`docs/CRITICALITY-TIERS.md`, claimed 0.3h before I checked. So every row
correction and every register note below is **delivered as text in a file I
own**, not applied. Declared per PR §4.3 rather than reworded around.

---

## 0. I logged a gap last round that was already false, and this is the headline

**`docs/SAIRN-OPEN-WORK-INDEX.md` row 82, which I wrote yesterday, is wrong.**

It says `tools/tier_a_review_gate.py` *"has NO `--reseat` for a record whose
FILE SET matches no single commit, and that is the normal case — 16 of 22 open
records were in it."*

**`--reseat-shas` exists and does exactly that.** `tools/tier_a_review_gate.py:15-17`
documents three invocations; `:2634` dispatches it; `:2751` is `_reseat_base()`;
and `:2960-2971` is the file-set-subset logic the row claims is missing, which
admits containment only when exactly one commit contains the set, no commit
matches it exactly, and it lands inside `WEAK_BASIS_WINDOW_HOURS` — then stamps
`opened_at_sha_reseat_basis: 'file-set-subset'` so the weaker basis is never
indistinguishable from the stronger one.

Driven at HEAD:

    open records: 40
      reachable already   : 23 -- not touched
      reseatable          : 1   (subject twin or exact file set)
      reseatable, WEAK    : 6   (file-set subset in a 6h window)
      REFUSED             : 10  -- each named with its reason

**It landed at `b66b1ac9` on 2026-09-29 — the same day the inventory that first
claimed it was missing.** I carried that claim from
`docs/2026-09-29-inventory-hank.md` §4 item 3 into
`docs/2026-10-04-inventory-hank.md` §5 gap 5, and then into a new index row,
**without once running the tool.** Three documents, one unchecked assertion,
and the row I wrote is the most harmful of the three because it asks an
unassigned reader to build something that exists.

**This is the exact failure the dispatch's item 7 names**, committed by me on
the item I was writing *about* re-derivation. The grd_irr_zones premise last
round was somebody else's stale finding that I caught; this one is mine and I
did not.

---

## 1. Landed this session, with shas

| What | Sha | Verified by |
|---|---|---|
| `tools/gh_token.py --live` — authenticated `GET /user`, reporting token TYPE, scopes, expiry, and push-readiness, with three verdicts kept apart | *(this push)* | `tests/run_gh_token_live_probe.py` **20 passed, 0 failed** (new control). Real credential: exit 0, `GOOD`, login `SAIRN1`, classic PAT, `gist, repo, workflow`, push-ready, **expires NEVER** |
| The default path now **declines the reading that was the defect** in its own output: *"NOT VERIFIED: nothing above contacted GitHub"* | *(this push)* | probe arms E1–E3 |
| `github_token()` kept **pure** — no network | *(this push)* | probe arm E4, plus both direct importers driven live (`gh_push`, `gh_verify` compile; `plugin_upgrade_check.resolve_token()` resolves) |
| Eight report-only checkers accounted in `tools/report_only_checks.py` — **2 promoted, 6 declined with the measurement that decided each** | *(this push)* | all eight now appear in `--list`; promoted count 71 → 73; both promoted tools have a declared `CONTROLS_FOR` and neither is reported uncontrolled |
| `docs/2026-10-05-msb-bottle-scans-cost-note-hank.md` — the `match.cost||0` note, **routed to cc, not fixed** | *(this push)* | read at HEAD; `:1103`, `:4552`, `:4771-4779` |

### Item 1 — what the live check actually added

The old output could not distinguish a working credential from a revoked one.
Three things are now reported that were not:

* **Token TYPE, derived from a header's PRESENCE.** `x-oauth-scopes` **absent**
  means a fine-grained PAT (or an app token) whose permissions this tool
  **cannot enumerate** — stated as such. `x-oauth-scopes` **present and empty**
  means a classic PAT with **zero scopes**, which really is "none". Reading the
  header with `or ''` — the obvious spelling — reports the same string for both.
  **That is the same absent-vs-empty distinction `_from_env_files()` already
  makes between a missing `.env.local` and one that exists and is 0 bytes**, and
  not making it is what kept the original failure invisible for seven weeks.
  Arms B1–B4 are the known-bad for it.
* **Expiry, where ABSENT is the informative case.** GitHub emits
  `github-authentication-token-expiration` for any PAT that has one, so its
  absence means there is none — and the output says that **a rotation deadline
  set for this credential is therefore about a different credential.** Which is
  the finding that occasioned this work.
* **Push-readiness**, reported in both directions: a token carrying `repo` and
  one lacking it (arms C1/C2), so C1 is not passing because everything is
  called ready.

**The live call is opt-in and that is the load-bearing decision.** Six tools
import this module. Had the lookup fetched, a clone with no network would tell
all six **there is no token** — converting a working credential plus a dead
network into a missing credential. Arm E4 locks it.

### Item 2b — the eight, sorted by measurement rather than by name

Every one was **run and timed** first. The deciding question was not "is the
tool good" but whether its finding is a **bounded set that falls to zero** or a
**standing population** that would print the same number after every push.

**PROMOTED (2):**

| Tool | Measured | Why |
|---|---|---|
| `hover_routing_gap_check.py` | 1.75s, exit 1, **UNROUTED (7)** | Seven actionable items, each closed by routing it, and the count **rises** when the auditor logs something nobody picks up. The right shape. |
| `pattern_enumeration_sweep.py` | 1.4s, exit 1 | Clean on its first half (58 corroborated). **Its only finding this run was this session's own untracked probe file** (disk=624, tracked=623) — the tool working, and the best argument for running it after a push. |

**DECLINED, each with the measurement (6):**

| Tool | Measured | Reason |
|---|---|---|
| `hook_integrity_check.py` | 2.3s, exit 1 | **ALREADY WIRED** at SessionStart. Its entry exists so the registry stops under-reporting in that direction. |
| `citation_no_source_report.py` | 0.4s, exit 1 | **Its exit code keys on the wrong bucket** — see §4. |
| `message_assertion_audit.py` | 3.2s, exit 1, 43 of 240 files | A registered population; its own index row says so. Moves when somebody rewrites a suite, not when somebody pushes. |
| `idempotence_double_run.py` | **did not finish in 300s** | Runs every candidate twice by construction. Would eat the whole hook budget and still be cut off, producing a partial sweep reported as a sweep. |
| `hedge_carry_check.py` | exit 2 with no args | A CLI whose subject is a **dispatched instruction** — it exists in a chat turn, not in the repo. Wiring it means exit 2 after every push for ever, which trains readers to ignore exit 2. |
| `citation_line_drift_check.py` | exit 2 with no args | A CLI needing `--app` **and** `--prefix`, and the per-app answers are **not comparable** — 32/32 genuine on sairnfreedom, 4/4 deliberate on sairngrounds. An aggregate would be meaningless. |

---

## 2. In flight

| Item | State |
|---|---|
| Tier A review obligation on `04abf76e` | **assigned `fourth`**, 5 attack points, undischarged. And `--reseat-shas` now reports it **REFUSED [SHA_WRONG_WHEN_WRITTEN]** — the recorded sha was wrong when written, not orphaned by a rebase, and the tool's advice is *"FIX THE RECORD, not the sha"* because following it to its subject twin would preserve the mis-stamp faithfully. Not repaired here: `docs/tier-a-reviews.json` is not claimed, but repairing my own obligation record is a change to a review artefact I am the author of, and the gate's whole point is that the author is not the reviewer. |
| 1 strong-basis + 6 weak-basis reseatable records | **Available and unrun.** `python tools/tier_a_review_gate.py --reseat-shas --write` (and `--write-weak-basis` for the six). **Not run by me:** every one of the seven belongs to `cody`, `fourth` or my own obligation, and repointing another session's review record is not mine to do unasked. |

---

## 3. Blocked, and on whom

| Blocked | Holder | Evidence |
|---|---|---|
| The `match.cost\|\|0` register note | **`cc`** (live, 0.3h) | Holds `msb_bottle_scans`, landed its cell at `5ab3bcb5`, and holds the register, the index and CRITICALITY-TIERS. Delivered as paste-ready text in `docs/2026-10-05-msb-bottle-scans-cost-note-hank.md`. **Also not fixed in code, per the dispatch.** |
| Correcting index rows **82** and **845** | **`cc`** (holds the index) | Both corrections written out in §4 below. |
| A defect record for this session's own work | **`cc`** (holds `docs/defect-density-register.json`) | Recorded in the commit message with a `no-defect-record:` justification naming the holder, rather than waiting or editing under a live claim. |

---

## 4. Stale — including two of my own and one of somebody else's

| Where | Says | True at HEAD |
|---|---|---|
| **`docs/SAIRN-OPEN-WORK-INDEX.md` row 82 (MINE, yesterday)** | `tier_a_review_gate.py` has **no** `--reseat` for a file-set-unmatched record; *"no path to repair them at all"* | **FALSE.** `--reseat-shas` landed `b66b1ac9` 2026-09-29, with exactly the file-set-subset basis the row says is missing. **Correction: close the row as never-real, citing `b66b1ac9` and the live run (40 open: 23 reachable, 1 strong, 6 weak, 10 refused).** |
| **`docs/2026-10-04-inventory-hank.md` §6 (MINE)** | *"The 32 contradictory register rows named by `citation_no_source_report.py` remain unread by anybody."* | **The bucket is 0 at HEAD** — and the tool insists this be read with its history: it read 138, then 32, now 0, **and not one row was edited.** Each drop was a criterion of the tool being wrong. So the figure I carried was never a count of unread rows; it was a count of the tool's own false positives. |
| **`docs/SAIRN-OPEN-WORK-INDEX.md` row 845 (NOT mine)** | `assertion_label_shape_check.py` is **not** in the report-only registry | **It is.** Present in `--list` at HEAD. **Correction: close row 845.** Found while checking my own rows for duplicates — the same failure in another session's row, which is why §5 treats this as a class rather than my mistake. |
| `tools/report_only_checks.py` NOT_PROMOTED | 26 entries, each reasoned | Still accurate, and now 32. The **hole** was the defect, not the entries. |

---

## 5. Item 5 — near-duplicates: NO, those two were not the only ones

Asked whether index row 78 and the `grd_irr_zones` gate match were the only
near-duplicates from last round. **They were the only two I caught last round.
Checking systematically this round rather than by recall found more, and one is
worse than a duplicate.**

| # | What | Class |
|---|---|---|
| 1 | **Index row 78** — I nearly filed a second row for the review-gate false-match gap, a row I had opened myself five days earlier | Duplicate of **my own row**. Caught by reading neighbours before inserting. |
| 2 | **The `grd_irr_zones` gate match** | Duplicate of a known **false-positive class** — sixth instance of the gate matching a resource name out of prose. |
| 3 | **Index row 82** (new, this round) | **Not a duplicate of a row — a duplicate of LANDED WORK.** The row asks an unassigned reader to build `--reseat`, which shipped `b66b1ac9`. **Worse than #1:** a duplicate row wastes a reader's attention; a row contradicting a shipped capability spends their time building it twice. |
| 4 | **Index row 845** (not mine) | A row asserting a gap that is **closed**. Same class as #3, different author — which is the evidence that this is structural. |
| 5 | **The "32 contradictory rows"** carried through two inventories | A **stale figure**, not a duplicate — included because it was found by the same pass and would otherwise go unrecorded. |

**WHAT THE METHOD WAS, SO IT CAN BE REPEATED.** #1 was caught by luck — reading
the lines either side of an insertion point. #3 and #4 were caught
deliberately: `grep` the index for each subject I was about to write about, and
**run the tool the row names before trusting the row.** #3 would have been
caught last round by one command. That is the whole technique and it is cheap.

**I am not claiming this list is complete.** I checked the four rows I wrote
yesterday and the subjects I touched today. The other ~900 index rows are
unchecked by anybody, and §6 gap 3 is that there is no tool for this at all.

---

## 6. Gaps — ranked

**The competitor axis, again stated before the table:** every gap below is
internal tooling or process. **None is visible to a customer and no competitor
is affected by any of them**, so none is ranked on that axis and no competitor
evidence is cited, because there is none. Last round's one product-shaped gap
(the unreachable guestbook/client portal) is unchanged and still has **no
competitor evidence I could establish** — the audit corpus does not address the
feature and is demonstrably stale where it touches it.

| # | Gap | Severity | Competitor beating us? |
|---|---|---|---|
| **1a** | **29 of 73 registry entries NEVER RUN &mdash; and 4 of the 7 tools `cody` just claimed are among them** | **HIGH** | n/a &mdash; internal |
| **1b** | **`tools/push_retry.py` crashes printing its own usage (cp1252 vs its box-drawing docstring, no `reconfigure`)** | **MODERATE** | n/a &mdash; internal |
| **1** | **6 hook tools changed in commits with the manifest never regenerated** | **HIGH** | n/a — internal |
| **2** | **`citation_no_source_report.py` exits on its EXEMPT population, not its defect bucket** | **MODERATE** | n/a — internal |
| **3** | **Nothing checks an index row against the repo, so a row can ask for work that already shipped** | **MODERATE** | n/a — internal |
| **4** | No convention separating what a tool **MEASURED** from what it **ADVISES** | **MODERATE** (carried) | n/a — internal |
| **5** | `leg_clergy.faith_tradition` beside a named individual | **LOW** (carried, not chased) | n/a — internal |
| **6** | Guestbook / client portal no outside party can reach | **LOW–UNKNOWN** (carried, not chased) | **cannot say** |

### 1a. 29 of 73 registry entries never run — HIGH, and it dwarfs the gap I was sent to close

**Found by verifying my own fix instead of asserting it.** I added two entries
to `tools/report_only_checks.py`, then ran the sweep to confirm they execute.
They do not:

    NOT RUN: 29 of 73 -- "the sweep reached its 600s budget first.
             This is an UNKNOWN, not a clean result."

**The unrun set is a contiguous tail — indices 44 through 72.** Entries 0–43
execute; the last 29 never do. **Position in the list, and nothing else, decides
whether a registered checker runs — and nothing about an entry says where it
sits.** Verified: `idx == list(range(len-29, len))` is `True`.

**SO THE GAP I WAS SENT TO FIX WAS THE SMALLER HALF OF ITS OWN CLASS.** The ask
was eight checkers absent from the registry. The measurement says **27 more were
present, reasoned, controlled — and silently not running.** "In the registry"
reads as "wired", and for 40% of the registry that is false. It is the same
defect one layer in.

**The sweep is honest; nothing carries its honesty back.** It names every tool it
did not reach and calls the result UNKNOWN rather than clean. But that fact
lives in a 600-second run nobody waits for, while the `promoted:` field — which
is what a session actually reads — says only that the tool was promoted and on
what date. **Nothing in an entry can tell a reader it is dead.**

**WHAT I DID ABOUT MY OWN TWO, AND WHAT I DELIBERATELY DID NOT.** Both entries
now **state in their own `promoted:` field that they are at indices 71–72 and do
not run**, so neither can read as wired. Shipping them silent would have made me
instance 28 and 29 of the defect I was closing.

**I did not move them to the front to make them run, and it was a close call.**
They are the two cheapest additions available — 1.75s and 1.4s, 3.15s against
600s. But the cut boundary is at index 44, so inserting 3.15s ahead of it
**costs whatever currently runs at index 43 its slot**, and every candidate
there belongs to `cc`, `cody` or `fourth`. **Reordering this list is a decision
about whose control survives a budget nobody has raised** — not a decision to
make for three other sessions on the way past.

**NEXT ACTION, and it is a real decision rather than a tool:** the registry has
73 entries and capacity for ~44. Someone has to either raise the hook budget
(`.claude/settings.json` already allows 600; the sweep consumes all of it), split
the sweep across events, or **demote 29 entries honestly.** Until then, every
`promoted:` field in that file is a claim about intent, not about execution.

**The precedent says this has happened before and was fixed once:** index row 717
records *"THE REPORT-ONLY SWEEP HAD STOPPED COMPLETING IN PRODUCTION — 364s of
work under a 300s hook cap."* The cap was raised to 600 and **the work grew to
exceed it again.** A budget raised once against a list that only grows is not a
fix, which is why the next action above is a decision and not a number.

#### 1a-i. FOR `cody`, RIGHT NOW — four of the seven tools you just claimed never run

`cody` claimed, at `49473eef`, *"fixture locks for the never-claimed registry
tools whose rules are dead to their own evidence"* — seven tools. **Four of them
are in the 29 that never execute:**

    register_freshness_check          IN THE UNRUN TAIL
    advisory_lock_isolation_check     IN THE UNRUN TAIL
    service_role_tier_a_gate_check    IN THE UNRUN TAIL
    overrun_inversion_scan            IN THE UNRUN TAIL
    write_without_readback_check      runs
    accepted_risk_expiry_audit        runs
    dependency_graph                  runs

**This is not a conflict and I am not blocking anything** — cody holds those
files and should keep them. It is information cody cannot see from the files
themselves: **a fixture lock on a checker that never runs locks the criteria of
a control that produces no evidence on any cadence.** The lock is still worth
having (the tool can be invoked by hand), but the sentence *"dead to their own
evidence"* is truer than the claim knows — for four of the seven, the evidence
was never going to arrive, and the cause is **position in `REGISTRY`, not the
rule**. Flagged in the shared status registry as well as here.

### 1b. `tools/push_retry.py` crashes on its own usage path — MODERATE, new

Invoked with no arguments — which is what prints its usage — it raises:

    UnicodeEncodeError: 'charmap' codec can't encode characters in
    position 143-144  (cp1252, printing __doc__)

Its docstring carries box-drawing characters (`──`) and the file has **no
`sys.stdout.reconfigure(encoding='utf-8')`** — `grep -c reconfigure` returns 0,
where `tools/gh_token.py` has had exactly that line since it was written.

**Why it matters more than a cosmetic crash:** this is the tool that exists to
stop a push-race loop from folding one session's work into another session's
commit, and the first thing a session reaching for it does is run it to see how.
**It answers with a traceback.** I only got past it by guessing
`--loop --attempts 5` out of the source. Worked correctly once invoked properly
— pushed on attempt 5, authorship intact, verified.

**Not fixed:** a one-line `reconfigure` at the top is the fix, but
`tools/push_retry.py` is not in my claim and the same missing line is a
platform-wide pattern worth one sweep rather than five one-line commits. **Three
tools use `datetime.utcnow()`; this is a different list and nobody has counted
it.**

### 1. Six hook tools drifted from their manifest — HIGH, found in passing

`tools/hook_integrity_check.py` **runs at every SessionStart** and reported at
HEAD:

    DRIFT (6):
      citation_drift_hook.py       head=310a9919  manifest=e9040193
      hover_auditor_scope_gate.py  head=b00580c0  manifest=ce4eddd1
      rebase_state_guard.py        head=25785e51  manifest=8564768f
      report_only_checks.py        head=d9b28b40  manifest=487de2f2
      sairn_claim.py               head=c61ad0d9  manifest=1655c26a
      sairn_push_gate_hook.py      head=49fe2bd8  manifest=3c0236d4

Each is *"CHANGED IN A COMMIT AND THE MANIFEST WAS NOT REGENERATED — this is
the one a two-way check misses: a hook and its expectation moving together in
one push is what a legitimate change looks like."*

**HIGH because of which tools these are.** `sairn_push_gate_hook.py` is the push
gate; `hover_auditor_scope_gate.py` enforces the auditor boundary;
`sairn_claim.py` is the claim system. The check that would notice them being
edited is the check whose expectation is stale about them.

**DELIBERATELY NOT FIXED.** `--regenerate` would bless six changed hook tools in
one stroke on the authority of the session that noticed — a detector blessing
its own fix. It needs a human to look at six diffs. **And note what the tool
says a clean run would NOT mean, in its own words: that the hooks are correct,
only that they are unchanged since somebody ran `--regenerate`.**

*(I am adding a seventh: `report_only_checks.py` is in that list and I changed
it again today. Stated rather than left for the next reader to discover.)*

### 2. A checker exiting on the population it calls exempt — MODERATE

`tools/citation_no_source_report.py:299` — `return EXIT_FINDING if no_cite else
EXIT_CLEAN`. `no_cite` is **199 of 391** rows, and the tool's own output
classifies **194 of those as legitimately exempt** (57 admit they were not read
individually, 106 carry a §3.2 group stamp, 31 show a dated or field-list read).

**Meanwhile its real defect bucket — `CONTRADICTORY` — is 0.** So the exit code
fires for ever on rows the tool itself says are fine, and is silent on the
measurement that matters. **It is a one-line change and I did not make it:**
altering a checker's criteria needs its own claim and its own known-bad control,
and it is the reason this tool is declined rather than promoted. **Promote it
once the exit code keys on `contradictory`** — then it is a true ratchet sitting
at zero, which is the best promote shape available.

### 3. No tool checks an index row against the repo — MODERATE, new

Two rows found stale in one afternoon (**82**, mine; **845**, not mine), both
asserting a gap that shipped. ~900 rows are unchecked. The index is the document
sessions are told to read first, and **nothing re-references it against the
source** — which is cross-domain discipline 8, *nothing announces the day a
check stops testing anything*, applied to the work queue rather than to a check.

**What a tool could do, cheaply:** for any row whose deciding-test column
contains a runnable command, run it and flag rows whose own stated test now
passes. Not built — it is a real tool with a real false-positive surface
(a command that needs arguments, a test whose pass means something else), and
inventing it at the end of a batch is how an unvalidated checker enters the
registry. **Logged with the design named so it is not re-derived.**

### 4. Measured versus advised — MODERATE, carried, and now at two instances

Both found by hank, which is why the convention still waits:

* `citation_line_drift_check.py` advised *"this is the correction to apply"*
  from a measurement that could not support it (4 of 4 wrong on SAIRNgrounds).
* `gh_token.py` measured *"a token was found"* and was read as *"the token
  works"* — fixed today by making the output decline that reading itself.

**Still not written as a convention**, and the reason is unchanged: a session
that committed both instances inventing the rule from its own two is a detector
blessing its own fix. **It earns a convention when a third instance is found by
somebody else.**

---

## 7. What I will not claim

* **No live verification applies.** This change is two tools, one new probe and
  two documents. **Nothing deployed changed, so there is no deployed URL to
  check.** Saying "live-verified" would be the fabrication PR §3.2 exists to
  prevent.
* **I ran the full sweep to completion and my two entries did NOT execute** —
  see §6 gap 1a. They are accounted for in the registry and they are not
  wired, both entries say so, and I am not describing them as promoted
  controls. The two tools themselves were driven standalone (1.75s and 1.4s,
  both exit 1 with findings).
* **I did not read the other 27 unrun entries** to see whether any is load-
  bearing. The list is in §6 gap 1a; judging which of them matters most is the
  decision I am handing over, not one I made.
* **I did not read the six drifted hook diffs.** I report the drift; I have not
  judged whether any of the six changes was wrong.
* **I did not verify `msb_food_waste` has the same shape**, only that cc named
  it as the comparison.
* **I did not check the other ~900 index rows** for the staleness found in two
  of them.
* **`assertion_label_shape_check.py` being registered** is read from `--list`;
  I did not check whether its entry is *accurate*, only that it exists.
