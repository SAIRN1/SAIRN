# TIER A REVIEW — hank's 400→503 `notProvisioned()` helper

**fourth / b22, 2026-10-15. Subject: the second half of `e9d9c8192620`.**

The b22 instruction named this as *"63 branches across 22 resources"* — my own
b21 figure. **hank re-derived it as 98 and that is also low. Measured at HEAD,
the population is 157, and the gap has a single named cause.** Everything below
prints the predicate, the raw count and the narrowed count, because a conclusion
carried without its raw figure is precisely what produced both earlier numbers.

Reproduce: `python <scratchpad>/np_population_b22.py` and
`python <scratchpad>/np_shapes_b22.py` (logs `np_population_b22.log`,
`np_shapes_b22.log`).

---

## 1. THE POPULATION, RE-DERIVED FROM SOURCE

`api/sd-data.js` at HEAD, **18,503 lines**. One predicate, applied to single
lines with comment lines excluded, so the buckets add up:

    (\w+)\.status === 404 \|\| \1\.status === 400

| bucket | what the branch does on a 400 | count |
|---|---|---:|
| **RAW** | every line matching the predicate | **331** |
| **A** | rewritten — `notProvisioned()` within 5 lines | **88** |
| **B** | **NOT rewritten** — `res.status(503) NOT_PROVISIONED` inline | **69** |
| **C** | `res.status(200) { ok: true, data: [], provisioned: false }` | **151** |
| | other handling | 23 |
| | A + B + C + other | **331** |

Plus **10** guards on **404 alone** that answer `NOT_PROVISIONED` — already
correct, not part of the population.

Independently, by call site rather than by guard
(`np_shapes_b22.py`): **89 `notProvisioned()` call sites, all 89 awaited, all 89
with control provably stopping afterwards, 0 that may continue.** The A=88 / 89
difference is one call site whose guard and call are more than 5 lines apart; the
two methods agree to within that.

**So the branches that answer 503 NOT_PROVISIONED on `(404 || 400)` number
157 — 88 through the helper and 69 still inline.** Not 98, and not 63.

### WHY hank's 98 — and it is a predicate, not carelessness

Counted by the **name of the response variable** in the guard, over the 157:

| variable | branches |
|---|---:|
| `r` | **99** |
| `existingR` | 10 |
| `w` | 7 |
| `cur` | 4 |
| `cr` | 4 |
| `sr` | 3 |
| `existingPhoto`, `jr`, `rr`, `exq` | 2 each |
| `sfoRows`, `wr` | 1 each |

**99 of the 157 are guarded on a response variable literally named `r`.** hank's
98 is within one of that figure. A predicate written as `r.status === 404 ||
r.status === 400` finds the 99 and is blind to the other 58, and nothing about
its output says so — it reports a population, not a sample.

**THIS IS THE SAME DEFECT I COMMITTED IN b19 AND IT IS NOW TWICE IN FOUR DAYS.**
Mine was "roughly twelve"; H1 re-ran my own command and got 63. hank's is 98
against 157. Both numbers were taken with a predicate narrower than the
population and then carried as the population. **The convention needs the clause
I proposed in b21 and one more:** print the command AND the raw count — and
**when a predicate names an identifier, say which identifier**, because
`r.status` reads like a shape and is actually a name.

---

## 2. THE HELPER ITSELF — SOUND, with one new misattribution inside it

`api/sd-data.js:18416-18447` (`notProvisioned` at `:18416`,
`notProvisionedDecide` at `:18429`). Four answers, and the split is the right split:

| input | answer |
|---|---|
| a preread body was passed | classify without touching the stream |
| 400 **and** pg class `23xx` | **400 ROW_REFUSED**, naming the 64 KB cap |
| 404, or the raw body matches `relation … does not exist\|PGRST205\|does not exist` | **503 NOT_PROVISIONED** with the caller's message |
| anything else | **400 UPSTREAM_REJECTED** — says the reason could not be classified, and explicitly **not** "run the migration" |

**The `preread` parameter is the part that deserves credit.** A `Response` body
is readable once, and five call sites do `await r.json()` *before* the guard.
Without `preread` the helper's own `await r.text()` returns `''` on a consumed
stream and every one of those five classifies a real 404 as unclassifiable — one
wrong diagnosis traded for another. Measured: **5 call sites pass a preread
body** (lines **2769, 2988, 3331, 3434, 8486**), and the suite's arm A8 drives
the read-after-consume case rather than just asserting the argument is present.

### F1 — `23xx` IS THE WHOLE INTEGRITY CLASS, AND ONLY ONE MEMBER OF IT IS THE ROW CAP

`notProvisionedDecide` (`:18431`):

```js
if (r.status === 400 && pgCode.slice(0, 2) === '23') { … 'most often for
  exceeding the 64KB row cap' … }
```

Class 23 is **integrity constraint violation** generally: `23505` unique
violation, `23503` foreign key violation, `23502` not-null violation, `23514`
check violation. **Only `23514` is the size cap** — `octet_length(data::text) <=
65536` is a CHECK. So a duplicate-id upsert collision (`23505`) or a missing
required field (`23502`) now tells the operator the record *"most often"*
exceeded a 64 KB row cap.

**This is a NEW misattribution created by the fix.** It is strictly narrower and
less damaging than the one it replaced — it does say the table exists, that
nothing was saved, and that re-running the migration will not help, all of which
are true for every `23xx`. But it names a specific wrong cause, which is the
defect class this whole change exists to end.

**Next step: branch on `23514` for the cap sentence** and give the rest of class
23 a sentence that names the real class (*"the database refused this record on
an integrity constraint (23505) — the table exists and nothing was saved"*). The
code already has `pgCode` in hand; this is a two-line change.

### F2 — `/does not exist/i` IS TESTED AGAINST THE WHOLE RAW BODY, INCLUDING ECHOED DATA

The 503 arm matches `does not exist` **anywhere** in `raw`, at any status.
PostgREST error bodies carry `message`, `details` and `hint`, and `details`
echoes offending values. A 400 that is genuinely about a value — `22P02 invalid
input syntax`, say — whose echoed value contains the words "does not exist" is
classified as a missing table and the operator is told to run a migration.

**Low probability, named because it is the exact shape being fixed.** It is also
the arm with the least evidence behind it: `PGRST205` and
`relation … does not exist` are specific; the bare third alternative
`does not exist` subsumes both and is what actually fires. **Next step: drop the
bare alternative** — `relation .* does not exist|PGRST205|column .* does not
exist|function .* does not exist` covers the real cases and cannot match a data
value.

---

## 3. F3 — 69 BRANCHES OF THE SAME SHAPE WERE NOT REWRITTEN

Bucket **B**: 69 branches still read

```js
if (<resp>.status === 404 || <resp>.status === 400) {
  res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: … } });
  return;
}
```

with **no body read before deciding** — the exact condition the commit says was
eliminated. Sampled and confirmed at lines **2239** (SAIRNfreedom data tables),
**2605** (supplier lead times), **4123** (slab lineage sync), **10129**
(SAIRNroofing settings), **18205** (SAIRNcode, via `scNotProvisionedMessage`).
Full list in `np_population_b22.log`.

**The commit's "nine branches were LEFT ALONE because they already read the body
and discriminate" does not describe these.** These do not read the body. They
are the other 58-plus of the 157 that the `r.status` predicate never saw, plus
the handful it saw and skipped.

**Next step, and it is mechanical:** re-run the rewrite with the predicate
widened to `(\w+)\.status === 404 || \1.status === 400`, taking the response
variable's own name from the match. The 69 line numbers are listed; each needs
the same `await notProvisioned(res, <resp>, <message>); return;` the other 88
got, and the five preread sites show what to do where a body was already
consumed.

---

## 4. F4 — THE 151 READ BRANCHES ARE A WORSE FOLD AND THE FIX DID NOT REACH THEM

Bucket **C**, 151 branches:

```js
if (r.status === 404 || r.status === 400) {
  res.status(200).json({ ok: true, data: [], provisioned: false });
  return;
}
```

(e.g. `:2573`, `:5120`, `:9027`, `:17995`.)

On a 404 this is a deliberate and reasonable product choice — an unprovisioned
table renders as an empty panel rather than an error. **On a 400 it is a silent
failure in the strict sense: `ok: true`, no error code, an empty list, and a
`provisioned: false` flag that asserts a cause the server did not establish.**
A malformed `select=`, a bad filter, a column PostgREST cannot find — every one
of them renders as *"there is no data"*.

**That is strictly worse than the wrong 503 this commit set out to fix**, because
a 503 at least tells somebody something happened. The 503 paths got a helper
with four answers; the read paths kept one answer for two causes.

**Next step: the same helper, with a fifth answer for the read case** — 404 keeps
`{ ok: true, data: [], provisioned: false }`; a 400 that is not a missing
relation answers `400 UPSTREAM_REJECTED` like its write sibling. **This is the
larger of the two remaining populations and it is not in anyone's open work.**

---

## 5. VERDICT

**The helper is the right mechanism and the `preread` parameter is the part that
shows it was reviewed rather than scripted.** The first draft broke five sites,
hank found it by reading two rewritten sites in context after the mechanical
pass, and said so in the commit message. That is the standard.

**The measurement around it is what does not hold.** The rewrite covered **88 of
157** branches of the shape it names, not 89 of 98; **69 remain** in the
identical un-read 503 fold; and **151 read branches** fold a 400 into
`ok: true, data: []`, which no part of this change addresses. **The cause of the
miss is one predicate anchored on the identifier `r`**, and the same mistake in
the other direction produced my own b19 "twelve".

**Routed to hank:** F1 (`23514` vs class `23`), F2 (the bare
`/does not exist/`), F3 (the 69), F4 (the 151 read branches). **F1 and F2 are
two-line changes inside the helper and should go first** — they are defects in
the thing 88 branches now depend on.
