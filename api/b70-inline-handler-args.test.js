// hank b70 (H1y): the b69 sairnlegacy H1x check, run across hank's other owned
// apps. An inline handler's attribute is HTML-decoded BEFORE its JS runs, so a
// stored value passed as \''+x.id+'\' (raw) or '&#39;'+H(x)+'&#39;' (HTML-only)
// can close the JS string. Each app now carries the same JA():
//   JSON.stringify(String(v)), then HTML-escaped.
//
// D arms drive each app's own JA() through attribute-decode then JS-parse with
// hostile ids. S arms fail if a raw or HTML-only argument comes back. Arm X
// runs the S scan over each file as committed at 8e481cea7 (before this fix)
// and REQUIRES findings, so the scan cannot pass vacuously.
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
// stonedesk.html is NOT here: fourth held an active stonedesk claim when this
// landed, so its 2 sites are a parked patch (hank b70 handoff, item H1y-SD).
const APPS = ['sairnvet.html', 'sairnbiz.html', 'sairncode.html'];
const BASE = '8e481cea7';
// Not record values: loop indexes, a fixed status map, a selector constant,
// and StoneDesk's escAttrJs(), which is already JS-escape-then-HTML-escape.
const ALLOWED = /^(?:i|idx|nextStatus|panelId|escAttrJs\(.*\))$/;
// sairnbiz and stonedesk keep the single-quoted form their suites pin, made safe
// by JS-escaping backslash and quote BEFORE the HTML escape.
const JSESC = '.replace(/[\\\\\\u0027]/g,\'\\\\$&\')';
const isJsEscaped = (e) => /^(?:H|escHtml)\(String\(.+\)/.test(e) && e.endsWith(JSESC + ')');

let passed = 0, failed = 0;
function arm(name, ok, detail) {
  if (ok) { passed++; console.log('  ok   ' + name); }
  else { failed++; console.log('  FAIL ' + name + (detail ? '  -- ' + detail : '')); }
}

function decodeAttr(v) {
  return v.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}
function run(attrValue) {
  const got = [];
  let extra = false;
  try {
    new Function('fn', 'alert', decodeAttr(attrValue))((...a) => got.push(a), () => { extra = true; });
  } catch (e) { return { err: e.message, got, extra }; }
  return { got, extra };
}

function scan(src) {
  const bad = [];
  const attrRe = /on(?:click|change|input|submit|keydown|keyup|blur|focus|dblclick|mouseover)="([^"]*)"/g;
  const rawRe = /\\''\+(.+?)\+'\\'/g;
  let m, r;
  while ((m = attrRe.exec(src))) {
    while ((r = rawRe.exec(m[1]))) if (!ALLOWED.test(r[1]) && !isJsEscaped(r[1])) bad.push(r[1]);
  }
  const builders = (src.match(/'&#39;'\+(?:H|escHtml)\([^\n]*?\+'&#39;'/g) || [])
    .filter((b) => b.indexOf(JSESC) === -1);
  return bad.concat(builders);
}

const HOSTILE = ["x');alert(1);//", 'a"b<c>&\'d\\e', '</script><img src=x>', ''];

APPS.forEach((app) => {
  const src = fs.readFileSync(path.join(ROOT, app), 'utf8');
  // sairnvet and sairncode carry JA(). sairnbiz and stonedesk write the
  // single-quoted form inline -- JS-escape, then their own HTML escape --
  // because their suites load app functions by hand-kept lists (a new global
  // breaks them) and pin the fn('ID') markup.
  const def = src.match(/^function JA\(s\)\{[^\n]*\}$/m);
  const escName = { 'sairnbiz.html': 'H', 'stonedesk.html': 'escHtml' }[app];
  const escDef = escName && src.match(new RegExp('^function ' + escName + '\\(s\\)\\{[^\\n]*\\}$', 'm'));
  let JA;
  if (def) JA = new Function(def[0] + '\nreturn JA;')();
  else if (escDef && src.indexOf('(String(') !== -1 && src.indexOf(JSESC) !== -1) {
    const e = new Function(escDef[0] + '\nreturn ' + escName + ';')();
    // The literal is taken from the file, so a weakened escape in the app fails here.
    const jsesc = new Function('v', 'return String(v)' + JSESC + ';');
    JA = (v) => "'" + e(jsesc(v)) + "'";
  } else { arm(app + ': an encoder is defined', false, 'neither JA() nor the inline escape found'); return; }
  HOSTILE.forEach((id) => {
    const attr = 'fn(' + JA(id) + ')';
    const r = run(attr);
    arm(app + ' D. JA(' + JSON.stringify(id) + ') reaches the handler as exactly that string',
      !r.err && !r.extra && r.got.length === 1 && r.got[0][0] === id && attr.indexOf('"') === -1, JSON.stringify(r));
  });
  const left = scan(src);
  arm(app + ' S. no raw or HTML-only value is passed from an inline handler', left.length === 0, left.join(' | '));
  let old = null;
  try { old = execFileSync('git', ['show', BASE + ':' + app], { cwd: ROOT, maxBuffer: 1 << 26 }).toString(); } catch (e) { /* below */ }
  arm(app + ' X. ABLATION: the same scan finds the shape at ' + BASE, old !== null && scan(old).length > 0,
    old === null ? 'COULD NOT READ ' + BASE : 'found ' + scan(old).length);
});

const raw = run("fn('" + HOSTILE[0] + "')");
arm('X. ABLATION: a raw value between quotes runs injected code', raw.extra === true, JSON.stringify(raw));

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
