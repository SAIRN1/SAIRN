# SAIRNvet ambient scribe — transcription-host LIVENESS check, scoping

**Status: SCOPED, NOT BUILT.** Michael approved the work and asked for the
shape first — call pattern, render-path cost, failure UX — because this is a
real latency and cost tradeoff rather than a one-line correction.

**Written 2026-09-23 (Hank).** Follows the preflight fix in the same session
and the review that found it (`tests/sairnvet_scribe_review_probe.js`).

---

## 1. What is already closed, and what is not

`scribePreflight()` used to decide availability by the ABSENCE of one failure
code. It now decides POSITIVELY from `CONSENT_REF_REQUIRED` — the only code
that proves host configured **and** licence valid **and** licence belongs to
this app, because `api/sairnvet-transcribe.js` checks those three in that
order.

**That closed the licence half. It did not close the liveness half**, and arm
`A1d` of the review probe measures the gap rather than implying it away:

> The preflight is answered **locally**. `api/sairnvet-transcribe.js` refuses
> at the consent check and never contacts `SAIRNVET_TRANSCRIBE_URL`, so a host
> that is configured and **unreachable** answers exactly like a healthy one.

So the status line means *configured and licensed*, not *working*. A vet can
still be shown an enabled button, ask a client to consent, and discover on the
first real POST that there was nowhere to send the audio — which is the harm
the module's own header calls consent theatre.

---

## 2. THE BLOCKING DEPENDENCY, stated first because it changes the plan

**A liveness check needs something cheap to call, and no transcription host
has been chosen.** Probing by sending the transcribe route a token request
would cost GPU time on a self-hosted model and could enter a bogus job in its
queue — a probe with a side effect is not a probe.

So the real deliverable today is a **contract requirement carried into the
host decision**:

> The transcription host MUST expose a cheap, side-effect-free health path —
> `GET /health` or an `OPTIONS` on the transcribe route — answering in well
> under a second, and answering **only** when it can actually accept audio.
> A health path that returns 200 from a front proxy while the model is
> unloaded is worse than none: it converts an honest failure into a
> confident wrong answer.

Until a host exists, **nothing here should be built**. Writing a probe against
an imagined health path means shipping a second thing that has never executed,
which is the state section 9 of the consent scoping doc already discloses for
the capture path and the CHECK constraint. One of those is a disclosure. Three
is a pattern.

---

## 3. Call pattern — four options, and why one wins

### A. Probe on every panel render (inside the existing preflight)

The obvious reading of "ping the host on panel render".

- **Render-path cost:** every paint of the SOAP panel adds an outbound request
  to a third host, **serialised behind** the existing one — browser → Vercel →
  transcription host. Two hops before the status line resolves.
- **Frequency:** every render. A busy practice paints this panel hundreds of
  times a day for a feature used a handful of times.
- **Failure mode:** a slow host makes the *panel* feel broken, not the scribe.
- **Verdict: rejected.** It puts the cost on the common path and the benefit
  on the rare one.

### B. Probe on render, with a short-TTL cache in the endpoint

- **Cost:** one probe per TTL window per warm instance.
- **Why it does not work here:** Vercel functions are ephemeral and
  horizontally scaled. "Per instance" is not a cache anybody can reason about
  — under load it degrades to option A, and on a long-lived instance it pins a
  **stale verdict**, which is the failure this whole exercise is about. A
  cached liveness flag is a fact with a tense, and this platform has a rule
  about those.
- **Verdict: rejected.** It trades a real cost for an unreliable answer.

### C. Probe at the ASK — when the vet presses “Start — ask the client”, before the consent modal opens ✅

- **Render-path cost: ZERO.** The panel status line keeps its current meaning
  and its current wording.
- **Frequency:** once per scribe session. A few per practice per day.
- **Latency lands where a wait is expected** — on a button the user just
  pressed, where a brief “checking the transcription host…” is ordinary UX.
- **It is where the harm is.** The harm is *asking a client to consent to a
  recording that cannot happen*. That harm occurs at the ask, so the check
  belongs immediately before the ask and nowhere else.
- **Verdict: this is the shape.**

### D. Probe after consent, before recording

Rejected on its own: the client has already been asked, which is the harm.
**But see §5 — it is needed IN ADDITION to C, not instead of it.**

### E. No probe; let the first real POST fail and recover

Rejected on the module's own terms: it means holding captured audio with
nowhere to send it, which is what the design refuses.

---

## 4. Shape of the call

Reuse the existing endpoint rather than adding a second one — one route, one
auth path, one set of structured refusals:

```
POST /api/sairnvet-transcribe   { app_id: 'sairnvet', probe: true }
```

- The existing order is preserved: method → host configured → licence →
  **then** the probe, so a probe still never runs on an unlicensed call.
- A **new positive code** is returned when the host answers:
  `HOST_READY`. The client's rule stays what it now is — decide from the
  positive code, never from the absence of a negative one.
- A **new refusal** when it does not: `TRANSCRIBE_HOST_UNREACHABLE`, 503.
  `UPSTREAM_UNAVAILABLE` already exists and already means "the host did not
  answer"; whether to reuse it or add a distinct code is a small decision for
  whoever builds it, and the argument for a distinct one is that a probe
  failure and a transcription failure land in different places in the UI.
- **Hard timeout, server side, 2 seconds.** A host that cannot answer a health
  path in 2s cannot stream audio either. Timeout is treated as unreachable —
  never as unknown-therefore-fine.
- **Nothing from the request is interpolated into the refusal**, per the rule
  the file already follows for a stronger reason than usual.

`scribePreflight()` is left alone. Its job stays "is this practice configured
and licensed", which is what the status line says.

---

## 5. The staleness window nobody would notice

**Probing at the ask is not sufficient on its own**, and this is the part most
likely to be missed:

```
probe ✅ → open consent modal → vet reads the statement aloud → client answers → scribeStart()
```

Reading the consent statement takes **30–90 seconds**. A probe that passed
before the modal opened is that stale when audio actually starts.

**Recommendation: probe at BOTH points** — before the ask (C) and again
immediately before `scribeStart()` (D).

The second probe is cheap (one request, once per session) and it does **not**
re-create the harm C prevents: by then consent has been asked and **recorded**,
and a failure at that point means the vet is told *"the host stopped
responding between asking and starting — nothing was recorded"*. A recorded
consent with no recording is an honest, harmless outcome. An unrecorded
consent with a recording is not, and neither is a recording with nowhere to go.

---

## 6. Failure UX — four states that must not collapse into one

The endpoint's whole design is that **"could not transcribe" is the sentence
that makes a configuration error and a consent error look identical to
whoever is holding the tablet.** The same discipline applies here.

| State | Where it shows | Wording |
|---|---|---|
| Not configured | panel status, unchanged | *“Not available on this practice yet.”* + the endpoint's message |
| Configured, licence invalid | panel status, unchanged | the endpoint's own structured message |
| **Configured + licensed, host unreachable** | **NEW — instead of opening the consent modal** | *“The transcription host is not responding, so the scribe cannot run right now. **Nothing was recorded and the client was not asked.** Dictation is available as usual.”* |
| Our own endpoint unreachable | panel status, unchanged | fail closed, as today |

Three things this wording is doing on purpose:

1. **“the client was not asked”** — the vet needs to know no consent
   conversation started, or they will not know whether to explain something to
   the client.
2. **It does not read as a transient glitch.** If it says *“try again”*, the
   vet presses twice and then records anyway on a dead host. It names the
   state and offers the alternative that works.
3. **It offers dictation inline**, because push-to-talk is genuinely
   unaffected and a refusal that does not say so reads as “the software is
   broken”.

**Open decision for Michael:** should a probe failure be *silent-and-blocking*
(the button simply refuses with that message) or should it *offer dictation as
a button right there*? Recommendation: the second — a refusal that hands the
user the working path is the difference between a gate and a dead end.

---

## 7. What must NOT be built

- **A background poller** keeping a liveness flag warm. It reintroduces
  staleness while adding continuous cost, and the failure it hides — host died
  since the last poll — is exactly the one this exists to catch.
- **A probe that sends real audio.** Cost, and a bogus job in the host's queue.
- **A health check that answers from a proxy** rather than from the thing that
  loads the model. See §2: a confident wrong answer is worse than none.
- **Caching the probe result across the consent ask.** See §5.

---

## 8. Cost, plainly

Under the recommended shape: **two outbound requests per scribe session**, on
a feature used a few times per practice per day. Nothing on the render path.

Under the rejected option A: one per panel paint — hundreds per day — for the
same benefit.

---

## 9. What is UNVERIFIED here, and it is most of it

- **No transcription host exists**, so nothing in this document has been
  driven against one. Every latency figure is a design budget, not a
  measurement.
- **The 2-second timeout is a judgement**, not a measured threshold. It should
  be re-derived against the real host's health path once one exists.
- **The capture path has still never run in a real browser** — the disclosure
  section 9 of the consent scoping doc already carries, unchanged by this.
- **§5's 30–90 second estimate** for reading the consent statement is a
  reasonable reading of the statement's length, not an observation of anyone
  doing it.

---

## 10. Recommended order, when a host is chosen

1. Get the health-path guarantee into the host decision (§2). **Blocking.**
2. Add `probe: true` and the two codes to `api/sairnvet-transcribe.js`, with
   the 2s timeout and arms that drive both a healthy and a dead host.
3. Wire `scribeAsk()` to probe before opening the modal (§3C).
4. Wire `scribeClientAnswer()` to re-probe before `scribeStart()` (§5).
5. The failure UX of §6, with Michael's call on the open question.
6. Extend `tests/sairnvet_scribe_review_probe.js` arm A1d from *measuring the
   gap* to *asserting it is closed*.
