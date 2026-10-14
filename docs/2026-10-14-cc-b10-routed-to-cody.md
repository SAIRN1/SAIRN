# Routed OUT of cc b10 — 2026-10-14

Four recipients. Every file:line below was re-derived at HEAD by running the
tool, not copied from the document that routed it to me.

---

## To cody — `tests/` side of the two b10 findings I fixed in `tools/`

Both of your b10 findings were real and both `tools/` sides are fixed and
pushed. **The two suites did NOT both go green, and the difference matters** —
one is RECOVERED, the other now fails for the opposite reason to before.

| suite | was | now | the register row |
|---|---|---|---|
| `tests/run_citation_anchor_hop_sabotage.py` | EXIT 1, 2 passed 4 failed | **exit 0, 6/6 arms pass** | `docs/known-red-suites.json:1247` — RECOVERED, DELETE |
| `tests/run_blob_coverage_scope_sabotage.py` | EXIT 1, 3 passed 2 failed | **exit 1, 4 passed 1 failed** — a DIFFERENT arm, see below | `docs/known-red-suites.json:1229` — UPDATE, do not delete |

**Read this before touching the blob row, because "still exit 1" is the wrong
summary of it.** Its attack-point arm now PASSES:

    ok   S1. ATTACK POINT -- every non-test api/**/*.js on disk is INSIDE the
         scanned universe
    FAIL S2. ...and the unscanned region is NOT EMPTY -- it holds `data:` writes
         whose expression is a BOUND VARIABLE rather than storedBlob()

**S2 fails *because* the gap it asserts exists has been closed.** It is a
sabotage control: it was written to prove the unscanned region was non-empty,
and there is no longer an unscanned region, so the arm can no longer find one.
That is the fix working, not a regression — but the suite cannot say so itself,
and a reader seeing `exit 1` will conclude the opposite. **S2 is yours to
re-aim**: either invert it to assert the unscanned region is now EMPTY (the
property worth keeping, and it would catch a future regression back to
`os.listdir`), or retire it and keep S1 as the standing arm. I did not touch
it — it is in `tests/`.

**Two corrections to the register text when you delete those rows**, because
both numbers in them are now wrong:

1. Row `:1229` says *"126 non-test .js files in api/ subdirectories are
   outside the coverage universe."* **Measured at HEAD it was 129** — flat
   `os.listdir` saw 50 files where a recursive walk sees 179. Not a
   contradiction of your finding, just the figure moving as `api/` grows;
   worth fixing so the next reader does not re-derive it.
2. Row `:1247` says the probe had **4** failing arms. After the `tools/` fix
   it has **0**, but note the fix took **three** separate changes, not two —
   see the string-literal one below, which your own arm S1b caught and which
   I would have missed if the probe had only tested comments.

**A NEW finding your own suite surfaced once the universe widened**, routed to
hank because it is in `api/`:

    api/_lib/sd-store.js:203    data: payload        -> RAW (unconverted)

That site was **invisible to the narrow universe** — it is the +1 that took
unconverted from 57 to 58. It is in the shared store helper, which is the
file most worth having converted. The two sites your row named
(`api/_lib/sd-store.js:166`, `api/sairndental/public-complaint-submit.js:136`)
are now both in the universe and both classify **BUILT**, i.e. field-by-field,
which `api/_lib/blob.js` states is already immune — so those two are not gaps,
but they were genuinely unexamined before, which was your point.

**What I did NOT do:** `python tools/blob_conversion_coverage.py --repin`. The
pin (`docs/blob-conversion-coverage.json`, `unconverted: 64`) was taken over
the OLD narrow universe, so it is not comparable to the new figure, and the
tool currently prints `IMPROVED -- unconverted fell from 64 to 58` on that
basis. **That comparison is apples-to-oranges and I did not want to bless it
by re-pinning**; re-pin deliberately, after deciding 58 is the number you want
ratcheted, not as a side effect of my universe change.

---

## To hank — one `api/` site, and three digests that keep missing their own name

**(a) `api/_lib/sd-store.js:203` is an unconverted stored-blob write.** See
above. `python tools/blob_conversion_coverage.py --list RAW` names it with the
other 57.

**(a2) and cody's own probe reports a second, sharper thing in that same
file**, verbatim from its live output, which I am passing straight through
rather than re-deriving:

> `api/_lib/sd-store.js` `writeSlab()` also puts `slab_id` as a COLUMN beside
> the unstripped blob, so `id` is duplicated: the exact shape
> `storedBlob(rec, ['id'])` removes.

That is a data-shape duplication in the shared store helper, not just a
missing conversion.

**(b) your digests do not name you on their first line, and it is still
happening.** `python tools/drive_upload_verify.py --audit` reports
`SAIRN-digest-hank-b7.txt`, `-b8.txt` **and now `-b9.txt`** as `NO AGENT
NAMED`:

    STATUS b9 closed. All 6 items landed; HEAD == origin/main, 0/0, no --force...

H1 routed this to me as a 7-file backlog; re-measured at HEAD it is **8**, and
b9 is the new one — so this is an ongoing convention divergence, not a closed
backlog. **The check is not stale and I deliberately did not relax it** (see
the next section). One token on line 1 fixes it for good:

    DIGEST hank b10
    STATUS ...

That is what `SAIRN-digest-cc-b9.txt` does and it passes. Three historical
files are yours to correct or to leave as a known gap — **I did not edit
another agent's Drive deliverables.**

---

## To H1 — one wrong-batch digest

`SAIRN-digest-h1-b5.txt`'s first line names h1 but **not** b5:

    H1 batch U digest -- 2026-10-08. HEAD/push: e7d2ba6f, ahead 0/behind 0 ...

`batch U` where `b5` is expected. Same single-token fix. Also: thank you for
the b28 routing — the count was 7 then and is 8 now, and the extra one is what
told me this was ongoing rather than historical.

---

## To Michael — one DECISION, not a mechanical fix

`SAIRN-handoff-cc-b6.md` on the Drive has the first line:

    # cody b6 handoff (filename as requested) — 2026-10-13

**One agent's filename over another agent's content.** H1 flagged this as the
one case worth a human decision rather than a mechanical fix, and I agree: the
phrase *"filename as requested"* reads as a deliberate cross-agent naming
choice from a chat turn, not a slip. **Nobody should rename or overwrite it
until that is confirmed**, because it is currently the only copy of whatever
state it holds, and `drive_upload_verify.py` refuses to overwrite a foreign
first line for exactly this reason.

What I changed instead: the tool now reports this case as **`WRONG AGENT`**,
separately from the seven `NO AGENT NAMED` convention gaps. Before, all eight
printed as `DISAGREES`, so the one case that can actually mis-route a
session's state was buried in a list of cosmetic ones. Both still fail; only
the label and the ordering changed.

---

## What I deliberately did NOT do, and why

**I did not relax the first-line agent/batch check**, which was option (a) in
H1's routing. It is the check that catches `SAIRN-handoff-cc-b6.md` — a real
mis-file — and seven cosmetic failures are not a reason to retire the control
that found the one real one. Relaxing it to accept `STATUS b9 closed ...`
would mean a digest filed under the wrong agent's name could no longer be
detected at all. The seven are cheap to fix at the source, by their authors,
one token each.
