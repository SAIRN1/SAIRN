# cody b19 — two `NOT_PROVISIONED` misclassifications, now driven, routed to hank

**2026-10-16.** Both were **observed by fourth in b25 §1 with a scratchpad
driver that was never landed**, so nothing in the tree would have noticed
either being fixed or getting worse. They are arms now:
**`tests/sd_data_not_provisioned_misclass.js`**, exit 1, **12 passed / 2
failed**, registered in `docs/known-red-suites.json` with
`expected_red_scope: "A1 AND B1 ONLY"`.

**Every line number below was re-derived at this commit.** fourth measured at
`12ffa069`; the file has moved since — the write guard fourth cited as `:14347`
is **`:14445`** here. Re-derive anything you mean to quote, including out of
this file.

---

## The fix hank has to make, and it is two call sites

### A — `alf_op_audits`, a **Tier A** compliance log. `api/sd-data.js:14445`

```
      if (w.status === 404 || w.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The operational audit log is not set up yet — run sql/sairncare_op_audit_schema.sql in Supabase first.' } });
        return;
      }
```

on the response of the upsert POST at **`:14440`**.

| | measured |
|---|---|
| injected 400 + `{"code":"23514"}` | **HTTP 503 `NOT_PROVISIONED`** |
| control, store healthy | HTTP 200 `ok:true` |
| counterfactual on a COPY, that one call site routed through the shipped `notProvisioned(res, w, <same message>)` | **HTTP 400 `ROW_REFUSED`** |
| same copy, genuine 404 + `PGRST205` | **still HTTP 503 `NOT_PROVISIONED`** |

**A row refused ON CONTENT is reported as a missing table**, and the operator
is told to run a migration that is already applied, on an append-only record
of a care observation. **No new helper, no new status code and no decision is
needed:** `notProvisionedDecide()` (`api/sd-data.js:18793`) already separates a
`23xxx`, a real missing relation, and the third unclassifiable case —
`ROW_REFUSED` / `NOT_PROVISIONED` / `UPSTREAM_REJECTED`. The suite's arms A2
and A3 drive exactly that change and both pass.

**The existing-row read two guards earlier, `:14316`, has the same shape** and
is not driven here. It is the append-only existence check, so a 23xxx there
would also render as "not set up yet". Named rather than asserted.

### B — `mech_site_assets`, a read. `api/sd-data.js:2851`

```
        if (r.status === 404 || r.status === 400) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
```

on the GET at **`:2842`**.

| | measured |
|---|---|
| injected 400 + `{"code":"42703"}` | HTTP 200 `{"ok":true,"data":[],"provisioned":false}` |
| injected 404 + `PGRST205` | HTTP 200 `{"ok":true,"data":[],"provisioned":false}` |
| control, store healthy | HTTP 200 `provisioned:true`, with the board |

**Byte-identical.** A dropped or renamed column is indistinguishable from a
table that was never created, nothing in the answer is an error, and that is
the state a **partial migration** leaves — which is the state this platform is
in most often.

**WHAT B1 DOES NOT CLAIM, and read this before arguing with it.** The branch's
own comment (`:2846-2850`) says a registry provisioned *before* the three AIM
Act columns existed lands here too and should be told to re-run the idempotent
migration, and **that argument is correct and is not disputed.** The arm
asserts only that the two states **differ in the answer**. A distinguishing
field beside `provisioned: false` satisfies it; an error status is not
required.

---

## The population, measured by the suite on every run rather than quoted

`318` guards of the form `X.status === 404 || X.status === 400` in
`api/sd-data.js`:

| answer | count |
|---|---|
| routed through `notProvisioned()` | **88** |
| raw `503 NOT_PROVISIONED` | **67** |
| raw HTTP 200 `provisioned: false` | **151** |
| other | 12 |

This is an **independent re-derivation of the 151** the dispatch named, and
the 22 class-B write-guarded branches fourth published are a subset of the 67.
Arm **P3** refuses unless all three answers are represented, so a regex that
stopped matching cannot read as a clean census, and **P4** asserts both
subjects are members of the counted set.

**WHICH OF THE SIBLINGS CARRY A REAL RISK IS NOT ASSERTED AND IS NOT MINE.**
A number typed into a document goes stale, which is why it is measured; but
converting 218 branches is a per-branch judgement about what a 400 can mean on
that table, and it belongs to whoever owns `api/`. This file drives the two
that were actually observed.

---

## One defect in the suite, found by driving it

`branchOf()` first bounded each branch at the next `\n    if (resource === `
and **overran by a factor of 130** — 23,575 characters for a branch of about
180 lines, because the next same-indent guard is a long way below. The slice
therefore contained other branches that *do* call `notProvisioned()`, and arm
**P5 — which exists to assert the defect has NOT already been fixed — reported
that it had been.** A precondition arm telling the suite to retire itself, over
a defect that is still shipped.

**A terminator is a guess about what comes next; a balanced brace is a property
of the branch itself.** The slice is closed by brace matching now, and new arm
**P1b** asserts neither slice mentions the other branch's resource — because a
counter that started in the wrong place still produces a "balanced" span.

---

## Not done here, and not claimed

* **No `api/` or `sql/` file is edited.** `api/` is copied to a temp tree for
  the counterfactual and the live tree holds no modification to it.
* **No production row read, no live deployment fetched, no table touched.**
  Every answer above comes from a mocked `fetch` with a real PostgREST failure
  body.
* **The 216 sibling guards are not converted and not individually assessed.**
* **The `alf_op_audits` existence-check guard at `:14316`** is named above and
  is not driven.
