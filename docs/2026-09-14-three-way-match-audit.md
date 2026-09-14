# Three-way match — what actually has to be true before money moves on the books

**2026-09-14 (CC). AUDIT ONLY. Nothing was changed and nothing was gated**, as
asked. Every claim below is a grep or a read you can repeat; the commands are at
the foot.

A three-way match is the control that a payable is not paid until three
independently-produced documents agree: **the purchase order** (what we agreed
to buy), **the receiving report** (what actually arrived), and **the vendor's
invoice** (what we are being asked to pay). It exists because any one of them
alone is a claim by a single party.

The question asked was narrower and sharper: **does any SAIRNbiz or StoneDesk
payment/invoice write commit on a single internally-generated record, with no
independent confirmation required first?**

**Yes. Both, and in two different ways.**

---

## SAIRNbiz — a zero-way match, and the documents do not exist

| step | function | what it requires |
|---|---|---|
| obligation created | `saveBill()` | a vendor name, an amount, an optional invoice number. One form, one person. |
| obligation settled | `sbPayBill(id)` | **the same record.** No second document, no second person, no amount re-entry. |

`saveBill()` writes the payable and **immediately posts to the general ledger**
— `bill_received`, debit 5010 COGS, credit 2010 Payable — from nothing but what
was typed into the modal. `sbPayBill()` then flips `status` to `Paid`, sets
`bal` to 0, and posts `bill_paid`, debit Payable / credit Cash, **against the
same internally-created row.**

**There is no purchase order and no receiving concept anywhere in SAIRNbiz.**

```
grep -ciE "purchase order|receiving|packing slip|bill of lading" sairnbiz.html
0
```

So this is not a match that is skipped. **Two of the three documents do not
exist**, and the third is typed by the person recording it. The AP cycle is
begun and completed by one hand with no external artefact at any point.

### What bounds the risk, stated because it changes the severity a lot

`sbPayBill()` says so itself, in the toast:

> *Marked paid: `<vendor>` `<amount>` — recorded in this app only, no payment
> was sent*

**The app moves no money.** Nothing here reaches a bank, a card, or a payment
processor. The exposure is a **wrong set of books** — a payable recorded that
was never owed, or settled that was never paid — not a wrong disbursement. That
is a real exposure for a business using this as its ledger, and it is a much
smaller one than "an unmatched invoice can be paid".

**What is genuinely good here, and worth not breaking:** receipt and payment are
**two entries, not an edit** — the ledger records what happened and when — and
each carries its own `source_kind`/`source_id`, which `api/ledger.js` uses for
idempotence. The accounting shape is right. It is the *authorisation* shape that
is absent.

---

## StoneDesk — all three documents exist, and nothing can join them

This is the more interesting finding, because StoneDesk is most of the way
there and does not know it.

| document | store | writer | fields |
|---|---|---|---|
| purchase order | `sd_pos` | `sdPOCreate()` | vendor, amount, material, expected date, status |
| receiving report | `sd_receiving` | `sdRecvLog()` | material (free text), qty, **value**, vendor, condition, notes |
| invoice | `sd_invoices` | `invSaveStore()` | the customer-facing sale |

All three are real, shipped and reachable. And:

```
grep -cE "po_id|poId|purchase_order_id|receiving_id|recv_id|receipt_id" \
     stonedesk.html sairnbiz.html
stonedesk.html:0
sairnbiz.html:0
```

**There is not one field anywhere that links any of these three records to
either of the others.** A receipt names a vendor and a free-text material
description; a PO names a vendor and a material description. Nothing carries the
other's id. Matching them would mean guessing from two strings a human typed on
two different days.

**So a three-way match here is not unenforced — it is unconstructible.** The
three legs exist as independent lists.

**And the receiving log records its own `value`**, typed by whoever booked the
delivery, with no reference to the PO amount. Two independently-typed money
figures for the same delivery, and no mechanism — not even a manual one — that
puts them side by side.

### One incidental defect found on this path

`sdPOCreate()` mints its number as:

```js
var num = 'PO-2024-0' + (50 + d.length);
```

Two problems, both real:

1. **It collides.** The number is derived from the array's LENGTH, so deleting
   any PO makes the next one reuse a number already issued. A purchase order
   number that is not unique is not a purchase order number.
2. **The year is hardcoded to 2024.** Every PO created today is stamped
   `PO-2024-…`.

This is recorded here rather than fixed, because the instruction was audit only.

---

## What this is NOT saying

- **Not that anyone should gate a payment write today.** Nothing was gated and
  nothing should be on the strength of an audit.
- **Not that SAIRNbiz needs a purchase-order module.** For a one-or-two-person
  shop the three-way match is often deliberately not run; the honest control at
  that size is a second pair of eyes, not a second system. **That is a product
  decision, and it belongs to Michael, not to this document.**
- **Not that the absence is a defect in the accounting.** The ledger postings
  are correct, paired, and idempotent. What is missing is *evidence that the
  obligation was real*, which is a different layer entirely.

## The smallest thing that would change the answer

**StoneDesk only needs a key.** A `po_num` on the receiving record and on the
invoice would make all three joinable, and a report — not a gate — could then
show POs with no receipt, receipts with no PO, and amount differences between
the two. That is a report-only instrument of exactly the kind this platform
already has several of, and it becomes possible the moment one field exists.

**SAIRNbiz needs a decision before it needs code**, per above.

---

## Re-derive everything above

```
grep -n "function saveBill\|function sbPayBill" sairnbiz.html
grep -ciE "purchase order|receiving|packing slip|bill of lading" sairnbiz.html
grep -n "@REGISTER module=purchase-orders" stonedesk.html
grep -n "window.sdPOCreate\|window.sdRecvLog" stonedesk.html
grep -cE "po_id|poId|purchase_order_id|receiving_id|recv_id|receipt_id" \
     stonedesk.html sairnbiz.html
```
