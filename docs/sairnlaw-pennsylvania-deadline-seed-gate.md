# Pennsylvania — deadline-seed source-availability gate

**Run 2026-09-18 (Fourth).** Verdict at §6: **BLOCKED on one legal question**,
and the question is narrow, nameable and not mine.

---

## 0. RESOLVED THE SAME DAY, AND THE GATE'S OWN PREMISE WAS WRONG (2026-09-18)

Read this before §2, because two things below are now out of date and one of
them was never true.

**PENNSYLVANIA WAS ALREADY SEEDED WHEN THIS GATE WAS RUN.** The gate says "DO
NOT SEED ON THE ASSUMPTION" and the open-work row said **NOT SEEDED**. Both
describe a state that had not existed since 2026-08-22. Counted across the seed
files on 2026-09-18: **eleven live `pa` rules** —
`sairnlaw_deadline_seed_pennsylvania` (2), `_state_appellate` (5),
`_state_discovery` (2), `_state_production` (1), `_subpoena_deposition` (1) —
and `COMPUTATION_STANDARDS.pa_rja_107` has mapped to `impl: 'frcp_6a'`, which
**rolls**, since Phase 3. So the gate was not standing in front of a decision.
**It was describing, as a thing to avoid, a thing already shipped.** That is
worth more than the legal question: a gate that re-derives a state from scratch
and never checks whether the engine already answers for it will keep producing
confident findings about the wrong repository.

**MICHAEL'S DIRECTION, 2026-09-18: the period ROLLS to the next day past a
weekend or holiday** — omit-and-continue. The engine's behaviour is unchanged;
what changed is that it is now **stated** rather than implied by an
implementation choice.

**IT IS RECORDED AS AN ASSUMPTION, NOT AS A CITATION, IN THREE PLACES:**

* `COMPUTATION_STANDARDS.pa_rja_107` — the full statement, at the standard.
* `JURISDICTION_COVERAGE.pa` — `direction: 'late'` with a `late_exposure`
  block, so it **rides on every Pennsylvania result** rather than living in a
  comment the person relying on the date will never open. This is the platform's
  **second** late-direction entry and the first that is an *assumption* rather
  than an unmodellable trigger; the note above that table says why a second one
  had to be a decision.
* `api/_lib/deadline-coverage-contract.test.js` — the arms that pinned
  `['al']` **failed on the way in**, which is what they were written for, and
  the expectation was changed with its reasoning attached.

**§2 BELOW STANDS AS THE STATEMENT OF THE AMBIGUITY.** Nothing in it is
retracted: no authority saying *"runs until the end of the next day"* for
Pennsylvania has been read, the reading comes from practice, and **if
omit-and-stop is right, all eleven rules return dates that are LATE.** The
lawyer's question is still open and still one sentence long. What changed is
that the exposure is now disclosed to the caller instead of being invisible.

**Why Pennsylvania.** Ohio, Michigan and Indiana were the three states with a
computation standard already in the engine, and all three are now gated. That
criterion is exhausted. The next one is population against source access, and
Pennsylvania is the largest unseeded state by a wide margin (~13M) with its
rules published free by the judiciary. **It has NO pre-built engine standard, so
this gate cannot claim the zero-engine-work position the last three had.**

---

## 1. Sources — and the rule everyone cites was RESCINDED

| Source | Location | Terms | Currency |
|---|---|---|---|
| Pa.R.J.A. 107, Computation of Time | `pacourts.us` / Pa. Bulletin vol. 53-46 | none | **adopted 18 Nov 2023, effective 1 Jan 2024** |
| 1 Pa.C.S. § 1908 | `legis.state.pa.us` | none | Statutory Construction Act of 1972 |

⚠ **THE RULE TEXT BELOW IS FROM CORNELL LII, NOT FROM THE JUDICIARY'S OWN PDF.**
Ohio's and Michigan's were downloaded and hashed; this one was not, and that is
a source grade down, the same shortfall recorded on Indiana. It must be read on
`pacourts.us` before any row is seeded.

**⚠ AND Pa.R.Civ.P. 106 — the rule every practice guide cites for Pennsylvania
time computation — HAS BEEN RESCINDED.** On 3 November 2023 the Supreme Court
extracted the rules of construction from the Civil Procedure rules, rescinding
**Pa.R.Civ.P. 101–104, 106–108 and 127–153** and adopting **Pa.R.J.A. 104–115**,
effective 1 January 2024. Rule 107 is the consolidation of former 106–108.

**THAT IS THE THIRD MOVED-CITATION TRAP IN THREE CONSECUTIVE STATES** — Ohio
Civ.R. 6(E) re-lettered to 6(D) in 2012 and still cited by secondary sources
fourteen years later; Indiana's mail extension at T.R. 6(G) and still cited as
6(E); now Pa.R.Civ.P. 106 rescinded outright and still the first hit. **A seed
row carrying a citation nobody re-checked is the recurring defect of this whole
series**, and it is now a standing check rather than three coincidences: read
the CURRENT rule set, not the rule number a search returns.

---

## 2. THE BLOCKER: Pennsylvania OMITS the day. Every other state ROLLS.

Pa.R.J.A. 107(b), verbatim:

> "Whenever the last day of any such period shall fall on Saturday or Sunday, or
> on any day made a legal holiday by the laws of this Commonwealth or of the
> United States, **such day shall be omitted from the computation**."

1 Pa.C.S. § 1908 uses the same words, and Rule 107's own note says it "reflects
the Court's prior use of 1 Pa.C.S. § 1908".

**THERE IS NO "RUNS UNTIL THE END OF THE NEXT DAY" ANYWHERE.** Compare the three
states just gated, all of which say it explicitly:

| State | Operative words |
|---|---|
| Ohio Civ.R. 6(A) | "the period runs until the end of the next day which is not a Saturday, a Sunday, or a legal holiday" |
| Mich. MCR 1.108(1) | "the period runs until the end of the next day that is not a Saturday, Sunday, legal holiday…" |
| Ind. T.R. 6(A) | "the period runs until the end of the next day that is not a Saturday, a Sunday, a legal holiday…" |
| **Pa.R.J.A. 107(b)** | **"such day shall be omitted from the computation"** |

**OMISSION AND ROLLOVER ARE NOT THE SAME OPERATION, AND THE ENGINE ONLY HAS
ROLLOVER.** Two readings of "omitted", and they differ in the direction that
matters:

* **Omit-and-continue** — the day does not count, so the period carries to the
  next day that is not omitted. **Equivalent to rollover.** This is how
  Pennsylvania practice treats it.
* **Omit-and-stop** — the day is removed from the period, so the period ends on
  the day before it. **EARLIER than rollover.**

If the second reading is right and the engine rolls forward, **the engine
computes LATE** — it returns Monday when the last day to act was Friday. That is
the direction that loses a filing, and it turns on one word.

**I CANNOT SETTLE IT FROM THE TEXT, AND THE TEXT IS WHAT THIS ENGINE IS BUILT
ON.** Pennsylvania's settled practice is extension, and that is almost certainly
the right answer — but "almost certainly, from practice rather than from the
rule" is precisely the standard this platform refuses to seed money and
deadlines on. It goes to the bundled lawyer's question (row 394) beside the
Illinois and Kentucky holiday questions.

**One sentence of confirmation from counsel unblocks the whole state.**

---

## 3. What Pennsylvania does NOT have, which is unusual and helpful

* **No short-period exclusion.** Rule 107 has no "when the period is less than
  N days, exclude intermediate weekends" clause at all. Ohio and Indiana both
  have one at seven days; Michigan has none either.
* **No clerk's-office-closed limb.** Ohio, Indiana, Michigan and Utah all carry
  one and none of them is modelled. Pennsylvania's absence removes a standing
  disclosure rather than adding one.
* **No emergency-order limb** of the Florida kind.

So once the omit-versus-roll question is answered, Pennsylvania is one of the
**simplest** rules in the series — which is exactly why the one ambiguity is
worth stopping for rather than working around.

---

## 4. What was NOT determined

* **The holiday list.** Rule 107(b) reaches "any day made a legal holiday by the
  laws of this Commonwealth or of the United States" — TWO sources, and the
  federal limb means a federal holiday is a Pennsylvania court holiday. Neither
  list was read here. **The union of two lists is also two chances for a
  governor- or president-proclaimed day**, the open limb every state has.
* **The service extension.** Whether Pennsylvania has an added-time-for-mail
  rule, and where it now lives after the 2023 extraction, was not determined.
  Given that the rescission moved 106–108 wholesale, the mail rule may also have
  moved, and citing the old number would repeat §1's trap.
* **The appellate rules** — Pa.R.A.P. not read, so appellate rows are out of
  scope, the same bound as Ohio, Michigan and Indiana.
* **Whether any engine change is needed.** If omit-and-continue is confirmed,
  Pennsylvania maps to the `frcp_6a` implementation with no short-period flag —
  the Michigan shape, and no new code. If it is not, the engine needs an
  operation it does not have. **The answer to §2 decides whether this is zero
  engine work or a new mechanism**, and that is the other reason not to guess.

---

## 5. Verdict

**GATED — BLOCKED.** Sources are official and free, and the rule is current to
1 January 2024. There is no short-period exclusion, no office-closed limb and no
emergency limb, which makes Pennsylvania structurally the cleanest state in the
series.

**It is blocked on one word.** Pa.R.J.A. 107(b) says a weekend or holiday last
day is "omitted from the computation" and never says the period runs to the next
day. The reading that matches practice is safe; the other reading makes this
engine compute LATE. **That is a lawyer's read, it is one sentence long, and it
unblocks a 13-million-person state.**

**Do not seed on the assumption.** Three states in this series have been blocked
on questions exactly this size, and the reason each was recorded rather than
worked around is that a deadline engine which is confidently wrong is worse than
one that refuses.

**⚠ THAT LAST SENTENCE WAS OVERTAKEN THE SAME DAY — see §0.** Pennsylvania was
already seeded when this was written, so "do not seed" was advice about a
decision that had been taken three weeks earlier. Michael directed the rolling
reading on 2026-09-18 and the assumption is now disclosed on every Pennsylvania
result rather than hidden. **The verdict this section renders is still the right
one about the SOURCES; it was wrong about the STATE OF THE REPO**, and the
correction runs in that direction.
