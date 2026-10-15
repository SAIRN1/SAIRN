# Compaction diagnosis — cody b17, 2026-10-15

**Read-only. Nothing was changed by this diagnosis.** Every figure below was
measured with the command shown; none is read from a document.

## The verdict, first

**None of the three offered verdicts. The premise is not reproducible from any
record on this machine.**

> **232 transcripts across all six SAIRN clones contain ZERO structural
> compaction events.** Not "few" — none. And every clone's sessions reach
> **957,000–999,683 context tokens** before they end.

* **Threshold too low?** No — it is set as high as it goes. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=97`.
* **Window smaller than assumed?** No — the measured ceiling is the full
  ~1,000,000 of `claude-opus-5[1m]`. Peak ever observed: **999,683** (fourth).
* **Flooding by my own tests?** No. The largest single tool result across the
  last five cody sessions is **24,190 chars ≈ 6k tokens**, and a whole
  session's tool results sum to **≈122k tokens = 12% of the window**. The
  persisted-output mechanism already caps any result over ~20KB to a file.

**What is actually happening instead:** these sessions do not compact, they
**end** — either stopped at 70% on instruction (b14, b15, b16) or sitting at
the ceiling. At the fastest growth rate ever measured here (**5,820 tok/min**)
a 1M window takes **2.6 hours** to fill, and at the median rate (~1,000
tok/min) it takes **15 hours**. "Every 5–15 minutes" is three orders of
magnitude away from the measured rate; nothing in these transcripts can produce
it.

---

## Which source wins, and its value

**`env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = "97"` in `C:\Users\marsh\.claude\settings.json`
(user scope).** It is the **only** autocompact knob set anywhere on the
machine, so there is nothing for it to lose a precedence contest to. Confirmed
live in the process environment, not just on disk:

```
$ printenv CLAUDE_AUTOCOMPACT_PCT_OVERRIDE
97
```

### Everything else, measured absent

| Knob | user | user.local | project | local | managed | live env |
|---|---|---|---|---|---|---|
| `autoCompactWindow` (top-level) | absent | absent | absent | absent | **no file** | — |
| `modelSettings.<model>.autoCompactWindow` | **no `modelSettings` block** | none | none | none | **no file** | — |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | — | — | — | — | — | **unset** |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | **`"97"`** | — | — | — | — | **`97`** |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | — | — | — | — | — | **unset** |
| `ANTHROPIC_BETAS` | — | — | — | — | — | **unset** |
| `DISABLE_AUTO_COMPACT` | — | — | — | — | — | **unset** |

Neither managed-settings path exists on disk:
`C:\ProgramData\ClaudeCode\managed-settings.json` and
`C:\Users\marsh\AppData\Local\ClaudeCode\managed-settings.json` are both
**missing**, so there is no managed override in play at all.

`.claude\settings.local.json` carries **only** a `permissions` key — no
compaction setting of any kind. `C:\Users\marsh\.claude\settings.local.json`
carries `effortLevel`, `model`, `outputStyle`, `permissions`, `skillOverrides`
— again none.

### Does the launch command pass `--autocompact`?

**No. Measured, not assumed.** All six live CLI processes were launched with no
arguments whatsoever:

```
$ powershell -NoProfile -Command "Get-CimInstance Win32_Process | ... CommandLine"
claude.exe | 15120 | "C:\Users\marsh\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"
claude.exe | 33312 | "...\claude.exe"
claude.exe | 20476 | "...\claude.exe"
claude.exe | 28160 | "...\claude.exe"
claude.exe | 20204 | "...\claude.exe"
claude.exe |  9368 | "...\claude.exe"
```

Six, one per clone plus one spare. Zero flags on any of them. CLI version
**2.1.222** (read from the `version` field of every entry in this session's own
transcript, 140 of 140 agreeing).

---

## The compaction events — there are none, and that is the finding

Scanned **every** `*.jsonl` under every `C--Users-marsh-Documents-SAIRN*`
project directory, matching on **structure** rather than on the word:
`type == "compact_boundary"`, `subtype == "compact_boundary"`,
`isCompactSummary is True` at either the entry or the `message` level.

```
SAIRN          transcripts=  0  compaction_events=0  max_ctx_tokens=0
SAIRN-cc       transcripts= 44  compaction_events=0  max_ctx_tokens=967,168
SAIRN-cody     transcripts= 42  compaction_events=0  max_ctx_tokens=998,916
SAIRN-fourth   transcripts= 43  compaction_events=0  max_ctx_tokens=999,683
SAIRN-hank     transcripts= 42  compaction_events=0  max_ctx_tokens=963,946
SAIRN-hover    transcripts= 33  compaction_events=0  max_ctx_tokens=971,934
SAIRN-hover2   transcripts= 28  compaction_events=0  max_ctx_tokens=962,703
```

**232 transcripts. 0 events.**

### A trap this diagnosis walked into and climbed out of, worth recording

A first pass searched for the **word** `compact` and reported the current
session as having `isCompactSummary:3`, `compact_boundary:3` and
*"This session is being continued from a previous conversation":1* — i.e. three
compactions in a 133-line fresh session whose peak context was 89,858 tokens,
which is impossible at a 97% threshold. Reading the lines showed every hit was
**my own search command and its own echoed result**, written into the
transcript by the act of searching. A substring search for a diagnostic marker
inside the log the search is being recorded in **finds itself**. The structural
scan above is immune and is the one the numbers come from.

### What a session does instead of compacting — the five most recent

| transcript | baseline | peak | peak at | growth rate | requests |
|---|---|---|---|---|---|
| `ee6c4b56` (b16) | 58,825 | 783,213 | +787.2 min | 920 tok/min | 749 |
| `ec3355ad` (b15) | 57,952 | 753,771 | +643.1 min | 1,082 tok/min | 708 |
| `6f734872` (b14) | 57,968 | 788,931 | +233.3 min | 3,133 tok/min | 588 |
| `7d8da884` | 57,441 | 165,436 | +18.6 min | 5,820 tok/min | 92 |
| `dcd1868a` | 57,470 | 455,049 | +620.0 min | 641 tok/min | 444 |

Peak = session end in all five. None reached the ~970,000 trigger point, so
none *could* have compacted even with the threshold correctly applied.

### The five largest tool outputs per session — the flooding question, answered

| transcript | tool results | total chars | ≈ tokens | top 5 single results (chars) |
|---|---|---|---|---|
| `ee6c4b56` (b16) | 529 | 488,392 | 122,098 | 12,424 · 11,090 · 9,763 · 9,401 · 8,719 |
| `ec3355ad` (b15) | 483 | 565,555 | 141,388 | 24,190 · 10,672 · 10,434 · 9,930 · 8,162 |
| `6f734872` (b14) | 383 | 384,624 | 96,156 | 15,341 · 10,112 · 9,206 · 8,160 · 8,101 |
| `7d8da884` | 54 | 127,466 | 31,866 | 17,355 · 13,263 · 8,210 · 6,725 · 5,352 |
| `dcd1868a` | 284 | 330,690 | 82,672 | 18,060 · 16,885 · 11,504 · 10,112 · 8,567 |

**No cap was needed and none was imposed.** The instruction said to cap test
output if the diagnosis found flooding; it did not. The largest single result
in five sessions is 24,190 chars, ~2.4% of the window, and it is a claim-tool
listing rather than a test run. Two results **were** auto-persisted to files
during this very session (23.9KB and 22.1KB `sairn_claim.py` outputs) — the
harness's own >20KB mechanism, working.

## The fixed baseline

**59,434 tokens**, measured from the first request of this session rather than
estimated:

```
input_tokens                     2
cache_read_input_tokens     24,842
cache_creation_input_tokens 34,590
                            ------
                            59,434
```

That is the floor every cody session starts from — system prompt + tool
schemas + `CLAUDE.md` (user + project) + `MEMORY.md` + the `SessionStart` hook's
status registry + the skills listing. It is stable to within 1,400 tokens
across the last five sessions (57,441 → 58,825), so it is not drifting.

**`/context` category breakdown is NOT included, and the reason is stated
rather than hidden:** `/context` is a client-side slash command and cannot be
invoked from a tool call, so any category split I printed would be my own
arithmetic wearing the command's name. The 59,434 total above is measured; the
split across its categories is not, and is left out.

---

## UNVERIFIED — the one thing this cannot settle

**Three sessions exceeded the 970,000 trigger point and still produced no
`compact_boundary` entry:** cody `998,916`, fourth `999,683`, cody `987,724`.
Two readings fit that equally well and the transcripts cannot separate them:

1. Compaction fired and CLI 2.1.222 does not write a structural marker for it
   into the `.jsonl`, in which case the 0 above is a measurement gap rather
   than an absence; or
2. Compaction never fired, and the session simply ran to the window ceiling.

Everything else here is measured. **This one is not, and the 0-events headline
should be read as "no record of any compaction", not as proof none occurred.**
Settling it needs a marker emitted at a known compaction, which this read-only
diagnosis cannot arrange.

## One thing found by accident, routed not fixed

**→ CC.** `C:\Python314\python.exe tools/run_all_tests.py` has been running in
`Documents\SAIRN-cc` since **08:12:23** (pid 79316) writing
`docs/sweep-2026-10-15.log`, and that log is **0 bytes after 1h41m** — the
tool's stdout is block-buffered, so a full-tree sweep gives no sign of progress
until it exits. Not mine, not touched. Flagged because a 0-byte log is
indistinguishable from a dead run, and cc may be waiting on something that
already died.

---

*Measured 2026-10-15 by cody b17. Commands are in the body next to each figure.*
