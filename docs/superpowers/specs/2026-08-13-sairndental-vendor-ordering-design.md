# SAIRNdental Vendor/Supply Ordering — Design Spec

**Date:** 2026-08-13
**Status:** Approved, ready for implementation planning

## Problem

SAIRNdental has no way to browse dental supplies/PPE/materials across real
vendors, track stock on hand, or place and log purchase orders. Every
other resource in the app (patients, appointments, billing) is fully
built; purchasing/supply management doesn't exist at all. StoneDesk (a
sibling SAIRN app) already has a real, working vendor-ordering module
(`panel-vendorcat`) that this feature mirrors in shape, adapted to real
dental vendors and dental-practice product categories.

## Reference Implementation (verified against the real code)

StoneDesk's `panel-vendorcat` (`stonedesk.html:6895-6954`, backing JS
`stonedesk.html:21031-22310`):
- `VENDORS` object: 5 real named vendors, each with `name`/`logo`/
  `website`/`phone`/`email`/`desc`/`products[]` (id/name/sku/cat/price/
  unit per product), ~25 products per vendor.
- Vendor tabs + category tabs, `renderVendor()` renders the active
  vendor's filtered product list with cross-vendor price-comparison
  badges ("Save $X at [vendor]" / "Best Price"), computed by matching
  product name (first 3 words) or exact SKU across all vendors.
- `sdCart` (localStorage-backed): `cartAdd()`/`cartUpdate()`/`cartClear()`,
  `renderCart()` shows items + running total.
- `vendorPlaceOrder()`: builds an itemized `mailto:` link to the active
  vendor, optionally increments matching `sdInventory` stock quantities
  (confirm-prompted), clears the cart. Wrapped by a later patch
  (`stonedesk.html:22289-22309`) that records the order into
  `sdOrderHistory` (localStorage, capped at 200 entries) before the
  original function runs.
- `sdPricingRules` (localStorage): vendor-level discount %, category-level
  discount % (per vendor+category), product-level price override —
  `sdGetEffectivePrice()` applies vendor discount first, then stacks the
  category discount on the discounted price; a product override wins
  outright over both tiers.
- `vendorUpdateKPIs()`/`vendorSpendReport()`: YTD spend, savings, active
  deals, low-stock count, spend-by-vendor breakdown, "Claude Spend
  Analysis" AI button.
- `sdInventory` is StoneDesk's separate Shop Supplies stock-tracking data
  source, cross-referenced by SKU for low-stock badges.

## Current State — SAIRNdental (verified against the real code)

- 12 panels exist today, in 4 sidebar sections: **Overview** (Dashboard),
  **Patients** (Patients, Insurance Capture, Referrals, Complaints),
  **Practice Setup** (Providers, Operatories, Provider Hours, Procedure
  Types, Coverage Rules), **Scheduling** (Booking Settings, Pending
  Requests, Appointments), **Billing** (Billing). Nothing related to
  vendors, supplies, stock, or purchasing exists anywhere in the file.
- `sairndental.html`'s existing resources (`dnt_patients` etc.) that DO
  sync to the server go through `sdnData(action, resource, payload)` →
  `api/sd-data.js`'s cross-app `RESOURCES` allowlist and a generic
  `dnt_`-prefixed read/write block. This feature does not touch that path
  at all (see Scope — local-only, no new synced resource).
- No edit flow exists anywhere in this app (matches the platform-wide
  convention already documented in this session's other SAIRNdental
  spec) — this feature follows the same add/remove-only convention.

## Scope

**In scope:**
- New `panel-vendorcat` (Vendor Catalog): 5 real named vendors — Henry
  Schein Dental, Patterson Dental, Benco Dental, Darby Dental Supply,
  Burkhart Dental — no fabricated local/national tier distinction (the
  user explicitly confirmed dental distribution doesn't have that
  structure the way StoneDesk's stone vendors do). ~20-25 representative
  products per vendor, real dental-practice categories: PPE, Impression
  Materials, Restorative Materials, Sterilization & Infection Control,
  Disposables, Instruments, Anesthetics, Preventive/Hygiene. Product
  names/SKUs/prices are a realistic representative catalog (same
  disclosed nature as StoneDesk's existing catalog — not live-synced
  vendor pricing; dental distributors don't publish public list prices).
- Vendor tabs + category tabs, cross-vendor price-comparison badges
  (same matching logic as StoneDesk's).
- Editable per-vendor rep contact (`rep_name`/`phone`/`email`), blank by
  default — differs from StoneDesk's hardcoded per-vendor contact, since
  real dental distribution runs through an assigned rep, not one
  universal company line (see Design section for the blocking behavior
  this creates on Place Order until filled in).
- Cart (add/update/clear, running total), "Place Order" via `mailto:` +
  local order history (capped at 200), optional stock-quantity
  auto-increment on order (confirm-prompted).
- New `panel-supplies` (Supplies): stock-on-hand tracking — item name,
  category, quantity, reorder threshold, unit cost, vendor. Low-stock
  badge cross-referenced by SKU in the Vendor Catalog panel, same pattern
  as StoneDesk's `sdInventory`.
- 3-tier negotiated pricing: vendor discount %, category discount %,
  product override — same stacking logic as StoneDesk's
  `sdGetEffectivePrice()`.
- AI features: per-product "Compare" button, Spend Report panel with
  "Claude Spend Analysis" button — both call the shared Claude proxy the
  same way every other AI button in this app already does.
- New sidebar section, **Supplies**, with two entries: Supplies,
  Vendor Catalog — placed after the existing Billing section.

**Explicitly out of scope:**
- No server sync for any new data (catalog, cart, stock, order history,
  pricing rules) — all localStorage, matching StoneDesk's actual reference
  feature exactly. No changes to `api/sd-data.js` or any SQL schema file.
- No real purchasing/checkout integration with any vendor's actual
  ordering system — `mailto:` only, same as StoneDesk.
- No edit flow for stock items, catalog products, or order history —
  matches this app's platform-wide add/remove-only convention.
- No live/real-time vendor pricing sync — catalog prices are static,
  editable only via the negotiated-pricing override system.

## Design

### Data model (all localStorage, all client-only)

```js
// Static catalog (not user-editable, ships with the app — same as StoneDesk's VENDORS).
// Note: phone/email are intentionally NOT hardcoded per vendor (see below) --
// website is a real, stable, verifiable company domain; name/desc are real/
// accurate; products/prices are a representative catalog (see Scope).
var DNT_VENDORS = {
  henryschein: { name:'Henry Schein Dental', logo:'🦷', website:'https://www.henryschein.com', desc:'...', products:[ {id,name,sku,cat,price,unit}, ... ] },
  patterson: { ... }, benco: { ... }, darby: { ... }, burkhart: { ... }
};

// User data (localStorage keys, prefixed dnt_ matching this app's convention)
dnt_supplies_list      // [{id, name, category, qty, reorder_threshold, unit_cost, vendor_sku, ...}]
dnt_vendor_cart         // {productId: qty}
dnt_vendor_order_history // [{id, date, vendor, items:[...], total}], capped at 200
dnt_vendor_pricing_rules // {vendorDiscounts:{}, categoryDiscounts:[], productOverrides:{}}
dnt_vendor_contacts     // {vendorKey: {rep_name, phone, email}} -- blank until the practice fills in their actual assigned rep (see "Vendor contact info" below)
```

### Vendor Catalog panel

Structurally identical to StoneDesk's `panel-vendorcat`: vendor tabs,
category tabs, product list with price-comparison badges, qty input +
Add button per product, cart summary card, Place Order button. Category
list (dental-specific, replacing StoneDesk's blades/abrasives/tooling/
adhesives/chemicals/hardware/safety): PPE, Impression Materials,
Restorative Materials, Sterilization & Infection Control, Disposables,
Instruments, Anesthetics, Preventive/Hygiene.

**Vendor contact info (differs from StoneDesk's reference):** real
distributors of this type work through an assigned territory rep, not
one universal company phone/email — so unlike StoneDesk's hardcoded
`phone`/`email` per vendor, this panel shows the vendor's real website
domain (stable, verifiable) plus an "Add rep contact" prompt/edit action
that writes `rep_name`/`phone`/`email` into `dnt_vendor_contacts` for
that vendor key. Until filled in, the vendor header shows "No rep contact
on file yet" instead of a phone/email link. `vendorPlaceOrder()`'s
`mailto:` step requires a real email to be set — if the active vendor has
no `email` in `dnt_vendor_contacts`, the button shows a toast ("Add this
vendor's rep contact info before placing an order") instead of opening a
`mailto:` link to nowhere.

### Supplies panel

Structurally identical to StoneDesk's Shop Supplies panel: add-item form
(name, category, qty, reorder threshold, unit cost, vendor), KPI row
(SKUs tracked, low-stock count, stock value), table with low-stock
indicator, CSV export, print.

### Cart, ordering, and pricing logic

Same functions/shapes as StoneDesk, renamed to this app's convention
(`dntCartAdd`, `dntVendorPlaceOrder`, `dntGetEffectivePrice`, etc.) —
exact signatures and behavior to be finalized during planning, following
StoneDesk's real implementation as the reference (including the
order-history-recording wrapper pattern, since that's how StoneDesk
itself layered the feature after the base cart/order flow shipped).

### AI features

Per-product "Compare" button and Spend Report's "Claude Spend Analysis"
button call this app's existing AI proxy path the same way every other
AI button in `sairndental.html` already does (same pattern used by, e.g.,
`scanDoc()` — real API call, not a placeholder).

### Navigation

New sidebar section `<div class="ss">Supplies</div>` after the existing
Billing section, with `sb-supplies` (Supplies) and `sb-vendorcat`
(Vendor Catalog) entries, matching this file's existing `nav('x')`
pattern exactly.

## Testing / Verification Plan

- `python tools/checkblocks.py sairndental.html` — must show
  `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0` after every step.
- Manual verification (no automated test runner exists for this file,
  matching its established convention): add a supply item below its
  reorder threshold, confirm the low-stock badge appears on the matching
  SKU in Vendor Catalog; add items to cart across 2+ vendors, confirm
  cart total and per-item math; place an order, confirm a `mailto:` link
  opens with correct itemized text, confirm order history records it,
  confirm stock quantities update when the increment prompt is accepted;
  set a vendor discount + category discount + product override and
  confirm `dntGetEffectivePrice()` stacks them correctly (vendor first,
  then category on the discounted price, product override wins outright);
  confirm price-comparison badges appear correctly across vendors for
  matching SKUs/names; confirm Place Order is blocked with the correct
  toast when the active vendor has no rep email on file, and succeeds
  once one is added.

## Open Questions

None — all material design decisions were resolved during brainstorming
(local-only data; 5 real named vendors, no fake tier distinction; stock
tracking included; negotiated pricing included; AI features included;
representative, disclosed-as-such catalog data).
