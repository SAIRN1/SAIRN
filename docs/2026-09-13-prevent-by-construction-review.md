# Prevent-by-construction — a design review, starting with the ledger

**2026-09-13 (Hank).** Item 41. A review, not a build. Nothing in
`api/_lib/ledger.js`, `api/ledger.js` or `sql/ledger_schema.sql` has been
changed.

The question as posed: **could item 6's balance checker be redesigned so an
unbalanced entry cannot even be submitted, rather than being caught after?**

Short answer: **yes for the shape most entries actually have, no for the general
case, and the reason is arithmetic rather than effort.** The rest of this is
what that distinction costs and what to do about it — plus four other places on
this platform where the same question has a better answer than the current one.

---

## 1. The ladder, and where the ledger already sits

Shingo's poka-yoke distinction, which is the useful part of the idea:

| Level | What it does | Ledger today |
|---|---|---|
| **Elimination** | the bad state cannot be represented | `reversalOf()` — see below |
| **Prevention / control** | the bad state is representable but cannot proceed | the DB's `ledger_lines_one_side` CHECK |
| **Detection at source** | caught at the moment of entry, before anything acts on it | **`validateEntry()` — this is where the balance rule lives** |
| **Detection after the fact** | found later by a sweep | not used here |

**The balance rule is already at detection-at-source, which is the good half of
the ladder.** `api/ledger.js:168` validates before any write, and the header is
written as `draft`, the lines next, and `status: 'posted'` only after both
succeed (`api/ledger.js:229–275`). A failed line write leaves a visible draft
excluded from the trial balance, not a half-posted entry. That ordering is
itself a construction-level control and should be credited rather than
refactored away.

**And the codebase already contains the exact pattern being asked for.**
`reversalOf()` builds the mirrored entry itself — sides swapped, amounts
unchanged, explicitly *"built here rather than left to a caller so the mirror
cannot be got subtly wrong."* A reversal of a balanced entry **cannot be
unbalanced**; there is no input by which a caller could make it so. That is
elimination, it is already shipped, and it is the model for everything below.
The pattern is present; it just was never applied to entry *creation*.

---

## 2. What elimination would look like for entry creation

### 2.1 The transfer constructor — it does work, and here is why

Today a caller hands over an array of lines, each with an account and one side,
and the engine adds the two columns up and compares. Imbalance is representable
by construction and refused by inspection.

The alternative is to accept **transfers** rather than lines:

    entryFromTransfers({ today, entry_date, memo, transfers: [
      { debit_account: '6010', credit_account: '2130', amount: 400.00 },
      { debit_account: '6010', credit_account: '2110', amount: 600.00 },
      { debit_account: '6010', credit_account: '1010', amount: 4000.00 }
    ]})

Each transfer contributes **the same cents to both totals**. The sums are
therefore equal for any input whatsoever — not "checked and found equal",
**incapable of being unequal**. There is no `problems` entry to write, because
there is no state to describe.

That payroll example is the real test of whether this is useful, and it passes:
one debit against three credits expresses exactly as three transfers. **Any
entry with a single account on one side decomposes uniquely**, and reading the
54-record register and the chart of accounts, that is what almost every entry on
this platform is.

Two honest consequences:

- **The constructor must aggregate by account.** Naive expansion of the example
  gives six lines (three separate debits to `6010`); the entry a person expects
  has four. Aggregation is the correct behaviour and it is a real difference
  from what the caller literally typed, so it belongs in the function's own
  documentation, not in a reviewer's head.
- **It changes the shape of an error, not just its presence.** A caller who
  types the wrong *amount* still gets a balanced, wrong entry. **This prevents
  imbalance; it does not prevent being wrong.** Nothing in this review should be
  read as saying otherwise.

### 2.2 Where it stops, and it stops hard

An entry with **several accounts on both sides** — m debits and n credits — has
**no unique transfer decomposition.** Debit A 100 and B 50 against credit C 120
and D 30 can be written as (A→C 100, B→C 20, B→D 30) or as (A→C 90, A→D 10,
B→C 30, B→D 20), and the ledger cannot tell which pairing the accounting
actually means, because in general it means neither. Forcing a caller to pick
one invents a relationship the transaction does not have, and that invented
pairing would then be stored and later read as fact.

**So the line-based path has to stay.** The recommendation is therefore not
"replace `validateEntry`" but:

> **make the constructor the only path that can reach `postable`, and let the
> raw line array reach `draft` only** — with the general m:n case an explicit,
> named opt-in rather than the default door.

That is a change to the API contract and is flagged as a decision in §5.

### 2.3 The option to refuse: the auto-balancing plug line

The obvious "make imbalance impossible" trick is to let the caller supply n−1
lines plus a plug account and have the engine compute the last line. Imbalance
becomes unrepresentable.

**Recommend against, firmly.** It prevents the *symptom* and lets the *error*
through — a mistyped amount silently becomes a posting to a suspense account
that balances perfectly and is wrong. This platform already has a name for that
shape: it is a fail-open, and the register's two `critical` records are both
fail-opens. **A poka-yoke that converts a loud refusal into a quiet wrong answer
is worse than the check it replaced.**

### 2.4 The database trigger — worth doing, but it is not elimination

`api/_lib/ledger.js`'s header already names this as the next step and is right
that a Postgres CHECK cannot span rows. Worth being precise about what it buys
and what shape it has to take:

- **What it buys:** it converts *"no code path writes an unbalanced entry"* into
  *"the database refuses one."* Today's guarantee holds because one endpoint is
  the only writer. A future writer — another app, a migration, a support script
  — inherits nothing. That is control, not elimination, and it is the more
  durable of the two.
- **The shape is constrained by the existing write order, and this is easy to
  get wrong.** The three writes are three separate HTTP calls, so there is no
  transaction to defer a constraint trigger to. A deferred trigger on
  `ledger_lines` would fire at the end of the *lines* call, when the entry is
  still legitimately a draft. **It has to fire on the status flip instead** —
  `after update of status on ledger_entries when (new.status = 'posted')`,
  summing `ledger_lines` for that `(license_hash, entry_id)` and raising if the
  two sides differ. That also makes the rule exactly as narrow as it should be:
  drafts are allowed to be unbalanced, posted entries are not.
- **`ledger_lines` has no foreign key to `ledger_entries`** — stated plainly in
  the schema's own comment — so an orphan line is representable today and the
  trigger would not see it. Named here because a trigger that makes the balance
  rule feel closed while orphans remain possible is the kind of partial
  guarantee that gets quoted as a whole one.

### 2.5 The option that looks like prevention and is a bad trade

Replacing `debit`/`credit` with a single signed `amount` would eliminate three
of `validateLine`'s seven checks outright — both-sides, neither-side, and
negative — because those states stop being representable.

**Recommend against.** It would give up `ledger_lines_one_side`, a constraint
**the database actually enforces today**, in exchange for deleting three cheap
in-process checks; and it contradicts the engine's own stated position that *"a
negative debit is not a credit in any ledger a reader would recognise."*
Prevention that spends an enforced guarantee to buy an unenforced one is a
downgrade wearing the right vocabulary.

---

## 3. The same question, elsewhere — four real ones

Each row is a defect this platform actually had, not a hypothetical.

| The defect | Today's control | By-construction alternative | What becomes unrepresentable |
|---|---|---|---|
| **Fail-open gates** — `if os.path.isfile(tool): run_check()`; the push gate once disabled 9 of its 10 checks this way (a `critical` register record) | reviewers noticing the `if` | a **manifest of required checkers**; the gate refuses to start when any listed file is absent | "skipped" rendering as "passed" — there is no skip branch to take |
| **Sabotage controls that no-op** — 21 of 37 never verify their own sabotage landed; `src.replace(anchor, …)` silently does nothing when the anchor rots | each probe remembering to assert | one `mutate(src, anchor, new)` helper that **raises** when the anchor is absent, and no probe calls `str.replace` directly | a silent no-op mutation |
| **The `app_id` allowlist** — three live apps 400'd silently in 2026-07-26, again for SAIRNsenior; and today it carries three ids (`sairnfuneral`, `sairnhr`, `sairnacc`) whose apps exist only under `archive/` | a hand-maintained literal list plus a Guardian check | **derive the list** from the same app map Guardian already treats as the source of truth | drift between the allowlist and the apps |
| **Float totals as the only readable output** — `invariant_runner.js` compared `debit_total`, a float, and produced a wrong conclusion about the engine (item 13) | `debit_total_cents` added alongside, additively | make the float a **`formatMoney()` display call** rather than a field, so there is no float on the object to compare | a consumer comparing money as a float |

A fifth, smaller and worth naming because it burned a whole session: **CRLF
phantom drift**, three false alarms on 2026-09-03. By-construction answer: one
comparison helper that normalises line endings, so a raw byte compare is not the
convenient path.

---

## 4. When prevent-by-construction is the wrong answer

Three cases, all of which appear above, stated together because the pattern is
easy to over-apply once it has a name:

1. **When the prevention hides the error** — the plug line (§2.3).
2. **When it spends an enforced guarantee to buy an unenforced one** — the
   signed-amount swap (§2.5).
3. **When the guarantee is partial and reads as total.** The transfer
   constructor makes imbalance impossible for 1:n entries and does nothing for
   m:n. That is a fine outcome — but if both paths return the same object, every
   later reader will assume the guarantee is universal. **The response should
   name which path built the entry.** This is disciplines §7 directly: a
   property proven on one case is not proven on another that merely looks the
   same, and Ariane 5 lost a vehicle to correct, faithfully-copied software
   re-used in a context nobody re-qualified.

---

## 5. Sizing, and the one decision

| Phase | What | Size | Breaking? |
|---|---|---|---|
| **A** | `entryFromTransfers()` + tests, exported alongside the existing four | **S** | No — purely additive, all 200 lines of `ledger.test.js` keep passing |
| **B** | the status-flip balance trigger in `sql/`, shipped NOT RUN and degrading honestly like the other 29 | **S** | No |
| **C** | narrow the `postable` path so raw line arrays reach `draft` only, with an explicit opt-in for m:n | **S** | **Yes** |

**The decision is C.** A and B are strictly additive and can be built on the
existing evidence. C changes what an existing caller may do, and the m:n opt-in
means somebody has to decide how visible that door should be — an opt-in nobody
notices is the line-based path with extra steps.

---

## 6. What this review does NOT claim

- **Nothing is built or changed.** The engine, the endpoint and the schema are
  as they were.
- **No defect is asserted in the ledger.** `validateEntry` is correct and its
  balance decision has always been on integer cents; §1 says so explicitly. This
  is a question about where a guarantee lives, not a bug report.
- **The transfer constructor prevents imbalance only.** A balanced entry with
  the wrong amounts is untouched by all of this.
- **The trigger in §2.4 has not been written or run** against the live database,
  and the orphan-line gap it does not close is named rather than left implied.
- **§3's four rows are diagnoses, not scheduled work**, and two of them sit
  inside other sessions' active claims.
