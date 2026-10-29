// hank b64: api/sd-sub-data.js computes the COI / licence "today" as a LOCAL
// calendar day (America/New_York), not the UTC day. The functions are taken
// from the SHIPPED source file, not re-typed here, so the test cannot drift
// from the code it claims to cover.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, 'sd-sub-data.js'), 'utf8');
function grab(name) {
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('not found in shipped source: ' + name);
  let depth = 0, j = src.indexOf('{', i);
  for (; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}' && --depth === 0) break;
  }
  return src.slice(i, j + 1);
}
const ctx = { EXPIRING_SOON_DAYS: 30, Intl, Date, String };
vm.createContext(ctx);
vm.runInContext(grab('localTodayISO') + '\n' + grab('complianceStatus'), ctx);

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

// 9:30 p.m. EDT on 28 Oct 2026 is already 29 Oct in UTC.
const evening = new Date('2026-10-29T01:30:00Z');
check('the evening of 28 Oct EDT is 28 Oct locally', ctx.localTodayISO(evening), '2026-10-28');
check('...while the UTC day has already turned', evening.toISOString().slice(0, 10), '2026-10-29');
check('EST in January: 23:59 local is still the same day', ctx.localTodayISO(new Date('2026-01-15T04:59:00Z')), '2026-01-14');
check('...and 00:01 local is the next', ctx.localTodayISO(new Date('2026-01-15T05:01:00Z')), '2026-01-15');

// A COI expiring 28 Oct is VALID on the evening of 28 Oct (it was 'expired' under the UTC day).
const row = { coi_expiry: '2026-10-28', licence_expiry: '2027-06-01', w9_on_file: true };
const st = ctx.complianceStatus(row, ctx.localTodayISO(evening));
check('a COI on its last valid evening is NOT blocking', st.blocking, []);
check('...and reads as expiring, not expired', st.coi, 'expiring');
check('CONTROL: under the UTC day it WAS blocked -- the defect this fixes',
  ctx.complianceStatus(row, evening.toISOString().slice(0, 10)).blocking, ['coi']);
check('the next local day it IS expired', ctx.complianceStatus(row, '2026-10-29').blocking, ['coi']);
check('the default (no date passed) uses the local helper, not the UTC day',
  /const today = todayISO \|\| localTodayISO\(\);/.test(src) &&
  !/new Date\(\)\.toISOString\(\)\.slice\(0, 10\)/.test(src) && !/nowISO\(\)\.slice\(0, 10\)/.test(src), true);

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
