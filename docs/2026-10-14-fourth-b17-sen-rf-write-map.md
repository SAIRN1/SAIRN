# THE PER-RESOURCE WRITE MAP — referral and training resources (`sen_*`, `rf_*`) — both options, one place, one test — 2026-10-14, fourth b17

**ROUTED TO hank (`api/`). SPEC ONLY — nothing outside `docs/` is written.**
**MICHAEL PICKS; hank implements the picked option.** Both options are
specified in full so the choice is between two written things, not between a
written thing and an idea.

**WHY NOW:** hank's b9 (`a6fa37a3`) narrowed the write on five SAIRNsenior
referral and training resources from a broad-read role set to management-only,
and said in its own Tier A obligation that this *"takes referral logging and
training-record entry away from coordinators and schedulers … it is a product
decision and reversing it is one map."* **This is that map, for both apps.**

---

## 1. WHAT IS TRUE TODAY, measured

```
CMD sed -n '6721,6760p' api/sd-data.js
    6721  const SEN_REFERRAL_RESOURCES = { sen_referral_sources: 'source_id',
             sen_referrals: 'referral_id', sen_training_rules: 'rule_id',
             sen_training_records: 'record_id', sen_applicants: 'applicant_id' }
    6738  read + write both require SEN_CLIENT_BROAD_READ_ROLES
    ...   "THE WRITE IS MANAGEMENT-ONLY NOW (2026-10-14, b9)"
CMD grep -n "SEN_CLIENT_BROAD_READ_ROLES = \|MANAGEMENT_ROLES = " api/sd-data.js api/sen-auth.js
    api/sd-data.js:6608  SEN_CLIENT_BROAD_READ_ROLES = owner, billing, coordinator, scheduler
    api/sen-auth.js:74   MANAGEMENT_ROLES          = owner, billing
CMD grep -n "sairnsenior:" api/_lib/auth.js
    222  sairnsenior: ['owner', 'scheduler', 'coordinator', 'billing', 'caregiver']
```

```
CMD grep -n "MANAGEMENT_ROLES = \|BROAD_READ_ROLES = " api/rf-auth.js
    133  MANAGEMENT_ROLES = owner, admin
    134  BROAD_READ_ROLES = owner, admin, estimator
CMD grep -n "sairnroofing:" api/_lib/auth.js
    253  sairnroofing: ['owner', 'admin', 'estimator', 'foreman', 'crew']
CMD api/sd-data.js:8441 / :8495 -- the two rf write gates
    rf_cert_rules    write -> rfAuth.MANAGEMENT_ROLES   ("Only management can change licensing rules")
    rf_certifications write -> rfAuth.MANAGEMENT_ROLES  ("Only management can record a certification")
```

**SO THE TWO APPS ALREADY AGREE, AND THAT IS THE ARGUMENT FOR LOOKING AT THEM
TOGETHER:** SAIRNroofing has been management-only on both certification
resources since 2026-08-24, and hank's b9 moved SAIRNsenior to the same stance.
**The question is whether the agreement is right or merely tidy** — a home-care
agency's coordinators *are* the intake desk, while a roofing company's
estimators are not the certification clerk.

| app | resource | read today | write today | what the record is |
|---|---|---|---|---|
| sen | `sen_referrals` | owner, billing, coordinator, scheduler | **owner, billing** | a logged referral — an intake event |
| sen | `sen_referral_sources` | same | **owner, billing** | the list of who refers to us |
| sen | `sen_applicants` | same | **owner, billing** | a caregiver applicant |
| sen | `sen_training_records` | same | **owner, billing** | *this* caregiver completed *that* training |
| sen | `sen_training_rules` | same | **owner, billing** | the RULE deciding whether a caregiver is compliant |
| rf | `rf_certifications` | owner, admin, estimator | **owner, admin** | *this* employee holds *that* certification |
| rf | `rf_cert_rules` | owner, admin, estimator | **owner, admin** | the state licensing RULE |

---

## 2. THE DISTINCTION THE OPTIONS TURN ON — a RULE is not a RECORD

**Two of the seven decide what compliant means; five record that something
happened.** `sen_training_rules` and `rf_cert_rules` are policy: change one and
every caregiver's or crew member's compliance status can flip without anybody
touching their record. **The other five are operational data entry.**

**Nobody is proposing coordinators write the rules.** The options differ only
on the five operational records.

---

## 3. OPTION A — COORDINATORS ALLOWED (the operational records open, the rules closed)

| resource | write roles |
|---|---|
| `sen_referrals` | owner, billing, **coordinator**, **scheduler** |
| `sen_referral_sources` | owner, billing, **coordinator** |
| `sen_applicants` | owner, billing, **coordinator** |
| `sen_training_records` | owner, billing, **coordinator** |
| `sen_training_rules` | **owner, billing only** |
| `rf_certifications` | owner, admin, **estimator** |
| `rf_cert_rules` | **owner, admin only** |

**THE CASE FOR IT.** The person who takes the phone call is the coordinator.
Under Option B a referral arrives, the coordinator cannot log it, and it lives
in a notebook until a manager is free — **which is how a referral is lost, and
a lost referral is lost revenue nobody can audit.** Same for a training
certificate handed over at a shift change.

**THE CASE AGAINST IT.** `sen_training_records` is one hop from compliance: a
coordinator who records a training that did not happen makes a non-compliant
caregiver look compliant, and the rule that evaluates it is untouched and
innocent. **Option A relies on the record being auditable rather than
restricted.**

**WHAT OPTION A MUST CARRY TO BE SAFE — not optional, and it is one line each:**
`updated_by` from the verified session on every one of the five, so a
coordinator-entered record is attributable. **If `updated_by` is not already
written on all five, Option A is not ready and Option B is the correct interim
state.**

---

## 4. OPTION B — MANAGEMENT-ONLY (what `a6fa37a3` landed)

| resource | write roles |
|---|---|
| all five `sen_*` | owner, billing |
| both `rf_*` | owner, admin |

**THE CASE FOR IT.** One rule, no per-resource judgement, and the narrowest
surface on records that feed compliance. **It is also already true**, so
choosing it costs nothing and breaks nothing.

**THE CASE AGAINST IT.** It makes the intake desk ask permission to do its job,
and the pressure that creates is not theoretical: **the predictable workaround
is a shared manager login**, which destroys the attribution the narrowing was
for. **An access rule that is routinely inconvenient becomes an access rule
that is routinely bypassed.**

**WHAT OPTION B MUST CARRY:** nothing. It is the status quo. **But the support
burden should be measured rather than assumed away** — if coordinators are
asking managers to log referrals daily, Option B is failing quietly.

---

## 5. ONE PLACE IN CODE — a per-resource map, not a role check per branch

**Both options are the same code shape.** The map is the decision; the branches
read it.

```js
// api/sd-data.js, beside SEN_REFERRAL_RESOURCES (:6721) -- or better, exported
// from api/sen-auth.js next to MANAGEMENT_ROLES, so one file names SAIRNsenior's
// roles. The rf half goes beside rfAuth's sets the same way.
const SEN_REFERRAL_WRITE_ROLES = {
  sen_referrals:        SEN_INTAKE_WRITE_ROLES,     // Option A: + coordinator, scheduler
  sen_referral_sources: SEN_INTAKE_WRITE_ROLES,     // Option B: = MANAGEMENT_ROLES
  sen_applicants:       SEN_INTAKE_WRITE_ROLES,
  sen_training_records: SEN_INTAKE_WRITE_ROLES,
  sen_training_rules:   senAuth.MANAGEMENT_ROLES,   // RULE -- unchanged either way
};

// the branch, once, replacing the single role test:
const allowed = SEN_REFERRAL_WRITE_ROLES[resource];
if (!allowed) {                        // a NEW resource with no row is a REFUSAL
  res.status(500).json({ error: { code: 'WRITE_MAP_MISSING',
    message: 'This resource has no write policy. Refusing rather than guessing.' } });
  return;
}
if (!allowed[session.role]) { res.status(403).json({ error: { code: 'FORBIDDEN', … } }); return; }
```

**THREE PROPERTIES THAT MATTER MORE THAN THE OPTION CHOSEN:**

1. **A resource with no row in the map is a 500 refusal, not a pass.** The map
   that replaced a ternary in `SEN_REFERRAL_SETUP_FILE` (`:6731`) was adopted
   for exactly this reason — hank's own comment: *"A map goes stale loudly (a
   missing key is visible) rather than quietly naming the wrong file."*
2. **Switching options is editing ONE constant** (`SEN_INTAKE_WRITE_ROLES`),
   not seven branches. That is what makes the decision cheap to reverse, which
   is what makes it safe to make now.
3. **The rule resources are named explicitly in the map**, so "management-only"
   for them survives a careless edit to the intake set.

---

## 6. ONE TEST — table-driven, both options expressible, routed to cody

```js
// tests/sen_rf_write_map.test.js
// THE MAP IS THE SUBJECT. One table, every resource x every role, so a change
// to the policy changes ONE table here and nothing else.
const CASES = [
  // resource,             role,          expect
  ['sen_referrals',        'coordinator', OPTION === 'A' ? 200 : 403],
  ['sen_referrals',        'owner',       200],
  ['sen_referrals',        'caregiver',   403],   // never, in either option
  ['sen_training_records', 'coordinator', OPTION === 'A' ? 200 : 403],
  ['sen_training_rules',   'coordinator', 403],   // RULE -- 403 in BOTH options
  ['sen_training_rules',   'billing',     200],
  ['rf_certifications',    'estimator',   OPTION === 'A' ? 200 : 403],
  ['rf_cert_rules',        'estimator',   403],   // RULE -- 403 in BOTH options
  ['rf_cert_rules',        'crew',        403],
];
```

**FOUR ARMS THAT ARE NOT IN THE TABLE AND MUST EXIST:**

| arm | asserts |
|---|---|
| **M1** | a resource **absent from the map** → **500 `WRITE_MAP_MISSING`**, and **nothing written**. The bad-input arm |
| **M2** | `sen_training_rules` and `rf_cert_rules` are **403 for every non-management role in both options** — the arm that must pass whichever way Michael picks |
| **M3** | a 403 wrote **nothing** — assert the upstream call count is zero, not just the status. A 403 that already wrote is the failure a status check cannot see |
| **M4** | **CONTROL:** every resource writes successfully for `owner` in both options. A map that locks the owner out is a map that gets deleted |

**M2 and M4 are the over-refusal guards; M1 is the bad input; M3 is the one
most suites omit.**

---

## 7. WHAT THIS SPEC DOES NOT DO

* **It does not pick.** Option B is running; Option A is one constant away.
* **It does not touch the READ side.** Reads stay as they are in both options —
  this is a write map.
* **It does not add `updated_by`.** §3 states it as Option A's precondition; if
  it is missing on any of the five, Option A is not ready.
* **It does not measure the support burden.** Whether coordinators are
  currently asking managers to log referrals is a question for the business,
  and it is the one fact that would settle this without anybody's opinion.
* **It does not touch `api/`, `sql/` or `tests/`.**
