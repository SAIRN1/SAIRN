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
