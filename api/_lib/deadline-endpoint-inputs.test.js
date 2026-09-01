// The endpoint must forward every input the engine reads.
//
// WHY THIS FILE EXISTS. On 2026-08-27 the engine grew a `service_methods`
// input -- the full set of methods actually used, for rules whose extension
// requires service by one method AND BY NOTHING ELSE (Utah URCP 6(c)
// "exclusively by mail", Fla. R. Gen. Prac. & Jud. Admin. 2.514(b) "by only
// mail"). `api/legal-deadlines.js` was never updated, so the field was
// silently dropped on every live request for five days.
//
// BOTH DIRECTIONS WERE WRONG AND NEITHER WAS VISIBLE FROM THE RESPONSE:
//   - Florida returned `applied_exclusivity_assumed` and +5 days even when
//     the caller sent ["mail","email"] -- the FIVE-DAY-LATE case the change
//     was built to close, on the shortest answer period in the engine.
//   - Utah's +7 was unreachable at all: `on_unknown_exclusivity: 'refuse'`
//     fired on every call, because the set could never arrive.
//
// AND THE SUITES WERE GREEN THROUGHOUT -- 14/14 on Florida, 59/59 on Utah --
// because they call computeDeadline() directly and never traverse the
// endpoint. That is Guardian Check 29's shape exactly: two files, one change,
// one updated, with high coverage on the wrong side of the seam.
//
// So this file does not test a date. It tests the SEAM: every `input.X` the
// engine reads must appear as a key in the endpoint's computeDeadline
// payload. A future engine input that nobody wires up fails here on the day
// it is added, rather than five days later against a live licence.

const fs = require('fs');
const path = require('path');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

const stripComments = s => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const engineSrc = stripComments(
  fs.readFileSync(path.join(__dirname, 'deadline-engine.js'), 'utf8'));
const endpointSrc = fs.readFileSync(path.join(__dirname, '..', 'legal-deadlines.js'), 'utf8');

// Everything the engine reads off its input object.
const engineReads = [...new Set(
  [...engineSrc.matchAll(/\binput\.([a-z_]+)/g)].map(m => m[1])
)].sort();

// Supplied by the endpoint from the DATABASE, not from the request body, so
// they are not part of the body-forwarding contract this file guards.
const SERVER_SUPPLIED = ['calendars', 'rules'];

// The literal object passed to computeDeadline in the endpoint.
const start = endpointSrc.indexOf('computeDeadline({');
check('the endpoint calls computeDeadline with an object literal', start !== -1, true);
let i = start + 'computeDeadline({'.length, depth = 1, payload = '';
while (i < endpointSrc.length && depth > 0) {
  const ch = endpointSrc[i];
  if (ch === '{') depth++;
  else if (ch === '}') depth--;
  if (depth > 0) payload += ch;
  i++;
}
const endpointSends = [...new Set(
  [...stripComments(payload).matchAll(/^\s*([a-z_]+)\s*:/gm)].map(m => m[1])
)].sort();

check('the engine reads a plausible number of inputs -- the scan is not empty',
  engineReads.length >= 10, true);
check('the payload was parsed and is not empty', endpointSends.length >= 10, true);

const missing = engineReads.filter(f => !endpointSends.includes(f) && !SERVER_SUPPLIED.includes(f));
check('EVERY engine input is forwarded by the endpoint', missing, []);

// The specific field the incident was about, named so a regression cannot
// hide behind a passing generic assertion.
check('service_methods specifically is forwarded', endpointSends.includes('service_methods'), true);
check('service_method is still forwarded too -- they are different fields',
  endpointSends.includes('service_method'), true);

// The reverse direction is informational, not a failure: the endpoint may
// legitimately pass something the engine has stopped reading, and that is a
// tidy-up rather than a live defect. Reported so it is visible.
const unread = endpointSends.filter(f => !engineReads.includes(f));
if (unread.length) console.log('NOTE  endpoint sends fields the engine does not read: ' + unread.join(', '));

// A guard on the guard: if the engine's input-reading style ever changes so
// this regex finds nothing, the assertions above would pass vacuously.
check('the scan found service_methods in the ENGINE, so the two lists are comparable',
  engineReads.includes('service_methods'), true);

console.log('\ndeadline-endpoint-inputs: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
