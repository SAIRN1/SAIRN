// tests/lib/save_reentry_harness.js
//
// The shared driver for the save re-entry arms (cody b65). A save handler that
// AWAITS a server write before its visible step (toast, form clear, modal
// close) while its trigger stays live creates a second record when it is
// pressed again during that wait. Every arm here drives the REAL handler,
// lifted from the shipped file by brace matching and run in a vm with stubs.
//
//   <id>1  two presses while the write is pending: ONE write (and, where the
//          handler stores locally, one row), and the second press is told why.
//   <id>2  once the write answers, the next press goes through.
//   <id>3  after a REFUSED write, a REJECTED write and a write that THROWS
//          synchronously, the next press is not held.
//
// A caller supplies mk(push) -> { press, refill, writes, toasts, rows? } and
// keeps its own `finished` flag: a run that ends with an arm still waiting
// must exit 2, and only the caller knows when its last arm has run.

'use strict';
const vm = require('vm');

const flush = () => new Promise((r) => setImmediate(r));
const settle = async () => { for (let i = 0; i < 4; i++) await flush(); };

// A .then()-style handler (no async) leaves a rejected chain nobody awaits;
// node would end the run on it. Recorded, never fatal: the arms measure the
// hold, and the real write helpers these stand in for never reject.
const unhandled = [];
process.on('unhandledRejection', (e) => { unhandled.push(e); });

function makeLift(html, FILE) {
  return function lift(head) {
    const i = html.indexOf(head);
    if (i < 0 || html.indexOf(head, i + 1) !== -1) {
      console.log('COULD NOT RUN: "' + head + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
      process.exit(2);
    }
    let k = html.indexOf('{', i), depth = 0;
    for (; k < html.length; k++) {
      if (html[k] === '{') depth++;
      else if (html[k] === '}' && --depth === 0) return html.slice(i, k + 1) + ';';
    }
    console.log('COULD NOT RUN: unbalanced ' + head); process.exit(2);
  };
}

// A hold's declaration, lifted if the file has it, so the pre-fix file runs
// unchanged and arm 1 measures the fix.
function optional(html, re) { return (html.match(re) || [''])[0]; }

const NOT_STUBBED = new Set(['if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'typeof']);

// Run `src` in a fresh context. `given` holds the stubs the handler's logic
// depends on; every OTHER free call in src becomes a no-op, so render and
// refresh calls need no hand-written stub. A free call to a hold helper the
// file declares nowhere becomes a no-op too -- and then arm 1 FAILS, it does
// not pass.
function vmWorld(src, given) {
  const ctx = Object.assign({
    JSON, Object, Array, Number, String, Boolean, Promise, Date, Math, Error, RegExp,
    parseFloat, parseInt, isNaN, isFinite, encodeURIComponent,
    setTimeout: () => 0, clearTimeout() {},
    console: { log() {}, warn() {}, error() {} }
  }, given);
  ctx.window = ctx;
  const declared = new Set([...src.matchAll(/function\s+([A-Za-z_$][\w$]*)/g)].map((m) => m[1]));
  for (const m of src.matchAll(/(^|[^.\w$])([A-Za-z_$][\w$]*)\s*\(/g)) {
    const id = m[2];
    if (id in ctx || declared.has(id) || NOT_STUBBED.has(id)) continue;
    ctx[id] = () => {};
  }
  vm.createContext(ctx); vm.runInContext(src, ctx);
  return ctx;
}

// The usual world: a DOM of plain objects keyed by id, toast/showToast
// captured, and the spec's own stubs. spec: src, fields (re-filled before
// every press), given(write, box) -> stubs, press(ctx), refill(ctx)?, rows(box)?
// `write` counts and forwards to the arm's push. What the handler "said" is
// every toast plus every element's textContent, since some forms report in an
// inline error line rather than a toast.
function mkFor(spec) {
  return (push) => {
    let writes = 0;
    const toasts = [];
    const els = {};
    const box = { rows: [] };
    const el = (id) => (els[id] = els[id] || { id, value: '', textContent: '', innerHTML: '', style: {}, checked: false });
    const write = function () { writes++; return push.apply(null, arguments); };
    const say = (m) => { toasts.push(String(m)); };
    const ctx = vmWorld(spec.src, Object.assign({
      $: el, document: { getElementById: el, querySelector: () => el('(selector)'), querySelectorAll: () => [] },
      toast: say, showToast: say
    }, spec.given(write, box)));
    return {
      ctx,
      press: () => spec.press(ctx),
      refill: () => { for (const [k, v] of Object.entries(spec.fields || {})) el(k).value = v; if (spec.refill) spec.refill(ctx, box); },
      writes: () => writes,
      toasts: () => toasts.concat(Object.values(els).map((e) => String(e.textContent || '')).filter(Boolean)),
      rows: spec.rows ? () => spec.rows(box) : undefined
    };
  };
}

// A press that throws synchronously is a rejected press, not a crashed run.
const pressOf = (w) => { try { return Promise.resolve(w.press()); } catch (e) { return Promise.reject(e); } };

async function drive(o) {
  const { check, id, name, mk } = o;
  const still = o.still || /Still /;
  const said = (w) => w.toasts().some((t) => still.test(t));
  const state = (w) => JSON.stringify({ writes: w.writes(), rows: w.rows ? w.rows() : undefined, toasts: w.toasts() });
  {
    // EVERY pending write is settled below -- an unsettled one would end the
    // run with the caller waiting, and node exits 0 on that.
    const held = [];
    let holding = true;
    const w = mk(() => (holding ? new Promise((r) => held.push(r)) : Promise.resolve(o.ok)));
    w.refill(); const first = pressOf(w); await flush();
    w.refill(); const second = pressOf(w); await flush();
    check(id + '1 ' + name + ': a second press while the write is pending makes NO second record, and says so',
      w.writes() === 1 && (!w.rows || w.rows() === 1) && said(w), state(w));
    holding = false;
    held.forEach((r) => r(o.ok));
    await Promise.allSettled([first, second]); await settle();
    const before = w.writes();
    w.refill(); await pressOf(w).catch(() => {}); await settle();
    check(id + '2 ' + name + ': once the write answers, the next press goes through',
      w.writes() === before + 1, JSON.stringify({ before }) + ' ' + state(w));
  }
  for (const [label, push] of [
    ['a REFUSED write', () => Promise.resolve(o.refused)],
    ['a REJECTED write', () => Promise.reject(new Error('offline'))],
    ['a write that THROWS', () => { throw new Error('offline'); }]
  ]) {
    const w = mk(push);
    w.refill(); await pressOf(w).catch(() => {}); await settle();
    w.refill(); await pressOf(w).catch(() => {}); await settle();
    check(id + '3 ' + name + ': after ' + label + ' the next press is not held',
      w.writes() === 2 && !said(w), state(w));
  }
}

module.exports = { makeLift, optional, vmWorld, mkFor, drive, flush, settle, unhandled };
