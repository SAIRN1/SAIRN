# Demo and test credentials — every SAIRN app, one owner login each

**Compiled 2026-09-03. State measured against the live platform, not read off any
tracking file.**

Michael has never held credentials for any SAIRN app's demo or test licence. The
work logs record the consequence repeatedly — *"both licenses already have an
owner account bootstrapped from an earlier session and I don't have those PIN
credentials"* — and the effect is that live click-through verification has been
substituted for, worked around, or skipped for weeks.

That cost is not hypothetical. On 2026-09-03 two production bugs were found
**only** because one licence, `SB-TEST-2026`, happened to have a documented PIN:
a session gate that returned 403 to every non-StoneDesk caller, and an app
allow-list that refused a real app as unknown. Both had a full green test suite
behind them. Neither was findable without signing in.

---

## ⚠ Before the table: run the SQL first

None of the PINs below work until **`sql/demo_owner_credentials_2026-09-03.sql`**
has been run in the Supabase SQL editor. It is one transaction, idempotent, and
carries the recoverability guard.

Run it as **its own paste**, not appended to anything else. The editor reports
success for the statements it did run, so a partial apply looks identical to a
full one — that is the failure the SAIRNroofing cleanup actually hit on
2026-08-26.

---

## The credentials

Employee id is **`sairn-demo-owner`** on every one of them. Role is `owner`
everywhere except SAIRNcode, which has no `owner` role at all — its provisioning
role is `admin`, and a list that assumed otherwise would have handed you a
credential that cannot provision anything.

| App | Licence key | Employee ID | PIN | Role | Sign-in endpoint |
|---|---|---|---|---|---|
| StoneDesk | `SD-AUDIT-2026` | `sairn-demo-owner` | `31840627` | owner | `/api/sd-auth` |
| StoneDesk (partner demo) | `SD-PARTNER-2026` | `sairn-demo-owner` | `52719084` | owner | `/api/sd-auth` |
| SAIRNbiz | `SB-TEST-2026` | `sairn-demo-owner` | `84350271` | owner | `/api/sb-auth` |
| SAIRNbiz (demo) | `SB-PINNACLE-2026` | `sairn-demo-owner` | `60417293` | owner | `/api/sb-auth` |
| SAIRNgrounds | `GRD-DEMO-2026` | `sairn-demo-owner` | `27593016` | owner | `/api/grd-auth` |
| SAIRNscape | `SCP-DEMO-2026` | `sairn-demo-owner` | `73018452` | owner | `/api/scp-auth` |
| SAIRNcare | `ALF-TEST-2026` | `sairn-demo-owner` | `19546830` | owner | `/api/alf-auth` |
| SAIRNlaw (test) | `LAW-TEST-2026` | `sairn-demo-owner` | `46201975` | owner | `/api/law-auth` |
| SAIRNlaw (demo) | `LAW-PINNACLE-2026` | `sairn-demo-owner` | `80362514` | owner | `/api/law-auth` |
| SAIRNdental | `DNT-PINNACLE-2026` | `sairn-demo-owner` | `25741609` | owner | `/api/dnt-auth` |
| SAIRNdesign | `SDN-PINNACLE-2026` | `sairn-demo-owner` | `63089127` | owner | `/api/sdn-auth` |
| SAIRNlegacy | `LEG-PINNACLE-2026` | `sairn-demo-owner` | `41957382` | owner | `/api/leg-auth` |
| SAIRNmechanical | `MECH-PINNACLE-2026` | `sairn-demo-owner` | `58203764` | owner | `/api/mech-auth` |
| SAIRNsenior | `SEN-PINNACLE-2026` | `sairn-demo-owner` | `90128473` | owner | `/api/sen-auth` |
| SAIRNroofing | `RF-AUDIT-2026` | `sairn-demo-owner` | `17462059` | owner | `/api/rf-auth` |
| SAIRNbuild | `BLD-PINNACLE-2026` | `sairn-demo-owner` | `35810946` | owner | `/api/bld-auth` |
| SAIRNcode | `SC-PINNACLE-2026` | `sairn-demo-owner` | `72694103` | **admin** | `/api/sc-auth` |

Signing in from a terminal, for any row above:

```
curl -s -X POST https://sairn.vercel.app/api/scp-auth \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer SCP-DEMO-2026' \
  -d '{"action":"login","employee_id":"sairn-demo-owner","pin":"73018452"}'
```

In a browser: open the app, enter the licence key at the gate, then the employee
id and PIN at the sign-in screen.

---

## Two licences are deliberately NOT here

| Licence | Why not |
|---|---|
| `SD-PINNACLE-2026` | Appears in **no seed file** and holds **real named accounts** — `cmonsul` (Carolyn Monsul, a named person) and `owner` (Michael). A published PIN cannot safely live beside those. This is not a new judgement: `sql/stonedesk_recovery_admin_seed.sql` reached it in August and moved StoneDesk's verification credential to `SD-AUDIT-2026` for exactly this reason. Use `SD-AUDIT-2026`. |
| `RF-PINNACLE-2026` | Also in no seed file, and the open-work index records real employee rows and a recoverability incident on it. Use `RF-AUDIT-2026` once its licence seed is run — see below. |

**If you need to get into either of those, the answer is a password reset on that
licence, not a published PIN.** Ask and I will write the reset SQL.

---

## What the probe found on the way

Every licence was probed with `bootstrap`, which answers definitively: `409
ALREADY_PROVISIONED` means credential rows exist, `200` means there were none,
`401 INVALID_LICENSE` means the licence key itself was never seeded.

**Three licences had no credential rows at all — nobody could sign in to them,
and nothing had noticed:**

- `LAW-PINNACLE-2026`
- `SDN-PINNACLE-2026`
- `SEN-PINNACLE-2026`

That is worth knowing separately from the credential gap. These are not licences
whose PIN was lost; they are licences that never had a login. `SAIRNlaw`'s in
particular is the app CLAUDE.md calls the canonical demo licence.

**One licence does not exist:**

- `RF-AUDIT-2026` returns `401 INVALID_LICENSE`, which means
  `sql/sairnroofing_audit_license_seed.sql` was written and **never run**. Its
  row in the credentials SQL is inert until that seed runs — it does not error,
  it simply belongs to a licence hash nothing will ever present. Run that seed
  first if you want SAIRNroofing verification on an audit licence rather than on
  the customer one.

**One app has no employee auth at all:**

- `SAIRNvet` (`SV-PINNACLE-2026`) has no `*-auth.js` endpoint anywhere in `api/`.
  There is no login to give you because there is no login. Its data calls hit
  `sd-data`'s session gate and get 403. That is a real gap in that app, not a
  credentials problem, and it is not fixed here.

---

## Housekeeping owed

The state probe had to use `bootstrap` — it is the only call that can tell "no
rows" from "rows I cannot open" — and `bootstrap` **creates a row** when the
answer is the former. So three licences now carry an extra account called
`zz-state-probe-do-not-use`:

`LAW-PINNACLE-2026`, `SDN-PINNACLE-2026`, `SEN-PINNACLE-2026`.

They are deactivated through the API once the SQL above has run and
`sairn-demo-owner` exists to deactivate them with — a licence must never pass
through zero active provisioners, which is the trapdoor `RF-PINNACLE-2026` fell
into. They are **not** deleted: no delete path exists for credential rows, by
design.

---

## The trade this document makes, stated plainly

Every licence listed here is `plan = 'demo'` with a `*.example` customer email —
checked in the seed files, not assumed from the names. The "PINNACLE" keys are
named after the fictional demo company, not after a customer.

Publishing their PINs is the same trade `sql/stonedesk_recovery_admin_seed.sql`
already made and wrote down: **a credential nobody can find is a credential
nobody uses**, and the cost of the past several weeks has been verification not
happening at all. These licences hold no real business data, so a published PIN
costs nothing.

**That precondition is the entire basis for it.** The moment any licence here is
given to a real customer or loaded with real data, its row in the SQL must be
deleted and its PIN rotated. Nothing enforces that automatically, which is why
it is written here rather than assumed.
