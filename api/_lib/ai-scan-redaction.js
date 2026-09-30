// api/_lib/ai-scan-redaction.js
//
// ONE DECLARED MAP of every resource that persists RAW MODEL OUTPUT, and one
// place that redacts it on the way into the row.
//
// ── WHY THIS EXISTS, AND WHY A MAP RATHER THAN A NAME ─────────────────────
// api/sd-data.js already carried this idea, scoped to one app and inlined:
// MECH_SCANNED_TEXT, three entries, defined inside the SAIRNmechanical branch.
// Its own history is the argument for this file. The gate before it read
// `if (resource === 'mech_docs')` -- a resource NAME rather than a property of
// the data -- so mech_takeoffs, four lines away in the same table map and
// storing the same shape, went ungated for as long as it existed. Widening a
// name-scoped gate to a map fixed one app. The same shape was live in five
// others.
//
// A resource earns an entry here on PROVENANCE, not on which app it belongs
// to: the field holds text a MODEL produced, usually over a PHOTOGRAPH, and
// nobody chose what went into it. A photograph of a job site carries whatever
// was on the whiteboard, the work order taped to the unit, or the sign on the
// van.
//
// ── THE DECIDING TEST, APPLIED PER FIELD AND WRITTEN DOWN PER RESOURCE ────
// REDACT if the field is model prose: the value is (or is a slice of) the
//   text the model returned, and the app would still work if a name in it
//   were replaced.
// DO NOT REDACT if the field is the DELIVERABLE: a number the customer is
//   quoted, a model number, a serial, a parsed quantity, a brand. Removing a
//   digit from a deliverable is not a safer failure -- it is a different way
//   to lose the record, and mech_checks already carries that reasoning: a
//   cheque register with the payee redacted is not a register.
//
// Every entry below names the file and the line the record is built at, so the
// next reader can re-derive rather than trust this list.
'use strict';

const mechRedact = require('./mech-redact');

// resource -> [fields]. Ordered by app. The comment on each line is the
// deciding test for THAT resource, not a restatement of the rule.
const AI_SCANNED_TEXT = {
  // ── SAIRNmechanical (already gated before this file; moved here whole) ──
  // Model output over a photographed plan or work order.
  mech_docs: ['text'],
  mech_takeoffs: ['text'],
  // Model output over a base64 IMAGE seeded at sairnmechanical.html:1416-1417
  // and generated at :1435. The deliverable is unaffected: :1441 shares from
  // memory, never from the stored row.
  mech_quotes: ['text'],

  // ── SAIRNbuild ─────────────────────────────────────────────────────────
  // sairnbuild.html:3666-3667 fpSave(). `full` is the model's answer over a
  // job-site PHOTOGRAPH verbatim; `summary` is its first 140 characters with
  // newlines flattened -- a slice of the same text, so redacting one and not
  // the other would leave the name in the field that is shown in the list.
  bld_photo_analyses: ['full', 'summary'],

  // ── SAIRNgrounds ───────────────────────────────────────────────────────
  // sairngrounds.html:3490-3492. Model prose over a progress PHOTOGRAPH.
  // `photo_b64` is the image itself and is NOT text; `qc_status`,
  // `captured_by` and the ids are app-set.
  grd_progress_photos: ['ai_analysis'],
  // sairngrounds.html:4183-4189. Seven concatenated model sections.
  grd_ecosystem_reports: ['summary'],
  // sairngrounds.html:4833. `raw` is the model's reply verbatim. `items` is
  // the parsed bullet list of FOOD ITEMS and is the deliverable -- an
  // inventory with the product names removed is not an inventory.
  msb_food_scans: ['raw'],

  // ── SAIRNscape ─────────────────────────────────────────────────────────
  // sairnscape.html:3426-3429. Same shape and same reasoning as
  // grd_progress_photos; the two panels are siblings.
  scp_progress_photos: ['ai_analysis'],

  // ── SAIRNroofing ───────────────────────────────────────────────────────
  // sairnroofing.html:5348. `ai_analysis` is the model's raw read of a
  // measurement photo. `parsed_quantities` are the NUMBERS the estimate is
  // built from and are the deliverable -- they are never touched.
  rf_photos: ['ai_analysis'],

  // ── StoneDesk ──────────────────────────────────────────────────────────
  // stonedesk.html:30425. A model-written one-sentence summary of the last
  // eight turns of a conversation, stored to be fed back into later prompts.
  // Nobody reads it, which is exactly why an unredacted name in it survives.
  memory: ['memory_text'],
};

// ── DELIBERATELY NOT IN THE MAP, each with the reason it was excluded ─────
// Kept in code rather than in a doc so the next person to widen the map reads
// the refusals at the same time as the entries. Names only -- no behaviour.
const DELIBERATELY_EXCLUDED = {
  bld_ai_chat:
    'NEVER REACHES A SERVER. api/_resources/sairnbuild.js:158 excludes it from '
    + 'sync as "an unbounded conversation transcript, not a business record", '
    + 'so there is no row to redact. The exposure is LOCAL storage only and a '
    + 'server-side gate cannot reach it. Registered, not gated here.',
  sd_stonehead_history:
    'NEVER REACHES A SERVER, same as bld_ai_chat -- '
    + 'api/_resources/stonedesk.js:334 excludes it as "an AI conversation '
    + 'transcript". Local only.',
  msb_bottle_scans:
    'NO MODEL PROSE IS STORED. sairngrounds.html:4780 stores brand_read and '
    + 'fill_pct, both scalars extracted by msbParseScanResult(), plus a note '
    + 'the APP computes from local cost data. The brand is the deliverable.',
  grd_quotes:
    'THE MODEL TEXT IS THE DELIVERABLE. sairngrounds.html:4258-4262 splits the '
    + 'design text into quote LINE ITEMS the customer signs. Redacting a line '
    + 'description corrupts the quote -- the mech_quotes-versus-mech_checks '
    + 'distinction, on the mech_checks side.',
  quotes:
    'Same record as grd_quotes, written through the shared `quotes` resource '
    + 'at sairngrounds.html:4263. Same reason.',
  rf_jobs:
    'FALSE POSITIVE OF THE DERIVATION, confirmed by reading. '
    + 'sairnroofing.html:5350 stores measurement_correction with numeric '
    + 'quantities and a HARDCODED reason string. The enclosing function reads '
    + 'the AI text for the sibling rf_photos write; this record does not carry '
    + 'it.',
  sd_negotiated_prices:
    'FALSE POSITIVE. stonedesk.html:27331 pmImportCSV stores {sku: price} '
    + 'parsed from a PASTED CSV. The identifier `raw` there is the CSV text, '
    + 'and it collided with a module-level `raw` that does hold model output.',
  sd_ai_counts:
    'FALSE POSITIVE. stonedesk.html:4840 stores two integers, today and total. '
    + 'The enclosing function also holds the model reply, which is what the '
    + 'derivation saw.',
  sd_intake:
    'NOT A MODEL WRITE. stonedesk.html:39869 is a LOCAL CACHE of a server '
    + 'read. It does carry customer PII, which is a separate question with a '
    + 'separate answer, and not this one.',
  sd_market_history:
    'NUMBERS, NOT TEXT. stonedesk.html:41515 stores MI_STATE.history, a list '
    + 'of market index figures with their fetch dates. The derivation saw it '
    + 'because the enclosing module also holds model output; no field on this '
    + 'record is model prose.',
  shared_knowledge:
    'A WORD BAG, NOT PROSE, AND A NAMED RESIDUAL RISK. '
    + 'stonedesk.html:24046 stores up to 60 lowercased words of five or more '
    + 'letters taken from model text, so a surname CAN survive. It is not '
    + 'gated here because redactDocumentText() works on prose and would have '
    + 'to be replaced by a per-word filter, which is a different change. '
    + 'Registered as an open finding rather than half-done.',
};

/**
 * Redact every declared field on a payload, or return it untouched.
 *
 * Returns the payload to STORE. When anything was redacted the returned object
 * also carries a `redaction` block -- ON THE ROW, not merely in the response --
 * so a reader of the stored record can see what the pass did AND what it could
 * not do. A row that looks redacted with no account of its limits is the false
 * confidence this whole mechanism exists to avoid.
 *
 * A declared field that is absent or not a string is SKIPPED, not coerced. A
 * missing field is not a redaction failure, and `String(undefined)` would
 * store the word "undefined" in a business record.
 */
function redactAiFields(resource, payload, nowISO) {
  const fields = AI_SCANNED_TEXT[resource];
  if (!fields || !payload || typeof payload !== 'object') return payload;

  const out = Object.assign({}, payload);
  const redactions = [];
  let complete = true;
  const notes = [];
  let touched = false;

  for (const f of fields) {
    if (typeof payload[f] !== 'string' || payload[f] === '') continue;
    const red = mechRedact.redactDocumentText(payload[f]);
    out[f] = red.text;
    touched = true;
    if (red.redactions && red.redactions.length) {
      for (const r of red.redactions) redactions.push({ field: f, kind: r });
    }
    if (red.complete === false) complete = false;
    if (red.note) notes.push(f + ': ' + red.note);
  }
  if (!touched) return payload;

  out.redaction = {
    applied_at: typeof nowISO === 'function' ? nowISO() : new Date().toISOString(),
    fields: fields.slice(),
    redactions: redactions,
    complete: complete,
    note: notes.length ? notes.join(' | ') : mechRedact.NOT_REDACTED_NOTE,
  };
  return out;
}

module.exports = { AI_SCANNED_TEXT, DELIBERATELY_EXCLUDED, redactAiFields };
