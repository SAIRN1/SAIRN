# Scoping: condition number — are the financial formulas themselves ill-posed?

**Written 2026-09-13 (Fourth).** Item 50, scoped before anything is built. The
question is deliberately **independent of whether the code is correct**: every
line examined here computes exactly what it says it computes, `node --check` is
clean, and the invariant runner reports these engines stable. The question is
whether the *formula* amplifies the uncertainty already present in its inputs.

Every figure below was produced by driving the **real exported functions** —
`wip.portfolio()` and `pq.bondingCapacity()`, wired together the same way
`api/sd-data.js` wires them — not by re-implementing the arithmetic. The
measurement scripts are named at the end.

---

## The short answer

**Three findings, and the middle one is the honest correction to the hypothesis
I started with.**

1. **`wip-accounting.jobWip`'s `over_under` is structurally ill-conditioned, and
   `position` flips on the smallest change the database can store.** Real, live,
   and not fixable by more precision.
2. **The bonding chain is NOT ill-conditioned in general — measured κ is 0.4 in
   the middle of the range.** It degrades to κ ≈ 656 only as the book approaches
   the surety's aggregate limit, which is exactly where the answer is acted on.
   **Conditioning here is a property of the OPERATING POINT, not of the
   formula**, and nothing reports which regime a given answer came from.
3. **Every other money formula in this family is well-posed, and the reason is
   the useful part: their inputs are RECORDED AMOUNTS, not estimates.** There is
   exactly one estimated input in the whole family — `pct_complete` — and every
   ill-conditioned result traces back to it.

**Integer cents does not help with any of this**, which is worth stating because
it is the instinctive fix. The cancellation here is exact in arithmetic. What is
lost is not bits; it is *significant figures relative to the input's own
uncertainty*, and an exactly-stored estimate is still an estimate.

---

## 1. `over_under` — a small difference of two large numbers, by construction

`api/_lib/wip-accounting.js:300`

    out.earned     = money(contract * out.pct_complete / 100);
    out.billed     = out.requested_total;
    out.over_under = money(out.billed - out.earned);
    out.position   = out.over_under > 0 ? 'over_billed'
                   : (out.over_under < 0 ? 'under_billed' : 'level');

Over/under billing is **defined** as the gap between two figures that are
supposed to track each other. The result is near zero whenever the job is being
billed correctly — so the operands are always nearly equal and always large. That
is the textbook ill-conditioned subtraction, and here it is not an accident of
implementation but the meaning of the field.

**Measured, $8,000,000 contract, perturbing `pct_complete` by 0.01 — one tick of
`numeric(5,2)`, the smallest change `sql/sairnroofing_draws_schema.sql:76` can
store:**

| `pct_complete` | `earned` | `over_under` | `position` |
|---|---|---|---|
| 81.98 | 6,558,400 | **+1,600** | over_billed |
| 81.99 | 6,559,200 | **+800** | over_billed |
| 82.00 | 6,560,000 | **0** | **level** |
| 82.01 | 6,560,800 | **−800** | under_billed |
| 82.02 | 6,561,600 | **−1,600** | under_billed |

**One storage tick is $800 of `over_under`, and `position` crosses
over_billed → level → under_billed inside three of them.** The relative condition
number, measured with the same 0.01 step:

| `over_under` | κ |
|---|---|
| 0 (`level`) | **infinite** |
| −40,000 | **165** |
| −80,000 | 83 |
| −160,000 | 42 |
| −640,000 | 11 |

κ is worst precisely at the value the field exists to identify. **A contractor
who is billing correctly is the case this number is least able to describe.**

**And `pct_complete` is an estimate, which is what makes κ bite.** The engine's
own comment says so: the live basis is `contractor_stated_percent`, *"how a
roofing draw is really written — usually off squares installed"*. Its uncertainty
is nowhere stated, in the schema, the engine or the response. At κ = 165, an
estimate good to ±1pp puts ±$80,000 of uncertainty on a $40,000 figure — **twice
the magnitude of the number itself** — and the response reports it to the cent
with no band.

### A second, avoidable loss — but it is DORMANT, so it is not the headline

The other basis quantises before it multiplies:

    out.pct_complete = Math.round(Math.min(1, costToDate / estTotalCost) * 1000) / 10;   // :280

That rounds to 0.1 percentage points, which on a $2,000,000 contract quantises
`earned` to **$2,000 steps**. Measured: `over_under` reports **+500 over_billed**
where the exact figure is **−412 under_billed** — wrong sign and wrong magnitude
— and a $1,000 change in `cost_to_date` moves it by $2,000 with nothing in
between. Rounding an intermediate for display and then spending it as money.

**NOT CLAIMED AS LIVE.** Both production callers (`api/sd-data.js:5780`, `:6030`)
read draws from `rf_draws` and supply neither `cost_to_date` nor
`estimated_total_cost`, so `basis` is always `contractor_stated_percent` in
production and this branch is reached only from
`api/_lib/wip-accounting.test.js`. Verified by reading both call sites, not by
keyword. It is a real defect in dormant code, which is a different severity and
is recorded as one.

## 2. The bonding chain — the hypothesis was too strong, and the measurement says so

`api/sd-data.js:5818` derives committed backlog from the same `earned`, and feeds
it to a surety-facing capacity decision:

    backlog = Σ max(0, contract_value − earned)        // sd-data.js:5818
    rem     = money(aggregate - backlog)               // roofing-prequal.js:228
    candidate > rem  →  'over_capacity'                // roofing-prequal.js:245

Three successive subtractions ending in a binary answer to *"can this contractor
bond this job"*. The algebra predicts compounding amplification. **It does not
happen at a normal operating point**, and that is recorded here rather than
quietly dropped:

| aggregate limit | backlog | `remaining_aggregate` | κ (wrt `pct_complete`) |
|---|---|---|---|
| 20,000,000 | 1,440,000 | 18,560,000 | **0.4** |
| 10,000,000 | 1,440,000 | 8,560,000 | 0.8 |
| 5,000,000 | 1,440,000 | 3,560,000 | 1.8 |
| 2,000,000 | 1,440,000 | 560,000 | 11.7 |
| 1,500,000 | 1,440,000 | 60,000 | 109.3 |
| 1,450,000 | 1,440,000 | 10,000 | **656.0** |

**κ below 1 means the chain DAMPS its input error over most of the range.** A
first pass that stopped at the algebra would have reported a serious platform
finding that the measurement does not support, and the three-job book I measured
first showed amplification **×0.8** — the opposite of the hypothesis.

**What is true is narrower and still worth acting on: κ is a function of how full
the book is, and it explodes exactly where the decision is close.** Measured at
the near-limit point, the verdict flips on a 0.1pp difference in a
human-estimated percentage:

| `pct_complete` | backlog | `remaining_aggregate` | verdict |
|---|---|---|---|
| 81.90 | 1,448,000 | 1,442,000 | **over_capacity** |
| 82.00 | 1,440,000 | 1,450,000 | **within_capacity** |

Candidate value $1,450,000 against a $2,890,000 aggregate. **A tenth of a
percentage point of somebody's estimate of how much roof is on decides whether
the app tells a contractor they can bond a $1.45M job.** The answer is not wrong;
it is undetermined by the data, and it is presented as determined.

## 3. The controls — what is NOT ill-conditioned, and why that is the finding

A check that flags everything has found nothing. Three formulas in the same
family were examined and are **well-posed**:

- **`ledger.validateEntry`** — `difference_cents: debits - credits`
  (`api/_lib/ledger.js:203`). Formally κ is infinite at balance, exactly like
  `over_under`. It does not matter, because `debits` and `credits` are **integer
  cents from `Math.round(v*100)`** and carry no uncertainty to amplify. κ
  multiplies zero.
- **`roofing-billing.computeTotals`** — `balance = money(totals.total - paid)`
  (`:233`), then `balance === 0 ? 'settled'`. Same shape, same conclusion: total
  and paid are **recorded amounts**, not estimates, and `money()` rounds before
  the equality so float dust cannot reach the decision.
- **`care-charges.reconcileAgainstInvoice`** — `net_change` (`:150`) is built
  from `added − removed + Σ(to − from)`: **the deltas directly, never as one big
  total minus another.** This is the numerically stable formulation of the same
  question `over_under` asks badly, and it is already in the repo.

**The unifying rule, and it is the whole of item 50 in one line: conditioning
only bites where an input is an ESTIMATE.** Every ill-conditioned result above
traces to `pct_complete` and nothing else. The platform's money engines are
well-posed wherever they subtract amounts somebody actually recorded.

---

## What to build, and one thing NOT to build

**Do NOT build a condition-number scanner.** A tool to find
difference-of-near-equals sites whose operands are estimates would, on today's
evidence, find the one site this document already names. That is a checker
written to rediscover a known answer, and the platform has enough of those.
Re-run the scoping by hand when a second estimated input appears.

| # | Work | Size |
|---|---|---|
| 50a | `over_under` and `position` carry a **margin** derived from `pct_complete`'s stated precision, and `position` answers `too_close_to_call` rather than picking a sign inside it. Convention 4 applied to an estimate instead of a tolerance. | **S** |
| 50b | `remaining_aggregate` states which **regime** it is in — the κ table above is the input, and the alarm belongs where κ crosses ~10, not at the limit itself. Same shape as `--drift`'s warn-at-three. | **S** |
| 50c | Delete the `Math.round(ratio*1000)/10` quantisation from the `cost_to_cost` branch: keep the full ratio for `earned`, round only the reported `pct_complete`. Dormant today, wrong whenever it wakes. | **S** |

**And the one thing that is a product decision, not a tool's call, stated rather
than silently assumed:** *nothing anywhere captures how good `pct_complete`
actually is.* 50a needs a number for that and there is no honest source for one
in the repo — asking a contractor for a confidence band on a draw percentage is a
workflow change, not a code change. **The defensible interim is the storage
precision itself** (`numeric(5,2)`, so ±0.005pp), which is a *floor* on the
uncertainty and not an estimate of it — and 50a must say which of the two it is
printing, or it becomes a fabricated error bar, which is worse than none.

---

## What this scoping does NOT claim

- **No live customer impact is claimed.** The path is live in the deployed API
  and gated to management roles; whether any provisioned licence has real draws
  in `rf_draws` was **not** checked, and "the code path exists" is not "a
  contractor read this".
- **No uncertainty figure for `pct_complete` is asserted.** The ±1pp used above
  is an *illustration attached to a measured κ*, not a measurement of contractor
  estimating accuracy. Read the κ column; supply your own band.
- **Nothing was changed.** No engine was edited and no number in any document was
  corrected.

**Measurement scripts** (scratchpad, not committed — they drive the real exports
and are cheap to rewrite from the tables above): the κ sweep perturbs
`pct_complete` by ±0.01 and takes a central difference of the real
`portfolio()` → `bondingCapacity()` chain, replicating `api/sd-data.js:5817-5818`
line for line rather than re-deriving the backlog formula.
