# Spec: Tier A population completeness check + chain-head external anchor

Written 2026-09-27 (H1), on direct instruction, priority items 1 and 2 of a
three-item queue. Item 1 is a BUILD-AGENT spec (the checker is a platform
tool under `tools/`, which hover does not build); item 2 is an audit result
plus the scoped fix for hover's own log (hover-scope, buildable by either
hover instance once Michael approves the shape).

---

## 1. `tier_population_check` — does the register's population match the code

**The gap this closes, stated as the audit principle it is.** Every existing
check on `docs/CRITICALITY-TIERS.md` — `criticality_tier_check.py`, the
rollup reconciliation, the coverage ledger, hover's row-by-row draws — tests
rows that are IN the register. PCAOB AS 1105-style completeness testing says
that proves nothing about rows that should exist and don't: you cannot find
a missing row by sampling harder inside a possibly-incomplete population.
The verification certificate's "Independent Review Coverage" claim currently
means "100% of the KNOWN population was reviewed" — this check is what makes
"known" defensible. The platform already owns the worked precedent:
`tools/sairn_app_map_check.py` derives the app population from three
independent sources instead of trusting the hand-maintained map, after that
map was wrong five times. This is the same discipline one level down.

**The reciprocal sources, each derivable mechanically, in order of
authority — DISAGREEMENT BETWEEN THEM IS THE FINDING:**

1. `api/_resources/*.js` — the per-app server registries (`{app, resources:
   [...]}`). What the API will actually serve. Machine-readable today; this
   is the primary source.
2. `sql/*.sql` `create table` statements — what has a schema. Catches
   server-side tables with no client accessor (the `alf_signals` shape:
   PHI at rest with no consumer — found by hand in H1 log #532; this
   source finds that class by construction).
3. Client storage accessors per app HTML — `ld('<key>')` /
   `localStorage.getItem('<key>')` keys, filtered to each app's known
   prefix family. Catches client-only stores never registered server-side
   (the `sc_specialty_checks` shape: schema queued, table absent, data
   client-device-only — open-work index :811).
4. `api/sd-data.js` `resource === '...'` dispatch branches — what has
   bespoke server handling.

**The diff, four verdict classes, none folded into another:**

- `UNREGISTERED` — in ≥1 source, not a register row. The completeness
  failure this exists for. Every one is a finding: an untriaged resource
  has NO tier, which operationally means nobody agreed it is not Tier A.
- `PHANTOM` — a register row matching NO source. Either a rename, a removal
  never reaped, or a row invented from a plan (the SAIRNfuneral/
  SAIRNmechanical class from the app-map history).
- `PARTIAL` — in the register and in some sources but missing where its
  own evidence cell says it should be (e.g. a row whose cell cites a
  server handler while only source 3 finds it). Report which sources,
  never a bare count.
- `MATCHED` — present and consistent. Printed as a count with the
  denominator, per the disciplines doc item 3.

**Fail-closed rules (PR §1.11), non-negotiable:** a source that yields ZERO
names is a refusal (exit 2 naming the source), never an empty-diff pass —
a glob that stops matching must not read as "no drift". Exclusions (demo
keys, `*_list` cache aliases, session/role keys) live in a named, versioned
exclusion table IN the tool with one comment line each saying why —
never inline regex carve-outs.

**Cadence and placement:** report-only in `tools/report_only_checks.py`
first (with a named owner to clear it, per disciplines item 8 — a
report-only check nobody clears degrades into a log line), promotion to a
gate decided after the first real run's noise level is known, not before.
Fixture lock before first real run: synthetic register + synthetic
registries covering all four verdict classes in both directions.

**What it must NOT do:** rewrite the register (the app-map rule: a human
edits the map); infer tiers for unregistered rows (its verdict is
"exists and untriaged", never "should be B").

---

## 2. Chain-head anchoring — audit result and scoped fix

**Audit result, confirmed from source (2026-09-27):** NO external anchor
exists. `hover_log.py` writes the chain and verifies it; `hover_tip_beacon.py
--publish` writes `TIP-BEACON.md` — same directory, same filesystem, same
writer (`io.open(BEACON_PATH, 'w')` at :91 is its only output; grep for
mail/anchor/remote/push across both tools: nothing). The beacon is a second
FILE, not a second WRITER: a retroactive edit plus full-chain recompute plus
beacon republish is one attacker with the same access doing three writes.
Tamper-EVIDENT holds only against an editor who does not recompute; against
one who does, there is currently nothing outside the machine to disagree.

**Scoped fix, cheapest real option — the emailed head (Michael's shape):**

- WHAT: on each `--publish` (and therefore at least at each self-health
  refresh), send `{seq, tip hash, entry count, ISO timestamp}` — four
  fields, one line — to Michael's inbox. Gmail's received-timestamp and
  stored copy are outside this machine's write path; that is the anchor.
- HOW: the session drives it through the Gmail connector when one is live.
  HONEST LIMIT, disclosed not papered over: that connector is
  session-interactive, so a headless/cron run cannot send — the cadence is
  "every live session that publishes", not "guaranteed daily". The beacon's
  staleness alarm (15 entries) already bounds how far the log can move
  between anchors a reader would notice.
- VERIFY: on suspicion, take ANY received anchor email, read its (seq,
  hash), and compare against `hover_log.py --verify`'s recomputed hash at
  that seq. A mismatch on any historical anchor proves a rewrite AFTER that
  anchor's date. Older anchors bound the rewrite window.
- FALLBACK for sessions without the connector (named, secondary): append
  the same one-line head to a `TIP-ANCHOR` file inside
  `.claude/skills/sairn-hover-auditor/` and push — origin history plus four
  other clones' copies are also outside this machine's exclusive write
  path. Weaker than email (same git identity could force-push; visible but
  noisier to prove), which is why it is the fallback and not the primary.
- NOT scoped: RFC3161 timestamping services — real, but not "cheapest",
  and the email already gives an independent third-party timestamp
  (Google's) at zero new infrastructure.

Decision left with Michael: approve the email anchor and it can be wired
into `--publish` behind a `--anchor` flag the same day.
