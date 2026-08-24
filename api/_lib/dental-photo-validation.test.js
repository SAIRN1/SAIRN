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
// DELIBERATE BEHAVIOUR CHANGE, 2026-08-24: the budget now counts the WHOLE
// data URL, not just the base64 payload after "base64,". These two tests were
// written against the old semantics and are updated rather than deleted, so
// the change is visible in the diff instead of silently disappearing.
//
// Why it changed: DATA_URL_RE permits an arbitrarily long MIME subtype, so the
// uncounted prefix was unbounded -- and dnt_appointments' size constraint is
// sized from this budget, which cannot be sound while any covered field is
// unbounded.
var PREFIX = 'data:image/jpeg;base64,'.length;
test('whole data URL just at the ceiling -> ok', () => {
  var r = validatePhotosPayload([fakeDataUrl(MAX_PHOTOS_PAYLOAD_BYTES - PREFIX)]);
  assert.strictEqual(r.ok, true);
});
test('whole data URL just over the ceiling -> PHOTOS_TOO_LARGE', () => {
  var r = validatePhotosPayload([fakeDataUrl(MAX_PHOTOS_PAYLOAD_BYTES - PREFIX + 1)]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'PHOTOS_TOO_LARGE');
});
test('a base64 payload at the old ceiling is now REJECTED, because the prefix counts', () => {
  var r = validatePhotosPayload([fakeDataUrl(MAX_PHOTOS_PAYLOAD_BYTES)]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'PHOTOS_TOO_LARGE');
});
test('a long MIME subtype can no longer smuggle unbounded bytes past the budget', () => {
  var longType = 'data:image/' + 'a'.repeat(4000) + ';base64,' + 'A'.repeat(1000);
  var r = validatePhotosPayload([longType]);
  assert.strictEqual(r.ok, true, 'well under the budget, so still allowed');
  var huge = 'data:image/' + 'a'.repeat(MAX_PHOTOS_PAYLOAD_BYTES) + ';base64,AAAA';
  var r2 = validatePhotosPayload([huge]);
  assert.strictEqual(r2.ok, false);
  assert.strictEqual(r2.code, 'PHOTOS_TOO_LARGE');
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


// -- patient_notes cap ----------------------------------------------------
// Added 2026-08-24. This field was previously unbounded on a fully
// unauthenticated endpoint, which is what made dnt_appointments' size
// constraint unsound no matter what number it carried.
var V2 = require('./dental-photo-validation.js');
var validatePatientNotes = V2.validatePatientNotes;
var MAX_NOTES = V2.MAX_PATIENT_NOTES_JSON_BYTES;

test('absent / null / empty notes are fine', () => {
  assert.strictEqual(validatePatientNotes(undefined).ok, true);
  assert.strictEqual(validatePatientNotes(null).ok, true);
  assert.strictEqual(validatePatientNotes('').ok, true);
});
test('a non-string notes value -> INVALID_NOTES', () => {
  var r = validatePatientNotes({ evil: true });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'INVALID_NOTES');
});
test('ordinary notes are accepted', () => {
  assert.strictEqual(validatePatientNotes('Chipped a molar on Saturday.').ok, true);
});
test('notes just at the byte ceiling -> ok', () => {
  // JSON.stringify adds two quote characters, so the raw string is MAX-2.
  assert.strictEqual(validatePatientNotes('n'.repeat(MAX_NOTES - 2)).ok, true);
});
test('notes just over the byte ceiling -> NOTES_TOO_LONG', () => {
  var r = validatePatientNotes('n'.repeat(MAX_NOTES - 1));
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'NOTES_TOO_LONG');
});
test('the cap is BYTES, not characters -- multi-byte text counts properly', () => {
  // Each emoji is 4 UTF-8 bytes. A character-based cap would let ~4x through.
  var emojiCount = Math.floor(MAX_NOTES / 4) + 10;
  var r = validatePatientNotes(String.fromCodePoint(0x1F9B7).repeat(emojiCount));
  assert.strictEqual(r.ok, false, 'multi-byte text must be measured in bytes');
  assert.strictEqual(r.code, 'NOTES_TOO_LONG');
});
test('JSON ESCAPE EXPANSION is counted -- control chars become 6 bytes each', () => {
  // A control character is ONE character but SIX bytes once JSON-encoded
  // (\u0001). A cap applied to raw string length would pass this and then
  // blow the storage bound the constraint is meant to guarantee.
  var n = Math.floor(MAX_NOTES / 6) + 10;
  var r = validatePatientNotes(String.fromCharCode(1).repeat(n));
  assert.strictEqual(r.ok, false, 'escape expansion must be counted');
  assert.strictEqual(r.code, 'NOTES_TOO_LONG');
  assert.ok(n < MAX_NOTES,
    'and the raw character count is well under the cap, which is the whole point');
});

// -- storage-ceiling drift check ------------------------------------------
// The DB constraint on public.dnt_appointments is DERIVED from the constants
// above (sql/sairndental_appointments_photo_size_migration.sql). If someone
// raises the photo budget and forgets the migration, real bookings start
// failing at the database with no code change to point at. This test is the
// tripwire: it fails the moment the two can no longer both be true.
var DB_CEILING_BYTES = 1291059;        // must match the migration exactly
var NON_PHOTO_ALLOWANCE = 32768;       // the migration's stated headroom

test('the DB ceiling still equals photo budget + the stated allowance', () => {
  assert.strictEqual(
    DB_CEILING_BYTES, MAX_PHOTOS_PAYLOAD_BYTES + NON_PHOTO_ALLOWANCE,
    'MAX_PHOTOS_PAYLOAD_BYTES changed without updating ' +
    'sql/sairndental_appointments_photo_size_migration.sql -- raise the ' +
    'constraint in the same change or bookings will fail at the database'
  );
});

test('a maximum-size appointment payload really fits under the DB ceiling', () => {
  // Build the largest payload the validators permit and measure it the way
  // octet_length(data::text) will. Not a recalculation of the estimate in the
  // migration -- an independent construction that must come out under it.
  var perPhoto = Math.floor(MAX_PHOTOS_PAYLOAD_BYTES / MAX_PHOTOS);
  var photos = [];
  for (var i = 0; i < MAX_PHOTOS; i++) {
    var len = (i === 0)
      ? MAX_PHOTOS_PAYLOAD_BYTES - perPhoto * (MAX_PHOTOS - 1)
      : perPhoto;
    photos.push('data:image/jpeg;base64,' + 'A'.repeat(len - 'data:image/jpeg;base64,'.length));
  }
  assert.strictEqual(validatePhotosPayload(photos).ok, true, 'the fixture must be legal');

  var notes = 'n'.repeat(MAX_NOTES - 2);
  assert.strictEqual(validatePatientNotes(notes).ok, true, 'the fixture must be legal');

  var appointmentData = {
    id: 'AP-' + 'x'.repeat(24), patient_id: 'PT-' + 'x'.repeat(24),
    provider_id: 'x'.repeat(64), operatory_id: 'x'.repeat(64),
    procedure_type_id: 'x'.repeat(64),
    start_time: '2026-08-24T12:00:00.000Z', end_time: '2026-08-24T12:30:00.000Z',
    status: 'Pending', source: 'self-scheduled',
    photos: photos, patient_notes: notes
  };
  var bytes = Buffer.byteLength(JSON.stringify(appointmentData), 'utf8');
  assert.ok(bytes <= DB_CEILING_BYTES,
    'worst-case payload is ' + bytes + ' bytes, over the ' + DB_CEILING_BYTES +
    '-byte DB ceiling -- the constraint would reject a legal booking');
  assert.ok(bytes > 65536,
    'sanity: the worst case must exceed the OLD 64KiB ceiling, or this ' +
    'migration was not needed and something is wrong with the fixture');
});

console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
