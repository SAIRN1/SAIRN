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

// patient_notes was UNBOUNDED. public-book.js trims it and stores it, with no
// length check anywhere, on a fully unauthenticated endpoint. That mattered
// once dnt_appointments' size constraint was sized from these limits: a
// storage bound is only sound if every field it covers is itself bounded, and
// an uncapped free-text field made the total unbounded no matter what number
// the constraint carried.
//
// Measured in BYTES of the JSON-encoded value, not characters. A 2,000-
// character cap sounds equivalent and is not: one emoji is 4 UTF-8 bytes, and
// a control character becomes a 6-byte \uXXXX escape inside JSON, so 2,000
// characters can be 12,000 bytes on the wire. Counting the encoded length is
// the only measure the database constraint actually sees.
var MAX_PATIENT_NOTES_JSON_BYTES = 8192;

function jsonByteLength(s) {
  return Buffer.byteLength(JSON.stringify(String(s)), 'utf8');
}

function validatePatientNotes(notes) {
  if (notes === undefined || notes === null || notes === '') return { ok: true };
  if (typeof notes !== 'string') {
    return { ok: false, code: 'INVALID_NOTES', message: 'patient_notes must be a string' };
  }
  if (jsonByteLength(notes) > MAX_PATIENT_NOTES_JSON_BYTES) {
    return { ok: false, code: 'NOTES_TOO_LONG',
      message: 'Notes are too long -- please shorten them and try again' };
  }
  return { ok: true };
}

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
    // COUNT THE WHOLE DATA URL, not just the base64 capture group.
    //
    // The old version summed only m[1], the payload after "base64,". The
    // prefix was therefore uncounted -- and DATA_URL_RE permits an arbitrarily
    // long MIME subtype ([a-zA-Z0-9.+-]+), so "data:image/<2000 chars>;base64,"
    // passed validation and was stored. Three of those is unbounded growth in
    // a field the storage constraint has to bound. Tightening by ~23 bytes per
    // photo against a 1.2MB budget costs nothing real and closes the hole.
    totalBase64Len += entry.length;
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
  validatePatientNotes: validatePatientNotes,
  hasExifSegment: hasExifSegment,
  jsonByteLength: jsonByteLength,
  MAX_PHOTOS: MAX_PHOTOS,
  MAX_PHOTOS_PAYLOAD_BYTES: MAX_PHOTOS_PAYLOAD_BYTES,
  MAX_PATIENT_NOTES_JSON_BYTES: MAX_PATIENT_NOTES_JSON_BYTES
};
