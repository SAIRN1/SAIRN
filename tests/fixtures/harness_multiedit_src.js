// Fixture SOURCE for tests/run_sabotage_harness_multiedit_probe.py. Not product
// code and not reachable from anything; it exists so the shared sabotage
// harness can be driven against a subject whose failure modes are known by
// construction rather than inferred from a real one.
//
// TWO MUTUALLY REDUNDANT GUARDS, deliberately. That is the shape the multi-edit
// mutation was added for: removing either ALONE leaves the survivor returning
// the identical answer, so only the conjunction is observable.
'use strict';

function classify(body) {
  if (body === null || body === undefined) return 'UNKNOWN';
  if (!Array.isArray(body)) return 'UNKNOWN';
  if (body.length === 0) return 'MISSED';
  return 'WROTE';
}

function handle(body) {
  const first = classify(body);
  if (first === 'UNKNOWN') { return 'REFUSED'; }   // GUARD A
  if (first === 'MISSED') { return 'CONFLICT'; }
  if (classify(body) !== 'WROTE') { return 'REFUSED'; }   // GUARD C
  return 'SAVED';
}

module.exports = { classify, handle };
