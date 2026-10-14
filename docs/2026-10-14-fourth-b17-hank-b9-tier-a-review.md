# TIER A REVIEW — hank b9, `a6fa37a3` — discharged by fourth — 2026-10-14, b17

**THE OBLIGATION:** `docs/tier-a-reviews.json`, author `hank`, opened
`2026-10-14T11:55:18Z`, 10 Tier A resources, 5 files. **Reviewed by fourth,
which the gate permits and self-review does not** — recording an obligation is
the author's job, discharging it is somebody else's.

**VERDICT: ACCEPT, with one correction that is MINE and not hank's, two
conditions, and one missing test routed to cody.**

```
CMD git show --stat --format='%h %cI' a6fa37a3
    a6fa37a3 2026-10-14T08:02:21-04:00
    api/_lib/ai-safeguards.js 229+ · api/ai-notice.js 220+
    api/ai-safeguards.test.js 426+ · api/sd-data-ai-approval.test.js 285+
    api/sd-data.js 57+ · sql/2026-10-14-hank-b9-ai-safeguards.sql 95+
    6 files, 1312 insertions
```

---

## 1. THE CORRECTION IS MINE: my b15 §7.5 ruling was built on a premise that is FALSE

**`docs/2026-10-14-ai-safeguards-spec.md` §7.5 ruled that `api/ai-notice.js`
is "the LOSER" and told hank to delete it and migrate.** That ruling assumed
the endpoint carried **a second ack store** — "two ack records for one fact".

**IT DOES NOT. Measured:**

```
CMD grep -nE "create table|alter table|add column" sql/2026-10-14-hank-b9-ai-safeguards.sql
    54:      'alter table public.%I
    55:         add column if not exists ai_notice_version text,
    56:         add column if not exists ai_notice_acked_at timestamptz',
```

**No new table. The migration adds the two columns to each
`*_employee_auth` row — which is exactly what §2.1 and §7.5 say the store must
be.** The ack lives on the employee login record; `api/ai-notice.js` is only
**where the action lives**, not a second store.

**SO §7.5 AS WRITTEN WOULD HAVE DELETED WORKING CODE THAT IMPLEMENTS ITS OWN
RULING.** The real difference between my spec and hank's build is narrow: my
§3.2 put the `ack_ai_notice` action on each existing `*-auth.js` endpoint; hank
put one endpoint beside them.

**RE-RULED, and the correction belongs in my document, not in hank's code:**

| | |
|---|---|
| **the ack store** | `*_employee_auth.ai_notice_version` + `.ai_notice_acked_at` — **agreed, built, unchanged** |
| **the action's home** | **hank's single `api/ai-notice.js` STANDS.** One endpoint beats the same action copied into 17 `*-auth.js` files, and §3.1 of my own spec argues for one shared helper for precisely that reason |
| **what §7.5 should have said** | "if a second store appears, delete it" — and no second store appeared |
| **the timing, said plainly** | `a6fa37a3` landed at **08:02**; §7.5 was written around **12:00** the same day. **hank could not have read a ruling that did not exist**, and the ruling was wrong anyway |

**`CURRENT_NOTICE_VERSION = '2026-11'` at `api/_lib/ai-safeguards.js:52`
matches §7.3 exactly.** The one thing §7.5 and the build already agreed on.

---

## 2. (d) THE CROSS-TENANT ACK — the highest-value bug in the feature, and it is CLOSED

hank asked for this one to be reviewed hardest. **It holds.**

```
CMD grep -n "app_id\|verifySessionToken\|license_hash\|employee_id" api/ai-notice.js
    80:  const app = body.app_id;
   117:    res.status(403).json({ code: 'LICENSE_WRONG_APP' ... })
   126:  const table = app && AUTH_TABLE_BY_APP[app];
   136:  const session = verifySessionToken(tokenFromRequest(req), licHash, app);
   145:  const mine = table + '?license_hash=eq.' + enc(licHash)
   146:    + '&employee_id=eq.' + enc(session.employee_id);
```

**`app_id` comes from the body and is used for ONE thing — picking which
`*_employee_auth` table to touch — and is then handed to
`verifySessionToken` as its third argument, which refuses a token minted for a
different app.** The row is then selected by `license_hash` **from the verified
licence** and `employee_id` **from the verified token**. Neither identity field
comes from the body.

**Three defences in series:** `LICENSE_WRONG_APP` (`:117`), the app-scoped
token check (`:136`), and the identity coming only from the session
(`:145-146`). **A forged `app_id` picks a table the caller's token cannot pass
the check for, and a forged `employee_id` in the body is never read.**

**AND THE UNMIGRATED CASE FAILS CLOSED**, which I did not expect to find:
`looksUnmigrated()` at `:163` turns a missing-column error into **503
NOT_MIGRATED** (`:170`, `:211`) rather than an empty ack state. **A notice that
cannot be recorded must not read as recorded** — this is PR §1.11 applied to a
column that does not exist yet.

---

## 3. (b) THE `sen_settings` ALLOWLIST ASYMMETRY — the direction is RIGHT, and the cost is a support call

```
CMD sed -n '7818,7845p' api/sd-data.js
    7818: if (resource === 'sen_settings' && action === 'read') {
    ...   UNKNOWN KEYS ARE WITHHELD FROM NON-MANAGEMENT, which is deliberately
    ...   the opposite of how the write path treats them ...
    ...   A store that accepts anything must not also DISCLOSE anything
```

**That sentence is the whole justification and it is correct.** A settings store
that accepts unknown keys **and** discloses them publishes every future setting
to every caregiver by default; the asymmetry makes *disclosure* the thing that
needs a decision, which is the right way round.

**THE COST, NAMED SO IT IS NOT A SURPRISE:** a new setting is invisible to
non-management until somebody adds it to `SEN_SETTING_PUBLIC_FIELDS`. **The
failure mode is "why can't my caregivers see X", not a leak** — the cheap
direction. **Condition:** the allowlist needs a comment at the map saying *add
here when a new setting must be visible to caregivers*, or the next person
debugs a read path for an hour.

---

## 4. (c) THE AI APPROVAL GATE FIRES ONLY ON A CLIENT-SUPPLIED FIELD — accept the dormancy, with a condition

```
CMD grep -n "^const \|^function " api/_lib/ai-safeguards.js
     62: const AI_SOURCE_FIELD = 'ai_source';
     86: const HIGH_RISK_AI = { ... }
    117: const NOT_HIGH_RISK_AI = { ... }     # excluded ON PURPOSE
    162: function isHighRisk(resource)
    188: function enforceAiApproval(resource, payload, verifyForApp, nowISO)
```

**A gate that can be bypassed by omitting a field is not a gate** — and hank
says so in the obligation. **But the alternative is impossible:** a server
cannot look at prose and know a model wrote it (`api/sd-data.js:2063` says
exactly that). **So the dormancy is the right trade and 25 driven arms is the
right amount of proof for it.**

**THE CONDITION, and it is the next piece of work rather than a defect here:**
the moment any client writes one of the five `HIGH_RISK_AI` resources, the
`ai_source` field must become **required on that surface** — not inferred, not
optional. **A per-surface required-field assertion is small; a broader
"guess whether this was AI" gate is impossible.** Until then the gate is
**honestly dormant**, and the `NOT_HIGH_RISK_AI` map at `:117` is what keeps
dormancy from quietly widening.

**Also accepted: `mech_checks` and `sc_auth_requests` appear only as negative
controls** — the narrowness arms asserting they are untouched. That is the
correct shape and it is the half most changes omit.

---

## 5. (a) THE `SEN_REFERRAL` WRITE NARROWING — NOT RULED ON HERE, BECAUSE IT IS MICHAEL'S

```
CMD sed -n '6721,6760p' api/sd-data.js
    6721: const SEN_REFERRAL_RESOURCES = { sen_referral_sources, sen_referrals,
                                           sen_training_rules, sen_training_records,
                                           sen_applicants }
    6738: read + write require SEN_CLIENT_BROAD_READ_ROLES
    ...   THE WRITE IS MANAGEMENT-ONLY NOW (2026-10-14, b9)
```

hank's own framing is right: **it is a product decision and reversing it is one
map.** It takes referral logging and training-record entry away from
coordinators and schedulers.

**So this review does not accept or reject it. It is spec'd both ways, in one
place, in `docs/2026-10-14-fourth-b17-sen-rf-write-map.md`, for Michael to
pick.** **The code as landed is Option B in that document** and is safe to
leave running while the decision is made — the failure direction is "a
coordinator has to ask a manager", not a data loss.

---

## 6. THE MISSING ACCEPTANCE TEST — ROUTED TO cody

**T12 of `docs/2026-10-14-ai-safeguards-spec.md` asserts the PROXY's response
carries `ai: true` and a non-empty `ai_label`. Nothing asserts that a surface
RENDERS it.** Those are different claims, and the gap is exactly where a
cached page lives.

**THE SCENARIO, which is the normal one rather than an edge case:** the proxy
fix ships; a user's browser still has yesterday's HTML; the response now
carries `ai_label` and **the stale page draws nothing**, because the page never
had code to read the field. **Every assertion in T12 passes.**

### T16 — a stale frontend must render the label from the RESPONSE, not from itself

```js
// tests/<app>_ai_label_render.test.js -- extract the render function from the
// shipped page, the way tests/sairncash_entitlement_gate.js extracts
// reverifySubscription(), so a mutation to the page is a mutation to what ships.

// ARM 1 -- THE LABEL IS DRAWN FROM THE RESPONSE FIELD.
{
  const el = renderAiAnswer({ ai: true, ai_label: 'AI assistant. Answers can be wrong.',
                              text: 'hello' });
  assert.ok(/AI assistant/.test(el.textContent),
    'the surface rendered an AI answer with no label');
}

// ARM 2 -- A DIFFERENT LABEL MUST APPEAR VERBATIM. Catches a page that
// hardcodes the words it expects instead of reading the field: the wording is
// [DRAFT -- LAWYER] and WILL change, so a hardcoded label is a stale label.
{
  const el = renderAiAnswer({ ai: true, ai_label: 'ZZ-SENTINEL-LABEL', text: 'hello' });
  assert.ok(/ZZ-SENTINEL-LABEL/.test(el.textContent),
    'the page is not reading ai_label -- it is printing its own copy');
}

// ARM 3 -- THE BAD INPUT: ai:true with NO ai_label must FAIL CLOSED, visibly.
{
  const el = renderAiAnswer({ ai: true, text: 'hello' });
  assert.ok(/AI/.test(el.textContent),
    'an AI answer with no label rendered as if a human wrote it');
}

// ARM 4 -- CONTROL: a non-AI response must NOT gain a label.
{
  const el = renderAiAnswer({ text: 'hello' });
  assert.ok(!/AI assistant/.test(el.textContent),
    'a non-AI answer was labelled AI -- the label stops meaning anything');
}
```

**ARM 2 IS THE ONE THAT MATTERS AND IT IS THE ONE A REVIEWER WOULD CUT.** A
page that hardcodes the current wording passes ARM 1 forever and goes stale the
day counsel changes a word — **which is the one thing §7.3's version bump
exists to make routine.**

**Scope for cody:** one such suite per app that has an assistant surface, and
**T12 stays** — it asserts the proxy; T16 asserts the page. **Neither replaces
the other, and that is the finding.**

---

## 7. WHAT THIS REVIEW DOES NOT CLAIM

* **I ran nothing.** No suite, no endpoint, no app. This is a read of
  `a6fa37a3` against its own obligation, with every claim cited at `file:line`.
  **hank's own 25 arms and 426-line suite are not re-run here**, and a green
  suite I did not drive is not evidence I am entitled to quote.
* **It does not review the 10 resources' data.** The obligation names Tier A
  resources; this reviews the code paths that serve them.
* **It does not close §5.** The write-map decision is Michael's, and the code
  as landed is a safe default while he decides.
* **It does not touch `api/`, `sql/` or `tests/`.** The correction in §1 is to
  **my own document**; the test in §6 is written out for its owner.
