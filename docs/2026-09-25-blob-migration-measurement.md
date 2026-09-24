# The blob-migration sweep, MEASURED — and two of its three legs refused

**2026-09-25 (CC).** Item 94's consolidation (`api/_lib/blob.js`, `storedBlob`)
landed on six branches on 2026-09-24. The obvious next step is "migrate the
other 83 sites". This is the measurement that was supposed to justify that,
run before writing any of it — cross-domain discipline 7, the Ariane rule:
**byte-identical is not safe-in-context, and a diff proving the code matches
is not a re-qualification.**

Two of the three legs REFUSED. The numbers are here so the next session does
not spend the same afternoon re-deriving them.

---

## What was measured

| Question | Method | Answer |
|---|---|---|
| Hand-rolled `Object.assign({}, payload)` blob builders in `api/sd-data.js` | grep, whole file | **22** (6 of them now `storedBlob`) |
| Generic dispatcher sites storing the payload whole (`data: payload,`) | grep, whole file | **61**, across **50** distinct tables (12 sites' table name is not resolvable from a 12-line window) |
| Does any CLIENT put a scope key INSIDE a write payload? | regex over all 16 app HTML files, `payload:{…}` literals and `var rec = {…}` builders | **ZERO** |
| Envelope-level `app_id` (a sibling of `payload`, read deliberately by the handler) | same sweep | 175 — **not** pollution, and not in scope |

## Leg 1 — the 61 dispatcher sites: REFUSED, and the reason is not caution

A dispatcher that stores `data: payload` does so **because the payload IS the
record**. There is no column list to subtract, so `storedBlob(payload, [])`
would strip exactly the three scope keys — and the measurement says **no client
sends one inside a payload**. So the change would:

* strip nothing that exists today (zero live instances), and
* touch 61 sites across 50 tables on one commit, on the platform's single
  largest and most-shared file, which `cody` was holding when this was
  measured.

That is a large blast radius buying defence-in-depth against a defect with no
current instance. **The honest verdict is that it is not worth one sweep**, and
the reason is the same one this repo already recorded about `sb_bud`'s baseline:
the mechanical fix and the correct fix are different when the stored figure
means something. Here the stored payload means "the record", and a global
subtraction is a decision about 50 tables made by one regex.

**What IS worth doing, and is cheap:** convert a dispatcher branch to
`storedBlob` when it is being edited for another reason, with the branch's own
read path checked in that same commit. That is defence-in-depth at the cost of
one line per branch somebody is already reading.

## Leg 2 — the 16 remaining hand-rolled builders: WORTH IT, one at a time

These already have a **per-branch column list** the author wrote out, which is
exactly the argument for `storedBlob(payload, [...])`: the column keys stay
where they belong (per branch, because which payload fields are real columns is
a fact about each table) and only the universal rule moves into the module. The
six converted on 2026-09-24 are the pattern. **Not a sweep either** — each needs
its column list read against its own table, and two of the six needed
`created_at` added for the shadow that the ALF review found, which a mechanical
conversion would have missed in both directions.

## Leg 3 — the Ariane re-qualification itself: this is the finding

The tempting sweep is **exactly the shape** discipline 7 was written for. The
six converted branches were each re-qualified individually: alf_mar and
alf_incidents needed `created_at` in the strip list (the read maps the column
and spreads the blob after it, so a payload copy shadows the real value);
law_matters needed an EMPTY column list (its read hands `x.data` back whole, so
the client's own `id` must survive inside data); rf_supplier_documents needed
nothing at all (it builds its body column-by-column and was already immune).
**Four branches, four different correct answers.** A find-replace would have
produced one answer four times, and been wrong twice.

So the recorded decision is: **the universal rule is consolidated and the
per-branch judgement is not consolidatable.** That is not a failure to finish
the migration; it is what the migration turned out to be.

---

## Re-run these numbers before quoting them

    grep -c "Object.assign({}, payload)" api/sd-data.js
    grep -c "data: payload," api/sd-data.js
    grep -c "storedBlob(payload" api/sd-data.js

and the client half, which is the leg that refuses the sweep:

    python - <<'EOF'
    import io,re,glob
    n=0
    for f in glob.glob('*.html'):
        src=io.open(f,encoding='utf-8',errors='replace').read()
        for m in re.finditer(r'payload\s*:\s*\{([^{}]{0,400})\}', src):
            if re.search(r'\b(license_hash|app_id|p_license_hash)\s*:', m.group(1)): n+=1
    print('scope key inside a payload literal:', n)
    EOF

A non-zero answer to that last one **changes the verdict above**: it would mean
real pollution exists and leg 1 becomes a fix rather than defence-in-depth.
