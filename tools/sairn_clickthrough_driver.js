/* tools/sairn_clickthrough_driver.js
 *
 * Drives every nav control in a SIGNED-IN SAIRN app and reports what actually
 * happened. This is the half no static checker can do: Guardian's own
 * "Known Scope Limitation" section says a clean code-level pass on an
 * auth-gated app is "the code looks right assuming the gate opens correctly",
 * never "the real app works".
 *
 * HOW TO USE
 *   1. Open the app and SIGN IN. A run against the licence or PIN screen
 *      describes that screen; the output records `navControls` so an empty
 *      run is visible rather than silent.
 *   2. LEAVE THE TAB IN THE FOREGROUND for the whole run. See the throttling
 *      note below -- this is not optional and it is not cosmetic.
 *   3. Paste this whole file. It returns immediately and runs in the
 *      background; poll `SCT.report()` until `SCT.running` is false.
 *
 * ── THE TAB MUST STAY FOREGROUND, AND HERE IS WHY ────────────────────────
 * Chrome throttles setTimeout in a hidden tab to roughly nothing. StoneDesk's
 * sbNav() puts EVERY panel's render hook inside a setTimeout, so a hidden tab
 * never renders any panel body. The first run of this driver was done hidden
 * and every one of 67 panels read blank -- 67 findings, all of them the
 * browser's power management. `document.visibilityState` is recorded in the
 * output so a run that was throttled can be thrown away rather than believed.
 *
 * ── THE THREE DETECTOR DEFECTS THIS FILE ALREADY SURVIVED ────────────────
 * Every one produced confident findings against a clean app. They are kept
 * here because each is a named class this platform keeps re-learning, and a
 * reimplementation will make them again.
 *
 *   1. A WRONG MODEL OF THE PAGE. v1 assumed a nav id resolves to
 *      `panel-<id>`. Three StoneDesk entries do not: Field Quote, Doc Scanner
 *      and Check Register are `.page` modules with `page-<id>` ids, shown by a
 *      SECOND nav system (window.showPage). showPanel's own comment at
 *      stonedesk.html:13031 says so in plain words. Three "dead nav buttons"
 *      reported against a feature that works. resolve() now tries both, and
 *      takes the nav ARGUMENT rather than the button id, because svNav() is
 *      passed the full `panel-x`.
 *
 *   2. A METHOD CALL IS NOT A GLOBAL. v1 matched `name(` anywhere in a handler
 *      attribute, so `event.preventDefault()`, `document.getElementById()`,
 *      `arr.reduce()` and `el.click()` were collected and reported missing --
 *      `window.preventDefault` is of course undefined. Twenty findings, all
 *      the same mistake. The pattern now refuses a name preceded by a dot.
 *
 *   4. A FIXED WAIT CANNOT MEASURE AN ASYNC RENDER -- AND RE-CLICKING TO
 *      CHECK MAKES IT WORSE. SAIRNvet's `panel-access` measured 0 controls.
 *      `svRenderAccess()` writes "Loading sign-ins..." and then fills the
 *      table from a real `/api/sv-auth` round trip, which takes longer than
 *      the 320ms wait, so what got measured was the placeholder.
 *
 *      THE TRAP IS THE SECOND PASS, not the first. Re-running the driver
 *      reproduced 0 controls EXACTLY -- which reads as confirmation and is
 *      the opposite: clicking the control RE-ARMS the render, resets the
 *      container to the placeholder and refetches. Two passes agreeing meant
 *      only that the same race was run twice.
 *
 *      settle() below is the measurement that is not racing anything: it
 *      clicks NOTHING, reads every target after the run, and uses
 *      `textContent` because `innerText` returns '' for a hidden element.
 *      Settled, `panel-access` is text=302 ctrls=1. ALWAYS report settle().
 *
 *   3. TEXT INSIDE A STRING LITERAL IS NOT CODE. Even then, `panel-priceintel`
 *      reported Entry / Mid / Premium as missing globals. They are words
 *      inside a quoted ARGUMENT -- material names like 'Granite Entry (Lv
 *      1-2)' -- and `Entry (` reads as a call to a regex that cannot see
 *      quotes. Measured on the live page: 4 hits before stripping string
 *      literals, 0 after. This is PR 1.2 exactly, arrived at independently on
 *      a different surface.
 *
 * WHAT IT REPORTS, and what each finding means:
 *   F1 nav-dead     the control was clicked and its target never became visible
 *   F2 blank        the target is visible and has effectively no content
 *   F3 threw        a JS error fired during or just after the click
 *   F4 handler-gone a control inside the target names a function that does not
 *                   exist at RUNTIME -- the live half of the dead-button audit
 *
 * WHAT IT DOES NOT DO, said plainly so a clean run is not over-read: it CLICKS
 * NAV ONLY. It does not fill a form, submit anything, or click a control
 * inside a panel -- deliberately, because those write real rows to a real
 * licence. A clean run means every panel opens, renders and wires its
 * handlers. It does not mean any feature works.
 */
(() => {
  const NAV_FN = (window.__SCT_NAV_FN) || (
    typeof sbNav === 'function' ? 'sbNav' :
    typeof svNav === 'function' ? 'svNav' :
    typeof scpNav === 'function' ? 'scpNav' :
    typeof nav === 'function' ? 'nav' : null);
  if (!NAV_FN) return 'no nav function found -- set window.__SCT_NAV_FN first';

  const SCT = window.SCT = { i: 0, rows: [], errors: [], running: true, navFn: NAV_FN };
  if (!window.__sctTrap) {
    window.__sctTrap = true;
    window.addEventListener('error', e =>
      SCT.errors.push(String(e.message) + ' @' + String(e.filename || '').split('/').pop() + ':' + e.lineno));
    window.addEventListener('unhandledrejection', e =>
      SCT.errors.push('rejection: ' + String((e.reason && e.reason.message) || e.reason)));
  }

  // Found by the handler that CALLS the nav function, not by a class: the
  // three apps use .sb-btn, .sidebar-btn and bare <a>, and a class list is one
  // more thing to keep true.
  const ARG = new RegExp(NAV_FN + "\\s*\\(\\s*['\"]([^'\"]+)['\"]");
  SCT.controls = [...document.querySelectorAll('[onclick]')]
    .map(el => { const m = (el.getAttribute('onclick') || '').match(ARG); return m ? { el, arg: m[1] } : null; })
    .filter(Boolean);

  const HANDLERS = ['onclick', 'onchange', 'oninput', 'onsubmit', 'onkeyup', 'onkeydown', 'onblur', 'onfocus'];
  // Lesson 2: not preceded by a dot. Lesson 3: run it over stripped text.
  const CALL = /(^|[^.\w$])([A-Za-z_$][\w$]*)\s*\(/g;
  const stripStrings = s => s.replace(/'[^']*'/g, "''").replace(/"[^"]*"/g, '""');
  const KEYWORD = new Set(['if', 'for', 'while', 'switch', 'return', 'function', 'typeof', 'new', 'catch',
    'try', 'void', 'delete', 'in', 'of', 'let', 'const', 'var', 'class', 'await', 'async', 'super',
    'throw', 'else', 'do', 'yield', 'case', 'instanceof']);

  // Lesson 1: the argument may already carry a prefix, and the target may be a
  // page rather than a panel.
  function resolve(arg) {
    return document.getElementById(arg)
        || document.getElementById('panel-' + arg)
        || document.getElementById('page-' + arg)
        || null;
  }
  function visible(el) {
    if (!el) return false;
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && (r.width > 0 || r.height > 0);
  }

  function record(arg, label, before, threw) {
    const el = resolve(arg);
    let chars = 0, ctrls = 0, missing = [];
    if (el) {
      chars = (el.innerText || '').replace(/\s+/g, ' ').trim().length;
      ctrls = el.querySelectorAll('button,input,select,textarea,a[href],[onclick]').length;
      const names = new Set();
      el.querySelectorAll('*').forEach(node => HANDLERS.forEach(h => {
        const v = node.getAttribute && node.getAttribute(h);
        if (!v) return;
        const src = stripStrings(v);
        let m; CALL.lastIndex = 0;
        while ((m = CALL.exec(src)) !== null) names.add(m[2]);
      }));
      names.forEach(n => { if (!KEYWORD.has(n) && typeof window[n] !== 'function') missing.push(n); });
    }
    SCT.rows.push({ arg, label, exists: !!el, targetId: el ? el.id : null, vis: visible(el),
                    chars, ctrls, missing, threw, errs: SCT.errors.slice(before) });
  }

  (function tick() {
    if (SCT.i >= SCT.controls.length) { SCT.running = false; return; }
    const { el, arg } = SCT.controls[SCT.i];
    const label = (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 30);
    const before = SCT.errors.length;
    let threw = null;
    try { el.click(); } catch (e) { threw = String((e && e.message) || e); }
    // 320ms: sbNav's render hooks are themselves in a setTimeout(0), and some
    // renders chain a second one. Shorter reported blank panels that were not.
    setTimeout(() => { record(arg, label, before, threw); SCT.i++; setTimeout(tick, 15); }, 320);
  })();

  // Lesson 4. Run AFTER the driver finishes, and believe this over report()'s
  // F2/F4 for anything that fetches. It clicks nothing, so nothing is
  // re-armed; textContent because innerText is '' on a hidden element.
  SCT.settle = function () {
    const out = [];
    SCT.controls.forEach(({ arg }) => {
      const el = resolve(arg);
      if (!el) return;
      out.push({ arg,
        text: (el.textContent || '').replace(/\s+/g, ' ').trim().length,
        ctrls: el.querySelectorAll('button,input,select,textarea,a[href],[onclick]').length });
    });
    const moved = out.filter(s => {
      const r = SCT.rows.find(x => x.arg === s.arg);
      return r && (r.ctrls !== s.ctrls);
    }).map(s => { const r = SCT.rows.find(x => x.arg === s.arg);
      return s.arg + ': ctrls ' + r.ctrls + ' during the run -> ' + s.ctrls + ' settled'; });
    return {
      measured: out.length,
      zeroControlsWhenSettled: out.filter(s => s.ctrls === 0).map(s => s.arg + ' text=' + s.text),
      thinnest: out.slice().sort((a, b) => a.text - b.text).slice(0, 4)
        .map(s => s.arg + ' text=' + s.text + ' ctrls=' + s.ctrls),
      // Every entry here was measured MID-FETCH by the run. They are not findings.
      measuredMidFetch: moved
    };
  };

  SCT.report = function () {
    const r = SCT.rows;
    return {
      navFn: NAV_FN,
      visibility: document.visibilityState,      // 'hidden' invalidates the run
      running: SCT.running,
      driven: r.length, navControls: SCT.controls.length,
      F1_nav_dead: r.filter(x => !x.vis).map(x => x.arg + (x.exists ? ' [exists,hidden]' : ' [NO ELEMENT]')),
      F2_blank: r.filter(x => x.vis && x.chars < 40).map(x => x.arg + ' chars=' + x.chars + ' ctrls=' + x.ctrls),
      F3_threw: r.filter(x => x.threw || x.errs.length).map(x => ({ id: x.arg, threw: x.threw, errs: x.errs.slice(0, 3) })),
      F4_handler_gone: r.filter(x => x.missing.length).map(x => x.arg + ': ' + x.missing.join(',')),
      totalErrors: SCT.errors.length
    };
  };
  return 'started: ' + SCT.controls.length + ' ' + NAV_FN + '() controls, visibility=' + document.visibilityState;
})()
