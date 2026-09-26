# The Tier 2 clearinghouse engagement, scoped — 2026-09-26

**Scoping only. Nothing built. No app file touched.**

**HEADLINE: this is probably not an engagement. SAIRNcode already ships a live,
customer-owned clearinghouse integration, and the vendor it uses is documented —
by this repo's own primary-source read — to support every X12 transaction these
four rows need. One of the four rows is the transaction that is ALREADY WORKING,
so it is a port rather than a relationship. What genuinely has to be built is not
the connection: it is the three things an 837 needs that a 270/271 does not.**

And there is a live blocker Michael has to clear first, verified against the
Vercel project rather than read from a document: **`SD_ENCRYPTION_KEY` is not
set**, so every stored clearinghouse credential is still encrypted under the same
string that signs sessions, and is still effectively unrotatable (§5).

Measured against the repo at **`0a202343`** and the `sairn` Vercel project
(`prj_bj475nKLxC1TTmpFU6j7HVCSMEhn`), 2026-09-26.

---

## 1. What the four rows actually need, as transaction sets

`docs/2026-09-26-gap-triage-four-verticals.md` §3 groups these as *"open, gated on
a relationship somebody could go and get"* and notes **one engagement unlocks
four rows.** That grouping is right about the commercial shape and hides that the
four rows are **three different technical problems**.

| Row | What it needs | Platform state at `0a202343` |
|---|---|---|
| **SAIRNdental A1** — real-time insurance eligibility | **270/271** | **ALREADY BUILT, in another app.** `api/sc-eligibility.js` runs live X12 270/271 through the practice's own Stedi account. Dental's own `eligibilit` × 4 are all No Surprises Act (`gfeEligibility`), none payer eligibility |
| **SAIRNdental A2** — claim submission | **837D** (dental) | **Absent.** `837` × 0, `x12` × 0, `clearinghouse` × 0 in `sairndental.html` |
| **SAIRNdental A3** — clearinghouse connection | the connection itself, plus **835** to close the loop | **Absent.** The remittance is read by a HUMAN today — `:992` *"Payer … as it appears on the remittance"*, `:999` *"Reason, in the payer's own words … copied from the remittance, not summarised"*. That transcription is the labour an 835 removes |
| **SAIRNsenior A4** — 837 / clearinghouse | **837P** (professional), plus **835** | **Absent, and the claim is already assembled.** `sairnsenior.html` has a **Billing & Claims** panel that *"generate[s] claims from EVV-verified"* visits into a `bl-claimstbody` table. `claim` × 222, `payer` × 141, and `837` × 0. **Senior builds claims and has nowhere to send them** |

**Verified platform-wide: no X12 claim or remittance code exists anywhere.** A
word-boundary search for `837` / `835` across `api/**`, `sql/**` and every root
`*.html` returns two files, both unrelated (a grant-revoke SQL script and a
SAIRNlaw deadline seed). The two apparent hits inside `sairncode.html` are CPT
**90837** and the hex colour `#78350f`. There is no half-built transport to
finish.

### 1.1 TWO BOUNDARIES THE "FOUR ROWS, ONE ENGAGEMENT" FRAMING WILL SWALLOW IF NOBODY SAYS SO

1. **SAIRNsenior A1's transmission half is NOT in this engagement.** An **EVV
   state aggregator is not a clearinghouse.** `api/_lib/sen-evv-readiness.js`
   reports whether a submission would have the data it needs and its own header
   names three blockers — *a trading-partner agreement per aggregator*, a place to
   hold per-agency credentials, and a wire format that could not be verified from
   primary sources. `transmit` × 0 in `sairnsenior.html`. That is a separate
   relationship, per state, with a different counterparty. **A clearinghouse
   contract closes none of it.**
2. **Prior authorisation (278) is not available on the incumbent and is not in
   scope.** `docs/superpowers/specs/2026-08-20-sairncode-prior-auth-phase2-design.md`
   §3, checked directly against Stedi's own docs rather than assumed: *"Stedi's
   documented transaction support is 270/271, 837P/I/D, 276/277, 835, 277CA.
   There is no 278, and no prior-auth item in docs, beta, or roadmap."* If prior
   auth is ever wanted, that is **a different vendor and its own scoping pass** —
   and the same document's decision gate already refused to build the FHIR PAS
   route, with the reason that the CMS-0057-F 2027-01-01 deadline *"is an
   obligation on payers to expose the API, not on providers or their software to
   consume it."*

---

## 2. Vendor candidates — and the honest state of this section

**The incumbent, and it is already integrated and already verified:**

**Stedi.** `api/sc-eligibility.js` + `api/sc-credentials.js`, live since
2026-08-20. Documented transaction support **270/271, 837P/I/D, 276/277, 835,
277CA** — which covers dental A1 (270/271), dental A2 (**837D**), senior A4
(**837P**) and the 835 both need. That list was read from Stedi's own docs in
this repo on 2026-08-20 and recorded, not recalled; the same pass recorded the
one absence (278). **Eligibility bills $0** per the prior-auth design doc's §2
premortem. **Claim-submission and ERA pricing is NOT recorded anywhere in this
repo and is the one number nobody here has** — see §6.

**A competitive comparison was NOT run in this pass, and no alternative vendor is
named, deliberately.** Naming clearinghouses I have not verified would be exactly
the fabrication this platform keeps catching, and the cloud-research lane that
would do it properly **ran out of its WebSearch budget** during the SAIRNbiz pass
(`docs/cloud-research/SAIRN-PLATFORM-2026-09-26-cloud-research-lane-handoff.md`
§1). What this pass can give instead is the **selection criteria**, which is the
part that actually constrains the choice:

1. **837D and 837P both**, from one account. Dental needs D and senior needs P;
   two vendors means two integrations and two credential slots.
2. **835 ERA delivery**, or the remittance stays a human transcription and A3 is
   not closed.
3. **277CA acknowledgment**, for the reason in §3.
4. **A per-practice API credential, not a SAIRN-held account.** This is
   non-negotiable and it is not a preference: `api/sc-credentials.js`'s header
   records the BAA reasoning — *"SAIRN never holds a clearinghouse account on
   their behalf."* A vendor whose model is one master account with sub-tenants
   changes SAIRN's regulatory position, not just its code.
5. **A test/sandbox mode that is distinguishable from production.** See the
   defect in §3.

**Recommendation: get a Stedi quote for 837P/837D/835 before evaluating anyone
else.** The integration is built, the credential pattern is proven, the
transaction coverage is verified, and the incremental question is a price.

---

## 3. Integration requirements — and the honest cost difference

**What is reusable, and it is a lot.** The proven shape is
`api/sc-credentials.js` (encrypted per-practice key, never redisplayed) plus a
per-app proxy endpoint modelled on `api/sc-eligibility.js`. Adding an app means
one `ALLOWED_SERVICES` entry (`api/sc-credentials.js:58` is `{ stedi: true }`
today) and one endpoint. **No new crypto, no new schema pattern.**

**Copy the anti-fabrication contract verbatim**, because it is the part that
makes a clearinghouse integration safe to ship:

- no credential configured → **503 NOT_CONFIGURED**, *never* a simulated or
  sample result;
- a Stedi or payer error → **that real error text is surfaced**, never swallowed,
  never replaced with a friendly *"not covered"*, never retried into a
  different-looking answer.

**AND COPY THIS DEFECT'S LESSON, which cost real time and is the sharpest thing
in the whole file.** `api/sc-eligibility.js`'s header records that the
`Authorization` scheme word is **`Key`** — not bare, not `Bearer`. The code sent
the key bare for three days and **a bare key still AUTHENTICATES**: every check
returned a real, well-formed 271 from a real payer, never a 401, so nothing
looked broken. What it did not do was resolve the key *object*, and test/production
mode travels with the key itself (same host, no sandbox URL, no mode parameter) —
so **mock requests were being forwarded to real payers**, which rejected Stedi's
fictional test patients identically across six payers. **A working response is not
proof the integration is configured correctly.** On a claims path the equivalent
mistake submits test claims to real payers.

### 3.1 THE THREE THINGS AN 837 NEEDS THAT A 270/271 DOES NOT

This is where the real work is, and none of it is the clearinghouse relationship.
Eligibility is request/response: send a question, render the answer, store
nothing that has to reconcile. A claim is none of those things.

1. **A claim builder.** An 837 is an assembled document — loops and segments,
   subscriber vs. patient, service lines, place of service, rendering vs. billing
   provider, NPIs and taxonomy. Senior already assembles the claim's *content*
   from EVV-verified visits; what does not exist is the mapping from that content
   to segments. **This is the largest single piece and it is per-app**, because
   837P and 837D are different documents.
2. **A 277CA reader, and it is the SILENT-FAILURE half.** A claim that the
   clearinghouse accepts and the payer rejects is indistinguishable from a paid
   claim if nothing reads the acknowledgment. **Submitting without reading 277CA
   is a fire-and-forget write on money** — the exact class this platform audits
   for. A submit button whose only outcome is "sent" must not ship.
3. **An 835 parser, and a reconciliation surface to put it on.** The 835 is what
   closes dental A3 and what removes the manual transcription at
   `sairndental.html:992`/`:999`. Both apps already have a `panel-billing` and
   dental has a denial record shaped for the payer's own words — so the
   **destination exists** and the parser does not.

**Sequencing that follows from this, and it is the cheap ordering:** dental A1
first (a port of a working 270/271 — days, not weeks, and it proves the credential
path in a second app before any claim money is at stake), then 835 (read-only,
cannot harm a payer relationship, and it removes real daily labour), then 837
behind a 277CA reader. **Do not ship 837 first.** It is the only one of the three
that can do outward harm, and it is the one whose failures are silent.

---

## 4. What is NOT reusable, and is worth knowing before the quote

- **`api/sc-credentials.js` allows exactly one service today.** Extending
  `ALLOWED_SERVICES` is trivial; what is not trivial is that two apps holding
  two credentials for the same vendor under one platform-wide encryption key
  multiplies the blast radius of §5.
- **Nothing on this platform has ever sent an X12 document.** The 270/271 path
  builds a JSON body and lets Stedi construct the X12. **Whether the claims API
  is also JSON-in or expects a raw 837 file is the single biggest unknown in the
  build estimate** and it is answerable in one read of Stedi's docs by anybody
  with network access. Do that before estimating.
- **SAIRNcode is not the place to build it.** The rows are SAIRNdental's and
  SAIRNsenior's. SAIRNcode is the **precedent and the reference implementation**,
  not the host.

---

## 5. THE BLOCKER, VERIFIED LIVE RATHER THAN READ: `SD_ENCRYPTION_KEY` IS NOT SET

**Clear this before any second app stores a clearinghouse credential.**

`api/_lib/auth.js` (Stage B, 2026-09-17) records that `getEncryptionKey()` *used
to be* `sha256(SD_AUTH_SECRET)`, so **one string was both the session-signing
HMAC key and the AES-256-GCM key for secrets at rest** — attorney MFA/TOTP
secrets and the stored Stedi API key. Two consequences it names: a leak did not
only forge sessions, it **decrypted every secret at rest**; and the secret was
effectively **unrotatable**, because changing it makes every stored ciphertext
undecryptable, **nothing errors at deploy time**, and MFA starts failing
per-attorney as each one next signs in.

The fix is a versioned format — `legacy iv.tag.ciphertext` under
`sha256(SD_AUTH_SECRET)`, `v2 v2.iv.tag.ciphertext` under
`sha256(SD_ENCRYPTION_KEY)` — and the code says plainly: **"UNTIL
`SD_ENCRYPTION_KEY` IS SET THIS DEPLOY CHANGES NOTHING."**

**It is not set.** Verified 2026-09-26 by listing the `sairn` project's
environment variable KEYS (no values decrypted): `SD_AUTH_SECRET` is present,
**`SD_ENCRYPTION_KEY` is absent** from every target. So the split is
code-complete and **environment-incomplete**, and today's state is the pre-fix
state: one string, both duties, unrotatable.

**Why this binds THIS engagement specifically.** A clearinghouse key is lower
stakes than the private signing key the prior-auth premortem refused to hold —
*"a Stedi API key reaches Stedi and bills $0; a private signing key lets the
holder impersonate that practice to every payer it registered with."* But a key
that can **submit claims and receive money-bearing remittances** is materially
above the read-only eligibility key sitting beside it under the same secret.
Adding two more apps' credentials under one unrotatable platform-wide key is
going the wrong way.

**The action is one environment variable**, and the migration order is already
safe by design: setting `SD_ENCRYPTION_KEY` moves new writes to v2 while legacy
values keep decrypting, so the code can land before the environment does — which
it has.

### 5.1 AND ONE THING FOUND WHILE LOOKING, ORTHOGONAL AND NOT ACTED ON

Listing those keys surfaced an unrelated problem: **the `SAIRN_INTERNAL_KEY`
variable has what appears to be its own secret value pasted into its `comment`
field.** The comment is plaintext metadata — it is not encrypted, it is returned
by the API to anyone who can list env vars, and it is visible in the dashboard
beside the masked value. The value is not reproduced here. **Not touched: it is
outside this dispatch and rotating a platform key is not a side effect anybody
should take.** Raised for Michael to decide.

---

## 6. What Michael needs to do

In order, and the first three are conversations rather than work:

1. **Set `SD_ENCRYPTION_KEY` in Vercel** (production and preview). One variable,
   the code is already waiting for it, legacy values keep working. **§5 — do this
   first.**
2. **Decide about `SAIRN_INTERNAL_KEY`'s comment field.** §5.1.
3. **Ask Stedi three questions.** (a) Price for 837P, 837D and 835 on a
   per-practice-account model. (b) Is the claims API JSON-in like the eligibility
   API, or does it expect a raw X12 837? (c) Is there a sandbox that is
   distinguishable from production **by something other than the key**, given
   what §3 records about mode travelling with the key.
4. **Confirm the customer-owned-account model is what you want commercially.**
   It is what is built and it is the right regulatory answer, but it means every
   practice must open its own clearinghouse account before the feature works for
   them — a sales and onboarding cost, not an engineering one. The alternative
   (SAIRN holds the account) changes SAIRN's BAA position and is a different
   decision, not a different implementation.
5. **Then dispatch, in this order, and not in one claim:** dental A1 port → 835
   reader → 837 behind a 277CA reader. §3.1.
6. **Separately, if a competitive vendor comparison is wanted:** dispatch it to a
   cloud-research session with a **fresh search budget**. The last lane exhausted
   its 200-call cap, and this pass deliberately named no unverified vendor.

---

## 7. What this pass did NOT do

- **It did not research a single clearinghouse vendor externally.** Every Stedi
  fact above is quoted from this repo's own 2026-08-20 primary-source reads, and
  every one of them is a claim to re-verify against Stedi's current docs before
  it is relied on — their API surface has moved once already (the prior-auth doc
  tells its own reader to recheck).
- **It did not price anything.** No figure for 837 or 835 appears above, because
  none exists in the repo and a snippet-sourced price is worse than an absent one.
- **It did not verify that Stedi's 837D covers the specific dental scenarios
  SAIRNdental's A2 row implies**, only that 837D is in the documented list.
- **It did not estimate the build.** §4 names the unknown (JSON-in vs raw X12)
  that makes an estimate meaningless until answered.
- **It did not decrypt any environment value.** §5 rests on which KEYS exist,
  which is the only thing it needed.
- **It touched no app file and built nothing.**

## 8. Decay

The environment finding in §5 is a live read and will be wrong the moment Michael
acts on it — **re-list the keys rather than trusting §5**. The Stedi transaction
list is five weeks old and is the kind of fact a vendor changes without telling
anybody. Everything in §1 is a marker count and a line number in files four
sessions are editing; two rows in the document this scoping descends from had
already moved in nine days.
