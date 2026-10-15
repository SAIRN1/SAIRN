// api/b15-corrections-hydrate.test.js
//
// Run:  node api/b15-corrections-hydrate.test.js
//
// b14 OPEN ITEM 2. The corrections queue reads LOCAL rows --
// senPendingCorrections() is built from visits(), which is server-merged by
// senHydrateVisits(). So a scheduler who opens the tab before a hydrate has
// completed sees an empty table under the sentence "Nothing is waiting", which
// is a FALSE STATEMENT about somebody's unpaid clock correction. It is the
// affirmative-false-success shape, and the queue was built in b14 precisely to
// stop a submission being invisible.
//
// TWO ARMS, BOTH NECESSARY, AND THE SECOND IS THE ONE THAT MATTERS:
//   * the tab must HYDRATE before it renders;
//   * and when it renders with no data of its own it must not CLAIM nothing is
//     waiting. A hydrate that fails -- offline, 503, an expired session --
//     leaves the same empty list, and "nothing is waiting" is still wrong.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '..');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

const HTML = (function () {
  try { return fs.readFileSync(path.join(ROOT, 'sairnsenior.html'), 'utf8'); }
  catch (e) { return null; }
})();
function lift(name) {
  if (HTML === null) return null;
  const re = new RegExp('\\nfunction ' + name + '\\([^)]*\\)\\{[\\s\\S]*?\\n\\}');
  const m = HTML.match(re);
  return m ? m[0] : null;
}

console.log('b15. the corrections tab must hydrate before it claims the queue is empty\n');

(async () => {
  if (HTML === null) {
    ['H1', 'H2', 'H3', 'H4'].forEach((n) => cannot(n + '. sairnsenior.html unreadable', 'ENOENT'));
  } else {
    // ── H1/H2. THE TAB HYDRATES, DRIVEN ───────────────────────────────────
    // THE HELPERS THE RENDER NOW SPLITS INTO ARE LIFTED TOO. The first draft
    // lifted only renderCorrectionsView and got a ReferenceError for
    // _renderCorrectionsRows -- which this suite would have reported as "the
    // extracted functions would not run", i.e. as an unproven arm about the
    // fixture rather than about the thing being measured.
    const names = ['renderCorrectionsView', '_renderCorrectionsRows',
                   '_corrFreshness', 'senPendingCorrections',
                   'vsCorrectionsBadgeText'];
    const missing = names.filter((n) => lift(n) === null);
    if (missing.length) {
      bad('H1. the corrections functions are not all present',
          'missing: ' + missing.join(', '));
      bad('H2. depends on H1', 'missing');
    } else {
      const els = {};
      const el = (id) => (els[id] = els[id] || { id: id, innerHTML: '',
                                                 textContent: '', style: {}, className: '' });
      let hydrated = 0;
      const sandbox = {
        console: console, $: el, H: (s) => String(s == null ? '' : s),
        senSession: { employee_id: 'S1', role: 'owner', token: 't' },
        senIsScheduler: () => true,
        VISITS: [],
        visits: function () { return sandbox.VISITS; },
        senHydrateVisits: function () { hydrated += 1; return Promise.resolve(true); },
        senData: () => Promise.resolve(null),
        senLastErrText: () => '',
        fdatetime: (v) => String(v),
        toast: function () {}, Array: Array, String: String, JSON: JSON,
        Promise: Promise, Object: Object
      };
      vm.createContext(sandbox);
      let booted = true;
      try { vm.runInContext(names.map(lift).join('\n'), sandbox); }
      catch (e) { booted = false; cannot('H1. the extracted functions would not run', String(e)); }
      if (booted) {
        const r = sandbox.renderCorrectionsView();
        // The render may now be async because it hydrates first.
        if (r && typeof r.then === 'function') await r;
        is(hydrated >= 1,
           'H1. renderCorrectionsView() calls senHydrateVisits(). Before this '
         + 'the queue read whatever was in the local store, so a scheduler '
         + 'opening the tab on a cold device saw an empty table',
           'senHydrateVisits called ' + hydrated + ' time(s)');
        const html = el('vs-view-corrections').innerHTML;
        is(/await|Loading|Checking/i.test(html) || html.length > 0,
           'H2. ...and it renders something afterwards rather than leaving the '
         + 'panel blank while it waits',
           JSON.stringify(html.slice(0, 160)));
      }
    }

    // ── H3. THE EMPTY STATE NO LONGER CLAIMS NOTHING IS WAITING ──────────
    // Read off the source, because what is being asserted is the ABSENCE of a
    // confident sentence, and the cheapest proof is that the string is gone.
    is(HTML.indexOf('Nothing is waiting.') === -1,
       'H3. THE ARM THAT MATTERS -- the empty state no longer says "Nothing is '
     + 'waiting." A hydrate that FAILED (offline, 503, expired session) leaves '
     + 'exactly the same empty list, so that sentence is a claim the page '
     + 'cannot support and it is the one a scheduler would act on',
       'the sentence is still in sairnsenior.html');
    is(/as of|last checked|could not|has not/i.test(HTML.slice(
         Math.max(0, HTML.indexOf('awaiting approval') - 2500),
         HTML.indexOf('awaiting approval') + 2500)),
       'H4. ...and the empty state says WHEN it last managed to check, or that '
     + 'it could not. "Nothing is waiting, as of a moment ago" is a claim the '
     + 'page can support; the bare version is not',
       'no freshness or failure wording near the empty state');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
