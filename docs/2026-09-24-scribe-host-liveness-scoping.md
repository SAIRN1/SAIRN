# SAIRNvet scribe: transcription-host LIVENESS check — scoped, deliberately not built

**2026-09-24 (Hank).** Michael approved a liveness check on the transcription
host and asked for it to be SCOPED FIRST — call pattern, render-path cost,
failure UX. This is that scoping, and its conclusion is a design plus a
deferral, for the same reason `api/sairnvet-transcribe.js` gives for its own
unwritten consent-ref verification: **no host exists, so liveness code written
today could never execute, and dormant code that has never run is not a
control — it is Guardian check 0d's subject.**

## The gap being scoped

`hostConfigured()` checks that `SAIRNVET_TRANSCRIBE_URL` is a non-empty
string. Nothing anywhere checks that the thing behind the URL ANSWERS. The
client preflight's own comment says `CONSENT_REF_REQUIRED` "proves the whole
chain" — and on the day a host is set, that becomes false in exactly one way:
the chain it proves is host-**configured** + licence-valid, not
host-**alive**. A configured-but-dead host walks a practice all the way to
"Available", the vet asks the client to consent to a recording, and the
transcription then fails — which is the consent-theatre failure the
2026-09-23 preflight correction exists to prevent, one rung higher.

## Call pattern — DECIDED: inside the existing preflight, server-side

The liveness probe belongs in `api/sairnvet-transcribe.js`, on the
**no-audio preflight path** (the POST with no `consent_ref`), between the
`hostConfigured()` check and the refusal that follows it:

- **Not a new client call.** `scribePreflight()` already makes exactly one
  request per panel open (`sairnvet.html:10209`), carries no audio and no
  consent reference by design, and its test locks the check ordering. The
  liveness question rides the call that already exists.
- **Not client→host direct.** The host URL is a server secret; shipping it to
  the browser to ping would publish the one thing the env var placement keeps
  private, and a browser CORS preflight against an ASR host is a new failure
  surface for zero gain.
- **Not a cron.** A practice opens the scribe panel when a visit starts; a
  five-minute-old "alive" from a cron is stale at exactly the moment it is
  read, and the panel's answer must be about NOW.
- **Probe shape:** `GET <host>/health` (or `HEAD <host>`, decided when a real
  host with a real health route is chosen — one more reason not to write it
  now), `AbortSignal.timeout(3000)`, **no audio, no body, no consent ref**.
  The probe must be as data-free as the preflight it rides.

## Render-path cost — BOUNDED: one host round-trip per panel open, never per render

- The preflight fires **once per panel open**, not per render and not per
  keystroke; adding the probe costs one host round-trip inside that single
  request, hard-capped by the 3s timeout.
- The RECORDING path is untouched. `scribeAsk()` refuses unless the preflight
  cleared, and the transcribe call itself already owns its failure ("The
  transcription host did not answer. No audio was retained."). Liveness is a
  gate on ASKING, not a wrapper on STREAMING.
- No caching. A per-instance memo would answer "it was alive for somebody
  else's panel earlier"; the whole point is the answer being about this
  practice's next five minutes. One bounded call is affordable; a wrong
  cached "alive" is not.

## Failure UX — a THIRD named refusal, because dead-but-configured is neither of the existing two

- New refusal code `TRANSCRIBE_HOST_UNREACHABLE`, distinct from
  `TRANSCRIBE_HOST_NOT_CONFIGURED`: *"The transcription host is configured
  but did not answer, so the scribe is off for this visit. Nothing was
  recorded. Dictation is unaffected."* Not-configured is a product absence;
  unreachable is an ops incident, and folding them makes a pager problem look
  like a pricing tier.
- The client preflight needs **no change**: its allowlist rule (only
  `CONSENT_REF_REQUIRED` enables the button; every other answer is a named
  refusal shown verbatim, could-not-tell stays off) already renders the new
  code correctly. That is the 2026-09-23 correction paying for itself.
- Timeout = refusal, never pass. "The host took >3s to say hello" and "the
  host is down" get the same answer, because the question is "should a client
  be asked to consent", not "is the host diagnosable".

## Why NOT built today, explicitly

1. **It could never run.** `hostConfigured()` is false in every environment;
   every line of liveness code would be dormant on arrival, and this file's
   own header names dormant never-run code as a non-control.
2. **The probe's shape depends on the host that does not exist** — health
   route, expected status, auth on the health endpoint. Writing it now means
   guessing, and a guessed health check is the string-anchor-that-never-
   matched shape (disciplines §8) at birth.
3. **The seam is already marked.** `hostConfigured()` is the single place the
   host is read, precisely so the day somebody sets the env var they land on
   the comment block. This document is now the second thing they land on.

## The trigger, so this is a plan and not a wish

On the day `SAIRNVET_TRANSCRIBE_URL` is set, the enabling change MUST land
three things together, and this document is the checklist: (1) consent-ref
verification against the stored `sv_scribe_consent` row (already required by
the endpoint's own header); (2) this liveness probe with
`TRANSCRIBE_HOST_UNREACHABLE`; (3) the probe's arms in
`api/sairnvet-transcribe.test.js`, including the ordering lock (host →
liveness → licence → consent) and a timeout-is-refusal arm. A host enabled
without all three re-opens the consent-theatre gap with a live microphone
behind it.
