# Is Idaho's Rule 6 → 2.2 gap repeated anywhere else?

**2026-08-30 (Hank). Scoping pass. Nothing changed in any seed or standard.**

Idaho moved computation of time from Rule 6 to **Rule 2.2** effective 1 July
2016. "Idaho Rule 6" has pointed at nothing for a decade, and nothing in this
repo would have caught it: **a stale rule number is not a syntax error, not a
failing test, and not a wrong date — it is a wrong citation on a right answer**,
invisible until somebody follows it.

Michael asked whether that risk is repeated. **The honest answer is that it can
be answered for nine of thirty-nine computation standards, and the other thirty
have never been checked.** This document says which is which, and
`tools/sairnlaw_citation_audit.py` now makes that ratio visible on every run
instead of leaving it to memory.

---

## 1. Verdict

| | |
|---|---|
| **Stale rule numbers found in the repo** | **none** |
| Computation standards whose number was read on a primary source today | **9 of 39** |
| Computation standards never checked | **30** |
| Dormant standards (declared, used by no seeded rule) | **2** |
| Renumberings now probed mechanically | **6** |

**No live citation in this repo points at a superseded rule number.** Every hit
the probes returned was a line warning about a renumbering, not relying on one.

**That is not the same as "no other state has this risk."** Thirty standards have
never had their number re-read since the day they were written, and a state can
renumber at any time. What changed today is that the gap is now counted rather
than assumed.

---

## 2. What was checked mechanically

`tools/sairnlaw_citation_audit.py` — read-only, no network, exit 1 on a hard
finding.

### 2a. Dormant standards — two, and neither is an error

| key | label | status |
|---|---|---|
| `bankr_9006a` | Fed. R. Bankr. P. 9006(a) | declared; **no seeded rule uses it** |
| `frap_26c` | Fed. R. App. P. 26(c) | declared; **no seeded rule uses it**, though `api/legal-deadlines.js` names it in a validator error message as an example |

**A dormant standard cannot compute a wrong date, because nothing calls it.** It
is listed because its citation has never been exercised by a real computation and
has never been re-read — so whoever eventually seeds bankruptcy deadlines inherits
a number nobody verified. That is the same shape as the Idaho problem, one step
further upstream.

### 2b. Uncorroborated citations — none

Every standard's rule number appears somewhere in the repo besides its own
declaration line — in a verbatim quote in an engine comment, in a gate document,
or in a calendar's authority block. A number written down exactly once would be a
number nobody had checked twice.

### 2c. Stale-number probes — six maintained, all clean

Each probe is a regex plus **the replacement citation**. A mention of a stale
number that names its replacement nearby is an explanation, not a live citation —
that is the suppressor, and it is more principled than a keyword list.

| probe | why it would be stale |
|---|---|
| Idaho "Rule 6" / "I.R.C.P. 6" | computation moved to Rule 2.2, 2016 |
| Nebraska "Rule 6(e)" | → § 6-1106(e) in 2008 → § 6-1106(c) in 2025 |
| Nebraska § 25-1143 | **repealed** by Laws 2000, LB 921 § 38; now § 25-1144.01 |
| Florida "R. Jud. Admin." without "Gen. Prac." | set renamed in 2021 |
| Florida "Rule 1.090" | computation moved to R. 2.514 in 2006 |
| California "R. Ct. 45" | Rules of Court renumbered 2007; now rule 1.10 |

**Never delete a probe that stops finding things.** A quiet probe is the point.

---

## 3. What was checked against a primary source, by hand

Four of these came out of today's seeding work; five were chosen by risk. The
risk criterion: **a computation rule that lives in a different rule set from the
substantive rules it governs**, because a rename or reorganisation of that other
set slips past everyone who only ever reads the civil rules.

| standard | verified | source |
|---|---|---|
| `id_ircp_2_2` | ✅ **the finding** | isc.idaho.gov — Rule 2.2, "Computing and Extending Time" |
| `ne_25_2221` | ✅ | nebraskalegislature.gov § 25-2221, named by Neb. Ct. R. Pldg. § 6-1106(a) |
| `ms_r_civ_p_6` | ✅ | courts.ms.gov, 2026-07-01 MRCP PDF |
| `nm_1_006` | ✅ | nmonesource.com, NMRA Rule Set 1 |
| `ks_60_206` | ✅ | ksrevisor.gov |
| `pa_rja_107` | ✅ | **201** Pa. Code Ch. 1 Rule 107, "Computation of Time" |
| `ca_crc_1_10` | ✅ | courts.ca.gov — page title is literally "Rule 1.10. Time for actions" |
| `nv_nrcp_6` | ✅ | leg.state.nv.us NRCP — "Rule 6. Computing and Extending Time" |
| `fl_rgpja_2514` | ✅ | current set name "Rules of General Practice and Judicial Administration" confirmed; 2.514 retained |

**Pennsylvania nearly produced a false alarm and the reason is worth recording.**
The first fetch of Pa.R.J.A. 107 used Title **204** and returned **HTTP 200 with
a page reading "File not found. Please go back and try again."** The rule lives at
Title **201**. That is the third soft-404-inside-a-200 today, after Mississippi's
commented-out MRCP link and Idaho's `printpdf` path — a 200 status code is not
evidence a legal source exists, on any of these hosts.

---

## 4. The thirty that have never been checked

Listed in full because a partial audit that reads as a complete one is worse than
none. **None of these is known or suspected to be wrong.** They are simply
unverified.

```
al_rcp_6              ar_rcp_6              bankr_9006a           ca_ccp_12_12a
ct_pb_63_2            frap_26a              frcp_6a               ga_ocga_1_3_1_d3
illinois_5ilcs70_111  indiana_tr_6a         ma_rcp_6a             md_rule_1_203
michigan_mcr_1108     mn_rcp_6_01           mo_rule_44_01_a       nc_rcp_6a
nj_r_1_3_1            ny_gcl_20             ohio_civ_r_6a         ok_12_2006
or_orcp_10            sc_rcp_6              tx_trap_41            tx_trcp_4
ut_urcp_6             va_code_1_210         wa_cr_6a              wi_801_15
wv_rap_39a            wv_rcp_6a
```

### Priority order, if this is ever worked through

**Tier 1 — computation lives in a different rule set or code title from the
substantive rules.** These are where a rename hides.
`michigan_mcr_1108`, `illinois_5ilcs70_111`, `ny_gcl_20`, `ga_ocga_1_3_1_d3`,
`va_code_1_210`, `ca_ccp_12_12a`, `ct_pb_63_2`, `or_orcp_10` (Oregon puts
computation at ORCP **10**, not 6, which is itself the kind of thing that gets
mis-cited).

**Tier 2 — states with restylings in living memory.** `ut_urcp_6`,
`mn_rcp_6_01`, `md_rule_1_203`, `sc_rcp_6`.

**Tier 3 — statutes, where renumbering is rare but repeal is not.**
`wi_801_15`, `ok_12_2006`. Nebraska's § 25-1143 is the reminder that a statute can
vanish entirely.

**Tier 4 — federal and FRCP-clone states**, low risk and high visibility:
`frcp_6a`, `frap_26a`, `bankr_9006a`, `ohio_civ_r_6a`, `indiana_tr_6a`,
`al_rcp_6`, `ar_rcp_6`, `ma_rcp_6a`, `nc_rcp_6a`, `wa_cr_6a`, `wv_rcp_6a`,
`wv_rap_39a`, `nj_r_1_3_1`, `mo_rule_44_01_a`, `tx_trcp_4`, `tx_trap_41`.

---

## 5. One thing found on the way that is not a renumbering

**Florida declares no `JURISDICTION_COVERAGE` entry, and Fla. R. Gen. Prac. & Jud.
Admin. 2.514(a)(1)(C) has a rollover limb this engine does not model:** the last
day rolls if it *"falls within a time extended by order of the chief justice"* —
the hurricane and emergency tolling limb. Read while confirming the rule number,
not sought.

**Direction: EARLY, so it is a disclosure gap and not a correctness bug.** If the
chief justice extends time and the engine does not know, the engine reports a date
sooner than the true one. Filing early is safe.

**Not fixed here.** Re-auditing a jurisdiction seeded months ago is a different
job from checking its citation, and doing it as a side effect of this pass is
exactly the scope creep that makes an audit untrustworthy. Recorded so it is a
decision rather than an oversight.

---

## 6. What to do next time

1. **Run `python tools/sairnlaw_citation_audit.py` when seeding a jurisdiction.**
   It is read-only and takes a second.
2. **Add the new standard to `LEDGER`** with the date and the URL the number was
   read from. Only add a row you actually verified — an absent row is the signal.
3. **When a renumbering turns up, add a `STALE_PROBES` entry** with its
   replacement citation, so it can never quietly come back.
4. **Do not treat "no hard findings" as "all citations are current."** The tool
   reports what it can prove. Section 4 of its output is the honest part.
