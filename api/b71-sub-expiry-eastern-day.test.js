// hank b71 (H1 #1817): api/sd-sub-data.js takes "today" as the America/New_York
// calendar day. Its comment used to claim that zone "can never call a
// still-valid document expired anywhere" in the fifty states. That is
// backwards -- Eastern rolls over FIRST -- and the comment now says so. This
// suite pins the behaviour the corrected comment describes, so the comment and
// the code cannot drift apart again:
//
//   W. a document whose last valid day is 2026-10-29 reads EXPIRED at
//      2026-10-30T04:30Z -- 00:30 in New York, but still 21:30 on 2026-10-29 in
//      Los Angeles. That is the disclosed early window for the West (safe
//      direction for a compliance gate).
//   E. at 2026-10-30T03:30Z (23:30 in New York, still the 29th) it reads VALID.
//   X. CONTROL: a UTC-day reading would already say expired at 03:30Z, so W/E
//      are measuring the zone, not the date string.
//
// The two functions are lifted from the file as TEXT (they are not exported).
'use strict';
const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(path.join(__dirname, 'sd-sub-data.js'), 'utf8');
let passed = 0, failed = 0;
function arm(name, ok, detail) {
  if (ok) { passed++; console.log('  ok   ' + name); }
  else { failed++; console.log('  FAIL ' + name + (detail ? '  -- ' + detail : '')); }
}
function lift(sig) {
  const i = SRC.indexOf(sig);
  if (i < 0) return null;
  let depth = 0, j = SRC.indexOf('{', i);
  for (let k = j; k < SRC.length; k++) {
    if (SRC[k] === '{') depth++;
    else if (SRC[k] === '}') { depth--; if (depth === 0) return SRC.slice(i, k + 1); }
  }
  return null;
}
const a = lift('function localTodayISO(now)');
const b = lift('function complianceStatus(row, todayISO)');
const soonDecl = (SRC.match(/const EXPIRING_SOON_DAYS = \d+;/) || [])[0];
if (!a || !b || !soonDecl) { console.log('COULD NOT RUN: functions not found in api/sd-sub-data.js'); process.exit(2); }
const { localTodayISO, complianceStatus } = new Function(soonDecl + '\n' + a + '\n' + b + '\nreturn { localTodayISO, complianceStatus };')();

const row = { coi_expiry: '2026-10-29', licence_expiry: '2026-10-29', w9_on_file: true };
const at = (iso) => complianceStatus(row, localTodayISO(new Date(iso)));

const w = at('2026-10-30T04:30:00Z');
arm('W. 00:30 New York / 21:30 Los Angeles on the last valid day: EXPIRED, blocking (the disclosed early window)',
  w.coi === 'expired' && w.licence === 'expired' && w.blocking.length === 2, JSON.stringify(w));
const e = at('2026-10-30T03:30:00Z');
arm('E. 23:30 New York on the last valid day: VALID or expiring, never expired',
  e.coi !== 'expired' && e.licence !== 'expired' && e.blocking.length === 0, JSON.stringify(e));
const utcToday = new Date('2026-10-30T03:30:00Z').toISOString().slice(0, 10);
arm('X. CONTROL: the UTC day at 03:30Z is already 2026-10-30, so a UTC reading would say expired here',
  complianceStatus(row, utcToday).coi === 'expired', utcToday);
arm('the comment no longer claims Eastern can never be early',
  !/can never call a still-valid\s*\n?\/\/\s*document expired anywhere/.test(SRC) && /backwards/.test(SRC));

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
