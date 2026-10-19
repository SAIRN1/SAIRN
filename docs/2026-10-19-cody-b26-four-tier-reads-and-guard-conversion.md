# cody b26 — four individual tier reads, the sibling-guard conversion, the known-red tail census, and the sweep continued

2026-10-19. Four items, each with its measurement and its ablation. Every
figure here was produced by a named re-runnable program in `docs/b26-logs/`;
none is quoted from a prior document.

---

## 1. Item 2 — the four tier rows b25 left disagreeing with `customers`

b25 retiered `customers` **B/B → A/A** and in doing so broke a stated CLASS
decision: four other rows were held at B on the same class reading, and that
reading is now struck through for one member and standing for the other four.
b25 §7.2 named the next step and deliberately did not take it: *"read each
one's columns out of its own `sql/` schema and its own write site — **not** out
of the register and **not** out of the `customers` decision."*

### 1.1 THE TEST, STATED BEFORE THE VERDICTS SO IT CANNOT BE FITTED TO THEM

> A row is **confidentiality A** when its own written fields, read together,
> identify a specific private individual **AND** attach to them something
> beyond how a business reaches them — a dwelling, an unbounded narrative, or
> a protected characteristic.
> A row is **B** when the fields identify a **business**, or identify a person
> **only** by how a business reaches them.

**THE CONTROL IS `customers`, WHICH THE TEST MUST RETURN A FOR.** Without it
this is a test that happens to return B three times and nothing establishes it
can return anything else. `customers` writes
`{id, name, service, recurring, phone, email, address, notes}` — `address` is a
**dwelling**, so A, which is the tier b25 landed on other grounds. **The test
reproduces a verdict it did not set.**

### 1.2 WHAT THE `sql/` SCHEMAS ANSWER, AND IT IS THE SAME ANSWER FOUR TIMES

**ALL FOUR ARE OPAQUE `data jsonb` ENVELOPES. Not one carries a single payload
field as a named column.**

| row | schema | shape |
|---|---|---|
| `bld_suppliers` | `sql/sairnbuild_data_schema.sql:383`–`393` | `{id uuid, license_hash, app_id, supplier_id, data jsonb, created_at, updated_at}`, `unique (license_hash, supplier_id)`, 65,536-byte cap |
| `sf_vendors` | `sql/sairnfreedom_data_schema.sql:678`–`688` | same, keyed `vendor_id` |
| `leg_clergy` | `sql/sairnlegacy_data_schema.sql:117`–`121` | same, keyed `clergy_id` |
| `dnt_vendor_contacts` | `sql/sairndental_vendor_schema.sql:108`–`118` | same, keyed `vendor_contact_id` |

**SO AN sql-ONLY READ OF THESE FOUR WOULD HAVE REPORTED "NO PII" FOR ALL FOUR
— INCLUDING THE TWO THAT CARRY A NAMED INDIVIDUAL's DIRECT PHONE AND EMAIL.**
That is why the instruction says *schema **and** write site*: the schema half
of this read is load-bearing only as the fact that **it cannot decide
anything**, and a reader who stopped there would have confirmed B four times
and called it four individual reads.

### 1.3 THE FOUR READS — columns quoted from the write site at HEAD

**`bld_suppliers` — B/B CONFIRMED, and now field-grounded.**
`saveSupplier()` at `sairnbuild.html:6649` writes
`{id, name, category, terms, contact, phone}`. Input labels at `:1701`–`:1703`
are *"Supplier Name"*, *"Category"*, *"Terms"*, *"Contact"* (placeholder
*"Optional"*), *"Phone"* (placeholder *"Optional"*). **There is no email field
anywhere on this row.** Identifies a **business**; the one person-shaped field
is how to reach it. → **B.**

> **THE NUANCE THE REGISTER DOES NOT STATE, recorded rather than left
> implied.** Its basis is *"`contact` IS A DEPARTMENT, NOT A PERSON in every
> seeded row"*. That is true of the **seed** (`:3472` — *"Order Desk"*,
> *"Sales"*, *"Estimating"*, *"Account Rep"*) and **the UI does not enforce
> it**: `supm-contact` is free text with a bare *"Optional"* placeholder. It
> does **not** move the tier, because even typed with a person's name the row
> holds a name plus a business switchboard number and no email, no address and
> no narrative.

Integrity **B**: `terms` is a string (*"Net 30"*); spend is computed live from
`bld_pos` — panel `:956` *"spend-to-date"*, KPI `sup-spend` `:960` *"Via issued
POs, all time"* — and is not stored here. **CITATION RE-DERIVED:** the cell
cites `:3379` for the write. At HEAD `:3379` is neither the write nor the seed
— the seed is `:3472` and the write is `:6649`. Named, not silently repointed;
the verdict is unchanged, so the cell was **not** rewritten.

**`sf_vendors` — B/B CONFIRMED, and the class never applied to it.**
`sfAddVendor()` at `sairnfreedom.html:5654` writes
`{id, name, category, brand, licensed}`. **No person, no phone, no email, no
address.** There is no individual on this row **at all**, so it cannot be in
`customers`' confidentiality class on any reading. → **B.**
**CITATION RE-DERIVED:** the cell says `sfAddVendor()` is *"currently near
`:5263`"*; it is at `:5654`. **Drift +391.** Verdict unchanged, cell not
rewritten.

**`dnt_vendor_contacts` — B/B CONFIRMED, and the JUSTIFICATION MOVES. This is
the row that most needed the read.**
`vEditContact()` at `sairndental.html:6803` stores `{rep_name, phone, email}`
keyed by vendor. A named individual, and **nothing beyond how a business
reaches them**: no address, no narrative, no protected characteristic. → **B.**

Its cell held it at B **on the CLASS**, in terms: *"the same shape already at B
for `bld_suppliers`, `sf_vendors` and `sen_applicants`"*. **That comparison is
FALSE ON THE FIELDS in two of its three directions** — `bld_suppliers` has no
email field anywhere on the row and `sf_vendors` has no person on the row at
all — so **the class it was held at B on contained no other member carrying a
named individual's direct phone AND email.** The tier survives; the reasoning
under it does not, and it is replaced with the field test rather than left
resting on a clause b25 struck through. **CITATION RE-DERIVED:** the cell cites
`:6598`; it is `:6803`. **Drift +205** — the fifth stale citation found in this
one cell.

**`leg_clergy` — B/B → A/A. THE TEST MOVES THIS ROW.**
`saveClergyPartner()` at `sairnlegacy.html:4930` writes
`{id, name, faith_tradition, phone, email, notes, created_at}`; the seed at
`:2152` is `{id:'CG-1', name:'Rev. Thomas Boyle', faith_tradition:'Catholic',
phone:'(440) 555-0210', email:'', notes:''}`.

A named individual's **direct phone AND email**, plus **`notes` — an unbounded
free-text field about that person, which no other row of the four has** — plus
`faith_tradition`.

> **THE RETIER DOES NOT REST ON `faith_tradition` AND THE PRIOR READING OF IT
> IS NOT OVERTURNED.** The 2026-09-24 argument (hover H1 log #531, folded by
> CC) that the field is a **service offering** on the `sv_staff` precedent is
> sound and is kept. The row moves on **`notes` plus `{name, phone, email}`**,
> which satisfies the test's second limb without touching the belief question.
> **The caveat that cell recorded stands and is NOT discharged by this
> retier:** if this platform ever adopts a special-category-belief rule,
> re-read this row first.

Integrity stays **B** — no money, no regulated determination computed from this
row. **Checked, not assumed:** `clergyBookingConflict()`
(`sairnlegacy.html:4917`) reads `leg_clergybookings`, **not** this row, so a
wrong clergy record means a call placed to the wrong officiant.

**CONSEQUENCE NAMED RATHER THAN DISCOVERED:** at A,
`tools/tier_a_review_gate.py` records a Tier A review obligation against any
future change whose diff names `leg_clergy`. That lands on whoever next touches
`sairnlegacy.html`, and it is **the point of the tier** rather than a side
effect.

**`sen_applicants`** (`:552`, name + phone only, no email, no narrative)
returns **B** under the same test and is **not touched** — not one of the four,
and its cell is already field-grounded. Named so the next reader does not
re-derive that it was considered.

### 1.4 THE EDIT, MEASURED BOTH WAYS

`docs/b26-logs/retier_b26_four_rows.py` rebuilds each row **WHOLE**, never
splitting on `|`:

```
lines          663 -> 663
`|`-rows       453 -> 453
leg_clergy     line 456  B/B -> A/A   pipes 7 -> 7
dnt_vendor_... line 318  B/B -> B/B   pipes 7 -> 7
lines differing from the original: [318, 456]   (expected exactly these two)
EXIT=0  python tools/md_table_check.py    docs/CRITICALITY-TIERS.md 434/434 OK
```

**Every other line asserted byte-identical by the inserter**, rather than
checked by eye. `bld_suppliers` (`:233`) and `sf_vendors` (`:382`) were **NOT
rewritten** — their cells already say *"individually read, not re-classified by
the rule"* and the read confirms them, so editing them would be a diff with no
finding in it. **TWO ROWS CHANGED, NOT FOUR. THAT IS THE "no bulk retier"
instruction honoured, not a shortfall.**

---

## 2. Item 3 — the sibling guard conversion. The decision, taken.

Standing in every handoff from b19 to b25 as *"the 151/57 sibling
`NOT_PROVISIONED` guards are still NOT converted — **a decision, not a
backlog**."* Decided and done.

### 2.1 THE TWO CONCEPTS, stated above the code in the file itself

> **THE READ-SIDE CONCEPT:** a read that could not be performed is not an empty
> table, so a 400 is classified **before** any `provisioned: false` is sent —
> an undefined-column 400 means the table **EXISTS and may be full** (503
> `SCHEMA_OUTDATED`), a genuine missing relation falls through to the caller's
> own `provisioned: false` which is the one case where that answer is **TRUE**,
> and a 400 that cannot be classified answers **502** rather than being folded
> into either.

> **THE WRITE-SIDE CONCEPT:** a row the table refused **ON CONTENT** is not a
> missing table, so the guard routes through the classifier this file already
> ships — `notProvisioned()`, which answers 400 `ROW_REFUSED` for a 23xxx, 503
> `NOT_PROVISIONED` for a real missing relation and 400 `UPSTREAM_REJECTED` for
> the third state — instead of answering 503 unconditionally and telling the
> operator to re-run a migration that is already applied.

**NEITHER IS A NEW DESIGN.** The write side is the helper shipped 2026-10-14.
The read side is **one branch that was already written this way** —
`mech_site_assets`, hand-written 2026-10-15 after fourth/H1 routed it, whose
own comment carries the reasoning: *"a compliance board for a refrigerant
registry that says 'no assets on file' while the table holds fifty of them"*.
`unreadableNotEmpty()` is that branch's logic named once.

### 2.2 THE POPULATION — AND "151/57" WAS NEVER THE REAL FIGURE

`docs/b26-logs/guard_census.py` reconciles both counts rather than replacing
one with the other:

```
occurrences of the guard spelling, loose                      319
  ...of which ONE IS INSIDE A COMMENT at :19586               -1
real guard sites                                              318
  ...with a brace block                                       314
  ...brace-less, returning a VALUE to a caller                  4
      :11339 return { missing: 'table' }
      :17039 return { provisioned: false, providerId: null }
      :18005 return { unreadable: 'NOT_PROVISIONED' }
      :18811 return null
```

**The suite's own 6-line-window classifier reported 57 raw-503 and 151 raw-200,
and BOTH figures are one too high, for two different reasons:**

* **57 = 56 + the COMMENT at `:19586`.** Six lines below that comment are the
  words *"503"* and *"NOT_PROVISIONED"*, so the population counter classified
  **an occurrence of the guard shape inside a comment describing the guard
  shape** as a raw-503 guard. **This repo's named b17 defect — an assertion
  satisfied by a comment about the code it is checking for — recurring in a
  population counter rather than in an arm.**
* **151 = 150 + the brace-less closure guard at `:17039`**, which returns
  `{ provisioned: false, providerId: null }` to a caller and never touches
  `res`. Pulled in by the five-line window: **window bleed, the cause b24
  named in the sweep classifier, here in a different tool.**

### 2.3 WHAT WAS CONVERTED, AND WHAT WAS HELD WITH A REASON

```
PLANNED  READ  150        PLANNED  WRITE 43        HELD 20
```

Every hold is printed by `docs/b26-logs/convert_sibling_guards.py` with its
reason — **no silent cap, because a silent cap reads as "covered everything"**:

| n | class | why it was held |
|---|---|---|
| 11 | RAW503 | the branch **already reads the body and discriminates** — the class `api/sd-data.js:19596` says was left alone on purpose. `:8172 :8955 :9987 :11222 :11463 :11662 :11966 :12043 :12236 :12294 :15848` |
| 6 | OTHER | answers neither a raw 503 nor a raw 200. `:10303 :10491 :10847 :11825 :15429 :16290` |
| 2 | RAW503 | **the body was ALREADY CONSUMED upstream** (`:3349` json, `:18020` untraceable) — the exact defect recorded at `api/sd-data.js:19628`, where the first write-side rollout broke five such sites |
| 1 | BOTH | `:3668` answers **both** a raw 503 and a raw 200 — two answers in one branch is a per-branch judgement |

**THE PRE-READ CHECK IS THE WHOLE SAFETY ARGUMENT.** `:19628` records that the
first draft of the write-side rollout broke five call sites that had already
done `await r.json()` — the helper's own `r.text()` got `''` and reclassified a
genuine 404 as UNCLASSIFIABLE, *"turning one wrong diagnosis into a different
wrong diagnosis"* — and its conclusion was **"a bulk edit is safe exactly as
far as the property the script checked, and the script checked INSIDE the
branch and not what came before it."** So every candidate here is checked from
its `= await fetch(` **assignment** forward, and any body read of that variable
in that window sends the site to HOLD.

### 2.4 THE CALLER KEEPS ITS OWN LITERAL, AND THAT IS WHY

The read conversion **inserts one line** and leaves the existing
`res.status(200).json(...)` untouched. Measured reason: the 150 sites send
**21 distinct 200-shapes** — `data: []`, `data: null`, `board: null`,
`wip: null`, `worksheet: null`, `programs: []`, `coverage: {...}`,
`scoped_projection: !broadStaffRead`, `summary: opAudit.summarise([])` and more.
A helper that sent the answer itself would have had to flatten all 21.

```
200-shape count   157 -> 157   (MUST NOT CHANGE)
NOT_PROVISIONED    86 ->  43   (falls by exactly the 43 write conversions)
```

### 2.5 THE REAL FINDING: THE ROUTED ONE-LINE FIX WAS **NOT SUFFICIENT**

Arm **C1** of `tests/sd_data_not_provisioned_misclass.js` has been **RED ON
PURPOSE since 2026-10-17** and was routed to hank in those words:

> *"THE SAME ONE-LINE FIX AS A1, one guard earlier: route it through
> `notProvisioned(res, existingR, <the same message>)`. `notProvisionedDecide()`
> needs no change."*

**b26 routed exactly that guard through exactly that helper — and C1 STAYED
RED.** Because `notProvisionedDecide()` itself folds 42703 into
`NOT_PROVISIONED`: its missing-relation test is a bare `does not exist`
substring, and a Postgres 42703 message is **literally** *"column
alf_op_audits.reviewed_by does not exist"*. **The routed fix was right about the
call site and wrong about where the defect was, and only DRIVING it showed
that.**

Repaired in **one** place for every call site at once, and **the order is the
whole fix** — after the broad test the arm would change nothing:

```js
if (r.status === 400 && (pgCode === '42703' || /undefined_column/i.test(raw))) {
  res.status(503).json({ error: { code: 'SCHEMA_OUTDATED', message: … } });
  return;
}
if (r.status === 404 || /relation .* does not exist|PGRST205|does not exist/i…
```

Same code and same 503 as the read side, on purpose: **one wire-level name for
one condition**, so a client cannot see the same database state under two names
depending on which verb it used.

**C1 IS NOW GREEN. The suite is 16/16, exit 0** — it was 15/1 before this batch
and 12/2 when the arm was written.

### 2.6 TWO MEASUREMENT-TOOL DEFECTS, BOTH FOUND BY AN ABLATION

**(a) P5 could no longer name its own subject.** It tested
`/notProvisioned\(\s*res\s*,/` over the **whole** `alf_op_audits` branch. The
conversion added a **second** such call to that branch, so with hank's upsert
call reverted in the ablation copy, **A1 went RED and P5 STAYED GREEN** —
satisfied by the other call. A precondition that names *"the fix"* is worthless
once two fixes are in scope and it matches either. Narrowed to the response
variable `w`, which is a property of the call site rather than of the helper's
name. **Fifth measurement-tool defect in four batches; second in this one file.**

**(b) The new suite's ablation mutated the WRONG BRANCH.** It did
`src.replace(INSERT, '')` file-wide. The inserted line is **byte-identical at
all 150 converted sites**, so it removed the **first** one — a branch thousands
of lines from the subject — and would have reported R1 and R3 green while the
thing the suite claims to ablate was untouched. **An ablation that mutates a
different instance of the same pattern is a control that proves nothing and
reads as one that proves everything.** Caught by the readback guard b24 paid
for, firing for a different reason than it was written for. Now scoped to the
branch, with the occurrence count asserted to fall by **exactly one** and the
subject branch asserted clean.

**(c) And the suite's population counter would have under-reported the
repair.** Its classifier tests `notProvisioned(` then `provisioned: false`; a
converted read branch contains **both**, so all 150 would still have counted as
`raw200` — *"151 guards still raw"* while 150 were protected. A population
figure that cannot see the repair is a stale document number one layer in.
`unreadableNotEmpty(` is tested first now.

### 2.7 THE NEW SUITE AND ITS ABLATION

`tests/sd_data_read_unreadable_not_empty.js` — **12 arms, exit 0**, subject
`alf_op_audits` read (**Tier A**, append-only, and its 200-shape carries an
extra `summary` field, so it also demonstrates the caller-keeps-its-literal
property). Four states, and they must be **four different answers**:

```
42703        -> 503 SCHEMA_OUTDATED        the table exists and may be full
404          -> 200 provisioned: false     TRUE here, and only here
400 PGRST100 -> 502 UPSTREAM_UNCLASSIFIED  "could not tell" is a third state
400 42P01    -> 200 provisioned: false     byte-identical to the 404, correctly
```

**R5 asserts the answers are really distinct**, because four green arms could
otherwise be four copies of one answer. **A1 ablates the inserted line in a
copy of `api/` and requires R1, R3 and P3 to go RED while R2 STAYS GREEN** —
R2 green in both legs is what makes R1 and R3 attributable, since a mutation
that broke the whole branch would take R2 with it.

**THE TRADE IS NAMED RATHER THAN DISCOVERED:** a malformed-filter 400 caused by
a bug in `api/sd-data.js` used to render as an empty board and now renders as a
502. That is louder, and it is the point — it was always a defect and it was
always invisible.

### 2.8 THE BLAST RADIUS, MEASURED AS A DIFFERENTIAL

Every suite referencing `api/sd-data.js` driven **ALONE**, in a **disposable
worktree**, at HEAD **and** at HEAD~1:

```
230 suites, 198s
  GREEN       221
  RED_KNOWN     5     registered in docs/known-red-suites.json
  RED_NEW       4     -> of which exactly ONE is attributable to this change
```

| suite | HEAD~1 | HEAD | verdict |
|---|---|---|---|
| `tests/roofing_claim_gate_single_source.js` | **exit 0** | exit 1 | **MINE. Repaired — §2.9** |
| `api/_resources/extra-actions.test.js` | exit 1, *41 passed, 7 failed* | identical | red at baseline, **unregistered** |
| `tests/sairnlegacy_reservation_lock.js` | exit 1 | **byte-identical output** | red at baseline, **unregistered** |
| `tests/sd_data_write_attribution_three_apps.js` | exit 1, *17 passed, 3 failed* | identical | red at baseline, **unregistered** |

**WITHOUT THE BASELINE LEG, ALL FOUR WOULD HAVE READ AS REGRESSIONS FROM THIS
CHANGE.** Three were already red and nothing in the tree recorded them.

**NOT CLEAN, SAID PLAINLY:** this run is **JS only**. The `.py` half of the
tree was not driven here and is **not counted as clean**.

### 2.9 THE ONE REAL REGRESSION, AND THE ARM WAS WEAK BEFORE I TOUCHED IT

`tests/roofing_claim_gate_single_source.js`, arm *"each branch keeps its own
not-provisioned policy"*. It said *"the photo WRITE no longer refuses loudly"*
and tested `/NOT_PROVISIONED/` inside **`src.slice(i).slice(0, 1400)`**.

**The rf_claim_photos write branch is 5,470 characters.** The literal that
satisfied that window was the one in the **claim-existence guard** at the top
of the branch — **not** the photo write's own refusal 34 lines further down.
b26 routed that first guard through `notProvisioned()`: behaviour identical,
literal gone, arm red, **and the policy it names fully intact at three sites
(`:9850`, `:9854`, `:9871`).**

**So it was never testing what it said.** A fixed-size window is a guess about
how long the branch is; a balanced brace is a property of the branch. Repaired:
both halves sliced by balanced brace with an explicit overrun guard; the
assertion is on the **policy**, not one spelling of it; and **the arm's actual
subject is asserted for the first time** — that the read's degrade-to-empty-list
literal does **not** appear in the write branch. The two policies differing is
the whole point of the arm and was never checked.

**GREEN IN BOTH LEGS, which is the control that this is a repair and not a
loosening fitted to the conversion:** the repaired suite was copied into the
HEAD~1 worktree and passes **23/23 against the unconverted handler too**.

---

## 3. Item 4 — the known-red `tail` census

Routed at `SAIRN-handoff-cody-b22.md` §6.6 and unmeasured through b23, b24 and
b25. b22 found **one** row whose `tail` had been an arm list since b19 while
the suite's last printed line was its closing expected-red paragraph — so the
two **never** matched and the row reported `CHANGED`, which reads as *"a second
defect is hiding inside an entry that says this file is expected to fail"* when
**the entry** is the thing that is wrong. Its words: **"A ROW REGISTERED WITH A
TAIL THE RUNNER CANNOT PRODUCE IS WORSE THAN AN ABSENT ROW. Absent reads NEW
and gets looked at."**

What it did not do was ask how many others are like that, *"because it is not
cheap … and several of those suites WRITE WHEN RUN."*

### 3.1 THE METHOD

`docs/b26-logs/known_red_tail_census.py` drives **every registered suite
ALONE** and compares its real `out[-1]` against the stored `tail`.

* **The comparison is IMPORTED, not re-implemented** — `tools/known_red_check.py`'s
  own `_same_reason` (digit-normalised, lower-cased). A census using a
  different rule from the tool it audits measures a different thing and can
  neither confirm nor contradict it. This is *"a structurally different method
  for independence"* read the other way: for **agreement** with a tool, use the
  tool's own rule.
* **The tail is built the way the runner builds it** —
  `(stdout or stderr).strip().splitlines()[-1]`, per `tools/run_all_tests.py:942`.
* **It REFUSES to run without `--disposable-clone`.** Several registered suites
  write when run; it does not try to detect *"am I in a worktree"*, because
  that is a guess and the cost of being wrong is a mutated live clone.
* **Five verdicts, and "could not run" is not folded into either:**
  `TAIL_MATCHES`, `TAIL_UNPRODUCIBLE`, `GREEN_RECOVERED`, `SKIPPED`, `TIMEOUT`.

**RESULT: see `docs/b26-logs/known_red_tail_census.json`** — written by the
run, with every verdict, every stored tail and every observed tail. The
headline figures are in `SAIRN-report-cody-b26.txt`; they are not restated here
because a figure typed into two documents drifts in one of them.

---

## 4. Item 5 — the 85-candidate sweep, continued

**b24's caveat read first, and it is the reason this item was not done by
reading 85 files.** Quoted rather than paraphrased:

> *"The residual cause is named: window bleed. The assertion window is a line
> plus up to five continuation lines, so an extraction sitting next to an
> assertion gets classified as one. 1 of 4 is better than b23's 6 of 16 and it
> is not good."*

At 1-in-4 odds, reading 85 candidates yields ~21 real ones and ~64 wasted
reads. So the bleed was **measured and removed mechanically first**.

### 4.1 THE SWEEP AT HEAD

```
619 test files scanned · 94 candidates · 9 cody's · 85 NOT MINE
FILE-DERIVED 63 · UNTRACED 31 · RUNTIME 0
```

### 4.2 THE BLEED, MEASURED OVER THE WHOLE POPULATION

`docs/b26-logs/sweep_bleed_measure.py` reuses the sweep's own `SUBJECT_RE` and
`classify_subject` and adds **one** discriminator: the subject occurrence must
fall inside an assertion call's **balanced parenthesis span**. A window is a
guess about where a statement ends; a balanced paren is a property of the call.

```
1,442 FILE-DERIVED occurrences across 201 files
  BLED       1,060    74%   extraction next to an assertion, never a claim
  IN-ASSERT    382
```

**b24's "1 of 4" on a sample of four is consistent with a 74% bleed rate
measured over the whole population.**

### 4.3 AND A SECOND DISCRIMINATION, FOUND BY READING THE TOP CANDIDATE

> **THE CONCEPT:** an **ABSENCE** assertion over unstripped source text
> **cannot** be satisfied by a comment — a comment carrying the spelling makes
> it **FAIL**, loudly — so only **PRESENCE** assertions are candidates for this
> defect at all, and folding the two together halves the signal.

Found by reading `tests/sairnvet_formulary_source_honesty.js`, where four of
its subject lines are absence assertions in the safe direction:
`region.indexOf('Verified</span>') === -1`,
`!/verified (database|record)/i.test(prompt)`,
`!/Verified calculation/.test(line)`, `src.indexOf(pair[1]) === -1`. **A
comment containing `Verified</span>` cannot make the first pass; it can only
make it fail.**

```
POLARITY of the 382 IN-ASSERT occurrences
  PRESENCE   264    <- the real work-list
  ABSENCE     73    <- SAFE DIRECTION, not this defect
  UNSURE      45    <- THIS TOOL COULD NOT TELL, a human must read these

WORK-LIST: 264 of 1,442 -- 18% of what the unsplit sweep reports
```

**`UNSURE` is a third state and is not folded into either.** Calling it
PRESENCE would inflate the work-list; calling it ABSENCE would hide a real one.

### 4.4 THE CONTROL, AND ITS FIRST SPELLING WAS WRONG IN BOTH DIRECTIONS

b24's four hand-read verdicts are driven as **fixtures against the real files,
before any population figure prints**, and the run **refuses** if they do not
come out right. **It refused on the first attempt, which is the control
working.** Two of the four are not about bleed at all:

* `sairncode_pt_gp_modifier.js:333` was expected IN-ASSERT because b24 read it
  as the one **REAL** finding — and **b24 also REPAIRED it, in the same batch,
  in its §4.1**. The file strips comments there now and line 333 is a comment.
  **A FIXTURE ENCODING A DEFECT THAT WAS FIXED BY THE DOCUMENT IT WAS READ
  FROM** — discipline 8 landing on the control written to honour it, one batch
  later. Excluded and named, rather than expected.
* `sf_operator_payee_review_probe.js:41` is
  `assert.strictEqual(HTML.indexOf(startAnchor, i + 1), -1, …)` — an anchor
  **UNIQUENESS** guard, genuinely inside an assertion, which b24 called a false
  positive of the **sweep** on semantic grounds because the shape is
  **stronger** than the one being swept for. **"False positive of the sweep"
  and "bled" are two different things** and the first spelling conflated them —
  the exact collapse the tool's own header warns about. `IN-ASSERT` is the
  **correct** answer there, and it is why IN-ASSERT is a work-list and never a
  defect count.

Fixtures are **anchored on line content as well as line number** now: a fixture
that finds nothing at its line is a **third state** (the subject moved) and
must not read as agreement.

```
3/3 -- the reclassifier agrees with every hand-read verdict it is ENTITLED
       to decide, in BOTH directions: two BLED, one correctly IN-ASSERT.
```

### 4.5 THE SAMPLE READ — 6 files, 47 PRESENCE hits

| file | judged | real candidates | correct as written |
|---|---|---|---|
| `tests/sairnvet_formulary_source_honesty.js` | 5 | 5 | 0 |
| `tests/base_prompt_single_source.js` | 8 | 4 | 4 — the `literal` arms assert on a prompt string extracted from the app; **the subject genuinely IS text** |
| `tests/sairnbuild_wip_percent_complete.js` | 10 | 10 | 0 |
| `tests/sairnlaw_citation_rule.js` | 8 | 8 | 0 |
| `tests/material_risk_engine.js` | 8 | 7 | 1 — `:192` asserts a specific **comment** is present, on purpose |
| `tests/run_rate_limit_race_probe.js` | 8 | 7 | 1 — `:145` asserts a **warning comment** exists, on purpose |
| **total** | **47** | **41** | **6** |

**41 of 47 — 87% — against b24's 1-of-4 (25%) on the unsplit FILE-DERIVED
class.** *Real candidate* here means **the assertion could be satisfied by a
comment**; it is **not** a confirmed defect. b24's standard holds: a confirmed
one needs an ablation.

### 4.6 ONE CONFIRMED BY ABLATION

`tests/sairnlaw_citation_rule.js:105`:

```js
assert.ok(/function citatorFetch\s*\(/.test(src), 'citatorFetch is gone');
```

In a **disposable worktree**, the real function was **renamed** — so the
definition is genuinely gone — and **one comment** was planted carrying the
exact spelling: `// b26 ablation: the old code used to be \`function citatorFetch (\` here.`

```
definitions of the ORIGINAL name left in the file : 1   <- and it is THE COMMENT
  ok   citatorFetch exists and is how a real citation is retrieved
```

**The arm whose whole job is "citatorFetch exists" passed with the function
gone and only a comment carrying its name. CONFIRMED green-but-worthless.**

**THE HONEST MITIGATION, said rather than omitted:** a *sibling* arm —
*"mtVerifyCitations still exists and still reaches the real citator"* — **did**
go red, so the file as a whole noticed the rename. The defect is that **this
arm** did not, and nothing about reading it reveals that. The worktree app was
restored (`git checkout -- sairnlaw.html`).

---

## 5. What is NOT done

* **No live endpoint check and no live render.** Every verification in items 2,
  3 and 5 is source-level or in-process. Nothing here establishes behaviour
  against a real Supabase or a real browser.
* **The `.py` half of the tree was not driven** in §2.8's regression and is not
  counted as clean.
* **The 20 held guards are not converted**, each with a printed reason. They
  are per-branch judgements, not a backlog remnant.
* **The 4 brace-less closure guards** (§2.2) are not converted: they return a
  value to a caller rather than answering `res`, so converting them means
  changing a return contract and every caller.
* **223 of the 264 PRESENCE sweep hits are unread**, and **none of the 41 read
  as real candidates is ablated** except the one in §4.6.
* **The 45 UNSURE polarity hits are unresolved** — that is what the third state
  is for.
* **Three red-and-unregistered suites** found in §2.8 were registered, not
  diagnosed.
