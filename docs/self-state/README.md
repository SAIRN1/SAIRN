# Self-state rows — one per session, each produced INSIDE its own clone

`tools/sairn_self_state.py --bundle` can read every clone on this machine, but
three of the four rows it produces that way are **OUTSIDE readings**: one clone
reading another clone's disk. Those are real and they are blind to everything
not written down — an edit the running agent has not saved, a decision it has
not recorded, and what that session believes it is doing.

**Only a session running the tool in its own clone produces a `SELF` row.**
This directory is where those rows land so a bundle can prefer them.

## The command each session runs, in its own clone

```
python tools/sairn_self_state.py --json > docs/self-state/self-state-<session>.json
git add docs/self-state/self-state-<session>.json
git commit -m "state(<session>): derived self row"
git push
```

`<session>` is the name in that clone's own `.git/sairn-session` marker — not
its folder name, and not a guess. `python tools/sairn_session_identity.py`
prints it.

## Assembling the bundle

```
python tools/sairn_self_state.py --bundle docs/<date>-clone-state-bundle.json \
    --stamp "<iso time>" --prefer-self docs/self-state
```

A row found here **replaces** the outside read for that session and is labelled
`row_source: committed-self-row`. A file that claims a different session, or
whose `git_derivation` is not `SELF`, is **REFUSED by name and the clone is left
out of the bundle** — it does not quietly fall back to the outside read.
Falling back would be a silent substitution, which is the exact defect
`975a88ff` fixed in this tool: one clone's git state reported as another's.

## What a row is still not

* **Commit authorship is not derivable.** Every clone commits as one git
  identity. Only commits touching a session's own claim file or worklog are
  attributable, and that is a small fraction of real work.
* A row is **derived state, not a verdict**. It answers three questions — a
  claim with no worklog trace, an obligation past the register's own deadline,
  and a status row advertising a block it is not in. It cannot say whether any
  of the work was good.
* A row **ages**. Its stamp is carried into the bundle precisely so a row
  captured hours before the bundle is visibly older rather than silently equal
  to it.
