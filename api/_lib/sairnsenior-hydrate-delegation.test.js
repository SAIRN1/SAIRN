// api/_lib/sairnsenior-hydrate-delegation.test.js
//
// REQUIREMENT: every sairnsenior hydrate goes through the shared
// senServerWinsMerge(), and each one is pinned BY ITS OWN BODY rather than by
// a file-wide match.
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// The server-wins conversion moved the merge out of each hydrate and into a
// shared helper. Three suites were re-aimed at the new shape on 2026-09-21
// (authorizations, pay-rates, payer-contracts). THE OTHER EIGHT CALL SITES
// WERE PINNED BY NOTHING -- rewriting any of them back to additive-only would
// have broken no test anywhere.
//
// MEASURED, TWICE, AND THE SECOND COUNT IS THE ONE THAT MATTERS.
// `senServerWinsMerge(` occurs 13 times in sairnsenior.html: one definition,
// one comment, and ELEVEN call sites. Eight pass a literal resource string.
// THREE PASS A VARIABLE `key` -- senHydrateReferrals, senHydrateOrg and
// senHydrateTraining -- and a resource-name grep cannot see those at all,
// which is exactly why the first survey of this gap reported eight call sites
// instead of eleven and five unpinned instead of eight.
//
// AND THE THREE VARIABLE-KEY HYDRATES CARRY TWO RESOURCES EACH, so the
// resource coverage is FOURTEEN, not eleven: sen_referrals +
// sen_referral_sources, sen_branches + sen_applicants, sen_training_records +
// sen_training_rules. A suite that pinned only the call would leave the second
// resource in each pair unmentioned anywhere.
//
// ── WHAT THIS SUITE DOES NOT DO, STATED SO THE SILENCE IS NOT READ AS COVER ─
// It pins DELEGATION, not the merge's behaviour. tests/server_wins_hydration.js
// owns the rule itself across all seven converted apps, and re-testing it here
// would be a second copy kept in step by nobody. The cost of that division is
// real and is the same one fourth named: these arms stay green if
// senServerWinsMerge itself breaks, and rely on a suite in another directory
// to catch that.
//
// ── THE RULE THE ARMS DESCRIBE HAS THREE CARVE-OUTS, NOT ONE ───────────────
// The guard is `if(!senBootstrappedNow && usable && seeded[id])`. Server wins
// EXCEPT: (a) this id's own first push never landed, so the server's row
// belongs to somebody else; (b) this page load ran the bootstrap; (c) the
// synced-id store is UNREADABLE, in which case no overwrite happens at all.
// The three suites re-aimed on 2026-09-21 describe only (a). Named in full
// here because that sentence is being copied, and an incomplete rule copied
// four times is harder to correct than one written out once.

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
const src = fs.readFileSync(path.join(ROOT, 'sairnsenior.html'), 'utf8');

// Brace-balanced extraction, the same shape the three re-aimed suites use.
// A prefix that happened to contain the call would pass while proving less,
// so the span is balanced rather than a fixed window.
function fn(name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('not found in sairnsenior.html: ' + name);
  let depth = 0;
  for (let i = start; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') {
      depth--;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error('unbalanced: ' + name);
}

// The eight that nothing pinned before this file. The three already covered
// elsewhere are deliberately absent -- duplicating them here would create the
// second copy this suite's own header argues against.
const LITERAL = [
  ['senHydrateClients', 'sen_clients'],
  ['senHydrateCaregivers', 'sen_caregivers'],
  ['senHydrateVisits', 'sen_visits'],
  ['senHydrateClaims', 'sen_claims'],
  ['senHydrateFranchise', 'sen_franchise_agreements']
];

// The three a resource-name grep cannot find. Each loops a pair-list and
// passes the loop variable, so the assertion has two halves: the call is in
// THIS body, and THIS body names both resources it is responsible for.
const VARIABLE = [
  ['senHydrateReferrals', ['sen_referrals', 'sen_referral_sources']],
  ['senHydrateOrg', ['sen_branches', 'sen_applicants']],
  ['senHydrateTraining', ['sen_training_records', 'sen_training_rules']]
];

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { console.log('  ok   ' + name); pass++; }
  else { console.log('  FAIL ' + name + (detail ? '\n       ' + detail : '')); fail++; }
}
function section(t) { console.log('\n' + t); }

section('THE FIVE WITH A LITERAL RESOURCE -- pinned by their own body');

LITERAL.forEach(function (pair) {
  const name = pair[0], res = pair[1];
  const body = fn(name);
  check(name + ' delegates to the shared merge for ' + res
    + ' -- server replaces a local row EXCEPT one this device created and '
    + 'never pushed, one seen during the bootstrap load, or any row when the '
    + 'synced-id store is unreadable',
  new RegExp('senServerWinsMerge\\(\'' + res + '\',\\s*serverRows\\)').test(body),
  'no senServerWinsMerge(\'' + res + '\', serverRows) inside ' + name);
});

section('THE THREE THAT PASS A VARIABLE -- invisible to a resource grep');

VARIABLE.forEach(function (pair) {
  const name = pair[0], resources = pair[1];
  const body = fn(name);
  check(name + ' delegates to the shared merge with a loop variable',
    /senServerWinsMerge\(key,\s*rows\)/.test(body),
    'no senServerWinsMerge(key, rows) inside ' + name);
  // THE SECOND HALF, and it is the half a call-only arm would miss: the PAIR
  // LIST is what decides which resources the loop covers, so a resource
  // dropped from it stops being merged while the call arm above stays green.
  //
  // ── ANCHORED ON THE PAIR LIST, NOT ON THE BODY, AND IT HAD TO LEARN THAT ──
  // The first version asked whether the resource appeared ANYWHERE in the
  // body. Every one of these hydrates names each resource TWICE -- once in
  // its senData('read', ...) fetch and once in the pair list -- so dropping
  // it from the pair list left the fetch behind and the arm passed. All six
  // of the probe's C mutations survived on the first run because of it.
  // `['<res>',` pins the position that actually decides the merge.
  resources.forEach(function (res) {
    check(name + ' still MERGES ' + res + ' -- it is in the pair list, not '
      + 'merely fetched',
    new RegExp('\\[\'' + res + '\'\\s*,').test(body),
    res + ' is no longer a pair-list entry in ' + name + '. It may still be '
    + 'FETCHED, which is exactly what makes this silent: the rows arrive and '
    + 'nothing merges them.');
  });
});

section('COVERAGE -- the census is derived, so a twelfth call site cannot hide');

check('sairnsenior.html still has exactly 11 senServerWinsMerge CALL SITES',
  (function () {
    const all = src.match(/senServerWinsMerge\(/g) || [];
    // 13 occurrences: one definition, one prose mention, eleven calls.
    const def = /function senServerWinsMerge\(/.test(src) ? 1 : 0;
    const prose = (src.match(/senServerWinsMerge\(\) /g) || []).length;
    return all.length - def - prose === 11;
  })(),
  'the call-site count moved. A NEW one needs an arm here; a REMOVED one means '
  + 'a hydrate stopped delegating. Either way this file has to be read, which '
  + 'is the point of counting rather than listing.');

check('every hydrate named here is pinned, and the three covered elsewhere '
  + 'are not duplicated', (function () {
    const here = LITERAL.map(function (p) { return p[0]; })
      .concat(VARIABLE.map(function (p) { return p[0]; }));
    const elsewhere = ['senHydrateAuthorizations', 'senHydratePayRates',
                       'senHydratePayerContracts'];
    const overlap = here.filter(function (h) { return elsewhere.indexOf(h) !== -1; });
    return here.length === 8 && overlap.length === 0;
  })(),
  'this suite either lost a hydrate or started duplicating one already pinned '
  + 'by api/_lib/sairnsenior-{authorizations,pay-rates,payer-contracts}.test.js');

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) { console.log('FAILURES ABOVE'); process.exit(1); }
