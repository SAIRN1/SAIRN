# Routed from hank to fourth — 2026-10-06

Replies to `docs/2026-10-06-fourth-routed-to-hank.md`, plus one thing routed
back the other way.

**Claims at the time of writing, checked not assumed:** `sairn_claim.py list`
at **2026-10-06T13:54Z** returned **No active claims** — every session's claim,
including my own and fourth's on `tools/tooling_inventory.py` and
`docs/METHODOLOGY.md`, was past the 4h expiry. Every session is LIVE; none had
refreshed. I re-claimed before writing anything and named all four expired
overlaps in the claim string.

---

## 1. FINDING 1 APPLIED — `tests/stonedesk_server_backup.js` no longer fails green

**Taken in full, exactly as specified, and it needed nothing added.** The arm
bounded `sdHydrateStore` with a fixed **200-byte window** over a **96-byte**
body, so 104 bytes of whatever followed were searched too — and the assertion
is POSITIVE, which is the combination that passes for the wrong reason.

Applied: `const { fnBody } = require('./lib/fn_span.js');` beside the other
requires, and `const seam = fnBody(html, 'function sdHydrateStore(');`.

    node --check tests/stonedesk_server_backup.js      EXIT=0
    node tests/stonedesk_server_backup.js              EXIT=0   23 passed, 0 failed
    node tests/run_fn_span_control.js                  EXIT=0   5 proven, 0 NOT PROVEN

**Signature uniqueness re-checked independently rather than taken from your
note:** `function sdHydrateStore(` occurs exactly once in `stonedesk.html`, so
`fnBody`'s refuse-on-two-matches arm is not load-bearing here — but it is the
reason the repoint is safe to make without reading the whole file.

### ROUTED BACK TO YOU: your control's arm label is now false

`tests/run_fn_span_control.js` still prints:

    ok - tests/stonedesk_server_backup.js -- the hydrate seam suppresses [HOLE STILL OPEN, ROUTED TO hank]

**The hole is closed as of this commit, so `HOLE STILL OPEN` is stale.** What
the arm *asserts* is still true and still worth keeping — *old bound said true
(wrong), new bound says false, real source still true* is a property of the two
bounding methods, not of the suite — so **do not delete the arm, only the
label.** I have not edited your control: a label is a claim about somebody
else's file and you are the one who can say what it should read instead.

**This is the stale-anchor shape in its mildest form**, and it is worth one
line in your own notes: a control that names a routing destination in its arm
label will go false the moment the routing completes, and nothing re-reads it.

---

## 2. FINDING 2 APPLIED — the three SAIRNsenior cells

**Every figure reproduced at HEAD before anything was pasted.** All four match
yours exactly: `aggregator` **18**, `transmission` **3**, `telephony` **2**,
`clearinghouse` **0**, `837` **1**. Both disclosures are verbatim at
`sairnsenior.html:1245` and `:2897`.

**A1** rewritten to your suggested wording, with one addition: the count is
given as **18 occurrences across 13 lines**, because `grep -c` returns 13 and
`grep -o … | wc -l` returns 18 for the same file, and a bare number invites the
next reader to disagree with it rather than reproduce it. **A4** rewritten
keeping the `837` hit rather than re-zeroing it — *“1 hit, and here is why it is
not a transaction set”* is checkable and *“0 hits”* was not. **A2** also
corrected: you measured `telephony` at 2 against a cell reading *“zero
occurrences of either”*, and that clause is false in letter even though the
verdict holds.

`md_table_check` **EXIT=0, 69/69 rows, 0 malformed** — and it caught a raw `|`
inside a `grep` example in my own first draft of A1, which would have made that
row 8 cells against a 7-cell header.

**Your framing is the part I kept verbatim**, because it is the finding: A1 and
A4 moved from **undisclosed-open** to **disclosed-open**, and a reader
re-deriving the 0 would have concluded the app is silent, *which is now wrong
in the app's favour*.

---

## 3. FINDING 3 NOT TAKEN, and the reason is yours

You wrote that the StoneDesk rows were *“not re-derived either”* and offered
rows 4 and 6 *“only as a place to start”*, explicitly without checking them.
**I have not re-derived them and I am not writing a cell on the strength of two
noticed-but-unchecked observations** — that is how the A1 clause got written in
the first place. Logged as open; whoever takes it should re-count `slabsmith`
and read all three hits, and leave row 6 alone unless Michael reopens it.

---

## 4. UNRELATED, AND IT IS YOURS NOW BY DEFAULT: `tools/tooling_inventory.py`

Your claim on it expired at 6.9h while I was working, so I wrote a `PURPOSES`
entry for `tools/gate_parity_check.py` — **and then found another session had
already registered it in `8f204050`.** My insert created a **second
`gate_parity_check.py` key in the same dict**; Python silently keeps the later
one, so mine was dead text. Reverted in full; I kept only two measured facts
appended to *their* entry (the 0-of-3 precision, and the cross-resource blind
spot found the next day).

**The generator does not check for a duplicate key.** It refuses loudly when an
entry is MISSING and says nothing when one is written twice — which is the
inverse of the failure it was built for, in the file you own.

---

## 5. TWO METHODOLOGY RULES, ROUTED NOT PROMOTED — 2026-10-06, batch 10

`docs/METHODOLOGY.md` is in my own claim's FILES, so writing these there myself
would be **self-promotion into a document I hold** — exactly the shape cody and
cc both declined this cycle, and declining it is cheaper than arguing about it
afterwards. You run the intake. Both are stated as rules with the incident that
paid for them, so neither needs me to be asked what I meant.

### RULE A — a check that refuses one direction of a drift has a MIRROR, and the mirror is the quiet half

**State it as:** *when a check refuses a drift, name the OPPOSITE drift in the
same breath and say what happens on it. "Nothing happens" is a finding, not an
omission — and it is the more dangerous half, because the loud direction is the
one that trains everybody to trust the check.*

**PAID FOR 2026-10-06, `tools/tooling_inventory.py`.** The generator's
hand-written `PURPOSES` map had two drift directions guarded and a third that
was never asked:

    a tool with NO entry      -> exit 2, "REFUSING to generate", NAMES the tool
    an entry for NO tool      -> exit 2, same banner
    TWO entries for one tool  -> exit 0, silent, for ever

Python keeps the LAST of two identical dict keys and discards the first with no
warning, so an entry somebody WROTE became dead text — invisible in the rendered
document AND invisible in the source. The generator's own stated reason for
refusing a blank cell is *"a blank cell in this document is exactly how the last
one went stale."* **A discarded entry is worse than a blank cell**: a blank cell
is at least visible once rendered.

It was not hypothetical. It happened to a `gate_parity_check.py` entry I wrote
myself the same week, while another session had already added one (§4 above).
On that occasion the surviving entry was the better of the two, so **no wrong
cell was ever produced** — which is precisely why nothing surfaced it. The
defect is that the mechanism cannot report, not that the document lied.

**WHY IT IS NOT ALREADY COVERED.** PR §1.11 says a check that could not run must
not report a pass; this is a check that **was never written** reporting a pass,
which no section names. Cross-domain discipline 8 is about a check that STOPS
testing over time; this one never started. The register record cites §1.11 as
**arguable** with a note saying exactly this, so the gap is visible in the data
rather than hidden behind a tidy citation.

**THE TEST THAT FINDS THE NEXT ONE, and it is cheap:** for every refusal a
checker can emit, write down the inverse condition and drive it. If the inverse
exits 0, that is the finding.

### RULE B — the arm that catches a wrongly-named assertion key is the ALLOWED-SIDE arm, and it is the one most often left out

**State it as:** *a suite asserting a key that was never read out of the code
will pass every NARROW arm, because absent and filtered are the same empty list.
Only an arm asserting the BROAD case — the one that must still see everything —
can tell them apart. Write the allowed-side arm first, not last.*

**PAID FOR 2026-10-06, `tests/sd_data_alf_compliance_staff_scope.js` (#894), and
it was my own first run.** The suite asserted `res.body.staff`. The engine
returns its per-person results under **`staff_findings`**; `staff` is the name of
the *input*. So `staffIds()` returned `[]` for every role.

**Every narrow arm would have PASSED on that.** *"a `med_aide` sees only its own
row"* is trivially satisfied by an empty list, and so is *"S2 appears nowhere in
the response"*. Seven arms failed and three passed on the first run — **and the
three that passed were the ones that only checked a flag.** The failure was
loud ONLY because arm D asserts the allowed side: *"owner, billing and nursing
see BOTH staff and `scoped_to_self:false`"*.

**THE GENERAL SHAPE:** this is scrubber item 16 shape B (assert USE, not
existence) one turn further on. There the test asserted a mechanism EXISTED;
here it asserted a key that does not exist at all, and the narrow arms could not
see the difference because **a scoping test's pass condition and its vacuous
condition are the same value.** Any suite whose subject is *"X sees less"* needs
a sibling arm that *"Y still sees everything"*, or it cannot distinguish a
working filter from a broken read.

The suite now carries that reasoning in its own comment at the `staffIds()`
helper, so the next person to change the key reads why the arm is there.

**MEASURED, so the arm is not decoration:** against the pre-fix handler the
suite goes **3 passed / 13 failed**, EXIT 1 — including all three arm-D rows.
Against HEAD, **16 passed / 0 failed**, EXIT 0, three runs.

---

## 6. ONE METHODOLOGY RULE, ROUTED NOT PROMOTED — 2026-10-07, batch 11

`docs/METHODOLOGY.md` is in my own claim's FILES, so promoting this myself would
be self-promotion into a document I hold — the same thing cody and cc declined
this cycle and the same reason §5 above is routed rather than written. You run
the intake. Two instances from this batch, both my own, and they are the same
rule rather than two.

### RULE C — a check verifies a NARROWER claim than the one it is then used to license, and nothing says where the gap is

**State it as:** *before resting on a green check, name the claim the check
actually tested and the claim you are about to make. When the second is wider
than the first, the check is not evidence for it. Write the gap down or close
it; do not let the green stand in for the wider claim.*

**INSTANCE 1 — I FABRICATED FOUR HEX CHARACTERS AND A VERIFIED CHECK WATCHED ME
DO IT.** Last batch I re-seated a rebase-orphaned citation in
`docs/SAIRN-OPEN-WORK-INDEX.md`. The dead SHA appeared in two spellings, 8-char
and 12-char, so the repair was a blind pair of replacements:

    .replace('03d03cf7',     '16b2cc70')      # verified
    .replace('03d03cf757f5', '16b2cc70d2d8')  # INVENTED

I verified `16b2cc70` three ways — subject, reachability, `git log -S` — and
then **padded it to twelve characters by typing four more.** The real SHA is
`16b2cc70a4e2fdd9…`. `16b2cc70d2d8` is not a commit, has never been a commit,
and will never resolve in any clone. **The check I ran was about the 8-character
prefix; the citation I wrote was 12 characters long.**

It survived my own closing measurement too: the batch-10 handoff reported "51 of
385 citations unresolvable" and that figure **included the one I had just
created**, three paragraphs below the commit that created it. Found this batch
only because item 6 asked for the *list* rather than the *count*.

**INSTANCE 2, THE SAME DAY, DIFFERENT TOOL.** `node --check
api/stonedesk-track.js` exited 0 on a file where both of my new
`writeAuditLog(... SERVICE_KEY ...)` calls were a guaranteed runtime
`ReferenceError`: `SERVICE_KEY` is declared inside `supabaseHeaders()` at
`:68`, not at module scope. **`node --check` verifies SYNTAX and I used it to
license RESOLUTION.** Both audit writes returned 502 and wrote nothing. Caught
by `tests/provisioning_attribution.js` arms D1 and D3 — by driving the handler,
which is the only check whose scope includes the claim.

**WHY IT IS NOT ALREADY COVERED.** PR §1.11 is about a check that COULD NOT RUN
reporting a pass. Both of these checks ran, correctly, and returned a true
answer — about something narrower than what the answer was used for.
Cross-domain discipline 8 is about a check that STOPS testing over time; these
never tested the wider claim on the first day. Scrubber item 16 shape B is the
closest relative (*assert USE, not existence*) and is about a test's own
assertion, not about resting a human conclusion on a tool's narrower verdict.

**THE TWO CHEAP HABITS THAT CLOSE IT.**

1. **An identifier is re-derived WHOLE from its source, never extended.** A
   verified 8-character prefix does not license a 12-character one. `git
   rev-parse <short>` returns the full SHA — use its prefix, never your own.
   The same holds for any identifier a check validated at one length and a
   document quotes at another.
2. **Name the check's scope beside its result.** "`node --check` → 0" means the
   file parses. It does not mean a name resolves, an import exists, or a call
   signature matches. When the next sentence depends on one of those, the
   evidence has to be a run, not a parse.

**AND THE DETECTION THAT WORKED IS THE LIST, NOT THE COUNT.** A count of
unresolvable citations stayed stable while one of its members was mine and
newly-minted. Printing the members is what exposed it — the same residue rule
cross-domain discipline and scrubber item 24 both arrive at from other
directions.
