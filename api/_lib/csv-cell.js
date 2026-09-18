// api/_lib/csv-cell.js
// ---------------------------------------------------------------------------
// ONE CSV CELL, ESCAPED FOR THE SPREADSHEET THAT WILL OPEN IT.
//
// Created 2026-09-17 after the hover auditor found the same unguarded cell
// construction in 13 files and 53 places -- one inline one-liner,
// copy-pasted:
//
//     '"' + String(c).replace(/"/g, '""') + '"'
//
// That is correct RFC 4180 quoting and it is NOT a defence against anything.
//
// ── WHAT THE DEFECT ACTUALLY IS ────────────────────────────────────────────
// Excel, LibreOffice Calc and Google Sheets all treat a cell whose first
// character is `=`, `+`, `-` or `@` as a FORMULA when the file is opened. So a
// customer name, a memo line, a complaint body -- any field a person can type
// into -- becomes executable content in the recipient's spreadsheet. The
// classic payload is `=cmd|'/c calc'!A0`, which is a DDE launch, not a
// calculation; `=HYPERLINK(...)` and `=IMPORTXML("http://…"&A1)` quietly
// exfiltrate the row it sits next to.
//
// THE QUOTES DO NOT HELP, and this is the part that makes the bug survive
// review. The importer strips the surrounding quotes as CSV syntax and then
// evaluates what is inside. Quoting solves commas and newlines. It has never
// had anything to do with formulas.
//
// ── THE FIX IS AN APOSTROPHE, AND IT IS CONDITIONAL ON PURPOSE ────────────
// Prefixing with `'` forces the cell to text. Applying it unconditionally to
// every cell starting with a dangerous character WOULD BREAK REAL EXPORTS:
// `roofing-gl-export.js` emits accounting journal lines, and a credit written
// as `'-50.00` arrives as TEXT -- every SUM in the accountant's spreadsheet
// silently stops counting it, which is a financial reporting error introduced
// by a security fix.
//
// So the guard fires only when the cell is NOT a number:
//
//     -50.00     Number() is finite  -> untouched, still a number
//     +1e5       Number() is finite  -> untouched
//     -1+1       Number() is NaN     -> "'-1+1", neutralised
//     =cmd|...   Number() is NaN     -> "'=cmd|...", neutralised
//     @SUM(A1)   Number() is NaN     -> neutralised
//
// A leading `=` is never a number, so `=` is always guarded. `-` and `+` are
// the only two characters where the distinction does any work, and they are
// exactly the two that appear in money.
//
// TAB AND CARRIAGE RETURN are in the dangerous set because a leading
// whitespace character is how a payload gets past a filter that only looks at
// `s[0] === '='`. `\t5` is still a number and passes through; `\t=cmd` does
// not.
//
// ── null AND undefined RENDER BLANK, AND THAT IS A SCOPE ADDITION ─────────
// Asked by the hover auditor on 2026-09-18: was this intentional, or did it ride
// along undocumented? INTENTIONAL, AND IT WAS UNDOCUMENTED -- both halves are
// true and the second is the auditor's point.
//
// IT IS A REAL BEHAVIOUR CHANGE, MEASURED RATHER THAN ASSUMED. Thirty of
// stonedesk's thirty-nine sites used a BARE `String(c)`, and:
//
//     '"' + String(null).replace(...) + '"'        ->   "null"
//     '"' + String(undefined).replace(...) + '"'   ->   "undefined"
//
// So those thirty exports wrote the literal text `null` into a cell. csvCell's
// `v == null ? '' : String(v)` writes a blank instead. The other nine sites and
// several apps already used `String(c == null ? '' : c)` and were unaffected --
// which is exactly why it slipped through: the majority of call sites agreed
// with the new behaviour and the minority that did not were the ones nobody
// diffed.
//
// WHY BLANK IS RIGHT. A cell containing `null` is the four-character STRING
// "null" to every spreadsheet that opens it. It sorts with text, it breaks a
// SUM over the column, it survives a copy-paste into a report, and it looks
// like data -- an accountant reading a charge column sees a value where there
// was none. A blank is what "absent" actually is. It also matches what this
// platform's own export layer already does: `api/_lib/dental-bi.js`'s coerce()
// maps undefined, null and '' to null BEFORE any conversion, and has since
// before this module existed. Diverging from that would have been the surprise.
//
// The two assertions in csv-cell.test.js are named as REGRESSION GUARDS rather
// than filed under ordinary inputs, so a future "simplification" back to a bare
// String() has something to fail against.
//
// ── WHY A MODULE HERE AND A COPY IN EACH APP ──────────────────────────────
// The single-file HTML apps cannot require() anything -- that is the whole
// shape of this platform -- so each one carries a named helper with this body
// rather than an inline expression. THE POINT OF THE NAME IS THE SWEEP:
// `tools/csv_formula_injection_check.py` can then assert that no raw cell
// construction remains anywhere and that every helper still carries the guard.
// Thirteen identical inline copies were unauditable; thirteen named functions
// are one grep.
// ---------------------------------------------------------------------------

// The characters a spreadsheet will act on if they lead a cell.
const DANGEROUS = /^[=+\-@\t\r]/;

function looksNumeric(s) {
  // `Number('')` is 0, which is finite -- so the empty check is not
  // decoration. It cannot be reached from csvCell (an empty string has no
  // leading character to be dangerous) but this function is exported and a
  // caller could ask directly.
  if (s === '') return false;
  return Number.isFinite(Number(s));
}

// ALWAYS QUOTED. The conditional form -- quote only when the value contains a
// comma, quote or newline -- is what `roofing-gl-export.js` used, and it meant
// a cell of `=cmd|'/c calc'!A0` was emitted completely BARE. Always quoting is
// two bytes per cell and removes a whole class of "is this one of the cases
// that needed quoting" reasoning from every caller.
function csvCell(v) {
  let s = v == null ? '' : String(v);
  if (DANGEROUS.test(s) && !looksNumeric(s)) s = "'" + s;
  return '"' + s.replace(/"/g, '""') + '"';
}

function csvRow(values) {
  return (values || []).map(csvCell).join(',');
}

module.exports = { csvCell, csvRow, looksNumeric, DANGEROUS };
