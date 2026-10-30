# cc b80: Tier A review of cody b68 (2026-10-30T09:00:48Z)
VERDICT: SOUND-WITH-GAPS (MEDIUM)

Reviewed at HEAD `47f40e2b`. Changes under review: `e22c9cd0` (13 licence guards, case-only
difference is the same licence; `tests/licence_guard_legacy_device.js` L5/L6) and `51d9b401`
(sairngrounds `gcdMarkShotEnd` snapshots the shot start before the GPS wait;
`tests/sairngrounds_save_reentry.js` GS1/GS2). Nothing in the working tree was modified; every
ablation and probe ran on copies in the session scratchpad. No database was queried.

**Summary.** Both fixes do what they say, and both tests have teeth (each ablation goes RED).
The per-app read/write forms all match (0 of 13 mismatched). No evidence was found that two
distinct licences can differ only in case. Three findings:

| # | Sev | Where | One line |
|---|---|---|---|
| F1 | MEDIUM | `sairngrounds.html:3098-3117` | **Introduced by 51d9b401.** END now survives an End-round / Arrive pressed during its GPS wait, and saves its stale `round` over theirs: the round close or hole arrival is silently reverted on a Tier A resource (`grd_rounds`). Before the fix END threw and the other write survived. |
| F2 | LOW | `sairnfreedom.html:2936-2949`, guard `sfLicenceGuard` at `:2635` | cc b76 F1 is not closed in sairnfreedom: after one failed `check_license` the key is removed but the fingerprint kept, so the same licence retyped in another case is still offered the "DIFFERENT licence" wipe. Pre-existing, not introduced. |
| F3 | LOW (latent) | `api/_lib/license.js:186-197`; DB `license_keys` | Nothing STRUCTURAL stops a case-only duplicate key: `license_keys_key_key` is `UNIQUE (key)`, case-sensitive. Today's safety rests on an issuance convention (all 30 minted keys upper-case, no runtime issuer). If a duplicate were ever minted, the loosened guard lets licence B open A's local data. |

---

## 1. Can two DISTINCT licences differ only in case?

**Server lookup order** — exact key first, upper-case retry only on a miss:

```
$ sed -n 183,199p api/_lib/license.js
  let rows = await lookup(key);
  // `key_normalised` is reported so a caller that cares can tell a canonical
  // hit from a case-corrected one. It is NOT a refusal signal: nothing refuses
  // on it, and adding a refusal here would re-create the 401 this removes.
  out.key_normalised = false;
  if (rows.length === 0) {
    const upper = key.toUpperCase();
    if (upper !== key) {
      rows = await lookup(upper);
      if (rows.length > 0) {
        out.key = upper;
        out.license_hash = hashLicense(upper);
        out.key_normalised = true;
      }
    }
  }
  if (rows.length === 0) {
    return out; // valid stays false — unknown key
  }
```

So if both `abc` and `ABC` existed as rows, `abc` resolves to the `abc` row and `ABC` to the
`ABC` row: **exact wins, they are two licences**, and the client guard (which now calls them the
same) would let one open the other's local data. Whether that can happen turns entirely on
whether such rows can exist.

**Runtime issuance: none.** No API handler writes `license_keys`; the only REST use is the
lookup above. The Stripe webhooks do not mint keys.

```
$ grep -rnE "rest/v1/license_keys" api/ --include=*.js | grep -v test | grep -vE "select=|key=eq"
(no output)
$ grep -niE "licen|key" api/agent/stripe-webhook.js api/sairncash/stripe-webhook.js api/agent/register.js | grep -viE "stripe_secret|webhook_secret|apikey|api_key|SERVICE_KEY|idempot"
api/agent/stripe-webhook.js:42:// push with a hardcoded key.
api/sairncash/stripe-webhook.js:34://   3. An audit trail of billing events, keyed by Stripe's own event id.
api/sairncash/stripe-webhook.js:169:  // exceptional. Keying the audit entry by Stripe's own event id means a
api/sairncash/stripe-webhook.js:237:    const stripe = new Stripe(stripeKey, { apiVersion: STRIPE_API_VERSION });
api/agent/register.js:12:// REQUIRES: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set as Vercel env vars
api/agent/register.js:14:// Guardian check 22 blocks any push with a hardcoded key.
api/agent/register.js:38:    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
$ grep -rniE "update\s+(public\.)?license_keys" sql/ tools/ api/
sql/alf_sen_demo_license_seed_2026-09-17.sql:178:-- update public.license_keys
sql/sc-pinnacle-2026-trial-extend.sql:58:  execute $q$update public.license_keys set trial_ends_at = null
```

(Neither update touches `key`.) **Hand-minted issuance: all upper-case, no collisions.** Every
`insert into public.license_keys` in `sql/` (30 distinct literal keys, from a Python extraction of
each insert's VALUES/SELECT first column):

```
$ python - <<'EOF'   # extract the first-column literal of every insert into license_keys under sql/
...
EOF
30 distinct literal first-column values
'ALF-AUDIT-0002' UPPER 1      'LEG-AUDIT-2026' UPPER 1      'SC-AUDIT-2026' UPPER 1
'ALF-AUDIT-2026' UPPER 1      'LEG-PINNACLE-2026' UPPER 1   'SCP-DEMO-2026' UPPER 1
'ALF-PINNACLE-2026' UPPER 1   'MECH-AUDIT-2026' UPPER 2     'SD-AUDIT-2026' UPPER 1
'ALF-TEST-2026' UPPER 1       'MECH-PINNACLE-2026' UPPER 1  'SD-PARTNER-2026' UPPER 1
'DNT-PINNACLE-2026' UPPER 1   'RF-AUDIT-0002' UPPER 1       'SDN-PINNACLE-2026' UPPER 1
'GRD-DEMO-2026' UPPER 1       'RF-AUDIT-2026' UPPER 1       'SEN-AUDIT-0002' UPPER 1
'LAW-AUDIT-2026' UPPER 2      'SB-PINNACLE-2026' UPPER 1    'SEN-AUDIT-2026' UPPER 1
'LAW-PINNACLE-2026' UPPER 1   'SB-TEST-2026' UPPER 1        'SEN-PINNACLE-2026' UPPER 1
'LAW-TEST-2026' UPPER 1                                     'SEN-TEST-2026' UPPER 1
'SF-PINNACLE-2026' UPPER 1    'SV-AUDIT-2026' UPPER 1       'SV-PINNACLE-2026' UPPER 1
'VERIFY-ONCONFLICT-2026-08-28' UPPER 1
case-only collisions: []
```

(Output re-flowed into columns; one value per line in the raw run, verbatim otherwise.)

**But the DB does not enforce it** (F3). The only constraint documented anywhere is a plain,
case-sensitive unique:

```
$ grep -rniE "license_keys.{0,60}(unique|primary|citext|lower\()|unique.{0,40}\(key\)|lower\(key\)|upper\(key\)" sql/ | head -3
sql/alf_sen_demo_license_seed_2026-09-17.sql:107:-- license_keys_key_key, UNIQUE (key). DO NOTHING rather than DO UPDATE so an
sql/demo_license_keys_seed.sql:73:--      license_keys_key_key, UNIQUE (key). ON CONFLICT (key) is valid.
sql/license_seed_onconflict_verify_2026-08-28.sql:35:-- EXPECT: a row `license_keys_key_key | u | UNIQUE (key)`.
```

No tracked `CREATE TABLE license_keys` exists (`sql/demo_license_keys_seed.sql:67` says so), so
the column type is not readable from source; nothing indicates `citext`.

**Where a lower-case key can even reach a guard.** 11 of 13 gates upper-case the entry before
the guard and before storing (`var k=($('gkey').value||'').trim().toUpperCase();`, e.g.
`sairndental.html:1850`), so on those a lower-case row would be unreachable from a fresh entry
and a lower-case stored key can only come from an older gate. `sairncode.html:3425`
(`var key = keyEl.value.trim();`) and `sairnfreedom.html:2937` (`var v=($('lic').value||'').trim();`)
pass the case through. sairncode validates with the server BEFORE the guard
(`sairncode.html:3466-3483`), freedom after (`:2940-2951`).

**Conclusion for (1):** on the evidence in the repo, no two distinct licences differ only in case,
so the client guard cannot today let licence B open licence A's data by case. That rests on an
issuance convention, not a constraint. The SQL below proves the live state; the structural fix
(owner: platform / Michael to apply) is a unique index on `upper(key)`, e.g.
`create unique index license_keys_key_upper_uniq on public.license_keys (upper(key));`.
**That index is a recommendation only — NOT written to `sql/` and NOT run.**

### Read-only proof SQL — NOT RUN

Returns counts only, no key material. Table `public.license_keys`, column `key`.

```sql
-- cc b80: NOT RUN. Read-only. Proves no two license_keys rows differ only in case.
-- EXPECT: case_only_duplicate_groups = 0. keys_not_upper_case is context (expected 0).
select
  (select count(*)
     from (select upper(key)
             from public.license_keys
            group by upper(key)
           having count(*) > 1) g)                                 as case_only_duplicate_groups,
  (select count(*) from public.license_keys where key <> upper(key)) as keys_not_upper_case,
  (select count(*) from public.license_keys where key <> btrim(key)) as keys_with_edge_whitespace;
```

---

## 2. Per-app: does the guard read the key the way the gate writes it?

```
$ grep -nE "^\s*(localStorage\.setItem\('(dnt|sen|alf|bld|sdn|rf)_license_key',k\)|try\{localStorage\.setItem\('law_license_key',k\)|localStorage\.setItem\('leg_license_key',k\)|st\('(sb|grd)_lic',k\)|scpSt\('scp_lic',k\)|st\(K_LIC, v\))" sairn*.html
sairnbiz.html:1850:  st('sb_lic',k);$('gate').style.display='none';$('pin').classList.add('on');
sairnbuild.html:2936:  localStorage.setItem('bld_license_key',k);
sairncare.html:1885:  localStorage.setItem('alf_license_key',k);
sairndental.html:1854:  localStorage.setItem('dnt_license_key',k);
sairndesign.html:1469:  localStorage.setItem('sdn_license_key',k);
sairnfreedom.html:2940:  st(K_LIC, v);
sairngrounds.html:1945:  st('grd_lic',k);$('gate').style.display='none';$('role').classList.add('on');
sairnlaw.html:1798:  try{localStorage.setItem('law_license_key',k);}catch(e){
sairnlegacy.html:1910:  localStorage.setItem('leg_license_key',k);
sairnroofing.html:1415:  localStorage.setItem('rf_license_key',k);
sairnscape.html:2297:  scpSt('scp_lic',k);scp$('scp-gate').style.display='none';scp$('scp-role').classList.add('on');
sairnsenior.html:1769:  localStorage.setItem('sen_license_key',k);
$ grep -nE "localStorage\.setItem\('sc_license_key', key\)" sairncode.html
3484:                localStorage.setItem('sc_license_key', key);
$ grep -nE "K_LIC='sf_license_key'" sairnfreedom.html
2546:    K_PERMIT_FLAGS='sf_permit_flags', K_LIC='sf_license_key',
$ grep -nE "localStorage\.setItem\(k,\s*JSON\.stringify\(v\)\)" sairnbiz.html sairngrounds.html sairnscape.html sairnfreedom.html
sairnbiz.html:1315:  try{localStorage.setItem(k,JSON.stringify(v));okWrite=true;}
sairngrounds.html:1543:  try{localStorage.setItem(k,JSON.stringify(v));return true;}
sairnscape.html:2036:  try{localStorage.setItem(k,JSON.stringify(v));return true;}
sairnfreedom.html:1842:    localStorage.setItem(k, JSON.stringify(v));
```

`grdStampChanged` (`sairngrounds.html:1509`) and `scpStampChanged` (`sairnscape.html:2002`) begin
`if(...||!Array.isArray(v))return v;`, so a string key is stored as `JSON.stringify(k)` unaltered.
Each app has exactly ONE writer of its key (the gate) plus server-reject `removeItem`s; no other
path writes it (grep of each storage-key name, every hit read).

| App | Storage key | Gate write (form) | Guard `sameKey` read (form) | Match |
|---|---|---|---|---|
| sairndental | `dnt_license_key` | `:1854` raw | `:1809` raw `getItem` | yes |
| sairnsenior | `sen_license_key` | `:1769` raw | `:1724` raw | yes |
| sairncare | `alf_license_key` | `:1885` raw | `:1840` raw | yes |
| sairnbuild | `bld_license_key` | `:2936` raw | `:2891` raw | yes |
| sairndesign | `sdn_license_key` | `:1469` raw | `:1424` raw | yes |
| sairnlaw | `law_license_key` | `:1798` raw | `:1749` raw | yes |
| sairnlegacy | `leg_license_key` | `:1910` raw | `:1865` raw | yes |
| sairnroofing | `rf_license_key` | `:1415` raw | `:1370` raw | yes |
| sairncode | `sc_license_key` | `:3484` raw | `:3381` raw | yes |
| sairnbiz | `sb_lic` | `:1850` `st()` → JSON `:1315` | `:1805` `JSON.parse` | yes |
| sairngrounds | `grd_lic` | `:1945` `st()` → JSON `:1543` | `:1900` `JSON.parse` | yes |
| sairnscape | `scp_lic` | `:2297` `scpSt()` → JSON `:2036` | `:2611` `JSON.parse` | yes |
| sairnfreedom | `sf_license_key` | `:2940` `st(K_LIC)` → JSON `:1842` | `:2657` `JSON.parse` | yes |

**Mismatches: 0 of 13.** Test gap (not a defect): the suite's `APPS` table carries its own `json`
flag per app and writes fixtures in that form, so it proves the read matches the TEST's belief, not
the gate's write. The gate side is what this table adds.

## 3. Normalisation identical on both sides; fingerprint on a match

All 13 added hunks reduce to two shapes that differ only in the raw/JSON read:

```
$ python - <<'EOF'   # per file: added non-comment lines of e22c9cd0, extract read / fp var / compare
...
EOF
sairnbiz.html | read: JSON.parse(localStorage.getItem('sb_lic')) | fp-written: SB_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairnbuild.html | read: localStorage.getItem('bld_license_key') | fp-written: BLD_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairncare.html | read: localStorage.getItem('alf_license_key') | fp-written: ALF_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairncode.html | read: localStorage.getItem('sc_license_key') | fp-written: SC_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairndental.html | read: localStorage.getItem('dnt_license_key') | fp-written: DNT_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairndesign.html | read: localStorage.getItem('sdn_license_key') | fp-written: SDN_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairnfreedom.html | read: JSON.parse(localStorage.getItem('sf_license_key')) | fp-written: SF_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairngrounds.html | read: JSON.parse(localStorage.getItem('grd_lic')) | fp-written: GRD_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairnlaw.html | read: localStorage.getItem('law_license_key') | fp-written: LAW_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairnlegacy.html | read: localStorage.getItem('leg_license_key') | fp-written: LEG_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairnroofing.html | read: localStorage.getItem('rf_license_key') | fp-written: RF_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairnscape.html | read: JSON.parse(localStorage.getItem('scp_lic')) | fp-written: SCP_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
sairnsenior.html | read: localStorage.getItem('sen_license_key') | fp-written: SEN_LIC_FP | cmp: typeof sameKey === 'string' && sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()
distinct normalised hunk shapes: 2
4 ['sairnbiz.html', 'sairnfreedom.html', 'sairngrounds.html', 'sairnscape.html']
9 ['sairnbuild.html', 'sairncare.html', 'sairncode.html', 'sairndental.html', 'sairndesign.html', 'sairnlaw.html', 'sairnlegacy.html', 'sairnroofing.html', 'sairnsenior.html']
```

Compare: `trim().toUpperCase()` on both stored and entered — identical in all 13. On a match the
guard writes `next` = fingerprint of `k`, the exact value the gate then stores, so the next
`prev === next` comparison is consistent. **But the fingerprint itself is NOT case-normalised.**
In the 11 upper-casing apps that is harmless (`k` is always upper). In sairncode and sairnfreedom
`k` keeps the typed case, so the fingerprint is case-sensitive and the new check only rescues a
case difference while the stored key is still present — which is F2.

Also checked and clean: the new branch trusts the stored key over the fingerprint. A divergence
(stored key from licence B, fingerprint from A) would pass B without asking, but the only writer of
each key is the gate immediately after the guard, and the only other mutation is a `removeItem`, so
divergence needs a failed `setItem` of the fingerprint (swallowed) followed by a successful write of
the key. Not reachable in practice; noted, no finding.

## 4. sairngrounds 51d9b401

`var start = gcdShotStart;` is taken before `await cmCaptureGps()` (`sairngrounds.html:3108`);
`if(gcdShotStart === start) gcdShotStart = null;` (`:3116`) clears only an unchanged start.
START / END / START quickly: both resolution orders are correct — GS1/GS2 drive START's fix landing
first; the scratch probe P3 drives END's fix landing first (shot from the tee, next start kept).
END/END is held by `gcdShotEnding` (`:3099`, arm MS4). START/START has no hold (last fix to land
wins); pre-existing, not in scope.

**F1 — the round snapshot is still taken before the wait.** `var round = gcdActiveRound();` and
`hole` (`:3100-3101`) are read before the await; `gcdActiveRound()` (`:2937`) returns a FRESH parse
of `grd_rounds`. If End round (`gcdEndRound`, `:3038`) or Arrive (`gcdArriveHole`, `:3053`) is
pressed during END's wait (up to `timeout:8000`, `:2673`), each saves its own fresh copy, then END's
`gcdSaveRound(round)` (`:3117`) writes the stale copy back over it — locally and via
`grdData('write','grd_rounds',round)` (`:2956`). Before 51d9b401, both of those actions null
`gcdShotStart` and END then threw on `gcdShotStart.accuracy_m`, so the other write survived (the shot
was lost, loudly in the console). The fix turned a crash into a silent revert.

## 5. Tests driven, and ablations

```
$ node tests/licence_guard_legacy_device.js ; echo "exit=$?"
  ok   sairnfreedom.html L6: fingerprint of the lower-case key recorded, same licence re-entered in upper case -> no question

ok  licence guard (legacy device), 13 apps: 78 passed, 0 failed, 0 could not run
exit=0
$ node tests/sairngrounds_save_reentry.js ; echo "exit=$?"
  ok   GS2 ...and the next shot's start, marked meanwhile, is kept, not thrown away

ok  sairngrounds save re-entry: 48 passed, 0 failed
exit=0
```

**Ablation A1 — revert upper-casing in one guard.** The licence test reads apps from
`path.join(__dirname, '..', file)`, so it cannot take a path; it was copied with all 13 apps into
`<scratchpad>/abl1/{tests/,}` (control run there: 78/0, exit 0), and only the scratch
`sairndental.html` was edited (`sameKey.trim().toUpperCase() === String(k).trim().toUpperCase()` →
`sameKey.trim() === String(k).trim()`, asserted exactly 1 occurrence):

```
$ node tests/licence_guard_legacy_device.js > abl.out; echo "ablation exit=$?"; grep -E "FAIL|^(ok|FAILED) " abl.out
ablation exit=1
  FAIL sairndental.html L5: no fingerprint, the same licence stored in lower case -> no question, nothing removed
  FAIL sairndental.html L6: fingerprint of the lower-case key recorded, same licence re-entered in upper case -> no question
FAILED  licence guard (legacy device), 13 apps: 76 passed, 2 failed, 0 could not run
```

**Ablation A2 — JSON read made raw** (dental restored; scratch `sairngrounds.html` read changed to
`localStorage.getItem('grd_lic')`):

```
json-read ablation exit=1
  FAIL sairngrounds.html L5: no fingerprint, the same licence stored in lower case -> no question, nothing removed
  FAIL sairngrounds.html L6: fingerprint of the lower-case key recorded, same licence re-entered in upper case -> no question
FAILED  licence guard (legacy device), 13 apps: 76 passed, 2 failed, 0 could not run
```

**Ablations B1-B3 — sairngrounds.** The suite takes the app path as `argv[2]`, so the real test
file ran against scratch copies: `a` = snapshot moved after the await (conditional clear kept),
`b` = unconditional clear only, `c` = both (the pre-fix code).

```
$ for f in a b c; do node tests/sairngrounds_save_reentry.js <scratchpad>/abl2/$f.html > $f.out; echo "$f exit=$?"; grep -E "FAIL|^(ok|FAILED) " $f.out; done
a exit=1
  FAIL GS1 the shot is measured from the tee it was started at, not from the next start
  FAIL GS2 ...and the next shot's start, marked meanwhile, is kept, not thrown away
FAILED  sairngrounds save re-entry: 46 passed, 2 failed
b exit=1
  FAIL GS2 ...and the next shot's start, marked meanwhile, is kept, not thrown away
FAILED  sairngrounds save re-entry: 47 passed, 1 failed
c exit=1
  FAIL GS1 the shot is measured from the tee it was started at, not from the next start
  FAIL GS2 ...and the next shot's start, marked meanwhile, is kept, not thrown away
FAILED  sairngrounds save re-entry: 46 passed, 2 failed
```

`git status --short` after all of the above: only ` M docs/tier-a-reviews.json` (pre-existing).

**Probe (scratch `probe_b80.js`, lifts the REAL shipped functions into a vm, stubs only storage,
GPS, toasts and `grdData`).** Run at HEAD and against `51d9b401^:sairngrounds.html` /
`e22c9cd0^:sairnfreedom.html` / `e22c9cd0^:sairndental.html`:

```
--- HEAD:
P1 sairnfreedom: a failed check_license removes the key but keeps the fingerprint
  FAIL P1 same licence in another case after a failed check is NOT offered a wipe  {"fpKept":true,"keyGone":true,"asked":1,"recordsLeft":false}
  ok   P1-control sairndental, same sequence: no question (gate upper-cases, fingerprint is of the upper-case key)
P2 sairngrounds: another round write lands while END waits for its fix
  FAIL P2 End round pressed during END's fix survives END's save  {"writtenBeforeEndResolved":true,"afterEnd":false,"shots":[1]}
  FAIL P2 Arrive at next hole pressed during END's fix survives END's save  {"writtenBeforeEndResolved":true,"afterEnd":false,"shots":[1]}
P3 sairngrounds: START during END, END's fix lands FIRST (the ordering GS1/GS2 do not drive)
  ok   P3 shot from the tee, next start kept

probe: 2 passed, 3 failed
exit=1
--- PRE (51d9b401^ / e22c9cd0^):
P1 sairnfreedom: a failed check_license removes the key but keeps the fingerprint
  FAIL P1 same licence in another case after a failed check is NOT offered a wipe  {"fpKept":true,"keyGone":true,"asked":1,"recordsLeft":false}
  ok   P1-control sairndental, same sequence: no question (gate upper-cases, fingerprint is of the upper-case key)
P2 sairngrounds: another round write lands while END waits for its fix
       END threw: Cannot read properties of null (reading 'accuracy_m')
  ok   P2 End round pressed during END's fix survives END's save
       END threw: Cannot read properties of null (reading 'accuracy_m')
  ok   P2 Arrive at next hole pressed during END's fix survives END's save
P3 sairngrounds: START during END, END's fix lands FIRST (the ordering GS1/GS2 do not drive)
  ok   P3 shot from the tee, next start kept

probe: 4 passed, 1 failed
exit=1
```

---

## Findings

**F1 — MEDIUM — silent revert of a round close / hole arrival during END's GPS wait.**
`sairngrounds.html:3098-3117` (`gcdMarkShotEnd`), with `gcdActiveRound` `:2937` and `gcdSaveRound`
`:2940-2956`. Failure scenario: player presses END, then within the GPS wait (up to 8 s) presses
"Arrive" at the next hole (or "End round"). Arrive saves a round with hole 2; END's fix lands and
saves its pre-wait copy, which has one hole. Result: hole 2's arrival and hole 1's `completed_at`
are gone (or `finished_at` is gone and the closed round reopens), the user was told "Arrived at
Hole 2" / "Round closed", and the stale copy is also pushed to the server. `grd_rounds` is Tier A
(`docs/CRITICALITY-TIERS.md:404`). **Introduced by 51d9b401**: probe P2 passes on the parent (END
threw) and fails at HEAD. Cause tag: `stale-snapshot-across-await` (lost update). Fix shape (not
applied): re-read `gcdActiveRound()` after the await, attach the shot to the hole whose
`zone_id` matched at press time, and drop the shot if the round was closed. Add an arm that presses
Arrive / End round during a pending END. Owner: **cody**.

**F2 — LOW — cc b76 F1 still reachable in sairnfreedom after a failed key check.**
`sairnfreedom.html:2936-2951` (`sfUnlock`) and the guard `sfLicenceGuard` at `:2635`. Failure scenario: device
holds the key `lic-aaaa-2026` and local records; the user re-enters it while offline,
`check_license` fails (`sfAuth` returns `ok:false` on a network error, `:2727-2728`) and
`removeItem(K_LIC)` runs, leaving the fingerprint; the user then types `LIC-AAAA-2026` — the guard
finds no stored key, the fingerprints differ by case, and it asks "DIFFERENT licence"; OK deletes
the licence's own local-only records (probe P1, `asked:1, recordsLeft:false`). The same sequence on
sairndental does not ask (P1-control). Pre-existing, not introduced by e22c9cd0, but the obligation
claimed to close F1 in all 13. Cause tag: `case-sensitive-fingerprint` (fingerprint of the
un-normalised key). Fix shape (not applied): have `sfUnlock` upper-case like the other 11, or
fingerprint the normalised key. sairncode also passes case through but validates before the guard
and never removes the key, so it is not reachable there. Owner: **cody**.

**F3 — LOW (latent) — case-only uniqueness is a convention, not a constraint.**
`api/_lib/license.js:186-197`; DB `public.license_keys`, constraint `license_keys_key_key UNIQUE
(key)`. Failure scenario: a future mint inserts `abc-…` beside `ABC-…`. The server resolves each
exactly (two licences); a device whose stored key is one opens the other's local data without a
question, because the guard now equates them. No such row exists in any tracked mint; the live state
is unproven until the SQL above is run. Cause tag: `invariant-by-convention`. Fix shape: unique
index on `upper(key)` (recommendation; not written, not run). Owner: **Michael** to run the
read-only SQL; platform owner for the index.
