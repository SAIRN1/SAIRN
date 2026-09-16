// api/_lib/record-parity.js
// ---------------------------------------------------------------------------
// RAID-STYLE PARITY OVER APPEND-ONLY RECORDS -- item 46.
//
// Item 35 gave this platform a hash chain over the audit logs. A hash chain
// DETECTS: it can tell you that row 412 is not what it was, and it can tell you
// when the divergence began. It cannot tell you what row 412 SAID. On
// `sv_controlled` -- SAIRNvet's controlled-substance register, Tier A, DEA-
// relevant, append-only, with no removal path -- that is the difference between
// knowing a record is gone and having it back.
//
// This is the correction half. For each GROUP of records it stores one parity
// block; lose or corrupt ANY ONE record in that group and its exact bytes are
// reconstructible from the survivors plus the parity, WITHOUT re-reading the
// original.
//
// ══ WHY IT CLEARLY EXCEEDS A BARE HASH, WHICH IT HAS TO EARN ════════════════
//   a hash of row 412         -> "row 412 is wrong"           (detect)
//   a hash chain over 1..500  -> "row 412 is wrong, and the
//                                divergence starts there"      (detect + locate)
//   parity over a group       -> "row 412 said EXACTLY THIS"   (correct)
//
// And it composes rather than competing: the hash is what tells you WHICH row to
// reconstruct, and it is what verifies the reconstruction afterwards. Parity
// without a digest would hand you bytes you could not check. Every group here
// therefore carries both, and `recover()` REFUSES to return a reconstruction
// whose digest does not match the one recorded for that record.
//
// ══ WHAT IT DOES NOT DO, STATED BEFORE THE API ══════════════════════════════
//
//   * IT RECOVERS ONE RECORD PER GROUP, NOT TWO. Single-parity XOR is exactly
//     RAID 4/5: one erasure per stripe. Lose two rows in a group and the group
//     is unrecoverable, and `recover()` says so rather than returning something
//     plausible. Two-erasure tolerance needs Reed-Solomon over GF(256), which is
//     a different and much larger piece of work, and pretending single parity
//     covers it would be the worst kind of overclaim on a DEA register.
//
//   * IT DOES NOT PROTECT AGAINST LOSING THE TABLE. Parity stored beside the
//     rows dies with them. This platform currently takes NO automated database
//     backups (Supabase free tier, confirmed 2026-09-14), so the realistic
//     threat this addresses is a CORRUPTED OR DELETED ROW, not a lost database.
//     Saying otherwise would let somebody read this as the backup they do not
//     have.
//
//   * IT DOES NOT CLOSE THE CREATION-TIME EXPOSURE WINDOW, IT NARROWS IT.
//     Computing parity needs the record's plaintext bytes at the moment it is
//     written -- there is no way around that, and any claim to the contrary would
//     be false. What it removes is the need to read the plaintext AGAIN later:
//     recovery runs on parity plus the other records, so a restore does not
//     require re-reading, re-exporting or re-handling the sensitive original. The
//     window is one write, not one write plus every future recovery.
//
//   * IT IS NOT ENCRYPTION. Parity of plaintext records is not confidential --
//     XOR of several records leaks structure, and with a group of one it IS the
//     record. `groupSize` is therefore required to be >= 2 and the reason is in
//     the refusal message.
// ---------------------------------------------------------------------------

'use strict';

const crypto = require('crypto');

const PARITY_VERSION = 1;
const MIN_GROUP = 2;

class ParityError extends Error {
  constructor(message, code) {
    super(message);
    this.name = 'ParityError';
    this.code = code || 'PARITY_INVALID';
  }
}

// ── THE CANONICAL FORM IS THE WHOLE THING, AGAIN ────────────────────────────
// Reused in spirit from api/sv-witness.js, which already learned this: two JSON
// encodings of one record must produce the same bytes or a reconstruction will
// be byte-different from an identical record and fail its own digest check.
// Keys sorted recursively, nothing else normalised -- no trimming, no case
// folding, no dropping of nulls. A record differing only in whitespace inside a
// STRING is a different record, and deciding otherwise here would be this file
// quietly editing a controlled-substance entry.
function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  return '{' + Object.keys(value).sort()
    .map((k) => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
}

function bytesOf(record) {
  if (record === undefined) {
    throw new ParityError('a record is required', 'PARITY_NO_RECORD');
  }
  return Buffer.from(canonical(record), 'utf8');
}

function digestOf(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

// ── LENGTH IS PART OF THE PROBLEM, NOT A DETAIL ─────────────────────────────
// XOR over variable-length records loses the lengths, and without them a
// reconstruction cannot be trimmed back to the original. RAID solves this with
// fixed-width stripes; here each record's LENGTH is stored alongside its digest,
// so the parity block is padded to the longest member and the recovered buffer
// is cut to the recorded length. Storing the length is not a leak worth worrying
// about next to storing the digest, and it is what makes recovery exact rather
// than approximate.
function xorInto(target, src) {
  for (let i = 0; i < src.length; i += 1) {
    target[i] = target[i] ^ src[i];
  }
  return target;
}

/**
 * Build a parity group. Returns the block to store.
 *
 * @param {Array<{id:string, record:object}>} members
 * @returns {{version, group_id, width, parity_b64, members:[{id,length,digest}]}}
 */
function buildGroup(groupId, members) {
  if (!groupId || typeof groupId !== 'string') {
    throw new ParityError('a group id is required', 'PARITY_NO_GROUP_ID');
  }
  if (!Array.isArray(members) || members.length < MIN_GROUP) {
    throw new ParityError(
      'a parity group needs at least ' + MIN_GROUP + ' records. WITH ONE MEMBER '
      + 'THE PARITY BLOCK *IS* THE RECORD, so a group of one would store a '
      + 'second plaintext copy of a controlled-substance entry and call it '
      + 'redundancy.', 'PARITY_GROUP_TOO_SMALL');
  }
  const seen = new Set();
  const encoded = members.map((m) => {
    if (!m || typeof m.id !== 'string' || !m.id) {
      throw new ParityError('every member needs a string id', 'PARITY_NO_ID');
    }
    if (seen.has(m.id)) {
      // Two members with one id makes recovery ambiguous: the survivor set
      // cannot be identified, so the XOR would silently include the wrong row.
      throw new ParityError('duplicate member id in group: ' + m.id,
                            'PARITY_DUPLICATE_ID');
    }
    seen.add(m.id);
    const buf = bytesOf(m.record);
    return { id: m.id, buf: buf, length: buf.length, digest: digestOf(buf) };
  });
  const width = encoded.reduce((w, e) => Math.max(w, e.length), 0);
  const parity = Buffer.alloc(width, 0);
  encoded.forEach((e) => {
    // Padded to the group width so a short record does not corrupt the tail.
    const padded = Buffer.alloc(width, 0);
    e.buf.copy(padded);
    xorInto(parity, padded);
  });
  return {
    version: PARITY_VERSION,
    group_id: groupId,
    width: width,
    parity_b64: parity.toString('base64'),
    members: encoded.map((e) => ({ id: e.id, length: e.length, digest: e.digest }))
  };
}

/**
 * Reconstruct ONE missing member from the parity block and the survivors.
 *
 * @param {object} group      the block from buildGroup
 * @param {string} missingId
 * @param {Array<{id, record}>} survivors  every OTHER member, still readable
 * @returns {{ok:true, record, bytes}|{ok:false, code, reason}}
 *
 * A RESULT OBJECT, not a throw, for the recovery path specifically: a failed
 * recovery on a DEA-relevant register is a situation somebody must read and act
 * on, not an exception to bubble. Programming errors (a malformed group, a bad
 * argument) still throw.
 */
function recover(group, missingId, survivors) {
  if (!group || group.version !== PARITY_VERSION) {
    throw new ParityError('unknown parity block version: '
                          + (group && group.version), 'PARITY_BAD_VERSION');
  }
  const known = group.members.find((m) => m.id === missingId);
  if (!known) {
    return { ok: false, code: 'PARITY_NOT_IN_GROUP',
             reason: missingId + ' is not a member of group ' + group.group_id };
  }
  const need = group.members.filter((m) => m.id !== missingId).map((m) => m.id);
  const have = new Set((survivors || []).map((s) => s && s.id));
  const absent = need.filter((id) => !have.has(id));
  if (absent.length) {
    // ── THE ONE-ERASURE LIMIT, REPORTED RATHER THAN APPROXIMATED ───────────
    // Single-parity XOR recovers exactly one erasure per group. With two gone
    // the equation is underdetermined, and an implementation that returned
    // *something* here would be handing back bytes that pass no check and look
    // like a record.
    return { ok: false, code: 'PARITY_TOO_MANY_MISSING',
             reason: 'single parity recovers ONE record per group. Also missing: '
                     + absent.join(', ') + '. This group is unrecoverable, and '
                     + 'that is a real limit rather than a failure to try harder '
                     + '-- two erasures need Reed-Solomon, not this.' };
  }
  const parity = Buffer.from(group.parity_b64, 'base64');
  if (parity.length !== group.width) {
    throw new ParityError('parity block width disagrees with its own header',
                          'PARITY_CORRUPT_BLOCK');
  }
  const acc = Buffer.from(parity);
  for (const s of survivors) {
    if (!need.includes(s.id)) continue;            // ignore extras
    const buf = bytesOf(s.record);
    const rec = group.members.find((m) => m.id === s.id);
    // A SURVIVOR THAT HAS ITSELF CHANGED POISONS THE RECOVERY SILENTLY. Its
    // digest is already recorded, so this is checkable -- and checking it is the
    // difference between reconstructing row 412 and reconstructing nonsense that
    // happens to XOR correctly.
    if (digestOf(buf) !== rec.digest) {
      return { ok: false, code: 'PARITY_SURVIVOR_CHANGED',
               reason: 'survivor ' + s.id + ' no longer matches the digest '
                       + 'recorded when the group was built, so it cannot be '
                       + 'used to reconstruct another record. Recover ' + s.id
                       + ' first, or treat this group as unrecoverable.' };
    }
    const padded = Buffer.alloc(group.width, 0);
    buf.copy(padded);
    xorInto(acc, padded);
  }
  const bytes = acc.slice(0, known.length);
  if (digestOf(bytes) !== known.digest) {
    // The reconstruction is REFUSED rather than returned with a warning. On an
    // append-only register a wrong row cannot be taken back: a correction is a
    // SECOND row and the wrong one stands forever.
    return { ok: false, code: 'PARITY_DIGEST_MISMATCH',
             reason: 'the reconstruction does not match the digest recorded for '
                     + missingId, expected: known.digest, got: digestOf(bytes) };
  }
  let record;
  try {
    record = JSON.parse(bytes.toString('utf8'));
  } catch (e) {
    return { ok: false, code: 'PARITY_UNPARSEABLE',
             reason: 'recovered bytes matched the digest but are not JSON: '
                     + (e && e.message) };
  }
  return { ok: true, record: record, bytes: bytes };
}

/**
 * Which members of a group no longer match their recorded digest.
 * The DETECT half, kept here so a caller does not have to reimplement it to
 * find out what to recover.
 */
function verifyGroup(group, present) {
  if (!group || group.version !== PARITY_VERSION) {
    throw new ParityError('unknown parity block version', 'PARITY_BAD_VERSION');
  }
  const byId = new Map((present || []).map((p) => [p && p.id, p]));
  const changed = [], missing = [], intact = [];
  group.members.forEach((m) => {
    const p = byId.get(m.id);
    if (!p) { missing.push(m.id); return; }
    (digestOf(bytesOf(p.record)) === m.digest ? intact : changed).push(m.id);
  });
  return { intact: intact, changed: changed, missing: missing,
           recoverable: (changed.length + missing.length) === 1 };
}

module.exports = {
  buildGroup, recover, verifyGroup, canonical, digestOf,
  ParityError, PARITY_VERSION, MIN_GROUP
};
