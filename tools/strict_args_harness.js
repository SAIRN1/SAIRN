#!/usr/bin/env node
/*
 * tools/strict_args_harness.js
 *
 * Standing proof for Guardian check 31. Not a one-off diagnostic.
 *
 * WHY THIS EXISTS AS A RUNNABLE TOOL RATHER THAN A PARAGRAPH IN THE SKILL.
 * On 2026-08-30 six window.fetch patches in stonedesk.html were found to be
 * silently discarding their own work: each did
 *
 *     opts = Object.assign({}, opts, { body: ... });
 *     return _orig.apply(this, arguments);
 *
 * Under 'use strict' the arguments object is NOT linked to the parameters, so
 * reassigning `opts` never reached the wrapped fetch. Three of the six were on
 * LIVE features -- Session Memory, Tone & Style, and the personalization /
 * shared-knowledge / employee-profile injector -- and all three had been doing
 * nothing, with no error, no failed request, and nothing visible on screen.
 *
 * THAT IS THE POINT. This bug class is invisible to static review (the code
 * reads correctly), invisible to visual review (nothing renders wrong), and
 * invisible to node --check (it is valid JavaScript). The ONLY thing that
 * settles it is running it. Same discipline as the rendered-DOM assertion in
 * sairn-visual-review: do not reason from the spec, execute.
 *
 * The trap that hides it: the functions carry no 'use strict' of their own.
 * They inherit it from the enclosing IIFE, which is dozens of lines away and
 * easy to miss when reading the function in isolation.
 *
 * Usage:  node tools/strict_args_harness.js
 * Exit 0 if behaviour matches what check 31 documents, 1 if it does not.
 */

'use strict';

let failures = 0;

function expect(label, actual, wanted) {
  const ok = actual === wanted;
  if (!ok) failures++;
  // padEnd, not printf width specifiers -- console.log supports %s but NOT
  // '%-46s', which prints the format string literally instead of padding.
  console.log('  ' + (ok ? 'ok  ' : 'FAIL') + ' ' + label.padEnd(44) +
              ' got ' + String(actual).padEnd(9) + ' want ' + String(wanted));
}

// ---------------------------------------------------------------------------
// Part 1 -- is `arguments` linked to the parameters, per strictness mode?
// ---------------------------------------------------------------------------
console.log('\nPart 1: does reassigning a parameter update `arguments`?');

function strictOwn(url, opts) {
  'use strict';
  opts = Object.assign({}, opts, { body: 'MUTATED' });
  return arguments[1].body;
}

// The real-world shape: no 'use strict' on the function, inherited from above.
const strictInherited = (function () {
  'use strict';
  return function (url, opts) {
    opts = Object.assign({}, opts, { body: 'MUTATED' });
    return arguments[1].body;
  };
})();

const strictAsync = (function () {
  'use strict';
  return async function (url, opts) {
    opts = Object.assign({}, opts, { body: 'MUTATED' });
    return arguments[1].body;
  };
})();

// `sloppy` cannot be declared inside this file's own 'use strict', so it is
// evaluated in a non-strict Function to show the contrast honestly.
const sloppyReal = new Function('url', 'opts',
  'opts = Object.assign({}, opts, { body: "MUTATED" }); return arguments[1].body;');

expect('non-strict function', sloppyReal('u', { body: 'ORIGINAL' }), 'MUTATED');
expect("function's own 'use strict'", strictOwn('u', { body: 'ORIGINAL' }), 'ORIGINAL');
expect('strict INHERITED from enclosing IIFE', strictInherited('u', { body: 'ORIGINAL' }), 'ORIGINAL');

// ---------------------------------------------------------------------------
// Part 2 -- the real chain shape, end to end
// ---------------------------------------------------------------------------
// Three injectors wrapping each other, exactly how stonedesk.html stacks
// Session Memory, Tone and Personalization on top of the security layers.
function buildChain(forwardStyle) {
  const innermost = (url, opts) => Promise.resolve(JSON.parse(opts.body).system);

  function injector(prev, label) {
    'use strict';
    return async function (url, opts) {
      if (opts && opts.body) {
        const body = JSON.parse(opts.body);
        if (!body.system.includes(label)) {
          body.system = label + '\n---\n' + body.system;
          opts = Object.assign({}, opts, { body: JSON.stringify(body) });
        }
      }
      if (forwardStyle === 'apply') return prev.apply(this, arguments);
      return prev.call(this, url, opts);
    };
  }

  let f = innermost;
  f = injector(f, 'SESSION MEMORY');
  f = injector(f, 'RESPONSE STYLE');
  f = injector(f, 'LEARNED USER PREFERENCES');
  return f;
}

async function layersDelivered(style) {
  const fetchLike = buildChain(style);
  const got = await fetchLike('https://sairn.vercel.app/api/claude', {
    body: JSON.stringify({ system: 'ORIGINAL APP SYSTEM PROMPT' })
  });
  return ['SESSION MEMORY', 'RESPONSE STYLE', 'LEARNED USER PREFERENCES']
    .filter((l) => got.includes(l)).length;
}

(async function () {
  const asyncInherited = await strictAsync('u', { body: 'ORIGINAL' });
  expect('async, strict inherited from IIFE', asyncInherited, 'ORIGINAL');

  console.log('\nPart 2: three chained injectors -- how many layers arrive?');
  expect('forwarding via apply(this, arguments)', await layersDelivered('apply'), 0);
  expect('forwarding via call(this, url, opts)', await layersDelivered('call'), 3);

  console.log('');
  if (failures) {
    console.log(failures + ' assertion(s) FAILED -- engine behaviour differs from what');
    console.log('Guardian check 31 documents. Investigate before trusting the check.');
    process.exit(1);
  }
  console.log('All assertions hold. Check 31 rests on real engine behaviour,');
  console.log('not on a reading of the spec.');
})();
