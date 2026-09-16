# The shared status registry — and why it is a directory, not a file

**2026-09-16, Hank.** `tools/sairn_status.py`, `tests/run_sairn_status_probe.py`
(55 arms), wired into `SessionStart` beside the session lock and the claim hook.

---

## The gap, named by the tool it sits beside

`tools/session_lock_check.py` put this in its own header on 2026-08-24 and left
it there:

> Detects same-clone concurrent sessions ONLY. Does NOT detect two different
> clones independently converging on the same external task — **that is a
> harder, TASK-REGISTRY-SHAPED problem and out of scope.**

This is that task registry. The lock answers *"is somebody else already in THIS
directory"*; this answers *"what is every agent on this machine actually
doing"*.

`tools/dispatch_state.py` already joins the open-work index against the claims
and answers it well — but **both of its inputs are in git**, so its answer is
only as fresh as the last fetch, and an unpushed claim is invisible to every
other clone. The claim tool warns about exactly that. This is the live half: it
sits in `~/SAIRN-SESSION-LOCKS/status`, outside every clone, and a write is
visible to the next reader with no push, pull or fetch.

---

## ONE FILE PER AGENT, NOT ONE FILE WITH SECTIONS

The scope said *"one structured status file … each agent writes only its own
section … **no cross-agent write contention by construction**"*. The last four
words are the requirement, and **a single file cannot meet them.**

Updating one section of a shared file is a read-modify-write. Two agents whose
reads interleave both write a whole file built from a snapshot that no longer
contains the other's change, and the later writer silently erases the earlier
one. Nothing is corrupt. Nothing errors. One agent's status simply is not
there — the silent-loss shape this platform polices everywhere else. A lock
would narrow the window, not remove it, and would add a lock that can be held
by a dead process.

So the registry is a **directory**, one file per session, presented to every
reader as one registry. An agent's write touches a path no other agent ever
opens: there is no window to narrow, because the two writes cannot interact at
the filesystem level at all.

Same shape `.claude/claims/` and `~/SAIRN-SESSION-LOCKS/` already use, for the
same reason, and it is why neither has ever lost an entry.

### The claim is measured, not asserted

An arm that only drives the chosen design cannot test that claim — *"six
concurrent writers all survived"* passes on any design that happens not to race
during one run, and a concurrency bug that does not reproduce on the run you
watched is the whole reason this class of defect ships.

So **section 2 of the control implements the rejected design** — one shared
file, read-modify-write, one section each — and drives the same six writers at
it.

| design | writers | rounds each | sections lost or stale |
|---|---|---|---|
| **one file per agent** (shipped) | 6 | 10 | **0** |
| one shared file with sections (rejected) | 6 | 10 | **5 of 6** |

The shared writer sleeps 10 ms between its read and its write. That **widens a
real window; it does not invent one.** The window exists in any
read-modify-write against a shared file and its size depends on disk, load and
file size — which is precisely why *"it worked when I ran it"* is not evidence
about it.

---

## Two real defects the concurrency arms found, both Windows, both silent

Neither was visible by reading. Both would have shipped.

### 1. `os.replace` fails when another process has the destination open

Four processes writing the **same** section left **eleven orphaned `.tmp-`
files** and crashed the losing writers with a traceback. `os.replace` is atomic
everywhere, but on Windows it raises `PermissionError` if the destination is
open — including by a reader that opened it a microsecond earlier.

Fixed: retry with a short backoff, remove the temp file in a `finally` either
way, and on final failure **report that the status was not written** rather than
letting a traceback out. A write that failed must not leave litter that looks
like a write in flight for ever.

### 2. A transient access error is not a corrupt file — and would have cried wolf

A reader looping over the registry while four agents wrote hit
`PermissionError` on **5 of 2,867 reads**. The file is not damaged; it is
momentarily unopenable while a rename lands on it.

The first version treated any exception as `unreadable`. So a perfectly healthy
agent would have been reported **UNREADABLE**, and the whole run pushed to exit
2, at random, roughly twice per thousand reads. **A registry that cries wolf
twice a day is one nobody reads.**

Fixed: an *open* failure is retried; only a file that still will not open, or
one that opens and does not parse, is reported — and the two are reported with
different words, because *"I could not open it"* and *"its contents are wrong"*
are different facts about a different agent's health.

**Zero reads were ever torn or half-written.** That is what `os.replace` buys,
and it is the only thing it buys — the arms now say which of the two they are
measuring.

---

## Five sabotages, each run

| sabotage | arms that went red |
|---|---|
| one shared file for every agent (the rejected design) | 8 |
| write straight to the final path, no `os.replace` | 4 (incl. torn reads) |
| no read retry | 1 — the false UNREADABLE returns |
| silently drop an unreadable entry | 2 |
| an empty registry reads as a clean all-clear | 2 |

---

## A defect in the control itself, and it is the third this session

The first draft passed **lists** as the condition in nine arms —
`ok('…', bad_parse, [])` — reading as `(actual, expected)` because a sibling
suite's helper has that shape. An empty list is falsy, so arms that should have
passed reported FAIL; a **non-empty** list is truthy, so
`ok('…', torn[:3], [])` **passed precisely when the reader had observed torn
files.**

Four of the nine failed loudly, which is the only reason it surfaced at all.
That is the third time in one session on this platform that an arm has reported
a check it never performed. The helper now carries its signature and the reason
in a comment above it.

---

## Reading it is a hook, not a habit

Every agent is handed the registry at `SessionStart`, beside the lock and the
claim hook. A line in `CLAUDE.md` asking people to read it would be enforced by
remembering, and this platform's own tooling says that is enforced on the days
people remember — which are not the days it matters.

**The hook FAILS OPEN, and that is the opposite of the fail-closed rule this
repo applies to checks — deliberately.** The difference is the consequence, not
an inconsistency: a *check* that cannot run must not report a pass; an
*advisory* that cannot run must not stop the work. A status registry that can
prevent a session from starting is worse than no registry.

**Failing open is not failing silent.** An absent or empty registry still emits
the sentence saying the answer is UNKNOWN, because emitting nothing reads as
*"nobody is working"* — which is the one conclusion this whole file exists to
prevent. Four arms pin the hook exiting 0 across a populated, absent, empty and
corrupt registry, and two more pin that it still says something in each case.

---

## Writing your row

    python tools/sairn_status.py                       # read the registry
    python tools/sairn_status.py set --state working --task "..."
    python tools/sairn_status.py set --state blocked --task "..." \
                                     --blocked-on "Michael: run the migration"
    python tools/sairn_status.py set --state idle

`blocked` **requires** `--blocked-on`. A blocked row that does not say what it
is waiting on is a silence wearing a status, and the whole value of this
registry to Michael is knowing what is waiting on him.

## What it does not do

* It does not decide whether two agents' task strings describe the **same
  work**. It names overlap candidates by shared vocabulary and says on every
  run that this is not a verdict — that judgement scored 38% with five false
  positives out of five the last time this platform automated it.
* It cannot see an agent that never writes a status. The consequence *is*
  tested: an empty registry is reported as UNKNOWN, never as all-clear.
* It is **machine-local**. `~/SAIRN-SESSION-LOCKS` is not shared between
  machines — the same limit the lock files already have. This answers for one
  workstation.
