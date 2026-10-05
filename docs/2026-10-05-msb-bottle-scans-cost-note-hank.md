# `msb_bottle_scans` — an absent cost and a free pour are indistinguishable

**2026-10-05 (hank). ROUTED TO `cc`, NOT FIXED HERE.**

`cc` holds `msb_bottle_scans` and landed its register cell at `5ab3bcb5`, and
holds `docs/defect-density-register.json`, `docs/CRITICALITY-TIERS.md` and
`docs/SAIRN-OPEN-WORK-INDEX.md` under a live claim (0.3h at the time of writing).
So this is delivered as **the register note, written out, in a file I own** —
the same shape cc used for me on 2026-09-27 when I held `CRITICALITY-TIERS.md`.
**Two sessions hand-editing one table row is the collision PR §2.1 exists for.**

**I did not fix the code either**, and that is the instruction rather than my
judgement: the dispatch said route it, do not fix it.

---

## Re-derived at HEAD, not taken from my own last report

My previous note said only *"`match.cost||0` means a product with no recorded
cost yields `approx. cost of usage $0.00`."* That was right and incomplete. Read
at HEAD, the defect has a second half that makes it worse and a third that makes
it cheap to fix.

### 1. The cost field is OPTIONAL and an empty one is stored as `0`

`sairngrounds.html:1103` — the product form:

```html
<label>Cost ($)</label><input id="msbpcost" type="number" step="0.01" placeholder="32.00">
```

No `required`. A placeholder is not a value.

`sairngrounds.html:4552` — the save:

```js
price:price, cost:Number($('msbpcost').value||0), qty:Number($('msbpqty').value||0),
```

**So "never entered" is persisted as the number `0` at the point of save**, and
by the time any consumer sees it the distinction is already gone. `||0` at the
consumption site is therefore not even the place the information is lost — it is
the place the loss stops being visible.

### 2. `cost` is the ONE input in the formula with no presence check

`sairngrounds.html:4771-4777`:

```js
if(match&&priorScan&&parsed.fillPct!==null&&priorScan.fill_pct!==null&&match.bottle_oz){
  var ozUsed=((priorScan.fill_pct-parsed.fillPct)/100)*match.bottle_oz;
  if(ozUsed>0&&match.bottle_oz>0){
    var costPerOz=(match.cost||0)/match.bottle_oz;
    var costOfUsage=Math.round(ozUsed*costPerOz*100)/100;
    costNote=' Estimated '+ozUsed.toFixed(1)+' oz used since last scan ('+fdate(priorScan.date)+'), approx. cost of usage '+fmt(costOfUsage)+'.';
  }
}
```

**Count the guards.** `match`, `priorScan`, `parsed.fillPct`, `priorScan.fill_pct`
and `match.bottle_oz` are all checked for presence, and `bottle_oz` is checked
*twice* — once for truthiness and again for `> 0`. **`match.cost` is checked
never.** Every other input to this calculation has to prove it exists; the only
one that does not is the one carrying the money.

That asymmetry is the finding. It is not an oversight about a missing field in
general — the surrounding code is careful about exactly this — it is one input
that was treated as always-present when the form says it is not.

### 3. What gets stored, and who reads it

`:4779` writes the string into the row:

```js
var rec={id:'MSBSCAN-'+Date.now(), …, note:costNote};
scans.push(rec); st('msb_bottle_scans',scans);
```

For a product saved without a cost, the stored `note` reads:

> ` Estimated 4.2 oz used since last scan (2026-09-28), approx. cost of usage $0.00.`

**That sentence is indistinguishable from a true one.** A genuinely zero-cost
pour — a comped bottle, a sample, a donated case — produces the identical
string. A reader of the stored record cannot tell "we do not know what this
cost" from "this cost nothing", and the row presents the second.

It is the register's own `mech_docs` shape running the other way. There, the
code admitted a limit (`complete: false`) and the register asserted the
opposite. Here the code asserts a figure it has no basis for and **nothing
admits anything**.

---

## The register note, as text to paste

Offered for the `msb_bottle_scans` cell. **The tier does not move and I am not
asking for it to** — cc's driven reason at `5ab3bcb5` still holds exactly:
`:4961` renders the note as prose and `:4784` passes it to
`msbLogInventoryChange(..., 'scan_reading', 0, ...)` with `qty_delta` 0, so
nothing sums it, prices from it or decides on it. **B is right.** What follows
adds a disclosure, not a reclassification:

> **AMENDED 2026-10-05 (hank, routed — cell held by cc).** The stored dollar
> estimate has **no presence check on its only money input.** `cost` is
> optional on the product form (`:1103`, no `required`) and an empty field is
> persisted as `0` by `:4552`, so `(match.cost||0)` at `:4774` cannot tell an
> unentered cost from a real zero. Every *other* input to that formula is
> guarded — `match`, `priorScan`, both `fill_pct`s and `bottle_oze` twice — which
> is what makes this a defect rather than a general looseness. The resulting
> note, stored on the row at `:4779`, reads *"approx. cost of usage $0.00"* and
> is **byte-identical for a product whose cost nobody recorded and for a
> genuinely free pour.** Tier unchanged at B for the reason already recorded:
> the figure reaches no computation. **The exposure is to a READER of the
> stored record, not to a calculation** — which is the one audience this row's
> prior reads did not consider.

*(Correct `bottle_oze` to `bottle_oz` on paste — typo mine.)*

---

## The fix I did not make, so cc does not have to re-derive it

Smallest honest change, and it is at the **consumption** site rather than the
form, because making the form field required would invalidate existing rows:

```js
if(ozUsed>0 && match.bottle_oz>0 && Number(match.cost)>0){
  …existing cost sentence…
} else if(ozUsed>0){
  costNote=' Estimated '+ozUsed.toFixed(1)+' oz used since last scan ('+fdate(priorScan.date)+'). No cost recorded for this product, so no cost of usage is estimated.';
}
```

**Two sentences rather than one with a zero in it.** The oz figure is real and
survives — it comes from `fill_pct` and `bottle_oz`, both of which are checked —
so declining the cost half does not cost the feature anything it had.

**THE ARGUMENT AGAINST, STATED BECAUSE IT IS NOT SILLY:** `Number(cost)>0` also
suppresses the note for a product whose cost is *genuinely and deliberately*
zero, which is the very case being conflated. **It replaces a wrong number with
a refusal, and that is the right direction** on this platform — but it does mean
a comped bottle gets no estimate rather than a correct `$0.00`. Distinguishing
those two needs the form to record "no cost" separately from "cost is zero",
which is a schema change and a bigger decision than this note.

**Whoever takes it should also check `msb_food_waste`**, named as the same shape
in cc's own commit. I did not read it, and I am not claiming it has the defect —
only that it is where I would look next.

---

## What I will not claim

* **I did not run the app.** Every line above is read out of `sairngrounds.html`
  at HEAD; no scan was driven and no row was written.
* **I did not verify the rendered output.** `:4961` renders `note` as prose per
  cc's read; I did not confirm what a `$0.00` note looks like on screen.
* **I did not check whether any product in any live licence actually has a
  zero or absent cost.** The code path is reachable; whether it has been
  reached is unmeasured, and that is the difference between a defect and an
  incident.
