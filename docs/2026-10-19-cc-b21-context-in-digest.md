# b21: the digest's context figure stops being typed, and the contrast gate is driven rather than read

**cc, 2026-10-19.** Two items, each with its concept stated before the code
was written, plus the one thing that went wrong while doing it and is a defect
in my own b20 work.

---

## Item 2 — the measured context figure, wired at the source

**The one-line concept, stated before any code:** *a build agent must not be
able to type a context figure into its digest at all — the `CONTEXT` line is
emitted by `context_verify.py --digest-line`, and a push gate re-derives it
from the pushing session's own transcript and denies any digest whose line is
not a measurement.*

### Why the board column was not enough

b20 measured the gap and then published it: every build agent's self-reported
context UNDER-READ the real figure by 7 to 12 points — cc 61.9 vs 68.8, cody
59.2 vs 66.3, fourth 48.0 vs 60.0, hank nothing at all vs 70.3. The board
gained a CONTEXT (VERIFIED) column beside the self-report, which makes the gap
**visible** and does nothing to stop the next digest carrying another estimate.
The defect is at the source and the source is a typed line.

### The arm with teeth is the token count, not the shape

An estimate can be written in the measured shape. What it cannot do is match,
**to the token**, a prompt size that a real assistant turn in that session's
own transcript actually carried. So:

1. The line must parse as `CONTEXT <pct>% of <window> -- <count> tokens, measured.`
2. `<pct>` must equal `round(100 * count / window, 1)` — this catches a real
   count with a hand-edited percentage over it, which is the exact under-read
   shape.
3. `<count>` must equal the prompt of some real assistant turn in that agent's
   transcripts. **This is the arm that cannot be talked past.**
4. `<window>` is checked **loosely** on purpose: a published size for the
   measured model, or the session's declared one. Not equal to the window
   measured at push time, because a session that crossed 200k between writing
   the digest and pushing it would have two honest answers and the gate would
   refuse the earlier one.

The transcript search is bounded to **24 hours**, measured rather than picked:
the four agents hold 44-47 transcripts and 246-275 MB each, and scanning all of
it in a push gate is not free — but only 1 or 2 per agent (4.8-5.9 MB) have
been touched in the last day, which is the only span a digest written this
batch can live in. The cost of the bound is stated in the tool: a figure from
an older session reads **UNMATCHED**, never **wrong**.

### Driven, in five directions

Each ran against a real digest file in a throwaway worktree provisioned with
cc's identity, with `context_verify.py --check-digest <file> --agent cc`:

| planted line | verdict | exit |
|---|---|---|
| `520,000 tokens` (fabricated, internally consistent) | `NOT_MEASURED` — "matches no assistant turn in any of this agent's 2 transcript(s) touched in the last 24h" | 1 |
| no `CONTEXT` line at all | `MISSING` — and the reason is the command to run | 1 |
| real count `192,782`, percentage typed as `12.0%` | `INCONSISTENT` — "192,782 tokens of 1,000,000 is 19.3%, and the line says 12.0%" | 1 |
| the tool's own output, unedited | `OK` — "matched a real assistant turn in c44c9acc (160 turn(s) read)" | 0 |
| a `SAIRN-digest-H1-*.txt` with `--agent hover` | `COULD_NOT_TELL` — outside the four by the separation boundary | 2 |

And the **whole pre-push hook** was driven on the fabricated one: it refused,
naming the file and quoting the verdict. Evidence: `ctx_fab.txt`, `ctx_ok.txt`,
`a.txt`, `b.txt`, `c.txt` in this batch's scratch.

### What the gate does and does not fail closed on

It fails closed on a measurement it cannot make — a missing
`tools/context_verify.py`, a non-zero exit, an exception — all deny, gate id
`context-digest` (now `WIRED` in `tools/gate_skip.py --gates`, 10 skippable).

**One exception, stated rather than hidden:** if the clone's session identity
cannot be established, nothing can tell *which* digest is ours, so there is no
check to fail closed on. That is reported the way check 16 reports an
unreadable claim state, and it has a known benign cause — a git worktree has
no identity marker. Everything past that point denies. A digest belonging to
another session in the same push is **named and not judged**: this clone cannot
measure a session it does not own.

---

## The defect in my own b20 work, found by using it

**`context_verify.py`'s window inference is a FLOOR, and b20 did not say so.**

Pointed at a fresh session for the first time, the tool reported cc at
**70.9% of 200,000** over 141,853 tokens. The session was in fact a 1M one at
**14.2%** — wrong by a factor of five, in the direction that reads as alarming
rather than as safe. The inference ("the smallest tabled window the measured
maximum fits in") is sound in one direction only: it is a floor on the window,
therefore a **ceiling** on the percentage, and it is tight only once the
session has passed the smaller window. b20's four figures were safe because
all four agents were already between 584k and 670k. **A batch's first digest is
exactly where they are not.**

Independently re-confirmed while finding it: my own transcript records
`claude-opus-5` on all 99 assistant turns while this session's model id is
`claude-opus-5[1m]`, and every occurrence of `claude-opus-5[1m]`,
`contextWindow`, `maxTokens`, `200000` and `1000000` in the file is my own
echoed command output. There is no window field. The system prompt is not in
the transcript either.

So the denominator now has a **declared** source and the inference is the
fallback:

```
python tools/context_verify.py --provision-window 1000000
```

writes `.git/sairn-context-window` — untracked, per-clone, surviving a rename,
the convention `sairn_session_identity.py` already uses and which this sits
beside.

**It is keyed by SESSION ID, not by clone, and that is not tidiness.** The
observed prompt witnesses a declaration that is too SMALL (and that case is
refused, naming the declaration as the wrong thing). Nothing witnesses one that
is too LARGE: `1000000` left standing in a clone whose next session runs on a
200k model would report 15% while that session sat at 75% — which is the
understatement b20 existed to stop. So a declaration speaks only for the
session that made it, and a new session declares again. One command per batch;
the correct trade.

With nothing declared and more than one published window still fitting, the row
is **AMBIGUOUS**: the token count is reported, both candidate percentages are
named, and `--digest-line` **refuses** to emit a confident line. A 5x-wrong
denominator wired into every digest is worse than a digest that says it does
not know.

Criteria lock: **56/56**, up from 23/23. The new arms include the real
2026-10-19 case (141,853 undeclared → AMBIGUOUS, not a confident 70.9%), the
too-small declaration, re-provisioning replacing rather than duplicating a
session's line, and a marker present-but-unreadable being a third state.

---

## Item 3 — is `wcag_contrast_check.py` really in the push gate?

**The one-line concept:** *prove the gate denies rather than reading that it
does — plant a NEW below-AA declaration in a real app file in an isolated
worktree, drive the pre-push hook, require the refusal, then remove the plant
and require the same push to pass.*

### VERIFIED — it is really wired, and it really denies

CHECK 5b exists at `tools/sairn_push_gate_hook.py` and `contrast` reads
`WIRED` in `gate_skip.py --gates`. Neither of those is proof, so it was driven:

- **Plant arm.** `.cc-b21-contrast-probe{color:#9ca3af;background:#ffffff}`
  added to `stonedesk-catalog.html` (a file with 0 findings, so the plant is
  unambiguously new), committed in a throwaway worktree, `--pre-push` driven:
  **exit 1**, and the refusal names the finding —
  `FAIL stonedesk-catalog.html .cc-b21-contrast-probe 2.54:1 (need 4.5)`,
  `NEW FINDINGS (not in the baseline): 1`.
- **Ablation arm.** Same rule, same file, same push shape, colour changed to
  `#374151` (AA-passing): **exit 0**, whole gate clean.

Evidence: `hook_plant.txt`, `hook_abl.txt`.

### ONE REAL GAP, measured, and it is not the wiring

**The baseline's universe is narrower than the gate's universe.**
`docs/wcag-contrast-baseline.json` is generated by `--static --all`, whose
`product_files()` excludes any root HTML whose stem contains a `-`. The gate
runs on **every** changed `.html`. So the five sub-apps are outside the
baseline while being inside the gate:

| file | new findings vs baseline | gate verdict today |
|---|---|---|
| `sairndental-book.html` | 6 | **deny** |
| `sairndental-complaint.html` | 2 | **deny** |
| `stonedesk-catalog.html` | 0 | pass |
| `stonedesk-hr.html` | 0 | pass |
| `stonedesk-intake.html` | 0 | pass |

Measured with `--gate <file> --baseline`, exit codes read directly rather than
through a pipe. The baseline currently holds **3** findings, all
`sairnroofing.html`.

**So any push touching `sairndental-book.html` or `sairndental-complaint.html`
is denied on 8 findings of PRE-EXISTING debt, with no route but a skip.** The
contrast fixes of b29-b31 took the platform from 153 to 3 across the 17 root
products and never looked at the sub-apps, because `--all` could not see them.

Two defensible fixes and this is not my file to choose in:
widen `product_files()` to include sub-apps and re-record the baseline, or fix
the 8 findings. **Routed to fourth, who owns
`tools/wcag_contrast_check.py` and `docs/wcag-contrast-baseline.json`** — both
are in fourth's b32 claim and neither was touched here.
