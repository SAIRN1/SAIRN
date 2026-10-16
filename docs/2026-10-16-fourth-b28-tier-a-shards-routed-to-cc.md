# Routed to cc — the Tier A ledger is now append-only per-agent, and the gate needs TWO FUNCTION BODIES changed

**Written 2026-10-16 by fourth, batch b28. Michael's decision, not mine to
make — I was dispatched to implement it.**

`tools/tier_a_reviews_store.py` is **landed, migrated and tested** (22 fixtures,
both directions, `--selftest` exit 0). `docs/tier-a-reviews/<session>.jsonl`
carries all **265** records. **The push gate does not read it yet**, and until
the change below lands, a discharge that exists only in a shard **is not seen
by the gate** — the store prints that sentence itself on every `--read` rather
than leaving it to be remembered.

`tools/tier_a_review_gate.py` is yours by the directory rule **and it was held
by your LIVE claim (`2026-10-16T11:34:50Z`, `CLAUDE_PID 23052`) for the whole
of this batch**, so it is routed rather than edited. I did not touch it.

---

## Why the problem is a claim-lock on a path, not a merge problem

**This matters because it rules out the obvious fix.** The ledger already
declares itself *"append-only across four clones"* in its own `merge_policy`,
and `tools/sairn_rebase_resolve.py` already 3-way merges it by identity. So git
was never the contention.

`tools/sairn_claim.py` decides on the **DECLARED FILE SET**. Two sessions naming
the same path block each other whatever the merge semantics are. **A single
shared append-only JSONL is still ONE PATH and would not have fixed anything.**
Only per-agent shards put two agents' writes on disjoint paths.

Measured, twice, on the same Tier A record (`cody 2026-10-15T15:12:47Z`,
`bld_bids`):

| batch | holder of `docs/tier-a-reviews.json` | outcome |
|---|---|---|
| b27 | **cc**, `2026-10-15T16:55:20Z` | discharge blocked, not started |
| b27 resume | **hank**, `2026-10-16T11:17:27Z` | discharge blocked, not started |
| b28 | **hank**, still held, `CLAUDE_PID 26072` confirmed running | **still blocked** |

Both holders were legitimate and were working on unrelated rows.

## The design, and the one part that needs testing rather than asserting

Identity is `(author_session, opened_at)` — **taken verbatim from the legacy
file's own `merge_policy.identity`, not invented.** `--validate` reports
`IDENTITY DRIFT` if those two ever disagree, because a discharge keyed on the
wrong fields would silently open a *second* obligation instead of closing one.

The reader unions layers and, for one identity, **the last layer wins
FIELD-BY-FIELD, not whole-record**:

1. `docs/tier-a-reviews.json` → `records` — the legacy base layer
2. `docs/tier-a-reviews/*.jsonl` — shards, in filename then line order

So **discharging an obligation that was OPENED in the legacy file is one
appended line** carrying the same identity plus `status`, `reviewer_session`
and `verdict` — and the legacy file is never touched. That is the property that
unblocks a discharge while another session holds the old file, and it is
fixture 3–4 in `--selftest`:

```
ok   a reviewer may append a discharge for ANOTHER session's obligation
ok   the discharge SUPERSEDES the legacy record, still ONE row
ok   the appended line did NOT erase fields it did not name
ok   THE LEGACY FILE WAS NOT TOUCHED
```

**Field-level and not whole-record is deliberate.** A discharge line names the
verdict and the reviewer; it does not restate the `resources`, `files` and
`rules` the opening record holds. A whole-record replace would erase those by
omission — so that is a fixture, in the direction that would have been wrong.

**The shard filename says who WROTE the line; `author_session` inside the
record says whose obligation it is.** Those are deliberately separate, because
a discharge is written by the reviewer and conflating them would make a
discharge impossible. `--read` reports provenance per record.

## Migration: already applied, and proved lossless

```
python tools/tier_a_reviews_store.py --migrate --apply
  legacy file read: 265 record(s)
  authors: cc=66, cody=71, fourth=48, hank=76, hover2=4
  APPLIED: 265 record(s) written into shards; 0 already there.
```

**Round trip proved lossless**, not assumed: 0 identities only in legacy, 0
only in the union, **0 records differing after the round trip**, 265 → 265.
`--migrate --apply` is **idempotent** (fixture) and **leaves the legacy file
byte-identical** (fixture). A record whose `author_session` is not a known
session is **named and not migrated** rather than filed under somebody else —
there were **zero** of those, but the refusal is tested.

**`docs/tier-a-reviews.json` is NOT deleted, emptied or rewritten.** It is the
base layer and stays exactly as it is, so every existing reader keeps working
unchanged while writers move over one at a time. It was also held by a live
session — a tool whose first act is to rewrite a file another agent is editing
would be the defect it was built to prevent, committed by the fix for it.

---

## What you need to change: TWO FUNCTION BODIES, not 18 call sites

This is the good news. `tier_a_review_gate.py` already funnels everything
through two chokepoints — **11 call sites of `load_reviews()` and 7 of
`save_reviews()`**, and none of them touch `REVIEWS` directly. So the whole
migration is those two bodies.

### 1. `load_reviews()` at `tools/tier_a_review_gate.py:519`

```python
def load_reviews():
    # ── READS THE UNION, NOT THE LEGACY FILE ALONE (2026-10-16) ───────────
    # The base layer is still docs/tier-a-reviews.json; the shards layer on
    # top, last-wins field-by-field. See tools/tier_a_reviews_store.py for
    # why per-agent shards and not one JSONL.
    import tier_a_reviews_store as _store          # same dir as this file
    r = _store.read_all()
    if r['degraded']:
        # SAME FAIL-CLOSED CONTRACT AS BEFORE. A layer that could not be read
        # is not an empty layer, and CouldNotTell is the state this gate
        # already has for exactly that.
        raise CouldNotTell(
            'the Tier A ledger could not be fully read, so this gate has '
            'checked NOTHING: ' + '; '.join(r['problems']))
    _LAST_LOADED[0] = {_store._ident(x): json.dumps(x, sort_keys=True)
                       for x in r['records']}
    return {'records': r['records']}
```

Add near `REVIEWS` at the top:

```python
# The snapshot load_reviews() last returned, so save_reviews() can append the
# DELTA instead of rewriting 2.1MB. A list of one, not a bare global, so the
# assignment inside load_reviews() needs no `global`.
_LAST_LOADED = [None]
```

`load_reviews()` returns a dict with `records` today and every caller uses
`data['records']`, so returning `{'records': ...}` is the same contract. **The
`_what_this_is` / `merge_policy` keys are NOT returned** — grep first: if any
caller reads one, pass the legacy doc through instead of a fresh dict. I did not
edit your file, so I did not run that grep against your working copy.

### 2. `save_reviews(data)` at `tools/tier_a_review_gate.py:531`

```python
def save_reviews(data, writer=None):
    # ── APPENDS THE DELTA TO ONE SHARD. DOES NOT REWRITE THE LEDGER ───────
    # The atomic temp-file-then-os.replace dance below is kept for the legacy
    # file and is no longer reached in the normal path: an append to one
    # session's own shard cannot race another session, because no other
    # session ever opens that path. The Windows ERROR_ACCESS_DENIED retry
    # loop that comment describes was a symptom of the shared file.
    import tier_a_reviews_store as _store
    me = writer or os.environ.get('SAIRN_SESSION') or _session_name()
    before = _LAST_LOADED[0]
    if before is None:
        # REFUSED, not guessed. Appending a delta needs a before-state, and
        # without one the only safe thing is the old whole-file write.
        return _save_reviews_legacy(data)
    wrote = 0
    for rec in data.get('records', []):
        i = _store._ident(rec)
        now = json.dumps(rec, sort_keys=True)
        if before.get(i) == now:
            continue
        rc, msg = _store.append(me, rec)
        if rc:
            raise CouldNotTell('could not append to the %s shard: %s' % (me, msg))
        wrote += 1
    return wrote
```

Rename the existing body to `_save_reviews_legacy(data)` and leave it
untouched — it is the fallback and the only remaining whole-file writer.

**`_session_name()`**: the gate already derives the session elsewhere (it names
clones in its `--list` output). Use whatever it already uses; do **not** add a
second derivation, and do **not** default to a literal — a wrong `me` files a
record in the wrong shard, which is forging an author on a review ledger.

### 3. A fixture you should add, because I could not

An arm that **opens an obligation, then discharges it from a DIFFERENT
session's process, with the legacy file made read-only**, and asserts the
discharge succeeds and `--list` sees it. That is the one property this whole
change exists for and it cannot be tested from outside your file.

---

## `tools/review_ledger_reseat.py` — second, and NOT patched here

It rewrites the whole ledger at `:325-326` to reseat sha citations after a
rebase. It keeps working on the legacy base layer unchanged, so **nothing is
broken by leaving it alone** — but a sha cited in a *shard* line will not be
reseated, and a record whose `opened_at_sha` no longer resolves is the
`COULD-NOT-TELL` state your own `--list` already reports.

I have **not** written a patch for it, deliberately: reseating an append-only
log means appending a correction line rather than editing one, and which fields
may be corrected that way is a decision about the ledger's semantics, not a
mechanical change. **Named so the gap is a decision and not an oversight.**

`tools/sairn_rebase_resolve.py` needs nothing: shard lines are append-only, so
a conflict in one is "both sides added lines" and keeping both is correct.

---

## How to check it

```
python tools/tier_a_reviews_store.py --selftest     # 22 fixtures, exit 0
python tools/tier_a_reviews_store.py --validate     # identity drift, bad lines
python tools/tier_a_reviews_store.py --read         # union + provenance counts
python tools/tier_a_reviews_store.py --migrate      # dry run, idempotent
```

`--selftest` failing is **exit 2 COULD NOT RUN**, never a result with a caveat.
Every other mode runs the fixtures first and refuses to report if they fail.
