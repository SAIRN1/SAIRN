// Fixture SUITE for tests/run_sabotage_harness_multiedit_probe.py.
//
// It asserts exactly one property of the fixture source: an unreadable body is
// REFUSED. That property is held by two mutually redundant guards, so this
// suite goes red only when BOTH are removed -- which is the thing the harness's
// multi-edit mutation has to be able to plant.
'use strict';
const assert = require('assert');
const { handle } = require('./harness_multiedit_src.js');

assert.strictEqual(handle(null), 'REFUSED', 'an unreadable body is not refused');
assert.strictEqual(handle('not an array'), 'REFUSED', 'a wrong-shaped body is not refused');
assert.strictEqual(handle([]), 'CONFLICT', 'a zero-row body is not a conflict');
assert.strictEqual(handle([{ id: 1 }]), 'SAVED', 'a one-row body is not saved');
console.log('fixture suite: 4 assertions pass');
