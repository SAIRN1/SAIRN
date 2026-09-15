// api/_lib/stripe-api-version.test.js
//
// Run:  node api/_lib/stripe-api-version.test.js
//
// EVERY PRODUCTION `new Stripe(...)` IN api/ MUST PIN AN apiVersion.
//
// ── WHY THE CONSTANT IS NOT THE GUARD ─────────────────────────────────────
// api/_lib/stripe-api-version.js pins the version and explains why. It cannot
// make a SIXTH call site use it. Somebody adding a new SAIRNcash endpoint will
// copy `new Stripe(stripeKey)` from muscle memory -- it is what these files
// looked like for their whole life until 2026-09-15 -- and the constant will
// sit there looking like it is doing something while the new endpoint quietly
// inherits whatever the SDK defaults to.
//
// That is the shape this repo keeps recording: a fix applied to the five sites
// that existed and invisible at the sixth. The count is what scales, so the
// count is what is asserted.
//
// ── WHY IT SCANS SOURCE RATHER THAN CALLING STRIPE ────────────────────────
// There is no node_modules in this clone -- Vercel installs at build time --
// so `require('stripe')` is unavailable here and a runtime assertion would
// SKIP rather than fail. A skip that reads as a pass on a payments path is
// worse than no test. The source scan works with nothing installed.
//
// ── THIS FILE FAILED ON ITSELF FIRST, AND THAT IS RECORDED ON PURPOSE ─────
// The first version kept one list of call sites and an EXEMPT set of
// filenames. It reported THREE unpinned constructions, all of them in this
// file: the assertion messages below quote the unpinned form, so the scanner
// matched its own PROSE. Stripping comments does not help -- these are string
// literals. That is the grep-matched-prose class already on record four times
// here, arriving inside the tool written to avoid assuming things.
//
// Splitting production from test by PATH is the honest fix, and it retires the
// exemption list, which was a stale-entry hazard of its own.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const API = path.join(__dirname, '..');
let pass = 0, fail = 0;

function test(name, fn) {
  try { fn(); pass++; console.log('  ok   - ' + name); }
  catch (e) { fail++; console.log('  FAIL - ' + name + '\n         ' + e.message); }
}

// Comments are stripped before matching. Without this the explanatory comment
// beside each call site -- which quotes the pinned form -- would satisfy the
// scan, and it would keep passing after somebody deleted the code under it.
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^[ \t]*\/\/.*$/gm, '');
}

function walk(dir, out) {
  out = out || [];
  for (const name of fs.readdirSync(dir)) {
    if (name === 'node_modules' || name === '.git') continue;
    const p = path.join(dir, name);
    if (fs.statSync(p).isDirectory()) walk(p, out);
    else if (name.endsWith('.js')) out.push(p);
  }
  return out;
}

const sites = [];
for (const f of walk(API)) {
  const src = stripComments(fs.readFileSync(f, 'utf8'));
  const re = /new Stripe\(([^)]*)\)/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    sites.push({ file: path.relative(API, f).replace(/\\/g, '/'), args: m[1] });
  }
}

// A test file is not a payments path. The count is REPORTED rather than
// dropped silently, so a constructor appearing in a new test is visible.
const PROD = sites.filter((s) => !s.file.endsWith('.test.js'));
const INTESTS = sites.filter((s) => s.file.endsWith('.test.js'));

console.log('every production new Stripe() in api/ pins an apiVersion');
console.log('  (' + PROD.length + ' production site(s), ' + INTESTS.length
  + ' in test files -- test files are out of scope)\n');

// ── ARM 0: THE SCAN FOUND SOMETHING ───────────────────────────────────────
// Without this, a regex that stopped matching -- a reformat putting the
// constructor on two lines, say -- would report ZERO sites and every
// assertion below would pass vacuously: a green test over files it never
// read. This is the arm that makes the rest mean anything.
test('the scan actually finds production Stripe constructions', () => {
  assert.ok(PROD.length >= 5,
    'found ' + PROD.length + ' production site(s) -- expected at least the '
    + 'five SAIRNcash endpoints. If the count DROPPED the regex stopped '
    + 'matching; do not lower this number to make it green.');
});

test('the pinned version is a real Stripe date-version string', () => {
  const { STRIPE_API_VERSION } = require('./stripe-api-version');
  assert.match(STRIPE_API_VERSION, /^\d{4}-\d{2}-\d{2}(\.[a-z]+)?$/,
    'got ' + JSON.stringify(STRIPE_API_VERSION));
});

test('no production call site constructs Stripe without an apiVersion', () => {
  const bare = PROD.filter((s) => !/apiVersion/.test(s.args));
  assert.deepStrictEqual(bare.map((b) => b.file), [],
    'these inherit whatever the installed SDK defaults to:\n           '
    + bare.map((b) => b.file + '  ->  ' + b.args).join('\n           '));
});

test('every production call site uses the SHARED constant, not its own literal', () => {
  const literal = PROD.filter((s) => /apiVersion\s*:\s*['"]/.test(s.args));
  assert.deepStrictEqual(literal.map((l) => l.file), [],
    'these hardcode a version string instead of importing STRIPE_API_VERSION, '
    + 'so the five can drift apart:\n           '
    + literal.map((l) => l.file).join('\n           '));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
