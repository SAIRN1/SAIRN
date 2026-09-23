// api/sairnvet-transcribe.js
// ---------------------------------------------------------------------------
// THE AMBIENT-SCRIBE TRANSCRIPTION CONTRACT. IT REFUSES EVERY REQUEST TODAY,
// AND THAT IS THE FEATURE.
//
// docs/2026-09-23-sairnvet-ambient-scribe-consent-scoping.md 6.2 recorded
// Michael's decision: transcription runs on a SELF-HOSTED model. Not Chrome's
// `SpeechRecognition` (which ships exam-room audio to a Google service), and
// not a paid third-party ASR. That decision has a consequence the document
// names rather than leaves to be discovered:
//
//     THE MODEL HOST DOES NOT EXIST YET, SO THE FEATURE MUST FAIL CLOSED.
//     It must refuse to capture and say why. It must NOT fall back to
//     SpeechRecognition "just for now", because a temporary fallback to the
//     exact vendor the decision rejects is how the decision gets reversed
//     without anybody deciding it.
//
// So this file is the endpoint's shape, written now so the client can be built
// against a real contract, and wired to refuse until `SAIRNVET_TRANSCRIBE_URL`
// names a host. There is no fallback branch in this file. There is no vendor
// name in this file. Grep it for one.
//
// ── WHY AN UNCONFIGURED ENDPOINT IS BETTER THAN NO ENDPOINT ────────────────
// api/greeting.js exists because sairnscape.html called a path that had never
// been written: 404, client reads `undefined`, nothing says so, and nobody
// noticed for the life of the feature. A missing endpoint fails SILENTLY. This
// one answers 503 with a code and a sentence, so the client can tell the vet
// "the scribe is not available on this practice yet" instead of showing a
// spinner that never resolves.
//
// ── THE ORDER OF THE CHECKS IS A PRIVACY PROPERTY, NOT TIDINESS ────────────
// The host check runs FIRST, before the licence, before the consent reference,
// before the body is touched at all. With no host configured there is no
// lawful destination for exam-room audio, so this process must never hold any.
// Checking the licence first would be more conventional and would mean parsing
// a request body full of a client's voice in order to reject it.
//
// ── WHAT THIS ENDPOINT MUST NEVER DO, STATED SO A LATER EDIT HAS TO ARGUE ──
//   * No audio to disk. No temp file, no cache, no `/tmp`.
//   * No audio to a log. `console.log(req.body)` here would write a client's
//     voice into a log retention this document never promised. 5's
//     discard-by-default is a property of TWO places now, not one -- 6.2
//     item 2 says exactly that, and the server is the second place.
//   * No echo of `audio` in any response, including an error response.
//   * No third-party call. Ever. That is the whole decision.
//
// ── THE CONSENT REFERENCE IS REQUIRED AND IS *NOT* VERIFIED HERE, WHICH IS
//    A GAP AND IS WRITTEN DOWN AS ONE ───────────────────────────────────────
// `consent_ref` must be present or this refuses. That stops the endpoint being
// used for audio with no recorded consent at all. IT DOES NOT PROVE CONSENT:
// a present string is a claim the CALLER makes, and api/_lib/biometric-consent.js
// already states the rule this platform works to -- a module that lets a caller
// assert `consent: true` as a flag is a module that would manufacture consent
// the first time somebody hit a deadline.
//
// Verifying the ref against the stored `sv_scribe_consent` row is therefore
// REQUIRED BEFORE THIS ENDPOINT IS EVER ENABLED, and it is deliberately not
// written today: with no host, that code could never execute, and dormant code
// that has never run is not a control -- it is Guardian check 0d's subject.
// `hostConfigured()` is the single place the host is read, so the day somebody
// sets `SAIRNVET_TRANSCRIBE_URL` they land on this comment.
// ---------------------------------------------------------------------------

'use strict';

const { validateLicenseKey } = require('./_lib/license');

// The one place the host is read. See the comment block above before changing
// what this returns: enabling the host without server-side consent
// verification is the failure this file is shaped to prevent.
//
// ── FOR ANYONE RUNNING GUARDIAN CHECK 30 (env-var name drift) ─────────────
// `SAIRNVET_TRANSCRIBE_URL` IS DELIBERATELY NOT SET IN VERCEL, and that is not
// the drift this check hunts. Check 30's incident was a MISNAMED variable
// reading as undefined and being reported as a missing secret, so the symptom
// pointed at infrastructure while the cause was a typo. Here the absence is
// the intended state and the report says so in words -- "this platform has no
// transcription host configured", not a 500 and not "missing secret". It
// becomes a two-place change on the day a host is chosen, and the second place
// is the Vercel project.
function hostConfigured() {
  const url = process.env.SAIRNVET_TRANSCRIBE_URL;
  return typeof url === 'string' && url.trim() !== '';
}

// Structured refusals. Every one names WHICH thing is missing, because "could
// not transcribe" is the sentence that makes a configuration error and a
// consent error look identical to whoever is holding the tablet.
const REFUSALS = {
  METHOD_NOT_ALLOWED: {
    status: 405,
    message: 'POST only.'
  },
  TRANSCRIBE_HOST_NOT_CONFIGURED: {
    status: 503,
    message:
      'The ambient scribe is not available: this platform has no transcription host configured. ' +
      'SAIRNvet transcribes on a self-hosted model by decision (2026-09-23) and will NOT fall back ' +
      'to a browser or third-party speech service, so there is no degraded mode to offer. ' +
      'Push-to-talk dictation is unaffected and remains available.'
  },
  LICENSE_REQUIRED: {
    status: 401,
    message: 'Send the practice licence key as an Authorization: Bearer header.'
  },
  LICENSE_INVALID: {
    status: 403,
    message: 'That licence key is not valid or is not active.'
  },
  LICENSE_WRONG_APP: {
    status: 403,
    message: 'That licence key belongs to a different SAIRN application.'
  },
  CONSENT_REF_REQUIRED: {
    status: 400,
    message:
      'No consent reference was sent. Exam-room audio is transcribed only against a recorded ' +
      'per-visit consent event; a request without one is refused rather than queued.'
  },
  AUDIO_REQUIRED: {
    status: 400,
    message: 'No audio was sent.'
  },
  UPSTREAM_UNAVAILABLE: {
    status: 502,
    message: 'The transcription host did not answer. No audio was retained.'
  }
};

function refuse(res, code) {
  const r = REFUSALS[code];
  // NOTHING FROM THE REQUEST IS INTERPOLATED INTO A REFUSAL. Same property
  // api/greeting.js carries and for a stronger reason here: the request body
  // is a recording of a person who is not the caller.
  return res.status(r.status).json({ ok: false, error: { code: code, message: r.message } });
}

async function handler(req, res) {
  if (req.method !== 'POST') return refuse(res, 'METHOD_NOT_ALLOWED');

  // FIRST, AND DELIBERATELY BEFORE EVERYTHING ELSE. See the header: with no
  // host there is no lawful destination for this audio, so this process must
  // not hold any of it even long enough to validate a licence.
  if (!hostConfigured()) return refuse(res, 'TRANSCRIBE_HOST_NOT_CONFIGURED');

  const authz = String((req.headers && req.headers.authorization) || '');
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : '';
  if (!licenseKey) return refuse(res, 'LICENSE_REQUIRED');

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (e) {
    // A lookup that COULD NOT RUN is not a pass. CLAUDE.md states this as the
    // most common defect shape on this platform: "could not tell" is a third
    // state and is never folded into "allowed".
    return refuse(res, 'UPSTREAM_UNAVAILABLE');
  }
  if (!lic || !lic.valid || !lic.active) return refuse(res, 'LICENSE_INVALID');
  // app_id is read IF PRESENT. A licence row without one is not evidence of
  // anything either way, so it is not treated as a refusal -- the same
  // absent-means-unknown rule api/_lib/license.js applies to its own columns.
  if (lic.app_id && lic.app_id !== 'sairnvet') return refuse(res, 'LICENSE_WRONG_APP');

  const body = (req.body && typeof req.body === 'object') ? req.body : {};

  const consentRef = typeof body.consent_ref === 'string' ? body.consent_ref.trim() : '';
  if (!consentRef) return refuse(res, 'CONSENT_REF_REQUIRED');

  if (!body.audio) return refuse(res, 'AUDIO_REQUIRED');

  // UNREACHABLE TODAY BY CONSTRUCTION, and left as a refusal rather than as a
  // half-written client. `hostConfigured()` is false in every environment, so
  // execution never arrives here. When it can, the work is: verify
  // `consentRef` against the stored sv_scribe_consent row (see the header),
  // stream the audio to the host, return the transcript, and hold nothing.
  return refuse(res, 'UPSTREAM_UNAVAILABLE');
}

module.exports = handler;
module.exports.hostConfigured = hostConfigured;
module.exports.REFUSALS = REFUSALS;
