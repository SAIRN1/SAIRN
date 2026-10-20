# SAIRN handoff — hank b25 — 2026-10-20

**Subject:** three defects that all **reported success** — a revoke silently
overwritten inside a read-then-write window, a zero-row PATCH logged as a plan
change, and two controls that **permitted when their setting was absent or
misspelled** — plus the deployed measurement that shows one of those modes
**cannot be observed from outside at all**; the two b24 items the digest omitted,
re-reported; and the OSHA duplicate warning **driven in a real browser on the
deployed page**.

**Written before the report, at a point where nothing is half-finished.** Every
figure re-driven at the landed sha.

---

## 1. COMMITTED AND PUSHED STATE

**LANDED on `origin/main`, `0 ahead, 0 behind` by sha after a fresh fetch.
NOT FORCED. ZERO gate overrides** — no `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no
`SAIRN_SEED_GATE`.

| sha | commit |
|---|---|
| `8f2036615` | `fix(agent+claude b25)` — the three defects, 30 arms, four ablations |
| `457589427` | `chore(derived b25)` — generated documents regenerated |
| `fc49c9cc6` | `chore(defect register b25)` — one record, four factors |
| *(+ this handoff/report/digest commit)* | **re-derive the tip** — five clones push to one branch |

### THE GATES

* **`register-feed` refused five attempts in a row**, naming
  `fix(agent+claude b25)`. **Fed, not escaped:** one record, **four contributing
  factors**, `--injection-unknown` with a stated reason rather than a guessed
  commit, and a `recurrence_open` naming the thing the fix cannot close.
* **The register's FMEA loop answered `PREDICTED` for `api/claude.js`** — rule
  1.11, from `docs/fmea/api_claude.js.json`. **That is the loop working as
  designed for the first time in my batches:** a draft written earlier named the
  rule this defect was later filed under. Five other files answered `NO DRAFT`
  and are listed in §4 C.
* **A ref-lock race on the first attempt** — not a gate finding; another clone
  pushed mid-upload.

---

## 2. CLAIMS HELD

**Mine, held through the batch and released at the end.** Subject: the revoke
window, the zero-row PATCH, the two fail-open settings, the two omitted b24
items, the browser drive, and the push.

**Held by others:** **cody** (`api/sd-data.js`, `tests/` — b28, incl. a
"role-from-token bypass in prepared-only mode" which is adjacent to the
countersign work and worth their attention beside §4 F); **cc** (`CLAUDE.md`,
`tools/sabotage.py` — b27; **every currency finding below is report-only because
of this**); **fourth** (`sairndental.html` — b40); **hover** and **hover2**
(audits).

**No other population's file was edited this batch.** Everything touched is
under `api/` or `docs/*-hank-b*`. **Nothing in `~/.claude/` was read for editing
or written.**

---

## 3. THE SIX ITEMS

### Item 1 — the revoke window in `api/agent/register.js`. **CLOSED.**

> **CONCEPT.** A registration must not RESURRECT a revoked agent: the
> not-revoked condition travels **in the same statement** as the update, and a
> zero-row result is a **REFUSAL**, never a success.

**Reproduced first**, with a recorded PostgREST that revokes the row **the
instant the read returns** — the real window, which stubbing one answer cannot
produce — and with **two concurrent calls**.

**Two halves, and the suite proves both are needed:** `&status=neq.revoked` on
the PATCH, and `return=representation` plus a zero-row check. **With `minimal`,
PostgREST answers 204 whether it changed one row or none**, so the condition
would be enforced in the database and invisible to the handler. **Ablation D2
removes only the handler half and arm A1 still reddens.**

A zero count **and a non-array body** both refuse with the **same 403 and
message** as the pre-write check, so a caller cannot tell the race from the
ordinary refusal and try to win it.

### Item 2 — the zero-row PATCH in `api/agent/stripe-webhook.js`. **CLOSED.**

> **CONCEPT.** The log line must say what the **write did**, not what was
> **asked for**.

`return=minimal` made `res.ok` true for one row updated **and for none**, and the
handler logged *"plan_status set to «paid»"* for a row that does not exist.
**That line is the only record this endpoint leaves** — Stripe gets its 200,
never retries, nothing reconciles the two sides, and in a billing dispute the one
artefact an operator reads says the opposite of what happened.

Three outcomes on two streams now, the success line carrying the row count.
**It deliberately does not throw:** retrying an event that names a missing row
can never succeed.

### Item 3 — the two permissive defaults. **CLOSED IN CODE; ONE HALF UNOBSERVABLE LIVE.**

> **CONCEPT.** A control whose setting is **missing or misspelled** must refuse,
> not permit.

Both reads were one line and had the **same two holes**: absent permits, and so
does every misspelling, because only an exact `enforce` took the other branch.
`api/_lib/fail-closed-mode.js` carries the rule and **both** call it. The third
answer is the point — `{mode:'enforce', configured:false, reason}` — because a
control that silently **hardened** is as hard to operate as one that silently
relaxed.

**The DEGRADED axis is untouched**: *"could not reach the counter"* still fails
open, because that is a measurement failure and enforcing a limit nobody counted
is the worst of both worlds.

**MEASURED ON THE DEPLOYED ENDPOINT, before this shipped:**

| probe | answer | reading |
|---|---|---|
| unauthenticated POST | **401 `NO_LICENSE`** | `SAIRN_CLAUDE_AUTH_MODE` **is** `enforce` in production — the auth half of this change is a **no-op there** |
| with `SD-AUDIT-2026` | **200**, a real `claude-sonnet-4-6` completion | the licence gate is the only refusal |
| **burst of 12 authenticated demo calls** | **12 × 200, zero 429, zero degraded flags** | **this does NOT show the limiter is in observe** |

**The third row is the honest one and it is the finding.** Twelve allowed calls
is equally consistent with `observe` and with `enforce` under a ceiling far above
twelve. **The response carries no mode, so the deployed rate-limit mode is not
observable from outside at all** — probing did not close the gap the dispatch
named; it measured that it cannot be closed from here. **See open item A.**

### Item 4 — the two b24 items the digest omitted. **RE-REPORTED.**

Both were done in b24 and both are in that batch's notes and handoff; the
**digest** omitted the stale-header fix entirely and reduced the currency sweep
to one DECISION-NEEDED line. Full text in
`docs/2026-10-20-hank-b25-notes.md` item 4; the five measured currency findings
are in §4 D–G below.

### Item 5 — the OSHA duplicate warning, **DRIVEN IN A REAL BROWSER. IT RENDERS.**

Against the **deployed** page `https://sairn.vercel.app/sairnbiz` (which carries
b24's fix), with three incidents seeded into the real page's own render path —
two sharing `2026-1` and one at `2026-2`:

* `sbCaseNoCollisions(rows)` → **`["2026-1"]`**, one finding for the one
  duplicated number.
* **Both** `2026-1` rows render Column A as
  **`2026-1 ⚠ DUPLICATE case number -- another entry in 2026 also holds 1. Two
  recordable cases cannot share one Column A; correct one on the log before
  filing.`**
* The `2026-2` row renders **no warning at all** — `hasWarn: false`. **That is
  the control**: without it, "the warning appears" is consistent with it
  appearing on every row.
* The warning is a `<strong>` with computed colour **`rgb(180, 83, 9)`** (amber),
  inside the Column A cell rather than in a banner elsewhere.
* The tab was created for this and **closed afterwards**.

**What this does NOT show:** it was read out of the live DOM, **not** judged as a
screenshot, so it is a rendered-structure pass and not a visual-design one. Three
rows were seeded by the drive; nothing was written to a server.

### Item 6 — push. **PUSHED WITHOUT FORCE, CONFIRMED BY SHA.** §1.

---

## 4. WHAT IS OPEN, AND THE EXACT NEXT STEP

### A. **FIRST, AND IT IS A DEPLOY-TIME RISK I CREATED** — is `SAIRN_AI_RATE_LIMIT_MODE` set?

If that variable is **absent or misspelled** in Vercel, this batch's fail-closed
change switches the AI **cost limiter ON at the daily ceiling** the moment it
deploys. I could not read it: the response carries no mode, and a 12-call burst
cannot distinguish `observe` from a high ceiling.

**NEXT STEP, before trusting the deploy:** `vercel env ls production --project
sairn` (names only, no values) and confirm `SAIRN_AI_RATE_LIMIT_MODE` exists and
reads exactly `observe` or `enforce`. **If it is missing, set it explicitly to
whichever you intend** — the whole point of the change is that silence is no
longer an answer. The same check applies to `SAIRN_CLAUDE_AUTH_MODE`, which is
**measured as already enforcing**, so no action is expected there.

### B. The deployed rate-limit mode is still not observable — **and it could be**

**NEXT STEP:** echo the resolved mode on the response the way
`rate_limit_degraded` already is — `rate_limit_mode` and `rate_limit_configured`
— so a probe can read what a deploy actually has. One field, and it closes the
measurement gap this batch could only describe. `api/claude.js` is mine; not done
for budget, not for doubt.

### C. Five files answered `NO DRAFT` in the FMEA loop

`api/_lib/ai-rate-limit.js`, `api/_lib/fail-closed-mode.js`,
`api/agent/register.js`, `api/agent/stripe-webhook.js`,
`api/b25-revoke-race-and-failclosed.test.js`. **NEXT STEP:**
`python tools/fmea_draft.py <file> --save` for each. `api/claude.js` already has
one and it **predicted this defect's rule**, which is the argument for doing the
other five.

### D. Four skippable gates are **declared and not wired** — **cc's**

`control-bytes`, `credential-sql`, `register-feed`, `scrutiny-ledger`. A
`SAIRN_SKIP` for any is **granted and ignored**. **b23, b24 and b25 were each
refused by one or two of those four**, so the scoped override everyone is pointed
at would have changed nothing. **NEXT STEP:** wire them — the tool says it is
*"one `gate=` kwarg at that check's `deny()`"* — or remove them from the
skippable list.

### E. `CLAUDE.md`'s stale figures — **PARTLY FIXED BY cc MID-BATCH**

The over-ceiling list **has been corrected to eight with the right membership**
(cc b27, visible in the working tree), and the sabotage figure now carries three
dated measurements. **Still stale:** *"covers **eight** named gates"* →
**measured 11**, and *"**Twelve** standing conventions"* →
**measured 39** (`grep -cE '^## [0-9]+\.'`). **NEXT STEP:** cc corrects both, or
deletes the numbers and keeps the instruction, which is the half that was never
wrong.

### F. `attest` is absent from `WRITE_ACTIONS` — **cc's**

`tools/live_probe_residue_audit.py`. A probe that only attested would not be
counted as a writer. **NEXT STEP:** add the verb with the reason in the commit,
the way `verify` was removed.

### G. Carried forward

The complete OSHA fix is a **server-side per-year sequence** in `api/sd-data.js`
(cody's) — until then the collision is detected, not prevented. `api/sd-data.js`
still unswept for the raw-PostgREST-filter class. `sairnlaw.html` still has **no
attestation UI**. The F2/F3 module arms in `api/b22-funeral-f1-f2-f3-wiring.test.js`
should be promoted to handler level now that cody wired `decide()`'s fifth
argument. `api/b19-iolta-reconcile-carveout.test.js` still carries its expected
reds, including b23's A1 — **re-aim, do not delete.**

---

## 5. EVIDENCE — RE-DRIVEN AT THE LANDED SHA

| suite / probe | result |
|---|---|
| `api/b25-revoke-race-and-failclosed.test.js` | **30 passed, 0 failed, 0 unproven** (new) |
| …its ablations | **D0 control green; D1 → A1+A2 red; D2 → A1+A6 red; D3 → C1+C6 red; D4 → B1 red** |
| `api/_lib/ai-rate-limit-tenant.test.js` | **10 passed, 0 failed** (one arm **re-aimed**) |
| `api/claude-cost-controls.test.js` | 31 passed, 0 failed |
| `api/ai-safeguards.test.js` | 47 passed, 0 failed |
| live `/api/claude` unauthenticated | **401 `NO_LICENSE`** |
| live `/api/claude` with a licence | **200**, real completion |
| live `/api/claude` burst ×12 | **12 × 200, 0 × 429** |
| **browser, deployed `/sairnbiz`** | **both duplicate rows warn in Column A; the non-duplicate row does not** |
| `md5sum` before/after every ablation | **unchanged on all three mutated files** |

**WHAT THIS DOES NOT COVER:**

* **The deployed rate-limit mode was NOT determined.** Item A.
* **No screenshot was judged** — the browser evidence is DOM structure and a
  computed colour, not a visual-design pass.
* **The register.js race was reproduced against a RECORDED PostgREST**, not
  against two real concurrent HTTP calls to the deployed function.
* No whole-tree suite run; suites chosen by what the diff touches.
* Five FMEA drafts named and not written.

---

## 6. TRANSCRIPT

    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\f904c24c-ad35-4782-b977-90b0346b7b9e.jsonl

**Context when this section was written: 78.7% — 786,679 of 1,000,000**, printed
by `python tools/context_verify.py --digest-line`, not self-reported. The
dispatch's wrap trigger for this batch was 85%.

---

## 7. THINGS I GOT WRONG IN THIS BATCH

1. **Arms C4 and C5 failed on a correct file**, because both assert that the old
   `|| 'observe'` default is **gone** and both fixes **quote that line in the
   comment explaining them**. The negation read the prose about the code. Third
   occurrence of this class in three batches — comments are stripped now, and
   C8, which asserts documentation on purpose, says so at the line.
2. **I left a placeholder arm in the suite** (`A3. placeholder`, asserting
   `true`) while drafting and only caught it on the first run.
3. **I spent two attempts on the register record's `--app` value**, passing
   `platform` and then `sairnbiz`, when the allowed list is printed by the tool
   on refusal and `PLATFORM` is upper-case.
4. **I planned to drive the browser against a local file** and only then
   realised the deployed page already carried b24's fix, which is the honest
   target — the local file would have proved my own copy renders, not the app.
