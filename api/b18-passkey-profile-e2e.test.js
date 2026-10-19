// api/b18-passkey-profile-e2e.test.js
//
// Run:  node api/b18-passkey-profile-e2e.test.js
//
// END TO END over the three client functions of StoneDesk's employee panel --
// Grant App Login Access, Register a Passkey, and the Employee Profile
// read/write -- including the failure paths that used to leave a pending label
// stuck or a failed read looking like an empty one.
//
// ── WHY THIS SUITE EXISTS, AND IT IS NOT "COVERAGE" ──────────────────────
// The 2026-08-06 "Granting..." bug is recorded in stonedesk.html's own comment
// and the sentence that matters is this one: the reset code was "confirmed
// present and correct on every path, CHECKED REPEATEDLY" -- and never ran,
// because a synchronous ReferenceError happened before it. READING THE CODE
// WAS THE METHOD AND THE METHOD FAILED. Nothing drives these functions, so the
// same class could not be found by the same means twice.
//
// THREE RESIDUALS OF THAT CLASS WERE FOUND IN b18 BY READING, AND ARE FIXED;
// THIS FILE IS WHAT MAKES THEM STAY FIXED:
//   1. sdRenderEmployeeProfiles drew "No profiles set yet." for a FAILED read.
//   2. Neither profile function had a `.catch`, so a throw in the handler left
//      "Loading..." standing, or a save failing in total silence.
//   3. sdGrantLoginAccess called showToast/escHtml unguarded AFTER a confirmed
//      server success, so a throw from either reported a CREATED credential as
//      "Network error -- check your connection".
//
// ── THE FUNCTIONS ARE LIFTED FROM stonedesk.html AND RUN, NOT REWRITTEN ──
// A reimplementation passes against the unfixed page, which is the whole
// lesson of api/b15-client-effective-clock.test.js and the reason that file
// says so in its own header.
//
// ── THE LIFT IS STRUCTURE-BOUNDED AND FAILS CLOSED ──────────────────────
// NOT a fixed-width window. b16's open item 1 is thirty-one of those still
// tolerated across this repo, and the failure they produce is the one recorded
// on 2026-10-07: a window that stops inside a structure gives a wrong answer
// with no warning. Here the end of a function is found by INDENTATION --
// the first line at the anchor's own indent whose content is `}` or `};` --
// and then the lifted text is COMPILED. A bad lift does not parse, so it
// reports UNPROVEN and never a pass.
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
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }
function section(t) { console.log('\n' + t); }

// ── AN UNHANDLED REJECTION IS A RESULT HERE, NOT A CRASH ──────────────────
// Section E removes the `.catch` from the lifted render and then makes the
// handler throw. WITHOUT a catch that becomes an unhandled rejection -- which
// Node turns into a process exit, and which a BROWSER turns into a console
// error nobody is looking at while the panel sits there saying "Loading...".
// That is precisely the defect, so it is COUNTED rather than allowed to kill
// the suite. Installed here and not inside section E because an unhandled
// rejection can surface a tick later than the code that caused it.
const unhandled = [];
process.on('unhandledRejection', function (e) { unhandled.push(e); });

const HTML = (function () {
  try { return fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8'); }
  catch (e) { return null; }
})();

// ── THE LIFT ────────────────────────────────────────────────────────────────
// `anchor` is the exact first line of the declaration. The end is the first
// subsequent line at the SAME indentation whose trimmed content is `}` or
// `};` -- which is this file's convention throughout and is verified by the
// compile below rather than trusted.
function lift(anchor) {
  if (HTML === null) return { missing: 'stonedesk.html could not be read' };
  const lines = HTML.split('\n');
  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].indexOf(anchor) !== -1) { start = i; break; }
  }
  if (start === -1) return { missing: 'anchor not found: ' + anchor };
  const indent = lines[start].length - lines[start].replace(/^\s*/, '').length;
  for (let j = start + 1; j < lines.length; j++) {
    const t = lines[j].trim();
    const ind = lines[j].length - lines[j].replace(/^\s*/, '').length;
    if ((t === '}' || t === '};') && ind === indent) {
      return { src: lines.slice(start, j + 1).join('\n'), from: start + 1, to: j + 1 };
    }
  }
  return { missing: 'no closing line at indent ' + indent + ' after: ' + anchor };
}

const ANCHORS = {
  grant: '  window.sdGrantLoginAccess=function(){',
  saveProfile: '  window.sdSaveEmployeeProfile=function(){',
  renderProfiles: '  function sdRenderEmployeeProfiles(){',
  passkey: 'window.sdRegisterPasskey = function() {',
  readFailedNote: 'function sdReadFailedNote(what) {',
  authRefusedNote: 'function sdAuthRefusedNote(what) {'
};

// ── THE REALM ───────────────────────────────────────────────────────────────
// A DOM small enough to read and honest about what it is. Elements are plain
// objects, so `innerHTML` and `textContent` are inspectable AFTER the call --
// which is the whole point: the arms assert what the panel SAYS, not what the
// function returned.
// ── innerHTML AND textContent ARE LINKED, AS THEY ARE IN A REAL ELEMENT ───
// Setting one REPLACES the other's content. A plain object with two
// independent string properties does not behave that way, and the difference
// is not cosmetic: `listEl.textContent='Loading...'` followed by
// `listEl.innerHTML=<the note>` leaves the stale 'Loading...' standing in
// `textContent` forever, so an arm asserting "the pending label is gone" FAILS
// ON CORRECT CODE. That is exactly what happened on the first run of B5/B6
// here, and the stub was wrong rather than the page. A harness that models the
// platform badly produces findings about the harness.
function makeEl(id) {
  let content = '';
  const el = { id: id, value: '', disabled: false, style: {},
               scrollIntoView: function () {} };
  Object.defineProperty(el, 'innerHTML', {
    get: function () { return content; },
    set: function (v) { content = String(v == null ? '' : v); },
    enumerable: true
  });
  Object.defineProperty(el, 'textContent', {
    // A real element's textContent is its markup with tags stripped. Stripping
    // is enough for these arms and is strictly closer than returning markup.
    get: function () { return content.replace(/<[^>]*>/g, ''); },
    set: function (v) { content = String(v == null ? '' : v); },
    enumerable: true
  });
  return el;
}
function realm(opts) {
  opts = opts || {};
  const els = {};
  [ 'emp-login-id', 'emp-login-name', 'emp-login-role', 'emp-login-pin',
    'emp-login-error', 'emp-login-success', 'emp-login-submit-btn',
    'emp-prof-id', 'emp-prof-exp', 'emp-prof-style', 'emp-prof-notes',
    'emp-prof-error', 'emp-prof-list',
    'emp-passkey-register-btn', 'emp-passkey-error', 'emp-passkey-unsupported'
  ].forEach(function (id) { els[id] = makeEl(id); });
  (opts.absent || []).forEach(function (id) { delete els[id]; });

  const toasts = [];
  const warns = [];
  const store = { sd_session_token: 'tok', sd_session_role: 'owner',
                  sd_session_employee_id: 'emp-1' };
  const fetches = [];

  const sandbox = {
    console: {
      log: function () {}, error: function () {},
      warn: function () { warns.push(Array.prototype.slice.call(arguments)); }
    },
    JSON: JSON, String: String, Number: Number, Array: Array, Object: Object,
    Math: Math, Date: Date, Promise: Promise, Error: Error, RegExp: RegExp,
    Uint8Array: Uint8Array, isFinite: isFinite, encodeURIComponent: encodeURIComponent,
    atob: function (s) { return Buffer.from(String(s), 'base64').toString('binary'); },
    btoa: function (s) { return Buffer.from(String(s), 'binary').toString('base64'); },
    setTimeout: setTimeout, clearTimeout: clearTimeout,
    document: {
      getElementById: function (id) { return els[id] || null; },
      addEventListener: function () {},
      readyState: 'complete'
    },
    sessionStorage: {
      getItem: function (k) {
        if (opts.sessionThrows) throw new Error('sessionStorage blocked');
        return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null;
      },
      setItem: function (k, v) { store[k] = String(v); }
    },
    // ── THE STUBS THAT CAN BE MADE TO THROW ─────────────────────────────
    // This is how residual 3 is driven: a `showToast` that throws AFTER a
    // confirmed success must not turn the success into an error message.
    showToast: function (m) {
      if (opts.toastThrows) throw new Error('showToast exploded');
      toasts.push(m);
    },
    escHtml: function (s) {
      if (opts.escThrows) throw new Error('escHtml exploded');
      return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
    },
    escAttrJs: function (s) {
      if (opts.escAttrThrows) throw new Error('escAttrJs exploded');
      return String(s == null ? '' : s).replace(/'/g, "\\'");
    },
    sdLicenseKey: function () {
      if (opts.licThrows) throw new Error('sdLicenseKey exploded');
      return opts.noLicence ? '' : 'SD-TEST-2026';
    },
    // `sdData` NEVER REJECTS in the real app -- its own catch is guarded for
    // that reason -- so the default here resolves. `opts.sdDataRejects` is the
    // case the real transport can still produce, because `sdLicenseKey()` is
    // called OUTSIDE sdData's try (stonedesk.html:30205).
    sdData: function (action) {
      fetches.push({ via: 'sdData', action: action });
      if (opts.sdDataRejects) return Promise.reject(new Error('transport threw'));
      if (action === 'read') return Promise.resolve(opts.readRows === undefined ? [] : opts.readRows);
      return Promise.resolve(opts.writeResult === undefined ? { ok: true } : opts.writeResult);
    },
    sdAuthWasRefused: function () { return !!opts.authRefused; },
    sdReadFailed: function () { return !!opts.readFailed; },
    fetch: function (url, init) {
      fetches.push({ url: String(url), method: (init && init.method) || 'GET' });
      if (opts.fetchRejects) return Promise.reject(new Error('network down'));
      const answer = opts.httpAnswers ? opts.httpAnswers.shift() : null;
      const a = answer || { ok: true, body: { ok: true } };
      return Promise.resolve({
        ok: a.ok,
        json: function () {
          return a.badJson ? Promise.reject(new Error('not json'))
                           : Promise.resolve(a.body);
        }
      });
    },
    SD_AUTH_API: 'https://sairn.vercel.app/api/sd-auth',
    SD_WEBAUTHN_API: 'https://sairn.vercel.app/api/sd-webauthn',
    PASSKEY_SUPPORTED: opts.passkeyUnsupported ? false : true,
    navigator: {
      credentials: {
        create: function () {
          if (opts.credentialsThrows) {
            const e = new Error('Cancelled or not completed');
            e.name = opts.credentialsErrName || 'NotAllowedError';
            return Promise.reject(e);
          }
          return Promise.resolve({
            id: 'cred-1', rawId: new Uint8Array([1, 2, 3]).buffer, type: 'public-key',
            response: {
              clientDataJSON: new Uint8Array([4, 5]).buffer,
              attestationObject: new Uint8Array([6, 7]).buffer,
              getTransports: function () { return ['internal']; }
            },
            getClientExtensionResults: function () { return {}; }
          });
        }
      }
    }
  };
  sandbox.window = sandbox;
  // The two b64url helpers and the serialiser live inside the passkey IIFE as
  // plain declarations; they are provided here rather than lifted, because
  // they are pure encoders and NOT what this suite is about. Stated so nobody
  // reads these arms as covering them -- api/sd-webauthn.js's own suite does.
  sandbox.b64urlToBuf = function (s) {
    const bin = sandbox.atob(String(s).replace(/-/g, '+').replace(/_/g, '/'));
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    return buf.buffer;
  };
  sandbox.bufToB64url = function (buf) {
    const b = new Uint8Array(buf); let s = '';
    for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return sandbox.btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  };
  sandbox.serializeCredentialForRegistration = function (c) {
    return { id: c.id, rawId: sandbox.bufToB64url(c.rawId), type: c.type,
             response: { clientDataJSON: sandbox.bufToB64url(c.response.clientDataJSON),
                         attestationObject: sandbox.bufToB64url(c.response.attestationObject),
                         transports: c.response.getTransports() },
             clientExtensionResults: c.getClientExtensionResults() };
  };

  vm.createContext(sandbox);
  return { sandbox: sandbox, els: els, toasts: toasts, warns: warns,
           fetches: fetches, store: store };
}

// Install a set of lifted functions into a realm. Returns an error object if a
// lift is missing or will not compile -- which is reported UNPROVEN, never as
// a pass.
function install(r, names) {
  const src = [];
  for (const n of names) {
    const l = lift(ANCHORS[n]);
    if (l.missing) return { missing: n + ': ' + l.missing };
    src.push(l.src);
  }
  const text = src.join('\n');
  try { new vm.Script(text); }
  catch (e) {
    return { missing: 'the lifted text does not COMPILE, so the extraction is '
                    + 'wrong rather than the code: ' + e.message };
  }
  try { vm.runInContext(text, r.sandbox); }
  catch (e) { return { missing: 'the lifted text would not run: ' + e.message }; }
  return { ok: true };
}

function tick() { return new Promise(function (res) { setTimeout(res, 0); }); }

// ═══════════════════════════════════════════════════════════════════════════
(async function () {
  console.log('b18 Passkey / Employee Profile E2E -- the "Granting..." class, '
            + 'driven\n');

  if (HTML === null) {
    cannot('the whole suite. stonedesk.html could not be read',
           'nothing below ran -- this is NOT a clean result');
    console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
    process.exit(3);
  }

  // ── Z. THE LIFTS THEMSELVES, FIRST ─────────────────────────────────────
  section('Z. the extraction -- every arm below depends on these');
  let anyLiftFailed = false;
  Object.keys(ANCHORS).forEach(function (n) {
    const l = lift(ANCHORS[n]);
    if (l.missing) {
      anyLiftFailed = true;
      cannot('Z.' + n + '. could not be lifted from stonedesk.html', l.missing);
    } else {
      ok('Z.' + n + '. lifted, lines ' + l.from + '-' + l.to + ' ('
         + l.src.split('\n').length + ' lines)');
    }
  });
  if (anyLiftFailed) {
    console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
    console.log('  UNPROVEN: ' + notProved.join(', '));
    process.exit(3);
  }

  // ── A. GRANT APP LOGIN ACCESS -- THE HAPPY PATH AND THE LABEL ──────────
  section('A. Grant App Login Access');

  {
    const r = realm({});
    const e = install(r, ['grant']);
    if (e.missing) { cannot('A1-A6. the grant function would not install', e.missing); }
    else {
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-name'].value = 'J Smith';
      r.els['emp-login-role'].value = 'install';
      r.els['emp-login-pin'].value = '123456';
      r.sandbox.window.sdGrantLoginAccess();
      is(r.els['emp-login-submit-btn'].textContent === 'Granting...'
         && r.els['emp-login-submit-btn'].disabled === true,
         'A1. the button enters the pending state SYNCHRONOUSLY -- this is the '
       + 'state the 2026-08-06 bug could not leave',
         JSON.stringify({ t: r.els['emp-login-submit-btn'].textContent,
                          d: r.els['emp-login-submit-btn'].disabled }));
      await tick(); await tick(); await tick();
      is(r.els['emp-login-submit-btn'].textContent === 'Grant Access'
         && r.els['emp-login-submit-btn'].disabled === false,
         'A2. ...and it LEAVES it on success',
         JSON.stringify({ t: r.els['emp-login-submit-btn'].textContent,
                          d: r.els['emp-login-submit-btn'].disabled }));
      is(r.els['emp-login-success'].style.display === 'block'
         && /Access granted/.test(r.els['emp-login-success'].innerHTML)
         && /jsmith/.test(r.els['emp-login-success'].innerHTML),
         'A3. the PERSISTENT inline confirmation is shown and names the person '
       + '-- the thing Michael reported needing because a 3-second fading '
       + 'toast is easy to miss',
         r.els['emp-login-success'].innerHTML);
      is(r.els['emp-login-id'].value === '' && r.els['emp-login-pin'].value === ''
         && r.els['emp-login-role'].value === 'install',
         'A4. and the form is cleared, PIN included -- a PIN left in a field is '
       + 'a shared credential on a shared screen',
         JSON.stringify({ id: r.els['emp-login-id'].value,
                          pin: r.els['emp-login-pin'].value }));
    }
  }

  // THE RESIDUAL THIS BATCH FIXED: a throw AFTER a confirmed server success.
  {
    const r = realm({ toastThrows: true });
    const e = install(r, ['grant']);
    if (e.missing) { cannot('A5. toast-throws path', e.missing); }
    else {
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-pin'].value = '123456';
      r.sandbox.window.sdGrantLoginAccess();
      await tick(); await tick(); await tick();
      is(r.els['emp-login-error'].style.display !== 'block'
         && r.els['emp-login-success'].style.display === 'block'
         && r.els['emp-login-submit-btn'].textContent === 'Grant Access',
         'A5. A THROW FROM showToast AFTER A CONFIRMED SUCCESS does NOT become '
       + 'an error message, the inline confirmation still appears, and the '
       + 'button resets. Before b18 this reported a CREATED credential as '
       + '"Network error -- check your connection"',
         JSON.stringify({ err: r.els['emp-login-error'].style.display,
                          errText: r.els['emp-login-error'].textContent,
                          ok: r.els['emp-login-success'].style.display }));
    }
  }
  {
    const r = realm({ escThrows: true });
    const e = install(r, ['grant']);
    if (e.missing) { cannot('A6. escHtml-throws path', e.missing); }
    else {
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-pin'].value = '123456';
      r.sandbox.window.sdGrantLoginAccess();
      await tick(); await tick(); await tick();
      is(r.els['emp-login-error'].style.display !== 'block'
         && r.els['emp-login-submit-btn'].textContent === 'Grant Access',
         'A6. ...and the same for escHtml. Both were unguarded while their '
       + 'sibling twenty lines up used `typeof`',
         JSON.stringify({ err: r.els['emp-login-error'].textContent,
                          btn: r.els['emp-login-submit-btn'].textContent }));
    }
  }
  // AND THE SILENT HALF: a REAL failure still reports one.
  {
    const r = realm({ fetchRejects: true });
    const e = install(r, ['grant']);
    if (e.missing) { cannot('A7. network-failure path', e.missing); }
    else {
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-pin'].value = '123456';
      r.sandbox.window.sdGrantLoginAccess();
      await tick(); await tick(); await tick();
      is(r.els['emp-login-error'].style.display === 'block'
         && /nothing was confirmed/.test(r.els['emp-login-error'].textContent)
         && r.els['emp-login-submit-btn'].textContent === 'Grant Access'
         && r.warns.length >= 1,
         'A7. CLEAN HALF OF THE PAIR -- a real network failure DOES report, '
       + 'resets the button, logs, and says NOTHING WAS CONFIRMED rather than '
       + 'naming a cause it cannot know',
         JSON.stringify({ shown: r.els['emp-login-error'].style.display,
                          text: r.els['emp-login-error'].textContent,
                          warns: r.warns.length }));
    }
  }
  // A server refusal is the server's message, verbatim.
  {
    const r = realm({ httpAnswers: [{ ok: false, body: { error: { message: 'That Employee ID is already in use' } } }] });
    const e = install(r, ['grant']);
    if (e.missing) { cannot('A8. server-refusal path', e.missing); }
    else {
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-pin'].value = '123456';
      r.sandbox.window.sdGrantLoginAccess();
      await tick(); await tick(); await tick();
      is(r.els['emp-login-error'].textContent === 'That Employee ID is already in use'
         && r.els['emp-login-submit-btn'].disabled === false,
         'A8. a server refusal shows the SERVER\'s message verbatim and still '
       + 'releases the button',
         r.els['emp-login-error'].textContent);
    }
  }
  // THE PENDING LABEL IS NEVER ENTERED ON A CLIENT-SIDE REFUSAL. The guards
  // return before it, which is why those paths were never the bug -- asserted
  // so a future edit cannot move the pending line above them.
  {
    const r = realm({});
    const e = install(r, ['grant']);
    if (e.missing) { cannot('A9. early-return paths', e.missing); }
    else {
      r.els['emp-login-id'].value = '';
      r.sandbox.window.sdGrantLoginAccess();
      const noId = r.els['emp-login-submit-btn'].textContent;
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-pin'].value = '12';
      r.sandbox.window.sdGrantLoginAccess();
      const badPin = r.els['emp-login-submit-btn'].textContent;
      is(noId === '' && badPin === ''
         && /6-8 digits/.test(r.els['emp-login-error'].textContent),
         'A9. a missing ID or a short PIN never enters the pending state at '
       + 'all -- the guards return above it, and this arm is what stops a '
       + 'future edit moving the pending line up',
         JSON.stringify({ noId: noId, badPin: badPin }));
    }
  }
  // AND THE MISSING BUTTON, which was an unguarded dereference before b18.
  {
    const r = realm({ absent: ['emp-login-submit-btn'] });
    const e = install(r, ['grant']);
    if (e.missing) { cannot('A10. absent-button path', e.missing); }
    else {
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-pin'].value = '123456';
      let threw = null;
      try { r.sandbox.window.sdGrantLoginAccess(); } catch (ex) { threw = ex; }
      await tick(); await tick(); await tick();
      is(threw === null && r.els['emp-login-success'].style.display === 'block',
         'A10. with the BUTTON ABSENT the grant still completes and still '
       + 'confirms. Before b18 `btn.textContent` was dereferenced unguarded '
       + 'while everything around it was `if(btn)`',
         threw ? String(threw.message) : 'no throw');
    }
  }

  // ── B. EMPLOYEE PROFILE -- THE FALSE EMPTY AND THE STUCK LABEL ─────────
  section('B. Employee Profile -- empty, refused and unfetched are three '
        + 'different facts');

  const PROF_CASES = [
    ['B1', { readRows: [] }, /No profiles set yet/,
      'genuinely empty says "none yet"'],
    ['B2', { readRows: null, readFailed: true }, /did not come back/,
      'a FAILED read says the request did not come back -- NOT "none yet". '
    + 'This is the defect: empty and unfetched rendered identically'],
    ['B3', { readRows: null, authRefused: true }, /Sign in to see/,
      'a REFUSED read says sign in -- a third fact again, and it must not read '
    + 'as an absence either'],
    ['B4', { readRows: [{ employee_id: 'emp-1', experience_level: 'veteran',
                          communication_style: 'terse' }] }, /emp-1/,
      'a real row renders']
  ];
  for (const c of PROF_CASES) {
    const r = realm(c[1]);
    const e = install(r, ['renderProfiles', 'readFailedNote', 'authRefusedNote']);
    if (e.missing) { cannot(c[0] + '. ' + c[3], e.missing); continue; }
    r.sandbox.sdRenderEmployeeProfiles();
    await tick(); await tick();
    const html = r.els['emp-prof-list'].innerHTML;
    is(c[2].test(html) && !/Loading/.test(html),
       c[0] + '. ' + c[3],
       'rendered: ' + String(html).slice(0, 180));
  }

  // THE STUCK LABEL, DRIVEN. A throw inside the render handler must clear
  // "Loading...", which is the 2026-08-06 class one layer over.
  {
    const r = realm({ readRows: [{ employee_id: 'emp-1', experience_level: 'new',
                                   communication_style: 'terse' }],
                      escAttrThrows: true });
    const e = install(r, ['renderProfiles', 'readFailedNote', 'authRefusedNote']);
    if (e.missing) { cannot('B5. render-throws path', e.missing); }
    else {
      r.sandbox.sdRenderEmployeeProfiles();
      await tick(); await tick();
      const html = r.els['emp-prof-list'].innerHTML;
      const text = r.els['emp-prof-list'].textContent;
      is(!/Loading/.test(html) && !/Loading/.test(text)
         && /did not come back/.test(html) && r.warns.length >= 1,
         'B5. A THROW INSIDE THE RENDER clears the pending label and says so, '
       + 'with a console line. Before b18 there was no `.catch` and the panel '
       + 'read "Loading..." forever -- a pending state entered before a path '
       + 'that could fail without clearing it, which is the bug this suite is '
       + 'named after',
         JSON.stringify({ html: String(html).slice(0, 120), text: text,
                          warns: r.warns.length }));
    }
  }
  // AND A REJECTING TRANSPORT, which `sdLicenseKey` throwing really can
  // produce -- that call is OUTSIDE sdData's own try.
  {
    const r = realm({ sdDataRejects: true });
    const e = install(r, ['renderProfiles', 'readFailedNote', 'authRefusedNote']);
    if (e.missing) { cannot('B6. rejecting-transport path', e.missing); }
    else {
      r.sandbox.sdRenderEmployeeProfiles();
      await tick(); await tick();
      is(!/Loading/.test(r.els['emp-prof-list'].innerHTML)
         && !/Loading/.test(r.els['emp-prof-list'].textContent),
         'B6. a REJECTING sdData also clears the label. sdData is written '
       + 'never to reject, and `sdLicenseKey()` at :30205 is called outside '
       + 'its try -- which that line\'s own comment records as the shape this '
       + 'file already paid for once',
         r.els['emp-prof-list'].textContent + ' / '
         + String(r.els['emp-prof-list'].innerHTML).slice(0, 120));
    }
  }

  // ── C. SAVING A PROFILE ────────────────────────────────────────────────
  section('C. saving a profile -- a failed save is never silent');

  {
    const r = realm({ writeResult: { ok: true } });
    const e = install(r, ['saveProfile', 'renderProfiles', 'readFailedNote', 'authRefusedNote']);
    if (e.missing) { cannot('C1-C2. the save function would not install', e.missing); }
    else {
      r.els['emp-prof-id'].value = 'emp-7';
      r.els['emp-prof-exp'].value = 'veteran';
      r.els['emp-prof-style'].value = 'terse';
      r.sandbox.window.sdSaveEmployeeProfile();
      await tick(); await tick();
      is(r.els['emp-prof-error'].style.display !== 'block'
         && r.els['emp-prof-id'].value === ''
         && r.toasts.some(function (t) { return /emp-7/.test(String(t)); }),
         'C1. a successful save clears the form and toasts the employee id',
         JSON.stringify({ err: r.els['emp-prof-error'].style.display,
                          id: r.els['emp-prof-id'].value, toasts: r.toasts }));
    }
  }
  {
    const r = realm({ writeResult: null });
    const e = install(r, ['saveProfile', 'renderProfiles', 'readFailedNote', 'authRefusedNote']);
    if (e.missing) { cannot('C2. null-result path', e.missing); }
    else {
      r.els['emp-prof-id'].value = 'emp-7';
      r.sandbox.window.sdSaveEmployeeProfile();
      await tick(); await tick();
      is(r.els['emp-prof-error'].style.display === 'block'
         && /Save failed/.test(r.els['emp-prof-error'].textContent),
         'C2. sdData returning NULL -- which is every server failure -- is '
       + 'reported',
         r.els['emp-prof-error'].textContent);
    }
  }
  {
    const r = realm({ sdDataRejects: true });
    const e = install(r, ['saveProfile', 'renderProfiles', 'readFailedNote', 'authRefusedNote']);
    if (e.missing) { cannot('C3. rejecting-save path', e.missing); }
    else {
      r.els['emp-prof-id'].value = 'emp-7';
      r.sandbox.window.sdSaveEmployeeProfile();
      await tick(); await tick();
      is(r.els['emp-prof-error'].style.display === 'block'
         && /nothing was confirmed/.test(r.els['emp-prof-error'].textContent)
         && r.warns.length >= 1,
         'C3. A REJECTING SAVE IS NO LONGER SILENT. `emp-prof-error` is hidden '
       + 'on the line above the call, so before b18 a throw here left the form '
       + 'looking exactly as it does before a click -- indistinguishable from '
       + 'not having clicked',
         JSON.stringify({ shown: r.els['emp-prof-error'].style.display,
                          text: r.els['emp-prof-error'].textContent,
                          warns: r.warns.length }));
    }
  }
  {
    const r = realm({});
    const e = install(r, ['saveProfile', 'renderProfiles', 'readFailedNote', 'authRefusedNote']);
    if (e.missing) { cannot('C4. missing-id path', e.missing); }
    else {
      r.els['emp-prof-id'].value = '   ';
      r.sandbox.window.sdSaveEmployeeProfile();
      await tick();
      is(r.els['emp-prof-error'].style.display === 'block'
         && /Enter an Employee ID/.test(r.els['emp-prof-error'].textContent)
         && !r.fetches.some(function (f) { return f.via === 'sdData'; }),
         'C4. a blank id is refused BEFORE the transport is touched',
         JSON.stringify({ text: r.els['emp-prof-error'].textContent,
                          fetches: r.fetches }));
    }
  }

  // ── D. PASSKEY REGISTRATION ────────────────────────────────────────────
  section('D. Register a Passkey -- the same pending-label question');

  {
    const r = realm({ httpAnswers: [
      { ok: true, body: { ok: true, challengeToken: 'ct',
        options: { challenge: 'AAAA', user: { id: 'BBBB', name: 'x' },
                   excludeCredentials: [] } } },
      { ok: true, body: { ok: true } }
    ] });
    const e = install(r, ['passkey']);
    if (e.missing) { cannot('D1-D2. the passkey function would not install', e.missing); }
    else {
      r.sandbox.window.sdRegisterPasskey();
      is(r.els['emp-passkey-register-btn'].textContent === 'Registering...'
         && r.els['emp-passkey-register-btn'].disabled === true,
         'D1. the passkey button enters its pending state synchronously',
         r.els['emp-passkey-register-btn'].textContent);
      await tick(); await tick(); await tick(); await tick(); await tick();
      is(r.els['emp-passkey-register-btn'].textContent === 'Register a Passkey on This Device'
         && r.els['emp-passkey-register-btn'].disabled === false
         && r.els['emp-passkey-error'].style.display !== 'block'
         && r.toasts.some(function (t) { return /Passkey registered/.test(String(t)); }),
         'D2. ...and leaves it on success, with the exact original label '
       + 'restored. A reset that writes a DIFFERENT label is a silent UI bug '
       + 'no status code shows',
         JSON.stringify({ t: r.els['emp-passkey-register-btn'].textContent,
                          d: r.els['emp-passkey-register-btn'].disabled,
                          toasts: r.toasts }));
    }
  }
  {
    const r = realm({ httpAnswers: [
      { ok: true, body: { ok: true, challengeToken: 'ct',
        options: { challenge: 'AAAA', user: { id: 'BBBB', name: 'x' },
                   excludeCredentials: [] } } }
    ], credentialsThrows: true });
    const e = install(r, ['passkey']);
    if (e.missing) { cannot('D3. user-cancelled path', e.missing); }
    else {
      r.sandbox.window.sdRegisterPasskey();
      await tick(); await tick(); await tick(); await tick(); await tick();
      is(r.els['emp-passkey-register-btn'].disabled === false
         && r.els['emp-passkey-error'].style.display === 'block'
         && /Cancelled/.test(r.els['emp-passkey-error'].textContent),
         'D3. a user who cancels Face ID gets "Cancelled or not completed" and '
       + 'the button back -- NotAllowedError is named rather than reported as '
       + 'a failure',
         r.els['emp-passkey-error'].textContent);
    }
  }
  {
    const r = realm({ httpAnswers: [{ ok: false, body: { error: { message: 'Passkeys are not enabled for this licence' } } }] });
    const e = install(r, ['passkey']);
    if (e.missing) { cannot('D4. server-refusal path', e.missing); }
    else {
      r.sandbox.window.sdRegisterPasskey();
      await tick(); await tick(); await tick(); await tick(); await tick();
      is(r.els['emp-passkey-register-btn'].disabled === false
         && /not enabled for this licence/.test(r.els['emp-passkey-error'].textContent),
         'D4. a server refusal at reg-options shows the server\'s message and '
       + 'releases the button',
         r.els['emp-passkey-error'].textContent);
    }
  }
  {
    const r = realm({ passkeyUnsupported: true });
    const e = install(r, ['passkey']);
    if (e.missing) { cannot('D5. unsupported-browser path', e.missing); }
    else {
      r.sandbox.window.sdRegisterPasskey();
      await tick();
      is(r.els['emp-passkey-unsupported'].style.display === 'block'
         && r.els['emp-passkey-register-btn'].textContent === ''
         && !r.fetches.length,
         'D5. an unsupported browser is TOLD so, never enters the pending '
       + 'state, and makes no request. PIN sign-in is unaffected',
         JSON.stringify({ unsup: r.els['emp-passkey-unsupported'].style.display,
                          btn: r.els['emp-passkey-register-btn'].textContent,
                          fetches: r.fetches.length }));
    }
  }
  {
    const r = realm({});
    r.store.sd_session_token = '';
    const e = install(r, ['passkey']);
    if (e.missing) { cannot('D6. expired-session path', e.missing); }
    else {
      r.sandbox.window.sdRegisterPasskey();
      await tick();
      is(/session has expired/.test(r.els['emp-passkey-error'].textContent)
         && r.els['emp-passkey-register-btn'].textContent === ''
         && !r.fetches.length,
         'D6. no session: told, no pending state, no request',
         r.els['emp-passkey-error'].textContent);
    }
  }

  // ── E. ABLATIONS, IN MEMORY, WITHOUT TOUCHING THE FILE ─────────────────
  section('E. ABLATIONS -- remove each b18 guard from the LIFTED source and '
        + 'confirm the arm above it goes red');

  // THE MUTATION IS ON THE LIFTED TEXT, NOT ON stonedesk.html. Rewriting a
  // 2.2MB file on disk to prove a three-line guard is load-bearing is a risk
  // with no reward -- a crashed process between the write and the restore
  // leaves the app broken. The lifted text IS the shipped code (Z proved the
  // extraction compiles and runs), so mutating it answers the same question
  // with nothing to restore.
  //
  // EACH ABLATION IS ONE NAMED LAYER and each is checked against the arm it
  // is supposed to hold -- per ARM, not per exit code.
  function ablateLifted(names, find, replace) {
    const src = [];
    for (const n of names) {
      const l = lift(ANCHORS[n]);
      if (l.missing) return { missing: n + ': ' + l.missing };
      src.push(l.src);
    }
    let text = src.join('\n');
    const hits = text.split(find).length - 1;
    if (hits !== 1) {
      return { missing: 'the ablation anchor matched ' + hits + ' time(s), not '
                      + 'exactly 1 -- refusing to measure. ' + find.slice(0, 70) };
    }
    text = text.replace(find, replace);
    try { new vm.Script(text); }
    catch (e) { return { missing: 'the ablated text does not compile: ' + e.message }; }
    return { text: text };
  }

  // E1 -- the render `.catch`. Without it, a throw in the handler leaves the
  // pending label standing, which is B5's exact subject.
  {
    const a = ablateLifted(['renderProfiles', 'readFailedNote', 'authRefusedNote'],
      '    }).catch(function(e){', '    }); if(false) (function(e){');
    if (a.missing) { cannot('E1. the render .catch is load-bearing', a.missing); }
    else {
      const r = realm({ readRows: [{ employee_id: 'emp-1', experience_level: 'new',
                                     communication_style: 'terse' }],
                        escAttrThrows: true });
      try { vm.runInContext(a.text, r.sandbox); } catch (e) {}
      const before = unhandled.length;
      try { r.sandbox.sdRenderEmployeeProfiles(); } catch (e) {}
      await tick(); await tick(); await tick();
      is(/Loading/.test(r.els['emp-prof-list'].textContent)
         && unhandled.length > before,
         'E1. WITHOUT the `.catch` the panel is left reading "Loading..." AND '
       + 'the error becomes an UNHANDLED REJECTION -- a console line nobody is '
       + 'watching, with the panel still claiming to load. So B5 is testing '
       + 'that guard and not something else. This is the 2026-08-06 bug '
       + 'reproduced on purpose',
         'textContent=' + r.els['emp-prof-list'].textContent
         + ' unhandled=+' + (unhandled.length - before));
    }
  }

  // E2 -- the three-state empty. Without the readFailed branch, a failed read
  // draws "No profiles set yet.", which is B2's exact subject.
  {
    const a = ablateLifted(['renderProfiles', 'readFailedNote', 'authRefusedNote'],
      "        if(typeof sdReadFailed==='function'&&sdReadFailed('employee_profile')){",
      "        if(false&&typeof sdReadFailed==='function'&&sdReadFailed('employee_profile')){");
    if (a.missing) { cannot('E2. the readFailed branch is load-bearing', a.missing); }
    else {
      const r = realm({ readRows: null, readFailed: true });
      try { vm.runInContext(a.text, r.sandbox); } catch (e) {}
      r.sandbox.sdRenderEmployeeProfiles();
      await tick(); await tick();
      is(/No profiles set yet/.test(r.els['emp-prof-list'].innerHTML),
         'E2. WITHOUT the readFailed branch a FAILED read draws "No profiles '
       + 'set yet." -- the false-empty, reproduced. Empty and unfetched look '
       + 'identical and only one means there is nothing to do',
         String(r.els['emp-prof-list'].innerHTML).slice(0, 140));
    }
  }

  // E3 -- the PER-STEP try AROUND THE SUCCESS BLOCK, which is the layer that
  // actually holds A5. Removing it lets a throwing toast reach the trailing
  // `.catch`, which then reports a CREATED credential as a failure -- the
  // pre-b18 behaviour, reproduced.
  {
    const a = ablateLifted(['grant'], '      }catch(_t){}', '      }catch(_t){throw _t;}');
    if (a.missing) { cannot('E3. the per-step try is load-bearing', a.missing); }
    else {
      const r = realm({ toastThrows: true });
      try { vm.runInContext(a.text, r.sandbox); } catch (e) {}
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-pin'].value = '123456';
      try { r.sandbox.window.sdGrantLoginAccess(); } catch (e) {}
      await tick(); await tick(); await tick();
      is(r.els['emp-login-error'].style.display === 'block'
         && r.els['emp-login-success'].style.display !== 'block',
         'E3. WITHOUT the per-step try, a throwing toast reaches the trailing '
       + '`.catch` and a CREATED credential is reported as a failure with no '
       + 'inline confirmation -- the pre-b18 behaviour reproduced. So A5 is '
       + 'testing THIS layer',
         JSON.stringify({ err: r.els['emp-login-error'].style.display,
                          errText: r.els['emp-login-error'].textContent,
                          ok: r.els['emp-login-success'].style.display }));
    }
  }

  // E3b -- AND THE MEASUREMENT THAT DID NOT GO THE WAY I EXPECTED, recorded
  // rather than dropped. The first version of E3 ablated the `typeof showToast`
  // guard and asserted the confirmation was lost. IT WAS NOT: the per-step try
  // swallows the throw either way, so that guard changes nothing on this path.
  // It is defence in depth and NOT the load-bearing layer, and saying so is
  // the point of an ablation -- an arm that had asserted otherwise would have
  // been a green claim about a layer doing work it is not doing.
  {
    const a = ablateLifted(['grant'],
      "        if(typeof showToast==='function'){", '        if(true){');
    if (a.missing) { cannot('E3b. the typeof guard measured alone', a.missing); }
    else {
      const r = realm({ toastThrows: true });
      try { vm.runInContext(a.text, r.sandbox); } catch (e) {}
      r.els['emp-login-id'].value = 'jsmith';
      r.els['emp-login-pin'].value = '123456';
      try { r.sandbox.window.sdGrantLoginAccess(); } catch (e) {}
      await tick(); await tick(); await tick();
      is(r.els['emp-login-success'].style.display === 'block'
         && r.els['emp-login-error'].style.display !== 'block',
         'E3b. removing the `typeof showToast` guard ALONE changes NOTHING -- '
       + 'the per-step try already covers it. Recorded as a measured '
       + 'redundancy, not claimed as a working layer',
         JSON.stringify({ ok: r.els['emp-login-success'].style.display,
                          err: r.els['emp-login-error'].style.display }));
    }
  }

  // E4 -- the CLEAN half. The same ablations, on inputs that do not throw,
  // must change nothing. Without this, an ablation harness that broke the
  // lifted code outright would have passed E1-E3 by accident.
  {
    const a = ablateLifted(['renderProfiles', 'readFailedNote', 'authRefusedNote'],
      '    }).catch(function(e){', '    }); if(false) (function(e){');
    if (a.missing) { cannot('E4. the clean half of the ablation pair', a.missing); }
    else {
      const r = realm({ readRows: [{ employee_id: 'emp-1', experience_level: 'new',
                                     communication_style: 'terse' }] });
      try { vm.runInContext(a.text, r.sandbox); } catch (e) {}
      r.sandbox.sdRenderEmployeeProfiles();
      await tick(); await tick();
      is(/emp-1/.test(r.els['emp-prof-list'].innerHTML)
         && !/Loading/.test(r.els['emp-prof-list'].textContent),
         'E4. CLEAN -- with the `.catch` removed but nothing throwing, the '
       + 'panel still renders normally. The ablations above are removing one '
       + 'guard, not breaking the function',
         String(r.els['emp-prof-list'].innerHTML).slice(0, 120));
    }
  }

  console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})();
