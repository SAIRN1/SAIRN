# The manifest against a fresh clone — and every fresh clone runs no hooks

**2026-09-29 (Hank).** Item 6 of queue23: verify `docs/hook-manifest.json`
against a fresh clone of `origin/main`, so the check is not only true of the
working tree that generated it.

## What was done

```
git clone --depth 1 --branch main https://github.com/SAIRN1/SAIRN.git <tmp>
python tools/hook_integrity_check.py --repo <tmp>
```

Clone at **`7441c19`**, which is the `origin/main` tip that carries the manifest.
`--repo` exists for exactly this: the manifest's whole value is that it is
*portable*, and a check only ever run where the manifest was written proves the
file agrees with itself.

## Result 1 — the content half is clone-independent. Confirmed.

| Covered | Count | Fresh clone |
|---|---|---|
| `.githooks/*` | 4 | **every hash matched** |
| `tools/*.py` invoked by a hook or by the wiring | 25 | **every hash matched** |
| `.claude/settings.json` wiring sets | 4 events | **every hash matched** |
| the checker itself | 1 | **matched** |

**Nothing about the hashes depends on this working copy.** That is the claim item 6
asked to test, and it holds — including through the line-ending normalisation,
which is what would have broken first: a fresh clone checks out with whatever
`core.autocrlf` says, and the normalisation makes that irrelevant. Had the check
hashed raw bytes, this run would have reported all 29 files as drifted and the
manifest would have been useless outside one directory.

## Result 2 — THE FINDING. A fresh clone of this repository runs no hooks at all.

```
core.hooksPath IS NOT SET AND THE MANIFEST EXPECTS '.githooks', so GIT IS
RUNNING NO HOOKS AT ALL IN THIS CLONE.
```

**`core.hooksPath` is local git config, not tracked content.** Cloning installs
all four hook files, byte-perfect, and arms **none** of them. Until somebody runs
`python tools/install_git_hooks.py`, the clone has:

- no pre-commit credential scan,
- no pre-commit conflict-marker check,
- no pre-push gate,
- no `prepare-commit-msg`, no `post-rewrite` sha reseat.

**This is the failure the tool's own header calls the one with the least evidence
on it**, and it turns out to exist *by default* rather than by accident: every
hook file is present and correct, every hash matches, and git reads none of them.
Nothing in any diff shows it, because nothing in the repository is wrong.

### It is not hypothetical, and it is not only about new agents

The realistic paths into this state are all ordinary:

* **A recovery clone.** If a clone is lost or corrupted, the replacement is
  unarmed at the moment somebody is in a hurry.
* **A CI or automation checkout.** Nothing here runs in CI today, and the day it
  does, the gates are off unless the pipeline runs the installer.
* **A seventh working copy.** One was found on this machine on 2026-09-29 —
  `Documents\SAIRN`, a clone of the same remote on `main`, able to push. Whether
  it has hooks armed is now a checkable question and was not before.

### Confirmed in both directions

Arming the fresh clone with one command and re-running:

```
git -C <tmp> config core.hooksPath .githooks
python tools/hook_integrity_check.py --repo <tmp>
  -> Every hook, every tool a hook invokes, the settings wiring and
     core.hooksPath match the manifest in the working tree AND at HEAD.   exit 0
```

**So the finding is exactly the arming, and nothing else.** That is the useful
shape: had the run reported a dozen mismatches, the signal would have been buried
and the real one — the only one that matters — would have looked like noise.

## What changed in the tool because of this run

The `core.hooksPath` finding now distinguishes **two causes with two different
sentences**, because a message naming the wrong one sends the reader to the wrong
fix:

| State | Meaning | Fix named in the message |
|---|---|---|
| **unset** | a fresh clone; files installed, nothing armed | `python tools/install_git_hooks.py` |
| **set, but elsewhere** | deliberately repointed | investigate — this one is an act |

The first version printed the repointed sentence for both, which would have sent
somebody looking for a malicious change when the answer was that nobody had run
the installer.

## What this run does NOT establish

* **That the hooks are correct.** It establishes they are unchanged. The check
  prints that limit on every run.
* **That the other six working copies are armed.** Each is local config and each
  would have to be checked where it lives. `--repo <path>` does that, and it has
  not been run against them: reading another clone's config is a read, but it is a
  read into somebody else's session's state, and the hover clone in particular is
  a boundary a build agent does not cross casually. **Flagged rather than done.**
* **That `install_git_hooks.py` itself is correct.** Its hash is in the manifest,
  so an edit to it is caught. Whether what it installs is right is a separate
  question and this check does not ask it.
