# h1 b42 -- RFC3161 token refresh cadence spec

**For the record / cross-auditor awareness, routed to cc** (coordinates
cross-cutting tooling and the shared status board, which surfaces chain-tip
data from both hover and hover2). Not a request for cc to build anything --
the implementation already landed this batch, in hover's own scope. This
is the DECISION document the implementation follows, so the rule is written
down once rather than re-derived from reading the code.

## The problem this closes

H1 b41's digest flagged, as DECISION-NEEDED: the RFC3161 token (last
requested at seq1434) and the chain tip (1471 at the time) had drifted 37
entries apart -- wider than any prior handoff recorded. Root cause,
confirmed by reading every prior batch's own check: **the beacon has had a
15-entry staleness rule since 2026-09-15 and is checked every batch; the
TOKEN has never had an equivalent rule or an equivalent per-batch check.**
Every batch asked "is the beacon within 15?" and republished it alone when
not; nothing ever asked the same question about the token, so it was only
refreshed on an ad hoc basis (a handful of named batches: seq793, seq810,
seq881, seq900, seq1098...1434), with no mechanism forcing the next
refresh before the gap grew arbitrarily large.

## The rule

**The RFC3161 token gets the SAME 15-entry staleness threshold the beacon
already has (`STALE_AFTER_ENTRIES` / `MAX_GAP`), checked at the SAME
moment every batch, by the SAME convention ("republish/refresh only if
more than 15 behind") -- not a new or different number, and not a
decision Michael has to keep making per batch.**

Deliberately NOT unified into one shared constant across the two tools:
`hover_chain_status_check.py`'s own `MAX_GAP` is a literal `15`, not an
import of `hover_tip_beacon.STALE_AFTER_ENTRIES` -- so a future change to
one threshold does not silently retune the other. If the two are ever
meant to diverge (e.g. because a real network call to freetsa.org is more
expensive than a local file write, which is a real asymmetry), that is a
deliberate future decision, made explicitly, not an accidental one from
sharing a constant.

## Why the same number, not a wider one for the token

Considered and rejected: a wider threshold for the token (since it costs a
real network round-trip to freetsa.org, unlike the beacon's local write).
Rejected because the token is the STRONGER of the two witnesses -- an
independent, third-party-signed proof, which is the whole reason it exists
alongside the weaker local beacon -- and a wider staleness bound on the
stronger witness would mean the chain's actual independently-provable
state is allowed to lag further behind than its own passive tripwire ever
is. That is backwards: the cheaper, weaker signal should not be kept
fresher than the expensive, strong one by design. The 15-entry number
itself was already chosen (2026-09-15) to be smaller than a typical
session's own entry count, so staleness is caught within roughly one
working session -- that reasoning applies identically to the token.

## Implementation

`tools/hover_chain_status_check.py` (new, this batch, hover's own scope --
not `tools/`, which is cc's; this lives under
`.claude/skills/sairn-hover-auditor/tools/` alongside `hover_log.py` and
`hover_tip_beacon.py`):

  python hover_chain_status_check.py --check
  -> prints chain tip, beacon seq+gap, token seq+gap, one line each
  -> exit 0 if both gaps <= 15
  -> exit 1 (FINDING) naming which gap(s) exceed 15 and the exact command
     to fix each (hover_tip_beacon.py --publish / hover_timestamp.py
     --request)
  -> exit 2 (COULD NOT RUN), fail-closed, if the log does not parse, the
     beacon is unreadable or missing its checkpoint_seq field, or no
     usable chain-tip-seq*.tsr+.msg pair exists at all

9/9 selftest, including two FAILING-FIRST arms (a 20-behind beacon and a
30-behind token are both confirmed flagged before the passing arms are
trusted), a boundary control (exactly 15 behind is NOT flagged -- `>`, not
`>=`), a known-bad control (a `.tsr` with no matching `.msg` is not
accepted as a usable token), and four FAIL-CLOSED controls (missing
beacon, zero token files, empty log, each returns an error rather than a
silent pass).

## Adoption

Item 1 of every future hover (H1) batch dispatch should run
`hover_chain_status_check.py --check` in place of the two separate
"chain tip" and "beacon" checks prior batches ran by hand -- same
information, one command, and the token can no longer be the one half
nobody asked about.
