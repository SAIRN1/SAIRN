# The SQL commit+push guard denies plain commits it cannot possibly be protecting — and I had its cause wrong

**Written 2026-10-05 (Fourth). FINDING AND EXACT REPLACEMENT TEXT. Nothing
edited — `tools/sairn_push_gate_hook.py` is HANK'S ACTIVE CLAIM**, and hank is
working on that file's denial-collection path right now, which is adjacent
code.

---

## 1. A CORRECTION TO MY OWN REPORT FIRST

I reported this as *"the hook matched the words in my commit MESSAGE BODY"* —
a third instance of a classifier keying on narrative text. **That was wrong.**
I read the symptom and inferred the cause instead of reading the condition.

The condition is at `tools/sairn_push_gate_hook.py:1058`:

```python
if MODE == 'pretooluse' and re.search(r'\bgit\s+commit\b', cmd):
```

**It never looks at the message.** It fires on any `git commit` at all, and
then denies if *any* `sql/*.sql` is pending in the working tree or index. My
message body was irrelevant; what triggered it was two untracked SQL files
sitting in the tree.

The denial text is therefore inaccurate for the case it actually caught:

> *"Blocked: this command commits AND pushes SQL in one step"*

My command did not push and did not touch SQL.

## 2. The real defect: over-breadth, and a message that misdescribes it

The guard exists for a real incident — 2026-09-01, a migration reached
`origin/main` through a combined commit+push the gate could not see into. That
reasoning is sound and this does not propose removing it.

What it currently does, though, is deny **every commit in a tree that happens
to hold an uncommitted `sql/*.sql`**, whether or not that file could enter the
commit. For a session holding a SQL file it deliberately is *not* committing —
exactly the SAIRNvet credential situation — every unrelated commit is blocked
and must be worked around.

**The ambiguity the guard was built for does not exist when the pending SQL is
UNTRACKED and the command stages nothing broad.** An untracked file cannot
enter `git commit` with no `-a` and no pathspec. The hook does not need to
predict what will be staged in that case; git already guarantees it.

## 3. Proposed replacement, narrowing to what could actually be committed

Replace the condition at :1058 and the `pending_sql` computation beneath it:

```python
    if MODE == 'pretooluse' and re.search(r'\bgit\s+commit\b', cmd):
        # NARROWED 2026-10-05. The old rule denied ANY commit while ANY
        # sql/*.sql was pending, which blocks every unrelated commit made by a
        # session that is deliberately holding a SQL file back -- and the
        # denial text then describes a combined commit+push that did not
        # happen. The guard's real subject is SQL that COULD enter the commit
        # the hook cannot see into.
        #
        # Three states, and only the first is ambiguous:
        #   * STAGED sql/   -> it is going in. Deny, as before.
        #   * MODIFIED-but-unstaged sql/ with `commit -a` or a pathspec that
        #     could reach it -> it may go in. Deny.
        #   * UNTRACKED sql/ with no `-a` and no broad pathspec -> git
        #     guarantees it CANNOT go in. Allow; there is nothing to guess.
        status = [ln for ln in git(repo, 'status', '--porcelain').splitlines()
                  if ln.strip()]
        broad = bool(re.search(r'\bgit\s+commit\b[^\n]*\s-(?:a|am|-all)\b', cmd))

        def _could_be_committed(line):
            xy, path = line[:2], line[3:].strip().replace('\\', '/')
            if not (path.startswith('sql/') and path.endswith('.sql')):
                return False
            if xy[0] not in ' ?':          # staged in the index
                return True
            if xy == '??':                 # untracked
                return broad               # only `-a`-style can sweep it in
            return broad                   # modified, unstaged

        pending_sql = sorted(line[3:].strip().replace('\\', '/')
                             for line in status if _could_be_committed(line))
        if pending_sql:
```

**And the denial text should say which case it caught** — "staged" and "could
be swept in by `-a`" are different warnings, and neither is "commits AND
pushes in one step" unless the command also pushes.

## 4. What this does NOT weaken

The 2026-09-01 shape is still denied: that migration was **staged** when the
combined command ran, so it is the first branch above. Nothing about a real
commit+push of real SQL changes.

The one case this newly allows is an untracked SQL file during a commit that
cannot reach it. If that is judged too generous, the smaller version is to
keep the current rule and only **fix the message** to say what it actually
tested — but the over-breadth is the part that costs a session time.

## 5. Residual, stated

`-a` detection is itself a text match on the command, and a pathspec like
`git commit sql/` is not handled by the sketch above (it falls into `broad =
False` and would be allowed). **Either add a pathspec check or treat any
pathspec as broad** — the conservative choice, and the one I would take, is
to treat the presence of ANY pathspec as broad, since a commit naming paths
is rare enough that a false deny there costs little.

## 6. Status

**BLOCKED on hank.** The code above is complete enough to paste and adjust;
nothing further is needed from me.
