# SAIRN handoff: cc, batch b40, 2026-10-21

**Six items, all six closed.** Two need a line of explanation: item 4 is
reported, not patched, because the dependency is not mine; item 5b was already
done in the file that holds the list. Nothing is half-finished, and **no
override** was used.

## 1. State

| | |
|---|---|
| Repo changes | the three deliverables only. `.claude/settings.local.json` is **untracked**, so the permission fix is local to this clone by design |
| Push | deliverables; see the report for the landing sha |
| Overrides | **NONE** |
| Context | in the digest, measured |

## 2. CLOSED

- **Items 1–2, the hover deny rules.** My clone's `settings.local.json` now
  has **13 deny entries, exactly hank's set**:
  - 8 `Edit`/`Write` rules on `SAIRN-hover/**` and `SAIRN-hover2/**`, in both
    the `//C:/…` and `~/…` spellings;
  - 5 Bash rules: `Bash(*SAIRN-hover*)`, `Bash(*sairn-hover2*)`,
    `Bash(*sairn-hover/*)`, `Bash(*sairn-hover\*)`, `Bash(*sairn-hover*)`.
  - **I ran a copy of `C:\Users\marsh\fix-deny.ps1` with `-cnotcontains`, as
    the dispatch asked.** The original uses `-notcontains`, which is
    case-insensitive and would have dropped `Bash(*sairn-hover*)` as a
    duplicate of `Bash(*SAIRN-hover*)`. The original file is unchanged.
  - Diffed before and after: only `permissions.deny` changed, and all 1423
    allow entries are untouched.
  - **Confirmed denied:** `ls` into both hover clones was refused, and `Edit`
    on `SECURITY.md` in both was refused ("in a directory that is denied").
  - **Not probed: `Write`.** A failed deny there would create a file inside an
    auditor clone. Its rules are spelled exactly like the `Edit` rules that
    refused.
- **Item 3:** no fix code was written in items 4–5, so no concept line was
  owed.
- **Item 4, Dependabot alert 5 (HIGH, open):** `node-forge` ≤1.4.0,
  GHSA-86w9-cpqp-85rv / CVE-2026-85393 (RSA PKCS#1 v1.5 signature
  verification). It is **transitive** in the root `package-lock.json`, through
  `firebase-admin` ^12.7.0. **No patched `node-forge` exists**
  (`first_patched_version` is null).
  - **Not mine.** The path manifest marks `package.json` / `package-lock.json`
    UNOWNED. The only consumer is `api/_lib/firebase-admin.js` (SAIRNcash's
    token minting), which is hank's api/.
  - The 2026-10-05 triage (`d788ee83`, `docs/2026-10-05-dependabot-high-triage.md`)
    made it a decision for the owner. I did not touch it.
  - **New fact:** `firebase-admin` **13.10.0** is the first release without
    `node-forge`. That is one major version up, not the two (14.5.0) that
    `npm audit` proposes. I could not run `npm ci` to check reachability; it
    was denied.
- **Item 5a, rt_stops SQL from b28:**
  - All three files are on origin (`cb0d94f5`).
  - **Applied, measured live** (read-only `pg_constraint` on sairn-platform):
    `rtstops_license_matches_route` (FK) and its helper
    `rtroutes_id_license_uniq` are PRESENT, `rtroutes_saved_sane` is GONE, and
    `rtroutes_saving_has_a_basis` is PRESENT.
  - The FK probe is a deliberately-raising read. Whether it was run is not
    observable, and with the FK present it would pass.
- **Item 5b, `SEN-AUDIT-2026` in `KNOWN_AUDIT_KEYS`:** **already done, in the
  file that holds the list.** `KNOWN_AUDIT_KEYS` is a tuple in
  `tools/audit_licence.py:106`. hank added `SEN-AUDIT-2026` in b35
  (`0ff033a3`, on origin) with its dated measurement. **I did not add it to
  CLAUDE.md.** CLAUDE.md is not where the list lives, and a second copy there
  is the hardcoded-list shape CLAUDE.md itself warns goes stale.
- **Item 6:** pushed and confirmed.

## 3. OPEN

- **Michael:** upgrade `firebase-admin` to 13.10.0 (with a mint test first,
  since there is none), or accept the risk with a named trigger.
- **Still routed:** hank (b40 barrier tests, keyboard close); fourth (review
  cc 2026-10-21T17:13:48Z). The OAuth upsert must set `consent_id`.
