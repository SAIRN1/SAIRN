# SAIRNvet ambient scribe — consent and UI scoping

**2026-09-23 (Fourth).** **§6.1 and §6.2 are now DECIDED (Michael, 2026-09-23). §6.3 and §6.4
remain open and do not block the build. NOTHING IS BUILT YET — §8 stands exactly as written.**
The build was claimed (`fourth`, `sairnvet-scribe-build`, 2026-09-23T09:40:21Z) and blocked six
minutes later by `cody`'s `audit-wave3` claim on the same app. It is waiting on a decision about
who runs it, not on any remaining scoping question. The instruction was explicit: an ambient scribe
auto-transcribing a live vet–client conversation has real consent implications,
so the consent and UI flow is scoped *before* the transcription logic, and the
capture is not built silently.

**THE ONE-LINE FINDING: the feature is not "dictation, but continuous". It adds
a SECOND HUMAN to the recording who has not agreed to be recorded, and that is
the whole difference.** Everything below follows from that.

---

## 1. What SAIRNvet already has, and why it is not this

`sairnvet.html:9591` already ships voice input, and its own header states the
scope:

> *browser-native SpeechRecognition, zero new vendor/cost. Wired to the AI
> Assistant question field and SOAP Notes' Subjective/Objective fields — SOAP
> generation is this app's highest-value quick-entry moment: a vet examining an
> animal, hands occupied, dictating findings…*

That is **push-to-talk dictation by one speaker into a named field**. The vet
starts it, the vet speaks, the vet stops it. There is no second party, nothing
runs unattended, and the only voice captured belongs to the person who pressed
the button.

**An ambient scribe inverts all four.** It runs continuously, captures whoever
is in the room, is not addressed to a field, and the person whose words are most
legally sensitive — the client — never touched the control. Treating the
existing dictation as precedent for it would be the same
byte-identical-is-not-safe-in-context error this platform records as the seventh
cross-domain discipline.

`navigator.mediaDevices.getUserMedia` appears once in the app today
(`:9410`) and it is **camera only**, `facingMode:'environment'`, for photo
capture. **There is no audio capture in SAIRNvet at all.** This feature would be
the first, which is the right moment to decide the rules.

---

## 2. The legal constraint, and the naive version of it is the wrong one

### 2.1 Sources, retrieved 2026-09-23

Per §8 of `docs/2026-09-17-sairnfreedom-tips-tax-treatment.md`, these are **web
pages, not hashed files**, and that is stated rather than glossed.

| Source | Retrieved from |
|---|---|
| Reporters Committee for Freedom of the Press, *Reporter's Recording Guide* — in-person conversations | `rcfp.org/reporters-recording-sections/in-person-conversations/` |
| Justia, *Recording Phone Calls and Conversations — 50-State Survey* | `justia.com/50-state-surveys/recording-phone-calls-and-conversations/` |

### 2.2 The trap

Federal law requires **one** party's consent. States may be stricter, and the
commonly-cited list of all-party states — California, Delaware, Florida,
Illinois, Maryland, Massachusetts, Michigan, Montana, New Hampshire,
Pennsylvania, Washington — **is a list about PHONE CALLS.**

**An exam room is an IN-PERSON conversation, and the split states split the
other way.** Retrieved from RCFP's in-person section:

- **Missouri** requires **all-party** consent for private in-person
  conversations, and only one party for phone. It is **not** in the usual
  eleven.
- **Connecticut** and **Nevada** are the reverse — all-party for phone, **one**
  party in person. Building the room gate from the phone list would impose a
  rule Connecticut does not have and **miss Missouri entirely.**

**So the list this feature needs is not the list everybody quotes.** Getting it
backwards is a one-line mistake with a criminal-liability tail.

### 2.3 And the ground moved

RCFP records that **Oregon's all-party in-person requirement was struck down as
unconstitutional in July 2023**, with recording of *public* conversations now
broadly permitted. **A veterinary exam room is not a public conversation**, so
whether that ruling reaches this use is genuinely unsettled and is **not
resolved here** — see §7. It is named because a scoping document written from a
pre-2023 list would encode a rule a court has since touched, which is precisely
the failure `docs/2026-09-17-sairnfreedom-tips-tax-treatment.md` was written
about.

---

## 3. The design decision this makes for us

**THE APP CANNOT KNOW WHICH STATE'S LAW APPLIES, AND SHOULD NOT TRY.** A
practice's licence key carries no verified jurisdiction, a mobile ambulatory vet
crosses state lines in a working day, and a per-state branch would be a
compliance claim the platform cannot stand behind.

**So: ALL-PARTY CONSENT EVERYWHERE, EVERY VISIT, NO STATE BRANCH.** Ask the
client, in the room, before capture starts, every time.

This is not caution for its own sake — it is the **cheaper** design:

- It is correct in every state, including the ones the naive list gets wrong.
- It removes the need to know, store or update fifty jurisdictions' rules.
- It turns §2's research from a **branch** (which must stay current or silently
  become wrong) into a **disclosure** (which does not).
- It survives the Oregon question unresolved, because all-party is stricter than
  either reading.

**The cost is real and is stated: some visits will not be recorded.** That is
the correct outcome, not a gap to engineer around.

---

## 4. The consent and UI flow, as scoped

### 4.1 Before anything is captured

1. **Per-visit, not per-practice.** Consent is asked at the start of each
   appointment. A practice-level setting may *disable* the feature entirely, but
   **must not** be able to pre-consent on a client's behalf.
2. **The vet cannot consent for the client.** Two distinct affirmations: the
   vet enables the feature, and the **client** agrees. A single button pressed
   by staff is not consent and must not be built as one.
3. **Refusal is one tap and costs nothing.** Declining returns the vet to the
   existing push-to-talk dictation, which is unchanged and always available. The
   feature must never be the only path to a SOAP note.
4. **The ask is in plain words**, naming: that audio is captured, that it is
   processed to draft a clinical note, how long the audio is kept (§5), and that
   they may decline or stop it at any time.

### 4.2 While capturing

5. **A visible indicator that cannot be dismissed or minimised**, present the
   whole time, readable from the client's side of the table — not a small dot in
   a corner of the vet's screen.
6. **STOP is always one tap, from the main view**, never behind a menu.
7. **No background capture, ever.** If the app is backgrounded, the tab loses
   focus, or the screen locks, capture STOPS and the vet is told it stopped.
   *Resuming requires the client to be asked again* — a recorder that quietly
   restarts is the failure mode this whole document exists to prevent.

### 4.3 After

8. **The draft is a DRAFT.** Nothing reaches `sv_soapnotes` without the vet
   reading and accepting it. `sv_soapnotes` is **Tier A on both axes** — *"a
   clinical record is lost or wrong, and treatment is given on it"* — and an
   auto-filled clinical record nobody read is the fabrication class this
   platform already polices.
9. **The note records HOW it was drafted**: scribe-assisted, with the model and
   date, so a later reader can tell a transcribed note from a typed one. A
   clinical record that hides its own provenance is worse than one that admits
   it.

---

## 5. What is stored and what is discarded — proposed

| Artefact | Proposal | Why |
|---|---|---|
| **Raw audio** | **Never persisted. Never leaves the device except to the transcription call, and is discarded as soon as a transcript returns.** | Audio is the highest-risk artefact and the one with the least clinical value once transcribed. Keeping it creates a subpoenable recording of a client's voice for no benefit the transcript does not already give. |
| **Raw transcript** | **Discarded once the vet accepts or rejects the draft.** Not written to any resource. | A verbatim transcript of an exam room contains far more than the clinical record — a client's finances, family, other animals, and everything said while the vet was out of the room. |
| **The drafted SOAP note** | Persisted, as a normal `sv_soapnotes` record, **only on explicit acceptance**. | This is the artefact the practice actually needs and the one the record system is designed for. |
| **Consent event** | **Persisted**: that consent was asked, by whom, for which appointment, and the answer. **No audio of the consent.** | The practice must be able to show consent was obtained. A stored *fact* of consent is defensible; a stored *recording* of it re-creates the problem it documents. |

**THE DEFAULT IS DISCARD AND IT IS DELIBERATE.** The tempting option — keep the
audio "in case of a dispute" — turns every consultation into a permanent
recording of a client, which is a far larger liability than the one it hedges.
If a practice genuinely needs retention, that is a **separate, explicit,
per-practice decision with its own retention period**, and it is **not in
scope here.**

---

## 6. DECISIONS

### 6.1 All-party-everywhere — **ACCEPTED** (Michael, 2026-09-23)

§3 stands as written. No per-state branch.

### 6.2 Where transcription runs — **DECIDED: SELF-HOSTED, e.g. Whisper** (Michael, 2026-09-23)

**Not Google's browser-native `SpeechRecognition`, and not a paid third-party
ASR service either.** A self-hosted model: real compute cost to host, no
per-call fee, and **no third-party data flow for exam-room audio**.

**The reasoning, recorded because it is the reasoning and not the conclusion
that has to survive:**

- **Trust and minimal-necessary.** This platform's whole posture is
  redaction-first and minimum-necessary. Routing a client's voice through a
  consumer speech API to save money would contradict the position every other
  feature is built on, and a consent notice that has to say *"and Google hears
  this"* is a notice practices will decline.
- **`SpeechRecognition` is a CONSUMER-FACING BROWSER API, not a production
  dependency.** It is unversioned, vendor-controlled, silently changeable and
  absent entirely in some browsers. The app already treats it that way — the
  existing dictation shows no button at all when it is missing
  (`sairnvet.html:21570`-style graceful fallback), which is fine for a
  convenience and not fine for the path a clinical record is drafted from.
- **Cost shape.** Per-call pricing scales with every consultation; a hosted
  model is a fixed cost that does not grow with use.

**WHAT THIS DECISION CHANGES IN THIS DOCUMENT, said explicitly rather than left
for a reader to infer:**

1. **§5's "never leaves the device" needs its qualifier read carefully.** Audio
   now DOES leave the device — to a **first-party** endpoint. The rule is
   unchanged in substance (no third party) and the wording in §4.1 must say
   *where* it goes rather than implying it goes nowhere.
2. **The server must discard too.** Discard-by-default is now a property of two
   places, not one. A transcription endpoint that writes audio to disk, a log or
   a temp file that outlives the request re-creates exactly the liability §5
   removes on the client.
3. **The host does not exist yet, and that is a real blocker for the MODEL half
   only.** Vercel's serverless runtime has an execution-time limit and no GPU,
   so `api/` is the wrong place for Whisper itself. The endpoint **contract**
   can be built and gated now; the model host is its own infrastructure
   decision.
4. **It becomes a SOUP entry.** A self-hosted model is third-party software the
   platform runs, which is exactly what the SOUP register is for — the vendor,
   the version, and the stated reason it is trusted.

**AND THE FAILURE MODE IS NAMED NOW RATHER THAN DISCOVERED: with no host, the
feature must FAIL CLOSED.** It must refuse to capture and say why. It must not
fall back to `SpeechRecognition` "just for now", because a temporary fallback to
the exact vendor this decision rejects is how the decision gets reversed without
anybody deciding it.

### 6.3 Discard-by-default retention — **still open**

§5 as proposed, or does a practice need a retention option?

### 6.4 Per-practice kill switch — **still open**

Should a practice owner be able to disable the feature so individual vets
cannot enable it unilaterally?

---

## 7. Not determined — do not build past these

- **Whether the July 2023 Oregon ruling reaches a private exam room.** The
  strike-down retrieved from RCFP concerns *public* conversations. Unresolved,
  and all-party-everywhere makes it moot for the build while it stays open.
- **Whether the all-party in-person list is exactly the seven RCFP names.** The
  retrieval named California, Florida, Illinois, Massachusetts, Michigan,
  Missouri and Pennsylvania explicitly. Whether Delaware, Maryland, Montana, New
  Hampshire and Washington also reach in-person conversations **was not
  determined**, and is not assumed either way. §3 means the build does not
  depend on the answer.
- **Whether a veterinary board in any state imposes its own recording or
  record-retention rule** on top of the wiretapping statutes. Not researched.
- **Whether the client's voice is biometric data** under any state biometric
  privacy act — Illinois BIPA is the obvious one to ask about, and it is
  **also** an all-party state, so the two questions land together.

**NOT LEGAL ADVICE.** This is internal scoping so a decision can be made and a
professional can be asked a narrow question instead of an open one.

---

## 8. What was deliberately NOT built

No audio capture, no `getUserMedia({audio:true})`, no transcription call, no
consent UI, no resource. **The instruction was to scope the consent and UI flow
before writing the transcription logic, and the reason that ordering matters is
that capture code is easy to add and impossible to un-ship.** §6's first two
questions — the two that change the architecture — are now answered (§6.1, §6.2).
**This section is still accurate as of 2026-09-23: none of it has been written.**
When it is, this section must be rewritten to say what WAS built, not left
standing as a stale claim that nothing exists.
