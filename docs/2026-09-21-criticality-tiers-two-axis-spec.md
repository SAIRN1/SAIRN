# A two-axis split for `docs/CRITICALITY-TIERS.md` — specification, not implementation

**Author:** hover2 (independent audit session). **For:** Michael's review, then a build agent's implementation.
**Status:** SPECIFICATION ONLY. No code in this document has been run against the live file; every column count, consumer list and regex quoted below was read from the real source tonight and is cited by path and line. This document itself is staged, uncommitted, per the same "propose, do not build" boundary this role holds everywhere else — writing the *code change* this spec describes is a build agent's job, not this one's.

---

## 0. The problem, restated precisely

Tonight's sweep (`hover_log.py` #393, and the sd_exec_msgs finding that triggered it) found a real, repeating pattern: a resource's tier is set from **one blended axis** — "the worst consequence of this resource being wrong or lost" — and that framing has no vocabulary for "the worst consequence of this resource being *read by someone who should not read it*." `sd_exec_msgs`, `exec_context` and (per Michael's own read tonight) `bld_change_orders` were all scored on durability alone while their real exposure is confidentiality. This is not a one-off drafting slip; it is a structural gap in what the single Tier column is even asking.

This is the textbook shape of conflating two of the three properties in the **CIA triad** (Confidentiality, Integrity, Availability) — the model **NIST SP 800-53** and its companion **FIPS 199** use to categorize federal information systems, the model **ISO/IEC 27001** Annex A controls are organized around, and the model **GDPR Article 32(1)** names explicitly: *"the confidentiality, integrity, availability and resilience of processing systems... appropriate to the risk."* All three treat these as **separate risk dimensions that can disagree** — a system can be HIGH on confidentiality and LOW on availability, or the reverse, and scoring only one hides the other. FIPS 199 additionally establishes the precedent this spec leans on hardest: a system's overall security category is the **high-water mark** — the maximum — across its three per-objective ratings, computed mechanically from the parts rather than assigned as a fourth, independent judgment call.

---

## 1. The column/format change

### 1.1 Recommendation: two axes, not three

The textbook CIA model has three axes. This spec recommends **two**: **Confidentiality**, and a combined **Integrity/Availability** axis that preserves the register's existing "worst consequence of wrong or lost" framing exactly as written today.

**Why not the full three-way split**, stated rather than assumed: SAIRN's own tier file has *never* distinguished integrity from availability — "an invoice wrong" (integrity) and "an invoice lost" (availability) already sit under the same sentence and the same letter for every one of the ~387 rows in the file today, and nothing found tonight suggests they diverge in practice for this platform's resources (a resource whose loss matters tends to be one whose corruption matters, for the same reason: someone downstream is relying on it being right and present). Splitting them now would triple the evidence-citation burden across ~387 rows for a distinction this sweep found zero real instances of needing. Confidentiality is different in kind — tonight's sweep found *three real instances* in one grep pass — so it earns the second column; a third axis does not yet earn a third. If a future sweep finds a real case where integrity and availability genuinely disagree for one resource, that is the trigger to revisit this, not a reason to pre-build it now (this platform's own "no over-engineering" standard, applied here rather than just cited).

### 1.2 Exact table shape

Current (verified against `docs/CRITICALITY-TIERS.md`, e.g. line 55):

```
| Resource | Tier | Worst consequence if it is wrong | Evidence |
```

`tools/criticality_tier_check.py:174-192` (`parse()`) reads this as an **exact 4-cell row** (`len(c) == 4`, using its own pipe-splitter `cells()` at line 49) — not a regex over the whole line. This is the single most consequential fact for this spec's migration design (see §2.1).

**Proposed:**

```
| Resource | Tier | Confidentiality | Worst consequence if it is wrong or lost | Worst consequence if it is read by the wrong person | Evidence |
```

Six cells. `Tier` **stays in column 2, in the exact same `**A**`/`**B**`/`**C**` bold-markdown shape**, and its value becomes a **derived, mechanically-computed** field: `Tier = max(Confidentiality, Integrity/Availability)`, using the register's own existing severity order A > B > C (worst-consequence, not likelihood — already stated in the file's own header, line 17, and unchanged by this spec). `Confidentiality` is a new column holding the SAME A/B/C letters, same bold convention, scored on the SAME "worst consequence, not likelihood" philosophy — just asking a different question: not "what if this is wrong," but "what if the wrong person reads this."

The two worst-consequence sentences and the evidence cell stay **one evidence column**, not two: a resource's evidence for why it's Confidentiality-A and why it's Integrity/Availability-A is usually the same paragraph doing double duty (e.g. `sd_negotiated_prices`, line 58, already says *"a leak is also a commercial disclosure"* in its one existing sentence — it was always making a confidentiality argument, just filed under a durability tier). Splitting evidence into two columns would double the citation burden for no real gain; one column that can name evidence for either or both axes, same as today's convention, keeps the migration cost proportional to what actually needs re-deriving.

### 1.3 Why `Tier` stays in column 2, exactly formatted as today — the compatibility argument, not an aesthetic one

Four real, independent consumers parse this file tonight, verified by reading each one directly rather than assumed from memory:

| Consumer | File:line | How it reads the tier | Breaks under this spec? |
|---|---|---|---|
| The file's own validator | `tools/criticality_tier_check.py:183-192` | Exact cell-count match, `len(c) == 4`, `c[1]` = tier | **YES, by design** — this is the one file that must be edited. See §2. |
| Tier A obligation gate | `tools/tier_a_review_gate.py:204` | `^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*A\*\*\s*\|` — position-anchored regex, column 2, exact `**A**` | **No**, if `Tier` (the derived column) stays in column 2 with the same bold format. |
| Isolation coverage grader | `tools/cross_tenant_isolation_scope.py:106` | `^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*A\*\*\s*\|` — identical shape to the above | **No**, same reason. |
| Cold-scan pool (this role's own tool) | `hover_cold_scan_pool.py` `TIER_ROW`, explicitly noted in its own comment as *"Identical to `tools/removal_path_check.py`'s TIER_ROW — reused, not reinvented"* | `^\|\s*`([a-z][a-z0-9_]*)`\s*\|\s*\*{0,2}([ABC])\*{0,2}\s*\|` | **No**, same reason — and by extension `tools/removal_path_check.py` itself, the fourth real consumer of this exact shape. |

Three of four consumers are **regexes anchored on "resource name, then column 2"** and genuinely do not care how many columns follow. Keeping the derived `Tier` in that exact position, in that exact bold format, means this spec changes **zero lines** in three real tools that currently read this file correctly. That is the actual reason for the column ordering recommended above — not convention for its own sake, but a measured, near-zero-blast-radius migration for everything except the one file whose whole job is validating this table's shape.

---

## 2. What `criticality_tier_check.py` needs to validate differently

### 2.1 The mechanical change, precisely

`parse()` (`tools/criticality_tier_check.py:173-193`) must accept **6-cell rows** instead of 4, and must stop trusting the human-entered `Tier` cell as raw data — it becomes a field the checker **computes and cross-checks**, the same way `main()` already cross-checks the rollup counts against the per-row counts (lines 217-235, "a summary that disagrees with its own detail is worse than no summary" — the identical principle, now applied to a computed cell instead of a computed table).

Concretely, `parse()`'s row tuple grows from `(name, tier, worst, evidence)` to `(name, tier, confidentiality, worst_wrong, worst_read, evidence)`, and `main()` gains one new check class alongside the existing `BAD TIER` / `NO WORST CASE` / `NO EVIDENCE` checks (lines 250-261):

```
COMPUTED TIER MISMATCH   <resource> states Tier <X> but Confidentiality=<C> /
                         Integrity-Availability=<IA> computes to <max(C,IA)>.
                         The Tier cell is derived, never hand-entered.
```

This is a **cheap, high-value, purely mechanical check** — exactly the class of error a human free-typing three letters into adjacent cells will make (transpose two rows, forget to bump the derived column after raising one axis), and exactly the class this codebase's own standing discipline says to catch mechanically rather than trust to review (the same reasoning already given for the rollup-count cross-check it sits beside).

### 2.2 Does a Confidentiality-A resource need the same evidence rigor as today's Tier-A? — **Yes, symmetrically, and this is the answer that actually closes tonight's gap**

Today's rule (line 259-261): *"A TIER A ROW MUST CARRY ITS OWN EVIDENCE... B and C are classified by the stated rule, A is hand-verified."* This spec's answer: **apply that same rule per-axis**, not just to the derived overall tier. Concretely:

```
if confidentiality == 'A' and not evidence:
    problems.append('NO EVIDENCE (confidentiality)  %s is Confidentiality-A '
                     'with an empty evidence cell.')
if integrity_availability == 'A' and not evidence:
    problems.append('NO EVIDENCE (integrity/availability)  %s is I/A-A with '
                     'an empty evidence cell.')
```

This is the mechanism that actually prevents a repeat of tonight's finding, not a formality. Under the OLD single-axis rule, `sd_exec_msgs` never triggered the evidence requirement at all — it was scored B, and B rows are "classified by the stated rule rather than individually read" (the platform-wide boilerplate this spec's §3 also has to retire). Under the new rule, the day someone tries to mark a resource Confidentiality-A, the checker demands a real sentence saying why, the same discipline that has kept the existing Tier-A column honest. The gap tonight's sweep found was not a missing rule — it was a missing **axis for the existing rule to apply to**.

### 2.3 The B/C boilerplate must become axis-aware, and must stop asserting things nothing verified

The current default sentence for a B row — *"Employee-auth-gated operational data: neither money nor a regulated record"* (used verbatim on well over 200 of the 302 B/C rows, e.g. `docs/CRITICALITY-TIERS.md` lines 98-110, 117-147, 153-165 and on through the file) — makes **two separate factual claims in one sentence**: an access-control claim ("employee-auth-gated") and a content claim ("neither money nor a regulated record"). Tonight's separate finding (`hover_log.py` #393) is that the access-control half of that sentence was **false** for all 41 `SV_RESOURCES` rows — SAIRNvet had no session gate wired at all, despite the boilerplate asserting one. That finding is independent of this tiering spec and already routed for a build agent to fix in the code; it is named here only because the same sentence is what this spec's boilerplate rewrite must not silently repeat.

**CORRECTION, 2026-09-22 — the sentence above says finding #393 is "already routed for a build agent to fix in the code", and at the time this was written that was not what had happened.** `api/sd-data.js` was re-read directly at the `SV_RESOURCES` block and there was **no session gate**. It was not an oversight awaiting a fix either: the handler carried an explicit comment recording the absence as a **decision** — *"SAIRNvet has no per-employee authentication at all -- `role` is a self-selected dropdown, never server-verified. A session gate here would gate on a session that does not exist."* What had landed was the **documentation** of the absence, not a gate.

**SUPERSEDED THE SAME DAY, AND THE CORRECTION IS LEFT STANDING RATHER THAN REWRITTEN, because the sequence is the point.** `6fb6d696` (hank) landed the real gate a few hours later — *"41 tables including the DEA-relevant controlled-substance register were readable and writable on a bare licence key"* — and `api/sd-data.js:10134` now runs `verifySessionToken(..., 'sairnvet')` over the whole `SV_RESOURCES` map and answers 401 without one. **Re-verified against the handler at the time of writing this line; do not take it from here either.** Its own note names what it does NOT cover: whether `sql/sairnvet_employee_auth_schema.sql` has been run against the live database is unverified, so a real call may answer NOT_PROVISIONED rather than the refusal a signed-out user expects.

**NONE OF THAT WEAKENS §2.3 — it is the argument.** The boilerplate asserted a gate for however long it did while there was none, and nothing in this table ever checked. That the gate exists *today* is exactly why an unverified claim is dangerous: a reader who trusted the sentence was right by accident on 2026-09-22 and wrong on every day before it. **A table that asserts code facts is right only until the code moves, and it never says which day that was.** The row count reconciles exactly and is unaffected — 41 `SV_RESOURCES` keys, 41 `sv_` rows in the register, 44 names in `api/_resources/sairnvet.js` less the three documented `notSynced` exclusions (`sv_audit_backed`, `sv_examrooms_turnover`, `sv_settings`); there is no discrepancy.

**LANDED 2026-09-22 — the enforceable half.** `tools/criticality_tier_check.py` now refuses a **migrated** row whose cells still assert an access-control fact (`ASSERTS A GATE`), and prints `ROWS_STILL_ASSERTING_A_GATE:N` on every run, clean or not, for the un-migrated ones. It binds to migrated rows only, because firing on all 264 live rows that carry the sentence today is precisely the atomic unreviewable diff §3.4 step 1 exists to avoid — the sentence gets fixed as each row moves, by whoever moves it. The cost of that is a check which tests nothing until a row migrates, so the outstanding count is derived and printed rather than left to be inferred, and arms 9–11 of `tests/run_two_axis_tier_parser_probe.py` drive it against a constructed table in both directions.

**RESOLVED 2026-09-22 — "role-restricted" is dropped, by Michael's decision.** The replacement sentence originally drafted below opened *"Internal, role-restricted data…"*, which is itself an access-control claim — weaker than *"employee-auth-gated"*, but the same kind of assertion, and equally unverified by this table. Found by making the §2.3 rule enforceable and then noticing the proposed replacement would have passed its own check. **The rule now stated plainly: this table claims only what it verifies.** A sentence describing who may reach the data is a code fact; the confidentiality axis is about what the data IS. That is the identical shape as every fabrication-adjacent finding this platform closes — a number with no function behind it, a tier with no evidence, and now an access claim with no check behind it. The default below is the corrected wording.

Proposed default sentences, split to match the new columns and to stop asserting the access-control claim as fact:

- **Integrity/Availability-B default:** *"Operational data lost or wrong: neither money nor a regulated record. Classified by the stated B rule rather than individually read."* (unchanged in substance from today, confidentiality claim removed)
- **Confidentiality-B default:** *"No elevated confidentiality class — no PII, PHI, privileged communication, or financial-account detail on this row. Classified by the stated B rule rather than individually read."* (The original draft opened *"Internal, role-restricted data…"*; that clause is **removed**, per the resolution above. It described access rather than content, and nothing in this table verifies it.)

Neither sentence claims a session gate exists. Whether one does is a code fact this table does not assert and should not — the exact lesson of finding #393.

### 2.4 Delta against the current checker, independently confirmed 2026-09-22 — one real gap this spec does not yet cover

Re-read `tools/criticality_tier_check.py` directly (not from memory) against §1-§2 above, **without editing it**, per the standing instruction that this spec proposes the target and a build agent writes the code.

**Confirmed unaffected — no delta needed:** `cells()` (escaped-pipe handling), `apps_with_registries()` / `resource_names()` (the `api/_resources/*.js` reader), `SHAPE_ERROR`, and the app-vs-registry checks (`NO ROLLUP`, `GONE`, `HALF DONE`, `NOT A RESOURCE`) — none of these read the resource-row cell shape this spec changes, and the spec doesn't ask them to.

**Confirmed as expected, already named in §2.1-§2.3:** `parse()`'s row tuple grows from 4 fields to 6; the `BAD TIER` check (currently just `tier not in ('A','B','C')`, line 250) must become a computed cross-check instead of trusting the entered cell; the `NO EVIDENCE` check (line 259, currently only fires on the overall Tier-A) must split per-axis.

**ONE REAL GAP, not yet in this spec, and worth closing before a build agent starts:** `parse()` (lines 173-193) currently tells a **rollup row** (`` `sairnvet` | 41 | **5** | 36 | 0 | **RE-TIERED**... ``, 6 cells) apart from a **resource row** (`` `sv_patients` | **A** | ... ``, today 4 cells) by **cell count alone** — `if len(c) == 6: rollup elif len(c) == 4: resource row`. §1.2/§2.1 above correctly plan to grow resource rows to **6 cells too** (`Resource | Tier | Confidentiality | Worst-wrong | Worst-read | Evidence`), which means the moment a single resource row migrates, it becomes indistinguishable BY CELL COUNT from a rollup row, and would fall into the `len(c) == 6` branch and get silently misread as a rollup line (its confidentiality letter parsed as a resource-count `n`, etc.) — a mis-parse, not a crash, so nothing would say so.

The data already carries a distinguishing signal the code doesn't yet use: a rollup row's cell 1 is a **bare integer** (`41`); a resource row's cell 1 is a **bold tier letter** (`` **A** ``), in both the old 4-cell shape and the new 6-cell shape (§1.2/§1.3 deliberately keep it there, position and format unchanged, specifically so the three regex-based consumers keep working). `parse()` needs to switch its rollup/resource-row test from `len(c) == 6` to checking cell 1's own shape (`` ^\*\*[ABC]\*\*$ `` = resource row, regardless of total cell count; a bare number = rollup row) — cheap, and it's exactly the kind of content-based disambiguation the file already uses elsewhere (the backtick-anchored regex on cell 0 exists for the identical reason, to keep the tier legend from being read as data). **Flagging this now because it's invisible until the first row is actually migrated, at which point it silently corrupts that row's own count rather than raising an error — the same "reports a pass it never performed" shape CLAUDE.md's §1.11 warns about, just found here rather than in a gate.**

This does not block approving the spec's *design* (§1-§2's two-axis model, derivation rule, and column layout are sound and internally consistent); it blocks a **literal reading of §2.1's "accept 6-cell rows instead of 4"** without also changing the disambiguation rule, which whoever implements needs to know going in.

---

## 3. Migration plan

### 3.1 Real numbers, RECOMPUTED at the moment of writing this spec, not quoted from memory

The file's own text (its "Gaps and honest limits" section, `docs/CRITICALITY-TIERS.md` line 543) already states a prose running-total was found wrong once tonight and corrected, and separately admits (line 540) that these prose counts are **not checked by any tool** and drift. Consistent with that warning, this spec does not quote a prose figure — it re-derives the count the same way the file's own text tells a reader to, using the exact command given at line 532:

```
python -c "import re,io;t=[m.group(2) for m in re.finditer(r'^\|\s*\`([a-z0-9_]+)\`\s*\|\s*\*\*([ABC])\*\*\s*\|',io.open('docs/CRITICALITY-TIERS.md',encoding='utf-8').read(),re.M)];print(len(t),{x:t.count(x) for x in 'ABC'})"
```

Run at the moment this section was written: **387 total registered resources, 85 A, 297 B, 5 C.** (This is one A and one B different from the figures quoted earlier in this same drafting session, because `sd_exec_msgs` was re-tiered B→A live, by another session, while this spec was being written — see the note on that row, line 76: *"Nothing mechanical found it and nothing mechanical would have: the checker verifies that every row HAS a tier and that every A row cites evidence, never that a B sentence describes the right axis of failure."* That sentence, written by whoever landed that fix, is this spec's own thesis stated independently, in the platform's own words, in the same file, on the same day. It is cited here as corroboration, not paraphrased as this spec's own idea.)

### 3.2 Which rows need genuine re-derivation, not a mechanical carry-forward

**All 85 Tier A rows** need a confidentiality pass, even though most already carry usable evidence. Reasoning: today's Tier A criteria (line 21) blend "money," "regulated/protected data," and "already caused an incident" into one bucket — and "regulated/protected data" (patient records, trust accounts, legal deadlines) is **already a confidentiality-flavored criterion** wearing an integrity-tier label. A first-pass rule, cheap to apply: money-only Tier A rows (no PHI/PII/privilege in their own evidence text) default to Integrity/Availability-A, Confidentiality-B, **unless** their own evidence already names a confidentiality concern (`sd_negotiated_prices` already does, per §1.2). Regulated/protected-data Tier A rows default to **A on both axes** unless individually read and found otherwise — a DEA-relevant register or a patient record is not usually "fine to read, dangerous to lose"; it is dangerous on both counts, and the existing evidence text for these rows was largely written with both concerns already in mind, just never split apart. This first pass should be near-zero marginal cost: the evidence sentence already exists for every one of these 85 rows; the work is re-reading each one and tagging which axis (or both) the existing sentence actually supports, not writing new evidence from nothing.

**Of the 302 B/C rows**, the great majority are genuinely low on both axes and can carry forward as B/B (or C/C) mechanically, with no new evidence needed — an inventory count, a schedule entry, a device preference is not more or less confidential than it is durable; both are correctly low. The rows that need a genuine, individually-read re-score are the ones tonight's own method (grep for name patterns suggesting sensitive content, then read the serving code) already surfaced as real candidates: **`exec_context`, `bld_change_orders`** (Michael's own two remaining named candidates — `sd_exec_msgs`, the third, is already moved per §3.1), plus this session's own lighter-touch candidates from the same sweep — `sd_comms`, `sv_comms`, `bld_comm_log`, `law_portalmessages`, `sv_soapnotes` — a small, tractable set on the order of **single digits to low teens out of 302**, not a wholesale re-audit. The file's own admission that B is *"the honest weak point"* (line 538) means this list should be treated as a floor, not a ceiling — §3.3's candidate-flagger exists specifically to find the ones a name-pattern grep, run by hand once, did not.

### 3.3 Can a script assist? — Yes, and its real job is *candidate-flagging*, not *scoring*

A script cannot correctly assign a confidentiality tier — that is a judgment call this file's own header already insists on for anything above the default rule (line 27, "a tier asserted with no evidence is a label"). What a script *can* do, reusing exactly the method this session used by hand tonight, is **narrow 302 rows down to the handful that need a human to actually read them**:

1. For each B/C resource name, grep `api/sd-data.js` and the app's own `.html` for the resource's serving code, same as tonight's manual passes.
2. Flag a resource as a **confidentiality-review candidate** if any of: (a) the resource or app-level field names match a sensitivity pattern (`exec|private|confiden|msgs?|notes?|comms?|portal|soap`, extendable — this is the exact pattern this session used by hand); (b) the resource's stored payload (read from `api/_resources/<app>.js`, the platform's own existing unit for this, per the file's own header line 13) contains field names matching PII/PHI indicators (`ssn|dob|diagnosis|ferified — as extendable as (a)`); (c) the resource is read by a role-gated UI element client-side but has **no corresponding server-side role check** — the exact shape of tonight's `SV_RESOURCES` finding, and a structural signal that whoever built the client already believed this data needed restricting.
3. Everything NOT flagged carries forward as Confidentiality-B by the stated default rule, exactly as B rows do today for the existing single axis — **no new evidence required**, matching §2.3's default sentence.
4. Everything flagged gets a **named, per-row TODO** in the migrated file (not left silently at the old tier) for a human pass, the same "COULD NOT TELL is a third state, never folded into a pass" discipline this codebase already applies everywhere else.

This script is a genuinely buildable, scoped tool (**a candidate-flagger, explicitly not an auto-scorer** — named here as a real next step, not built in this specification) — the same "propose the target, not the code" boundary this whole document holds to.

### 3.4 Sequencing

1. Land `criticality_tier_check.py`'s new 6-cell parser and the two new evidence checks (§2), gated so it accepts **either** the old 4-cell shape or the new 6-cell shape during migration — a hard cutover on a 387-row file edited by hand is exactly the shape of change this platform's own precedent (item 22, borrowed reasoning; the eighth cross-domain discipline, nothing announces a check going stale) says to avoid landing as one atomic, unreviewable diff.
2. Run the candidate-flagger (§3.3) once; hand-review the flagged rows (single digits to low teens); re-score the 85 Tier A rows per §3.2's first pass.
3. Migrate the file itself, row by row, app by app — the same unit (`api/_resources/<app>.js`) and the same per-app rollup structure the file already uses, so a partial migration is visible exactly the way "NOT YET RE-TIERED" already is today (line 218).
4. Once every row is migrated, tighten the checker to require the 6-cell shape only, and retire the compatibility branch from step 1.

---

## 4. `exec_context` — resolving the disagreement with `265d09d9`, re-read against the actual source

**The conflict.** Independent review commit `265d09d9` ("review(sd-exec-msgs-tier): discharge cody 22:26:28Z", 2026-09-21) states, while checking for confidentiality-axis siblings: *"exec_context is B and correctly so -- a derived summary, not a channel."* That is the opposite of §3.2/§3.3 above, which name `exec_context` as one of "Michael's own two remaining named candidates" for confidentiality re-score. Two independent passes disagreeing on the same resource, same night, is resolved here with the source file, not by authority.

**Re-read directly:** `api/_lib/exec-context.js` (184 lines) and the gate at `api/sd-data.js:1787-1819`.

**What the file says it is, in its own header (lines 3-19):** moved OUT of `stonedesk.html` on 2026-09-02 specifically because it "carr[ies] SAIRN Tech LLC's own internal business data: the chart of accounts, the StoneDesk price book, and the provisional-patent filing dates with the non-provisional deadline," and because stonedesk.html "is served in full to every customer... so every one of those facts was readable with View Source by anyone who could load the page." The read gate at `sd-data.js:1799-1819` requires a verified employee session AND role `owner`/`admin`, with its own comment stating the browser-side check is "advice" and "this is the copy that actually decides."

**What it actually contains (lines 74-172, the ceo/cfo/cto blocks):** the real chart of accounts (1010-6210 account codes), payroll tax rates, the live StoneDesk price book ($299/$599/$799, itself replacing an earlier price book that had leaked), fundraising round sizing (Pre-seed $500K-$2M, Seed $1-5M), a description of the security/session architecture, and **"provisional patents filed May 21 2026. Non-provisional deadline May 21 2027."** A non-provisional filing deadline is not only commercially sensitive — premature disclosure of the underlying invention ahead of that deadline is a live legal risk to the patent itself, a harder failure mode than "an operational summary is wrong."

**Why "derived summary, not a channel" doesn't resolve the axis in question.** The confidentiality axis asks "what is the worst consequence if the wrong person reads this," not "is this shaped like a channel." A derived summary of a chart of accounts and a patent deadline carries exactly the sensitivity of the facts it summarizes — deriving it does not launder that out. The `265d09d9` measurement method, by its own account, was a grep for the literal word "confidential" in the register's prose plus a name-pattern judgment ("exec_context... genuinely operational") — not a read of `api/_lib/exec-context.js` itself. That is the identical failure this spec's own §2.3 names: a B row "classified by the stated rule rather than individually read."

**Conclusion: the earlier finding stands, unchanged, on this re-read.** `exec_context` is Confidentiality-A, not B — it is already gated as if it were (owner/admin only, enforced server-side, with the file's own header stating the confidentiality rationale for existing at all) — and the served content justifies that gate. The `265d09d9` verdict is the one that needs correction on this specific resource; it is not a case of this spec having overstated anything. **Flagged for Michael's direct decision**, since two independent reviews now disagree on the same row and the disagreement traces to different evidence bases (grep the register's prose vs. read the served file), not to different values.

**RESOLVED 2026-09-22 (Michael's decision, on the re-verification above as deciding evidence): `exec_context` is Tier A.** The re-read of the actual served file and gate is the deciding evidence over `265d09d9`'s keyword-search of the register's prose; that verdict was wrong on this specific row for the reason stated above, not a difference of judgment. `exec_context` joins four other confirmed tier-mismatches found the same night — `law_portalmessages`, `bld_change_orders`, `rf_draws`/`bld_draws`, `law_pimedical` — all B→A, all held pending the two-axis spec (§1-§3 above) being approved and implemented; none of the five has been hand-edited into `docs/CRITICALITY-TIERS.md` directly, since a one-off tier flip ahead of the axis split would re-create the exact "hand-entered, uncross-checked" cell this spec's §2.1 exists to retire.

---

## 4a. Sample pass, 2026-09-22 — two of §3.2's own lighter-touch candidates individually read

Note on tooling: this clone (`SAIRN-hover2`) does not carry `hover_log.py`, `hover_cold_scan_pool.py`, or a coverage ledger — those live only in the primary auditor clone (`Documents\SAIRN-hover`). In their absence this pass drew its sample from §3.2's own named candidate list above, which is the closest equivalent this clone actually has on disk.

**`sd_comms` — read, and correctly B. No mismatch.** `api/_resources/stonedesk.js:144-162,171` places it in `SD_LOCAL_RESOURCES`, the deliberately ungated shared-shop-record list, with a 2026-09-21 comment specifically re-affirming (post the `sd_exec_msgs` incident) that the other twenty members of that list, this one included, are genuine shared shop records rather than exclusion-defined channels. Read in `stonedesk.html:10307-10399`: customer message threads (quote follow-up, installation scheduled, balance due, review request) — operational, customer-facing, exactly what any shop employee needs to see. The "worst consequence" sentence in the register (*"a customer message lost"*) is the right axis for this resource. No re-tier.

**`sv_soapnotes` — read, and flagged as a NEW candidate, not yet in tonight's confirmed batch of five.** The register (line 510) calls it *"neither money nor a regulated record,"* B on the stated default rule, unread. Read directly: `sairnvet.html:518,8494-8495` — this resource IS the veterinary clinical record: subjective/objective findings, an AI-drafted ranked differential diagnosis, and a treatment plan, explicitly gated by a vet sign-off checkbox before, in the app's own words, "it becomes part of the medical record." `api/sd-data.js:9948-10019` (`SV_RESOURCES`) gates it on any valid employee session — no role restriction — which is access-appropriate for clinical staff but does not touch the register's content claim. The inconsistency worth naming: `sv_patients` (the same patient's demographic record) is independently Tier A elsewhere in this platform's registers (`docs/SAIRN-OPEN-WORK-INDEX.md`'s Tier-A list), while `sv_soapnotes` — the diagnosis and treatment narrative for that identical patient — sits at B. A sibling resource not inheriting the tier its own paired record already carries is the same shape §1 names for `sd_exec_msgs`/`exec_context`, run in the other direction. **RESOLVED 2026-09-22 (Michael's decision): `sv_soapnotes` is Tier A.** Same reasoning as the five above: a clinical record (diagnosis, differential, treatment plan) belonging to the same patient whose `sv_patients` row is already Tier A cannot coherently sit at a lower tier itself. `sv_soapnotes` joins the batch — six confirmed tier-mismatches now (`exec_context`, `law_portalmessages`, `bld_change_orders`, `rf_draws`/`bld_draws`, `law_pimedical`, `sv_soapnotes`), all B→A, all held pending the two-axis spec (§1-§3) and a build agent, same reason as §4's closing note.

**§3.2's named candidate list is now fully worked through.** The remaining two — `sv_comms`, `bld_comm_log` — read directly, both confirmed correctly B, no mismatch:

- `sv_comms` (`sairnvet.html:8296-8311`): aggregate marketing/reminder metadata — appointment-reminder and wellness-campaign sends, recipient counts, open rates. No patient-specific or clinical content, no exclusion boundary. Correctly B.
- `bld_comm_log` (`sairnbuild.html:3415-3419,6798-6808`): a per-job client-portal message thread (PM/Office/Client) about ordinary project status — demo complete, a fixture selection question. Customer-facing operational communication, the same shape as `sd_comms`. Correctly B.

Cross-checked against the primary `hover` session's own status row (`C:\Users\marsh\SAIRN-SESSION-LOCKS\status\hover.json`, updated 2026-09-22T03:57:29): it independently reports the identical five-item batch (`exec_context, law_portalmessages, bld_change_orders, rf_draws/bld_draws, law_pimedical`) plus "15 discharged obligations re-verified clean" — consistent with, not additional to, what's recorded here. No cross-reference conflict.

---

## 5. Appendix — concurrency-control validation note

Separate topic, folded in at Michael's request rather than forced into the tiering logic above.

**The question:** does real distributed-systems practice support the direction already chosen tonight for the claim-matching problem — Fourth's owner-assignment work (`tools/tier_a_review_gate.py`, stamping a reviewing OWNER at `--open` time) and cc's proposed obligation-ID scheme — over the platform's existing lexical/keyword matcher (`tools/sairn_claim.py`)?

**Yes, and the theory is not close.** This is the textbook distinction between locking on a **precise resource identifier** and locking on **lexical similarity of a resource's description**, and the second approach is a well-documented anti-pattern for exactly the two failure modes this platform measured tonight:

- **Database two-phase locking** acquires a lock on a row's primary key, never on a text description of the row.
- **HTTP's own optimistic-concurrency mechanism**, RFC 7232's `ETag`/`If-Match`, conditions a write on an opaque, precise version identifier — not on comparing the textual content of two requests for similarity.
- **Distributed lock services** (Google's Chubby, Apache ZooKeeper, etcd) all lock on exact path/key identity; none of them offer or would sanely offer a "lock anything whose description shares two words with mine" mode.
- **ORM optimistic locking** (a `version` column keyed to one specific row's primary key) is the same pattern at the application layer.

The reason lexical matching fails structurally, not just in this platform's specific tuning, is that it is answering the wrong question in both directions at once: it produces **false positives** (two genuinely different resources whose free-text descriptions happen to share vocabulary — the exact shape `sairn_claim.py`'s own measured 38%-accuracy-with-5-false-positives-of-5 result already demonstrated) and **false negatives** (two operations on the identical resource, described in different words, never collide at all — the exact shape behind "FOUR duplicates today" that motivated Fourth's owner-assignment work in the first place). A precise identifier closes both directions at once, because identity comparison has no partial-match failure mode to have in the first place.

**This validates the direction already taken, not a new one.** Fourth's owner-assignment stamp (identity assigned at obligation-open time) and cc's proposed obligation-ID scheme are both instances of the same textbook-correct pattern — assign a stable, precise identifier to the thing being locked, and gate concurrency on identity equality of that identifier, never on how similarly two claims happen to be worded. No further validation work is needed here; this is confirmation that the existing plan is theoretically sound, not a request to change it.
