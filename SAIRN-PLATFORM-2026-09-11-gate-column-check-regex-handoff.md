# SAIRN Platform — Handoff, 2026-09-11 (`gate_column_check.py` sees 4% of its subject)

**Written for CC**, who holds the claim `gate-reads-nonexistent-column`. Found
while triaging two new reds in the full suite, not by looking for it.

**Not fixed, because the file is inside your active claim.** It is a
one-character change.

---

## The finding

`tools/gate_column_check.py:60`:

```python
REST_RE = re.compile(r"/rest/v1/([a-z_][a-z0-9_]*)|<BS>rest(?:Url)?\(\s*'([a-z_][a-z0-9_]*)")
```

`<BS>` is a **raw 0x08 backspace byte**, typed where `\b` (word boundary) was
meant. In a raw string `\b` would be the two characters backslash-b; what is on
disk is the control character itself, so the second alternative requires a
literal backspace in the source being scanned. Source files do not contain one.

**That alternative can never match.** Measured directly against the pattern as
it sits on disk:

```
rest('rpc                    -> NO MATCH
  rest('cl_rate_limit_log    -> NO MATCH
restUrl('foo                 -> NO MATCH
/rest/v1/bar                 -> /rest/v1/bar      <- the first alternative still works
```

With `\b` restored, `rest('rpc` matches and `xrest('rpc` correctly does not —
so the word boundary is doing real work and is not decorative.

## What it costs, counted rather than described

Across every tracked `*.js` and `*.html` outside `archive/`:

| | call sites | distinct tables |
|---|---|---|
| seen **as shipped** | 26 | 7 |
| seen **with `\b`** | 498 | 162 |
| **invisible** | **472** | **155** |

The checker is reading **5% of the call sites and 4% of the tables** while its
output reads as a complete answer. Among the tables it never sees:
`alf_clients`, `alf_mar`, `alf_staff_credentials`, `alf_compliance_rules`,
`ai_memories`, `business_profiles`, `bld_tna_assessments`,
`accounting_connections` — i.e. most of the platform, including the clinical
and credential tables.

**This matters for the conclusion, not just the tool.** Any "no gate reads a
column that does not exist" result from this run is a statement about 4% of the
surface. The trial-expiry gate that started this whole row was found in
`api/sd-data.js`, which the surviving first alternative does happen to cover —
so a green run would look consistent with the known case while missing the rest.

## How it surfaced

Two new reds in the full suite, both tracing to this one file:

- `tests/run_control_char_probe.py` — *"the real SAIRN tree is currently clean"*
  fails; `tools/control_char_check.py` names the byte at `:60`, offset 2966.
- `tests/run_report_only_checks_probe.py` H6 — *"a clean sweep stays silent"*
  fails, because the promoted sweep now reports both this byte and
  `gate_column_check.py` exiting 1.

**The control-char checker did exactly what it was built for.** CLAUDE.md
records that two of the four literal control bytes found on 2026-09-10 *"were
regexes that could never match, one of them guarding a database privilege"* —
this is the third, in a checker written the same week.

## Suggested fix

Replace the raw byte with the escape sequence, which is what the checker's own
message asks for: `r"...|\brest(?:Url)?\(\s*'..."`. The runtime string changes
meaning (that is the point); the file also becomes searchable.

**Worth re-running your conclusions afterwards** — with 472 more call sites in
view, the finding set is likely to be different rather than merely larger.

## Standard verification reminder

Re-verify before acting: `python tools/control_char_check.py` names the byte,
and the match table above reproduces from the pattern as it sits on disk. This
document is a claim like any other.
