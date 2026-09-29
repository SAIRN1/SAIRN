# Where a GitHub push credential is read from — LOCATIONS ONLY

**Written 2026-09-28 for the SAIRN-Session55 rotation. Verified against disk
2026-09-29.** Item 2 of queue22.

**THIS FILE CONTAINS NO CREDENTIAL, NO VALUE AND NO FRAGMENT, AND THAT IS A
CONSTRAINT RATHER THAN A STYLE.** A credential has been pasted into a chat three
times on this platform during a rotation — `tools/gh_token.py` records it in its
own header and that is why `--report` prints the token's *length* and never a
prefix: **a prefix is enough to confirm a guess.** Every row below is a path, an
environment-variable *name*, or a credential store. Nothing here is a secret and
nothing here should become one.

**Scope.** Every place any agent, tool, hook, script or config reads a credential
that can push to `github.com/SAIRN1/SAIRN`. Read *sites*, not mentions —
documentation that discusses `GITHUB_TOKEN` is not a read site and is excluded.

---

## 1. The store that actually answers: the Windows Credential Manager

| | |
|---|---|
| **Location** | Windows Credential Manager, entry for `https://github.com` |
| **Read via** | `git credential fill`, with `protocol=https` / `host=github.com` |
| **Configured by** | `credential.helper=manager`, in **`C:\Program Files\Git\etc\gitconfig`** — the **system** gitconfig, not per-user and not per-clone |
| **Who shares it** | **ALL SEVEN working copies, and therefore every agent.** No clone sets a local `credential.helper`; all inherit the system one, so there is exactly **one** stored credential behind every push on this machine |

**This is the one that matters for the rotation.** Every `git push` from every
session resolves here. Rotating it rotates all seven at once, and nothing in any
clone needs editing.

**The seven working copies**, counted from disk rather than listed
(`python tools/nhi_register.py`):

| Directory | Role |
|---|---|
| `C:\Users\marsh\Documents\SAIRN` | **the seventh — see the correction below** |
| `C:\Users\marsh\Documents\SAIRN-cc` | build agent |
| `C:\Users\marsh\Documents\SAIRN-cody` | build agent |
| `C:\Users\marsh\Documents\SAIRN-fourth` | build agent |
| `C:\Users\marsh\Documents\SAIRN-hank` | build agent |
| `C:\Users\marsh\Documents\SAIRN-hover` | audit, not build |
| `C:\Users\marsh\Documents\SAIRN-hover2` | audit, not build |

Each has `remote.origin.url = https://github.com/SAIRN1/SAIRN.git`, verified
individually. **No remote URL on any clone embeds a credential** — checked on all
seven; every one is the bare HTTPS URL.

### The correction this enumeration produced, and it is the THIRD instance

`docs/NHI-REGISTER.md` said **six** working copies. There are **seven**.
`C:\Users\marsh\Documents\SAIRN` is a clone of the same remote, on `main`, able
to push, and it was invisible to the register because
`nhi_register.sibling_clones()` filtered siblings with
`name.startswith('SAIRN-')` and that directory has no hyphen.

The same undercount has now happened three times:

1. **2026-09-16** — `CLAUDE.md` said *"Four clones"* and named four while a fifth
   was pushing. Found by `tools/landing_verification.py`.
2. **2026-09-17** — the register's own row said *"FOUR working copies"* for the
   same reason. Fixed by **counting from disk instead of typing the list**, and
   the tool's header explains that at length.
3. **2026-09-29, here** — the count *was* derived from disk and was *still
   wrong*, because **the predicate was a naming convention rather than the
   question being asked.**

**That is the finding worth keeping, not the number.** Deriving a population does
not make it right if the filter encodes a habit. The question is *"is this
directory a git clone of the same origin"*, and nothing about a hyphen answers
it. Fixed in `tools/nhi_register.py` — the name filter is gone, every sibling
holding a `.git` is asked for its origin, and `.git` is tested with `exists()`
rather than `isdir()` because a worktree's `.git` is a file. Control:
`tests/run_nhi_clone_enumeration_probe.py`, which builds real repositories in a
throwaway parent — including one named `SAIRN` with no hyphen and one called
`checkout-of-sairn` that matches no convention at all.

---

## 2. `GITHUB_TOKEN` in the process environment

| | |
|---|---|
| **Location** | environment variable **`GITHUB_TOKEN`** |
| **Read by** | `tools/gh_token.py` → `_from_env()`, first in its lookup order |
| **Reaches** | `tools/gh_push.py` and `tools/gh_verify.py`, both of which import `github_token` from it |
| **Who shares it** | any session that exports it; **currently set in none** — verified unset in this shell |
| **Note** | this is the **override**, and the only source a CI runner would have. It takes precedence over the credential manager |

---

## 3. `.env.local`, two paths, both currently 0 bytes

| | |
|---|---|
| **Locations** | `C:\Users\marsh\Documents\SAIRN\.env.local`<br>`<this clone>\.env.local` — i.e. one per working copy, resolved relative to `tools/` |
| **Key read** | a line beginning `GITHUB_TOKEN=` |
| **Read by** | `tools/gh_token.py` → `_from_env_files()`, **last** in the order |
| **State on disk** | both exist and are **0 bytes**. Verified 2026-09-29 |
| **Who shares it** | per-clone for the second path; the first is shared by every tool in every clone, since it is an absolute path |

**Why last rather than deleted, and it is a seven-week silent failure.** The
absolute path above has been 0 bytes since **2026-08-08**. `gh_push.py` and
`gh_verify.py` each carried their own copy of a lookup that read only that file,
so both raised `GITHUB_TOKEN not found in .env.local` on **every invocation for
seven weeks** and nothing said so — neither tool is wired into a hook, gate or
suite, so the failure surfaced only when somebody reached for one. Found
2026-09-25. The order is now deliberate: a stale file must never shadow a live
credential, but a file somebody re-populates should still work.

**For the rotation: putting a new token in either file does nothing while the
credential manager holds a working one.** It is third in the order.

---

## 4. A SECOND, UNCENTRALISED COPY of the credential-manager lookup

| | |
|---|---|
| **Location** | `tools/plugin_upgrade_check.py`, its own `github_token()` at **line 182**, called at line 256 |
| **Reads** | `git credential fill` directly — the same store as §1 |
| **Does NOT use** | `tools/gh_token.py`, which exists to be *"the ONE place that knows where the GitHub token comes from"* |

**This is the defect `gh_token.py` was created to remove, still present in a
third file.** Its header names the shape: two tools, two copies of one decision,
and *"when the token moved, both copies went stale together and neither could be
fixed without finding the other."* A third copy is the same exposure again.

It does **not** block the rotation — it reads the same store, so it will pick up
the new credential. It is recorded here because a credential lookup that is
duplicated is one that can rot independently, and this one is now in a tool that
reaches the network.

**Not fixed in this pass, and the reason is stated rather than silent:**
`tools/plugin_upgrade_check.py` is outside the files named in my claim, and
routing it through `gh_token.py` changes its failure behaviour — `gh_token`
raises `TokenUnavailable` naming every source, while that function returns a
falsy value its caller already handles. That is a small change with a real
behavioural difference and it wants its own decision.

---

## 5. Not present on this machine — checked, so the absence is a finding

| Candidate | State |
|---|---|
| `gh` CLI config (`~/.config/gh/hosts.yml`, `%AppData%\GitHub CLI`) | **absent.** `gh` is not on PATH in this shell and no config directory exists. Nothing reads a token from it |
| `~/.git-credentials` (the `store` helper's plaintext file) | **absent.** The helper in use is `manager`, not `store` |
| `GH_TOKEN`, `GITHUB_PAT`, `GIT_ASKPASS`, `GH_CONFIG_DIR`, `SSH_AUTH_SOCK` | **all unset.** No tool here reads `GH_TOKEN` — only `GITHUB_TOKEN` |
| A credential embedded in any `remote.origin.url` | **none.** All seven checked |
| SSH keys / an `ssh://` or `git@` remote | **none.** Every clone pushes over HTTPS |

`tools/redaction_check.py` matches `github_pat` and `github_token` as *patterns
to refuse in written content*. It is a guard, not a read site, and is listed here
only so a later reader does not count it as one.

---

## What to do for SAIRN-Session55

1. **Rotate the token on GitHub**, then update the **Windows Credential Manager**
   entry for `https://github.com` — the single store at §1. `git credential fill`
   interactively is how it gets re-seeded.
2. **Nothing in any clone needs editing.** No `.env.local` holds a value, no
   remote URL embeds one, no clone overrides the helper.
3. **All seven working copies are affected simultaneously**, including both hover
   clones. Any session mid-push during the rotation will fail on the old
   credential; that failure is loud, not silent.
4. **Confirm with `python tools/gh_token.py`** from any clone. It prints **which
   source answered** and the token's **length** — never a prefix, never the
   value. That is the verification step and it is safe to paste into a chat.

## What this file cannot tell you

* **Whether the token has ever been rotated.** `docs/NHI-REGISTER.md` records the
  `github-pat` row as **attested only** — it appears nowhere in tracked files by
  design, so no check in any clone can derive it, and a blank `last rotated`
  there means **nobody knows**, not *never*.
* **What the credential's scopes actually are.** The register claims *"push to
  SAIRN1/SAIRN, and read of a PUBLIC repository"* on attestation. Nothing here
  verifies it against GitHub.
* **Whether anything outside this machine holds it** — a CI runner, a second
  machine, a phone. Everything above is disk on this box.
