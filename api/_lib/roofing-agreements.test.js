// api/_lib/roofing-agreements.test.js
// Isolation suite for the contingency-agreement engine. Every expected date
// here was worked out by hand from the statute named in the test, not read back
// off the implementation.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const ag = require('./roofing-agreements.js');

// ── The four rules, as they would sit in rf_contingency_rules ──────────────
const OHIO = {
  rule_id: 'RFCON-OH-HSSA', state: 'OH', trigger: 'execution', count: 3,
  unit: 'business_days', business_day_basis: 'oh_hssa',
  notice_required: true, form_required: true,
  indefinite_if_noncompliant: true, applies_only_when_solicited: true,
  authority: 'Ohio Rev. Code 1345.21-.28 (Home Solicitation Sales Act)'
};
const COLORADO = {
  rule_id: 'RFCON-CO-6-22-104', state: 'CO', trigger: 'insurer_denial', count: 72,
  unit: 'hours', notice_required: true, form_required: false,
  indefinite_if_noncompliant: false, applies_only_when_solicited: false,
  authority: 'C.R.S. 6-22-104'
};
const FLORIDA = {
  rule_id: 'RFCON-FL-489-147', state: 'FL', trigger: 'execution', count: 10,
  unit: 'calendar_days', notice_required: true, form_required: false,
  indefinite_if_noncompliant: false, applies_only_when_solicited: false,
  authority: 'Fla. Stat. 489.147(6)'
};

function executed(over) {
  return Object.assign({
    agreement_id: 'RFAGR-1', claim_id: 'C1', event_type: 'executed',
    signer_name: 'A Homeowner', signing_venue: 'buyer_residence',
    executed_at: '2026-08-03T15:00:00.000Z', // a Monday
    state: 'OH', notice_given: true, cancellation_form_given: true
  }, over || {});
}

test('an unsigned claim is unsigned -- not zero, not expired', () => {
  const r = ag.evaluateAgreement({ rule: OHIO, events: [], now: '2026-08-05T00:00:00Z' });
  assert.strictEqual(r.signed, false);
  assert.strictEqual(r.status, 'unsigned');
  assert.strictEqual(r.deadline_at, null);
});

test('Ohio: 3 business days from a Monday execution runs to midnight Thursday', () => {
  // R.C. 1345.22 -- "prior to midnight of the third business day". Mon 3 Aug
  // 2026 + 3 business days = Thu 6 Aug, end of day.
  const r = ag.evaluateAgreement({ rule: OHIO, events: [executed()], now: '2026-08-04T00:00:00Z' });
  assert.strictEqual(r.status, 'open');
  assert.strictEqual(r.deadline_at, '2026-08-06T23:59:59.999Z');
  assert.strictEqual(r.trigger, 'execution');
});

test('Ohio: SATURDAY IS a business day -- a Thursday signing lands on Monday, not Tuesday', () => {
  // THE BUG THIS TEST EXISTS FOR. R.C. 1345.21 defines a business day as "any
  // calendar day except Sunday" plus eleven named holidays. Thu 6 Aug 2026 + 3:
  // Fri 7 (1), SAT 8 (2), Sun 9 skipped, Mon 10 (3). The ordinary Mon-Fri
  // reading gives Tue 11 -- a full day later, and wrong.
  const r = ag.evaluateAgreement({
    rule: OHIO, events: [executed({ executed_at: '2026-08-06T15:00:00.000Z' })],
    now: '2026-08-07T00:00:00Z'
  });
  assert.strictEqual(r.deadline_at, '2026-08-10T23:59:59.999Z');
});

test('Ohio: a named holiday is excluded, and Saturday still counts around it', () => {
  // Wed 25 Nov 2026 + 3: Thu 26 is Thanksgiving (4th Thursday) so it is skipped;
  // Fri 27 (1), SAT 28 (2), Sun 29 skipped, Mon 30 (3).
  const r = ag.evaluateAgreement({
    rule: OHIO, events: [executed({ executed_at: '2026-11-25T15:00:00.000Z' })],
    now: '2026-11-26T00:00:00Z'
  });
  assert.strictEqual(r.deadline_at, '2026-11-30T23:59:59.999Z');
  assert.strictEqual(r.disclosures.holidays_applied, true);
});

test('the mon_fri basis is still available, and still discloses that holidays are NOT applied', () => {
  // For a state whose definitions section has not been read. Thu 6 Aug + 3 on
  // the ordinary meaning = Tue 11 Aug.
  const generic = Object.assign({}, OHIO, { business_day_basis: 'mon_fri', applies_only_when_solicited: false });
  const r = ag.evaluateAgreement({
    rule: generic, events: [executed({ executed_at: '2026-08-06T15:00:00.000Z' })],
    now: '2026-08-07T00:00:00Z'
  });
  assert.strictEqual(r.deadline_at, '2026-08-11T23:59:59.999Z');
  assert.strictEqual(r.disclosures.holidays_applied, false);
  assert.match(r.disclosures.note, /has NOT been read/);
});

test('Ohio: the basis used is named on the result, not left implicit', () => {
  const r = ag.evaluateAgreement({ rule: OHIO, events: [executed()], now: '2026-08-04T00:00:00Z' });
  assert.strictEqual(r.disclosures.business_day_basis, 'oh_hssa');
  assert.strictEqual(r.disclosures.holidays_applied, true);
  assert.match(r.disclosures.note, /Saturday IS a business day/);
});

test('Ohio: NO cancellation form means the right to cancel never expires', () => {
  // R.C. 1345.23 -- the seller must supply both the notice and a separate
  // detachable form; failing that, the buyer may cancel until they do.
  const r = ag.evaluateAgreement({
    rule: OHIO, events: [executed({ cancellation_form_given: false })],
    now: '2027-01-01T00:00:00Z' // long past any 3-day window
  });
  assert.strictEqual(r.status, 'indefinite');
  assert.strictEqual(r.deadline_at, null);
  assert.deepStrictEqual(r.disclosures.missing, ['the separate detachable cancellation form']);
});

test('Ohio: missing BOTH the notice and the form lists both', () => {
  const r = ag.evaluateAgreement({
    rule: OHIO, events: [executed({ notice_given: false, cancellation_form_given: false })],
    now: '2026-08-04T00:00:00Z'
  });
  assert.strictEqual(r.status, 'indefinite');
  assert.strictEqual(r.disclosures.missing.length, 2);
});

test('Ohio: signed at the shop, the Act does not reach the contract at all', () => {
  const r = ag.evaluateAgreement({
    rule: OHIO, events: [executed({ signing_venue: 'seller_place_of_business' })],
    now: '2026-08-04T00:00:00Z'
  });
  assert.strictEqual(r.status, 'rule_not_applicable');
  assert.strictEqual(r.deadline_at, null);
  assert.match(r.disclosures.note, /place of business/);
});

test('an unread state falls back to mon_fri rather than silently borrowing the Ohio basis', () => {
  const noBasis = Object.assign({}, OHIO, { applies_only_when_solicited: false });
  delete noBasis.business_day_basis;
  const r = ag.evaluateAgreement({
    rule: noBasis, events: [executed({ executed_at: '2026-08-06T15:00:00.000Z' })],
    now: '2026-08-07T00:00:00Z'
  });
  assert.strictEqual(r.disclosures.business_day_basis, 'mon_fri');
  assert.strictEqual(r.deadline_at, '2026-08-11T23:59:59.999Z');
});

test('a non-solicitation rule is NOT switched off by the signing venue', () => {
  // Only Ohio's Act turns on venue. Florida's does not, so the same venue that
  // disables Ohio must leave Florida running.
  const r = ag.evaluateAgreement({
    rule: FLORIDA,
    events: [executed({ state: 'FL', signing_venue: 'seller_place_of_business' })],
    now: '2026-08-04T00:00:00Z'
  });
  assert.strictEqual(r.status, 'open');
  assert.strictEqual(r.deadline_at, '2026-08-13T15:00:00.000Z');
});

test('Colorado: the clock starts on the INSURER DENIAL, not on signing', () => {
  // C.R.S. 6-22-104 -- 72 hours after written notice of denial.
  const r = ag.evaluateAgreement({
    rule: COLORADO, events: [executed({ state: 'CO' })],
    denial_at: '2026-09-01T09:00:00.000Z', now: '2026-09-02T00:00:00Z'
  });
  assert.strictEqual(r.trigger, 'insurer_denial');
  assert.strictEqual(r.trigger_at, '2026-09-01T09:00:00.000Z');
  assert.strictEqual(r.deadline_at, '2026-09-04T09:00:00.000Z');
  assert.strictEqual(r.status, 'open');
});

test('Colorado: with no denial recorded the clock has NOT started -- not expired', () => {
  const r = ag.evaluateAgreement({
    rule: COLORADO, events: [executed({ state: 'CO' })], now: '2027-01-01T00:00:00Z'
  });
  assert.strictEqual(r.status, 'not_triggered');
  assert.strictEqual(r.deadline_at, null);
  assert.match(r.disclosures.note, /written denial/);
});

test('Florida: 10 CALENDAR days from execution, weekend included', () => {
  // Fla. Stat. 489.147(6). Mon 3 Aug + 10 calendar days = Thu 13 Aug.
  const r = ag.evaluateAgreement({
    rule: FLORIDA, events: [executed({ state: 'FL' })], now: '2026-08-04T00:00:00Z'
  });
  assert.strictEqual(r.deadline_at, '2026-08-13T15:00:00.000Z');
});

test('an elapsed window reads expired, and hours_remaining goes negative not null', () => {
  const r = ag.evaluateAgreement({ rule: OHIO, events: [executed()], now: '2026-08-20T00:00:00Z' });
  assert.strictEqual(r.status, 'expired');
  assert.ok(r.hours_remaining < 0);
});

test('a rescission row supersedes and wins over any computed window', () => {
  const r = ag.evaluateAgreement({
    rule: OHIO,
    events: [executed(), { agreement_id: 'RFAGR-2', event_type: 'rescinded', supersedes: 'RFAGR-1', rescinded_at: '2026-08-05T10:00:00.000Z' }],
    now: '2026-08-05T12:00:00Z'
  });
  assert.strictEqual(r.status, 'rescinded');
  assert.strictEqual(r.hours_remaining, null);
  assert.ok(r.rescission);
});

test('a rescission naming a DIFFERENT agreement does not silently apply', () => {
  const r = ag.evaluateAgreement({
    rule: OHIO,
    events: [executed(), { agreement_id: 'RFAGR-9', event_type: 'rescinded', supersedes: 'RFAGR-SOMETHING-ELSE', rescinded_at: '2026-08-05T10:00:00.000Z' }],
    now: '2026-08-05T12:00:00Z'
  });
  assert.strictEqual(r.status, 'open');
  assert.strictEqual(r.rescission, null);
});

test('a rescission of a SUPERSEDED agreement does not void the later one', () => {
  // Found by a test fixture accidentally putting two executed rows on one
  // claim. A rescission names one agreement_id; re-signing afterwards produces
  // a NEW agreement, and cancelling the old one must not silently cancel the
  // new one -- that would read as "cancelled" on a contract that is live.
  const r = ag.evaluateAgreement({
    rule: OHIO,
    events: [
      executed({ agreement_id: 'RFAGR-OLD', executed_at: '2026-08-03T15:00:00.000Z' }),
      executed({ agreement_id: 'RFAGR-NEW', executed_at: '2026-08-17T15:00:00.000Z' }),
      { agreement_id: 'RFAGR-R', event_type: 'rescinded', supersedes: 'RFAGR-OLD', rescinded_at: '2026-08-05T10:00:00.000Z' }
    ],
    now: '2026-08-18T00:00:00Z'
  });
  assert.strictEqual(r.executed.agreement_id, 'RFAGR-NEW');
  assert.strictEqual(r.status, 'open');
  assert.strictEqual(r.rescission, null);
});

test('no rule on file is an honest empty state, NOT "no right of rescission"', () => {
  const r = ag.evaluateAgreement({ rule: null, events: [executed({ state: 'WY' })], now: '2026-08-04T00:00:00Z' });
  assert.strictEqual(r.status, 'no_rule');
  assert.strictEqual(r.deadline_at, null);
  assert.match(r.disclosures.note, /no contingency rule is on file/);
});

test('an invalid rule refuses to compute rather than producing a confident date', () => {
  const r = ag.evaluateAgreement({
    rule: { rule_id: 'BAD', trigger: 'vibes', count: -1, unit: 'fortnights' },
    events: [executed()], now: '2026-08-04T00:00:00Z'
  });
  assert.strictEqual(r.status, 'rule_invalid');
  assert.strictEqual(r.deadline_at, null);
  assert.ok(r.problems.length >= 3);
});

test('a rule with no authority citation is refused -- it cannot be relied on', () => {
  const problems = ag.validateRule({ trigger: 'execution', count: 3, unit: 'business_days' });
  assert.ok(problems.some((p) => /authority citation/.test(p)));
});

test('two executed agreements: the latest wins and the ambiguity is flagged', () => {
  const r = ag.evaluateAgreement({
    rule: OHIO,
    events: [executed(), executed({ agreement_id: 'RFAGR-2', executed_at: '2026-08-10T15:00:00.000Z' })],
    now: '2026-08-11T00:00:00Z'
  });
  assert.strictEqual(r.executed.agreement_id, 'RFAGR-2');
  assert.ok(r.problems.some((p) => /2 executed agreements/.test(p)));
});

test('validateAgreement demands a signature and a venue on an executed row', () => {
  const problems = ag.validateAgreement({ id: 'X', claim_id: 'C1', event_type: 'executed' });
  assert.ok(problems.some((p) => /signature_data/.test(p)));
  assert.ok(problems.some((p) => /signing_venue/.test(p)));
  assert.ok(problems.some((p) => /signer_name/.test(p)));
  assert.ok(problems.some((p) => /state is required/.test(p)));
});

test('validateAgreement demands that a rescission name what it supersedes', () => {
  const problems = ag.validateAgreement({ id: 'X', claim_id: 'C1', event_type: 'rescinded' });
  assert.ok(problems.some((p) => /supersedes/.test(p)));
});

test('an executed agreement with everything present validates clean', () => {
  const problems = ag.validateAgreement({
    id: 'RFAGR-1', claim_id: 'C1', event_type: 'executed', signer_name: 'A Homeowner',
    signature_data: 'data:image/png;base64,AAAA', signing_venue: 'buyer_residence',
    executed_at: '2026-08-03T15:00:00.000Z', state: 'OH'
  });
  assert.deepStrictEqual(problems, []);
});

test('event vocabularies are closed and disjoint', () => {
  assert.deepStrictEqual(ag.AGREEMENT_EVENTS, ['executed', 'rescinded']);
  assert.deepStrictEqual(ag.RESCISSION_TRIGGERS, ['execution', 'insurer_denial']);
  assert.ok(ag.SIGNING_VENUES.indexOf('buyer_residence') !== -1);
});
