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
 * ── THE FOREGROUND RULE IS RETIRED (2026-09-25) -- READ THIS FIRST ───────
 * Step 2 below and the section under it describe the OLD contract and are kept
 * because they are the record of why the driver looked the way it did. The
 * throttling they describe is real and was re-measured on 2026-09-25 (a 50 ms
 * timer taking 517 ms in an unfocused tab). What changed is that the driver no
 * longer RACES it: every wait is quiescence-polled rather than a fixed 320 ms,
 * so a clamped tab lengthens the sweep and cannot manufacture a blank panel.
 * Keep the tab foreground if you can -- it is faster -- but a hidden run is
 * now usable, and `timerClampMs` in the report says which kind you got.
 *
 * ── THE TAB MUST STAY FOREGROUND, AND HERE IS WHY (HISTORICAL) ───────────
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
 *      SUPERSEDED 2026-09-25 -- THE FIXED WAIT IS GONE ENTIRELY. Lessons 4 and
 *      the foreground rule above were both symptoms of one defect: a CONSTANT
 *      racing a render. Waits are quiescence-polled now (sample until the
 *      panel's chars/ctrls are identical three reads running, ceiling 6s), so
 *      a throttled tab makes the sweep SLOWER rather than WRONG, and the tab
 *      no longer has to be babysat. A panel that never goes quiet lands in
 *      COULD_NOT_SETTLE and is excluded from the blank finding: "still
 *      rendering when I gave up" and "renders nothing" are different facts.
 *      The measured clamp is reported as timerClampMs on every run.
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

  // ── THE FIXED WAIT IS GONE. IT WAS A GUESS RACING A RENDER (2026-09-25) ──
  // 320ms was tuned on a FOREGROUND tab. Chrome clamps setTimeout in a hidden
  // or unfocused tab to roughly one per second, and the render hooks this is
  // waiting for are THEMSELVES setTimeout(0) -- so in a throttled tab the wait
  // and the thing it waits for are clamped together and the wait loses. That
  // produced 67 uniform, plausible, entirely false blank-panel findings on the
  // driver's first run, and it is why the tab had to be babysat in the
  // foreground ever since.
  //
  // A FIXED WAIT CANNOT BE RIGHT. Too short and a slow panel reads blank; too
  // long and a 67-panel sweep takes minutes for no gain -- and neither number
  // is knowable in advance, because it depends on the tab's focus state, the
  // machine, and whether the panel fetches. So do not guess: MEASURE WHEN THE
  // PANEL STOPPED CHANGING.
  //
  // QUIESCENCE, NOT A DEADLINE. Sample (chars, ctrls) repeatedly; a panel is
  // settled when the pair is IDENTICAL for QUIET_SAMPLES consecutive reads.
  // A throttled tab then simply takes longer -- it cannot produce a false
  // blank, because a blank that is still changing is not yet quiet.
  //
  // AND THE CEILING IS A THIRD STATE, NOT A VERDICT. If a panel never goes
  // quiet within SETTLE_CEILING_MS the row is marked `settled:false` and is
  // EXCLUDED from the blank finding rather than counted as blank -- "still
  // rendering when I gave up" and "renders nothing" are different facts, and
  // folding one into the other is how this detector lied the first time.
  // ── POLLING WAS NOT ENOUGH, AND RUNNING IT SAID SO (2026-09-25) ────────
  // The first version of this fix replaced the fixed 320ms wait with a
  // setTimeout POLL: sample until the panel's chars/ctrls repeat, ceiling 6s.
  // Correct in principle and useless in practice, MEASURED on SAIRNbiz with
  // the tab hidden: `settleMs` came back at 51,996 for a 6,000 ceiling.
  //
  // WHY, AND IT IS THE SAME DEFECT ONE LEVEL UP: the ceiling is only CHECKED
  // when a poll fires, and the poll is itself a setTimeout. Chrome clamps
  // chained timers in a hidden tab progressively -- measured 668ms here early
  // on and far worse after a few minutes -- so a 6s ceiling enforced by a
  // clamped timer is not a 6s ceiling. I had replaced a constant that raced a
  // render with a ceiling that raced the same clock.
  //
  // MutationObserver IS THE PRIMITIVE THAT IS NOT THROTTLED. It fires on DOM
  // mutation regardless of visibility, so the panel itself tells us when it
  // changed instead of us asking on a clock we do not control. ONE clamped
  // timer is still needed for "nothing has happened for a while" -- there is
  // no unthrottled way to observe an absence -- but one is affordable where
  // three-plus polls were not, and a wall-clock ceiling is enforced on the
  // mutation callback too so a panel that never stops mutating still ends.
  const QUIET_MS = 250;           // requested; clamped, and that is fine
  const SETTLE_CEILING_MS = 8000; // wall-clock, checked on every mutation

  function whenQuiet(arg, done) {
    const t0 = Date.now();
    const el = resolve(arg);
    if (!el) return done({ settled: true, ms: 0 });
    let timer = null, obs = null, finished = false;
    const finish = (settled) => {
      if (finished) return;
      finished = true;
      if (timer) clearTimeout(timer);
      if (obs) obs.disconnect();
      done({ settled: settled, ms: Date.now() - t0 });
    };
    const arm = () => { if (timer) clearTimeout(timer); timer = setTimeout(() => finish(true), QUIET_MS); };
    try {
      obs = new MutationObserver(() => {
        // THE CEILING LIVES HERE, not only on the timer: a panel mutating
        // forever (a clock, a poller) would otherwise re-arm the quiet timer
        // for ever and this control would never return.
        if (Date.now() - t0 >= SETTLE_CEILING_MS) return finish(false);
        arm();
      });
      obs.observe(el, { childList: true, subtree: true, characterData: true, attributes: true });
    } catch (e) { return done({ settled: true, ms: Date.now() - t0 }); }
    arm();
  }

  (function tick() {
    if (SCT.i >= SCT.controls.length) { SCT.running = false; return; }
    const { el, arg } = SCT.controls[SCT.i];
    const label = (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 30);
    const before = SCT.errors.length;
    let threw = null;
    try { el.click(); } catch (e) { threw = String((e && e.message) || e); }
    whenQuiet(arg, (q) => {
      record(arg, label, before, threw);
      const row = SCT.rows[SCT.rows.length - 1];
      if (row) { row.settled = q.settled; row.settleMs = q.ms; }
      SCT.i++;
      setTimeout(tick, 15);
    });
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
    // ── THE TIMER CLAMP IS MEASURED AND REPORTED, NOT INFERRED FROM FOCUS ──
    // `visibilityState` was recorded so a throttled run could be thrown away.
    // With quiescence polling a throttled run is SURVIVABLE, so what a reader
    // needs is not the flag but the FACT: how much slower timers actually ran.
    // SCT.clampMs is measured once at start-up; well above the requested 50ms
    // means the tab was throttled and the sweep simply took longer.
    const unsettled = r.filter(x => x.settled === false).map(x => x.arg + ' gave-up-after=' + x.settleMs + 'ms');
    return {
      navFn: NAV_FN,
      visibility: document.visibilityState,
      hasFocus: (typeof document.hasFocus === 'function') ? document.hasFocus() : null,
      timerClampMs: SCT.clampMs,                 // requested 50; >400 means throttled
      running: SCT.running,
      driven: r.length, navControls: SCT.controls.length,
      // NOT A FINDING, AND KEPT OUT OF F2 DELIBERATELY: a panel that was still
      // changing when the ceiling hit is "I gave up watching", not "it renders
      // nothing". Folding the two is exactly how this detector lied the first
      // time it ran.
      COULD_NOT_SETTLE: unsettled,
      F1_nav_dead: r.filter(x => !x.vis).map(x => x.arg + (x.exists ? ' [exists,hidden]' : ' [NO ELEMENT]')),
      F2_blank: r.filter(x => x.vis && x.settled !== false && x.chars < 40).map(x => x.arg + ' chars=' + x.chars + ' ctrls=' + x.ctrls),
      F3_threw: r.filter(x => x.threw || x.errs.length).map(x => ({ id: x.arg, threw: x.threw, errs: x.errs.slice(0, 3) })),
      F4_handler_gone: r.filter(x => x.missing.length).map(x => x.arg + ': ' + x.missing.join(',')),
      totalErrors: SCT.errors.length
    };
  };
  // Measure the clamp once, at start-up, so every report can state it as a
  // fact rather than leaving a reader to infer it from the focus flag.
  SCT.clampMs = null;
  (function () {
    const t0 = Date.now();
    setTimeout(() => { SCT.clampMs = Date.now() - t0; }, 50);
  })();
  return 'started: ' + SCT.controls.length + ' ' + NAV_FN
       + '() controls, visibility=' + document.visibilityState
       + ' -- a hidden tab no longer invalidates the run: waits are quiescence'
       + '-polled, so throttling makes it SLOWER, not wrong. Read timerClampMs'
       + ' and COULD_NOT_SETTLE in report().';
})()
