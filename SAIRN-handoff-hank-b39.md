# SAIRN handoff — hank b39 — 2026-10-21

**Subject:** root cause of hank's `npm install` block. Diagnosis only — no code, no config change. Written
before the report, nothing half-finished.

## 1. PUSHED STATE
This batch commits only these three documents. **NOT FORCED.** Re-derive the tip after the push.
`.claude/settings.local.json` unchanged (13 deny / 1213 allow).

## 2. CLAIMS HELD
None (released at the end of the batch).

## 3. THE ITEM
**Concept, before any change:** *a deny that lives in a layer every clone shares cannot be fixed by one clone —
the diagnosis names the layer and the decision that put it there, and stops.*

**Reproduced, harmlessly:** `npm install --dry-run` in this clone → `Permission to use Bash with command npm
install --dry-run has been denied.` (a dry run writes nothing, so the probe was safe either way).

**Root cause — the rule exists TWICE, at two shared levels, and neither is hank-only:**
| layer | file | entries | reaches |
|---|---|---|---|
| user | `~/.claude/settings.json` `permissions.deny` | `Bash(npm install *)`, `Bash(npm install)`, `Bash(npm i *)`, `Bash(npm ci *)`, `Bash(npm ci)`, `Bash(npm add *)` (+ yarn/pnpm/pip) | every Claude session on this machine, every clone |
| project (tracked) | `.claude/settings.json` `permissions.deny` | the same 12 | every clone that pulls `main`, hover clones included |
| local | `.claude/settings.local.json` | none | — |

Introduced by `392249206` (2026-10-13, cc b5, "mechanical deny/allow rules … on Michael's instruction");
rationale in that file's `_permissions_note` and `docs/2026-10-13-cc-routed-b5.md`. **Deny wins at every level
and an allow cannot carve an exception**, so no `settings.local.json` change could unblock hank alone, and
removing either entry would unblock every session. That is not a one-line fix scoped to me → **HELD.**
Also: `Edit`/`Write` on both settings files are themselves denied, and the auto-mode classifier refused a
settings write in b38 as self-modification.

**No record of hank actually needing npm install:** no denial in any hank transcript or hank handoff/report;
the repo has no `npm install` in a hank work item. If a task needs a package, the route is Michael running the
install once, not lifting the rule.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| N1 | npm install denied at user + project level | Michael: keep (the b5 intent), or name the one command to allow and run it by hand. Lifting needs removal from BOTH layers |
| H2 | Bash deny on cc, cody, fourth | Michael, per `SAIRN-handoff-hank-b38.md` §4 |
| H3 | `~/fix-deny.ps1` case-insensitive dedup | Michael, per b38 §4 |
| C | Static Maps on the Maps key | Michael, Cloud Console |
| B | snapshot re-export (b35 G) | Michael, per `SAIRN-handoff-hank-b35.md` §4 |
| D | untracked `conflict_excerpt.txt`, `full_conflict.txt`, `dir`, `resolve_conflict.py`, `schema_snapshot_raw.json`, `.claude/settings.json*.bak` | not mine, not touched |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
