#!/usr/bin/env node
/* tests/sairnfreedom_tax_entity_facts.js
 * ---------------------------------------------------------------------------
 * SAIRNfreedom: the per-post EXEMPT ENTITY STRUCTURE field, and the reporter
 * that renders what it determines. cody b22, 2026-10-17.
 *
 * WHY THIS IS A LANDED SUITE AND NOT A SCRATCHPAD DRIVER. The same batch that
 * added `taxEntityFacts()` found it with ZERO CALLERS by running Guardian 0d
 * against its own change -- dormant code, in a feature whose whole purpose is
 * to stop an assumption being silent. It was wired to `sfRenderTaxFacts()` and
 * driven in all four structural states before the push. THAT DRIVER WAS A
 * SCRATCHPAD FILE, which is exactly the defect
 * `docs/2026-10-15-fourth-b25-findings.md` section 1 was criticised for and
 * that `tests/sd_data_not_provisioned_misclass.js` exists to correct: a probe
 * that is not in the tree means nothing notices the subject getting fixed OR
 * getting worse. So it is here.
 *
 * WHAT IT ASSERTS, and the shape matters more than the count:
 *   - the UNSET state renders a NON-EMPTY box naming the unknown. A blank box
 *     reads as "no issue here", and the entire reason this field exists is
 *     that an unrecorded structure was being read as 501(c)(19).
 *   - the §45B wage floor is NEVER printed without the LIMB that licenses it.
 *     Form 8846 (2025) carries TWO floors -- $5.15 frozen at 2007-01-01 for
 *     food and beverage, the CURRENT federal minimum ($7.25 today) for the
 *     beauty-service limb -- so a bare floor is right for one population and
 *     silently wrong for the other. See §12.6a/§12.6b and §13 of
 *     docs/2026-09-17-sairnfreedom-tips-tax-treatment.md.
 *   - the `both` state DISCLOSES that two employers are possible and that this
 *     app does not record which one employs a given tipped worker. A feature
 *     that records a structure it cannot key rows by must say so.
 *   - an unrecognised stored value falls to the UNSET branch and is not echoed
 *     into innerHTML raw.
 *
 * NOTHING HERE COMPUTES A §45B CREDIT, and that is asserted rather than
 * assumed: §7.3 of the tips document is explicit that building toward the
 * credit pushes the decision the wrong way round, because reaching §45B needs
 * the post to first be in the UBIT state it is trying to stay out of.
 *
 * EXIT CODES: 0 clean, 1 an arm failed, 2 COULD NOT RUN. The third state is
 * never folded into the first -- if an anchor below stops matching, this file
 * says the extraction failed and which anchor, rather than reporting a pass it
 * never performed.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'sairnfreedom.html');

/* ── EXTRACTION, and it FAILS CLOSED ─────────────────────────────────────────
 * The subject is a single-file browser app with no module boundary, so the two
 * regions are sliced out by anchor and evaluated. EVERY ANCHOR IS ASSERTED
 * UNIQUE: `indexOf` alone would silently take the first of several, and a slice
 * that starts in the wrong place produces arms that test nothing. That is the
 * branchOf() overrun defect from the not_provisioned suite, one file over. */
function region(src, startAnchor, endAnchor) {
  const nStart = src.split(startAnchor).length - 1;
  const nEnd = src.split(endAnchor).length - 1;
  if (nStart !== 1) {
    couldNotRun('start anchor ' + JSON.stringify(startAnchor) + ' occurs '
      + nStart + ' times, expected exactly 1');
  }
  if (nEnd !== 1) {
    couldNotRun('end anchor ' + JSON.stringify(endAnchor) + ' occurs '
      + nEnd + ' times, expected exactly 1');
  }
  const i = src.indexOf(startAnchor);
  const j = src.indexOf(endAnchor, i);
  if (j <= i) {
    couldNotRun('end anchor ' + JSON.stringify(endAnchor)
      + ' does not follow the start anchor -- the regions have moved');
  }
  return src.slice(i, j);
}

function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + '.');
  console.log('  Nothing was asserted. This is a THIRD STATE and is not a pass:');
  console.log('  re-derive the anchors against sairnfreedom.html and fix them here.');
  process.exit(2);
}

if (!fs.existsSync(APP)) couldNotRun('sairnfreedom.html not found at ' + APP);
const SRC = fs.readFileSync(APP, 'utf8');

const DEFS = region(SRC, 'var TAX_ENTITIES = [', '/* Capabilities are the enum.');
const RENDER = region(SRC, 'function sfRenderTaxFacts(){', '\nfunction sfRenderPostFlags(){');

/* The three app globals the extracted code closes over, stubbed to the app's
 * real contracts: H() is the app's escaper, getPost() its stored record, $()
 * its element lookup. */
const PRELUDE = `
function H(s){ return String(s==null?'':s).replace(/[&<>"']/g, function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
var _POST={};
function getPost(){ return _POST; }
var _BOX={innerHTML:null};
function $(id){ return id==='pp-taxfacts' ? _BOX : null; }
`;

let api;
try {
  // eslint-disable-next-line no-new-func
  api = new Function(PRELUDE + DEFS + '\n' + RENDER + `
    return { render:sfRenderTaxFacts, facts:taxEntityFacts,
             entities:TAX_ENTITIES, limbs:SEC45B_LIMBS,
             setPost:function(p){ _POST=p; }, box:function(){ return _BOX.innerHTML; } };
  `)();
} catch (e) {
  couldNotRun('the extracted regions do not evaluate: ' + e.message);
}

const failed = [];
let run = 0;
function arm(label, cond, detail) {
  run++;
  if (cond) { console.log('  ok   ' + label); return; }
  console.log('  FAIL ' + label);
  if (detail) console.log('         got: ' + String(detail).slice(0, 400));
  failed.push(label);
}
function paint(id) { api.setPost({ taxEntity: id }); api.render(); return api.box(); }

console.log('SAIRNfreedom exempt-entity structure -- ' + APP);
console.log('');
console.log('PRECONDITIONS -- each a third state, never folded into a pass');

arm('P1. the three structural shapes are the ones the research named: c19, c7, both',
  api.entities.map(function (e) { return e.id; }).join(',') === 'c19,c7,both',
  api.entities.map(function (e) { return e.id; }).join(','));

arm('P2. §45B(b)(2) carries TWO limbs with DIFFERENT floors, read off Form 8846 '
  + '-- a single floor is the defect this models away',
  api.limbs.length === 2
  && api.limbs[0].floor !== api.limbs[1].floor
  && api.limbs.filter(function (l) { return l.frozen; }).length === 1,
  JSON.stringify(api.limbs.map(function (l) { return [l.id, l.floor, l.frozen]; })));

arm('P3. the frozen limb is the FOOD-AND-BEVERAGE one at 5.15, and the UNFROZEN '
  + 'one is beauty service at 7.25 -- the pairing, not just the values',
  api.limbs[0].id === 'food_bev' && api.limbs[0].floor === 5.15 && api.limbs[0].frozen === true
  && api.limbs[1].id === 'beauty' && api.limbs[1].floor === 7.25 && api.limbs[1].frozen === false);

console.log('');
console.log('A. THE UNSET STATE -- the assumption this field exists to remove');

const u = paint('');
arm('A1. it renders a NON-EMPTY box. A blank box reads as "no issue here", and '
  + 'an unrecorded structure being read as 501(c)(19) is the whole defect',
  !!u && u.length > 40, JSON.stringify(u));
arm('A2. it says the entity is NOT RECORDED', /not recorded/i.test(u), u);
arm('A3. ...and says in terms that it is NOT DEFAULTED to 501(c)(19)',
  /not defaulted/i.test(u), u);
arm('A4. and prints NO wage floor, because nothing is determined yet',
  !/5\.15|7\.25/.test(u), u);

console.log('');
console.log('B. EACH CONFIGURED SHAPE REPORTS ITS OWN AUTHORITY');

const a = paint('c19');
arm('B1. c19 names 501(c)(19) and §512(a)(1)',
  a.indexOf('501(c)(19)') >= 0 && a.indexOf('512(a)(1)') >= 0, a);
arm('B2. c19 says Rev. Rul. 2003-64 is answered IN PRINCIPLE and NOT on all fours '
  + '-- §512(a)(3) does not apply to a (c)(19), so the ruling\'s facts do not transfer',
  /in principle, not on all fours/i.test(a), a);

const b = paint('c7');
arm('B3. c7 names §512(a)(3)', b.indexOf('512(a)(3)') >= 0, b);
arm('B4. c7 says the ruling IS on all fours with this structure',
  /on all fours with this structure/i.test(b), b);

const c = paint('both');
arm('B5. both names BOTH IRC paragraphs rather than picking one',
  c.indexOf('501(c)(19)') >= 0 && c.indexOf('501(c)(7)') >= 0, c);
/* B6 IS ASSERTED ON THE `unknowns` LIST, NOT ON THE RENDERED HTML, AND THE
   FIRST VERSION WAS WRONG IN EXACTLY THE WAY THIS REPO KEEPS PAYING FOR.
   It read `c.indexOf('TWO EMPLOYERS') >= 0` against the box, and an ablation
   that DELETED the two-employer unknown LEFT IT GREEN -- because
   `TAX_ENTITIES[both].note` also contains the words "TWO EMPLOYERS ARE
   POSSIBLE" and the renderer prints that note too. An arm satisfied by a
   DIFFERENT string than the one it intends to check is the P5-satisfied-by-a-
   comment defect from tests/sd_data_not_provisioned_misclass.js, found by
   ablation in the same batch, one file over. It now checks the list the
   disclosure actually lives in, requires it to REACH the rendered unknowns
   block, and -- the discriminating half -- requires the single-entity shapes
   NOT to carry it, so a disclosure pushed unconditionally would fail too. */
api.setPost({ taxEntity: 'both' });
const bothUnknowns = api.facts().unknowns;
arm('B6. both DISCLOSES that two employers are possible and that this app does '
  + 'NOT record which entity employs a given tipped worker -- as a NAMED UNKNOWN, '
  + 'and it reaches the rendered unknowns block',
  bothUnknowns.some(function (k) { return /TWO EMPLOYERS/.test(k); })
  && /Still open[\s\S]*TWO EMPLOYERS/.test(c), JSON.stringify(bothUnknowns));
arm('B6b. ...and NEITHER single-entity shape carries that unknown, so the arm '
  + 'above cannot be satisfied by a disclosure pushed unconditionally',
  ['c19', 'c7'].every(function (id) {
    api.setPost({ taxEntity: id });
    return !api.facts().unknowns.some(function (k) { return /TWO EMPLOYERS/.test(k); });
  }));

console.log('');
console.log('C. THE FLOOR IS NEVER PRINTED WITHOUT THE LIMB THAT LICENSES IT');

['c19', 'c7', 'both'].forEach(function (id) {
  const h = paint(id);
  arm('C[' + id + ']. the floor appears WITH its limb named, never alone',
    h.indexOf('5.15') >= 0 && h.indexOf('food_bev') >= 0, h);
  arm('C[' + id + ']. ...and the OTHER limb is disclosed as carrying a different floor',
    h.indexOf('other limb carries a different floor') >= 0, h);
  arm('C[' + id + ']. ...and the app still claims to COMPUTE nothing',
    /nothing in this app calculates the credit/i.test(h), h);
});

console.log('');
console.log('D. CONTROLS');

const x = paint('<img src=x onerror=alert(1)>');
arm('D1. an unrecognised stored value falls to the UNSET branch and is NOT '
  + 'echoed into innerHTML raw',
  x.indexOf('<img') < 0 && /not recorded/i.test(x), x);

const f = (api.setPost({ taxEntity: 'both' }), api.facts());
arm('D2. taxEntityFacts() reports the limb and the floor TOGETHER, so a caller '
  + 'cannot read the figure without the population it applies to',
  f.limb === 'food_bev' && f.floor === 5.15 && typeof f.floorBasis === 'string'
  && f.floorBasis.indexOf('8846') >= 0, JSON.stringify(f));
arm('D3. ...and every configured shape carries at least one named unknown, '
  + 'because "customary tipping" is a factual test §45B(b)(2) supplies no criteria for',
  ['c19', 'c7', 'both'].every(function (id) {
    api.setPost({ taxEntity: id });
    return api.facts().unknowns.length >= 1;
  }));

console.log('');
console.log(run + ' checks run, ' + failed.length + ' failed');
if (failed.length) {
  console.log('');
  console.log(failed.length + ' ARM(S) FAILED:');
  failed.forEach(function (l) { console.log('  - ' + l); });
  console.log('');
  console.log('NO ARM HERE IS EXPECTED RED. Every failure is a real one. An A arm '
    + 'means the unset state has started reading as an answer; a B arm means a '
    + 'structure reports the wrong authority; a C arm means a §45B floor is being '
    + 'shown without the limb that licenses it, which is wrong for one of the two '
    + 'populations; a D arm means escaping or the limb/floor pairing broke.');
  process.exit(1);
}
process.exit(0);
