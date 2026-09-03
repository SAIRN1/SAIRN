// api/_lib/roofing-supplier-match.js
// SAIRNroofing B6 -- supplier purchase order / receipt / invoice reconciliation.
//
// PURE -- no I/O.
//
// ── WHAT THIS IS, AND WHAT IT DELIBERATELY IS NOT ───────────────────────────
// docs/2026-09-02-competitive-gap-status-rederived.md records B6 -- "Supplier
// EDI (PO / ASN / invoice)" -- as the ONLY genuinely open SAIRNroofing item,
// verified absent word-boundary on `edi`, `asn`, `punchout`. Re-verified before
// building rather than taken from the doc: `supplier` and `vendor` each appear
// ZERO times in sairnroofing.html, and the single `receiving` hit is inside a
// patent-claim comment. There is no purchasing capability at all.
//
// THIS IS NOT EDI TRANSPORT, and saying so is the point. An X12 850/856/810
// exchange needs a trading-partner agreement with ABC Supply, Beacon or SRS,
// an AS2 or VAN connection, and a certification cycle with each partner. None
// of that is engineering this app can do alone, and shipping a screen that
// says "EDI" without it would be the same claim-without-substance this
// codebase keeps finding.
//
// What IS buildable, and is where the money actually is, is the THREE-WAY
// MATCH those documents exist to enable: what was ordered, what arrived, what
// was billed -- and where those three disagree. That reconciliation is
// identical whether the documents arrive over EDI, as a PDF, or typed off a
// paper packing slip. A contractor's real loss is paying an invoice for
// material that never showed up, and it does not become a different loss
// because the invoice came by email.
//
// So: the documents are modelled the way EDI models them -- three documents
// referencing one PO number -- and the transport is left as the integration it
// is. If a trading partner is ever signed, it fills these same records.
//
// ── UNKNOWN IS NOT SHORT, AND IT IS NOT ZERO ────────────────────────────────
// The rule this file exists to keep. If NO receipt has been recorded against a
// PO line, the line is `unknown` -- not `short_received`. Nobody scanning the
// delivery is a different fact from the delivery not arriving, and only one of
// them is the supplier's problem. Reporting the first as the second sends a
// contractor to argue with a supplier about a truck that did arrive.
//
// The mirror also holds: a line with no invoice yet is `unbilled`, which is a
// normal state mid-job, not a discrepancy to chase.
//
// ── DISCREPANCIES ARE NAMED SEPARATELY AND NEVER NETTED ─────────────────────
// Over-invoiced on one line and short on another is TWO problems, not zero. A
// single "variance" number that nets them is how a $4,000 over-bill hides
// behind a $4,000 short delivery. Every line carries its own findings and the
// summary counts them by class.
//
// ── IT DOES NOT APPROVE PAYMENT ─────────────────────────────────────────────
// Same boundary as the refrigerant scope and the fall-protection board: this
// reports what disagrees and by how much. Whether to pay is a person's call
// with a phone in their hand, and an app that answers it has claimed an
// authority nobody gave it.

'use strict';

// Every tolerance is STATED. There is no silent default that quietly forgives
// a variance -- a shop that has not chosen a tolerance gets exact matching,
// which is the conservative answer and is visible in the output.
const DEFAULT_QTY_TOLERANCE = 0;
const DEFAULT_PRICE_TOLERANCE = 0;

const DOC_TYPES = { order: true, receipt: true, invoice: true };

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

// A recorded number, or null. NOT Number() directly: Number('') and
// Number(null) are both 0, so an empty quantity field would read as a genuine
// zero -- "we received none of it" -- when it means nobody wrote anything
// down. That distinction is the whole point of this module.
function num(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

// Lines are matched on the supplier's item code where there is one, falling
// back to a normalised description. Not on position: a supplier's invoice does
// not list lines in the order they were ordered, and matching by index would
// silently compare shingles to fasteners.
function lineKey(l) {
  const code = String((l && (l.item_code || l.sku)) || '').trim().toLowerCase();
  if (code) return 'c:' + code;
  const desc = String((l && l.description) || '').trim().toLowerCase().replace(/\s+/g, ' ');
  return desc ? 'd:' + desc : '';
}

function sumBy(docs, key) {
  // Returns a map of lineKey -> { qty, amount, seen } summed across documents.
  // `seen` is what separates "recorded as zero" from "never recorded", and it
  // is why this cannot be a plain numeric sum.
  const out = Object.create(null);
  (docs || []).forEach(function (d) {
    ((d && d.lines) || []).forEach(function (l) {
      const k = lineKey(l);
      if (!k) return;
      const e = out[k] || (out[k] = { qty: null, amount: null, seen: 0, description: l.description || null, item_code: l.item_code || l.sku || null });
      e.seen += 1;
      const q = num(l[key]);
      if (q !== null) e.qty = (e.qty === null ? 0 : e.qty) + q;
      const amt = num(l.unit_price);
      if (amt !== null && q !== null) e.amount = (e.amount === null ? 0 : e.amount) + amt * q;
    });
  });
  return out;
}

function within(a, b, tol) {
  return Math.abs(a - b) <= Math.abs(tol || 0);
}

// The three-way match for ONE purchase order.
//
//   order    -- exactly one document, doc_type 'order'
//   receipts -- zero or more 'receipt' documents against the same po_number
//   invoices -- zero or more 'invoice' documents against the same po_number
//
// Returns per-line findings plus counts by class. Never a single netted
// variance, and never an approve/reject verdict.
function matchOrder(docs, opts) {
  const o = opts || {};
  const qtyTol = Number.isFinite(o.qty_tolerance) ? o.qty_tolerance : DEFAULT_QTY_TOLERANCE;
  const priceTol = Number.isFinite(o.price_tolerance) ? o.price_tolerance : DEFAULT_PRICE_TOLERANCE;

  const all = Array.isArray(docs) ? docs.filter(function (d) { return d && DOC_TYPES[d.doc_type]; }) : [];
  const orders = all.filter(function (d) { return d.doc_type === 'order'; });
  if (orders.length === 0) {
    return refuse('NO_ORDER',
      'There is no purchase order for this reference, so there is nothing to match against. ' +
      'An invoice with no order behind it is exactly the case worth investigating -- it is not a match failure, it is an unordered charge.');
  }
  if (orders.length > 1) {
    // Two orders under one PO number is a data problem, and picking one would
    // silently halve the ordered quantity.
    return refuse('DUPLICATE_ORDER',
      'More than one purchase order is recorded under this reference. Reconciliation cannot proceed until one of them is corrected -- matching against either would understate what was ordered.');
  }
  const receipts = all.filter(function (d) { return d.doc_type === 'receipt'; });
  const invoices = all.filter(function (d) { return d.doc_type === 'invoice'; });

  const ord = sumBy(orders, 'qty_ordered');
  const rec = sumBy(receipts, 'qty_received');
  const inv = sumBy(invoices, 'qty_invoiced');

  const keys = Object.keys(Object.assign(Object.create(null), ord, rec, inv)).sort();
  const lines = keys.map(function (k) {
    const O = ord[k], R = rec[k], I = inv[k];
    const findings = [];

    const orderedQty = O ? O.qty : null;
    const receivedQty = R ? R.qty : null;
    const invoicedQty = I ? I.qty : null;

    // 1. On the invoice, never ordered. The expensive one.
    if (!O && I) findings.push({ code: 'not_ordered', detail: 'invoiced but not on the purchase order' });

    // 2. Ordered, and nothing invoiced yet. Normal mid-job, reported so it is
    //    visible, not flagged as a problem.
    if (O && !I) findings.push({ code: 'unbilled', detail: 'ordered, no invoice recorded yet' });

    // 3. RECEIPT UNKNOWN vs SHORT. The distinction this module exists for.
    if (O && receipts.length === 0) {
      findings.push({ code: 'receipt_unknown', detail: 'no receipt has been recorded against this order at all -- this is not evidence the material did not arrive' });
    } else if (O && !R) {
      findings.push({ code: 'receipt_unknown', detail: 'receipts exist for this order but none names this line -- nobody wrote it down either way' });
    } else if (O && R && orderedQty !== null && receivedQty !== null && !within(orderedQty, receivedQty, qtyTol)) {
      findings.push({
        code: receivedQty < orderedQty ? 'short_received' : 'over_received',
        detail: 'ordered ' + orderedQty + ', received ' + receivedQty,
        variance: receivedQty - orderedQty
      });
    }

    // 4. Invoiced more than received. The one that costs money.
    if (I && R && invoicedQty !== null && receivedQty !== null && invoicedQty > receivedQty + Math.abs(qtyTol)) {
      findings.push({
        code: 'over_invoiced_qty',
        detail: 'invoiced ' + invoicedQty + ', received ' + receivedQty,
        variance: invoicedQty - receivedQty
      });
    }
    // Invoiced against a line with no recorded receipt is NOT called
    // over-invoiced -- there is no receipt to compare to. It is reported as
    // unknown above and the invoice stands unverified, which is the true state.

    // 5. Price. Compared per unit, because comparing extended totals hides a
    //    price change behind a quantity change.
    const ordUnit = (O && O.qty) ? (O.amount === null ? null : O.amount / O.qty) : null;
    const invUnit = (I && I.qty) ? (I.amount === null ? null : I.amount / I.qty) : null;
    if (ordUnit !== null && invUnit !== null && !within(ordUnit, invUnit, priceTol)) {
      findings.push({
        code: 'price_variance',
        detail: 'ordered at ' + ordUnit.toFixed(4) + '/unit, invoiced at ' + invUnit.toFixed(4) + '/unit',
        variance: invUnit - ordUnit
      });
    } else if ((ordUnit === null || invUnit === null) && O && I) {
      findings.push({ code: 'price_unknown', detail: 'a unit price is missing on the order or the invoice, so no price comparison was made' });
    }

    return {
      key: k,
      item_code: (O && O.item_code) || (I && I.item_code) || (R && R.item_code) || null,
      description: (O && O.description) || (I && I.description) || (R && R.description) || null,
      ordered_qty: orderedQty,
      received_qty: receivedQty,
      invoiced_qty: invoicedQty,
      ordered_unit_price: ordUnit,
      invoiced_unit_price: invUnit,
      findings: findings,
      clean: findings.length === 0
    };
  });

  const counts = Object.create(null);
  lines.forEach(function (l) {
    l.findings.forEach(function (f) { counts[f.code] = (counts[f.code] || 0) + 1; });
  });

  return {
    ok: true,
    po_number: orders[0].po_number || null,
    supplier: orders[0].supplier || null,
    // Stated in the output so a reader can see what was forgiven.
    qty_tolerance: qtyTol,
    price_tolerance: priceTol,
    documents: { orders: orders.length, receipts: receipts.length, invoices: invoices.length },
    lines: lines,
    // Counted by CLASS, never netted into one variance -- over on one line and
    // short on another is two problems, not zero.
    counts: counts,
    clean_lines: lines.filter(function (l) { return l.clean; }).length,
    // Surfaced beside the rest rather than under it: a reconciliation that
    // buries how much of itself is unverified reads as a clean match.
    unverified_lines: lines.filter(function (l) {
      return l.findings.some(function (f) { return f.code === 'receipt_unknown' || f.code === 'price_unknown'; });
    }).length,
    // Deliberately absent: any approve / hold / pay recommendation. This
    // reports what disagrees. Whether to pay is a person's call.
    note: 'This is a reconciliation, not a payment decision. Unverified lines are not cleared lines.'
  };
}

module.exports = {
  DEFAULT_QTY_TOLERANCE,
  DEFAULT_PRICE_TOLERANCE,
  DOC_TYPES,
  lineKey,
  matchOrder
};
