# SAIRNfreedom Phase 6 — the cross-tenant read, designed before it is written

**Date:** 2026-09-01 · **Status:** design only, no code written · Run with
`sairn-software-architect` per the build spec's own instruction: *"Cross-tenant
read is a genuinely new authorisation shape for this platform — every existing
app is single-tenant-per-licence. Design it with `sairn-software-architect`
before writing it."*

---

## 0. The ceiling, stated first, because everything else follows from it

**Phase 6 is not buildable on SAIRNfreedom's current storage model. Not
difficult — impossible.**

Phases 1–4 are entirely `localStorage`. Verified today, not assumed:

- there is **no `api/_resources/sairnfreedom.js`** — the directory holds
  thirteen apps and SAIRNfreedom is not one of them;
- there is **no `sql/sairnfreedom_*` schema** of any kind;
- SAIRNfreedom appears in `api/claude.js`'s `KNOWN_APP_IDS` **only**, for the AI
  proxy, and nowhere else in `api/`.

`localStorage` is per-browser, per-device. A district officer's browser cannot
read Post 214's browser. There is no polling interval, no bridge trick and no
sync shim that changes that. **Phase 6 is the feature that forces SAIRNfreedom
to have a server for the first time**, and that is the actual decision in front
of you — the authorization shape is downstream of it.

### Two prerequisites the spec's dependency graph does not list

The spec says *"Phase 6 — needs all of the above"*, meaning Phases 1–5. It needs
two things that are not phases:

1. **A server tier.** Schema, an `api/_resources/sairnfreedom.js` entry or a
   dedicated endpoint, and a migration path for four phases of existing
   localStorage data.
2. **Real authentication. SAIRNfreedom has none today.** `sfUnlock()` accepts
   any non-empty string, stores it in `localStorage` and opens the app. Nothing
   is validated server-side because there is no server. **There is currently no
   actor to authorize** — so an authorization design has nothing to attach to
   until `sairn-employee-auth-scaffold` (which thirteen apps already ship) is
   applied here.

Neither is Phase 6 work. Both are strictly larger than Phase 6.

---

## 1. What the platform's tenancy invariant actually is

Read from `api/_lib/license.js` and `api/_lib/auth.js` today rather than
recalled:

    license_hash = sha256(license_key)

Every tenant-scoped row is keyed by it and every query carries
`?license_hash=eq.<hash>`. And in `verifySessionToken`, the last check before
success is:

    if (!license_hash || payload.license_hash !== license_hash) return null;

with the comment: *"a token minted for one shop's license must never be accepted
against a different shop's requests, even if somehow replayed."*

**That line is the platform's tenancy boundary, and thirteen apps depend on it
being absolute.** Phase 6 is, by definition, a request to read across it.

### The three existing cross-tenant paths, and why none of them is the answer

| Path | What it does | Why it does not generalise |
|---|---|---|
| `api/sairndental/send-reminder.js` | Cron-only, service-role, scans every practice, bypasses the licence layer entirely | **Works because no human is on the other end.** It is gated by `CRON_SECRET` and is not user-callable. A district officer is a human with a browser; the same posture would be an unauthenticated read of every post on the platform |
| `api/bridge.js` | StoneDesk-only relay | Its own header says **"NO AUTHORIZATION on push, deliberately… anyone can write to any shop_id… NOT fine for personal or financial data."** Phase 6 is entirely financial data. Its `pull` action has **zero callers** platform-wide |
| `api/sd-data.js` shared resources | The real cross-**app** data path, used by ten apps | Cross-**app**, not cross-**tenant**. Still `license_hash`-scoped. It solves a different problem |

### The one precedent worth copying: `api/sen-portal.js`

SAIRNsenior's family portal is the closest thing on the platform to a second
actor class reading data it does not own, and its security model contains the
rule Phase 6 most needs:

> "the `client_id` it resolves to is **NEVER supplied by the caller** — there is
> no `client_id` parameter on `view` at all, only the token. A family member
> cannot access a different client's data by guessing or editing a parameter,
> **because there isn't one**."

**Carry that forward verbatim: no district endpoint may take a `license_hash`,
`post_id` or `entity_id` parameter.** The server derives the readable set from
the caller's identity. An id the caller can edit is the vulnerability.

---

## 2. The options, with their real costs

### Option A — a district "super-licence" whose token carries member hashes

Mint a district session token containing a list of post `license_hash`es; the
endpoint checks the requested hash is in the list.

**Reject.** Two independent reasons:

- A privilege list **inside a token** is a privilege-escalation surface. The
  list must live server-side and be re-read per request, at which point the
  token is not carrying it and this is really Option B.
- It requires relaxing `verifySessionToken`'s `license_hash` equality check in
  **shared** `api/_lib/auth.js`. That weakens the boundary for **thirteen apps**
  to serve one feature in one app. The blast radius is the entire platform.

### Option B — grant-gated read: each post explicitly grants a district

A `sairnfreedom_district_grants` table keyed by
`(post_license_hash, district_id)` with `granted_by_employee_id`, `granted_at`,
`revoked_at`, and a `scope`. The district's session resolves to a `district_id`;
the server reads the grant table, derives the set of post hashes, and queries
only those. The district supplies nothing.

**Good, and necessary — but not sufficient on its own.** Consent is per-post,
revocable by the post, and auditable, which matches the legal reality that each
post is a separately-governed entity. But a grant is a *permission*, and the
spec asks for read-only **by construction**. With Option B alone, the district
endpoint still has a code path that reaches a post's raw rows; one bug in a
filter and it returns them.

### Option C — published aggregates: the district reads a different table

Each post computes its own rollup figures and **publishes** them to
`sairnfreedom_district_reports`. The district reads only that table and has no
query path to any post's transactional rows.

**This is what "read-only by construction" means taken literally.** Construction,
not permission. A bug in the district endpoint cannot leak a member roster, a
canteen ticket or a prize winner, because those bytes were never in the table it
reads.

**The PII argument makes this decisive, and it connects to a decision already
taken.** Phase 3 item 3.5 is held precisely because ORC 2915.10(A)(3) requires
storing winner **Social Security numbers** for prizes of $600 or more. If the
district tier ever had a read path to a post's gaming records, a district
officer would be one filter bug away from SSNs. Publishing aggregates means the
district tier never touches that table at all — **the held 3.5 decision and this
one protect the same data, and they should not be allowed to disagree.**

Its cost is real and should be said: reports are **as of last publish**, and the
post controls what it publishes. Both are arguably correct — they are the post's
books — but a district cannot use this to catch a post that simply stops
publishing. It shows silence, not falsehood.

### Option D — signed export / import, no server at all

Each post exports a signed aggregate file; the district imports them.

**Ships today, inside the current architecture.** Zero infrastructure, zero new
authorization surface, and consent is inherent — the post chooses to send the
file. Costs: manual, stale, no revocation, no completeness guarantee.

This is a serious option, not a strawman. For a district of ten to forty posts
reporting quarterly, it may be genuinely adequate, and it **proves the demand
before the platform investment.**

---

## 3. Recommendation

**Build Option D now. Build B + C only when a real district asks for it.**

- **D fits the existing architecture exactly** and is the cheap, reversible move
  the platform's whole model is built on. It also produces the artefact B + C
  would need anyway: a settled *aggregate shape*. Getting that shape right is
  the part that is expensive to reverse; the transport is not.
- **B + C is the real feature**, and it is the most expensive item in the app —
  it is the platform's first multi-tenant read, and it drags a server tier, an
  auth system, a migration and a publish job in behind it.

**Do not build B + C speculatively.** The spec calls the district rollup one of
three defensible moat items with no verified competitor. A moat nobody has asked
to cross is not yet a moat.

### If and when B + C is built, the shape is

    post browser ──publish──> sairnfreedom_district_reports ──read──> district
                              (aggregates only, never raw rows)
                                        ▲
                              sairnfreedom_district_grants
                              (post-granted, post-revocable, server-read)

- District session is a **separate actor class** with its own role set, not a
  post employee with extra permissions. Mixing them means one bug promotes a
  post's own officer into a district reader.
- **No write path exists for a district actor at all** — not gated, absent. The
  posts are separate legal entities with separate treasuries.
- **No caller-supplied entity identifier anywhere**, per `sen-portal`.
- Grants carry `granted_by_employee_id` and are subject to the platform's
  existing credential-recoverability rules; `tools/employee_auth_guard_check.py`
  and the seed/SQL push gate both apply the moment credential rows exist.

### The aggregate shape, derived from what Phases 1–4 actually hold

Entities, never locations — per spec §1b, an auxiliary is a separate tenant
sharing a building, and Phase 1 already keeps `entityId` and `locationId` as
separate keys, so the foundation holds.

| Group | Fields |
|---|---|
| Membership | counts by category, S.A.L. sub-count, active waivers |
| Money owed upward | per-capita liability accrued and remitted — **the district's most direct interest**, and already modelled as a liability rather than revenue |
| Gaming | sessions held, gross receipts, prizes, gross profit, net profit **split by regime** (traditional vs instant — they are governed by different rules and must not be summed into one number for a district either) |
| Distribution | ORC 2915.101 required vs distributed, and the running shortfall |
| Disbursement | totals by Ohio charitable purpose and by national category, kept as the two independent taxonomies they are |
| Service | person-hours, person-miles, national-countable split |
| Compliance | permit-filing flags outstanding, barred operators, prize-cap breaches, unmet distributions |

**The compliance row is the most valuable and the most politically sensitive
line in the whole feature** — a district seeing which of its posts are
non-compliant. Worth deciding deliberately whether it is in scope, rather than
discovering the answer after the first district officer reads it.

---

## 4. What must not be done

1. **Do not relax the `license_hash` equality check in `api/_lib/auth.js`.**
   Thirteen apps rely on it.
2. **Do not route Phase 6 through `api/bridge.js`.** No authorization on push,
   explicitly bounded away from financial data, and its read side has no callers.
3. **Do not give a district a service-role path.** `send-reminder.js` is safe
   because no human can call it.
4. **Do not put an entity, post or licence identifier in any district request.**
5. **Do not build Phase 6 before SAIRNfreedom has real authentication.** Today
   any string opens the app.

---

## 5. Premortem — *"eighteen months on, this went wrong"*

- **"A district officer saw a winner's SSN."** Prevented by Option C: the
  district tier reads a table that has never contained one. Option B alone does
  not prevent it.
- **"A post's data was aggregated without its consent."** Prevented by the grant
  table being post-granted and post-revocable, with `granted_by_employee_id`
  recorded.
- **"The district numbers disagreed with the post's own books."** Expected, and
  should be designed for rather than denied — reports are as of last publish.
  Show the publish timestamp next to every figure, the same discipline as the
  read-date on a searched vendor price.
- **"We built a multi-tenant platform tier for a district that never signed."**
  The reason the recommendation is D first.
- **"The rollup summed traditional and instant bingo net profit into one
  figure."** The two are governed by different statutes; a single "net profit"
  number at district level would be exactly the error Phase 4 was careful to
  avoid at post level.

---

## 6. Sequencing

Phase 5 is localStorage-native and introduces no new architecture. Phase 6, in
its real form, is a platform decision rather than an app feature.

**Recommended: Phase 5 next, Option D alongside it, and B + C held pending a
real district.** That is a recommendation, not a blocker — the design above is
complete enough to build B + C from if the call goes the other way.

## 7. What this design did not settle

- **The migration** of four phases of localStorage data into a server tier.
  Named as a prerequisite, not designed.
- **Whether a district may see the compliance row.** Flagged above as a
  deliberate decision, deliberately left open.
- **Whether any real district officer wants this**, in what cadence, and in what
  format their own state or national body already requires. No district was
  consulted. That is the single largest unknown here and it is a product
  question, not an architecture one.
