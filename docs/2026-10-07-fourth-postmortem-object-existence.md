# Blameless postmortem — I used an object-existence test as a reachability test

**fourth (Ted), 2026-10-07. Subject: `git cat-file -e <sha>^{commit}` cited as
evidence that three commits were UNREACHABLE.** Blameless in the real sense:
the question is what made the wrong move the reasonable one, and what in the
system has to change so the next person doing the reasonable thing gets it
right.

---

## WHAT I DID

On 2026-10-06, during batch 11, I landed six commits and then ran
`git pull --rebase` onto eleven upstream commits. Every one of my six was
rewritten. Three of them — `100b82fc` (now `6b77545f`), `7c911e5c` (now `326d277e`), `6984634e` (now `7eabd192`) — were cited by
SHA in two dated documents I had written twenty minutes earlier.

`.githooks/post-rewrite` ran and reported, correctly, *"The map named 6
rewritten commit(s) and NONE of them is cited in the tracking documents."* It
re-seats the defect register and the generated pair; a dated inventory is
neither, so its clean verdict was **true and did not cover me**.

I re-seated the three citations by hand to their post-rebase equivalents and
wrote, in both documents, that the pre-rebase SHAs *"are UNREACHABLE"*. I
verified that with:

    git cat-file -e <sha>^{commit}

**It returned OK for all three.** I read the exit code as confirming the claim
and shipped the sentence.

## WHAT WAS ACTUALLY TRUE

| sha | what I wrote | what it is |
|---|---|---|
| `100b82fc` (now `6b77545f`) | UNREACHABLE | **ORPHANED** — object present, no ref reaches it |
| `7c911e5c` (now `326d277e`) | UNREACHABLE | **ORPHANED** |
| `6984634e` (now `7eabd192`) | UNREACHABLE | **ORPHANED** |

`cat-file -e` tests whether the **object exists**. An orphaned commit's object
survives until `git gc`, so it answers OK. The test I ran **could not have
returned the answer I claimed it did.**

The conclusion happened to be close enough to act on — those SHAs are indeed
useless to another clone. **The verification was worthless**, and that is the
finding. A check that cannot fail would have let the next re-seat pass itself
as verified, which is the shape this platform has paid for repeatedly.

## WHY IT MADE SENSE AT THE TIME, and this is the part worth keeping

1. **The two commands are indistinguishable at the call site.** `cat-file -e`
   and `merge-base --is-ancestor` have the same shape, the same exit-code
   convention, and neither name says which question it answered. Nothing in the
   output disambiguates them.
2. **The failure is one-directional and silent.** An existence test never
   reports a reachable commit as missing — only a missing one as fine. So it
   always errs toward *"this is OK"*, which is the direction nobody
   double-checks.
3. **The surrounding evidence agreed with me.** `git log` no longer showed
   those commits and `git show` on the new SHAs showed the right content.
   Every other signal pointed at the conclusion I reached, so a test that
   agreed looked like confirmation rather than a non-answer.
4. **I was in a correction, which is the worst moment for care.** I had just
   found a real defect (my own orphaned citations) and was fixing it. Attention
   was on the content of the sentence, not on the command underneath it.
5. **`cat-file -e` is the obvious command for "is this sha any good".** It is
   what a careful person reaches for. That is precisely why this needed to
   become a convention rather than a note.

**Nothing here is a lapse of diligence.** The command was run deliberately, its
exit code was read, and the claim was written against it. The system let a
correct-looking verification be the wrong verification.

## HOW IT WAS CAUGHT

The dispatch for batch 12 asked me to re-derive every reachability verification
I had recorded, using `merge-base --is-ancestor`. The redo over seven of my
documents found 12 distinct SHAs asserted about — 7 ON-REF, **3 ORPHANED**, 2
ABSENT — and the three ORPHANED are exactly the three I had verified with an
existence test. `PROGRAM_EXIT=0`, run at `eb430f25`.

**Not caught by review, and it would not have been.** The sentence reads
correctly and the command beside it looks like support.

## AND IT WAS NOT ONLY MINE — THE SAME DEFECT WAS LIVE IN A GATE

`tools/tier_a_review_gate.py` resolved each Tier A record's subject commit with
`git rev-parse --verify --quiet <sha>^{commit}` — the same class of test — and
then diffed against it and printed an ordinary FRESH or STALE verdict.

At `eb430f25` `docs/tier-a-reviews.json` cited **seven orphaned 40-character
SHAs**, and `** STALE ** moved since 00030f2d11b7` was printed on an **open**
obligation: a diff against a commit no other clone has, reported as a plain
verdict with no caveat.

**The gate already contained the correct test.** Its own `_is_reachable()` uses
`merge-base --is-ancestor`, about 1,500 lines below the freshness path. The
file carried both the strong and the weak form of one check, and the path that
mattered used the weak one. **A file holding two forms of the same check will
be read by whoever is nearest.**

## THE ONE SYSTEM-LEVEL FIX, IN AN EXISTING CHECK

**Fixed:** the freshness path now asks reachability after resolving, accepting
`origin/main` **or** `HEAD` (a record opened at an unpushed local commit is
ordinary work, not an orphan), and refuses with a COULD-NOT-TELL that **names
orphaned** so it reads differently from *"never fetched"*. Four open records
now report it correctly.

**And the arm that enforces it**, in the existing
`tests/run_tier_a_review_gate_probe.py` — four arms, two negative plus a paired
positive on a synthetic source:

* the freshness path does not stop at an existence test — it asks reachability;
* the refusal names ORPHANED;
* **NEGATIVE:** an existence-only synthetic source is reported as missing the
  check;
* **PAIRED POSITIVE:** a reachability-asking synthetic source is reported as
  having it, so the arm is not rejecting everything.

**Verified:** `ALL ARMS PASS`, 215 ok arms, exit 0, run twice at this SHA, both
clean. **Ablated:** guard removed → probe exit 1 naming both arms; file
restored byte-identical; guard back → exit 0.

## THE SECOND MISTAKE, WHICH IS THE SAME ONE A LEVEL UP

**My first version of that arm was vacuous and the ablation is the only reason
I know.** It sliced the gate's source from the resolve message to
`def _file_set_index` — roughly 1,500 lines — which **swallowed the definition
of `_is_reachable` itself**. So `'_is_reachable(' in slice` was true whether or
not the freshness path called it. **With the guard removed, the probe stayed
green.**

I had written an arm to enforce *"test the method, not the verdict"* and the arm
tested nothing. Had I not ablated it, I would have shipped a convention, a fix,
and a guard that could not fail — and reported all three as verified.

**Fixed:** the window is bounded to 3,000 bytes, truncated at
`def _is_reachable`, **the bound is asserted by its own arm**, and the
extraction is exercised in both directions against synthetic sources.

## WHAT I AM NOT CLAIMING

* **The recurrence is open and named.** This fixes ONE call site in ONE tool.
  Ten other files use `cat-file` or `rev-parse --verify`:
  `tools/conflict_marker_preflight.py`, `tools/credential_purge_check.py`,
  `tools/doc_sha_reseat.py`, `tools/gh_push.py`,
  `tools/landing_verification.py`, `tools/review_ledger_reseat.py`,
  `tools/sairn_push_gate_hook.py`, `tools/source_manifest.py`,
  `tests/claims/run_push_verify_probe.py`, `tests/run_tier_a_reseat_probe.py`.
  **None has been read** to decide whether it asks existence where it means
  reachability. Recorded in the defect register's `recurrence_open`.
* **The seven orphaned ledger SHAs are not fixed.** The gate now *reports* them.
  Whether each record is re-seated or retired is a per-record decision for its
  author — reseating them here would be reclassifying other sessions' records.
  Routed in `docs/2026-10-07-fourth-routed.md` item 2.
* **No conclusion in any document changed.** All 7 SHAs I had called REACHABLE
  are genuinely ON-REF. Only the method and the wording were wrong, and both
  documents now say so in place rather than being quietly swapped.

## THE CONVENTION

**19. Object existence is never evidence of reachability.** Three states where
an existence test sees two:

| state | `cat-file -e` | `merge-base --is-ancestor` |
|---|---|---|
| **ON-REF** | OK | yes |
| **ORPHANED** — present, no ref, gc-eligible, absent elsewhere | **OK** | **no** |
| **ABSENT** | fails | no |

The rule bites wherever the word in the sentence is **still**, **current**,
**landed**, or **on main**. It does not apply when the question really is *"can
I read this object"*.

Written into `docs/2026-09-13-cross-domain-disciplines.md` as item **19** and
recorded in `docs/METHODOLOGY.md` as **chat-adopted** — not self-promoted,
because promoting a convention out of my own defect is the
detector-blessing-its-own-fix shape convention **11** refuses, and this one came
from my own mistake twice over.
