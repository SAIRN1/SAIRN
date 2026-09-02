// Offline EVV capture, driven verbatim from sairnsenior.html.
//
// Competitive-gap audit A2. The audit names GPS-plus-telephony as the
// table-stakes pairing and rural/no-signal visits as the reason telephony
// persists. This is the half that needs no phone system. Verified absent
// before building: `offline` 0, `telephony` 0, `navigator.onLine` 0, `queue` 0.
//
// THE GAP IN THE CODE THIS REPLACES: a failed write returned "check your
// connection and try again" and DISCARDED the clock event. A caregiver in a
// basement, a rural home or a concrete stairwell could not record the visit at
// all -- and EVV is federally mandated, so a visit that really happened had no
// record.
//
// THE THREE PROPERTIES THIS FILE EXISTS TO HOLD:
//
//   1. THE RECORDED TIME IS WHEN THE CAREGIVER CLOCKED, NEVER WHEN IT SYNCED.
//      The queued payload is replayed UNCHANGED. Re-stamping on flush would
//      produce an EVV record that is precise, plausible and false -- worse
//      than a missing one, because nothing downstream could tell.
//   2. FIFO, STOPPING AT THE FIRST FAILURE. A visit clocked in and then out
//      while offline queues TWO entries for one visit. Flushing in parallel,
//      or skipping a failure to try the next, can apply the clock-out before
//      the clock-in -- a completed visit with no start time, which reads as an
//      EVV exception that never happened.
//   3. NOTHING IS SILENTLY DROPPED. The queue is capped, and reaching the cap
//      is said out loud rather than swallowed.

const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', '..', 'sairnsenior.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start, open, close) {
  let i = src.indexOf(open, start), depth = 0;
  if (i < 0) throw new Error('no ' + open);
  for (; i < src.length; i++) {
    if (src[i] === open) depth++;
    else if (src[i] === close) { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced');
}
function fn(name) {
  const sig = ['function ' + name + '(', 'async function ' + name + '('];
  for (const s of sig) {
    const start = src.indexOf(s);
    if (start >= 0) return src.slice(start, src.indexOf('{', start)) + balanced(start, '{', '}').slice(balanced(start, '{', '}').indexOf('{'));
  }
  throw new Error('not found: ' + name);
}
function whole(name) {
  const s = src.indexOf('async function ' + name + '(') >= 0
    ? src.indexOf('async function ' + name + '(') : src.indexOf('function ' + name + '(');
  if (s < 0) throw new Error('not found: ' + name);
  return balanced(s, '{', '}');
}
function scalar(name) {
  const m = src.match(new RegExp('var ' + name + '=([^;]+);'));
  if (!m) throw new Error('not found: var ' + name);
  return 'var ' + name + '=' + m[1] + ';';
}

// The world: a localStorage stand-in plus a senData whose success is
// controlled per call, so "offline" is modelled the way it really arrives --
// a write that returns falsy.
function build(opts) {
  opts = opts || {};
  const store = Object.assign({ sen_visits: [], sen_evv_queue: [] }, opts.store || {});
  const w = {
    calls: [], toasts: [], now: opts.now || '2026-09-02T15:00:00.000Z',
    store,
    ld: (k, d) => JSON.parse(JSON.stringify(store[k] === undefined ? d : store[k])),
    st: (k, v) => { store[k] = JSON.parse(JSON.stringify(v)); },
    visits: () => JSON.parse(JSON.stringify(store.sen_visits)),
    senLicenseKey: () => opts.noKey ? '' : 'KEY',
    toast: (m) => w.toasts.push(m),
    renderClockView: () => {}, vsRenderKpis: () => {},
    $: () => null,
    senData: async (action, res, payload) => {
      w.calls.push(JSON.parse(JSON.stringify(payload)));
      const ok = typeof opts.online === 'function' ? opts.online(w.calls.length) : opts.online !== false;
      if (!ok) return null;
      return Object.assign({}, payload);
    }
  };
  const names = ['ld', 'st', 'visits', 'senLicenseKey', 'toast', 'renderClockView', 'vsRenderKpis', '$', 'senData'];
  const body =
    scalar('SEN_EVV_QUEUE_KEY') + '\n' + scalar('SEN_EVV_QUEUE_MAX') + '\n' +
    'var _evvFlushing=false;\n' +
    whole('evvQueue') + '\n' + whole('evvQueueAdd') + '\n' +
    whole('senFlushEvvQueue') + '\n' + whole('evvRenderQueueBadge') + '\n' +
    whole('vsRecordClockEvent') + '\n' +
    'return { evvQueue, evvQueueAdd, senFlushEvvQueue, vsRecordClockEvent, SEN_EVV_QUEUE_MAX };';
  w.api = new Function('W', ...names, body)(w, ...names.map((n) => w[n]));
  return w;
}

const IN = (id, at) => ({ id: id, clock_in_at: at, status: 'in_progress', clock_in_lat: 41.5, clock_in_lng: -81.9 });
const OUT = (id, at) => ({ id: id, clock_out_at: at, status: 'completed', services_notes: '' });

(async () => {
  // ── the event is KEPT, not discarded ──────────────────────────────────
  {
    const w = build({ online: false, store: { sen_visits: [{ id: 'V1', status: 'scheduled' }] } });
    const ok = await w.api.vsRecordClockEvent('V1', IN('V1', '2026-09-02T14:00:00.000Z'), 'Clocked in');
    check('an offline clock-in is kept rather than discarded', [ok, w.api.evvQueue().length], [true, 1]);
    check('and applied locally so the caregiver\'s own screen is right',
      [w.store.sen_visits[0].clock_in_at, w.store.sen_visits[0].status, w.store.sen_visits[0].evv_offline],
      ['2026-09-02T14:00:00.000Z', 'in_progress', true]);
    check('the GPS captured offline is kept too -- offline is not an excuse for a missing location',
      [w.store.sen_visits[0].clock_in_lat, w.store.sen_visits[0].clock_in_lng], [41.5, -81.9]);
    check('the caregiver is told it is on this device only, not that it succeeded',
      /saved on this device with the real time and location/.test(w.toasts[0]), true);
  }

  // ── THE TIME IS NEVER RE-STAMPED ──────────────────────────────────────
  {
    let online = false;
    const w = build({ online: () => online, store: { sen_visits: [{ id: 'V1', status: 'scheduled' }] } });
    await w.api.vsRecordClockEvent('V1', IN('V1', '2026-09-02T14:00:00.000Z'), 'Clocked in');
    online = true;
    const r = await w.api.senFlushEvvQueue();
    check('the backlog flushes when the connection returns', [r.sent, r.left], [1, 0]);
    const replayed = w.calls[w.calls.length - 1];
    check('and the replayed payload carries the ORIGINAL clock time, unchanged',
      replayed.clock_in_at, '2026-09-02T14:00:00.000Z');
    check('the visit keeps that time too -- the sync time is recorded separately',
      [w.store.sen_visits[0].clock_in_at, !!w.store.sen_visits[0].evv_synced_at],
      ['2026-09-02T14:00:00.000Z', true]);
    check('and the record stays flagged as offline-captured for a compliance reviewer',
      w.store.sen_visits[0].evv_offline, true);
  }

  // ── FIFO, AND STOP AT THE FIRST FAILURE ───────────────────────────────
  {
    const w = build({ online: false, store: { sen_visits: [{ id: 'V1', status: 'scheduled' }] } });
    await w.api.vsRecordClockEvent('V1', IN('V1', '2026-09-02T14:00:00.000Z'), 'Clocked in');
    await w.api.vsRecordClockEvent('V1', OUT('V1', '2026-09-02T16:00:00.000Z'), 'Visit completed');
    check('two events for one visit queue in the order they happened',
      w.api.evvQueue().map((e) => Object.keys(e.payload).filter((k) => /clock_/.test(k))[0]),
      ['clock_in_at', 'clock_out_at']);
    // Now let only the FIRST replay succeed. The second must stay queued and
    // the clock-out must NOT be applied ahead of it on a later attempt.
    let n = 0;
    const w2 = build({
      store: { sen_visits: [{ id: 'V1', status: 'scheduled' }], sen_evv_queue: w.api.evvQueue() },
      online: () => { n++; return n === 1; }
    });
    const r = await w2.api.senFlushEvvQueue();
    check('a failure stops the flush instead of skipping to the next entry', [r.sent, r.left], [1, 1]);
    check('the clock-IN went first and the clock-OUT is still waiting',
      [w2.calls.length, !!w2.calls[0].clock_in_at, w2.api.evvQueue()[0].payload.clock_out_at],
      [2, true, '2026-09-02T16:00:00.000Z']);
  }
  {
    // The ordering guarantee stated as its own assertion: a clock-out never
    // reaches the server before its clock-in.
    const w = build({ online: false, store: { sen_visits: [{ id: 'V1' }] } });
    await w.api.vsRecordClockEvent('V1', IN('V1', '2026-09-02T14:00:00.000Z'), 'in');
    await w.api.vsRecordClockEvent('V1', OUT('V1', '2026-09-02T16:00:00.000Z'), 'out');
    const w2 = build({ online: true, store: { sen_visits: [{ id: 'V1' }], sen_evv_queue: w.api.evvQueue() } });
    await w2.api.senFlushEvvQueue();
    const order = w2.calls.map((c) => (c.clock_in_at ? 'in' : 'out'));
    check('replayed in order -- a clock-out never reaches the server before its clock-in', order, ['in', 'out']);
  }

  // ── nothing is silently dropped ───────────────────────────────────────
  {
    const full = [];
    for (let i = 0; i < 200; i++) full.push({ queued_at: 'x', payload: { id: 'V' + i } });
    const w = build({ online: false, store: { sen_visits: [{ id: 'V1' }], sen_evv_queue: full } });
    const ok = await w.api.vsRecordClockEvent('V1', IN('V1', '2026-09-02T14:00:00.000Z'), 'Clocked in');
    check('at the cap the event is REFUSED rather than quietly dropped', ok, false);
    check('and the caregiver is told the cap was hit and what to do',
      /already has 200 visits waiting to sync/.test(w.toasts[0]), true);
    check('the queue is not grown past its cap', w.api.evvQueue().length, 200);
    check('and the earlier entries are untouched -- nothing is evicted to make room',
      w.api.evvQueue()[0].payload.id, 'V0');
  }

  // ── a normal online clock is unchanged ────────────────────────────────
  {
    const w = build({ online: true, store: { sen_visits: [{ id: 'V1', status: 'scheduled' }] } });
    const ok = await w.api.vsRecordClockEvent('V1', IN('V1', '2026-09-02T14:00:00.000Z'), 'Clocked in');
    check('an online clock-in queues nothing and is not flagged offline',
      [ok, w.api.evvQueue().length, w.store.sen_visits[0].evv_offline], [true, 0, undefined]);
    check('and its toast is the plain one, with no offline wording',
      /saved on this device/.test(w.toasts[0]), false);
  }
  {
    const w = build({ online: true, noKey: true, store: { sen_evv_queue: [{ queued_at: 'x', payload: { id: 'V1' } }] } });
    const r = await w.api.senFlushEvvQueue();
    check('with no licence key the flush does nothing rather than erroring', [r.sent, r.left, w.calls.length], [0, 1, 0]);
  }

  // ── the page ──────────────────────────────────────────────────────────
  check('the queue lives only on the device -- it is by definition what could not reach the server',
    /sen_evv_queue/.test(fs.readFileSync(path.join(__dirname, '..', '_resources', 'sairnsenior.js'), 'utf8')), false);
  check('the flush is retried when the browser says the network came back',
    /window\.addEventListener\('online'/.test(src), true);
  check('and the online event is treated as a hint, not proof -- the flush still stops on failure',
    /'online' is a hint and[\s\S]{0,200}not a guarantee/.test(src), true);
  check('the pending count is shown to the caregiver rather than left silent',
    /vs-offline-badge/.test(src), true);
  check('and the row itself says the record is on this device only',
    /On this device only/.test(src), true);
  check('a synced offline record still says it was captured offline',
    /Sent &mdash; recorded offline/.test(src), true);
  // THE FAILURE MODE THIS REPLACED, asserted gone: the old code discarded the
  // event and told the caregiver to try again.
  check('the old discard-and-retry path is gone from both clock actions',
    /Could not clock (in|out) -- check your connection and try again/.test(src), false);

  console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
  if (fail) process.exit(1);
})();
