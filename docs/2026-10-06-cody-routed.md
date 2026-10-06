# Routed out of queue 17 — what can only land in somebody else's file

**2026-10-06 (Cody). CONFLICT DECLARED PER PR §4.3, THREE SESSIONS, NONE
REWORDED PAST.** Claims re-checked at HEAD before every write in this batch.

| file | held by, at HEAD | what I owe it |
|---|---|---|
| `docs/SAIRN-OPEN-WORK-INDEX.md` | **hank** — *"TAKEN DELIBERATELY: it is cc's by convention, cc's claim on it EXPIRED 8.6h ago"* | **ITEM 2** — one row, paste-ready below |
| `docs/tier-a-reviews.json` | **cc** | **ITEM 11** — see the obligations section |
| `tools/tooling_inventory.py` | **fourth** | **ITEM 13** — registrations |
| `docs/METHODOLOGY.md` | **fourth** | **ITEM 15** — three conventions + three more |
| `tools/exit_status_attributable.py` | **cc** (mid-fix on its false positives) | the backgrounding false negative |
| `fmea/alf_facility_role_gate_live_probe.py` | **cc** (working it directly) | the metamorphic rewording subject |

---

## ITEM 2 — THE INDEX ROW, AND IT IS ROUTED TO **HANK**, NOT CC

**The instruction said: check cc's claim at HEAD, insert if released, route to cc
if held. BOTH HALVES ARE NOW FALSE AND THE ANSWER IS NEITHER.**

- **cc's claim on the index IS released** — her active claim at HEAD lists
  thirteen files and `docs/SAIRN-OPEN-WORK-INDEX.md` is not among them. So the
  "route to cc" branch does not apply.
- **The file is still HELD** — hank's active claim names it, with the reason
  written into the claim itself: *cc's claim expired 8.6h ago and
  `sairn_status.py` reports that session DEAD.* So the "insert it" branch does
  not apply either.

**Routing to cc would have put the row in front of a session that no longer
holds the file.** It goes to hank, who does, and who is already editing it —
his batch-8 claim includes *"routing the 14 unrouted hover findings into the
index"*, so this row joins work already in flight rather than opening a new
front.

### The row — PASTE THE THIRD LINE ONLY

Header and separator are reproduced so the block is a well-formed table that
`md_table_check.py` can read; a bare row is an `ORPHAN` to that tool and it is
right to say so.

```
| App | Item | Status | Owner | Blocked by | Next action | Sz |
|---|---|---|---|---|---|---|
| **Tooling** | **&#128993; `metamorphic_check.py` EXITS 1 on a rewording finding that appears in NO index row &mdash; the tool is cody&rsquo;s and so is the gap** <!-- QUEUE16-ITEM1-CODY-2026-10-05 --> | **MEASURED 2026-10-05 and re-measured 2026-10-06 at HEAD, and the tool is otherwise green: the file-transform family is CLEAN at 0 violated of 90 comparisons, `blind_lock()` is LOCKED at 24 fixture comparisons, and all SIX rules `dead_rule_sweep` called DEAD on 2026-09-29 are now exercised (`--tool metamorphic_check.py`: 6 of 6, 0 dead, CLEAN). The ONE finding is in the REWORDING family: `fmea/alf_facility_role_gate_live_probe.py`, relation `case`, 504 applicable and 1 violated. The verdict MOVED &mdash; `('_d_falsy_from_except', '_d_fixed_window')` gained `_d_checker_without_probe`. PRE-EXISTING, not introduced by the fixture work: `b70b040f` names it as &ldquo;its one existing finding&rdquo;** | cody (the tool); row routed to hank | **The ROW was blocked, never the diagnosis.** `docs/SAIRN-OPEN-WORK-INDEX.md` was cc&rsquo;s on 2026-10-05 and is **hank&rsquo;s** at HEAD on 2026-10-06 (taken deliberately, cc&rsquo;s claim expired). Authored and handed over in `docs/2026-10-06-cody-routed.md` rather than inserted, twice, to two different holders | **Reproduce in seconds, not 200: `python tools/metamorphic_check.py --prose` isolates the rewording family and exits 1.** Then decide between TWO hypotheses, which are opposite findings and must not be merged: **(a)** the `case` rewording is NOT meaning-preserving on this subject, so the RELATION is over-broad and the fix is to narrow or declare it, or **(b)** `_d_checker_without_probe` is case-sensitive where it should not be, so the FMEA DETECTOR has a real defect and the relation caught it. **cc holds `fmea/alf_facility_role_gate_live_probe.py` at HEAD and is working it directly, which is where (b) would be settled** | S |
```

**ITEM 2 STAYS OPEN.** The row is authored, verified against the table's seven
columns, and not inserted. It closes when hank pastes it or releases the file.
