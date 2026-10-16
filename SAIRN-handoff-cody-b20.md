# Handoff — cody, batch b20, 2026-10-16

**Written BEFORE the report**, at a point where **everything is committed except
this file and the two artefacts that follow it**. Nothing is half-edited: the
index row is inserted and its shards regenerated and `--check`ed, both documents
are appended/created whole, and every suite named below was driven at the
current HEAD.

**THE HEADLINE IS THAT TWO OF THE SIX ITEMS WERE ALREADY DONE, AND FINDING THAT
OUT WAS THE WORK.** Item 1's fix landed in b19 and needed re-verification, not
re-implementation. Item 2's research question was already answered in this repo
by a document the app's own source code cites — and the one part of it that was
genuinely open turned out to be answered by a 2003 IRS revenue ruling nobody
here had found. **Writing either from scratch would have produced a duplicate,
which is this platform's most expensive recurring defect.**

---

## 1. Committed and pushed state

| | |
|---|---|
| commits | **`ef8d6b06`** `chore(claims): cody claims platform` and **`7adcd2a6`** `docs(b20): Rev. Rul. 2003-64 closes the counsel question…` |
| claim | `platform` (**`cody-1792155139`**, 2026-10-16T12:52:19Z), taken **BEFORE any work**, published to `origin/main` |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, in any form |
| boundaries | **NO `api/`, `sql/` or `tools/` file edited.** Twelve suites, `sairn_http.py`, `open_work_shard.py` and `index_duplicate_check.py` were **RUN**. No hook restored. `.claude/settings.json` never committed. No auditor clone entered |
| outward actions | **No POST to `checkout` or `portal`, no Stripe object created, no Vercel environment read, no Stripe dashboard opened.** §4 is why |
| committer | `fx <fx@example.invalid>`, this clone's local config, unchanged |
| push | no `--force`, in any form |

**Files in `7adcd2a6`:**

```
docs/2026-09-17-sairnfreedom-tips-tax-treatment.md   +section 12 (13,012 chars)
docs/2026-10-16-cody-b20-sairncash-billing-live-status.md   NEW
docs/SAIRN-OPEN-WORK-INDEX.md                        +1 row (3,839 chars)
docs/open-work/ACTIVE.md                             regenerated
docs/open-work/platform.md                           regenerated
```

---

## 2. Item by item

### ITEM 1 — arm Z. RE-VERIFIED, not redone

The `else` branch landed in b19. Re-running the committed ablation at this HEAD:

```
BASELINE  EXIT=0   16 passed, 0 failed   arm Z ok:1 FAIL:0
ABLATED   EXIT=1   15 passed, 1 failed   arm Z ok:0 FAIL:1   CAUGHT
```

`docs/b19-logs/ablate_arm_z.py` → **EXIT=0**. **The arm fires.** Implementing it
again would have been a second copy of a landed fix.

### ITEM 2 — §45B on VFW/Legion canteen tips. ANSWERED, and the open part is now closed

**`docs/2026-09-17-sairnfreedom-tips-tax-treatment.md` §12.** Appended to the
canonical document rather than written as a new one, **because the app's own
code cites that file at `sairnfreedom.html:4418`** and §§7 and 10 already
carried Pub. 3386, TD 10044, §45B, the §501(c)(19) chain, the frozen minimum
wage and the customary-tipping split. Checked **before** writing anything.

**THE ANSWER, in one paragraph:** **Yes — §45B applies to tips reported by
canteen staff, and member tips count**, on Rev. Rul. 2003-64 and the face of
§45B(b)(2). **But the credit is nonrefundable and the post must first owe tax it
can offset** — in practice §511 UBIT on Form 990-T — so a post with no UBTI gets
nothing now and only a §39 carryforward. **TD 10044 is irrelevant to the
employer credit**; it governs the employee's §224 deduction. **Pub. 3386 does
not address §45B** and routes the tip question to Pub. 531.

**WHAT WAS GENUINELY OPEN AND IS NOW CLOSED.** §9 escalated one question to
outside counsel and filed an index row so it would get asked. **Rev. Rul.
2003-64 answers it** and no section above cited it:

> Section 45B does not prohibit social clubs described in § 501(c)(7) from
> claiming the credit, nor does it limit the credit to social security taxes
> paid in connection with a social club's unrelated trade or business.

**THE GAP WAS A SEARCH GAP, NOT A REASONING GAP** — §7.1 and §10.0 list statute,
regulation, DOL and Ohio sources and **not one published IRS ruling.** A source
table with no ruling line cannot find a ruling. That is the reusable part.

**AND THE IRS's OWN LIVE PAGE CONTRADICTS THE STATUTE.** §45B(b)(1)(B) freezes
the floor at the minimum wage *"as in effect on January 1, 2007"* — **$5.15**,
confirmed by IR-2007-155. The IRS FICA Tip Credit page, **last reviewed
16-Aug-2026**, says **$7.25 / July 24, 2009**. **The direction matters: $7.25
makes the credit SMALLER**, so a post following that page understates it.
Recorded as a two-citation question for a professional, **not** as a
determination that the page is wrong.

### ITEM 3 — SAIRNcash billing. "Incomplete" is wrong about the code and right about the deployment

**`docs/2026-10-16-cody-b20-sairncash-billing-live-status.md`.**

**CODE: COMPLETE and mutation-tested.** Twelve suites green at this commit,
including three Python probes that plant defects and require refusal
(`entitlement_gate_probe` → ALL 12 ARMS PASS, 8 mutations refused).

**THE STANDING ROW IS STALE ON ITS OWN EVIDENCE:** it quotes
`{"error":"Stripe not configured"}`, and **that string no longer exists as a
response** — `api/_lib/stripe-config.js` replaced five per-file conditions with
one generic message.

**LIVE, NON-MUTATING:** `POST /api/sairncash/verify` with an **empty body** →
**400 `Missing sessionId or subscriptionId`**, which proves the config check at
`verify.js:45` **passed**. `verify`'s capability row is `[STRIPE_SECRET_KEY]`.
→ **`STRIPE_SECRET_KEY` IS PRESENT IN PRODUCTION.**

**AND THE INVERSE OF THE OLD MISTAKE IS NAMED BEFORE IT IS MADE:** that 400 is
evidence about the **key and nothing else**. Only `checkout` needs
`STRIPE_PRICE_ID`, so neither `verify` nor `portal` can see it.
**`STRIPE_PRICE_ID` is the live suspect and is NOT proven absent.** And
**present is not working** — the key was once set and expired.

### ITEM 4 — routing confirmed, and one half was NOT actually routed

* **cc — CONFIRMED, nothing re-sent.** The Tier A obligation opened
  **2026-10-16T12:24:12Z** on `alf_facility`, `alf_op_audits`, `leg_aftercare`,
  `mech_site_assets` reads **ASSIGNED TO cc** in
  `tier_a_review_gate.py --list`. **The gate is the place people look**, so a
  second copy would be the two-lists-must-agree shape rather than a routing.
* **hank — HALF-ROUTED, and now fixed.** The routing doc
  `docs/2026-10-16-cody-b19-notprovisioned-misclass-routed-to-hank.md` is on
  `main` (133 lines, names `:14445` and `:2851`) — and had **ZERO rows** in
  `docs/SAIRN-OPEN-WORK-INDEX.md`. **That is the failure §9 of the other
  document in this commit names in its own words**, committed one batch later
  by the session that wrote the warning. One row added, Hank, size S.

**THE ROW WAS BUILT WHOLE AND NEVER BY SPLITTING ON A PIPE.** Pipe count
asserted at 8 before and after; the literal `||` inside the quoted guard is
escaped as the numeric entity — **the first attempt got that wrong and the
assertion caught it, not review.** 8-pipe rows 774 → 775. Shards regenerated:
`open_work_shard.py --write` → 813 rows against 813 in the index; `--check` →
**CLEAN**; `index_duplicate_check.py` → **exit 0**.

### ITEM 5 — this file. ITEM 6 — the push, §6

---

## 3. Verification at this HEAD — exit codes from `echo "EXIT=$?"` on its own line, never a pipeline

```
EXIT=0  python docs/b19-logs/ablate_arm_z.py                 CAUGHT
EXIT=0  node api/sairncash/portal.test.js                    19 passed, 0 failed
EXIT=0  node api/sairncash/verify.test.js                    22 passed, 0 failed
EXIT=0  node api/sairncash/trial-start.test.js               10 passed, 0 failed
EXIT=0  node api/sairncash/trial-renew.test.js                4 passed
EXIT=0  node api/sairncash/trial-renew-idempotency.test.js   11 passed, 0 failed
EXIT=0  node api/sairncash/stripe-webhook.test.js
EXIT=0  node tests/sairncash_entitlement_gate.js             19 passed, 0 failed
EXIT=0  node tests/sairncash_plan_label.js                   10 passed, 0 failed
EXIT=0  node tests/sairncash_safe_harbor.js                  35 passed, 0 failed
EXIT=0  python tests/sairncash_entitlement_fault_probe.py     0 failure(s)
EXIT=0  python tests/sairncash_fault_probe.py                 0 failure(s)
EXIT=0  python tests/sairncash_entitlement_gate_probe.py      12 arms, 8 mutations refused
EXIT=0  python tools/open_work_shard.py --check               CLEAN, 813 rows
EXIT=0  python tools/index_duplicate_check.py
```

---

## 4. The methodology item, because it is the thing most likely to be useful again

> **A PROBE WHOSE SAFETY DEPENDS ON THE ANSWER IT IS TRYING TO OBTAIN CANNOT BE
> RE-RUN TO CHECK WHETHER THE ANSWER HAS CHANGED.** The one state in which it is
> safe is the state it is testing for.

`docs/2026-09-17-sairncash-stripe-readiness.md` records its live check as
`POST /api/sairncash/checkout`. It was safe when it ran, because the config
guard fired and no Stripe object was created. **`checkout.js` validates nothing
before calling Stripe** — `email` is optional at `:49`, the session is created
at `:60` — so **if `STRIPE_PRICE_ID` has since been added, that same command
creates a real Checkout Session on a live payments account.**

**The remedy is derivable rather than lucky:** aim a configuration probe at the
endpoint with the **narrowest capability row** and a **validation gate in front
of its outward call**. `api/_lib/stripe-config.js`'s capability table is what
makes "narrowest" a lookup instead of a guess. Hence `verify` with an empty
body: its refusal sits **after** the config check and **before** any outward
call, so it discriminates the same variable **in both directions** with no side
effect either way.

**ROUTED, NOT TAKEN:** the readiness doc's prescribed command should carry this
warning. Re-writing another session's dated document to add my caveat is not
mine to do; §3 of the new status doc is the caveat and cites it by name.

---

## 5. Claims held

**`platform` (`cody-1792155139`, 2026-10-16T12:52:19Z), taken BEFORE any work, STILL HELD as this file is
written** — because the push in §6 has not happened yet and a claim released
before the work lands is a claim that was never true. **It is released with the
report and digest**, and the report records the release.

**b19's two claims were released at the end of b19** and nothing was inherited.

---

## 6. Open — every item, why, and the exact next step

### 6.1 → MICHAEL. Two environment facts, and no probe can answer either

1. **Is `STRIPE_PRICE_ID` present in the Vercel project?** It cannot be
   determined from outside without creating a Stripe object (§4).
   **NEXT STEP: read the Vercel env list.** One look settles it.
2. **Does the present `STRIPE_SECRET_KEY` authenticate?** Present ≠ working — it
   was a set-but-expired `sk_test_` key once already, and `verify.js` catches an
   expired key and a non-existent subscription into the **same** 500 (`:204`),
   so the outside cannot separate them. **NEXT STEP: one Stripe dashboard look.**

### 6.2 → MICHAEL. The billing-portal token, unchanged

`docs/2026-09-26-presigned-remedy-scoping.md`, scoped by cc, nothing built. A
single-use token is **ruled out on customer-harm grounds** — that scoping already
ran. **NEXT STEP: mint a token, or keep `sub_…` plus a rate limit.**

### 6.3 → THE POST's CPA. Two narrow questions, both one line

1. **Is the canteen held under §501(c)(19) or a companion §501(c)(7)?** Pub. 3386
   says a veterans' org running a bar or canteen for members *"may be recognized
   as tax exempt under IRC 501(c)(7)"*, and that **changes which authority is on
   all fours** — §512(a)(3) does not apply to (c)(19).
2. **§45B(b)(1)(B) says January 1, 2007 and the IRS's FICA Tip Credit page says
   July 24, 2009 — which figure do we use?** Both quoted and dated in §12.6.

### 6.4 → WHOEVER OWNS §9's INDEX ROW. Re-word it; I deliberately did not

It still reads *"needs outside counsel"*. It should read **"answered in
principle by Rev. Rul. 2003-64; two narrow questions remain."**
**NOT DONE HERE on purpose:** re-wording another session's open-work row to
carry my own answer is the edit this platform has least tolerance for.

### 6.5 → HANK. The two call sites, now with an index row as well as a doc

`api/sd-data.js:14445` raw 503 → `await notProvisioned(res, w, <same message>)`
(arms A2/A3 already drive it on a copy); then decide what distinguishes a 42703
from a 404 at `:2851`. **Re-derive both line numbers.** A third guard is named
and not driven: `:14316`.

### 6.6 → CC. The Tier A obligation opened today. cody cannot discharge its own

### 6.7 → NOT TOUCHED IN b20, named so it is not mistaken for done

The b17/b18 carry-overs are exactly as b19 left them: `tooling_inventory
--hooked` failing open on an empty hook set; the two claims probes' retyped-task
fixtures; `sairnbuild.html`'s bare `catch(e){}` in `st()`; six named
`recurrence_open` register records; `run_capa_fields_probe.py`'s 200–420s
per-arm 2.46MB register rewrite; b16's three deterministic ablation arms. **And
the 151/67 sibling guards are NOT converted — that is a decision, not a
backlog** (cross-domain item 7).

---

## 7. Scratch and transcript

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\0f5c2c46-aab3-44b3-997b-47c60e2fbcce.jsonl`

**Scratch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\0f5c2c46-aab3-44b3-997b-47c60e2fbcce\scratchpad\`
— `cash_probe.py` (the non-mutating live probe), `pdftext.py` (the PDF decoder),
`rr2003-64.txt`, `p3386_v2.txt`, `add_index_row.py`, `sec12.md`, the commit
messages and the suite logs.

**No worktree was created this batch.**
`C:/Users/marsh/AppData/Local/Temp/gate-probe3-17976` is registered against this
clone, is **not mine**, and was left alone. The 109 files / 247 MB that `rm` has
refused across b14–b16 are still at the b16 path, listed in
`SAIRN-handoff-cody-b16.md` §6. **Nothing in the repo or on the Drive depends on
any of them.**

---

*Written before the report, at a point where everything above is committed
except this file and the two artefacts that follow it.*
