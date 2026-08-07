# SAIRN Backlog

Deferred items — not urgent, not forgotten. Pick up at a natural pause,
not mid-session. Each entry: what, why deferred, what "done" looks like.

## Rebuild graphify's knowledge graph, properly scoped

**Logged:** 2026-08-07

**What:** Re-run graphify against only `C:\Users\marsh\Documents\SAIRN`
(or wherever the live SAIRN app files actually live), at the current
commit, not the whole `C:\Users\marsh` git root.

**Why deferred:** Current graph (`graphify-out/graph.json`, built
2026-07-31 at commit `df84b21`, 84 commits stale as of this logging) is
unusable for its intended purpose — 91% of its 191,739 nodes are
unrelated `AppData\Local\Microsoft\Edge`/`Office` noise from an unscoped
directory walk, and it contains **zero** nodes for the actual live
`stonedesk.html`/`sairngrounds.html` files. Confirmed via two real
queries (`explain "grdData"`, `explain "sairngrounds.html"`) both
returning "no node matching."

**Done looks like:** A fresh `graphify .` run scoped to just the real
SAIRN app files, current commit, verified by querying a symbol that
exists in the current codebase (e.g. a function added this session) and
getting a real match back — not just "the command completed."

**Standing reminder:** re-run after any major merge, same staleness
problem will recur otherwise. The `graphify` skill is set to `"off"` in
`.claude/settings.local.json`'s `skillOverrides` until this is done —
its current output shouldn't be treated as authoritative for duplicate-
feature checks in the meantime.
