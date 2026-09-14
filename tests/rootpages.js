// tests/rootpages.js
//
// THE ONE DEFINITION OF "a root app page this repository ships".
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// Four suites independently did `fs.readdirSync(ROOT).filter(f =>
// f.endsWith('.html'))`, which asserts over whatever .html happens to be in a
// clone's WORKING DIRECTORY -- untracked files included. On 2026-09-14 an
// untracked `piac.html` (dated 2026-08-28, never committed) turned
// tests/public_token_leaves_the_address_bar.js RED, while the same suite was
// GREEN on a clean origin/main worktree.
//
// The other three survived it by LUCK, not by design:
//   licence_rekey_isolation.js     filters on /^sairn|^stonedesk/, and
//                                  `piac` matches neither
//   idless_rows_are_reported.js    its assertion tolerated the extra file
//   sairn_storage_wrapper_honesty  the same, at three separate call sites
// A differently-named stray would have taken any of them red.
//
// ── A FALSE RED IS NOT THE HARMLESS DIRECTION ─────────────────────────────
// A suite that goes red for reasons unrelated to the code is one people learn
// to skip, and the next time it is red for a real reason nobody looks. That
// costs more than a false green, which at least stays quiet. This platform has
// the receipt for the other direction too: `run_all_tests.py --hook` is paused,
// so a suite that goes red can stay red for days, and two did.
//
// ── ONE DEFINITION, BECAUSE FOUR COPIES OF A RULE IS FOUR PLACES TO DRIFT ──
// "A root app page" is a fact about what the repository SHIPS -- the git index
// -- not about somebody's working directory. `:!:*/*` excludes subdirectories,
// so dist/ and node_modules/ cannot creep in.
//
// FAILS CLOSED. An empty or implausibly short list is a broken reader or a
// wrong pathspec, and every caller's loop would pass VACUOUSLY against it. It
// throws rather than returning [], because "no pages to check" and "checked
// every page" are indistinguishable from the outside once the loop has run.

'use strict';
const cp = require('child_process');
const fs = require('fs');
const assert = require('assert');

// The floor is a plausibility check, not a count anybody maintains: there are
// 22 today and the number moves when an app is added. Anything under 15 means
// the reader is broken, not that the platform shrank by a third overnight.
const MIN_PAGES = 15;

function rootPages(root, opts) {
  const o = opts || {};
  let out;
  try {
    out = cp.execFileSync('git', ['-C', root, 'ls-files', '--', '*.html', ':!:*/*'],
                          { encoding: 'utf8' });
  } catch (e) {
    throw new assert.AssertionError({
      message: 'git ls-files could not run in ' + root + ' (' +
        ((e && e.message) || e) + '). NOTHING was checked -- this is not a '
        + 'repository with no app pages.'
    });
  }
  const tracked = out.split('\n').map((s) => s.trim()).filter(Boolean);
  assert.ok(tracked.length >= MIN_PAGES,
    'git ls-files returned ' + tracked.length + ' root .html files, under the '
    + MIN_PAGES + ' floor -- that is a broken reader or a wrong pathspec, not a '
    + 'platform with no app pages. Every loop over this list would have passed '
    + 'vacuously.');

  if (o.announce !== false) {
    // NAMED, NOT SILENTLY SKIPPED. Excluding an untracked page is right;
    // pretending it is not there is not -- a stray app page in a clone is worth
    // somebody knowing about, and this is the only thing that looks.
    const strays = fs.readdirSync(root)
      .filter((f) => f.endsWith('.html') && tracked.indexOf(f) === -1);
    if (strays.length) {
      console.log('       (ignoring ' + strays.length + ' UNTRACKED .html in this '
        + 'working directory -- not files this repo ships: '
        + strays.join(', ') + ')');
    }
  }
  return tracked.sort();
}

module.exports = { rootPages, MIN_PAGES };
