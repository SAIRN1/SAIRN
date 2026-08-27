// FLORIDA EXCLUSIVITY REGRESSION TEST -- "by only mail".
//
// DELIBERATELY NARROW, like the federal one. Florida has no full suite, and
// that is part of why this went unnoticed: Fla. R. Gen. Prac. & Jud. Admin.
// 2.514(b) adds five days only "when ... service is made BY ONLY MAIL", and
// every Florida row was seeded with that condition unexpressed. It covers the
// one question that was got wrong.
//
// WHY IT WAS MISSED IS WORTH KEEPING. Every Florida row's authority.quote came
// from the CIVIL PROCEDURE PDF, which CITES 2.514(b) but does not CONTAIN it --
// 2.514 lives in the General Practice and Judicial Administration rules, a
// separate document that 403s to a bare curl and needs a browser user-agent.
// A seed can be fully quote-verified against the wrong document.
//
// THE ARITHMETIC IS UNCHANGED ON PURPOSE, on Michael's direction 2026-08-27.
// Dropping the five days would make the COMMON case wrong: a Florida party
// served by mail is typically one for whom portal e-service is unavailable, so
// "only mail" is usually literally true, and refusing would report EARLY on
// most mailed Florida answers -- a frequent early error traded for a rare late
// one. What changed is that the assumption is now VISIBLE instead of silent.
//
// Contrast Utah, whose ut_urcp_6_c sets on_unknown_exclusivity: 'refuse'. Seven
// days is too large an overshoot to assume and Utah had no live arithmetic to
// preserve. The two jurisdictions differ deliberately; if that ever looks like
// an inconsistency, read both notes before "fixing" either.
//
// Run: node api/_lib/deadline-florida-exclusivity.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_florida.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_florida.json'), 'utf8'));

const calendars = {};
for (const row of cal.holiday_calendars) {
  calendars[row.jurisdiction] = calendars[row.jurisdiction] || {};
  calendars[row.jurisdiction][String(row.year)] = row.dates;
}

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

const ANSWER = 'fl-rcp-1140a1-answer-to-complaint';
function res(extra) {
  const r = seed.rules.find(x => x.rule_id === ANSWER);
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'fl', domain: r.domain, trigger_event: r.trigger_event,
    trigger_date: '2026-06-01', rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  }, extra));
}
const shape = r => [r.due_date, r.service_extension.days_added, r.service_extension.state];

// ── The rows declare the condition ────────────────────────────────────────
const withExt = seed.rules.filter(r => r.service_extension);
check('four rows carry fl_rgpja_2514b', withExt.length, 4);
check('every one declares requires_exclusive',
  withExt.every(r => r.service_extension.requires_exclusive === true), true);
check('and every one ASSUMES rather than refuses -- the deliberate difference from Utah',
  [...new Set(withExt.map(r => r.service_extension.on_unknown_exclusivity))], ['assume_exclusive']);
check('five days, not the federal three', [...new Set(withExt.map(r => r.service_extension.add))], [5]);
// The method half was already right; this guards against someone "fixing" it.
const std = engine.SERVICE_EXTENSION_STANDARDS.fl_rgpja_2514b;
check('the standard is mail-only, so e-service already added nothing',
  ['mail', 'email', 'electronic', 'fax', 'hand_delivery'].map(m => std.qualifies(m)),
  [true, false, false, false, false]);

// ── THE ARITHMETIC MUST NOT MOVE FOR TODAY'S CALLERS ──────────────────────
// 2026-06-01 + 20 days = 2026-06-22 (Fla. R. Civ. P. 1.140(a)(1), the shortest
// answer period in the engine); + 5 = 2026-06-27, a Saturday, rolls to Monday
// 2026-06-29. If this line ever changes, the trade-off was re-decided --
// go and read why before accepting it.
check('bare service_method: mail still returns 2026-06-29 with five days',
  shape(res({ service_method: 'mail' })), ['2026-06-29', 5, 'applied_exclusivity_assumed']);
// The state is the whole point: same date, no longer silent.
check('but the state now SAYS the assumption was made',
  res({ service_method: 'mail' }).service_extension.state, 'applied_exclusivity_assumed');
check('and the detail says which direction it can fail and how to resolve it',
  [/EARLIER/.test(res({ service_method: 'mail' }).service_extension.detail),
   /service_methods/.test(res({ service_method: 'mail' }).service_extension.detail)],
  [true, true]);

// ── WITH THE FULL SET, THE CONDITION IS ACTUALLY CHECKED ──────────────────
check('an EXCLUSIVE set gives the same date, now verified rather than assumed',
  shape(res({ service_method: 'mail', service_methods: ['mail'] })), ['2026-06-29', 5, 'applied']);
check('a COMBINED set adds NOTHING -- this is the five-day-late case, now correct',
  shape(res({ service_method: 'mail', service_methods: ['mail', 'email'] })), ['2026-06-22', 0, 'not_exclusive']);
check('not_exclusive is distinct from not_qualifying -- they mean different things',
  res({ service_method: 'email' }).service_extension.state, 'not_qualifying');
check('a set that contradicts service_method is treated as combined, never as exclusive',
  res({ service_method: 'mail', service_methods: ['email'] }).service_extension.state, 'not_exclusive');
check('no method supplied is still not_requested',
  res({}).service_extension.state, 'not_requested');

// ── The mechanism must stay inert for jurisdictions that never asked ───────
{
  const others = [];
  for (const f of fs.readdirSync(SQL)) {
    if (!/^sairnlaw_deadline_seed_.*\.json$/.test(f)) continue;
    for (const r of JSON.parse(fs.readFileSync(path.join(SQL, f), 'utf8')).rules) {
      const se = r.service_extension;
      if (se && se.requires_exclusive && r.jurisdiction !== 'fl' && r.jurisdiction !== 'ut') {
        others.push(r.jurisdiction + ':' + r.rule_id);
      }
    }
  }
  check('ONLY Florida and Utah declare exclusivity -- the two rules that say so', others, []);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
