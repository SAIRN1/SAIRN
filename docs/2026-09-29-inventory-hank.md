# Hank inventory — in flight, blocked, stale, and unlogged

**2026-09-29.** Item 10 of queue24. House-cleaning round, written to be read by the
next session in this clone rather than by me.

---

## 1. In flight

**Nothing is half-built.** Every tool written today has a control that passes and is
pushed. What is *open* is not code:

| Item | State |
|---|---|
| The 32 rows `citation_no_source_report.py` flags as claiming an individual read with **neither a line citation nor a group stamp** | Named by the tool, **unread by anybody.** This is the next real pass on the register and it is nobody's. |
| `docs/2026-09-29-register-cells-hank.md` — 7 replacement cells, one gap-ledger row, one pasteable `api/sd-data.js` patch | **Text, awaiting two holders** (see §2) |
| The tier obligation opened today on the two new report-only checks | Assigned to `cody`, 5 review points named |
| 3 records reseated in the review ledger; **16 REFUSED** | Each refusal named. The refusals are the honest majority: most dangling records name a file set no single commit matches, because the work landed across several pushes. |

---

## 2. Blocked, and on whom

| Blocked | Holder | Held | Evidence |
|---|---|---|---|
| **`docs/CRITICALITY-TIERS.md`** — items 2, 4, 5, 8 of queue24 | **`hover`** | claimed **2026-09-29T14:00:36Z**, 0.2h before I checked | Refusal quoted verbatim in `docs/2026-09-29-register-cells-hank.md`. The overlap is **genuine, not lexical** — hover's own queue names the `leg_guestbook` contradiction and the `sd_customers` / `sd_business_snapshots` citation drift. |
| **`api/sd-data.js`** — the `mech_takeoffs` redaction scope fix | **`fourth`** | standing | Patch delivered as pasteable text instead. |
| **Item 3 of the earlier paste** — the ALF audit-licence bootstrap | **Michael** | held at his instruction | `ALF-AUDIT-2026` is live and `zz-audit-owner` exists with no recorded PIN. `docs/2026-09-29-alf-audit-licence-unusable.md` has the recovery SQL. |
| **`tools/report_only_checks.py`** — wiring today's four new report-only checks into the recurring set | **unclaimed, NOT attempted** | — | Four tools shipped report-only and **none is on a cadence.** See §4. |

**One claim refusal that was NOT a real conflict**, recorded because it cost three
attempts: my first three claim strings were refused on shared *methodology
vocabulary* (`tests first`, `known-bad control`) and on **my own naming of a held
file inside a disclosure**. The established resolution is cc's: keep the PR §4.3
declaration out of the claim string, where the tool writes it into the claim file's
`refusals` section itself. **Naming a held file in order to declare that you are
not touching it blocks your own claim.**

---

## 3. My own docs and tool headers that are now stale

Found by re-reading what I wrote, not by a tool.

| Where | What it says | What is true |
|---|---|---|
| `tools/install_git_hooks.py` header | *"must be run once in each of the four clones (SAIRN-hank, SAIRN-cc, SAIRN-cody, SAIRN-fourth)"* | **SEVEN working copies.** **FIXED TODAY** — the count is no longer written there at all; the header points at `nhi_register --check`, which asks git for each sibling's origin and has no name filter. |
| `docs/2026-09-29-write-site-basis-rule-scope.md` | *"209 rows cite nothing"*, and treats that population as undifferentiated | Still 209, but it is now **three populations**: 65 that admit they were not read, 106 carrying a 3.2-pass group stamp, 32 claiming a read with neither. **The doc's argument survives and its number is now coarser than the tool's.** Not corrected — it is a dated scoping document and re-writing it would erase what was known when the recommendation was made. |
| `docs/2026-09-29-gray-error-check-scope.md` | recommends building the hedge rule *"as twenty lines"* | **Built, and it is ~250 lines** with a selftest and a probe. The estimate was wrong by an order of magnitude, in the direction that matters (I under-estimated). Left standing as the record of what I predicted. |
| `docs/FACT-SHEET-2026-09-29.md` | *"22 figures had moved in the twenty minutes between two runs"* | Still true of that measurement, and now **understates it** — the commits figure moves within minutes of any refresh. The sheet says so separately. No correction needed. |
| `tools/fact_sheet_regenerates.py` `NOT_DERIVED_HERE` | lists the tooling-inventory and live-probe rows as not derived | **Still accurate.** Re-checked today; those rows remain unchecked by that tool and the list still names them. |
| `tools/hover_routing_gap_check.py` header | *"2 of 686 entries carry `routable`"* | **11 of 710** now. H1 has kept adding it. **This is a hardcoded measurement in a header** — the exact shape I have corrected in two other files today. **NOT FIXED, and it should be:** the number belongs in the output, which already prints it, not in the prose. Logged here rather than silently left. |

---

## 4. Gaps found and never logged

Each of these was noticed in passing today and has no row anywhere.

1. **Four report-only checks are on no cadence.**
   `hover_routing_gap_check.py`, `hook_integrity_check.py`,
   `citation_no_source_report.py`, `hedge_carry_check.py`,
   `pattern_enumeration_sweep.py`, `idempotence_double_run.py` — six, in fact.
   Only `hook_integrity_check.py` is wired (SessionStart). **A report-only check
   nobody runs is a tool, not a control**, and `tools/report_only_checks.py`
   carries no live claim. Nobody has taken it.

2. **The review gate matches a resource name out of comments, docstrings and test
   fixtures — FOUR instances in three days.** `quotes` against *"unbalanced
   quotes"* in a shlex comment; `leg_processions` and `msb_sale_hours` against test
   fixtures; `sc_anesthesia_base_units` against a docstring (cc's own record
   predicted it); four money resources against a worked example quoting a dispatch
   sentence. **PR §1.2 inside the review gate itself.** Reported four times in four
   obligation records and never made a row.

3. **`tools/tier_a_review_gate.py` has no `--reseat` for a record whose FILE SET
   matches no single commit.** 16 of 22 open records are in that state, because
   work lands across several pushes. The command refuses correctly; there is no
   path to repair them at all.

4. **`leg_clergy` carries `faith_tradition` next to a named individual.** Tier B.
   Religious affiliation is a special category in several regimes. The
   counter-argument is that a clergy member's tradition is their advertised
   professional qualification. **Genuinely arguable, and nobody has argued it** —
   the cell has never been individually read. Not in `docs/2026-09-29-register-cells-hank.md`
   because Michael did not route it; logged here so it is not lost.

5. **A guestbook and a client portal that no outside party can reach.**
   `leg_guestbook` entries are typed by staff and shown to nobody outside the firm;
   SAIRNbuild's Client Portal has no homeowner link. **Same product shape in two
   apps** — a feature named for an outside audience that cannot reach it. Only the
   SAIRNbuild half is written up.

6. **`sairncare`'s other panels have no client tests.** From fourth's own
   obligation record, which I discharged today: the family-contact panel was broken
   in both directions for days, and *"the panel being broken is why the missing role
   gate went unnoticed."* **A dead UI path is not a safe one; it is an unexercised
   one, and the gate behind it has never been tested by anybody.** That note is in
   a verdict and in no index row.

7. **`SV-AUDIT-2026` does not exist**, deliberately, and four probe files name an
   `SV-` audit licence. Recorded in the seed file's own comment. **The probes that
   name it still cannot run**, and that is not written anywhere a probe author
   would look.

8. **The `redaction.complete` field is stored and nothing renders it.** `mech_docs`
   rows carry the residue note deliberately *"so a reader of the stored record can
   see what the pass did"* — and I found no render of it. A disclosure nobody
   displays is the shape `bld_integrations` has in the other direction.

---

## 5. What I will not claim

* **I have not verified the 32 contradictory register rows.** The tool names them.
* **I did not check whether the other six working copies have their hooks armed.**
  Each is local config and must be checked where it lives; one of them is the hover
  auditor's clone, which is a boundary I do not cross casually.
* **The full idempotence corpus run is long** — 64 candidates × 2 runs. Its result
  is reported in the commit that lands it, not here.
