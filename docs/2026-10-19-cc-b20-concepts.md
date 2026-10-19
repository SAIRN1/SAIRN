# cc b20 — the concept for context-verify, stated BEFORE the code

**Committed before `tools/context_verify.py` exists**, so the ordering is
provable from `git log`. Every number below was measured first, and two of the
measurements changed the design.

---

## The one line

**REAL context% is the LAST ASSISTANT TURN's whole prompt — `input_tokens` +
`cache_read_input_tokens` + `cache_creation_input_tokens` — over the smallest
published window for that turn's own model that the measured prompt actually
fits in, read out of each agent's newest transcript in its own project folder;
and anything that cannot be resolved is COULD NOT TELL rather than a
percentage.**

---

## 1. `cache_read_input_tokens` is COUNTED, and so is `cache_creation`

Not a judgement call — measured on all four build agents' live transcripts,
2026-10-19T14:29Z:

    hank    input_tokens 2   cache_creation 112    cache_read 670,816
    cc      input_tokens 2   cache_creation 1,501  cache_read 654,276
    cody    input_tokens 2   cache_creation 596    cache_read 616,217
    fourth  input_tokens 2   cache_creation 523    cache_read 584,884

**`input_tokens` alone is TWO.** A figure built on it would report every agent
at 0.0% of its window while each is carrying over half a million tokens of
prompt. All three fields are parts of one prompt — uncached, read from cache,
and written to cache on this turn — so the real context is their sum. Omitting
`cache_creation` would be a smaller version of the same error.

## 2. The window size CANNOT be read from the transcript, and that is measured

Searched cc's own 4.7MB transcript for `context_window`, `1m` and the literals
`200000` / `1000000`. **Every hit is prose or an echoed command of cc's own —
there is no structured window field anywhere in the file.**

So the window comes from the model string on the assistant turn plus a table
declared in the tool. **And the model string does not settle it:** all four
agents record `claude-opus-5`, while this session's own model id is
`claude-opus-5[1m]` — the 1M variant records the same string a 200k session
would.

**The rule, therefore: the window is the SMALLEST tabled window for that model
that the measured maximum prompt actually fits in.** cc's own maximum observed
prompt is 657,248 tokens, which is evidence — not an assumption — that the
session is not on a 200k window. If a prompt exceeds every tabled window the
answer is **COULD NOT TELL**, never a percentage over 100 with a denominator
known to be wrong.

## 3. Resolving each agent's current session

`~/.claude/projects/C--Users-marsh-Documents-SAIRN-<agent>/` →
**the newest `*.jsonl` by mtime**, then the last record in it carrying an
assistant `message.usage` with an `input_tokens` key.

**The limits, stated now rather than discovered:**

- **mtime is a proxy for "current".** A resumed older session, or a compaction
  that starts a new file, changes which file is newest. The tool prints the
  session id and the file's age so a reader can see what it chose.
- **The newest transcript may be stale.** An agent that stopped hours ago still
  has a newest file; the figure is then *that session's last turn*, which is
  true and not current. The age is printed beside it for exactly this reason.
- **A folder with no `*.jsonl` is COULD NOT TELL**, not 0%.
- `hank` has 44 transcripts, `cc` 46, `cody` 44, `fourth` 46 — so picking the
  wrong one is a real failure mode, not a theoretical one.

## 4. Scope: the four build agents ONLY

`hover` and `hover2` are **excluded by the separation boundary, not by
oversight.** Their project folders exist on this machine, and reading an
auditor's own transcript from a build clone is the same boundary violation as
writing into its clone — running the wrong way. The tool must not list them,
and a reader must be told that is a decision rather than a gap.

## 5. Independence is the whole point

The tool **never reads any agent's self-reported `CONTEXT` line**, not from the
status registry and not from a digest. It reads transcripts only. The board
then publishes both figures side by side — self-reported and verified — so a
disagreement is visible instead of averaged away. **The self-report is not
replaced**; a figure that silently overwrote the thing it was meant to check
would leave nothing to compare.

**And the honest limit of the comparison:** the two figures measure slightly
different moments — the self-report is whatever the agent last wrote with
`set --context`, the verified figure is its last assistant turn. A gap between
them is often just elapsed time, so the board prints the age of each rather
than inviting a reader to treat any difference as a lie.
