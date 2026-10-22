# SAIRN handoff — hank b52 — 2026-10-22

**Subject:** Tier A review of fourth `847e89943`; the leg_settings defect plus a platform sweep for the fail-open
class; cc b50 test gaps on `2fe89f26` / `040ac5a9`; the rt_ app-boundary red. Written before the report, nothing
half-finished.

**Methodology concept (items 2 and 5):** *an answer that cannot be understood is not an empty answer. A row read
must prove it is a list before "no row" is believed, and a partial update merges onto what is stored, never onto
defaults. Before closing a fix, sweep every call site with the same shape.*

## 1. PUSHED STATE — NOT FORCED, LANDED
- `352176001` review: fourth b54 discharged.
- `6a3755cac` fix(sairnlegacy): leg_settings merge, plus 502 on an unreadable read.
- `e157ca8cb` test: b40 / b48 / app-boundary.
- `29739fe14` fix(platform): four more Tier A fail-open sites.
- `cd8c64c2d` bookkeeping: register records, Tier A obligation (assigned to cc), derived docs, bypass-log row.
- The handoff, report and digest are pushed after this file is written. Re-derive the tip.
- **Override used, said out loud:** `SAIRN_SKIP=external-files` (scoped, granted per attempt through
  `tools/gate_skip.py`). The only unindexed file was `g:\my drive\sairn-status\h1_countersign_repro.js`, which
  belongs to the hover auditor h1. A build agent must not index the auditor's work. cc b54 logged the same skip
  for the same file. Every other gate ran.

## 2. CLAIMS HELD
`leg-settings-api` (b52) is released at the end of the batch. fourth's `sairnlegacy` claim (F3 UI) was
respected: the work was scoped to api/ and Michael approved it.

## 3. THE ITEMS
**1. Tier A, fourth `847e89943` (= `76b475f58`) — DISCHARGED: DEFECT (one), otherwise SOUND.**
- **Defect:** `stonedesk.html:27173` renderVendor. The aria-label edit corrupted the quantity input to
  `value=""'+escHtml(cartQty)+'"`. After any re-render, every vendor quantity box shows empty while sdCart holds the
  quantity, and typing then replaces it.
- The fix is one character. **Routed to fourth** (the author, who holds the active stonedesk claim).
- Everything else holds:
  - 40 hunks classified: 33 style, 2 attribute, 4 new a11y code, 1 the defect;
  - no data path moved;
  - contrast claims hold (5.07 / 5.44 / 5.02 / 4.83 / 6.40);
  - 129 script blocks pass `node --check`;
  - a11y suite 22/22 at the commit, 25/25 at HEAD.

**2. leg_settings, cc b50 DEFECT on `38b2b506` — FIXED (`6a3755cac`).**
- A partial apprentice object now MERGES onto the stored policy (Michael's decision). The cross-list rule runs on
  the merged lists.
- An unparsable or non-list settings read → 502 UNREADABLE_SETTINGS on read and write.
- `api/b45-leg-settings-owner-write.test.js` 38/0: B1–B3 new; M4–M6 red. mustFail now counts only an
  AssertionError as a kill.
- **For fourth's F3 UI:** a partial `apprentice` object keeps the omitted keys. To CLEAR a list, send `[]`
  explicitly. Stated in the status note.

**5. Sweep (methodology item).** A read-only agent classified 63 row-or-null sites: OPEN 9, TRUTHFUL 13, CLOSED 38,
N/A 2, 1 already fixed. **Fixed in `29739fe14`, the Tier A OPEN ones:**
- the leg_ role gate: an unreadable OR HTTP-500 settings read → 502. Before, this fell to the wide default,
  which let an apprentice reach a forbidden type;
- the alf_family_contacts write's prior read → 502, where it used to re-stamp MAR consent provenance;
- sairncare-witness.js and sv-witness.js policy reads: a non-list → could-not-tell 503, where the two-person
  rule used to be dropped;
- law-auth.js loadEmployee: a non-list throws, and mfa_enroll refuses a token with no active row, where it
  used to switch 2FA off.

Evidence:
- `api/b52-unreadable-is-not-empty.test.js` 9/0. L1 and F1–F2 are driven; W1–W2 and A1 are SOURCE pins only;
  mutants M1–M3 go red.
- Related suites green: witness 38/0 and 41/0, sv-auth 52/0, cross-tenant dispatchers 418/0, all leg suites.
- `sd-data-family-contacts` 3 failures and `sairnlegacy_reservation_lock` 35/36 were already failing before
  this change.

**3. cc b50 gaps.**
- `2fe89f26`: b40 mustFail now counts only ArmFailure, and the suite is 27/0.
- `2fe89f26`, not done: the overlay's "none stored" message when every stored photo is filtered is in
  `stonedesk.html`, under fourth's active claim. **Held** (next step below).
- `040ac5a9`:
  - the unscoped-read mock now returns every agency's rows;
  - M5 (true only of the old mock) is replaced by M6, where B sees A's closing;
  - G5 drives one warm handler instance across two agencies;
  - 24/0.
- `040ac5a9`, not done: the straddling week, reopen inside the run, and O7 multi-rate.

**4. rt_ app-boundary — RESOLVED as intended.** rt_routes and rt_stops are visible to every app by design
(`visibleToAllApps` in routes.js, cody b27).
- The all-pairs arm now skips the registry's own `CROSS_APP_NAMES`.
- A new arm pins that set to exactly those two names, owned by `routes`.
- 14/0.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| D-SD | stonedesk.html:27173 `value=""'` → `value="'` | fourth | one-character fix + an arm on renderVendor |
| T1 | Tier A on `6a3755cac` + `29739fe14` | cc | review per the obligation's points (a)–(c) |
| T2 | Tier A on `76193dc91` (b51 MAR gate) | cc | unchanged |
| S1 | sd-data.js 4946 / 20236: the soft-delete check is skipped on an unreadable read, and the comment says that is DELIBERATE | Michael | decide: refuse (fail closed) or keep (availability) |
| S2 | not-Tier-A OPEN 3000 / 3983; dnt-bi.js:450 token cap; audit-checkpoint.js:339 verify "ok" on a non-array; ~18 `*-auth` bootstrap checks | hank (next dispatch) / cc for audit-checkpoint | same Array-first guard |
| S3 | a static detector for the row-or-null shape | cc (tools/) | write the check; the sweep classification is in this handoff |
| G2 | overlay all-filtered message (stonedesk.html) | hank, after fourth releases stonedesk | count stored vs shown, say "stored but not a showable format" |
| G3 | b48 straddling week / in-run reopen / O7 multi-rate | hank | add engine arms |
| L1 | leg_settings merge on the deployed API | — | no LEG audit licence exists; LEG-PINNACLE is demo-facing, so this stays unverified live |

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
