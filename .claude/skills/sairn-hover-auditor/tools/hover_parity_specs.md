# Parity specs — three H1 tools H2 does not yet have

Written 2026-09-24 (H1), on direct instruction. These are BUILD-AGAINST
specs, not copy instructions: per discipline 7 (Ariane — two identical
copies fail identically, a second copy is not a second opinion), H2 should
implement each from this spec against its OWN log and its OWN paths, and
divergence in implementation is a feature as long as the contract below
holds. Both existing H1/H2 builds of `claim_collision_scan.py` already
diverged this way and the divergence surfaced a real DST bug — that is the
model, not a problem to avoid.

A correction for the record: all three tools EXIST as real, running code in
H1's `hover-audit-log/` (the tip beacon ran and republished today). What
did not exist until this file is a spec another instance could build
parity against without reading H1's source.

Common contract for all three (PR §1.11, disciplines doc):
- Three outcomes, never two: PASS (0), FINDING (1), COULD-NOT-RUN (2).
  "Could not read the log" is exit 2 with the reason named — never a pass.
- Every threshold states its epistemic status in its own output: MEASURED
  (from what data) or REASONED (starting number, not yet calibrated).
- A `--selftest` with negative controls that must FAIL the check on
  purpose, run before the tool is trusted; a selftest that cannot go red
  proves nothing.
- Read structured fields, never prose. If the needed structured field is
  absent from an entry, that entry is reported as unreadable, not guessed.

---

## 1. hover_tip_beacon.py — passive tamper seal for the self-log

**Purpose.** A second, PASSIVE integrity signal for the instance's
tamper-evident log, mechanically independent of the hash chain's active
`--verify`. `--verify` is O(n), replays genesis-to-tip, and only reports to
whoever remembers to run it. The beacon is the tamper-seal analog: a small
separate human-readable file stating a checkpoint claim in plain words, so
mismatch or staleness is visible on casual inspection, O(1).

**What it writes** (`--publish`): a beacon file (H1: `TIP-BEACON.md`)
carrying at minimum: the log's current entry count, the tip entry's seq and
chain hash, and the publish timestamp. Refuses to publish (exit 2) if the
log is unreadable or the tip entry is malformed.

**What it checks** (`--check`):
- MISMATCH (exit 1): the beacon's checkpointed (seq, hash) no longer
  matches the log's actual entry at that seq — the seal is broken; possible
  rewrite of already-checkpointed history.
- STALE (exit 1, distinct wording): beacon (seq, hash) still matches, but
  the log has grown ≥ N entries past it (H1: N=15, REASONED). Staleness is
  not tampering and the output must say so — the remedy is republish after
  confirming the chain, not an alarm.
- PASS (exit 0): matches and within the staleness bound.
- COULD-NOT-RUN (exit 2): beacon absent or log unreadable.

**Must NOT.** Substitute for full chain verification, or auto-republish on
mismatch (that would re-arm a broken seal without a human seeing it).

**Negative controls.** (a) tamper a copied log's checkpointed entry →
MISMATCH; (b) append >N entries to a copy without republishing → STALE;
(c) delete the beacon → exit 2.

---

## 2. scope_narrowing_check.py — has attention quietly narrowed

**Purpose.** Detect silent narrowing of what this role reviews: for each of
the four build agents (hank, cc, fourth, cody), count real check/finding
entries logged since that agent was last the SUBJECT of one — from the
structured `target` field, never from summary prose. An agent far past the
others is a computed drift-of-attention signal nobody decided on purpose.

**Pass/fail.**
- FINDING (exit 1): any agent's since-last-subject count ≥ threshold
  (H1: NARROWING_THRESHOLD = 60 real entries, REASONED starting number —
  say so in output). The finding is ATTENTION-ONLY: output must state it
  cannot distinguish "coverage narrowed" from "that agent had less real
  work to check", and that the stale agent is a candidate for the next
  targeted/undirected pass, not a confirmed neglect finding.
- PASS (exit 0): all four under threshold, counts printed anyway (the
  margin, discipline 4).
- COULD-NOT-RUN (exit 2): log unreadable / no parseable entries.

**Entry eligibility.** Only real check/finding entries count toward the
"entries since" denominator (exclude process/self entries) — state the
rule in output so the denominator is published, not implied.

**Negative controls.** A synthetic log where one agent's last-subject entry
is > threshold real entries ago → FINDING; all-recent → PASS.

---

## 3. undirected_sweep_freshness.py — is the undirected sweep actually happening

**Purpose.** Make the deliberately-undirected sweep (no target and no seed
chosen in advance) a mechanically-enforced cadence instead of a principle in
SKILL.md. Reads the structured `undirected_sweep` boolean that the log
tool's `--add` accepts (same discipline as `process_pass` /
`eqa_checkpoint`): a sweep only counts if the field is set — never inferred
from wording.

**Pass/fail.**
- FINDING (exit 1): ≥ cadence real check/finding entries since the last
  entry with `undirected_sweep: true` (or since genesis if none exists).
  H1: UNDIRECTED_SWEEP_CADENCE = 40, REASONED not calibrated — zero prior
  occurrences existed to measure from, and the output must say this on
  every run until a real repeat-gap history exists to calibrate from
  (discipline 8: cadence from a MEASURED drift rate, and until measurable,
  the number's provenance is disclosed, not laundered into fact).
- PASS (exit 0): within cadence; the current count-since is printed (the
  margin).
- COULD-NOT-RUN (exit 2): log unreadable; also if the log tool predates
  the structured field entirely, say that — do not report PASS on a log
  that cannot record the thing being counted.

**Prerequisite for parity.** H2's log tool must accept and store the
structured field first; a freshness checker over a field that cannot exist
in the data is the "check that structurally cannot fire" shape.

**Negative controls.** Synthetic log with cadence+1 real entries and no
sweep field → FINDING; one with a recent `undirected_sweep: true` → PASS.
