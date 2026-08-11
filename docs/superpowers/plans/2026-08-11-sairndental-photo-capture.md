# SAIRNdental Guided Photo-Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Up to 3 optional, client-compressed photos + one optional note
attached to a public booking request, reviewed by staff as thumbnails on
the existing Pending Requests panel — per
`docs/superpowers/specs/2026-08-11-sairndental-photo-capture-design.md`.
Zero AI involvement anywhere in this feature.

**Architecture:** A new `step-photo` wizard step in
`sairndental-book.html` compresses each selected photo client-side
(canvas downscale/re-encode ladder, same technique as StoneDesk's
`bsuCompressUnderBudget`, new ~300KB budget) before it ever leaves the
browser. `api/sairndental/public-book.js` gains a new, explicit
server-side validation step (extracted into a pure, testable module)
that rejects an oversized or malformed `photos` payload before any
database call. `sairndental.html`'s existing Pending Requests panel
renders thumbnails/note inline — no new panel.

**Tech Stack:** Plain browser Canvas API (no new dependency) for
compression; plain Node (`api/_lib/*.js`, zero new npm dependencies) for
server-side validation, matching this repo's existing convention.

## No SQL migration in this plan

`photos` and `patient_notes` are new keys inside the existing
`dnt_appointments` JSONB `data` payload `public-book.js` already
constructs — same no-migration pattern as the fee-schedule and
email-reminders plans. No new table, no new `sd-data.js` resource entry,
no promoted column.

## Global Constraints

- Photo is optional; up to 3 per request; nothing in the photo step
  blocks submission (spec §0, §1).
- Client-side compression targets ~300KB base64-string-length per photo
  (spec §0, §2) — a new budget, not the platform's existing 64KB
  convention (that convention belongs to `api/sd-data.js`'s generic
  write-payload check, which `public-book.js` does not go through).
- Server-side: reject (400 `PHOTOS_TOO_LARGE`) if the combined base64
  length of all `photos` entries exceeds `MAX_PHOTOS_PAYLOAD_BYTES`
  (1.2MB, spec §2), and reject (400 `INVALID_PHOTO`) if any entry isn't
  a well-formed `data:image/...;base64,...` string — both checks run
  **before** any database read/write, matching the existing
  rate-limit-first, fail-fast posture already in this file (spec §5).
- Capture-prompt copy is fixed/universal, never per-procedure-type
  (spec §0).
- No cancel/reschedule-style new public write capability beyond what
  already exists; photos/notes ride inside the existing booking POST,
  no new endpoint (spec §1).
- No new nav entry/panel on the staff side — thumbnails go into the
  existing Pending Requests panel only (spec §0, §4).
- `python tools/checkblocks.py sairndental.html sairndental-book.html`
  is not directly supported (the tool takes one file — run it once per
  file) / `div_balance_check.py` / `duplicate_global_check.py` clean
  after every HTML change. `node --check` on every new/modified `.js`
  file. Push Protocol: full local checks before push, real live-verify
  after.

---

### Task 1: Pure photo-validation module (size ceiling, format check, EXIF-segment detector)

**Files:**
- Create: `api/_lib/dental-photo-validation.js`
- Create: `api/_lib/dental-photo-validation.test.js`

**Interfaces:**
- Consumes: nothing (pure functions, no I/O).
- Produces: `validatePhotosPayload(photos)` — Task 2 imports and calls
  this exact function with a `photos` array (or `undefined`/`null`) and
  uses its return shape `{ok:true}` or
  `{ok:false, code:'PHOTOS_TOO_LARGE'|'INVALID_PHOTO'|'TOO_MANY_PHOTOS', message:string}`.
  `hasExifSegment(dataUrlOrBase64String)` — Task 5's live verification
  step imports and calls this exact function, returning `true`/`false`.

- [ ] **Step 1: Write the module**

```js
// api/_lib/dental-photo-validation.js
// Pure validation for SAIRNdental's public booking-photo attachments --
// no network/DB access, testable in isolation
// (dental-photo-validation.test.js). Enforced server-side because
// public-book.js is a fully unauthenticated endpoint with zero payload
// protection today (unlike api/sd-data.js's generic 64KB check, which
// this endpoint doesn't go through). See
// docs/superpowers/specs/2026-08-11-sairndental-photo-capture-design.md §2.

var MAX_PHOTOS = 3;
// 1.2MB combined base64 length -- headroom above 3 x the client's
// ~300KB compression target (spec §2), not a tight fit to it.
var MAX_PHOTOS_PAYLOAD_BYTES = Math.round(1.2 * 1024 * 1024);
var DATA_URL_RE = /^data:image\/[a-zA-Z0-9.+-]+;base64,([A-Za-z0-9+/=]+)$/;

function validatePhotosPayload(photos) {
  if (photos === undefined || photos === null) return { ok: true };
  if (!Array.isArray(photos)) {
    return { ok: false, code: 'INVALID_PHOTO', message: 'photos must be an array' };
  }
  if (photos.length > MAX_PHOTOS) {
    return { ok: false, code: 'TOO_MANY_PHOTOS', message: 'A maximum of ' + MAX_PHOTOS + ' photos is allowed' };
  }
  var totalBase64Len = 0;
  for (var i = 0; i < photos.length; i++) {
    var entry = photos[i];
    if (typeof entry !== 'string') {
      return { ok: false, code: 'INVALID_PHOTO', message: 'Each photo must be a data URL string' };
    }
    var m = DATA_URL_RE.exec(entry);
    if (!m) {
      return { ok: false, code: 'INVALID_PHOTO', message: 'Each photo must be a well-formed data:image/...;base64,... URL' };
    }
    totalBase64Len += m[1].length;
  }
  if (totalBase64Len > MAX_PHOTOS_PAYLOAD_BYTES) {
    return { ok: false, code: 'PHOTOS_TOO_LARGE', message: 'Photos are too large -- try retaking with better lighting or removing a photo' };
  }
  return { ok: true };
}

// Byte-scan for a JPEG EXIF (APP1) segment -- the real test for the
// design spec's "EXIF stripped by canvas re-encoding" claim (spec §0,
// §7). A JPEG's EXIF segment always contains the literal ASCII bytes
// "Exif\0\0" immediately after its APP1 marker (0xFFE1) and 2-byte
// length field, per the JPEG/EXIF spec -- searching for that literal
// byte sequence is a standard, reliable presence check without needing
// a full EXIF parser.
function hasExifSegment(dataUrlOrBase64) {
  var base64 = dataUrlOrBase64;
  var commaIdx = base64.indexOf(',');
  if (base64.slice(0, 5) === 'data:' && commaIdx !== -1) base64 = base64.slice(commaIdx + 1);
  var buf;
  try {
    buf = Buffer.from(base64, 'base64');
  } catch (e) {
    return false;
  }
  var marker = Buffer.from([0x45, 0x78, 0x69, 0x66, 0x00, 0x00]); // "Exif\0\0"
  return buf.includes(marker);
}

module.exports = {
  validatePhotosPayload: validatePhotosPayload,
  hasExifSegment: hasExifSegment,
  MAX_PHOTOS: MAX_PHOTOS,
  MAX_PHOTOS_PAYLOAD_BYTES: MAX_PHOTOS_PAYLOAD_BYTES
};
```

- [ ] **Step 2: `node --check`**

```
node --check api/_lib/dental-photo-validation.js
```

Expected: no output, exit code 0.

- [ ] **Step 3: Write the failing tests, then confirm they pass**

```js
// api/_lib/dental-photo-validation.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/_lib/dental-photo-validation.test.js

const assert = require('assert');
const { validatePhotosPayload, hasExifSegment, MAX_PHOTOS, MAX_PHOTOS_PAYLOAD_BYTES } = require('./dental-photo-validation');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

console.log('api/_lib/dental-photo-validation.js');

function fakeDataUrl(base64Length) {
  var body = 'A'.repeat(base64Length);
  return 'data:image/jpeg;base64,' + body;
}

// ── validatePhotosPayload ────────────────────────────────────────────
test('undefined photos -> ok (optional field, spec §0)', () => {
  assert.deepStrictEqual(validatePhotosPayload(undefined), { ok: true });
});
test('null photos -> ok', () => {
  assert.deepStrictEqual(validatePhotosPayload(null), { ok: true });
});
test('empty array -> ok', () => {
  assert.deepStrictEqual(validatePhotosPayload([]), { ok: true });
});
test('non-array photos -> INVALID_PHOTO', () => {
  var r = validatePhotosPayload('not-an-array');
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'INVALID_PHOTO');
});
test('exactly 3 well-formed small photos -> ok (at the count limit)', () => {
  var photos = [fakeDataUrl(100), fakeDataUrl(100), fakeDataUrl(100)];
  assert.deepStrictEqual(validatePhotosPayload(photos), { ok: true });
});
test('4 photos -> TOO_MANY_PHOTOS (over MAX_PHOTOS)', () => {
  assert.strictEqual(MAX_PHOTOS, 3);
  var photos = [fakeDataUrl(100), fakeDataUrl(100), fakeDataUrl(100), fakeDataUrl(100)];
  var r = validatePhotosPayload(photos);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'TOO_MANY_PHOTOS');
});
test('a non-string entry -> INVALID_PHOTO', () => {
  var r = validatePhotosPayload([12345]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'INVALID_PHOTO');
});
test('a string that is not a data URL -> INVALID_PHOTO', () => {
  var r = validatePhotosPayload(['not-a-data-url']);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'INVALID_PHOTO');
});
test('a data URL with a non-image MIME type -> INVALID_PHOTO', () => {
  var r = validatePhotosPayload(['data:text/plain;base64,aGVsbG8=']);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'INVALID_PHOTO');
});
test('combined base64 length just at the ceiling -> ok', () => {
  var r = validatePhotosPayload([fakeDataUrl(MAX_PHOTOS_PAYLOAD_BYTES)]);
  assert.strictEqual(r.ok, true);
});
test('combined base64 length just over the ceiling -> PHOTOS_TOO_LARGE', () => {
  var r = validatePhotosPayload([fakeDataUrl(MAX_PHOTOS_PAYLOAD_BYTES + 1)]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'PHOTOS_TOO_LARGE');
});
test('three photos whose SUM exceeds the ceiling, none individually over -> PHOTOS_TOO_LARGE', () => {
  var third = Math.floor(MAX_PHOTOS_PAYLOAD_BYTES / 3) + 100;
  var r = validatePhotosPayload([fakeDataUrl(third), fakeDataUrl(third), fakeDataUrl(third)]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'PHOTOS_TOO_LARGE');
});

// ── hasExifSegment ────────────────────────────────────────────────────
test('a buffer containing the literal EXIF marker bytes is detected', () => {
  var jpegLike = Buffer.concat([
    Buffer.from([0xFF, 0xD8, 0xFF, 0xE1, 0x00, 0x10]),
    Buffer.from([0x45, 0x78, 0x69, 0x66, 0x00, 0x00]), // "Exif\0\0"
    Buffer.from([0x00, 0x00, 0x00, 0x00])
  ]);
  var b64 = jpegLike.toString('base64');
  assert.strictEqual(hasExifSegment(b64), true);
  assert.strictEqual(hasExifSegment('data:image/jpeg;base64,' + b64), true);
});
test('a buffer with no EXIF marker bytes is NOT detected as having EXIF', () => {
  var plainJpegLike = Buffer.from([0xFF, 0xD8, 0xFF, 0xDB, 0x00, 0x43, 0x01, 0x02, 0x03, 0xFF, 0xD9]);
  var b64 = plainJpegLike.toString('base64');
  assert.strictEqual(hasExifSegment(b64), false);
});
test('invalid base64 input does not throw, returns false', () => {
  assert.strictEqual(hasExifSegment('not-valid-base64-!!!'), false);
});

console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
```

```
node --check api/_lib/dental-photo-validation.test.js
node api/_lib/dental-photo-validation.test.js
```

Expected: all 16 tests print `ok`, final line `16 passed`.

- [ ] **Step 4: Commit**

```bash
git add api/_lib/dental-photo-validation.js api/_lib/dental-photo-validation.test.js
git commit -m "feat: SAIRNdental -- pure photo-validation module (size/format checks + EXIF-segment detector) + tests"
```

---

### Task 2: Wire validation + storage into `public-book.js`

**Files:** Modify `api/sairndental/public-book.js`

**Interfaces:**
- Consumes: `validatePhotosPayload()` from Task 1
  (`../_lib/dental-photo-validation.js`).
- Produces: `appointmentData` (already existing object in this file)
  gains `photos` and `patient_notes` keys — Task 4's staff-side render
  reads these exact field names off the synced appointment record.

- [ ] **Step 1: Import the validator and read the two new body fields**

At the top of `api/sairndental/public-book.js`, after the existing
`require`:

```js
const { resolveSlug, checkAndIncrementRateLimit } = require('../_lib/dental-public');
const { validatePhotosPayload } = require('../_lib/dental-photo-validation');
```

In the existing required-field block (currently `const body = req.body
|| {}; ... if (!slug || !patient.name || ...) { ... return; }`), add
reading the two new fields right after `const providerId = ...` line:

```js
    const body = req.body || {};
    const slug = body.slug;
    const patient = body.patient || {};
    const providerId = body.provider_id, procedureTypeId = body.procedure_type_id, startTime = body.start_time;
    const photos = body.photos;
    const patientNotes = typeof body.patient_notes === 'string' ? body.patient_notes.trim() : '';
    if (!slug || !patient.name || !patient.dob || !patient.phone || !providerId || !procedureTypeId || !startTime) {
      res.status(400).json({ error: { message: 'slug, patient (name/dob/phone), provider_id, procedure_type_id, start_time are required' } });
      return;
    }
```

- [ ] **Step 2: Validate photos immediately after the existing required-field check, before any Supabase call**

Insert right after that `if (!slug || ...) { ...; return; }` block (still
before the `const licenseHash = await resolveSlug(slug);` line):

```js
    const photosCheck = validatePhotosPayload(photos);
    if (!photosCheck.ok) {
      res.status(400).json({ error: { code: photosCheck.code, message: photosCheck.message } });
      return;
    }
```

- [ ] **Step 3: Store photos/notes on the appointment record**

In the existing `appointmentData` object construction, add the two new
fields:

```js
    const appointmentId = newId('AP');
    const appointmentData = {
      id: appointmentId, patient_id: patientId, provider_id: providerId, operatory_id: operatoryId,
      procedure_type_id: procedureTypeId, start_time: startTime, end_time: endTime, status: 'Pending', source: 'self-scheduled',
      photos: Array.isArray(photos) ? photos : [], patient_notes: patientNotes
    };
```

(The rest of the function — the Supabase insert, the 409/502 handling,
the 200 response — is unchanged; `appointmentData` already flows into
that same `body: JSON.stringify({..., data: appointmentData, ...})`
call.)

- [ ] **Step 4: `node --check`**

```
node --check api/sairndental/public-book.js
```

Expected: no output, exit code 0.

- [ ] **Step 5: Write the failing tests, then confirm they pass**

These tests cover only the paths that return **before** any network
call (the existing required-field check, regression-tested, plus the
three new photo-validation outcomes) — proven by injecting a `fetch`
stub that throws if it's ever called, the same technique used to keep
these tests free of any real Supabase dependency.

```js
// api/sairndental/public-book.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/sairndental/public-book.test.js
//
// Covers only the pre-network-call validation paths (existing
// required-field check + the new photos validation). The full
// resolveSlug -> Supabase -> insert flow needs a real (or live-mocked)
// Supabase environment and is covered by the plan's Task 5 live
// verification instead, not here.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}
function mockReq(body) {
  return { method: 'POST', headers: {}, body: body };
}

let passed = 0;
async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

var VALID_BASE = {
  slug: 'test-practice', patient: { name: 'Jane Doe', dob: '1990-01-01', phone: '555-0100' },
  provider_id: 'PV-1', procedure_type_id: 'PC-1', start_time: '2026-08-13T14:00:00.000Z'
};

async function main() {
  console.log('api/sairndental/public-book.js');

  var originalFetch = global.fetch;
  global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
  delete require.cache[require.resolve('./public-book.js')];
  var handler = require('./public-book.js');

  await test('missing required field (existing regression: no patient.name) -> 400, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { patient: { dob: '1990-01-01', phone: '555-0100' } });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('4 photos -> 400 TOO_MANY_PHOTOS, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { photos: ['data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA'] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'TOO_MANY_PHOTOS');
  });

  await test('a malformed photo entry -> 400 INVALID_PHOTO, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { photos: ['not-a-real-data-url'] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PHOTO');
  });

  await test('an oversized combined photos payload -> 400 PHOTOS_TOO_LARGE, never calls fetch', async () => {
    var res = mockRes();
    var big = 'data:image/jpeg;base64,' + 'A'.repeat(1.3 * 1024 * 1024);
    var body = Object.assign({}, VALID_BASE, { photos: [big] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'PHOTOS_TOO_LARGE');
  });

  global.fetch = originalFetch;
  console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
}

main();
```

```
node --check api/sairndental/public-book.test.js
node api/sairndental/public-book.test.js
```

Expected: all 4 tests print `ok`, final line `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add api/sairndental/public-book.js api/sairndental/public-book.test.js
git commit -m "feat: SAIRNdental -- public-book.js accepts + validates photos/patient_notes (fail-fast, before any DB call) + tests"
```

---

### Task 3: Guided capture UI in `sairndental-book.html`

**Files:** Modify `sairndental-book.html`

**Interfaces:**
- Consumes: nothing from earlier tasks (browser-side only).
- Produces: `submitBooking()`'s POST body gains `photos` (array of
  compressed data-URL strings) and `patient_notes` (string) — Task 2's
  `appointmentData` construction already expects exactly these field
  names.

- [ ] **Step 1: Add the new step's HTML, and change the details step's button**

Change the `step-details` submit button to a "Continue" button that
just advances the wizard (no network call), and add the new
`step-photo` block right after it:

```html
  <div id="step-details" class="step">
    <div class="card">
      <div class="fg"><label>Full Name</label><input type="text" id="bk-name"></div>
      <div class="fg"><label>Date of Birth</label><input type="date" id="bk-dob"></div>
      <div class="fg"><label>Phone</label><input type="text" id="bk-phone" placeholder="(555) 555-5555"></div>
      <div class="fg"><label>Email (optional)</label><input type="email" id="bk-email"></div>
      <button class="btn" id="bk-details-continue-btn" onclick="continueToPhotoStep()">Continue</button>
      <div class="msg" id="bk-details-msg"></div>
    </div>
  </div>

  <div id="step-photo" class="step">
    <div class="card">
      <div class="msg">Find good lighting, hold the camera steady, and get close to the area of concern. Photos are optional -- you can skip this and still submit your request.</div>
      <div id="bk-photo-tiles" style="display:flex;gap:10px;flex-wrap:wrap;margin:14px 0"></div>
      <input type="file" id="bk-photo-input" accept="image/*" capture="environment" style="display:none" onchange="onPhotoFileSelected(event)">
      <button class="btn" id="bk-add-photo-btn" onclick="document.getElementById('bk-photo-input').click()" style="background:#fff;color:var(--pd);border:1px solid var(--p)">+ Add Photo</button>
      <div class="fg" style="margin-top:16px"><label>Anything you'd like the dentist to know? (optional)</label><textarea id="bk-notes" rows="3" style="width:100%;border:1px solid var(--border);border-radius:8px;padding:10px 12px;font-size:14px;font-family:inherit"></textarea></div>
      <button class="btn" id="bk-submit-btn" onclick="submitBooking()">Request This Appointment</button>
      <div class="msg" id="bk-submit-msg"></div>
    </div>
  </div>
```

- [ ] **Step 2: Compression ladder + tile management**

Add before `function esc(s){...}`:

```js
var bkPhotos=[]; // array of compressed data-URL strings, max 3

function continueToPhotoStep(){
  var name=document.getElementById('bk-name').value.trim();
  var dob=document.getElementById('bk-dob').value;
  var phone=document.getElementById('bk-phone').value.trim();
  var msgEl=document.getElementById('bk-details-msg');
  if(!name||!dob||!phone){msgEl.textContent='Name, date of birth, and phone are required.';msgEl.className='msg err';return;}
  msgEl.textContent='';
  showStep('photo');
}

function bkCompressOnce(dataUrl,maxDim,quality){
  return new Promise(function(resolve){
    var img=new Image();
    img.onload=function(){
      var scale=Math.min(1,maxDim/Math.max(img.width,img.height));
      var w=Math.max(1,Math.round(img.width*scale)),h=Math.max(1,Math.round(img.height*scale));
      var canvas=document.createElement('canvas');
      canvas.width=w;canvas.height=h;
      canvas.getContext('2d').drawImage(img,0,0,w,h);
      resolve(canvas.toDataURL('image/jpeg',quality));
    };
    img.onerror=function(){resolve(dataUrl);};
    img.src=dataUrl;
  });
}
// Budget ~300KB base64-string length (design spec §0/§2) -- a more
// generous ladder than StoneDesk's stone-photo uploader since dental
// photos need to stay genuinely useful for a dentist's real review, and
// this endpoint isn't bound by api/sd-data.js's 64KB payload check.
// Canvas re-encoding (drawImage + toDataURL) mechanically drops all
// original EXIF/GPS metadata as a side effect -- verified explicitly in
// Task 5, not just assumed.
async function bkCompressUnderBudget(dataUrl,budgetBytes){
  var attempts=[[1400,0.75],[1100,0.68],[900,0.6],[700,0.5],[550,0.4],[420,0.32]];
  var out=dataUrl;
  for(var i=0;i<attempts.length;i++){
    out=await bkCompressOnce(dataUrl,attempts[i][0],attempts[i][1]);
    var b64Len=out.length-(out.indexOf(',')+1);
    if(b64Len<=budgetBytes)return out;
  }
  return out; // best effort -- server-side size check (Task 2) is the real backstop
}

function renderPhotoTiles(){
  var el=document.getElementById('bk-photo-tiles');
  el.innerHTML=bkPhotos.map(function(dataUrl,i){
    return '<div style="position:relative"><img src="'+dataUrl+'" style="width:80px;height:80px;object-fit:cover;border-radius:8px;border:1px solid var(--border)" onclick="window.open(this.src)">'+
      '<button onclick="removeBkPhoto('+i+')" style="position:absolute;top:-6px;right:-6px;width:20px;height:20px;border-radius:50%;border:none;background:var(--danger);color:#fff;font-size:12px;cursor:pointer">&times;</button></div>';
  }).join('');
  document.getElementById('bk-add-photo-btn').style.display=bkPhotos.length>=3?'none':'block';
}
function removeBkPhoto(i){bkPhotos.splice(i,1);renderPhotoTiles();}

async function onPhotoFileSelected(event){
  var file=event.target.files[0];
  event.target.value='';
  if(!file)return;
  var msgEl=document.getElementById('bk-submit-msg');
  if(file.type.indexOf('image/')!==0){msgEl.textContent="That doesn't look like an image -- try again.";msgEl.className='msg err';return;}
  msgEl.textContent='';
  var reader=new FileReader();
  reader.onload=async function(e){
    var compressed=await bkCompressUnderBudget(e.target.result,300*1024);
    bkPhotos.push(compressed);
    renderPhotoTiles();
  };
  reader.readAsDataURL(file);
}
```

- [ ] **Step 3: Send photos/notes in `submitBooking()`**

```js
async function submitBooking(){
  var name=document.getElementById('bk-name').value.trim();
  var dob=document.getElementById('bk-dob').value;
  var phone=document.getElementById('bk-phone').value.trim();
  var email=document.getElementById('bk-email').value.trim();
  var notes=document.getElementById('bk-notes').value.trim();
  var msgEl=document.getElementById('bk-submit-msg');
  if(!name||!dob||!phone){msgEl.textContent='Name, date of birth, and phone are required.';msgEl.className='msg err';return;}
  if(!pickedSlot){msgEl.textContent='Select a time first.';msgEl.className='msg err';return;}
  var btn=document.getElementById('bk-submit-btn');
  btn.disabled=true;btn.textContent='Sending request...';msgEl.textContent='';
  try{
    var res=await fetch(BOOK_API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      slug:slug,patient:{name:name,dob:dob,phone:phone,email:email},
      provider_id:pickedProvider,procedure_type_id:pickedProcedure,start_time:pickedSlot.start_time,
      photos:bkPhotos,patient_notes:notes
    })});
    var data=await res.json();
    if(!res.ok||!data.ok){
      msgEl.textContent=(data.error&&data.error.message)||'Could not complete booking -- try again.';
      msgEl.className='msg err';
      btn.disabled=false;btn.textContent='Request This Appointment';
      return;
    }
    showStep('done');
  }catch(e){
    msgEl.textContent='Could not connect. Check your connection and try again.';msgEl.className='msg err';
    btn.disabled=false;btn.textContent='Request This Appointment';
  }
}
```

(This replaces the existing `submitBooking()` function body — same
error handling, same `try/catch`, same 409/400 message passthrough,
unchanged. Also note `pickSlot(i)` currently calls
`showStep('details')` — leave that unchanged; `continueToPhotoStep()`,
new in Step 2, is what advances from `details` to `photo`.)

- [ ] **Step 4: Syntax-check**

```
python tools/checkblocks.py sairndental-book.html
python tools/div_balance_check.py sairndental-book.html
python tools/duplicate_global_check.py sairndental-book.html
```

Expected: all clean (no duplicate IDs — `bk-details-continue-btn`,
`bk-photo-tiles`, `bk-photo-input`, `bk-add-photo-btn`, `bk-notes`,
`bk-details-msg` are all new and unique).

- [ ] **Step 5: Manual verification (browser/canvas code — no Node test harness for this in this repo, matching established convention)**

Open the real public booking page (`?slug=<a real practice slug>`),
walk through: select a slot → fill in name/dob/phone → Continue → the
photo step appears. Add a real photo (confirm a thumbnail appears and
shrinks to a reasonable preview size), add a second and third (confirm
"+ Add Photo" disappears after the 3rd), remove one (confirm "+ Add
Photo" reappears), select a non-image file if possible (confirm the
rejection message), fill in the optional note, submit with photos +
note present (confirm success), then repeat with zero photos and no
note (confirm submission still succeeds — the optional-field
regression case).

**Compression-budget test (the real check for spec §7's budget claim):**
with the browser devtools console open during the "Add Photo" step, run
`bkPhotos[bkPhotos.length-1].length` after each photo is added — this
is the actual base64 string length (plus the short `data:image/jpeg;
base64,` prefix) the ~300KB target applies to. Confirm each added photo
lands at or reasonably close to that budget (not still multiple
megabytes, which would mean the ladder never engaged), across at least
2 real photos of different original sizes/qualities if available.

- [ ] **Step 6: Commit**

```bash
git add sairndental-book.html
git commit -m "feat: SAIRNdental -- guided photo-capture step on the public booking page (up to 3 photos, optional note, client-side compression)"
```

---

### Task 4: Staff-side thumbnails + note on Pending Requests

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: `appointments()`, `patients()`, `providers()`, `H()`, `$()`,
  the existing `rPending()` (line 864) and `pending-table` HTML (line
  397). Reads `a.photos` and `a.patient_notes` — the exact field names
  Task 2's `appointmentData` writes.
- Produces: no new functions — a display-only change.

- [ ] **Step 1: Add a Photos/Notes column**

In the `pending-table` header (line 397):

```html
          <table id="pending-table"><thead><tr><th>Patient</th><th>Provider</th><th>Time</th><th>Source</th><th>Photos / Notes</th><th></th></tr></thead><tbody id="pending-tbody"></tbody></table>
```

- [ ] **Step 2: Render thumbnails + note, update the empty-state colspan**

```js
function rPending(){
  var list=appointments().filter(function(a){return a.status==='Pending';});
  var pats=patients(),provs=providers();
  var tbody=$('pending-tbody');
  tbody.innerHTML=list.map(function(a){
    var pt=pats.find(function(x){return x.id===a.patient_id;});
    var pv=provs.find(function(x){return x.id===a.provider_id;});
    var photos=Array.isArray(a.photos)?a.photos:[];
    var thumbs=photos.map(function(src){
      return '<img src="'+src+'" style="width:36px;height:36px;object-fit:cover;border-radius:4px;border:1px solid var(--border);cursor:pointer;margin-right:4px" onclick="window.open(this.src)">';
    }).join('');
    var noteHtml=a.patient_notes?('<div style="font-size:12px;color:var(--muted);margin-top:4px">'+H(a.patient_notes)+'</div>'):'';
    return '<tr><td>'+H(pt?pt.name:'(unknown patient)')+'</td><td>'+H(pv?pv.name:'(unknown provider)')+'</td>'+
      '<td>'+H(a.start_time?new Date(a.start_time).toLocaleString():'--')+'</td><td>'+H(a.source||'staff')+'</td>'+
      '<td>'+thumbs+noteHtml+'</td>'+
      '<td><button class="btn bp bs" onclick="confirmAppointment(\''+a.id+'\')">Confirm</button> <button class="btn bo bs" onclick="rejectAppointment(\''+a.id+'\')">Reject</button></td></tr>';
  }).join('')||'<tr><td colspan="6" style="color:var(--muted);text-align:center">No pending requests</td></tr>';
}
```

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

- [ ] **Step 4: Manual verification**

After Task 3's live submission (with photos + note) lands as a real
Pending appointment, open the Pending Requests panel — confirm the
thumbnails and note render, clicking a thumbnail opens the full-size
image in a new tab, and a Pending request with no photos/note (an
existing/staff-created one) renders exactly as it did before this
change (`H(a.patient_notes)` never emits anything for an empty string,
`thumbs` is `''` for an empty array — no thrown error either way, per
spec §5's malformed/missing-field requirement).

- [ ] **Step 5: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- Pending Requests panel shows photo thumbnails + patient note"
```

---

### Task 5: End-to-end verification, push, live-verify

- [ ] **Step 1:** Full local re-check: `checkblocks.py` /
  `div_balance_check.py` / `duplicate_global_check.py` on both
  `sairndental.html` and `sairndental-book.html`; `node --check` on all
  4 new/modified `.js` files; run all 3 new test suites
  (`dental-photo-validation.test.js`, `public-book.test.js`, and
  confirm no existing test suite regressed).
- [ ] **Step 2:** Push to `main`.
- [ ] **Step 3: Real EXIF-strip verification (the actual test for spec
  §0/§7's privacy claim) — genuinely live, not simulated.** Using a
  real phone camera (which embeds real EXIF, including GPS if location
  services are on), capture a photo through the live deployed public
  booking page's new photo step. After the booking is created, read
  back the stored `photos[0]` value for that test appointment (via a
  Supabase read using the existing patterns already established
  elsewhere in this codebase) and run it through Task 1's
  `hasExifSegment()` helper. Expected: `false` — confirms canvas
  re-encoding genuinely stripped the EXIF segment on a real photo, not
  just on the hand-constructed byte fixture in Task 1's unit test.
- [ ] **Step 4: Size-ceiling live test.** `curl` the live
  `public-book.js` endpoint directly with a `photos` array whose
  combined base64 length exceeds 1.2MB. Expected: `400`
  `PHOTOS_TOO_LARGE`, and confirm (via a Supabase read scoped to that
  test slug/patient) that no appointment record was created at all.
- [ ] **Step 5: Malformed-photo live test.** Same live `curl`
  technique with a `photos` entry that isn't a valid data URL.
  Expected: `400` `INVALID_PHOTO`, no appointment created.
- [ ] **Step 6: Optional-field regression live test.** Submit a real
  booking through the live page with zero photos and no note (skip the
  whole photo step). Expected: succeeds identically to the pre-feature
  booking flow — confirms this feature didn't break the baseline path.
- [ ] **Step 7: Existing-behavior regression.** Confirm the pre-existing
  409 `SLOT_TAKEN` response (submit the same slot twice) and the
  pre-existing 400 missing-required-field response (omit `patient.name`
  in a live `curl`) are both unchanged by this feature's additions.
- [ ] **Step 8:** Delete all test appointments/patients created for
  Steps 3-7 so they don't pollute real practice data or the live
  Pending Requests panel.
- [ ] **Step 9:** Update
  `docs/superpowers/specs/2026-08-11-sairndental-photo-capture-design.md`'s
  status line with the real commit SHAs and confirmed-live date.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-5
is written**, per your instruction.
