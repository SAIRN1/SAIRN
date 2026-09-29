# 29 criteria rules you can delete with nothing going red

**2026-09-29 (Cody).** A rule in `tools/assertion_label_shape_check.py` shipped
with a literal backspace where every `\b` should have been. It matched nothing,
ever — and the tool ran, its fixture lock passed, its control passed, and the
count it existed to move went to zero by a different branch. **It read as a
working rule from every angle.** It was caught only because an attribution
ablation counted the demotions and got 0 where it expected 2.

So `tools/dead_rule_sweep.py` asks the question directly, of everything.

## The method

For every module-level `NAME = re.compile(...)` in every tool in the report-only
registry, the pattern is replaced with `(?!x)x` — valid, unmatchable, and the
module still imports, so a failure is about the **rule** and not a `NameError`
somewhere else — and the tool's own evidence is re-run: its fixture lock if it
has one, else its declared control. **If neither turns red, the rule is dead to
its own evidence.**

The rewrite goes through `ast`, not text surgery. A pattern spans lines, carries
adjacent string literals and ends with flags, and a regex that edits regexes by
regex is how this defect class is born in the first place.

## The result

    70 tools, 156 module-level compiled rules
    CHECKED / UNIVERSE : 65 of 156 could be ablated against evidence the tool ships
                         36 exercised
                         29 DEAD
    COULD NOT TELL     : 91 -- the tool ships no fixture lock and no control

**The 91 are not clean.** "Nothing to ablate against" and "the rule is
exercised" are opposite findings, and a sweep that printed them the same would
be the defect it is looking for.

## DEAD does not mean WRONG, and the distinction decides the repair

It means **nothing the tool carries as proof of itself would notice the rule
vanishing.** A rule in that state can be deleted, mistyped, or shipped with a
literal backspace and every green light stays green.

Two repairs, and they are different answers:

- **add a fixture** — when the rule is load-bearing;
- **register a named limit** — when it is defensive, covers a shape that no
  longer occurs, or is a second spelling of something already caught. A named
  limit is honest. An unexercised rule presented as a criterion is not.

## FIXED — the three that were mine

| rule | what it does | fixture added |
|---|---|---|
| `CLAUSE_MARKER` | splits a label at `-- / so / because` and keeps the text before it as the claim | two arms: the exhaustive word **after** the marker must demote to ADVISORY; **before** it must stay CONFIRMED |
| `PARTITIVE_OF` | tells `only 3 of the 14 rows` (a subset) from `only the owner may write` (a universal) | two arms, one each way |
| `JS_BARE_CALL` | feeds the registered-limit line — *1811 bare-truthiness calls, of which **0** carry an exhaustive label* | four arms on the counter itself |

`JS_BARE_CALL` was the worst of the three. **That second figure is the only
thing separating a registered limit from an unreported gap**, and with the rule
neutralised the counter silently returns `(0, 0)` — which prints as *"while that
is 0 the limit costs nothing"*. The most reassuring possible wrong answer.

**Both `CLAUSE_MARKER` fixtures were written with the expectation backwards and
were corrected to what the rule correctly does.** That is discipline 1's *first*
kind of correction — the expectation was wrong, not the rule — and it is
recorded here because the discipline requires saying which kind it was. After:
**8 of 8 rules exercised, 0 dead.**

## ROUTED — the other 26, by file

Ownership is from the claim record, which is the only session attribution this
repo has. None is under a live claim; they are unrouted, not unowned.

| tool | dead rules | likely owner |
|---|---|---|
| `dependency_graph.py` | `REQ`, `ENV`, `BASELINE_RE`, `BASELINE_DATE_RE`, `SCHED_HEAD_RE`, `SCHED_DATE_RE` | never claimed |
| `metamorphic_check.py` | `_LINE_NO`, `_LEAD_NO`, `_LINES_LIST`, `_BYTES`, `_ENTITY_TOKEN`, `_FULL_LINE_COMMENT` | cody (2026-09-25) |
| `register_freshness_check.py` | `BARE_PATH`, `SHA`, `CELL_FILE`, `CELL_CALL`, `CELL_CAMEL` | never claimed |
| `advisory_lock_isolation_check.py` | `READ_RE`, `AGG_RE`, `DROP_RE` | never claimed |
| `accepted_risk_expiry_audit.py` | `ACCEPTED`, `CLOSED_STATUS` | never claimed |
| `register_feed_gate.py` | `TIER_A_ROW`, `REST_PATH` | fourth |
| `service_role_tier_a_gate_check.py` | `TIER_A_ROW` | never claimed |
| `overrun_inversion_scan.py` | `DISPLAYISH` | never claimed |

**`metamorphic_check.py`'s six are the ones to read first.** Its `blind_lock()`
is one of the best fixture locks in the repo — two hand-built fixtures, one
sensitive and one robust, run on the default path and refusing the measurement
when unlocked — and **six of its own normalisation rules are invisible to it.**
A strong lock over one half of a tool says nothing about the other half, which
is exactly the shape worth knowing about.

## What this does not establish

**Whether the fixture that saves a rule is any good.** One fixture that happens
to touch the pattern clears it here. That is
`tools/sabotage_control_check.py`'s question.

**Whether a dead rule matters on real data.** The evidence a tool *ships* is the
thing under test, deliberately: a rule defended only by the corpus is defended
by something that changes without anybody deciding.

**Re-run it rather than quoting these figures.**

    python tools/dead_rule_sweep.py
    python tools/dead_rule_sweep.py --tool <name>.py
