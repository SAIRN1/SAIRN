# SAIRN Platform — Handoff, 2026-09-11 (push gate: the empty-range fail-open)

**Written for Cody**, who holds the claim
`push-gate-unresolvable-base-failopen -- outgoing_files and outgoing_subjects
return empty`. Michael's decision, same day: **Cody owns the full fix**;
Fourth stands down from that claim and hands over what it found.

Every claim below was **measured in this clone today**, not reasoned from the
code. The commands are included so you can re-run them rather than trust them.

---

## 1. The headline: the framing in the claim is right, and the trigger is wider than "unresolvable base"

I originally argued the opposite — that the tool was fine and only the probe
was wrong. **The probe half of that was correct and is fixed (`ee60b7e2`).
The tool half was not, and this document is the correction.**

`base` is only ever non-`None` in **prepush** mode.
`tools/sairn_push_gate_hook.py:582` sets `base = None`, and the only
assignment is inside `if MODE == 'prepush':` at :597. So **in PreToolUse mode
— the hook that runs on every `git push` typed in a session — `base` is
always `None`** and `outgoing_files()` goes straight to the fallback chain.

That matters because the fallback chain is thinner than it looks.

---

## 2. Three findings, each measured

### 2a. The two fallbacks are the SAME REF when pushing `main`

```python
refs = ([base] if base else []) + ['@{u}', 'origin/main']
```
— `tools/sairn_push_gate_hook.py:391`

Measured today:

```
$ git rev-parse --abbrev-ref @{u}
origin/main
$ git rev-parse --short origin/main
b0530e7a
```

On `main`, `@{u}` **is** `origin/main`. The "three-level fallback" the
docstring describes is, in the mode that actually runs, **one level tried
twice.**

### 2b. The documented `HEAD~1` last resort DOES NOT EXIST

The docstring at :350–354 says:

> *"Falls back through three references … `@{u}` is right when it exists,
> `origin/main` is right in this repo, and **`HEAD~1` is a last resort that at
> least sees the newest commit**."*

```
$ grep -n "HEAD~1" tools/sairn_push_gate_hook.py
352:    and HEAD~1 is a last resort that at least sees the newest commit. Returning
```

**One occurrence in the whole file, and it is that sentence.** There is no
`HEAD~1` in `refs`. The last resort that would have caught the case in 2c is
described and not implemented.

### 2c. THE REACHABLE FAIL-OPEN: a tip that is not ahead of `origin/main`

Both fallback ranges are empty whenever the pushed **tip** is an ancestor of
`origin/main`, so `outgoing_files()` returns `[]` — which the gate reads as
*"no seed touched"*. Measured in this clone, in the PreToolUse mode's exact
call shape, while it happened to be behind:

```
## main...origin/main [behind 5]
HEAD              : 3306abdc
origin/main       : b0530e7a
HEAD is ancestor of origin/main: True

outgoing_files(repo, None, "HEAD")    -> []
outgoing_subjects(repo, None, "HEAD") -> []
```

**`outgoing_subjects()` returns `[]` on the same input — I did not examine its
coverage at all beyond this measurement, and it feeds check 8's PROBE-commit
detection at :1288. Please treat it as unverified rather than as confirmed
broken or confirmed fine.**

#### Why this is not the benign edge case

The dismissal I first reached was *"in sync means nothing to push."* That is
true of `HEAD` → `main`, and it is **not** true of these, all of which send
real content while the tip sits at or behind `origin/main`:

- **`git push origin HEAD:some-branch`** while this clone is behind — the
  ordinary state, since four clones push all night. Real commits reach a real
  branch; both fallbacks are empty; the gate sees no seed files.
- **`git push origin <older-sha>:<branch>`** — the shape that started this.
- **any push whose tip is not on top of `origin/main`**, including a
  force-push after `origin/main` moved backwards.

I have **not** demonstrated an end-to-end denied-seed-change slipping through
on a live push — what is measured is the range function returning `[]` under
conditions a real push reaches. Please close that last step before or as part
of the fix, rather than taking my word for the consequence.

---

## 3. What Fourth already changed, and what it deliberately did NOT

**Changed — `ee60b7e2`, `tests/push_gate/refspec_and_override_probe.py`.**
The arm *"an UNRESOLVABLE base still widens"* asserted a fact about **this
clone's sync state**: the widening can only return something when the clone is
ahead of origin, so the arm passed or failed depending on who pushed last. It
now builds the precondition in a detached throwaway worktree. **My first
version of that fixture used `commit --allow-empty`, which produces no
filenames under `git log --name-only`, so it failed against correct code for a
second, different reason** — the fixture now commits a real file.

**Not changed — anything in `tools/sairn_push_gate_hook.py`.** That is yours.
The probe fix is orthogonal and should not need revisiting when you land the
real fix; if it does, that is a signal worth reporting rather than working
around.

---

## 4. The one thing to be careful about in the fix

**Failing closed here is not free.** `outgoing_files()` returning `[]` today
means "allow", and the gate is a **blocking** one — so a fail-closed change
makes every push with an empty computed range get denied. The cases in 2c
include ordinary, legitimate pushes to side branches. A fix that simply
inverts the default will deny work that should go through, and a denied push
that people learn to override with `SAIRN_SEED_GATE=off` is the same gate
hollowed out by a different route.

The `HEAD~1` fallback the docstring already promises (2b) looks like the
cheaper half: it makes the range non-empty for a real push without turning an
unknown into a refusal. Your call — you have the whole picture and I have one
corner of it.

---

## 5. Standard verification reminder

Re-verify every measurement above against the current tree before acting on
it: `base = None` at :582, the `refs` line at :391, the single `HEAD~1`
occurrence at :352, and the two `[]` returns. This document is a claim like
any other, and it already contains one correction of my own earlier claim.

---

# ⚠ RETRACTED — 2026-09-12 (Fourth)

**The severity claim in this document is WRONG. The fail-open does not exist.**

Cody implemented the fail-closed widening on Michael's decision, then
**reverted it in `014953aa`** after building the scenario in a real clone level
with its origin. I checked that reasoning against my own framing rather than
accepting it, and it holds:

**The range is empty only when the pushed tip is an ancestor of what origin
already has** — and such a push ships no new objects. To `main` it is a
non-fast-forward the remote rejects; to a NEW branch it creates a ref over
commits origin already holds, so no seed content is newly published.

**My own example was the counter-example.** Section 2c offers
`git push origin HEAD:some-branch` *"while this clone is behind"* as an
ordinary push that sends real content. It does not: while behind, those commits
are already on origin. I did not check that before writing it down.

**The widening had a real cost**, which is the part worth keeping: an accurate
`[]` became a 1,671-file scan of the whole history, handed to every
SQL-consuming check, which then judged files no push was sending — one
whack-a-mole per check, and no new branch ever pushable, which is how a gate
gets switched off.

**What kept this from being a confident wrong claim** is section 2c's own
paragraph saying the end-to-end case was *not* demonstrated and that
`outgoing_subjects()` was unverified. That caveat is the only reason this is a
retraction rather than a blocking gate rebuilt around a defect nobody had.

**The three facts under the claim still stand**, and one of them was a real
defect: `base` is only ever set in prepush mode; `@{u}` *is* `origin/main` when
pushing main, so the chain is one rung tried twice; and **the `HEAD~1` last
resort the docstring promised was never implemented**. That last one is fixed
2026-09-12 — docstring only, no behaviour change — along with a note in
`outgoing_files()` recording why an empty range is correct, so the next reader
who notices it does not re-report it a third time.
