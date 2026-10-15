# The 69 and the 151, classified — a count of a SHAPE is not a count of DEFECTS

**fourth / b23 item 3, 2026-10-15.** `api/sd-data.js` at HEAD, **18,770 lines**.
Routed to hank with `file:line`. **Every figure names the command; re-derive
anything you mean to quote, including out of this file.**

Reproduce: `python <scratchpad>/branch_census_b23.py` (log
`branch_census_b23.log`), `python <scratchpad>/body_read_b23.py`
(`body_read_b23.log`), `node <scratchpad>/branch_drive_b23.js`
(`branch_drive_b23.log`).

---

## 1. THE SHAPES, RE-COUNTED AT THIS HEAD

Predicate: a single line matching `(\w+)\.status === 404 \|\| \1\.status === 400`,
comment lines excluded. **332 guards** (b22 measured 331 at 18,503 lines; the
file has since grown).

| | b22 | b23 |
|---|---:|---:|
| **A** rewritten to `notProvisioned()` | 88 | **88** |
| **B** inline `503 NOT_PROVISIONED` | 69 | **70** |
| **C** `200 {ok:true,data:[],provisioned:false}` | 151 | **151** |
| other | 23 | **23** |
| total | 331 | **332** |

---

## 2. THE CLASSIFIER, AND WHY THIS IS THE RIGHT AXIS

**A fold is harmless exactly when the guarded request cannot return 400 for any
reason other than the table being absent.** PostgREST's 400s split by method:

* **WRITE (POST/PATCH/DELETE)** — class `23xxx` integrity violations. **`23514`
  is the 64 KB row CHECK every `sd_*` table carries**, plus `23505` unique,
  `23503` FK, `23502` not-null, and `22P02` invalid input syntax. All 400, none
  a missing table.
* **GET** — `PGRST100` (a query param that will not parse), `42703` (a column
  that does not exist), `22P02` on a filter **value**.

So each branch is classified on two **measured** facts: the HTTP method of the
`await fetch(...)` whose status it tests, and what that URL interpolates.
Branches whose fetch cannot be located are **UNCLASSIFIED**, never folded into
either verdict.

**AND THE FIRST VERSION OF THIS CLASSIFIER WAS WRONG, WHICH IS WHY THE NUMBERS
BELOW ARE NOT THE FIRST NUMBERS IT PRODUCED.** Its caller-influence test was
`'select=' in blob and '(' in blob.split('select=')[1][:40]`, which matched the
trailing `'), { headers }` of essentially every URL — it reported **68 of 151**
as caller-influenced. Caught by spot-reading `:5120` and `:3604`, both of which
interpolate nothing but the server's own `licHash`. Replaced with the thing that
actually makes a 400 reachable from outside: an interpolated value the **caller**
chose (`enc(payload…)`), distinguished from a **session**-derived one
(server-verified) and from **server-only**. **68 → 0 on class C.** Stated
because a predicate that inflates by punctuation is the b22 lesson arriving on
my own tool one batch later.

---

## 3. THE TRUE COUNTS

| class | branches | method | URL interpolates | verdict |
|---|---:|---|---|---|
| **A** | 88 | **88 WRITE** | 88 server-only | **FIXED.** hank's rewrite hit exactly the write class |
| **B** | **22** | WRITE | 22 server-only | ** REAL DEFECT, HIGH ** — `23xxx` reachable, answers "run the migration" |
| **B** | **13** | GET | **CALLER** | ** REAL DEFECT, MODERATE ** — `22P02` on a malformed caller id answers 503 |
| B | 33 | GET | server-only | not a caller-reachable defect; **untested** |
| B | 2 | — | — | **UNCLASSIFIED** — fetch not located, could-not-tell |
| **C** | **150** | GET | server-only | ** REAL BUT DEPLOY-REACHABLE, LOW ** — see §5 |
| C | 1 | GET | SESSION | `:3604`, same class, session-derived id |

### THE 22 HIGH ONES — `api/sd-data.js`

`2644, 3206, 3567, 4123, 4182, 4431, 4513, 4588, 8231, 9029, 9224, 10553,
10700, 10899, 11018, 11188, 11265, 11516, 11595, 13660, 13791, 14348`

**These are the same class hank already fixed 88 of.** Each guards a
POST/PATCH/DELETE, so each can receive a `23514` from the 64 KB row cap and
answer **503 NOT_PROVISIONED — "run the migration"** for a row the database
refused on content.

**TWO OF THEM ALREADY READ THE BODY FIRST** and so could discriminate with no
extra round trip: **`:3206`** (`var wr`, fetch at `:3179`) and **`:11018`**
(`var w`, fetch at `:11003`). Those two want `notProvisioned(res, w, msg,
prereadBody)` — the 4-argument form that already exists. The other **20** want
the ordinary 3-argument call.

### THE 13 MODERATE ONES — `api/sd-data.js`

`4786, 6119, 6475, 6646, 7036, 7139, 7452, 8312, 8483, 8951, 9075, 11242, 11886`

Each is a GET whose URL interpolates a **caller-chosen** value — e.g. `:7036` is
`sen_visits?license_hash=eq.<licHash>&visit_id=eq.` + `enc(payload.id)`. A
malformed `payload.id` yields `22P02` → 400 → **503 "run the migration"** for
what is actually a bad request. Lower severity than the 22 because no data is
mis-saved; it still sends an operator to Supabase for a client bug.

### THE 2 UNCLASSIFIED — `:13503`, `:17127`

The assigning `await fetch(` is not within 60 lines of the guard. **Reported as
could-not-tell, not as clean and not as a defect.** Somebody has to read those
two by hand.

---

## 4. DRIVEN, NOT ARGUED

`notProvisionedDecide` is not exported, so it was **extracted by text from the
shipped file** (18 lines) and run in a `vm` context — the same method hank's own
b12 suite adopted after an ablation showed a source grep could not see an early
return. Four inputs, the bodies PostgREST really returns:

| input | the helper answers |
|---|---|
| `400` + `23514` *(the 64 KB CHECK, a write refusal)* | **400 ROW_REFUSED** |
| `400` + `PGRST100` *(unparseable query param)* | **400 UPSTREAM_REJECTED** |
| `400` + `42703` *(column does not exist)* | **503 NOT_PROVISIONED** |
| `404` *(the table really is absent)* | **503 NOT_PROVISIONED** |

**So routing one of the 22 through the helper changes its answer on a `23514`
from "run the migration" to "the row was refused, most often the 64 KB cap" —
the exact fix, demonstrated on the real function rather than asserted.**

**AND IT CONFIRMS MY b22 F2 CONCRETELY:** `42703` — a missing *column*, not a
missing table — is classified **503 NOT_PROVISIONED** by the bare
`/does not exist/i` alternative. For an incomplete migration that advice is
defensible; it is still the catch-all doing it rather than a rule about columns.

**AND A CORRECTION TO MY OWN FIRST MEASUREMENT.** My first body-read detector
searched the lines **after** the guard and reported "reads the body first: YES"
for all eight samples — it was matching `code: 'NOT_PROVISIONED'` **inside the
answer**. Re-measured positionally (is there a `.json()`/`.text()` on that
variable **between** the fetch and the guard): **7 of 332 read first, 323 do
not, 2 have no locatable fetch.** hank b12 said "the nine branches that already
read the body and discriminate were LEFT ALONE"; measured, it is **seven**, and
four of the seven are the preread sites already wired into the helper.

---

## 5. THE 151 — MY b22 SEVERITY WAS OVERSTATED, AND THE RESIDUAL IS A DEPLOY RISK

**b22 called the 151 "a silent failure strictly worse than the wrong 503" and
"the largest un-owned population".** The shape claim stands. **The reachability
claim does not: 0 of the 151 interpolate a caller-chosen value and none guards a
write, so a caller cannot provoke a non-missing-table 400 on any of them.** The
corrected count of caller-reachable defects in class C is **0**, with one
session-interpolated sibling at `:3604`.

**WHAT IS STILL REAL, AND IT IS NOT CALLER-REACHABLE — IT IS DEPLOY-REACHABLE.**
Every one of the 151 is a GET carrying a `select=` list. A table that exists with
a **renamed or dropped column** answers `42703`/`PGRST204` as **400**, and these
branches render that as `{ok:true, data:[], provisioned:false}` — an empty panel,
no error, and a `provisioned:false` flag asserting a cause the server never
established. **That is a partial-migration failure mode, which is exactly the
state this platform is in most often**, and the helper already answers it
better (503, naming the migration).

**NEXT STEP, and it is one change not 151:** give the helper a fifth answer for
the read case — `404` keeps `{ok:true,data:[],provisioned:false}`; a 400 that is
not a missing relation answers `503 NOT_PROVISIONED` or `400 UPSTREAM_REJECTED`
like its write sibling — then route the 151 through it. **Severity LOW on
likelihood, HIGH on diagnosability**: today a dropped column looks exactly like
an empty table on 150 read paths.

---

## 6. ROUTING SUMMARY FOR hank

1. **The 22 write branches — do these first.** 20 plain calls, 2 preread
   (`:3206`, `:11018`). Same change as the 88.
2. **The 13 caller-interpolated GETs** — same call, lower severity.
3. **Read the 2 unclassified by hand** (`:13503`, `:17127`).
4. **Decide on the read-case fifth answer** before touching the 151; the 151 is
   a one-helper change or nothing.
5. **The 33 server-only GETs in class B** are not a caller-reachable defect and
   are **untested** — no arm anywhere drives a 400 on them. Not a fix; a gap.

**WHAT NO ARM COVERS, SAID SO IT IS NOT MISTAKEN FOR COVERED:** nothing in the
repo drives a `23514` through any of the 22, and nothing drives a `42703`
through any of the 151. Everything above is static classification plus a driven
counterfactual on the helper. **The failing-first arms belong to cody and are
not written.**
