# The Tier A obligation queue — triage by age, and the tool that stops it happening again

**fourth, batch b18, 2026-10-14. Measured at clone HEAD `ebd8f9bd`.**

> **RE-MEASURED AFTER THE REBASE, AND THE NUMBER MOVED — read this before
> quoting any count below.** Between taking these figures and pushing them,
> `git pull --rebase origin main` brought in **50 commits**, and the register
> went **18 → 19 open** again:
>
> | | |
> |---|---|
> | open obligations | **19** (`reviewer_owner`: cody 5, **cloud 4**, cc 4, **fourth 3**, hank 3) |
> | what arrived | **one new obligation assigned to `fourth`**, `hank` 2026-10-14T13:50:42Z, `leg_*` — **3h old, inside the 24h deadline, not overdue** |
> | what did NOT change | the four `cloud` rows, both of my overdue rows (now 397h and 338h), and every disposition in §2 |
>
> **The triage below is therefore correct and already one row out of date**, and
> that is the honest state rather than a flaw to paper over: **a queue
> measurement is a snapshot, which is the eighth cross-domain convention
> restated** — re-run `--list` rather than quoting §0. The new row needs no
> disposition yet; it needs one in 21 hours, which is exactly what §3's surface
> is for.

**WHY THIS DOCUMENT EXISTS AND NOT A LONGER QUEUE.** My own b17 handoff left a
**418-hour** Tier A obligation open and said so in capitals. It was discharged
this batch (`docs/2026-10-14-fourth-b18-tier-a-queue14-discharge.md`) — but a
17-day-old obligation is not a scheduling accident, and the reason it happened
is mechanical: **nothing anywhere tells a session, at the moment it starts, that
it owns an overdue review.** `--list` answers that question perfectly and only
when somebody thinks to ask it. **This document triages what is there now, and
specifies the surface that would have made the 418 hours impossible.**

---

## 0. THE MEASURED STATE — every figure with its command

```
CMD PYTHONIOENCODING=utf-8 python tools/tier_a_review_gate.py --list     ->  EXIT 1
    19 open Tier A review obligation(s)        [before this batch]
    18 open                                   [after the b18 discharge]
    17 of them are past the 24h deadline     [of the 19; 16 of the remaining 18]
    6 are STALE BY CODE      -- a named file moved since the commit recorded
    7 could not be compared  -- UNSTAMPED or COULD-NOT-TELL
```

```
CMD PYTHONIOENCODING=utf-8 python tools/tier_a_review_gate.py --reseat-shas   (DRY RUN)
    records examined : 18
    reachable already: 12
    reseatable       :  1   [EXACT FILE SET]
    reseatable, WEAK :  1   [file-set subset, 0.4h apart]
    REFUSED          :  4   [NO_OBJECT_IN_CLONE]
    REVIEWED records carrying a sha: 88 -- 34 of them also dangle, NOT examined in this mode
```

| | count | command |
|---|---:|---|
| open obligations, after b18 | **18** | `--list` |
| of those, past the 24h deadline | **16** | ages over the open records; `--list` said 17 of 19 **before** the b18 discharge |
| of those, past the 48h **takeover** gate | **16** | the same 16 — the only two inside 24h are both 4h old. `OWNER_STALE_HOURS = 48` at `tools/tier_a_review_gate.py:1322` |
| oldest still open | **399h** (`fourth` → `cloud`, 2026-09-28T00:16:59Z) | `--list` |
| **owners holding them** | cody 5, **cloud 4**, cc 4, hank 3, fourth 2 | `reviewer_owner` over the open records |
| **authors who opened them** | cody 6, hank 6, fourth 3, hover2 2, cc 1 | `author_session` |
| open records whose recorded sha is unusable | **6 of 18** (4 refused + 1 reseatable + 1 weak) | `--reseat-shas` |
| **REVIEWED** records whose sha also dangles | **34 of 88** | `--reseat-shas` |

**THE 34 IS THE FIGURE NOBODY HAS LOOKED AT.** The dry run says it plainly:
*"RE-RUN WITH `--include-reviewed` TO EXAMINE THEM. Until then this run says
nothing about them, which is not the same as saying they are fine."* **A
discharged review whose commit no longer exists cannot be re-derived by anybody
asking what was reviewed.** That is not urgent and it is not mine, but it is
larger than the open queue it sits behind.

---

## 1. THE FINDING THIS TRIAGE PRODUCED — four obligations are assigned to a session that has not run in 17 days

**`cloud` holds four open obligations, including two opened in the last 30
hours, and `cloud` has not run since 2026-09-27.**

```
CMD git log -1 --format="%h %ad %s" --date=iso -- .claude/claims/cloud.json
    e3b8b0cd 2026-09-27 03:52:51 +0000 claim(cloud): sairngrounds external
             competitive-gap audit + lane handoff, docs/cloud-research only

CMD (mtime of .claude/claims/cloud.json)   ->  2026-09-27T11:05:14Z
CMD git log --oneline -500 | grep -ci "cloud claims"   ->  0
```

**WHY IT KEEPS HAPPENING, and it is one function:**

```
CMD sed -n '1329,1343p' tools/tier_a_review_gate.py
  def eligible_reviewers():
      """Sessions that may be assigned a review, from the claim files on disk."""
      names = sorted(f[:-5] for f in os.listdir(CLAIMS_DIR) if f.endswith('.json') …)
      names = [n for n in names if not is_hover_session(n)]
      return names if len(names) >= 2 else None
```

**Eligibility is "a claim file exists on disk".** There is no liveness test of
any kind, so a session that stopped running three weeks ago is still a candidate
every time `assign_owner` runs (`:1345-1376`, least-loaded, tie-broken
alphabetically). `cloud`'s file is still there, so `cloud` still gets work.

**That is the defect, and the design is otherwise right.** The docstring is
explicit that the roster must not be a hardcoded list — *"never a guess and
never a hardcoded roster"* — and it is correct about that. **The remedy is not a
roster, it is a liveness fact**, which the repo already has: the mtime and the
last commit of the claim file, and `~/SAIRN-SESSION-LOCKS/status`.

**Consequence, stated exactly:** an obligation assigned to a session that never
runs again **can only be closed by `--takeover`**, and nothing surfaces that it
needs one. Those four are not slow. **They are stuck**, and two of them were
created stuck this week.

---

## 2. THE TRIAGE — all 18, by age, with one disposition each

**The four dispositions, and the rule behind each**, because a triage that does
not say its rule is a list of opinions:

| disposition | rule |
|---|---|
| **DISCHARGE (mine)** | the owner is `fourth` and `fourth` is running. Mine to do, in age order, no exceptions and no reassignment |
| **TAKEOVER NEEDED** | the owner has not run since 2026-09-27 and the 48h gate is long past. `--takeover` is the only instrument that expresses this, and it **records** the handover rather than overwriting a verdict |
| **STAYS WITH ITS LIVE OWNER** | the owner has committed within the last 24h. It is overdue, not stuck — and the fix is §3's surface, not a reassignment |
| **FIX THE SHA FIRST** | the recorded commit does not resolve, so the obligation can only receive a state review. Worth one command before the review, not after |

| # | age | author | resources (n) | owner | **disposition** |
|---:|---:|---|---:|---|---|
| — | ~~418h~~ | hank | `alf_staff`, `sen_visits` | fourth | **✅ DISCHARGED THIS BATCH** — `docs/2026-10-14-fourth-b18-tier-a-queue14-discharge.md`. One finding on the one attack point never reviewed |
| 1 | **399h** | fourth | 12 | **cloud** | **TAKEOVER NEEDED.** The oldest open obligation on the platform is assigned to a dead session. Author is `fourth`, so **I may never review it** — it needs any other live build session |
| 2 | **395h** | cody | 2 (`dnt_ar`, `dnt_revenue`) | **fourth** | **DISCHARGE (mine) — b19 ITEM 1.** Five named claims to test, one file (`tests/reachability/resource_demand_probe.py`). **FIX THE SHA FIRST**: `f88105a88287` is `REFUSED [NO_OBJECT_IN_CLONE]` |
| 3 | **337h** | hover2 | 2 (`leg_insurance`, `mech_checks`) | **fourth** | **DISCHARGE (mine) — b19 ITEM 2.** Retrospective, opened by hank on hover2's behalf. **Its verdict is pre-refused unless it names what it opened and looked for**, so it needs a real drive of `hover_citation_linter.py` — read-only, in my own clone's mirror, **never by entering `Documents\SAIRN-hover`** |
| 4 | 335h | hover2 | 3 | **cloud** | **TAKEOVER NEEDED.** Re-opened after a de-duplication keyed on a non-unique field deleted it once already |
| 5 | 216h | fourth | 1 | cody | STAYS WITH ITS LIVE OWNER |
| 6 | 209h | fourth | **246** | cody | STAYS WITH ITS LIVE OWNER. 246 resources — the real Supabase snapshot; big, not complicated |
| 7 | 201h | cc | 2 | cody | STAYS. **FIX THE SHA FIRST** — `c0ef09bdad7e` is reseatable on a **WEAK** basis (file-set subset, 0.4h apart) and needs two flags on purpose |
| 8 | 199h | hank | 1 (`sen_settings`) | cody | STAYS. **STALE BY CODE** — `sairnsenior.html` moved since `f98982410649` |
| 9 | 199h | hank | 1 (`sdn_projects`) | cody | STAYS |
| 10 | 61h | hank | 9 | cc | STAYS. **STALE BY CODE** — four `api/` files moved |
| 11 | 61h | cody | 7 | cc | STAYS |
| 12 | 51h | cody | 23 | cc | STAYS. **STALE BY CODE** |
| 13 | 31h | cody | 27 | hank | STAYS. **STALE BY CODE** |
| 14 | 30h | hank | 11 | **cloud** | **TAKEOVER NEEDED — and it is 30h old, created already stuck** |
| 15 | 29h | hank | 32 | cc | STAYS. **FIX THE SHA FIRST** — `f82a177b6729` refused, no object in clone |
| 16 | 27h | cody | 5 | hank | STAYS. **STALE BY CODE** |
| 17 | **4h** | hank | 10 | **cloud** | **TAKEOVER NEEDED — four hours old and already unreviewable by its owner.** This is the clearest single proof that §1 is a live defect and not a historical one |
| 18 | 4h | cody | 3 | hank | STAYS — **the only one inside the 24h deadline** |

### What I did NOT do, and why — stated so it is a decision and not an omission

1. **I did not hand-edit `reviewer_owner` on any record.** The owner stamp
   exists *because* four obligations were double-reviewed on 2026-09-21
   (`tools/tier_a_review_gate.py:2687-2699`). Re-pointing it by hand from one
   build clone is the exact collision it was added to prevent. **`--takeover` is
   the only instrument that records a handover**, and it is the caller's own
   name it records.
2. **I did not `--takeover` the four `cloud` obligations myself.** A takeover is
   not a filing action — it makes me the reviewer, and **four Tier A reviews in
   one batch produces four thin verdicts.** The discharge in this batch is
   ~9,000 words over one obligation because that is what the artefact costs.
   **A takeover I cannot then discharge is worse than leaving it visible**: the
   queue would look owned and moving. *(And #1 is `fourth`-authored, so I am
   refused on it by the gate itself, correctly.)*
3. **I did not run `--reseat-shas --write`.** One record is strong-basis
   reseatable and one is weak. The register is shared, the weak basis is a
   containment claim rather than an equality claim, and the tool splits them
   across two flags deliberately. **Reseating somebody else's record from my
   clone is a register-wide write on a measurement I did not take.** Named as an
   ask below instead.
4. **I did not discharge obligations 2 and 3 in this batch** even though both
   are mine. Both are named as b19 items 1 and 2 **in age order**, which is the
   same rule that produced this batch's item 2. Obligation 3's verdict is
   *pre-refused* unless it names what it drove — that is a real drive, not a
   read, and it is not something to start in the last hour of a batch.

---

## 3. THE ASK TO cc — a session-start surface for any obligation over 48h

**THIS IS A REQUEST, NOT A BUILD. `tools/` is cc's and my b18 claim declares
`docs/` only.** No file under `tools/` is written by this batch.

### Why a new surface rather than "remember to run `--list`"

`--list` already produces every fact needed. **It produced them on 2026-09-27
and on every day since, and the obligation still sat 418 hours**, because the
output only exists when somebody types the command. **The failure is not missing
information. It is information that has to be requested.** The platform already
solved this exact shape once: the shared status registry is *"handed to you
automatically at session start by a `SessionStart` hook"* precisely because a
registry nobody reads is indistinguishable from one nothing writes to.

### What it must do

1. **Print, at session start, every open obligation OWNED BY THIS SESSION whose
   age is over 48 hours**, loudest first, with its age in hours, its author, its
   resources and the exact `--discharge` command to close it. **Nothing else** —
   a surface that prints all 18 is a wall of text that gets scrolled past, which
   is how this one got missed.
2. **Print a second, shorter block: obligations whose OWNER has not run
   recently**, with the measured liveness fact beside each one and the
   `--takeover` command. **This is §1's finding made visible rather than
   rediscovered**; it is the block that would have caught obligation #17 four
   hours after it was created.
3. **Say the two counts even when both are zero** — *"0 overdue owned by you,
   0 stuck on a dormant owner"*. A silent tool and an absent tool look the same
   at session start, and this platform has the shared-status registry's own
   warning on exactly that point.
4. **Define "has not run recently" from a MEASURED fact, never a roster.** The
   mtime and last commit of `.claude/claims/<session>.json`, or
   `~/SAIRN-SESSION-LOCKS/status`. **The threshold must be stated in the output**
   — *"no commit in 17 days"* — so a reader can disagree with it. Do not
   hardcode a session name; `cloud` is today's instance, not the rule.
5. **FAIL CLOSED, PR §1.11.** If `docs/tier-a-reviews.json` is missing or
   unparseable, or if `tier_a_review_gate.py` is absent, it must say **which
   file**, say the check did not run, and **exit 2 COULD NOT RUN — never 0**. A
   hook that silently prints nothing when the register moved is worse than no
   hook, because the absence of a warning becomes evidence there is nothing to
   warn about.
6. **It must not write anything.** Not a discharge, not an assignment, not a
   takeover. Per the eleventh cross-domain convention, a tool that surfaces work
   and also disposes of it is a detector blessing its own fix. **Print the
   command; let a session run it.**

### The failing-first arms, so the surface cannot ship untested

| arm | bad input | must happen |
|---|---|---|
| **A1** | a register containing one obligation owned by this session, 100h old | it is printed, with 100h and the ready-to-paste `--discharge` command. **Fails today — there is no such surface** |
| **A2** | the same obligation at **47h** | **not** printed in block 1. The threshold is a threshold, not a mood |
| **A3** | `docs/tier-a-reviews.json` **absent** | **exit 2, names the file, says the check did not run.** Not exit 0, not a silent skip. This is the arm the whole thing turns on |
| **A4** | the register present and **nothing overdue** | prints `0 / 0` **and exits 0**. The both-zero line is the arm, not the exit code |
| **A5** | an obligation owned by a session with no commit in 17 days | appears in block 2 with the measured fact and the `--takeover` command — **driven with a fixture claim file, never against the live `cloud`** |
| **A6** | an obligation whose `owner_assigned_at` is **unreadable** | reported as a third state, never as fresh and never as overdue. `owner_age_hours` already returns `None` for this (`tools/tier_a_review_gate.py:1379-1384`); the surface must not coerce it to 0 |

**A3 and A6 are the two a reviewer would cut, and they are the two that matter:
A3 is the fail-closed leg, and A6 is the one where a missing stamp quietly
becomes a clean bill.**

### Two smaller asks, same owner

* **Add a liveness note to `eligible_reviewers()`'s output or to `--list`.** Not
  a change to assignment — **changing who gets assigned is a bigger decision
  than I should route in a sentence** — but `--list` printing *"owner `cloud`:
  no commit in 17 days"* beside those four rows costs nothing and makes the
  takeover self-evident. If assignment *is* changed to skip dormant sessions,
  it needs its own arm proving a roster of two does not collapse to zero.
* **`--reseat-shas --write`** on the one strong-basis record (`hank`
  `2026-10-13T09:03:35Z`, `f0e81b92459c -> 8a572a6ead25`, EXACT FILE SET), and
  a decision on the weak one. **And then the 34 dangling REVIEWED records**, via
  `--include-reviewed` — the tool is explicit that the default run says nothing
  about them.

---

## 4. THE METHODOLOGY POINT, in one paragraph

**The 418 hours were not caused by anybody forgetting.** They were caused by a
queue whose only reader is a command, held by a session that had no reason to
run it, about work it had already reviewed and written up on disk
(`docs/2026-09-29-tier-a-review-verdict-hank-queue14-fourth.md`) without the
register ever learning. **Three separate mechanisms each worked exactly as
designed and the obligation still aged 17 days**: the gate assigned an owner,
the owner reviewed the code, and the register waited to be told. **The fix is
not more discipline. It is one unasked-for line at session start** — which is
the same answer the shared status registry reached, for the same reason, on
2026-09-16.
