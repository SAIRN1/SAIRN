// hank b69 (H1x, from H1 #1734; moved from tests/ to api/, which hank owns): sairnlegacy.html passed stored record ids
// into inline handlers as raw text between \' quotes, e.g.
//     onclick="advanceKeepsakeOrder(\''+o.id+'\')"
// The server write branch checks no format of id, so an id holding a quote
// closes the JS string and runs in whoever opens the page. Every such site now
// goes through JA(): a JSON string literal, HTML-escaped, because the browser
// HTML-decodes the attribute BEFORE the JS runs.
//
// Arms D drive the real H() and JA() from the file through the same two steps
// a browser takes (attribute decode, then JS parse). Arm X drives the OLD raw
// form and the OLD idArg form (&#39;+H(id)+&#39;) and REQUIRES both to break,
// so this cannot pass against code that never had the defect.
'use strict';
const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(path.join(__dirname, '..', 'sairnlegacy.html'), 'utf8');
let passed = 0, failed = 0;
function arm(name, ok, detail) {
  if (ok) { passed++; console.log('  ok   ' + name); }
  else { failed++; console.log('  FAIL ' + name + (detail ? '  -- ' + detail : '')); }
}

function src(name) {
  const m = SRC.match(new RegExp('function ' + name + '\\(s\\)\\{[^\\n]*\\}'));
  return m ? m[0] : null;
}
const hSrc = src('H'), jaSrc = src('JA');
if (!hSrc || !jaSrc) {
  console.log('COULD NOT RUN: H() or JA() not found in sairnlegacy.html');
  process.exit(2);
}
// One scope, as in the page: JA calls H.
const { H, JA } = new Function(hSrc + '\n' + jaSrc + '\nreturn { H: H, JA: JA };')();

// What the browser does with onclick="...": decode entities, then run as JS.
function decodeAttr(v) {
  return v.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}
function run(attrValue) {
  const got = [];
  let extra = false;
  const stub = (...a) => { got.push(a); };
  try {
    new Function('fn', 'alert', decodeAttr(attrValue))(stub, () => { extra = true; });
  } catch (e) { return { err: e.message, got, extra }; }
  return { got, extra };
}

const HOSTILE = ["x');alert(1);//", 'a"b<c>&\'d\\e', "O'Brien", '</script><img src=x>', ''];

HOSTILE.forEach((id) => {
  const attr = 'fn(' + JA(id) + ')';
  const r = run(attr);
  arm('D. JA(' + JSON.stringify(id) + ') reaches the handler as exactly that string, nothing else runs',
    !r.err && !r.extra && r.got.length === 1 && r.got[0][0] === id, JSON.stringify(r));
  arm('D. ...and the attribute value carries no raw " to end the attribute early', attr.indexOf('"') === -1, attr);
});

// ── ARM X: the OLD forms really did break. ──────────────────────────────────
const raw = run("fn('" + HOSTILE[0] + "')");
arm('X. ABLATION: the old raw \\\'+id+\\\' form runs injected code', raw.extra === true, JSON.stringify(raw));
const oldIdArg = run('fn(' + '&#39;' + H(HOSTILE[0]) + '&#39;' + ')');
arm("X. ABLATION: the old idArg form (&#39;+H(id)+&#39;) runs injected code too -- H() alone is not enough here",
  oldIdArg.extra === true, JSON.stringify(oldIdArg));

// ── STRUCTURE: no record value is interpolated raw into a handler any more.
const attrRe = /on(?:click|change|input|submit|keydown|keyup|blur|focus)="([^"]*)"/g;
const rawRe = /\\''\+(.+?)\+'\\'/g;
const left = [];
let m;
while ((m = attrRe.exec(SRC))) {
  let r;
  while ((r = rawRe.exec(m[1]))) if (r[1] !== 'nextStatus') left.push(r[1]);
}
arm('S. no handler attribute interpolates a value raw between \\\' quotes (nextStatus is a fixed map, allowed)',
  left.length === 0, left.join(', '));
arm('S. the employee id argument goes through JA', /var idArg=JA\(e\.employee_id\);/.test(SRC));
const jaCount = (SRC.match(/\+JA\([a-z]\.(?:id|case_id)\)\+/g) || []).length;
arm('S. 33 record-id arguments go through JA (count moved -> re-read this test)', jaCount === 33, 'got ' + jaCount);

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
