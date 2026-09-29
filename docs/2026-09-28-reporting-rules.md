# A stated start is not a start

**2026-09-28/29 (Hank).** Item 8 of queue22, added because I broke it the same
session it was given to me.

## The rule

**Never report a queued item as begun until it has a file or a test on disk.**
State intent as:

    queued: item N -- <subject>

Not *"starting item N"*, not *"beginning item N"*, not *"item N now"*. No verb
that implies motion, because a verb implying motion is read as a progress report
and that is what it is not.

## What happened

I closed a report with **"Starting item 2 (the amend guard) now."** The next
message was a status check. The honest answer was:

> nothing built, nothing tested — no `tools/rebase_state_guard.py`, no probe, a
> clean working tree at `11fbc8c1`.

The sentence had cost a round trip, and it had cost it in the one direction that
matters: it made the state sound further along than it was, to the person who
was about to leave for company visits and needed to know what was actually
finished.

## Why it is the same defect this repo already names everywhere else

**PR §5** — *"a status report is a claim, not a fact, until checked against real
current state."* That rule was written about reports on OTHER people's work and
about reports on finished work. It applies identically to a report on my own
work in the future tense, and the future tense is the version nobody thought to
check, because there is nothing yet to check it against.

It is also the **fabricated-KPI** shape from `sairn-guardian-v2` Check 0b, one
step earlier: a number with no function behind it, and a status with no file
behind it, are the same category of statement. Both read as evidence. Neither is.

And it is why **`tools/sairn_claim.py` commits the claim rather than trusting the
session to remember it** (PR §2.2): *a claim that is not committed is invisible
to every other clone.* An uncommitted claim and an announced start are the same
object — an intention that looks like a fact from outside.

## The three things this changes, concretely

1. **End-of-turn lists** name remaining work as `queued: item N`, with no verb.
2. **"Started", "begun", "in progress"** are only written once `ls` would show
   the file. The test is mechanical on purpose: not *"have I thought about it"*
   but *"is there a path I could print."*
3. **A status request about an item with nothing on disk** is answered in those
   words — *nothing built, nothing tested, clean tree at `<sha>`* — and not by
   describing the plan. Describing the plan in answer to "where are you" is how
   the first mistake gets made twice.

## What it does NOT change

It is not a rule against saying what comes next. The queue has to be visible or
nobody can reorder it, and Michael reorders it constantly. **The rule is about
the verb, not about the disclosure.** `queued: item 4 — discharge cc's
2026-09-26 obligation` says more than "starting item 4" and claims less.

## Why this is written down and not only remembered

The same correction has a memory entry under
`~/.claude/projects/.../memory/stated-start-is-not-a-start.md`, which loads every
session. That covers me. This file exists because the failure is not personal:
**every session on this platform writes end-of-turn summaries to the same one
reader**, and a summary is the only artifact of a session that is not checked by
anything. There is no hook that can see a narration verb, which
`CLAUDE.md`'s response-style section already says out loud about a different
narration rule:

> No hook can mechanically block narration text, so this is self-checked every
> turn.

An unenforceable rule is worth writing down precisely because nothing will remind
anybody of it. **That enumeration — every rule on this platform that no gate
covers — does not exist yet**, and it was item 8 of an earlier paste that has not
been done. This file is one entry it would contain; it is not the enumeration,
and saying so is cheaper than the next session discovering that a referenced
document is a plan.

**What a gate could catch here and what it could not, since the honest bound
matters:** nothing can read a narration verb in my output, so the rule itself is
unenforceable. What IS mechanically checkable is the other half — *does the file
the report names exist* — and that is a real check somebody could build against a
session's own end-of-turn summary if summaries were written to disk. They are
not. Recorded as the reason, not as a plan.
