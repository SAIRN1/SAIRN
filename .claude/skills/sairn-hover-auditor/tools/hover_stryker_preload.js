// hover_stryker_preload.js -- loaded with `node -r` by hover_stryker_signal.py's test command.
//
// WHY. Stryker instruments a COPY of the mutated file in its sandbox. A test
// that reads the source's TEXT (fs.readFileSync) to build its own mutants by
// string anchor finds the instrumented text, so every anchor matches 0 times,
// the test exits 2 COULD NOT RUN in Stryker's dry run, and (worse) exit 2 would
// shadow a real arm failure on every mutant. This returns the PRISTINE text for
// those reads and leaves `require` alone, so the file is still loaded
// instrumented and the test's own arms and in-file mutation controls behave as
// they do in a plain checkout.
//
// Loader reads are told apart by the immediate caller frame (Node's CJS loader),
// not by path: a test's own top-level code also runs inside Module._extensions.
'use strict';
const fs = require('fs');
const path = require('path');
const pristineRoot = process.env.HOVER_STRYKER_PRISTINE;
const targets = (process.env.HOVER_STRYKER_TARGETS || '').split('|').filter(Boolean);
if (pristineRoot && targets.length) {
  const orig = fs.readFileSync;
  const LOADER = /Module\._extensions|Module\.load|Module\._load|Module\._compile|cjs\/loader|loadSource/;
  fs.readFileSync = function (p, ...rest) {
    if (typeof p === 'string' || p instanceof URL) {
      let abs;
      try { abs = path.resolve(p instanceof URL ? p.pathname : p); } catch (e) { abs = null; }
      if (abs) {
        const rel = path.relative(process.cwd(), abs).split(path.sep).join('/');
        if (targets.indexOf(rel) !== -1) {
          const caller = (new Error().stack || '').split('\n')[2] || '';
          if (!LOADER.test(caller)) {
            return orig.call(fs, path.join(pristineRoot, rel), ...rest);
          }
        }
      }
    }
    return orig.call(fs, p, ...rest);
  };
}
