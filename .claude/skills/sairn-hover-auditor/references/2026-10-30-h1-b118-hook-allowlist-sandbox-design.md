# H1 b118: closing the seven open deny-hook classes by architecture, not by patch

**Status: DESIGN ONLY. No code written, no hook changed.** Written before touching code, per Michael's b118 item 3.
Classes are numbered as in H2's cold read of `hover_builder_path_deny.py` (b117 handoff, item 7): 2 parent-directory self-protection, 4 UNC admin-share and NTFS stream spellings, 5 shell forms whose program word is not recognised, 6 interpreter calls missing from the write pattern, 7 PowerShell and cmd forms, 8 git option abbreviations, 9 git read subcommands that write. (1 crash-open and 3 shadow-import are fixed in the tracked copy.)

## 1. Why a seventh patch is the wrong move

The hook is a DENY-list over command TEXT: it enumerates the ways a string can write, and anything it did not enumerate passes. Every one of the seven is an instance of one fact: **the set of spellings is open, the set of things we protect is closed.** The file is 1,135 lines, its own docstring says "it is not a sandbox", and each class found by a second reader (H2) was a spelling the first reader (me) did not think of. A deny-list's miss rate cannot be driven to zero by more reading; it can only be moved by changing what the default is.

Measured, so the design is sized to real use and not to a guess (50 hover transcripts, `scratchpad/progwords.py`, 2026-10-31): **18,995 shell calls.** Most-run program words: python 9,029, git 7,969, grep 7,275, head 6,590, tail 5,943, echo 3,357, cut 3,105, sed 2,352, ls 894, cat 779, wc 677, node 591, find 341, cp 312, sort 220, awk 185. Git subcommands: log 1,780, show 991, status 988, fetch 867, pull 622, stash 426, rev-parse 325, diff 278, add 263, push 241. **2,124 calls (11.2%) contain `$(`, a backtick, a heredoc, `xargs` or `eval`.** (The program-word tail is polluted by heredoc bodies counted as commands; the head of the table is reliable, the 5,807 "distinct words" is not a vocabulary.) Two consequences: the genuine vocabulary is small enough to enumerate, and **python is half of all traffic and is Turing-complete**, so no text rule over `python -c` or a heredoc can be complete. That second point is what decides the architecture.

## 2. Architecture: three layers, and which class each one closes

**Layer A. Enforcement below the text (closes 2, 4, and the residue of 6, 7, 9 by construction).**
The filesystem decides, not the parser. Run the hover session so that every builder-owned tree (sibling clones, SAIRN-SESSION-LOCKS, this clone's non-manifest paths, the hook, both settings files) is **read-only to the process**, whatever spelling reaches it. Candidates, in order of how much each really holds:

| Option | Holds against | Does NOT hold against | Needs |
|---|---|---|---|
| A1. Separate low-privilege Windows account for the hover session; builder trees ACL read-only for it | every write spelling incl. UNC, streams, `\\?\`, junction, 8.3 names, any interpreter | execution of builder code as a read (a read-only file can still be run; see Layer B) | Michael / an elevated prompt; account creation is user-only; Claude Code credentials and `~/.claude` move to that account |
| A2. WSL2 or a container with builder clones bind-mounted `ro` | same, and path-spelling classes vanish (no drive letters, no UNC) | git for Windows tooling parity; the 14 push-gate hooks run Windows-side | WSL install, one-time mount recipe, Michael |
| A3. Same-user ACL `deny write` on builder trees | accidental writes | **nothing deliberate**: the owner can `icacls` it back, so it is a speed bump, not a boundary | none, so it is the only one I could do alone, and I would not call it enforcement |

Recommendation: **A1** (smallest change to tooling, kernel-enforced). State the limit now: until A1 or A2 exists, classes 2 and 4 are only narrowed (Layer B), not closed.

**Layer B. Default-deny allow-list in the hook (closes 5, 7, 8, 9 and narrows 6).**
Invert the default. The hook parses with a deliberately tiny grammar and **refuses anything it cannot fully parse**:
1. Grammar: simple commands joined by `&&`, `||`, `;`, `|`; plain quoting only. Anything else (`$(`, backticks, process substitution, `eval`, `xargs`, `-exec`, here-strings, `^` caret forms, `%VAR%`, `$env:`) = REFUSED, with the construct named. 11.2% of calls use some of these; the cost is real and is paid by writing the call differently (a scratch file, a loop in a script).
2. Program word must be in `ALLOW_PROGRAMS` by **real resolved path or exact builtin name**, else REFUSED (class 5: an unrecognised word is no longer a pass). Initial set from the measured head: git, grep, head, tail, cut, sed (`-n` only, never `-i`/`--in-place`/`w`/`e` commands), ls, cat, wc, find (no `-exec/-delete/-fprint*/-ok`), sort, awk (no `system`, no `>`; or drop awk), cmp, diff, date, echo, cp/mkdir (write targets must be inside the hover write zone, computed from the resolved path, see 4), python and node (rule 6).
3. PowerShell and cmd (class 7): **not allow-listed at all** except by exact named invocation. There are no recorded hover calls that need them beyond what bash covers, and a second shell grammar doubles the attack surface for no measured use.
4. git (classes 8, 9): per-subcommand allow-list of **full-length option names only**; any `--x` that is a unique prefix of a long option, or a `-` cluster not in the table, is REFUSED (no abbreviation parsing). Read subcommands get an explicit option deny that includes the ones that write or run code: `--output`, `-O`/`--open-files-in-pager`, `--ext-diff`, `--textconv` on `diff/log/show`, `--exec`, `-c core.*`/`-c alias.*`/`-c diff.*.command`, `GIT_*` env prefixes, `--git-dir/--work-tree`, and `-C <path>` only when the path resolves into this clone. Write subcommands (add, commit, push, pull, stash, fetch, rebase, merge) are allowed only for this clone and only with the option table; checkout/restore/reset/clean/rm/mv are refused as today.
5. Interpreters (class 6): **run only a pinned script file, never inline code.** `python -c`, `python -` and heredocs are REFUSED. `python <path>` is allowed when the real path is under this clone's tools dir, the scratchpad, or the hover skill, **and** (for tracked tools) the file's sha256 matches the committed manifest. Scratch scripts in the scratchpad are allowed to run **only inside Layer A**; without Layer A, a scratch script that opens a path built at run time is exactly the hole the current docstring admits, so the design does not pretend otherwise. Cost: 9,029 python calls are mostly heredoc/`-c`; they become "write the script to the scratchpad, run it". That is the one real workflow change.
6. Paths (classes 2, 4): resolve every path argument to a canonical form with the OS (`GetFinalPathNameByHandle` on an existing path, `os.path.realpath` on its nearest existing ancestor otherwise). **Charset gate before resolution:** a path containing a `:` anywhere past the drive letter (NTFS stream), a leading `\\` or `//` or `\\?\` or `\\.\` (UNC, admin share, device namespace), an 8.3 `~N` segment, or a trailing dot or space is REFUSED outright, because canonicalisation of those forms is where the bypasses live. Self-protection (class 2) becomes a **containment** test: a write is allowed only if its resolved path is under an explicit WRITE ZONE (this clone's manifest-allowed paths, the scratchpad, the Drive upload staging dir); **everything else is refused, including any operation whose target is an ancestor of a protected path** (`rm -r ~/.claude`, `mv ~/.claude/projects x`), because ancestors are not in any write zone. Allow-by-zone replaces the exact-path protected set.

**Layer C. Detective, independent of the hook (catches whatever A and B miss, and is the only layer that does not trust the parser).**
At session start and close, record a tree hash of every builder-owned tree and the two settings files and the hook, and compare: any change not made by a commit in that clone's own history is a finding. `hover_separation_audit.py` is the existing nearest tool (builder-owned, read as data); a hover-owned copy of the comparison is in scope. This turns "a spelling slipped through" from invisible into a logged breach within one batch, which is the property the current design lacks (a bypass leaves no trace unless the hook happened to log it).

## 3. Class-by-class: what closes it, and what is left

| Class | Closed by | Remaining after the design |
|---|---|---|
| 2 parent-dir self-protection | B6 write-zone containment; A | none for writes through the hook; none at all under A |
| 4 UNC / NTFS streams | B6 charset gate; A (kernel path resolution) | a spelling the gate's charset rule did not list, until A exists |
| 5 unrecognised program word | B2 default-deny | allow-listed program with an unlisted write flag (mitigated by per-program flag tables for sed, find, awk) |
| 6 interpreter calls | B5 no inline code; pinned scripts; A for scratch scripts | scratch script building a path at run time, until A exists |
| 7 PowerShell / cmd | B3 not allow-listed | none while unlisted |
| 8 git abbreviations | B4 full-length options only | git config/alias reached through a file, not an option (checked by Layer C, not by B) |
| 9 git read subcommands that write | B4 explicit option deny | a git subcommand added by a future git version (allow-list is by name, so a new one is refused by default) |

**Honest summary:** B alone closes 5, 7, 8, 9 and narrows 2, 4, 6. **Only A closes 2, 4 and 6 completely**, and A needs Michael. C does not prevent; it makes a miss visible.

## 4. Cost, risk and what would make this wrong

- **Fail-closed regression risk is the main hazard.** A default-deny hook that refuses a legitimate close-out step stops a batch. Mitigation: build the allow-list from the measured corpus, then replay **all 18,995 recorded calls** through the new `decide()` offline (as text, nothing run) and report how many are refused and why. A refusal rate above a few percent on genuinely read-only calls means the grammar is too narrow and is reopened before any rollout. This replay is the acceptance gate, and its numbers are stated before the hook is switched.
- **Fail-closed means a broken manifest, an unreadable allow-list or an unparseable command is a REFUSAL** with the failure named, never a pass (CLAUDE.md fail-closed rule; PR 1.11). `exit 2` on every escape from `main`, as b117 already did for crash-open.
- **The b91 rule has two halves and a sandbox serves only one.** "Do not WRITE builder trees" is enforceable by A. "Do not RUN builder code, because its output is not independent evidence" is a policy about trust, not about bytes: a read-only process can still run a builder test. B keeps the exec check (exact-path exemptions, `EXEC_OK_TOOLS`) as defence in depth; no sandbox removes the need for it.
- **A hook that is itself self-protected cannot be updated by me** (live copy under `~/.claude`). Every rollout step below that touches it is Michael's copy step, as in b116 and b117.
- This design does not touch the other agents' hooks. It covers the clone that wires it; builders have their own and the deny-blocks log is shared.

## 5. Verification plan (before any rollout; follows the cross-domain disciplines)

1. **Known-bad controls first, locked before code** (discipline: lock criteria on synthetic fixtures): one fixture per open class (7), each shown PASSING (wrongly) on the current hook and REFUSED on the new one, plus two controls per class for the legitimate neighbour that must still pass.
2. **Ablation per layer** (discipline 12): with A off, B alone; with B off, A alone; measure per class which layer carries it. A table that shows B alone leaving 2, 4, 6 partially open is the expected result and is reported as such.
3. **Corpus replay** of the 18,995 recorded calls (text only) as in section 4; separately replay the refused set from `deny-blocks.log` and confirm every previously refused call is still refused.
4. **Independent reader:** hand the finished parser to H2 with the seven fixtures withheld, and ask for a new class. The nine came from H2; a design that has not been attacked by H2 is another first-reader artifact.
5. **Live probe after the copy** (still owed from b98 for the existing hook): the fixtures run as real tool calls, not as text through `decide()`, because the harness's own handling of exit codes is what b117 class 1 turned on.

## 6. Order of work, and what needs Michael

1. (hover, no approval needed) Lock fixtures; write the corpus replay harness; measure refusal rate of a **prototype** allow-list on a scratch copy. Nothing live changes.
2. (hover) Layer C tree-hash comparison, hover-owned.
3. (Michael) Decide A1 vs A2 vs "B and C only, classes 2/4/6 stay narrowed". This is the one decision; everything else follows from it.
4. (hover, then Michael copies) Rollout of B in tracked copy; live probe; H2 attack round.

**Decision needed from Michael:** A1 (separate Windows account), A2 (WSL/container, read-only bind mounts), or accept B+C with 2, 4, 6 documented as narrowed rather than closed.
