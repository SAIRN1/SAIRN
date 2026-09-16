// api/_lib/record-parity.test.js
// REQUIREMENT: two records that should agree are compared on their CONTENT rather than
//   their representation, so a formatting difference is never reported as a
//   data difference
//
//
// Run:  node api/_lib/record-parity.test.js
//
// Control for api/_lib/record-parity.js -- item 46.
//
// THE ARMS THAT MATTER, and none of them is "does XOR work":
//
//   § 2  IT ACTUALLY RECONSTRUCTS. The whole claim over item 35's hash chain is
//        correction rather than detection, so a recovered record must come back
//        BYTE-IDENTICAL, and the arm proves it against the original bytes rather
//        than against a re-serialisation.
//   § 3  IT REFUSES THE CASES IT CANNOT DO. Two erasures, a changed survivor, a
//        digest mismatch. A parity implementation that returns plausible bytes on
//        an underdetermined group is worse than none on an append-only DEA
//        register, where a correction is a SECOND row and the wrong one stands.
//   § 4  A GROUP OF ONE IS REFUSED, because with one member the parity block IS
//        the record -- a second plaintext copy of a controlled-substance entry,
//        stored as redundancy.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const P = require('./record-parity.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

// Shaped like a real sv_controlled row rather than {a:1}: variable-length
// strings, a nested object, a null, and records of DIFFERENT lengths, which is
// the case fixed-width XOR gets wrong.
const R1 = { id: 'C-1', drug: 'ketamine', qty: 2, unit: 'mL',
             vet: 'dr-a', witness: 'dr-b', notes: null,
             patient: { id: 'P-1', species: 'canine' } };
const R2 = { id: 'C-2', drug: 'buprenorphine hydrochloride', qty: 0.3,
             unit: 'mL', vet: 'dr-c', witness: 'dr-a',
             notes: 'split dose, second half discarded and witnessed',
             patient: { id: 'P-2', species: 'feline' } };
const R3 = { id: 'C-3', drug: 'diazepam', qty: 5, unit: 'mg', vet: 'dr-a',
             witness: 'dr-c', notes: '', patient: { id: 'P-3', species: 'equine' } };

const G = () => P.buildGroup('g-1', [
  { id: 'C-1', record: R1 }, { id: 'C-2', record: R2 }, { id: 'C-3', record: R3 }]);

// ════════════════════════════════════════════════════════════════════════════
section('1. the group block');
t('it carries a digest AND a length per member', () => {
  const g = G();
  assert.strictEqual(g.members.length, 3);
  g.members.forEach((m) => {
    assert.strictEqual(typeof m.digest, 'string');
    assert.strictEqual(m.digest.length, 64);
    assert.ok(m.length > 0);
  });
});
t('the width is the LONGEST member, so a short record does not corrupt the tail', () => {
  const g = G();
  assert.strictEqual(g.width, Math.max.apply(null, g.members.map((m) => m.length)));
});
t('the parity block is exactly the group width', () => {
  const g = G();
  assert.strictEqual(Buffer.from(g.parity_b64, 'base64').length, g.width);
});
t('canonical form is key-order independent -- the sv-witness lesson', () => {
  // Two encodings of one record must give the same bytes, or a reconstruction is
  // byte-different from an identical record and fails its own digest.
  assert.strictEqual(P.canonical({ a: 1, b: 2 }), P.canonical({ b: 2, a: 1 }));
  assert.notStrictEqual(P.canonical({ n: 'a b' }), P.canonical({ n: 'a  b' }),
    'whitespace inside a string is a different record');
  assert.notStrictEqual(P.canonical({ a: null }), P.canonical({}),
    'null is not the same as absent');
});

// ════════════════════════════════════════════════════════════════════════════
section('2. IT RECONSTRUCTS -- the claim over a hash chain');
t('the LONGEST member comes back byte-identical', () => {
  const g = G();
  const r = P.recover(g, 'C-2', [{ id: 'C-1', record: R1 }, { id: 'C-3', record: R3 }]);
  assert.ok(r.ok, r.reason);
  assert.deepStrictEqual(r.record, R2);
  assert.strictEqual(r.bytes.toString('utf8'), P.canonical(R2),
    'byte-identical, not merely deep-equal after a round trip');
});
t('a SHORT member comes back with no padding left on it', () => {
  const g = G();
  const r = P.recover(g, 'C-3', [{ id: 'C-1', record: R1 }, { id: 'C-2', record: R2 }]);
  assert.ok(r.ok, r.reason);
  assert.deepStrictEqual(r.record, R3);
  assert.strictEqual(r.bytes.length, P.canonical(R3).length,
    'the recorded length is what trims the XOR back');
});
t('every member of the group is independently recoverable', () => {
  const g = G();
  const all = { 'C-1': R1, 'C-2': R2, 'C-3': R3 };
  Object.keys(all).forEach((id) => {
    const survivors = Object.keys(all).filter((k) => k !== id)
      .map((k) => ({ id: k, record: all[k] }));
    const r = P.recover(g, id, survivors);
    assert.ok(r.ok, id + ': ' + r.reason);
    assert.deepStrictEqual(r.record, all[id]);
  });
});
t('recovery needs NO access to the original -- only parity and the others', () => {
  // The point of the exposure-window claim: a restore does not re-read the
  // sensitive record. Proven by the call signature having nowhere to pass it.
  const g = G();
  const r = P.recover(g, 'C-1', [{ id: 'C-2', record: R2 }, { id: 'C-3', record: R3 }]);
  assert.ok(r.ok);
  assert.deepStrictEqual(r.record, R1);
});
t('an EXTRA survivor that is not a member is ignored, not XORed in', () => {
  const g = G();
  const r = P.recover(g, 'C-1', [{ id: 'C-2', record: R2 }, { id: 'C-3', record: R3 },
                                 { id: 'C-9', record: { id: 'C-9' } }]);
  assert.ok(r.ok, r.reason);
  assert.deepStrictEqual(r.record, R1);
});

// ════════════════════════════════════════════════════════════════════════════
section('3. IT REFUSES what single parity cannot do');
t('TWO missing records is unrecoverable and SAYS so', () => {
  const g = G();
  const r = P.recover(g, 'C-1', [{ id: 'C-2', record: R2 }]);
  assert.ok(!r.ok);
  assert.strictEqual(r.code, 'PARITY_TOO_MANY_MISSING');
  assert.ok(/ONE record per group/.test(r.reason), r.reason);
  assert.ok(/Reed-Solomon/.test(r.reason),
    'the real remedy is named rather than implied to exist here');
});
t('a CHANGED survivor is caught before it poisons the recovery', () => {
  // This is the sharpest refusal. A survivor that has itself drifted XORs in
  // wrongly and the result would pass no check -- but only because the digest is
  // verified. Without this arm the failure is silent nonsense.
  const g = G();
  const tampered = Object.assign({}, R3, { qty: 500 });
  const r = P.recover(g, 'C-1', [{ id: 'C-2', record: R2 },
                                 { id: 'C-3', record: tampered }]);
  assert.ok(!r.ok);
  assert.strictEqual(r.code, 'PARITY_SURVIVOR_CHANGED');
  assert.ok(/C-3/.test(r.reason));
});
t('a corrupted PARITY BLOCK fails the digest check rather than returning bytes', () => {
  const g = G();
  const buf = Buffer.from(g.parity_b64, 'base64');
  buf[0] = buf[0] ^ 0xff;
  const bad = Object.assign({}, g, { parity_b64: buf.toString('base64') });
  const r = P.recover(bad, 'C-1', [{ id: 'C-2', record: R2 }, { id: 'C-3', record: R3 }]);
  assert.ok(!r.ok);
  assert.strictEqual(r.code, 'PARITY_DIGEST_MISMATCH');
});
t('a member that was never in the group is refused by name', () => {
  const g = G();
  const r = P.recover(g, 'C-99', [{ id: 'C-2', record: R2 }]);
  assert.ok(!r.ok);
  assert.strictEqual(r.code, 'PARITY_NOT_IN_GROUP');
});
t('an unknown block version THROWS -- never silently best-effort', () => {
  const g = Object.assign({}, G(), { version: 99 });
  assert.throws(() => P.recover(g, 'C-1', []), (e) => e.code === 'PARITY_BAD_VERSION');
});

// ════════════════════════════════════════════════════════════════════════════
section('4. a group of ONE is refused, and the reason is confidentiality');
t('groupSize 1 throws, naming what the parity block would be', () => {
  assert.throws(() => P.buildGroup('g', [{ id: 'C-1', record: R1 }]),
    (e) => e.code === 'PARITY_GROUP_TOO_SMALL'
           && /PARITY BLOCK \*IS\* THE RECORD/.test(e.message));
});
t('an empty group throws too', () => {
  assert.throws(() => P.buildGroup('g', []), (e) => e.code === 'PARITY_GROUP_TOO_SMALL');
});
t('a duplicate member id throws -- recovery would be ambiguous', () => {
  assert.throws(() => P.buildGroup('g', [{ id: 'C-1', record: R1 },
                                         { id: 'C-1', record: R2 }]),
    (e) => e.code === 'PARITY_DUPLICATE_ID');
});
t('a group id is required', () => {
  assert.throws(() => P.buildGroup('', [{ id: 'a', record: R1 }, { id: 'b', record: R2 }]),
    (e) => e.code === 'PARITY_NO_GROUP_ID');
});

// ════════════════════════════════════════════════════════════════════════════
section('5. verifyGroup -- the DETECT half, so a caller knows what to recover');
t('an intact group reports all intact and nothing recoverable-because-nothing-broke', () => {
  const g = G();
  const v = P.verifyGroup(g, [{ id: 'C-1', record: R1 }, { id: 'C-2', record: R2 },
                              { id: 'C-3', record: R3 }]);
  assert.deepStrictEqual(v.intact.sort(), ['C-1', 'C-2', 'C-3']);
  assert.deepStrictEqual(v.changed, []);
  assert.deepStrictEqual(v.missing, []);
  assert.strictEqual(v.recoverable, false, 'nothing to recover is not recoverable');
});
t('one changed row is named and reported recoverable', () => {
  const g = G();
  const v = P.verifyGroup(g, [{ id: 'C-1', record: R1 },
                              { id: 'C-2', record: Object.assign({}, R2, { qty: 9 }) },
                              { id: 'C-3', record: R3 }]);
  assert.deepStrictEqual(v.changed, ['C-2']);
  assert.strictEqual(v.recoverable, true);
});
t('one absent row is MISSING, not changed -- different facts', () => {
  const g = G();
  const v = P.verifyGroup(g, [{ id: 'C-1', record: R1 }, { id: 'C-3', record: R3 }]);
  assert.deepStrictEqual(v.missing, ['C-2']);
  assert.deepStrictEqual(v.changed, []);
  assert.strictEqual(v.recoverable, true);
});
t('TWO broken rows reports recoverable FALSE', () => {
  const g = G();
  const v = P.verifyGroup(g, [{ id: 'C-1', record: R1 }]);
  assert.strictEqual(v.missing.length, 2);
  assert.strictEqual(v.recoverable, false);
});

// ════════════════════════════════════════════════════════════════════════════
section('6. the header claims only what the code does');
t('it does NOT claim to be a backup, and says why', () => {
  const src = fs.readFileSync(path.join(__dirname, 'record-parity.js'), 'utf8');
  assert.ok(/DOES NOT PROTECT AGAINST LOSING THE TABLE/.test(src),
    'parity stored beside the rows dies with them, and this platform takes no '
    + 'automated backups');
});
t('it does NOT claim to close the creation-time exposure window', () => {
  const src = fs.readFileSync(path.join(__dirname, 'record-parity.js'), 'utf8');
  assert.ok(/NARROWS IT/.test(src) && /no way around that/.test(src),
    'computing parity needs the plaintext at write time; the honest claim is '
    + 'that recovery does not need it again');
});
t('no Reed-Solomon is implemented, and the single-erasure limit is stated', () => {
  const src = fs.readFileSync(path.join(__dirname, 'record-parity.js'), 'utf8');
  const code = src.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  assert.ok(!/GF\(256\)|galois|reedSolomon/i.test(code),
    'checked on CODE with comments stripped -- the header mentions Reed-Solomon '
    + 'precisely to say it is NOT here, and a text match over prose would read '
    + 'that explanation as an implementation');
  assert.ok(/Reed-Solomon/.test(src), 'the comment should still name the real remedy');
});

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\nrecord-parity: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
