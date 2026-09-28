# `sf_vendors` and `sf_inventory_counts` — the evidence cells were pointing at the wrong code

**2026-09-29 (Cody).** Both rows in `docs/CRITICALITY-TIERS.md` carried a bare
line-number citation as their evidence. **Both had drifted, and neither verdict
was wrong** — which is the thing worth noticing, because a cell whose reasoning
is sound and whose citation points somewhere else reads exactly like a cell that
was checked.

## What the cells said, and where those lines actually are today

| row | cited | what is at that line NOW | the real write |
|---|---|---|---|
| `sf_inventory_counts` | `:4075` | expense-row rendering — `expenseCategory`, approval tags. Nothing to do with inventory. | `sfRecordInventory()`, near `:4815`, pushing `{id, date, by, bottlesWithReading}` |
| `sf_vendors` | `:4514` | the `PRODUCT_CATEGORIES` table — beer/wine/spirits and their ORC 4301.22 cites | `sfAddVendor()`, near `:5263`, pushing `{id, name, category, brand, licensed}` |

Both were re-read out of `sairnfreedom.html` before the cells were touched. The
field lists in both cells were **already correct** — `{date, by,
bottlesWithReading}` and `{name, category, brand, licensed}` are exactly what
those two functions write. So the audit that produced these cells on 2026-09-23
read the right code; only the pointer it left behind went stale.

## What changed

Both cells now cite the **function name** and carry the line number as a
"currently near" rather than as the anchor:

> `sf_inventory_counts` — READ OUT OF THE APP: `sfRecordInventory()` in
> `sairnfreedom.html` writes `{date, by, bottlesWithReading}`. **RE-ANCHORED
> 2026-09-29: this cell cited `:4075`, which is now expense-row rendering and has
> nothing to do with inventory** — the real write is `sfRecordInventory()`,
> currently near `:4815`. A bare line number is an anchor that nothing re-checks;
> the function name moves with the code.

> `sf_vendors` — READ OUT OF THE APP: `sfAddVendor()` in `sairnfreedom.html`
> writes `{name, category, brand, licensed}`. **RE-ANCHORED 2026-09-29: this
> cell cited `:4514`, which is now the `PRODUCT_CATEGORIES` table** — the real
> write is `sfAddVendor()`, currently near `:5263`. The verdict itself was
> re-read and is unchanged.

**Tiers are unchanged.** `sf_inventory_counts` stays **B/B** — it is a count, not
a valuation; no price and no variance on the row, which is what separates it from
`sf_shifts`. `sf_vendors` stays **B/B** — `licensed` is a flag *about* a supplier
that nothing gates on today, and the prices live on `sf_vendor_prices`, which is
already A. Re-anchoring a citation is not a re-tiering and this document does not
pretend it is.

## Why this was delivered as text before, and applied now

The earlier plan delivered these as replacement text because
`docs/CRITICALITY-TIERS.md` was inside a live `cc` claim (PR §4.3 — declare the
conflict, do not reword the task to slip past the matcher). **At the time of
this edit that register carries no live claim from any session**, so the cells
were applied directly and are also reproduced above, so the record of what
changed does not depend on reading a diff.

## THE CLASS, WHICH IS LARGER THAN TWO ROWS

`docs/CRITICALITY-TIERS.md` contains **104** bare `:NNNN` citations of this
shape. Two were named in this task, two were checked, and **two of two were
stale**. That is a sample of two and it is reported as a sample of two — it is
not a 100% drift rate and this document does not claim one.

But the mechanism is not in doubt, and it is cross-domain discipline 8 exactly:
**nothing announces the day a citation stops pointing at its subject.** A line
number in a 5,000-line single-file app is invalidated by any edit above it, in a
file four sessions push to. The citation stays syntactically valid, the cell
still reads as evidenced, and the only way to find out is to open the file.

**The remedy, not taken here because it is a different task:** a checker that
resolves every `:NNNN` citation in the tier register against the app the row
belongs to and reports the ones whose neighbourhood no longer mentions the
resource. It needs a row→app mapping the register does not currently carry in a
machine-readable form, which is the real work and the reason this is named rather
than done. Filed as a named gap rather than left as an observation.
