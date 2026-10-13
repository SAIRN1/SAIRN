# DECISION RECORD — the external-files check should WARN, not BLOCK, on another session's untracked Drive handoff

**Written by fourth/ted, batch b8 item 12, 2026-10-13. ROUTED TO cc**, who owns
`tools/external_file_index_check.py` and `docs/external-files-index.json` by the
b6 directory rule. **This record decides nothing on cc's behalf and changes no
code** — it states a decision Michael has already made, with the evidence that
supports it, so cc has something to implement rather than an opinion to weigh.

**THE DECISION, as given:** the external-files check should **warn** on another
session's untracked Drive handoff, and must **not** block the push. I did not
override the current behaviour in getting here.

---

## 1. WHAT THE LOG SHOWS, counted rather than recalled

`docs/BYPASS-LOG.jsonl`, 95 rows at this HEAD:

| session | rows |
|---|---:|
| fourth | 47 |
| hank | 21 |
| cc | 14 |
| cody | 13 |

**Every single one of hank's 21 is `check: "ALL"`, `blanket: true`** — the
`SAIRN_SEED_GATE=off` form that disables all of the gate's checks rather than
the one that refused. The six most recent cluster inside seven minutes on
2026-10-13 (`05:59:05`, `05:59:34`, `05:59:45`, `06:04:20`, `06:06:53`) and come
in pairs, because one push writes two rows — the Bash-hook path and the prepush
path both record.

**THAT PAIRING MATTERS FOR READING THE FIGURE.** 21 rows is not 21 decisions to
override; it is roughly half that many pushes. Nobody should quote the row count
as a count of bypasses, and this paragraph exists so the next reader does not.

## 2. WHY A BLANKET OVERRIDE IS THE PREDICTABLE RESPONSE

The gate's own SOFT CAPTURE text says it: *"This replaces reaching for
`SAIRN_SEED_GATE=off`, which skips all fourteen checks and leaves you re-running
them by hand to find out what it hid."* The scoped mechanism exists —
`SAIRN_GATE_EXEMPT=<check>` — and `EXEMPTABLE` at
`tools/sairn_push_gate_hook.py:860` is **`{'seed': 'seed-gate'}`**: one entry.

So a session blocked by the external-files check has exactly two options: the
blanket flag, or not pushing. **A gate with no scoped exemption teaches the
blanket one**, and the log is what that looks like after a fortnight.

## 3. WHY THIS PARTICULAR CHECK SHOULD NOT BLOCK

**The condition it fires on is not caused by the session it blocks.** Measured
across b5–b8, the file named in the refusal was somebody else's every time but
once:

| batch | files named in the refusal | mine |
|---|---|---|
| b5 | `handoff-h2-2026-10-11b.md` | 0 of 1 |
| b6 | `handoff-fourth-2026-10-11.md` | 1 of 1 |
| b7 at push time | none — the gate was CLEAR, exit 0 | — |
| b7 at report time | `handoff-hank-2026-10-12.md`, `handoff-h2-2026-10-12d.md`, `SAIRN-handoff-h1-b13.md` | 0 of 3 |

**AND THE QUEUE IS REFILLED BY COMPLIANCE.** Every session is instructed to
upload its handoff to the Drive folder the moment it is written;
`g:\my drive\sairn-status\` is a declared, non-transient external directory; a
handoff uploaded there is by construction neither git-tracked (different path)
nor indexed (nothing adds a row automatically). So **following the instruction
arms the gate against the next session**, and the next session's only lever is a
blanket override of fourteen unrelated checks.

A gate that fires on a condition the blocked party did not create and cannot
clear without editing another session's file is not enforcing a standard. It is
converting other people's compliance into your refusal.

## 4. WHAT WARN-NOT-BLOCK KEEPS

**The check is right about the underlying problem and should keep saying so.**
Its own words: *"A handoff nobody can find is worse than no handoff — the next
session reads the one it CAN find."* That is true, and three unindexed handoffs
is a real gap in the record. Warning keeps the whole signal; it only stops the
signal from being load-bearing on an unrelated push.

**WHAT MUST NOT BE LOST IN THE CHANGE, and this is the half a warn-only patch
usually drops:**

1. **The count must stay in the output of every push**, not move to a tool
   somebody has to remember to run. A warning nobody sees is the silence this
   platform keeps paying for.
2. **MY OWN FILE MUST STILL BLOCK.** The argument above is entirely about
   *another* session's upload. A handoff **I** wrote and did not index is mine to
   fix before I push, and softening that would remove the only pressure that
   keeps the index current at all.
3. **"Could not read the external directory" must stay a refusal.** An
   unreachable Drive mount is a third state, not an empty one, and folding it
   into "warn" would make the check pass loudest exactly when it knows least.

## 5. THE SHAPE, for cc to implement or reject

| | |
|---|---|
| file | `tools/external_file_index_check.py` |
| caller | `tools/sairn_push_gate_hook.py`, the external-file-index check |
| the discriminator | does the unindexed file belong to THIS session? |
| if mine | **BLOCK**, unchanged |
| if another session's | **WARN**: print the names and the count, exit 0 for gate purposes |
| if the directory is unreadable | **BLOCK**, unchanged — could-not-tell is not a pass |
| and regardless | add this check to `EXEMPTABLE` at `tools/sairn_push_gate_hook.py:860`, so a scoped exemption exists even after the change |

**HOW "MINE" IS DECIDED IS cc's CALL AND IS THE ONLY HARD PART.** The filename
convention (`handoff-<session>-<date>.md`, `SAIRN-report-<session>-<batch>.txt`)
is the obvious key and it is a convention rather than a guarantee — `h1`, `h2`
and `hank` are three spellings in that folder today, and
`SAIRN-handoff-h1-b13.md` inverts the word order. A session-name parser that
guesses wrong in the permissive direction would let my own unindexed file
through, which is the one case that must still block. **If it cannot be decided
reliably, blocking only on an EXACT match of my own session name and warning on
everything else fails in the safe direction.**

## 6. WHAT THIS RECORD IS NOT

* **Not an edit to cc's files.** Nothing under `tools/` was touched.
* **Not a claim that hank was wrong.** With one scoped exemption in `EXEMPTABLE`
  and a refusal caused by somebody else's upload, the blanket flag was the only
  lever available. The log is evidence about the gate, not about hank.
* **Not an override.** b8 attempted one push, it was refused by a different
  check, and `SAIRN_SEED_GATE=off` was not used — `docs/BYPASS-LOG.jsonl` gained
  no `fourth` row this batch, which is the mechanical check on that sentence.
