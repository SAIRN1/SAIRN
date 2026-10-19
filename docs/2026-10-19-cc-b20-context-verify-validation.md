# b20 item 3 — validating context_verify against two known live data points

**The question is not "does it print a number".** It is whether the numbers are
real. Two live sessions were used — **hank's**, which is a window somebody else
is filling, and **cc's own**, whose true value is known from the inside.
`hover`/`hover2` are out of scope and were not read.

Measured 2026-10-19, `tools/context_verify.py` criteria `2026-10-19.1`,
23/23 fixtures passing.

    agent   REAL %      prompt      window   age h
    hank     67.1%     670,930   1,000,000    0.13
    cc       67.1%     671,427   1,000,000    0.0
    cody     63.4%     633,965   1,000,000    0.0
    fourth   58.8%     588,142   1,000,000    0.0

---

## Data point 1 — cc's own session, where the answer is known from the inside

`tools/sairn_status_line.used_tokens()` is **different code, written for a
different purpose** (the status line), reading the same transcript. It sums the
same three prompt fields from the last usage record.

    context_verify   prompt 671,427
    used_tokens      671,427        <- identical, to the token

Not independent *evidence* — same source — but it is an independent
**implementation**, and a disagreement would have meant one of them was
parsing the wrong record. They agree exactly.

**Re-read minutes later, all four agents, and the agreement holds while the
figures MOVE** — which is the strongest available evidence that nothing here is
a constant:

    agent   context_verify   used_tokens   agree   bytes/token
    hank           670,930       670,930    True          6.66
    cc             674,406       674,406    True          7.24
    cody           635,215       635,215    True          6.79
    fourth         592,390       592,390    True          7.85

cc moved 671,427 → 674,406 and cody 633,965 → 635,215 between two reads a few
minutes apart, because both sessions were working. **Every figure in this
document is true of the moment it was taken and of no other moment**, which is
the property a context reading has and a placeholder does not.

**And the figure moved while this batch ran**, which is the check that rules out
a placeholder: cc's b19 digest quoted **61.9% / 619,477** at wrap, measured the
same way. b20's work has since added about 52,000 tokens of prompt. A constant
would not have moved; a hardcoded one would not have matched b19's number
either.

## Data point 2 — hank's live window, and a disagreement worth having

    context_verify  hank  67.1%   670,930 tokens, transcript age 0.13h
    the board's self-reported cell for hank  46%  (source: digest b17)

**These are both right.** hank's self-report is a figure hank wrote into a
digest on 2026-10-16; the verified figure is hank's last assistant turn minutes
ago. The gap is three days of work, not a lie — which is exactly why item 4
puts the two side by side with the age of each rather than replacing one.

**It also shows something the self-report alone could not:** hank's status row
was last written 2026-10-17T10:20 — 46 hours old on the board — while hank's
transcript was appended 8 minutes before this measurement. **hank is working
and its status row is stale**, and only the verified column makes that visible.

## Plausibility, rather than "the tool said so"

**Bytes per token across four independent transcripts** — a ratio that would
scatter if the token figures were arbitrary:

    hank    4,461,062 bytes / 670,930 tokens = 6.65
    cc      4,762,021 bytes / 671,427 tokens = 7.09
    cody    4,150,196 bytes / 633,965 tokens = 6.55
    fourth  4,601,398 bytes / 588,142 tokens = 7.82

All four land between 6.5 and 7.9 bytes per token. Transcript bytes include
JSON envelopes, tool results and duplicated system prompt text, so a ratio
somewhat above the ~4 bytes/token of plain English is what a correct figure
looks like. **The four agree with each other without being equal**, which is
what rules out a constant: the percentages are 67.1 / 67.1 / 63.4 / 58.8 and
the prompts differ by 83,000 tokens across the set.

## What this validation does NOT establish, stated rather than discovered

- **It does not prove the window is 1,000,000.** It proves the window is not
  200,000 — a 670,930-token prompt could not have fitted. 1M is the next
  published size for this model family and is the smallest that fits. If a
  third size existed between them, the tool would pick that one instead.
- **It does not prove any session is *current*.** `age h` is the transcript's
  mtime, and four of these were seconds old only because four agents happen to
  be live. A stopped session reports its last turn, truthfully, forever.
- **It cannot see a compaction.** If a session compacts, the prompt drops and
  the figure drops with it — correctly, but a reader comparing two readings
  across a compaction is comparing different things.
- **Neither data point was independently re-derived by another agent.** cc
  wrote the tool and ran it. H1/H2 re-driving it is the thing that would make
  this independent, and it is not done here.
