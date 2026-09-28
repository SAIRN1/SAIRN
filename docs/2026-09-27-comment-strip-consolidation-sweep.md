# The comment-strip consolidation sweep — 2026-09-27

**What this is:** the migration of every ad-hoc comment stripper in the test
suite onto `tests/lib/strip_comments.js`, the library built earlier the same week
after the third and fourth instance of the same bug. It closes 24 call sites
across 20 files, gives the library its first control, and **found a real failing
defect in the library itself** — which is the part worth reading.

**Do not quote any count from this document without re-running the command
beside it.** Every figure here is a measurement with a date on it.

---

## 1. Why a shared library needed a sweep at all

`tests/lib/strip_comments.js` exists because three suites each grew their own
comment stripper in one day and all three were wrong in **different** ways. Its
header records them:

1. **A line filter** — drop lines starting `//` or `<!--`. Kept every
   *continuation* line of a multi-line block comment, which is exactly where a
   removed string is quoted.
2. **A greedy regex** — `/\/\*[\s\S]*?\*\//`. Matched across an unintended span
   and ate a real statement, taking a count from two to **zero**.
3. **A naive state machine** — treated `/*` as a block start *anywhere*, so
   `accept="image/*"` opened a comment that swallowed thousands of lines.

The library was correct and **nothing was migrated onto it.** Five suites used
it; the rest kept their copies. So the platform had *four* implementations of one
rule, and the shared one was not the most-used.

---

## 2. What the sweep did

**24 call sites, 20 files.** Migrated with a script that **refuses** a file when
its anchor text is absent or not unique, so a partial migration cannot pass
silently. That refusal fired immediately and usefully: the first run matched
**zero of nine** patterns because a shell heredoc had eaten the backslash
escapes, and it said so rather than reporting nine successes.

| Kind | Sites | Entry point used |
|---|---|---|
| Whole HTML file | 7 | `stripComments(html)` |
| Bare JS file or fragment | 17 | `stripJs(src)` |

### `stripJs()` is new, and the sweep could not have been done safely without it

**Most call sites do not pass a whole file.** They locate a function in the HTML
by index, slice it, and strip the slice. Handing that slice to `stripComments()`
means script context is **false** for the whole fragment — so `//` and `/* */`
are not comments, **nothing is stripped, and the call returns its input
unchanged.**

That is a worse failure than any of the three copies it replaced, because it
*looks like the fix*: a call to the shared library sitting in the right place,
doing nothing. So the fragment case got its own named entry point rather than an
options flag somebody has to remember, and arm B1 of the new control asserts that
`stripComments()` on a fragment still strips nothing — because that is correct
for the whole-file path and is the trap that must stay visible.

---

## 3. THE FINDING: the shared library hid real code

**`var re = /\/\//;` was read as a line comment**, so everything after it on that
line vanished from the stripped output.

That is the **failing direction**. A suite asserting a string is ABSENT would pass
on code that is PRESENT. Five suites already depended on the library when this was
found.

### How it was found: by borrowing a reviewer's attack, not by reading the code

`tests/sairnvet_scribe_review_probe.js` section A2 exists to *attack* a comment
stripper. It extracts `api/sairnvet-transcribe.test.js`'s character scanner and
asks, for each of five shapes, whether real code can be hidden behind it. Its own
history is the argument for reusing it: **the arm originally attacked a
regex-based stripper, two of the five attacks defeated it, and that suite was
rewritten with a character scanner in response.**

Those five attacks are now arms A1–A6 of `tests/lib/strip_comments.test.js`. The
regex one went red on the first run. **The library had never faced them.**

### The fix

Regex-literal handling, using the heuristic the platform already had right in
`api/sairnvet-transcribe.test.js`: a `/` starts a regex only when the previous
significant character cannot end an expression. After an identifier, a number,
`)` or `]`, a `/` is division.

It is a heuristic and not a grammar, **and the direction of its error is chosen**:
anything it does not recognise stays division, so it can only ever *under*-strip.
Under-stripping leaves a comment in and shows up as a red arm. Over-stripping
hides code and shows up as green.

`//` and `/*` are still checked **before** the regex branch, so an empty regex
`//` still reads as a comment — which is what JavaScript itself does.

---

## 4. The library's first control

`tests/lib/strip_comments.test.js`, **27 arms**. Run it:

    node tests/lib/strip_comments.test.js

The library had **no test of its own** while five suites depended on it — a shared
helper with no control is not a fix, it is the same bug with a smaller blast
radius on the day it lands and a larger one every day after.

Structure, and why each section exists:

- **H / J / S** — one pair per historical bug: the input that broke the old
  version, and an input the old version handled that must keep working. A fixture
  set that only proves the bug is gone cannot tell a fix from an over-correction,
  and two of the three original bugs *were* over-corrections.
- **B** — the bare-fragment trap in both directions.
- **A** — the five borrowed attacks, plus A6 running all five through the
  whole-file path, because a fragment and a `<script>` block must not answer
  differently.
- **X** — the documented limits, asserted as limits, each with a message saying
  what to rewrite if the limit is ever closed.

**Two fixtures were corrected during authoring and both corrections are recorded
in the file**, per discipline 1. Both were the safe kind — the *expected verdict*
was wrong, not the library — and one of them found that **the library is better
than its own header claimed**: a `</script>` inside a string does *not* end script
context, because the boundary check is guarded on quote state. That is now pinned
as a strength (X3) and the real limit is pinned separately (X4).

---

## 5. Verification: a differential, not a green run

A green suite after a migration proves nothing unless you know what it said
before. **Exit code and arm counts were recorded for all 25 candidate suites
before any edit, and compared after:**

    25 suite(s) IDENTICAL, 0 MOVED

The one non-zero exit, `tests/faults/transport_timeout_sweep.js` (79 passed, 2
failed), **was already red on `main` before this sweep** and is untouched by it.

Six further suites were migrated in a later batch and checked the same way,
including `api/_resources/extra-actions.test.js`, which was **already at 41
passed / 7 failed** beforehand and still is.

---

## 6. What was NOT migrated, and why — each one named

A sweep that does not say what it skipped reads as complete when it is not.

### Deliberately left: two real character scanners that a reviewer reads by name

- `api/sairnvet-transcribe.test.js` — `function stripComments(src)`
- `tests/faults/transport_timeout_sweep.js` — `function stripComments(src)`

Both are full character scanners, **not one of the three broken shapes**, and
`tests/sairnvet_scribe_review_probe.js` extracts the first **by that exact name**
and evaluates it with `new Function`. Replacing the body with a call to the
library would leave `stripJs` out of scope and the reviewer's arm would throw —
so migrating either silently breaks a probe whose whole job is to attack a
stripper. The attacks that justify them are now in the library's own control, so
the evidence is not lost.

### Deliberately left: three sites that are not strippers at all

- `tests/stonedesk_shop_identity.js:44` — *classifies* a line as `'comment'`.
- `tests/stonedesk_hook_dormancy_disclosure.js:64` — same shape.
- `tests/sairnlegacy_write_failure_voice.js:181` — asserts a line **starts with**
  `//`. The comment is the subject, not the noise.

### Left as a named remainder: seven PER-LINE PREDICATES

These filter lines matching a pattern **and** not starting with `//`, in one
expression. Converting them means stripping first and then filtering, which
changes the arm's shape rather than swapping a helper, and each needs its own
read:

    tests/ai_shortcuts_reach_the_chat.js:73, :138
    tests/invoice_panel_kpis.js:263
    tests/pricing_single_source.js:135
    tests/sairnscape_memory.js:271
    tests/stonedesk_field_quote_wiring.js:335

They are the **weakest** version of the pattern — a trailing `//` comment on a
matching line slips through — so this remainder is real exposure, not tidiness.

### Excluded on ownership, not on merit

- `api/_lib/deadline-weekend-days.test.js:230` — `api/_lib/deadline-engine.js`
  and its suite are under an **active hank claim** as of this sweep. Flagged
  rather than edited (PR 4.3).

---

## 7. The methodological finding: the first search vocabulary was incomplete

The sweep's first pass searched for `startsWith('//')` and
`replace(/<!--`. **It missed every site written as
`l.trim().indexOf('//') !== 0`** — the same rule, a different spelling. Seven
more sites appeared only when the pattern was widened, including a **second**
site in a file the sweep had already "finished".

This is the shape `subprocess_decode_check.py` recorded on 2026-09-15: its
completeness claim was *a count of what the detector could see*, and widening the
detector moved the count. A sweep's denominator is its search vocabulary, and a
vocabulary assembled by recalling the idioms you have seen is not a denominator.

**So the count in section 2 is a floor.** Re-derive it rather than quoting it:

    grep -rnE "startsWith\('//'\)|indexOf\('//'\) !== 0|replace\(/<!--" tests/ api/

---

## 8. Files changed

**Library and its control**

    tests/lib/strip_comments.js          stripJs(), regex-literal handling
    tests/lib/strip_comments.test.js     NEW -- 27 arms

**Migrated — whole HTML file**

    tests/ai_auth_wrapper.test.js
    tests/aiq_speed_and_waste_calc.js
    tests/sairndental_write_failure_voice.js
    tests/sairnlaw_csp.js
    tests/sairnsenior_org_hydrate.js
    tests/sv_audit_completeness.js
    api/sd-data-sairnlaw-resources.test.js

**Migrated — bare JS or a fragment**

    tests/idless_rows_are_reported.js
    tests/pricing_single_source.js                (2 sites)
    tests/refusal_not_empty.js
    tests/sairndental_outbound_queue.js
    tests/sairndental_settings_patch.js
    tests/sairnlaw_hydrate.js
    tests/server_wins_hydration.js
    tests/stonedesk_drawing_snapshot_budget.js
    tests/stonedesk_followup_chip.js
    tests/stonedesk_po_sequence_and_join.js
    tests/stonedesk_quote_load_state.js           (2 sites)
    tests/stonedesk_saved_drawings.js
    api/_lib/anon-rate-limit.test.js
    api/_lib/money.test.js
    api/_lib/record-parity.test.js
    api/_lib/roofing-gl-export.test.js            (2 sites)
    api/_lib/roofing-supplier-match.test.js
    api/_lib/stripe-api-version.test.js
    api/_resources/extra-actions.test.js          (2 sites)
    api/sd-data-dental-ledger-validation.test.js  (2 sites)

**One migration needed a hand fix worth recording:** the import script anchored
on `const assert = require('assert');`, and in
`api/sd-data-dental-ledger-validation.test.js` that string appears **inside a
nested block** as well as at the top. The import landed in the nested scope, so
`stripJs` was undefined at the call site 600 lines later and one arm failed with
`stripJs is not defined` — loudly, which is the only reason it took a minute
instead of a session. An anchor that is not unique is not an anchor.
