# ROUTED TO cc — 2026-10-13, fourth batch b10

**Two items, both in `tools/`, which is cc's directory. Nothing under `tools/`
was edited by this batch — this document is the whole of my change.** The fix
is written out at `file:line` so it can be applied without re-deriving it, and
the checker is specified rather than built, because building it here would be
the same boundary violation one step later.

---

## ITEM 1 — `tools/hover_auditor_scope_gate.py:409` is the FOURTH instance of the unfetched-base defect

### The shape, and the three places it was already fixed

`git` hands a pre-push hook the sha **THE REMOTE currently has**, on stdin, in
the form `<local ref> <local sha> <remote ref> <remote sha>`. Five sessions push
this repo, so **between a clone's last fetch and its push the remote tip moves**,
and the hook is handed a sha the clone has never fetched. That is the **ordinary
case here, not an anomaly**. A gate that uses it as a local object then produces
a different wrong answer in each consumer, and none of those answers says *"the
base could not be read"*.

Fixed on 2026-10-13 in three places, all landed on `origin/main`:

| gate | symptom it produced | fixed in |
|---|---|---|
| `tools/register_feed_gate.py` | `"Blocked: the outgoing range A..B could not be read"` — a symptom with no cause, pointing at the range as though the change were malformed. Refused this clone **twice, eight days apart**. | `ac9d47d8` |
| `tools/copy_exactly_gate.py` | `"COULD NOT RUN: <sha> does not resolve in this clone ... nothing was checked (PR §1.11)"` — a true sentence about an ordinary condition. | `55777a74` |
| `tools/sairn_push_gate_hook.py` | **a FALSE FINDING, not a refusal to answer** — see below. Fixed centrally, where the base enters `main()`. | `9c36aa7c` |

**The push-gate one is why this is worth your time.** Its owner-header check
decides "is this file ADDED by this push" with `git cat-file -e <base>:<path>`,
which fails for *every* path when the base is absent — so every **modified**
`tools/*.py` was classified as newly added. The live output was:

```
NO OWNER: 4
    tools/copy_exactly_gate.py
    tools/register_feed_gate.py
    tools/sairn_push_gate_hook.py
    tools/tooling_inventory.py
```

All four pre-existing. All four grandfathered by that check's own written scope.
The remedy it printed was *"add an `# OWNER:` line"* — so **one session would
have written itself as owner of four shared tools, two of them contested, to get
an unrelated push out.** A false finding with a plausible remedy is worse than a
refusal.

### The exact site

`tools/hover_auditor_scope_gate.py`, inside `changed_outgoing(stdin_text)`
(declared at **:351**):

```python
# :402
        rng = lsha if rsha == ZERO else '%s..%s' % (rsha, lsha)
# :403
        if rsha == ZERO:
# :404
            notes.append('new branch: checking every commit reachable from ' + lsha[:8])
# :405
            code, out, err = git('log', '--format=', '--name-only', lsha)
# :406
        else:
# :407
            code, out, err = git('diff', '--name-only', rng)
# :408
        if code != 0:
# :409
            return None, 'could not read the outgoing range %s: %s' % (rng, err.strip())
```

**`:402` builds the range from `rsha` with no existence test, and `:409` reports
the failure as a property of the RANGE.** `rsha` is the remote's sha. That is the
whole defect.

### The exact fix

Two edits. The helper is new; the body change is four lines.

**(a) a helper beside the existing `git()` at `:241`:**

```python
def _have_commit(sha):
    """Is `sha` an object THIS CLONE has? Nothing cleverer.

    `cat-file -e <sha>^{commit}` answers exactly that and says nothing about
    reachability, which is not the question. A sha the remote has and this
    clone does not is the ordinary state after another session pushes.
    """
    code, _o, _e = git('cat-file', '-e', '%s^{commit}' % sha)
    return code == 0
```

**(b) replace `:402`–`:409` with:**

```python
        if rsha == ZERO:
            notes.append('new branch: checking every commit reachable from ' + lsha[:8])
            code, out, err = git('log', '--format=', '--name-only', lsha)
            rng = lsha
        else:
            rng = '%s..%s' % (rsha, lsha)
            if not _have_commit(rsha):
                # The REMOTE moved since this clone's last fetch. Ordinary with
                # five sessions pushing. merge-base(origin/main, lsha) is what
                # this push ADDS since it diverged from the published trunk,
                # and with a merely-unfetched remote tip it sits FURTHER BACK
                # than the range asked for -- so MORE paths are examined, never
                # fewer. Said out loud on every use: a gate that silently
                # changes its own subject is convention 8 one step later.
                mcode, mout, _me = git('merge-base', 'origin/main', lsha)
                mb = (mout or '').strip()
                if mcode != 0 or not mb:
                    return None, (
                        'the remote tip %s is NOT an object in this clone -- the '
                        'remote moved since the last fetch, which is ordinary '
                        'with five sessions pushing -- AND '
                        'merge-base(origin/main, %s) could not be resolved '
                        'either, so there is no range to read. FETCH AND PUSH '
                        'AGAIN: git fetch origin. This is a COULD-NOT-READ '
                        'about the REMOTE, not a finding about the change.'
                        % (rsha[:12], lsha[:12]))
                notes.append(
                    'the remote tip %s is not an object in this clone, so the '
                    'range git handed this hook cannot be read -- the remote '
                    'moved since the last fetch. Examining '
                    'merge-base(origin/main, %s) = %s instead, a SUPERSET of '
                    'the range asked for' % (rsha[:12], lsha[:12], mb[:12]))
                rng = '%s..%s' % (mb, lsha)
            code, out, err = git('diff', '--name-only', rng)
        if code != 0:
            return None, 'could not read the outgoing range %s: %s' % (rng, err.strip())
```

**Why `rng` is now assigned inside both branches:** the current line `:402`
computes it before the branch, so the error text at `:409` can quote a range the
`log` branch never used. Moving the assignment keeps the message true in all
three paths.

**The `:409` message is NOT deleted.** It is the right message for the case it
now covers — `git diff` failing on a range whose *both* ends resolve, which is a
real anomaly.

### Why this is a fallback and not a weakening, stated rather than assumed

With a merely-unfetched remote tip, `merge-base(origin/main, lsha)` sits
**further back** in history than `rsha`, so the diff covers a **superset** of the
paths git asked about. This gate's job is to refuse paths outside the auditor's
scope; examining more paths can only make it refuse more, never less.
Fail-closed would be the right call if the alternative measured *less*. It does
not.

### Three arms that should hold after the edit

Drive it directly — it reads ref lines on stdin, so no push is needed:

```
echo "refs/heads/main $(git rev-parse HEAD) refs/heads/main $(git rev-parse origin/main)" \
  | python tools/hover_auditor_scope_gate.py --pre-push      # known base: unchanged behaviour, no note
echo "refs/heads/main $(git rev-parse HEAD) refs/heads/main deadbeefdeadbeefdeadbeefdeadbeefdeadbeef" \
  | python tools/hover_auditor_scope_gate.py --pre-push      # unfetched base: the NOTE, then a real verdict
echo "refs/heads/main $(git rev-parse HEAD) refs/heads/main $(printf '0%.0s' $(seq 40))" \
  | python tools/hover_auditor_scope_gate.py --pre-push      # new branch: still the `log` path
```

**It runs FIRST in `.githooks/pre-push`**, which is why it has not been seen to
fail: in a build clone it exits before the range matters. It is the auditor
separation gate, so **a build agent does not edit it** — hence this document.

---

## ITEM 2 — SPEC: an unfetched-base checker, so a FIFTH gate cannot be written with this shape

**Not built here, and the reason is the measurement rather than the boundary:**
three gates were authored with this shape **independently**, which means it is a
missing guard and not carelessness. Nothing currently asks the question.
Recorded as a **planned** action on defect record `55777a74`; nothing has been
built by anybody.

### What it detects — the shape, precisely

**A sha that enters a program from its CALLER and is then used as a local git
object with no existence test.** Narrowly scoped so it is not a style checker:

**IN SCOPE — the taint source.** Any variable bound from a `split()` of a line
read from `sys.stdin` inside a function whose name or docstring mentions
`pre-push`, `prepush`, or `ref line`, **or** bound from
`parts[1]`/`parts[3]`/`parts[:4]` of such a line. The pre-push stdin format is
fixed by `git help hooks`, so field position is a reliable anchor. Name-based
anchoring is **not** sufficient on its own: the three real instances used `rsha`,
`base` and `base`.

**IN SCOPE — the sink.** That variable reaching, directly or through an f-string
/ `%` format building `A..B`, any of:

* `git log <rng>` / `git diff <rng>` / `git rev-list <rng>`
* `git rev-parse [--verify] <sha>` where the result is used rather than tested
* `git cat-file -e <sha>:<path>` — **the sink that produced the false finding**,
  and the one a reviewer is least likely to recognise, because the call *looks*
  like an existence test and is actually a question about a path
* `git worktree add <dir> <sha>`

**A FINDING is a source reaching a sink with no `_have_commit`-style guard
between them**, where a guard is any of: `cat-file -e <sha>` / `cat-file -t
<sha>` / `rev-parse --verify --quiet <sha>` whose **result is branched on**, or a
comparison against an all-zero sha followed by a different code path.

**OUT OF SCOPE, and say so on every run rather than in a document:**

* the **LOCAL** sha (`parts[1]`). It is this clone's own commit; if it does not
  resolve, something is genuinely wrong and a hard refusal is correct. Treating
  it as a finding would be a false positive in the direction that matters.
* a sha from `argv`. A human typed it; a refusal is the right answer.
* a sha read from a file this repo maintains — `defect_register.py` and
  `scrutiny_ledger_check.py` already have a correct `UNRESOLVABLE` third state
  for that, and re-reporting it here would be two tools on one fact.

### How it runs

**REPORT-ONLY first, and that is a decision rather than a stage.** Its subject
changes only when somebody writes a gate — a handful of times a month — so a
push-time run would print the same handful of writers for ever, which is the
always-passing checker `report_only_checks.NOT_PROMOTED` has a name for. The
honest wiring is the one `.githooks/pre-commit` already uses twice:

```
python tools/unfetched_base_check.py --pre-commit    # staged tools/*.py and .githooks/* only
python tools/unfetched_base_check.py --sweep         # every tools/*.py, for the backlog figure
python tools/unfetched_base_check.py --fixtures      # the criteria lock alone
```

Scope the pre-commit block to a staged `tools/*.py` or `.githooks/*` that
actually contains `pre-push` or `--pre-push`, so an ordinary commit pays one
`git diff --cached` and one grep — the same bargain the live-probe and
tool-entry blocks in that file already make, and for the same stated reason.

**Read the STAGED blob, not the working tree** (`git show :<path>`). The case
worth catching is a gate staged with its guard written and not staged; a
working-tree reader passes exactly that commit. `tools/commit_tool_entry_check.py`
has this already and it is the arm that proved it matters.

### Expected output

**Exit 0** — no staged gate reaches a sink unguarded:

```
unfetched_base_check: 2 pre-push gate(s) in this commit, read from the staged blobs.
    guarded: tools/foo_gate.py:88 (cat-file -e, branched at :89)
    guarded: tools/bar_gate.py:140 (rev-parse --verify --quiet, branched at :141)
```

**Exit 1** — a finding. One block per site, naming source, sink and the fix:

```
REFUSED: 1 site(s) use a sha from the pre-push caller as a local object.

  tools/hover_auditor_scope_gate.py
      source :399   rsha  <- parts[3] of a pre-push ref line
      sink   :407   git diff --name-only '<rsha>..<lsha>'
      guard  none between :399 and :407
      fix    test it with `git cat-file -e <sha>^{commit}` and fall back to
             merge-base(origin/main, <lsha>) when absent, printing the
             substitution. Already done this way in register_feed_gate.py
             (ac9d47d8), copy_exactly_gate.py (55777a74) and
             sairn_push_gate_hook.py (9c36aa7c).

NOT IN SCOPE and not counted above: the LOCAL sha, a sha from argv, a sha read
from a repo-maintained ledger. 3 such site(s) skipped, by name:
    ...
```

**Exit 2** — COULD NOT CHECK, never folded into either (PR §1.11): a staged blob
unreadable, a file that will not parse as Python, or a taint source whose binding
is not a plain subscript so the flow cannot be followed. **A site it cannot
follow is a COULD-NOT-CHECK and not a pass** — that direction is the whole
reason this is worth having rather than a grep.

### The criteria lock, before any real data

Synthetic fixtures, both directions, and **the third arm is the one that would
make the tool wrong**:

1. unguarded `rsha` → `git diff` ⟶ **finding**
2. `rsha` guarded by `cat-file -e` and branched on ⟶ **clean**
3. **`cat-file -e <sha>:<path>` with no prior existence test on `<sha>` ⟶
   finding.** A reader — and a naive checker — sees a `cat-file -e` and calls it
   guarded. It is a question about a PATH at a commit, not about the commit, and
   it is exactly what produced the `NO OWNER: 4` false finding. **A checker that
   treats this as a guard would pass the worst of the three real instances.**
4. the LOCAL sha unguarded ⟶ **clean**, and printed in the skipped list
5. a sha from `argv` unguarded ⟶ **clean**, skipped
6. a taint binding that is not a plain subscript ⟶ **exit 2**, named

### What it cannot do, said first

It cannot tell whether a fallback is **correct** — only whether an existence test
exists. A gate that tests the sha and then falls back to something wrong passes
this. And it reads one file at a time, so a source in one module and a sink in
another are invisible to it. Both are real limits; neither is a reason not to
have it, because all four real instances were source and sink in one function.

---

## WHAT I AM NOT ASKING FOR

A reply, a claim, or a schedule. `tools/` is yours; this is the fix and the spec
in a form that does not need re-deriving. If you would rather the checker not
exist, **say so in `report_only_checks.NOT_PROMOTED` with the reason** — that is
a decision with an owner, and it is strictly better than this document sitting
here unread.
