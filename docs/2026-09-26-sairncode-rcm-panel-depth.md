# The eight enterprise RCM panels, measured — 2026-09-26

**The debt two audits recorded and neither paid. Measured, not argued.**

**HEADLINE: one of the eight has a server-side domain rule. The other seven are
store-and-render behind a generic handler, and every mention of them in
`api/sd-data.js` is inside a comment.** `claims` scores 9/9 on the depth
instrument; `prebill`, `hcc`, `drg`, `rac`, `denial`, `ar` and `revenue` each
score 6/9 and each is missing **the same three** deep signals — `server_named`,
`domain_verb`, `verb_sent`.

Measured at `0456f0cb` by `python tools/panel_depth.py sairncode claims prebill
hcc drg rac denial ar revenue`, criteria `2026-09-26.2`, fixture lock 12/12.

---

## 1. Why this was owed

`docs/competitive-gap-audit-sairncode.md` (2026-09-23), §5:

> *"SAIRNcode's existing panel set already covers real enterprise RCM breadth ON
> PAPER — claims, prebill, HCC, DRG, RAC, denial, AR, revenue — and that is
> exactly the sentence to be careful with. Breadth of panel is not depth of
> function, and this audit measured the presence of vocabulary and resources, not
> the sufficiency of any one workflow at scale. **A direct depth check on those
> eight panels is owed before pitching a large hospital system**, and it is not
> performed in this document."*

The 2026-09-26 cloud wide-lens audit inherited that verdict and deferred it
again, in its own §6: *"It does not verify … the depth of SAIRNcode's eight
enterprise RCM panels."* Two documents named it as owed and neither did it, which
is how a caveat becomes a permanent feature of a file.

---

## 2. The measurement

Nine signals, four SHALLOW and five DEEP. **The shallow four are what "the
vocabulary and resources are present" already meant** — they are what both audits
had — so a panel scoring well on them tells you nothing new. The discrimination is
entirely in the deep five.

| panel | PRESENT | UNKNOWN | missing DEEP |
|---|---|---|---|
| **claims** | **9/9** | 0 | — |
| prebill | 6/9 | 0 | `server_named`, `domain_verb`, `verb_sent` |
| hcc | 6/9 | 0 | same three |
| drg | 6/9 | 0 | same three |
| rac | 6/9 | 0 | same three |
| denial | 6/9 | 0 | same three |
| ar | 6/9 | 0 | same three |
| revenue | 6/9 | 0 | same three |

**PRESENT and UNKNOWN are two numbers and are never added.** UNKNOWN is 0 across
the board here, which is the only reason the PRESENT column can be read at face
value — a row at 6 present / 3 unknown would be a different finding entirely.

### 2.1 What all eight DO have, and it is real

Every one of the eight has a panel, a nav route, a registered resource, a client
write path, and **a real `create table` in `sql/`** — not localStorage. That is
not nothing: it is a persisted, licence-scoped, server-backed store per panel,
and it is why the audits' "breadth on paper" was a fair description rather than a
generous one.

### 2.2 The three signals seven of eight are missing

**`server_named` — the resource is not named in executable code anywhere in the
endpoint.** `api/sd-data.js` mentions `sc_denial`, `sc_ar` and `sc_revenue`
repeatedly, and **every one of those mentions is a comment.** Code-line count:
`sc_claims` 4, the other seven **0**. All seven ride the generic `SC_RESOURCES`
handler, so whatever validation they have is whatever that branch does for all
22 `sc_` resources — there is no per-resource rule, by construction rather than
by oversight.

**`domain_verb` — no verb beyond generic CRUD.** The registry builds
`extraActions` in a loop that gives every resource `['delete']` or
`['soft_delete','tombstones']`, and exactly one line adds anything else:

    if (name === 'sc_claims') map[name] = map[name].concat(['therapy_accumulator']);

**Cross-checked across the whole `sc_` family, not just the eight: that is the
only domain verb SAIRNcode has.** `sc_anesthesia`, `sc_auth`, `sc_coded_items`,
`sc_compliance`, `sc_credential_scope`, `sc_dme`, `sc_eligibility`, `sc_encoder`,
`sc_fraud`, `sc_pctc` — all report none.

**`verb_sent` — nothing to send.** Reported False for the seven because there is
no domain verb, not because a declared verb is unsent. The distinction matters and
the tool prints it: *"DECLARED AND NEVER SENT"* is the SAIRNmechanical
`eligibility` defect — engine, endpoint, registry, ten tests and no caller — and
none of these seven is in that state. `claims`' verb **is** sent
(`therapy_accumulator`).

### 2.3 What `claims` has that the others do not

`sql/sairncode_claims_schema.sql`; four code mentions in `api/sd-data.js`
including `if (resource !== 'sc_claims')` refusing the verb for anything else and
a `503 NOT_PROVISIONED` that says *"nothing was accumulated"*; the
`therapy_accumulator` verb, declared and sent; and 12 test files naming the
resource against 3 for each of prebill/hcc/drg/rac.

**It is the shape the other seven would need**, and the registry comment says why
it exists rather than being a table: *"there is no second fact to store: the
figure IS the claims, and a stored running total is a number that silently stops
agreeing with the rows the day one is corrected."*

---

## 3. WHAT THIS DOES AND DOES NOT ANSWER

**It does not answer the question the audits deferred.** They asked about
*sufficiency at hospital scale*, and no static instrument can reach that — it
needs a real customer's volume and a real coder's judgement. What this separates
is **"a table and a form"** from **"a rule, a server that enforces it, and a test
that drives it."** That is strictly weaker, it is stated as weaker everywhere it
appears, and it is not a substitute.

**A DEEP signal reading NO is not automatically a defect**, and the seven are the
case in point: several of these panels may correctly have no domain verb because
there is no second fact to compute. The instrument prints a shape, not a score,
and carries **no threshold** — deliberately, because a threshold here would
manufacture a pass/fail out of a design question.

**Three named limits:**

1. **`suite` counts files that NAME the resource.** A file can name it and assert
   nothing about it. The 12-vs-3 split is a real signal about attention, not a
   coverage measurement.
2. **A capability served by its OWN endpoint is invisible to `server_named` and
   `domain_verb`.** `sc_eligibility` reports no domain verb and yet SAIRNcode runs
   live X12 270/271 through `api/sc-eligibility.js` — a whole endpoint the
   registry knows nothing about. **This does not affect the eight**: `ls api/sc-*`
   is `sc-ai`, `sc-auth`, `sc-credentials`, `sc-eligibility`, and none of the
   eight has one. But quoting a 6/9 for any other resource without checking for a
   dedicated endpoint would understate it.
3. **The criteria moved once, after the first real run.** `2026-09-26.1`'s
   `domain_verb` credited `sc_prebill` with five verbs — `sc_drg`,
   `sc_eligibility`, `sc_fraud`, `sc_hcc`, `sc_pctc` — because
   `SC_TIER_A_SOFT_DELETE_ONLY` puts several resource names on one line and a
   quoted-string scan cannot tell a neighbour from a verb. Sibling names are now
   excluded by prefix and a fixture holds it. **Any figure stamped `.1` is not
   comparable to one stamped `.2`.**

### 3.1 And the fixture lock earned itself before any data was touched

`2026-09-26.1`'s `sig_panel` searched the raw file, and the lock's *"a panel named
ONLY in a comment does not count"* fixture **rejected the criteria before a single
real panel was judged** — the tool exited 2 with *"NOTHING REAL WAS JUDGED"*.
That is cross-domain discipline 1 working exactly as written: a criterion chosen
by looking at what produced a number is a description of the data wearing a
check's clothes.

**Declared per that discipline's own rule:** one fixture was **corrected** because
its expectation was wrong (the original `domain_verb` fixture expected a file-wide
match to count), and two were **added** after the real run surfaced shapes the lock
had not predicted. No fixture was changed to match tool output.

---

## 4. What follows from this, ordered

**Nothing here is built. This is the measurement the audits owed; what to do with
it is a product decision.**

1. **The sentence to stop using externally is "eight enterprise RCM panels."** It
   is true and it invites a reading the code does not support. The honest version
   is: *eight persisted, licence-scoped RCM data stores, one of which carries a
   server-enforced domain rule.* That is still a real answer to a small practice
   and is not yet an answer to a hospital system.
2. **If one of the seven is worth deepening first, `denial` has the strongest
   case** — it already has the most test attention of the seven (11 files), it has
   a second resource (`sc_denial_events`) purpose-built beside it, and
   `scPreSubmissionRisk()` already computes real counts from it. Naming it
   server-side and giving it a verb is the smallest step from 6/9 to 9/9. **Not
   proposed as work; named so the next dispatch is not guessing.**
3. **`tools/panel_depth.py` takes any app and any panel list.** The same debt
   exists unmeasured for SAIRNdental's 22 panels and SAIRNsenior's 18, and
   re-running it there is cheap.

## 5. Decay

Every figure is a code-line count at `0456f0cb` against criteria `2026-09-26.2`.
**Re-run rather than quote**, and check the criteria stamp before comparing two
runs — the stamp moved once in this document's own lifetime and the reason is in
§3.3.
