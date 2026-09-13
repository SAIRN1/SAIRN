# Coordination health check — first pass, and it is a real case study

**2026-09-13 (Hank).** First run of the coordination-health-check practice. The
subject is the coordination layer itself: the chat relay between Michael and the
four clone sessions. Every other audit in this repo points at code or documents;
nothing had ever pointed here.

Skill used: **`sairn-memory-curator`** — §1 (where a fact belongs), §6 (when a
thing is explained twice it needs a mechanism, not a louder sentence).

**Scope, stated plainly: one night, four incidents, all from a single
conversation thread.** That is a small sample and the conclusions are shaped
accordingly — three of the four are the same root cause, which is either a
strong signal or an artefact of one session's bad luck. The fourth is a
one-off. **This is a first case study, not a base rate.** The honest next step
is to run this again after a few more nights and see whether the same class
dominates.

**Nothing here is a criticism of the dispatcher.** Every incident below is a
*channel* failure or a *timing* failure. None required anybody to have been
careless, and three of the four were invisible from the sending end.

---

## The four incidents

### A1 — the schema snapshot never arrived, twice

**What happened.** `db/schema_snapshot.json` needed replacing with a fresh
capture. The relay was attempted through chat and failed twice:

1. *"Fresh schema_snapshot.json received directly from Michael... Save this
   verbatim over db/schema_snapshot.json"* — **no file was attached.**
2. *"Save this exact JSON as db/schema_snapshot.json, then commit and push:"* —
   **the message ended at the colon.**

**What stopped it.** Nothing structural. In both cases the receiving session
happened to check, said so, and refused to reconstruct a file it had not
received. Had it instead written *something* — a best-effort reconstruction, or
a partial paste — the result would have been a valid-looking capture with
tables missing.

**Why that is worse than it sounds, and it is the whole reason this is #1.**
`tools/schema_snapshot_freshness.py` reads a missing table as *"this migration
was never run"*, and on 2026-09-12 it produced exactly that verdict for **89
tables**. A truncated capture would have manufactured that finding out of
nothing, and it would have looked identical to a real one. **A short capture
that still parses is the dangerous shape; an empty one is the safe shape,
because it fails loudly.**

**Root cause.** A ~360KB artefact was being moved through a channel with no
integrity check, no size guarantee, and no acknowledgement. The relay had
exactly one safeguard — a human noticing — and it was applied on the wrong end.

**The structural fix, built: `tools/load_schema_snapshot.py`.**

    python tools/load_schema_snapshot.py <path>            # check only
    python tools/load_schema_snapshot.py <path> --write

It refuses an empty payload, malformed JSON, a capture that is **not newer**
than the committed one, a capture with **no `_generated_at`**, and — the one
that matters — **a capture that has LOST tables**, naming every one. The rule is
asymmetric on purpose: tables appearing is ordinary; tables disappearing is the
signature of a bad transfer. Overriding it requires `--allow-shrink "<reason>"`
and the reason is echoed into the output so it reaches the commit message.

It **does not commit**, deliberately. Writing and publishing are separate acts,
and a tool doing both would make `--write` something you run to see what it
says.

Held by `tests/run_snapshot_loader_probe.py` — 20 arms, every refusal planted on
a fixture, **and a control demanding a genuinely good capture PASS**, because a
gate that refuses everything satisfies every other arm.

**And the process half, which the tool cannot do:** *don't move file bodies
through chat.* Save the capture to disk and send the **path**. The tool then
turns "did the transfer survive" from a judgement call into an exit code.

### A2 — a dispatch arrived in the wrong session's window

**What happened.** A message opening *"For Ted:"* — instructing Ted to install
the snapshot and notify Hank — was delivered to **Hank's** window. Hank held no
claim on that work, and Ted had already claimed it minutes earlier.

**What stopped it.** The receiving session read the addressee, checked the claim
record, found `fourth: checker-control-registry` already active, and declined.

**Root cause.** Messages are **addressed by a name in the body** and **delivered
by window focus**, and nothing binds the two. Any mis-click routes work to a
session that has no way to know it was not meant for it — except by reading the
salutation, which is a convention, not a mechanism.

**The structural fix — two halves, and the second is the real one.**

1. *Cheap and immediate:* a session that receives a message opening `For
   <name>:` where `<name>` is not its own clone must **stop and say so** before
   doing anything. Worth a line in `CLAUDE.md`; it costs one comparison.
2. *The real fix:* **dispatch by claim, not by person.** "Run the snapshot load
   — claim `snapshot-load` first" is verifiable by the receiving session against
   `sairn_claim.py check`, and it fails closed when another session already
   holds it. A name in a salutation is unverifiable; a claim is not. This also
   subsumes the 2026-09-01 lesson already in `CLAUDE.md` — *"run `list` and name
   the FILE before sending a session at it"* — which was about the dispatcher's
   preparation. This is the same rule made checkable by the receiver.

### A3 — a message was sent before the session had finished reporting

**What happened.** A message ended mid-sentence — *"On schema_snapshot_freshness
— this is likely"* — and was then re-sent complete a turn later. The truncated
version arrived while the session was still working.

**What stopped it.** The session declined to guess the ending, said the message
had cut off, and stated what it could establish independently so the answer was
useful either way.

**Root cause.** The dispatcher cannot see whether a session is mid-turn, so a
send can land against a state that is about to change. Combined with A1, the
pattern is the same one twice: **an instruction that ends mid-sentence, or with
an empty payload, is not an instruction.**

**The structural fix.** This one is *mostly* not fixable from the repo, and it
is worth saying so rather than inventing a mechanism that would not work. What
the receiving session can do, and must:

- **Never act on a truncated instruction.** Say where it cut off and ask. Two of
  tonight's four incidents were this, in different disguises.
- **When a message is re-sent, treat the later one as authoritative and say
  which one is being acted on** — otherwise a partial and a complete instruction
  both look like live instructions.
- **Do everything that does not depend on the missing part first**, so the reply
  carries real information rather than only a question. That is what happened
  here and it is why the round trip cost nothing.

### A4 — a relay asked for work already assigned elsewhere

**What happened.** After A2 was corrected, a later message again asked this
session to install the snapshot — still Ted's assigned work, and still with no
payload attached.

**Root cause.** Not a new class. It is A1 and A2 co-occurring: the assignment
had moved but the relay had not, and the payload was missing again. Recorded
separately only because **it shows the first correction did not stick**, which
is the argument for a mechanism rather than a reminder.

---

## What this says, honestly

**Three of four incidents share one root cause: a channel with no integrity
check carrying something that needed one.** Not carelessness — a missing
acknowledgement path. The fix for the expensive instance is built; the cheaper
instances are a convention plus a `CLAUDE.md` line.

**The one genuinely encouraging finding: the receiving end caught all four.**
Every incident was detected before anything was written, by a session checking
rather than assuming. That is the verification discipline in `CLAUDE.md` working
in a place it was never written for. **It is also exactly what should not be
relied on** — it worked four times out of four tonight and it is one distracted
turn from working three out of four, which is the one that ships a fabricated
capture.

**What I could not determine.** Whether any *earlier* relay failed and was NOT
caught. Nothing records a failed transfer, so the sample is only the ones
somebody noticed. If a truncated capture has ever been committed, the evidence
would look like a snapshot that lost tables between two consecutive commits —
checkable in principle by walking the history of `db/schema_snapshot.json`, and
**not done here**, so it is listed as open rather than reported as clean.

## Recommended, in priority order

1. **Stop relaying file bodies through chat.** Save to disk, send the path, load
   through `tools/load_schema_snapshot.py`. *(Tool built; the habit is the
   remaining half.)*
2. **Dispatch by claim, not by name.** Name the claim string in the dispatch so
   the receiving session can verify it mechanically.
3. **Add to `CLAUDE.md`:** a message addressed to another clone, or one that
   ends mid-sentence or with an empty payload, is refused and reported — never
   guessed at.
4. **Re-run this health check in a week.** One night is not a base rate, and the
   dominant class here may not be the dominant class overall.
