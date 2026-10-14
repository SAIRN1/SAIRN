# `c78b545b`'s five unreviewed siblings — owner named for each, and each routed

**fourth, batch b20, 2026-10-14.** Closing the bound my own b19 verdict put on
itself.

**WHY THIS EXISTS.** `docs/2026-10-14-fourth-b19-hover2-citation-linter-discharge.md`
discharged hover2's obligation on **one** file of `c78b545b` and said so in the
register verdict: *"the other five are NOT reviewed and are not blessed by this
verdict."* **That sentence is only worth having if somebody then names them.**
This document names all five, names an owner for each from evidence rather than
assumption, and routes each. **It reviews none of them** — routing is not
reviewing, and saying otherwise would repeat the defect b19 was avoiding.

---

## 0. THE COMMIT, EXACTLY

```
CMD git show --name-only --format="" c78b545b
  .claude/skills/sairn-hover-auditor/tools-hover2/claim_collision_scan.py
  .claude/skills/sairn-hover-auditor/tools-hover2/dependency_health_check.py
  .claude/skills/sairn-hover-auditor/tools-hover2/hover_citation_linter.py     <- reviewed in b19
  .claude/skills/sairn-hover-auditor/tools-hover2/hover_cold_scan_pool.py
  .claude/skills/sairn-hover-auditor/tools-hover2/hover_self_health_fires.jsonl
  .claude/skills/sairn-hover-auditor/tools-hover2/hover_self_health_hook.py

CMD git log -1 --format="%an | %ad | %s" --date=iso c78b545b
  Michael Dibert | 2026-09-29 20:57:33 -0400 | chore(hover2): sync 6 fixed tools to the platform-repo backup
```

**A CORRECTION TO MY OWN b19 WORDING, AND IT IS NOT PEDANTRY.** b19 said the
commit *"synced SIX tools"*. **It touched six PATHS, of which five are `.py`
and one is a `.jsonl` data file.** So the five unreviewed siblings are **four
tools and one data file** — and the data file turns out to be the most
interesting of the five (§2.5). **A count of "tools" that silently includes a
log is the same shape of error as a count of "checks" that includes a skip.**

**The commit author is Michael, not hover2.** That matters for routing only in
that it confirms the commit is a *sync of hover2's working copies into the
platform backup* rather than hover2 committing from its own clone — which is
consistent with the obligation's own account of why hank had to open the
record on hover2's behalf.

---

## 1. HOW THE OWNER WAS DETERMINED — evidence, not assumption

**This platform has an owner convention and a tool that reads it.**
`tools/tool_owner_map.py` resolves ownership from, in order: an `# OWNER: name`
line in the file; then claim history; then git history (`UNRECORDED`); then
`UNKNOWN`.

**MEASURED FIRST, because it changes the answer: none of the four tools carries
an `# OWNER:` line.**

```
CMD grep -m1 -E '^#\s*OWNER:' <each file>, both trees
  claim_collision_scan.py      hover2 copy: NONE    h1 copy: NONE
  dependency_health_check.py   hover2 copy: NONE    h1 copy: NONE
  hover_cold_scan_pool.py      hover2 copy: NONE    h1 copy: NONE
  hover_self_health_hook.py    hover2 copy: NONE    h1 copy: NONE
```

**So the owner had to come from the directory and from commit provenance, and
both are unambiguous:**

```
CMD git log --oneline -12 -- .claude/skills/sairn-hover-auditor/tools-hover2/
  chore(hover2 audit): batch b19 ...        feat(hover2-tools): ...
  chore(hover2 audit): batch b18 ...        fix(hover2-tools): ...
     -> every commit scoped `hover2` / `hover2-tools`

CMD git log --oneline -6 -- .claude/skills/sairn-hover-auditor/tools/
  fix(hover): one tracked hover_tip_beacon.py ...
  fix(hover): one tracked hover_log.py ...
  chore(hover): self-health fires log, routine appends
     -> every commit scoped `hover`
```

**`tools-hover2/` is H2's tree. `tools/` is H1's tree.** All five paths in
`c78b545b` are under `tools-hover2/`, so **the owner of all five is `hover2`**,
and that is the routing answer for every row below.

### THE TRAP THIS CHECK WALKED INTO, AND IT IS THE REASON TO STATE THE METHOD

**All four tools exist under BOTH names, and the two copies are NOT mirrors of
each other:**

| basename | H1's `tools/` | H2's `tools-hover2/` | differing lines |
|---|---:|---:|---:|
| `claim_collision_scan.py` | 263 | 583 | 780 |
| `dependency_health_check.py` | 145 | 363 | 464 |
| `hover_cold_scan_pool.py` | **1738** | **716** | 2348 |
| `hover_self_health_hook.py` | 382 | 460 | 748 |

*(Compared after `tr -d '\r'`, per the standing rule that a CRLF-vs-LF
difference is not drift.)*

**`hover_cold_scan_pool.py` is 1738 lines in H1's tree and 716 in H2's.** These
are **independent tools that share a name**, not one tool mirrored into two
places. **So "route the sibling to the auditor" would have been ambiguous
between two owners**, and a router that resolved it by basename would have sent
H2's work to H1 or vice versa. **The path is the owner, not the name.**

---

## 2. THE FIVE, EACH WITH ITS OWNER AND ITS ROUTE

**Every row's owner is `hover2`.** What differs is *what* is routed and *why*,
and one row is routed to a second party as well.

### 2.1 `claim_collision_scan.py` — 8 lines changed in `c78b545b`

| | |
|---|---|
| **owner** | **hover2** — `tools-hover2/`, no `# OWNER:` line, provenance `hover2-tools` |
| **what it is** | by name, a scanner for colliding claims across sessions. **Not read beyond the name and the line count** |
| **route** | **hover2: does this file need its own Tier A obligation?** The b19 verdict's premise — read-only toward platform data, writes only to `%TEMP%`, platform resources only as frozen fixture tokens — was established **for `hover_citation_linter.py` and for nothing else.** A claim scanner reads `.claude/claims/*.json`, which **is** platform data, so the premise is not transitive |
| **plus** | **add an `# OWNER: hover2` line.** One line per file closes the whole class |

### 2.2 `dependency_health_check.py` — 5 lines changed

| | |
|---|---|
| **owner** | **hover2** — same basis |
| **what it is** | by name, a dependency-health reporter. **Not read** |
| **route** | **hover2: same question.** A dependency checker is the shape most likely to shell out, and `hover_citation_linter.py`'s clean bill rested in part on `grep -n '\bgit\b'` returning **zero matches**. **That is a per-file fact and it has not been established here** |
| **plus** | the `# OWNER:` line |

### 2.3 `hover_cold_scan_pool.py` — 50 lines changed, **the largest code delta of the five**

| | |
|---|---|
| **owner** | **hover2** — same basis |
| **what it is** | by name, the cold-scan rotation pool. **Not read** |
| **route** | **hover2, and this is the one I would open an obligation on first.** It is the biggest change in the commit, and **its same-named H1 counterpart is 1738 lines against this one's 716** — so whichever of the two is authoritative, a reader who finds the wrong one is reading a different program. **Say which tree is canonical for this tool, or stop sharing the name** |
| **plus** | the `# OWNER:` line |

### 2.4 `hover_self_health_hook.py` — 61 lines changed

| | |
|---|---|
| **owner** | **hover2** — same basis |
| **what it is** | by name, a self-health hook. **Not read** |
| **route** | **hover2 — and this one has a second route, to a platform question I cannot answer from the auditor's side.** The word **hook** is load-bearing on this platform: my standing instruction every batch is *never restore or add hooks*, and hooks in this clone are cleared. **A file named `..._hook.py` inside a skill tree may be an ordinary module with "hook" in its name, or it may register something.** Which it is decides whether it is in scope for the hook rule at all. **I did not open it, so I am not guessing** |
| **plus** | the `# OWNER:` line |

### 2.5 `hover_self_health_fires.jsonl` — **NOT A TOOL, and it is no longer there**

| | |
|---|---|
| **owner** | **hover2** for the path; **the data is hover2's own self-health log** |
| **measured** | ① `c78b545b` added this exact path (`git show --name-only`). ② **It is not tracked at HEAD** — `git ls-files` on it is empty. ③ **It is gitignored**, by a `.gitignore` *inside that directory*: `.claude/skills/sairn-hover-auditor/tools-hover2/.gitignore:1:hover_self_health_fires.jsonl`. ④ The same basename **does** exist and **is** tracked in H1's tree, at 44 lines |
| **route** | **hover2: a file your own commit added is now ignored at that path, and the commit's own description calls the change a "sync to the platform-repo backup".** If the intent was that the log should NOT be in the backup, **the ignore is right and `c78b545b` should not have added it** — in which case the commit did one thing it did not mean to. If the intent was that it SHOULD be backed up, **the backup is silently not happening.** Either way it is one line of intent that is currently undeclared |
| **and the reason it matters beyond tidiness** | this is **the same shape as the `sd_photos` finding in my b19 batch**: a thing the system believes it is backing up, that the storage layer is quietly refusing. There the refusal was a size cap misreported as an unprovisioned table; here it is a `.gitignore`. **Neither is loud, and in both cases the local copy still exists, so nothing looks wrong** |

**UNVERIFIED — the mechanism, not the facts.** `git log --all -- <that path>`
returns **nothing**, and `--diff-filter=D` returns nothing, while
`git show --name-only c78b545b` lists it. **I cannot reconstruct from this
clone how the path went from added to untracked**, and I am not going to
narrate a deletion that no commit records. **The four numbered facts above are
measured; the story joining them is COULD NOT TELL.**

---

## 3. THE ONE ASK THAT COVERS ALL FIVE

**`# OWNER: hover2` at the top of each of the four `.py` files.**

`tools/tool_owner_map.py` exists precisely because *"most tracked tools carry no
`# OWNER:` line"*, and its own documentation says **the OWNER_LINE count is the
number to watch.** Four files, four lines, and the routing question this whole
document answers stops needing a document: **the next session greps.**

**I did not add them.** The auditor skill tree is read-only under my b20 claim
and a build agent must not reach into it — which is the same boundary b19's
discharge held, and holding it here costs four lines of somebody else's typing
rather than a boundary.

---

## 4. WHAT THIS DOCUMENT DOES NOT CLAIM

1. **It reviews none of the five.** Every "what it is" above is **from the
   filename**. I opened none of the four tools' bodies. **Routing is not
   reviewing** — and a routing document that implied otherwise would recreate
   exactly the gap b19 named.
2. **It does not open Tier A obligations.** The gate assigns a reviewer when a
   record is opened, and opening five records on another session's behalf is a
   decision about somebody else's queue. **hover2 decides whether each needs
   one; §2 says what I would ask first.**
3. **It did not enter either auditor clone.** `Documents\SAIRN-hover` and
   `Documents\SAIRN-hover2` were not read, listed or entered. Everything is from
   this clone's tracked mirror.
4. **It does not claim the b19 premise extends.** That premise was established
   for one file by reading all 701 of its lines and driving it four ways.
   **Four files sharing a directory with it inherit nothing**, and the §2 rows
   say which specific half of the premise is unestablished for each.
5. **It does not resolve the two-trees problem.** Four basenames exist in both
   auditor trees with substantially different contents. **Naming which tree is
   canonical is hover2's and hover's call, jointly** — and until it is made, any
   future routing by basename is a coin flip.
