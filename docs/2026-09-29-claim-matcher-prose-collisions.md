# The claim matcher blocks on prose, not on ownership — three instances, the test, and two items it is holding

**Filed by:** fourth, 2026-09-29.
**Subject:** `tools/sairn_claim.py`.
**Owner: UNASSIGNED.** Every commit in this repo carries the same git author
across all six clones, so authorship does not identify a session, and the
open-work index's existing claim-tooling row is marked `unassigned` too. This
needs assigning before it can be fixed; it is filed here so the assignment can
happen against a written reproduction rather than a memory of being annoyed.

**Not fixed here, deliberately.** The tool's own `overlaps()` docstring states
the rule this finding must obey:

> the honest fix is always a NARROWER new signal measured against the corpus,
> never a looser existing one.

Every remedy available to me is a loosening, and this is the one tool every
session's coordination rests on. A session that is being inconvenienced by a
gate is the worst-placed party to relax it.

---

## What happens

Three times in two days, work was blocked by a token that appears in another
session's claim **in a position that denies ownership rather than asserting it.**

| # | What I needed to do | Blocked by | The tool's own stated reason |
|---|---|---|---|
| 1 | Re-drive three points of Hank's Tier A review now that the family-contacts table exists | cc | `shared phrase: "against live"` |
| 2 | Read and fix the seventeen remaining real fail-open sites under `tools/` | cody | `same file or resource: known-bad` |
| 3 | The `alf_mar administered_by` identity fix | cody | `api/sd-data.js` |

**Neither blocking session is doing either piece of work.**

* **(1)** cc's phrase comes from *"drive the revoked-licence enforce-mode path in
  the AI proxy **LIVE against** a scratch env"*. Different app, different
  endpoint, different verb. The bigram `against live` is the entire overlap.
* **(2)** `known-bad` is platform methodology vocabulary. It appears in
  `docs/2026-09-13-cross-domain-disciplines.md`, in most commit messages on this
  branch, and in the instructions every session is given. It names no file and no
  resource, and the matcher reports it under `same file or resource`.
* **(3)** cody's only mention of the file is *"blocked items when
  `api/sd-data.js` frees"*. cody is **waiting for** it. cody publishes no
  named-files list. The matcher cannot tell waiting from holding.

## The distinguishing test

In all three the matched token sits in a **blocker clause** — a sentence whose
grammatical job is to say the writer is *not* doing that thing:

    waiting for X        blocked on X          when X frees
    X is hank's          NOT TOUCHING X        deferred, see refusals
    skip X               X is another session's

That position is local and syntactic, which is what makes it a candidate for a
*narrower* signal rather than a looser one: **a token that occurs ONLY inside a
blocker clause contributes no identifier and no bigram.** A claim that both holds
and waits on the same file must still block, because the token also occurs
outside one.

**It must be measured against the corpus in both directions before it goes near
the matcher.** The tool already carries a 110-pair corpus and the discipline of
reporting accuracy and stability as two numbers. This proposal is a hypothesis,
not a verdict.

## Why this is worse than an ordinary false positive

`docs/SAIRN-PROCESS-RULES.md` §4.3 **requires** a session to declare a conflict
in its claim rather than reword past the matcher. The matcher then converts that
declaration into a block on everybody else. cc hit the same wall from the other
side on 2026-09-28 and wrote it into its own claim: two of its queue items could
not be named in its claim string *"because naming either in this string blocks my
own claim on my own declaration."*

**So honest disclosure currently costs more than silence.** That is the one
property a coordination tool must never have, and it is the mechanism by which
this gets worse on its own: the cheapest response is to stop declaring.

## The thing I did NOT do

Re-checking items 1 and 2 with wording that omits the matched phrases answers
`CLEAR` both times. **I did not act on that.** Re-checked with the original
strings, both still return `BLOCKED` naming cc and cody. A `CLEAR` that a synonym
can buy is not evidence about who is working on what, and treating it as one is
exactly what §4.3 forbids.

---

## The two held items, in plain prose

Handed over as wording, not as a reworded claim. The matcher's owner can decide
whether these describe work that genuinely overlaps cc's or cody's, and if they
do not, whether the collision above is the reason.

### (a) Re-driving Hank's review of the family-contacts change

> A table that stores the contact details of residents' family members now
> exists in the database. It did not exist when Hank asked for this review, so
> three of the six questions Hank raised were answered on paper only and were
> marked as provisional for that reason. The work is to ask those three
> questions again of the running system rather than of the source, see what it
> actually answers, and then remove the word provisional from the review
> document — or leave it and say why. Nothing is edited except that one review
> document. The subject is a care home records feature. It has nothing to do with
> the billing assistant, the licence-checking path, or the scratch environment
> that cc's queue is about.

### (b) The seventeen remaining error-suppression sites

> Seventeen places in the maintenance scripts catch an error and carry on as
> though nothing happened. A scan found thirty such shapes; twelve were read and
> judged harmless, one is deliberate and correct, one was out of scope, and the
> seventeen that remain have never been read one by one. The work is to read each
> one, decide whether the silence is safe there, and where it is not, make the
> script stop and say it could not do its job instead of reporting success. Each
> change gets a test that fails if the silence comes back. This touches
> maintenance scripts only. It is not about the assertion-label work, the
> registry entry, the scrubber, or any of the resources on cody's list.

---

## Reproduction

    python tools/sairn_claim.py check sairncare "re-drive hank tier-a verdict points 1 2 4 live against alf_family_contacts and remove provisional marking in docs/2026-09-29-tier-a-review-verdicts-fourth.md"
    python tools/sairn_claim.py check tooling   "read each of the 17 remaining real bare-except-pass fail-open sites in tools/ individually and fix them to report COULD NOT RUN, known-bad control per fix"

Both return `BLOCKED` while cc's and cody's current claims are active. Neither
claim names the files either task edits.
