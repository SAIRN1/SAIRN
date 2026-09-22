// api/_lib/mech-redact.js
// ---------------------------------------------------------------------------
// REDACT THE DIRECT IDENTIFIERS OUT OF SCANNED-DOCUMENT TEXT BEFORE IT IS
// STORED. Pure -- no I/O, no fetch, no LLM. Same functional-core split as
// api/_lib/dnt-rollup.js and api/_lib/sen-payroll.js: the gate, the write and
// the 503 live in the caller.
//
// ── THE GAP, READ RATHER THAN ASSUMED ─────────────────────────────────────
// `sairnmechanical.html`'s `scanDoc()` photographs a document and asks the
// model, in its own words, to
//
//     "EXTRACT: Every field -- names, dates, amounts, codes, reference numbers"
//
// over work orders, maintenance contracts, permits, inspection reports and
// INVOICES. `saveDoc()` then takes `el.textContent` -- the raw model output,
// verbatim -- and stores it as `{id, date, text}`, and `mechPushRecord` syncs
// that row to the server. Nothing redacted anything. A customer's name, site
// address and phone number went to a server table because a technician
// photographed a work order.
//
// ── WHY THIS RUNS SERVER-SIDE, NOT ONLY IN THE APP ────────────────────────
// A client-side redactor is a convenience, never a boundary -- the same
// sentence this platform already applies to hidden buttons and role checks.
// `api/sd-data.js` calls this on the `mech_docs` write path, so text that
// reaches the table has been through it regardless of what the caller sent.
// The app calls it too, so the LOCAL copy is redacted as well; that second
// call is the convenience and the server one is the boundary.
//
// ── WHAT IT REDACTS, AND WHY EACH ONE IS DETERMINISTIC ────────────────────
// Every pattern below is one a regular expression can actually recognise
// without guessing. Nothing here infers meaning from context.
//
//   EMAIL          a structural shape, unambiguous.
//   PHONE          NANP-shaped, with enough punctuation or grouping to tell it
//                  from a part number. See the comment on the pattern.
//   SSN/EIN        ###-##-#### and ##-#######, both fixed shapes.
//   CARD           13-19 digits in one run, optionally spaced or hyphenated.
//   LABELLED NAME  a LINE whose label is a person role -- `Customer: ...`,
//                  `Technician: ...`. THE LABEL is what is matched, never the
//                  name, which is the only way to find a name deterministically.
//   ADDRESS        a street line: number + words + a street-type suffix.
//
// ── WHAT IT DOES NOT REDACT, AND THIS IS THE HALF THAT MATTERS ────────────
// A PERSON'S NAME WRITTEN IN PROSE IS NOT FOUND. "Spoke to Dave about the
// condenser" survives, and no regular expression will reliably find it without
// a dictionary that would also redact "Carrier", "Trane" and "York". The
// output therefore carries `complete: false` ALWAYS, and a caller that renders
// this as "redacted" rather than as "redacted for the patterns below" has
// undone the honesty this file exists for.
//
// AMOUNTS ARE DELIBERATELY KEPT. A mechanical contractor's document store is
// quotes, invoices and takeoffs; the money is the content, not the leak.
// Redacting it would make the feature useless and would be this file deciding
// something it was not asked to.
//
// EQUIPMENT SERIALS AND MODEL NUMBERS ARE KEPT for the same reason, and the
// CARD pattern is bounded to 13-19 digits precisely so a long equipment serial
// is not swallowed -- see the note there. A redactor that eats the document's
// own subject matter gets switched off, and a redactor that is switched off
// redacts nothing.
// ---------------------------------------------------------------------------

'use strict';

// ── THE PATTERNS. Each returns the replacement token it writes. ────────────
// Order matters: EMAIL runs before PHONE and CARD so the digits inside an
// address-like local part are not clipped first, and CARD runs before PHONE so
// a 16-digit run is not partly eaten as a phone number.
const RULES = [
  {
    kind: 'EMAIL',
    re: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
    token: '[EMAIL REDACTED]',
  },
  {
    // 13-19 digits in ONE run, allowing single spaces or hyphens between
    // groups. BOUNDED AT 19 ON PURPOSE: an unbounded `\d{13,}` swallows long
    // equipment serials and EPA certificate numbers, which are the document's
    // actual subject. 13-19 is the payment-card range; anything longer is far
    // more likely to be equipment than money.
    kind: 'CARD',
    re: /\b(?:\d[ -]?){13,19}\b/g,
    token: '[CARD/ACCOUNT REDACTED]',
  },
  {
    kind: 'SSN',
    re: /\b\d{3}-\d{2}-\d{4}\b/g,
    token: '[SSN REDACTED]',
  },
  {
    kind: 'EIN',
    re: /\b\d{2}-\d{7}\b/g,
    token: '[EIN REDACTED]',
  },
  {
    // NANP with STRUCTURE -- parentheses, dots, hyphens, or a leading +1/1.
    // A BARE TEN-DIGIT RUN IS NOT MATCHED, deliberately: model and serial
    // numbers on a spec sheet are bare digit runs, and eating them is the
    // failure that gets a redactor disabled.
    kind: 'PHONE',
    re: /(?:\+?1[ .-])?(?:\(\d{3}\)[ .-]?|\d{3}[ .-])\d{3}[ .-]\d{4}\b/g,
    token: '[PHONE REDACTED]',
  },
  {
    // A street line: house number, one to five words, then a street type.
    // Anchored on the TYPE, which is a closed vocabulary, rather than on
    // "looks like an address", which is not.
    kind: 'ADDRESS',
    re: new RegExp(
      '\\b\\d{1,6}\\s+(?:[A-Za-z0-9.\'-]+\\s+){0,5}'
      + '(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|'
      + 'Ct|Court|Way|Pl|Place|Ter|Terrace|Cir|Circle|Hwy|Highway|Pkwy|Parkway|'
      + 'Suite|Ste|Unit|Apt)\\b\\.?', 'gi'),
    token: '[ADDRESS REDACTED]',
  },
];

// A LINE whose label names a person. The LABEL is matched, never the name --
// matching a name would need a dictionary, and a dictionary that knows "Dave"
// also knows "Carrier", "Trane" and "York", which are equipment brands this
// document store exists to record.
const LABELLED_NAME = new RegExp(
  '^([ \\t]*(?:customer|client|contact|technician|tech|installer|owner|'
  + 'occupant|tenant|signed[ _]?by|signature|attn|attention|prepared[ _]?for|'
  + 'bill[ _]?to|ship[ _]?to|homeowner|caller|requested[ _]?by)'
  + '[ \\t]*[:\\-][ \\t]*)(.+)$', 'gim');

const NOT_REDACTED_NOTE =
  'A person\'s name written in ordinary prose is NOT redacted by this pass -- '
  + 'only labelled name fields, emails, phones, addresses, SSN/EIN and '
  + 'card-length digit runs are. Amounts, model numbers and equipment serials '
  + 'are kept deliberately, because they are the document\'s subject rather '
  + 'than its leak. Treat this text as REDUCED, never as anonymous.';

/**
 * @param {string} text  raw extracted document text
 * @returns {object}
 *   text        {string}  the redacted text
 *   redactions  {Array}   [{kind, count}], only kinds that actually fired
 *   redacted    {boolean} did anything change
 *   complete    {boolean} ALWAYS false -- see the header
 *   note        {string}  what was not redacted, carried WITH the record
 *
 * NON-STRING INPUT IS NOT AN ERROR AND IS NOT SILENTLY EMPTIED. A caller that
 * hands this a number or null gets '' back with `redacted: false`, so a write
 * path cannot accidentally store the string "null" or lose the field's shape.
 */
function redactDocumentText(text) {
  const counts = Object.create(null);
  const bump = (kind, n) => { counts[kind] = (counts[kind] || 0) + n; };

  if (typeof text !== 'string' || text === '') {
    return {
      text: '', redactions: [], redacted: false, complete: false,
      note: NOT_REDACTED_NOTE,
    };
  }

  let out = text;

  // Labelled names first: the line-anchored rule would otherwise see a value
  // already replaced by a token and leave the label pointing at nothing.
  out = out.replace(LABELLED_NAME, (m, label, value) => {
    const v = String(value).trim();
    if (!v) return m;
    // ── ALREADY REDACTED IS NOT A NEW FINDING (caught by the idempotency arm)
    // Without this the rule matches its OWN output: `Customer: [NAME
    // REDACTED]` still has a person label and a non-empty value, so a re-saved
    // row produced identical text and a SECOND count. The text was never
    // wrong; the COUNT was, and the count is what a record would carry as
    // "how many identifiers this document held". The RULES loop below already
    // had this guard and this one did not.
    if (v.indexOf('REDACTED]') !== -1) return m;
    bump('LABELLED_NAME', 1);
    return label + '[NAME REDACTED]';
  });

  RULES.forEach((rule) => {
    out = out.replace(rule.re, (m) => {
      // A run that is ALREADY a token must not be re-counted. Tokens contain
      // no digits or @, so in practice this cannot fire -- it is here because
      // "in practice it cannot" is how the next pattern added to this list
      // quietly double-counts.
      if (m.indexOf('REDACTED]') !== -1) return m;
      bump(rule.kind, 1);
      return rule.token;
    });
  });

  const redactions = Object.keys(counts).sort()
    .map((k) => ({ kind: k, count: counts[k] }));

  return {
    text: out,
    redactions: redactions,
    redacted: redactions.length > 0,
    // NEVER TRUE. Stated as a constant rather than computed, because there is
    // no input for which this pass is complete and a field that could be true
    // invites a caller to branch on it.
    complete: false,
    note: NOT_REDACTED_NOTE,
  };
}

module.exports = { redactDocumentText, NOT_REDACTED_NOTE };
