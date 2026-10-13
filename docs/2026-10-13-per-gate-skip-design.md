# Per-gate named skip, with a required reason — DESIGN ONLY

Written 2026-10-13 by cc, batch b5, queue item 7. **No code this batch, as
instructed.** This is the design plus the measurement that justifies it; it is
not an implementation and nothing in the repo behaves this way yet.

---

## The measurement, before any proposal

`docs/BYPASS-LOG.jsonl`, read 2026-10-13:

| | |
|---|---|
| rows | **94**, from 2026-09-16 to 2026-10-13 |
| **`blanket: true`** | **80 (85%)** — `SAIRN_SEED_GATE=off`, which disables *every* check in the push |
| `blanket: false` | 14, all of them `check: seed-gate` |
| `check: ALL` | 80 |
| rows whose `reason` is anything beyond the boilerplate `"SAIRN_SEED_GATE=off ... the BLANKET form"` | **13** |
| rows naming a `command` | 63 |
| rows naming a `tip` | 13 |
| retractions | 1 |
| by session | fourth 46, hank 21, cc 14, cody 13 |

Two facts matter more than the total.

**First: the override that gets used is the one that switches off everything.**
80 of 94. Nobody chose to disable a specific gate; the only thing available was
the main switch, so the main switch is what the log records. Every one of those
80 pushes also skipped the credential scanner, the seed check, the register
feed, the Tier A gate and the derived-document check — none of which the session
had any complaint about.

**Second: 81 of 94 rows carry no reason a reader can act on.** The `reason`
field is populated, but with the mechanism (`"SAIRN_SEED_GATE=off in the
environment (prepush mode) — the BLANKET form"`) rather than with why the push
should proceed anyway. The field exists and means nothing, which is the exact
shape this platform already refused for the register's `not-citable`: *an escape
hatch with no note does not produce honesty, it produces a field that means
nothing.*

**And a third fact from this session, which changes the stakes.** The b5
permission work established by measurement that `SAIRN_SEED_GATE=off`
**cannot be stopped by a permission rule at all** — not as a deny (deny rules
match *past* a leading env assignment, so the assignment is never the thing
matched) and not by falling out of allow (documented to prompt; it ran with no
prompt). So the gate-side design below is not a belt-and-braces addition. It is
the only available control.

---

## The design

### 1. The variable names ONE gate, never all of them

```
SAIRN_SKIP=seed-gate  git push origin main
SAIRN_SKIP=tier-a     git push origin main
```

- The value is a **gate id** from a closed list the gates themselves publish.
  An unknown id is a **refusal**, not a silent no-op — an override that silently
  matched nothing is worse than no override, because the push proceeds and the
  log records a skip that did not happen.
- **No `all`, and no comma list.** Two gates to skip is two decisions, and
  somebody who needs five is in a situation that wants a human, not a longer
  variable. (A comma list is the blanket form wearing a different spelling; it
  is the first thing that will be asked for and it is the thing to refuse.)
- `SAIRN_SEED_GATE=off` is **retired**, not kept as an alias. An alias is the
  blanket form with extra steps, and 80 rows say that is what gets reached for.

### 2. The reason is required, and it is checked for substance, not length alone

```
SAIRN_SKIP=seed-gate SAIRN_SKIP_WHY="the seed files are mid-migration; Michael is running sql/x.sql now and the drift is the migration, not a defect" git push origin main
```

- **Absent `SAIRN_SKIP_WHY` → the skip does not apply and the push is refused.**
  Not "proceeds with a warning". The reason is the mechanism, not a courtesy.
- Minimum 40 characters, and **refused if it merely restates the mechanism**:
  a reason matching `/seed.?gate|skip|override|bypass|off/i` and nothing else is
  the boilerplate that produced 81 useless rows. The check is crude on purpose
  — it cannot tell a good reason from a bad one, and it can tell a reason from
  a label.
- The required shape is **what the gate would have refused, and why that is
  acceptable here** — so the row answers the question a reader has.

### 3. What the log row must carry

Every field below is already in the schema except `skipped_findings`, which is
the one that makes a row auditable rather than merely present:

| field | why |
|---|---|
| `at`, `session`, `tip`, `command` | already recorded |
| `check` | the gate id — never `ALL` |
| `reason` | the human sentence, validated as above |
| **`skipped_findings`** | **the findings the gate WOULD have raised, verbatim.** Without it, a row says a gate was skipped and not what was let through. This is the field that turns the log from a count into evidence |
| `blanket` | retained, and permanently `false` once the blanket form is gone — kept so the 80 historical rows stay readable |

### 4. The gate publishes its own id, and the list is derived

Each gate exposes `SKIP_ID` (e.g. `seed-gate`, `tier-a`, `register-feed`,
`external-files`, `derived-docs`, `scrutiny-ledger`). The dispatcher derives the
valid set by **importing the gates**, never from a hand-kept list — a closed
list typed in one place is the staleness this repo keeps paying for, and a new
gate nobody adds to it would be unskippable (annoying) or, worse, silently
skippable under a typo.

### 5. What must NOT be skippable at all

Stated as part of the design rather than discovered later. A skip is for a gate
whose *input* is temporarily wrong, not for a gate whose finding is
inconvenient:

- the **credential/secret scanner** — a leaked key is not a false positive
  somebody is in a hurry about;
- the **syntax check** — `node --check` failing means the push breaks the app;
- the **hook-integrity** check — skipping the thing that notices disarmament is
  the one skip that hides every other skip.

These three refuse `SAIRN_SKIP` with a message naming this list.

---

## What this design does NOT do, said plainly

- **It does not stop a determined session.** `python -c` can write anything,
  including the log, and the b5 permission work measured that a deny rule does
  not reach a subprocess's own file writes. This raises the cost of a blanket
  skip from one env var to a deliberate act, and makes the cheap path the
  honest one. It is not a boundary.
- **It does not reduce the number of overrides**, and should not be judged on
  that. 94 rows over four weeks across four sessions is not obviously too many;
  the defect is that 80 of them say nothing about what was let through.
- **It does not retroactively explain the 80 blanket rows.** They stay as they
  are. Back-filling a reason nobody recorded is how a CAPA form fills with
  guesses — the register already refuses that for old records and this follows
  it.

## The order to build it in, if approved

1. `skipped_findings` on the existing log row, under the existing blanket
   override. **One field, no behaviour change**, and it immediately makes the
   next blanket row auditable.
2. `SKIP_ID` on each gate plus the derived valid-id set, with a probe asserting
   an unknown id REFUSES.
3. `SAIRN_SKIP` + `SAIRN_SKIP_WHY`, both required, with the three unskippable
   gates refusing it.
4. Retire `SAIRN_SEED_GATE=off`. **Last**, and only once a week of rows shows
   the named form being used — retiring it first just means a session that
   needs a push blocked with no way through, which is how a gate gets edited
   instead of overridden.
