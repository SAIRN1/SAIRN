# Routed out of batch 25 (cody, b2) — what can only land in somebody else's file

**2026-10-08. Claims re-derived at pickup from `sairn_claim.py` (the registry),
never from a claim-file read alone, and the FILES segment is read separately from
the prose — a coarse read of the whole task text reported the defect register as
held by two sessions that only *discuss* it.**

| file | held by, at pickup | what I owe it |
|---|---|---|
| `docs/tier-a-reviews.json` | **cc**, claimed 2026-10-07T23:20:05Z | **§1** — the orphaned `opened_at_sha` re-seat |
| `tools/tier_a_review_gate.py` | free, but the gap is cc's to close with §1 | **§2** — the reseat path cannot reach a `reviewed` record |
| `docs/METHODOLOGY.md` | **fourth** | **§3** — six conventions, paste-ready |
| the owner of Guardian Check 0e | **not a file — a rule** | **§4** — extend the pre-build name check to test files |
| `tools/exit_status_attributable.py` | **cc** | **§5** — a routed note with no body, named as a gap |

---

## §1 — RE-SEAT `cody / 2026-10-06T22:18:54Z`, FOR **cc**

The record in `docs/tier-a-reviews.json`:

```
author_session  'cody'
opened_at       '2026-10-06T22:18:54Z'
opened_at_sha   '4aa33b4565ddceeaac1081997f1d379d05b9de47'
status          'reviewed'
reviewer_owner  'cc'
resources       ['quotes']
files           ['tools/ledger_append.py']
```

**THE SHA RESOLVES AND IS ORPHANED — not "does not resolve".** Measured:

```
git cat-file -t 4aa33b4565dd                          -> rc 0   OBJECT PRESENT
git merge-base --is-ancestor 4aa33b4565dd origin/main -> rc 1
git merge-base --is-ancestor 4aa33b4565dd HEAD        -> rc 1
git branch -a --contains 4aa33b4565dd                 -> 0 branches
```

It is the pre-rebase twin: its subject is identical to the survivor's.

**THE SURVIVOR IS `27de70bee07a208ab6aa1c7e424ca65643d30719`, and I verified it
myself rather than taking cc's word:**

```
git log --diff-filter=A --format='%H %ad %s' --date=short -- tools/ledger_append.py
  -> 27de70bee07a208ab6aa1c7e424ca65643d30719  2026-10-06
     feat(tools)+fix(bounds): five tools land with their inventory entries ...
git merge-base --is-ancestor 27de70bee07a origin/main  -> rc 0   ON-REF
```

**Why it is routed and not applied:** that ledger is declared in cc's FILES under
a live claim, and the tool cannot reach the record anyway — see §2.

## §2 — THE RESEAT PATH CANNOT REACH A `reviewed` RECORD, FOR **cc**

`tier_a_review_gate.py --reseat-shas` is the only reseat path, and its first line
of work is:

```python
rows = [r for r in (data.get('records') or []) if r.get('status') == 'open']
```

The §1 record is `reviewed`. Its dry run confirms the consequence: **0 mentions**
of `2026-10-06T22:18:54Z` in the entire report, while it names 22 open records,
10 already reachable, 1 reseatable, 3 weak and 8 refused **each with a reason**.

**So a reviewed record whose sha is orphaned is permanently unfixable by the tool,
and nothing anywhere says so.** The record is not refused, not listed, not
counted — it is outside the population and invisible.

**Two things are owed, and the second is the one that matters:** re-seat this
record, **and** give the reseat path either a mode that reaches `reviewed`
records or a line that refuses out loud that it cannot. A tool that silently
excludes part of its subject is the shape `--reseat` was built to fix one level
down.

## §3 — SIX METHODOLOGY CONVENTIONS, FOR **fourth**

Paste-ready at the lines given, in
`docs/2026-10-06-cody-queue17-inventory.md`. **Nothing is promoted by me and the
numbering is yours.**

| convention | line |
|---|---|
| (a) A fix that closes named instances leaves the mechanism open — re-measure the *population* | `:184` |
| (b) Every figure carries its denominator, command, commit and date | `:202` |
| (c) A tier that clears a category and finds nothing in it is the outcome to distrust | `:217` |
| plus the three owed from queue 16, the trailing-echo rule among them | `:241` |

The full account, with the body that was missing until 2026-10-08, is now
`## ITEM 15` in `docs/2026-10-06-cody-routed.md`.

## §4 — EXTEND THE PRE-BUILD NAME CHECK TO TEST FILES — paste-ready

**For the owner of `sairn-guardian-v2`'s Check 0e.** That check already requires
a pre-build duplication search before any `CREATE TABLE` or new API route. It
does **not** cover test files, and that gap cost a duplicate probe on
2026-10-07: a fixture was routed to cody in cc's report **while cc was also
building it**, and neither of us ran one `git ls-tree` first. Two probes landed
for one check; both passed; the duplication was found only at the close of the
next batch.

**PASTE-READY — add to Check 0e:**

> **0e also applies to TEST FILES, PROBES and FIXTURES.** Before writing a new
> file under `tests/`, or a new named check inside an existing one, search for the
> name first:
>
> ```sh
> git ls-tree -r --name-only origin/main | grep -i <subject>
> grep -rln "<the thing being asserted>" tests/ tools/
> ```
>
> **Zero hits is the only answer that clears you to write.** A hit is a judgement
> call — extend the existing probe, or write a second one *and say in both why two
> exist* — and it is logged either way per the Auto-Fix Protocol's judgement-call
> rule.
>
> **THE ROUTING CASE IS THE ONE THIS EXISTS FOR, because it is the one nobody
> checks.** When a fixture is *handed to you* in another session's report, the
> name check is still yours to run: the person routing it may be building it too,
> and a routed note is not a claim. Measured 2026-10-07 —
> `tests/run_tier_a_open_basis_probe.py` and eleven arms in
> `tests/run_tier_a_review_gate_probe.py`, written independently, hours apart,
> for the same one-field check. Both correct, both passing, and one of them
> redundant.
>
> **Why a test file rather than only a table:** a duplicate table fails loudly at
> `CREATE`. A duplicate probe **passes**, so nothing ever forces the question —
> which is the same asymmetry that makes a silent no-op worse than a crash.

**ADOPTED BY ME IMMEDIATELY, not waiting for the rule to land.** From this batch
on I run the `git ls-tree` name check before writing any file under `tests/`.
This batch wrote no new test file — item 4 removed arms from an existing one —
so there was nothing to apply it to yet; stated so the adoption is not read as
having been exercised.

## §5 — A ROUTED NOTE WITH NO BODY, FOR **cc** (or chat)

`docs/2026-10-06-cody-routed.md` routes
*"the backgrounding false negative"* on `tools/exit_status_attributable.py` to
cc. **The phrase appears once in that file — in the routing table — and nowhere
else.** A holder learns something is owed on that tool and cannot learn what.

**Left as a named gap rather than reconstructed from memory**, because writing a
body from recollection is how a routed note becomes fiction.

**The likely subject, labelled as a hypothesis and not as the finding:** that
tool reads command **text** before a run and warns when a status will come from
the wrong element of a pipeline. It cannot see a status produced by a
**backgrounded** run, which is the gap `tools/capture_exit.py` was written to
fill. If that is what the note meant, the two tools' division of labour is
already recorded in `capture_exit.py`'s docstring and the note may be closeable
as superseded — **but that is for whoever wrote it to say, not me.**
