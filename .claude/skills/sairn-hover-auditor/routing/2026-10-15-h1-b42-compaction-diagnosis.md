# h1 b42 -- compaction diagnosis: no evidence of frequent compaction found; one undocumented config value, one tooling-verbosity contributor

**For the record, and DECISION-NEEDED items surfaced to Michael directly in
this batch's digest** -- this is not a defect report against any build
agent. The one actionable finding against a build agent's own tool
(item 3 below) is routed to cc.

## What was checked

1. **Env vars** (`env`, and explicit `printenv` on each named variable):
   only `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=97` is set, anywhere, on this
   machine. `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_CODE_MAX_CONTEXT_
   TOKENS`, `ANTHROPIC_BETAS`, `DISABLE_AUTO_COMPACT` are all unset.
2. **Settings files**: `autoCompactWindow` and `modelSettings.<model>.
   autoCompactWindow` were grepped for across `~/.claude/settings.json`,
   `~/.claude/settings.local.json`, this project's `.claude/settings.json`
   and `.claude/settings.local.json`, and all four build-agent clones'
   equivalent files (SAIRN-cc, SAIRN-hank, SAIRN-cody, SAIRN-fourth) --
   **zero matches anywhere.** No managed/enterprise settings.json was
   found on this machine (`/c/ProgramData`, standard install locations
   checked).
3. **Launch command**: `Get-CimInstance Win32_Process` on every running
   `claude.exe` (6 instances, consistent with H1/H2 plus four build
   agents) -- none carries a `--autocompact` flag. All launched bare.
4. **Compaction events in transcripts**: searched for `isCompactSummary`
   and any `"compact"` substring across this session's own transcript
   (`6472a233...jsonl`, now 1600+ lines) and every prior H1 transcript in
   this project directory, plus cc's largest available transcript
   (`5521d10f...jsonl`, 5.7MB) in `SAIRN-cc`'s own project dir (read access
   confirmed available cross-clone). **Zero compaction-boundary markers
   found anywhere.** `messageCount` (a field on `turn_duration` system
   events) climbs monotonically with no resets in every transcript
   checked -- 344 -> 2471 in one H1 session, 1153 -> 2791 in cc's -- which
   is inconsistent with compaction having fired at all in either, let
   alone every 5-15 minutes.
5. **Current usage vs. threshold**: this session's own real token count
   (measured via `tools/sairn_status_line.used_tokens()` against its own
   transcript) sits at roughly 40-42% of the 967K Sonnet-5 window at the
   time of this check -- nowhere near a 97% threshold, consistent with
   finding (4).

## What a specialist lookup (claude-code-guide) added

Asked for the documented precedence order and `/autocompact`/`/context`
semantics. Key finding: **`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` does not
appear in Claude Code's own documentation at all.** The documented
mechanism is absolute-token-based, not percentage-based: `/autocompact
500k` or `CLAUDE_CODE_AUTO_COMPACT_WINDOW` set an absolute token count;
documented precedence is CLI flag > `CLAUDE_CODE_AUTO_COMPACT_WINDOW` >
project-local `settings.json` > project-shared `settings.json` > managed
settings. Whether `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` is honored by the
current binary (2.1.222) at all is **unconfirmed** -- it may be a legacy
or internal-only variable, silently ignored, or converted to an absolute
figure the lookup could not find documentation for.

## Verdict

**The evidence does not support "every window compacts every 5-15
minutes" as something currently reproducible from this role's own or a
build agent's transcript data.** Neither "threshold too low" nor "window
smaller than assumed" nor "flooding" fits what was actually measured:
zero compactions occurred in either transcript checked, and current usage
is well under any plausible threshold in both. The most likely
explanations, in order: (a) the observation is from a different
interface this role cannot introspect (an interactive desktop/web
session, distinct from these autonomous CLI agent sessions); (b) the
observation predates this machine's current configuration; (c) a
terminology mismatch (something other than a full context compaction was
meant). **Not resolvable further from this role's own tooling** -- next
step, if the premise is confirmed real by Michael from the interface
where he observed it, is a fresh transcript from THAT session to compare
against the pattern found here.

## Secondary finding, routed to cc: a real token-consumption contributor, distinct from compaction itself

Not evidence of compaction, but a measured inefficiency worth cc's
attention since `tools/` is cc's scope: `tools/sairn_claim.py`'s
`list`/`claim`/`check` subcommands print the ENTIRE historical claim log
-- every claim ever taken, full free-text task strings included -- with
no limit, growing unbounded as the platform accumulates claims. This
role hit 11-30KB single-command outputs from this tool repeatedly across
b41 and b42, each requiring a truncate-to-file-plus-Read-back round trip
under this session's own `BASH_MAX_OUTPUT_LENGTH=10000` setting. This
does not cause compaction (see verdict above) but it is real, avoidable
token cost on every session that runs `sairn_claim.py list` or `claim`,
which is every build agent, every batch. A `--since <N>` or `--tail <N>`
option, or defaulting `list` to recent-plus-active rather than the full
history, would cut this substantially. Not fixed here: `tools/` is cc's,
not hover's, and this role's own scope gate (tested and confirmed
enforced last batch) correctly refuses this role from writing there.

## No fix made in hover's own scope

This role's own tools (`hover_log.py`, `hover_tip_beacon.py`,
`hover_timestamp.py`, the new `hover_chain_status_check.py`) were checked
for the same pattern -- none prints unbounded historical output by
default; `--tail N` already exists on `hover_log.py` and was used
throughout this session. No flooding source was found inside this role's
own scope to fix.
