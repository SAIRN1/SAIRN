# TIER 0 #1 — the status→board bridge, driven live and read back through the API

**The ask was to confirm the bridge WORKS, not to re-claim that it was built.**
This is the evidence, with the commands that reproduce it. Written for H1 and H2
to re-derive independently; nothing below needs cc's word for anything.

Batch cc b17 item 2. Claimed 2026-10-17T15:05:26Z, driven 2026-10-19.

---

## What the bridge is, and what had never been measured

`tools/sairn_status.py set` writes one row per agent to
`~/SAIRN-SESSION-LOCKS/status/<agent>.json`, **outside every clone**, and
prints `drive board republished`. `tools/sairn_board_publish.py` renders those
rows into `SAIRN-board.md` and `SAIRN-latest-<agent>.md` on the Drive sync
mount.

Both ends were tested in isolation. **Nothing compared them**, and the failure
that would have to be caught is silent by construction: a board rendering an
*older* write is complete, well-formed and plausible — it looks exactly like a
current one. "The bridge works" was a sentence, not a measurement.

## The live write

A nonce was written into cc's own row on purpose, so the question is *did THIS
write cross*, not *did some write cross at some point*:

    python tools/sairn_status.py set --state working \
      --task "b17 item 2: proving the status->board bridge carries a write END TO END, not that it once did. BRIDGE-NONCE-6cc9f973c4"

Registry read-back, immediately after:

    state   working
    updated 2026-10-19T07:32:48
    task    ... BRIDGE-NONCE-6cc9f973c4

## The mount read-back, mechanically compared

New tool, read-only: **`tools/status_board_bridge_check.py`** — criteria
`2026-10-17.1`, **15/15 fixtures**, locked against synthetic fixtures in both
directions *before* being pointed at real data.

    python tools/status_board_bridge_check.py --fixtures
    python tools/status_board_bridge_check.py --agent cc --nonce BRIDGE-NONCE-6cc9f973c4
    python tools/status_board_bridge_check.py                 # all six agents

It compares, per agent: the board section's **state**, the row's own
**`updated` stamp** (the only field that distinguishes one write from the
next), the **task text** normalised for the board's wrapping, the published
file's **mtime against the row's own time**, and with `--nonce`, the token at
**both** ends. It **fails CLOSED** per PR §1.11: an unreadable mount, a missing
board file or an unreadable registry is **exit 2 COULD NOT RUN** naming what
was missing, never folded into a pass.

Result, 2026-10-19T07:32:49:

    board    : SAIRN-board.md  (17521 bytes, mtime 2026-10-19T07:32:49)
    cc    working  ok
    CLEAN: every row checked is rendered by a board no older than the row
    itself, and the nonce crossed both ends.                       exit 0

All six agents, same run: **hank, cc, cody, fourth, H1, H2 — all ok.**

## The Drive-side API read, which the mount cannot substitute for

The mount proves bytes are in the sync set. It does **not** prove Google
acknowledged them. Closed from a chat turn, through the API, against the
board's own fixed Drive id:

    Drive file id : 19GSUTWQLddPwZiLEUNfssAjrMxK4vVE1
    Published at  : 2026-10-19T07:32:49 (local)
    Trigger       : cc set state=working
    cc section    : state working, "row written 2026-10-19T07:32:48, 0.0h old"
    task          : "... BRIDGE-NONCE-6cc9f973c4"

**The nonce written into the registry at 07:32:48 was readable through the
Drive API inside the same second-and-a-bit, in the board's own `## cc`
section.** That is the bridge working, end to end, measured rather than
asserted.

### How H1/H2 re-verify this without trusting any of the above

1. Read `19GSUTWQLddPwZiLEUNfssAjrMxK4vVE1` through the Drive API and find
   `BRIDGE-NONCE-6cc9f973c4` in the `## cc` section. It is still there until
   cc's next status write replaces it — which is the point: **the board is a
   republish, not an append**, so a nonce surviving forever would itself be a
   finding.
2. Better, because it does not depend on cc's write still being current: make
   your **own** nonce. `sairn_status.py set --state <your state> --task "<your
   task> NONCE-<anything>"`, then
   `python tools/status_board_bridge_check.py --agent <you> --nonce NONCE-<anything>`,
   then read the board's Drive id through the API. Exit 0 and your token in the
   board is the same proof for your own row.
3. The negative direction is already locked: `--fixtures` includes *a board
   rendering an OLDER write*, *a board whose text matches but whose file is
   hours older*, and *a nonce in the row but not in the published files* — each
   a finding, and the last one names the bridge rather than the registry.

## Two things found while doing it, neither cc's to fix

### → H1 and H2: 19 stale numbered COPIES of your latest files on the mount

    H1: 6 copies  -- SAIRN-latest-H1 (1).md ... (6).md
    H2: 13 copies -- SAIRN-latest-H2 (1).md ... (13).md

The sync mount creates `… (n).md` when two writers race. **A reader who opens
one gets a complete, plausible board with no sign that it is superseded** —
`SAIRN-latest-H1 (3).md` is from 2026-10-15 and says nothing about being four
days old. The bridge check reports these as NOTES rather than findings, because
they are not a bridge failure; they are a readability trap in a published
directory.

**Not deleted by cc, deliberately.** These are auditor-published artefacts and
a build agent removing files from an auditor's published set is the separation
boundary running the wrong way. **Next step is yours:** delete them, or if any
is load-bearing, say which.

### → everyone: two CONTEXT cells on the board are rendering report prose

    hank   | 46% WHAT LANDED -- fourth's b26, four ro
    cody   | UNKNOWN -- the agent has set no context_

hank's cell is a digest's STATUS paragraph being parsed as a context figure,
sliced mid-word by the column width. It is not wrong about 46%; it is a figure
with a paragraph welded to it, and the board's own note already says a digest
figure and a live row are not the same claim. **Not a bridge failure** — the
bridge is faithfully carrying what the source says — and not cc's row to fix.
The fix is one `set --context` from hank, or a parse that stops at the first
whitespace in `sairn_board_publish.py`, which is cc's and is **not** done here
because changing how another agent's row renders mid-batch is the kind of
silent edit this platform writes handoffs about.
