# Item 99 — graduated consent: Bitcoin Core's model, and the one property SAIRN is missing

**2026-09-15 (Fourth).** Asked: does Bitcoin Core's consent model for
irreversible changes have anything to teach a platform whose own register lists
**55 Tier A resources with no removal path**?

**Answer: yes, but not the obvious thing. The lesson is not "review more" — this
platform already reviews hard, and independently. It is that Bitcoin Core makes
consent a property OF THE ARTIFACT, and SAIRN keeps it in a different document
with no link in either direction.**

---

## 1. What Bitcoin Core actually does, and which part is transferable

Three structural properties, not one:

| | Property | Why it exists |
|---|---|---|
| **(a)** | **Consent is attached to the change.** ACKs are comments on the PR. You cannot read the change without reading who agreed to it | There is no second place to go and no way to lose the link |
| **(b)** | **The KIND of consent is named.** Concept ACK, Approach ACK, **utACK** (untested), **tested ACK**, Code Review ACK, NACK | *"I read it"* can never be counted as *"I ran it"*. A maintainer counting ACKs is counting distinguishable things |
| **(c)** | **Consent is measured over a WINDOW with a way to still fail.** BIP9 versionbits: SIGNALLING → LOCKED_IN → ACTIVE, with a timeout | Agreement is a process with a failure mode, not a switch somebody flips |

And the reason all three exist at all: **a consensus change cannot be rolled
back.** The bar is set by blast radius, not by diff size — a one-line consensus
change gets more scrutiny than a thousand-line GUI change.

---

## 2. SAIRN already has (b), and does it better than most

The rule is written down. `docs/CRITICALITY-TIERS.md` §"What a tier is FOR":

> *"A change touching a Tier A resource is where independent review and a live
> check stop being optional."*

And the practice is real. Of **32** rows in `docs/SAIRN-OPEN-WORK-INDEX.md`
whose status says REVIEW, **27 cite running something** — a probe, a
measurement, a reproduction — rather than only reading. One row states the
distinction outright, in the platform's own words rather than Bitcoin's:

> **`REVIEWED 2026-09-14 (Hank), measured not read`**

That is a tested ACK, invented independently and expressed better. There is even
an author-blind review protocol on record (item 44,
`docs/2026-09-14-rubric-blind-grading-protocol.md`).

**So (b) is present as a habit.** What it is not is a *vocabulary*: it is ad hoc
prose, so it cannot be counted, and a row that omits the distinction is
indistinguishable from one where nobody thought about it.

---

## 3. (a) is absent, and this is the measurable finding

**Measured over `git log --since=2026-09-08`:**

| | count |
|---|---|
| Commits whose **diff lines** name a Tier A resource | **32** |
| …carrying any record of review **on the change itself** | **0** |

Reviews unquestionably happened — the index carries rows like *"INDEPENDENT
REVIEW of Fourth's item 65a and item 78"*. **The record simply lives somewhere
else, and nothing links the two directions:**

- From a commit you cannot ask *"was this reviewed, and how?"*
- From a review row you cannot ask *"which commits did that cover?"*

The rule in §2 is therefore **stated and unenforceable**. Not unenforced by
oversight — unenforceable, because the fact it depends on is not recorded
anywhere a tool or a reader could check it against a specific change.

**The measurement is deliberately narrow.** An earlier, looser version of it
asked "does this commit touch a FILE that mentions a Tier A resource" and
returned 107 commits — including a comment-only change to `api/sd-data.js`,
which names 43 Tier A resources and therefore makes every touch of that file
look like a Tier A change. That number is discarded, not reported. Only
changed diff lines count.

---

## 4. (c) was already answered, by item 101

Staged activation with a window to abort is the same question item 101 asked of
SAIRN's hard-commit points, and it answered it:
`docs/2026-09-14-graduated-mechanical-commitment.md`. Deploy commits already
have three phases — push gate, `deploy_verify_notify.py` re-measuring the live
site, production — and the gap there is that **abort is not cheap**, not that a
phase is missing. Repeating that analysis here would be a second copy of an
answer, so it is cited instead.

---

## 5. The minimal mechanism, and why it is NOT built here

Git already carries structured consent: this repo's commits use
`Co-Authored-By:` and `Claude-Session:` trailers. A `Reviewed-By:` trailer
naming the reviewer **and the kind** —

```
Reviewed-By: CC <tested>          # ran it, reproduced the finding
Reviewed-By: Hank <read>          # read the diff, did not run it
```

— would put consent on the artifact (property **a**), force the distinction to
be stated rather than inferred (property **b**), and be mechanically checkable
against the Tier A list with no new system.

**It is not built here, and the reason is a standing rule of this platform
rather than a lack of time.** A checker shipped today would report 32 of 32
Tier-A-touching commits as non-compliant, on a convention that did not exist
when those commits were written. `packages/testint/`'s own README states the
consequence: *"the moment a number exists somebody drives it to zero by the
cheapest available route, which for a checker is switching it off."* A gate that
is red on arrival gets disabled, and then the rule is worse off than when it was
merely unenforceable.

**What it needs first is Michael's call on the convention**, because a consent
vocabulary that the people doing the reviewing did not agree to is a vocabulary
nobody uses. Once `<tested>` / `<read>` is settled, the check is small and this
document is the specification for it.

---

## 5.1 OVERTAKEN THE SAME DAY — the gate exists, and it is better than the trailer

**Appended 2026-09-15, hours after §5 was written. §5 is left exactly as it
stood, because the reasoning is still the reasoning and editing it silently
would hide that this document was overtaken.**

Another session shipped **`tools/tier_a_review_gate.py`**, and it refused a push
of mine within the hour. It closes property **(a)** — consent attached to the
change — by a different and better route than the `Reviewed-By:` trailer §5
proposed:

| | §5's proposal | What shipped |
|---|---|---|
| Where consent lives | a git trailer on the commit | `docs/tier-a-reviews.json`, an OBLIGATION opened at push time |
| When it is required | at review time | **at push time, and it does not require the review to have happened** |
| Self-review | checkable | **refused mechanically — a record signed by its own author** |

**The design decision §5 got wrong** is the one that solves the objection §5
raised against itself. §5 declined to build a gate because *"a checker shipped
today reports 32 of 32 non-compliant against a convention that did not exist"*.
That gate sidesteps the problem entirely: it does not ask whether a change WAS
reviewed, it asks that the **obligation be RECORDED** so the next session can
see an unreviewed Tier A change instead of guessing. Nothing historical is
retroactively non-compliant, and nothing is red on arrival. That is a better
answer than waiting for a vocabulary decision, and it is worth saying plainly.

Its header also reports the same discarded measurement this document does, found
independently: a content-based rule *"reported 78 Tier A resources touched,
because api/sd-data.js contains every resource name on the platform"*. §3 threw
out its own 107 for the same reason. **Two sessions hit the same false positive
and both threw it out** — which is the independence property
`docs/2026-09-13-cross-domain-disciplines.md` asks for, arrived at by accident.

**Property (b) is still open.** The gate records THAT an obligation exists, not
what KIND of review discharges it — "I read it" and "I ran it" are still
indistinguishable in the record. That is the half §2 shows this platform already
does well in prose, and the half a vocabulary would make countable. It remains
Michael's call.

### 5.2 One false positive, reported rather than worked around

The gate tripped on **`SAIRN-ACTIVE-WORK-fourth.md`** — a worklog — because the
entry described `dnt_patients` and `dnt_rollup` by name. Its own exclusion list
already excludes `docs/` and `sql/` on exactly the right reasoning: *"a document
or a migration naming a resource is not code serving it"*. A root-level
`SAIRN-ACTIVE-WORK-*.md` is a document by the same argument and is not excluded,
because the list is keyed on `docs/` rather than on what the file is.

**Not fixed here**: the gate is another session's, the exclusion list is
deliberately kept tiny, and *"a growing exclusion list is how a gate stops
covering anything"* is its own stated reason. This is one row to add, not a
policy change — recorded for its author to judge rather than edited under a
different claim.

**The obligation it prompted was recorded anyway and is real**: the `dnt_rollup`
work is genuinely Tier A code written by one session, and it should have an
independent eye on it. A false positive that produced a true obligation is still
a false positive, and both halves are said here.

---

## 6. What this does NOT claim

- **It does not claim any Tier A change went unreviewed.** It claims the review
  is not discoverable from the change, which is a different and smaller
  statement, and the only one the evidence supports.
- **It does not propose more review.** §2 is evidence the review standard here is
  already high; the gap is recording, not rigour.
- **It does not re-open item 101's question.** Staged activation is that item's
  territory and was answered there.
- **`git log --since=2026-09-08` is one week**, chosen because it spans the
  current push of Tier A work. A longer window would give a different count and
  was not run.
