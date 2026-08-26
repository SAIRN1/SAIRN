# SAIRN-PLATFORM — Closing Handoff, 2026-08-26 (anon/authenticated grant hardening + provisioning)

Written as a **closing** handoff — this session is being wound down after it, so
it is written to be complete rather than to be resumed by the same context.
Claims below are verified against the real repo and the live platform, not
carried from memory. **Section 3 (corrections) is the most important section
here** — this session corrected its own claims five separate times, and each
correction is load-bearing for whoever picks this up.

Session: **Fourth** (`C:\Users\marsh\Documents\SAIRN-fourth`).
Active-work log: `SAIRN-ACTIVE-WORK-fourth.md` (append there, not to the shared file).

---

## 1. Verified current state

- `origin/main` HEAD: **`46a9a9a8f11d58434242de477d9620f564763a73`** — via
  `git rev-parse origin/main` after a real `git fetch`. Branch `main`.
  Other sessions were pushing throughout; re-derive this before trusting it.
- Live site serving: `sairn.vercel.app/stonedesk` HTTP 200 (~2.23 MB),
  `sairn.vercel.app/sairnroofing` HTTP 200 — real `curl`, not assumed.
- **Pre-Stage-B proxy baseline, captured deliberately so the post-run check
  compares against a real reading rather than an assumption:**
  `POST /api/sd-data {"resource":"dnt_patients","action":"read"}` with
  `DNT-PINNACLE-2026` → **HTTP 200, `ok:true`, `provisioned:true`, 8 rows.**
  That is the exact expected result of Stage B verification step 2.
- Declared tables in `sql/`: **227** (comment-stripped, minus two transient
  sweep baselines). Live tables in `public`: **251** as of the ownership check.
- Platform grant state: **zero `grant … delete` outside `sc_*`** in any form,
  literal or dynamic. `sc_*` intact at 29 lines / 15 files.

---

## 2. Commits this session, in order (oldest first)

Pulled from real `git log`, not paraphrased.

| SHA | Summary |
|---|---|
| `437cc09` | dnt_referrals verified live; probe-row pattern logged |
| `b0a58cc` | remove DELETE from the two dynamic grant loops the literal sweep missed |
| `cd48a59` | merge |
| `183cd21` | read-only provisioning-gap query; NOT RUN label drift is systemic |
| `407b673` | Guardian Check 23 wording corrected |
| `1fc72de` | read-only introspection for the three live-but-undeclared tables |
| `68f94f4` | declare business_profiles, ai_memories, employees from live structure |
| `bb32a59` | ACL check for the remaining live-but-undeclared tables |
| `df8e0c2` | anon/authenticated TRUNCATE/REFERENCES/TRIGGER sweep, built to scope |
| `d084cb0` | Section 0b failed its assertion — anon has no access at all |
| `7960647` | Stage A Section 2 — tables, sequences, routines, default privileges |
| `24c469d` | the Section 1 count drift is this file's own baseline tables |
| `2abe3e4` | supabase_admin has a SECOND default ACL granting anon full CRUD |
| `1ca18bd` | Stage B written; supabase_admin proven inert and accepted as monitored |

Plus merge commits. `9ddd45b` (Guardian: "done when queried back, not when run")
landed from another session in the same window and is not mine.

---

## 3. What was CORRECTED, not just added

**Five corrections, all of my own claims. Read these before trusting anything
else in this document.**

1. **`.claude/settings.json` was truncated, not merely malformed.** The working
   copy stopped mid-string at 2272 bytes, so the whole file failed to parse and
   **none of it was in effect** — not the hooks, not the permission lists, not
   `outputStyle: silent`, not the plugin. The `C:/SAIRN/tools/` repoint was
   therefore never live in this clone. Rebuilt from HEAD; 6 path rewrites plus
   the PreCompact payload. Another session had independently made the identical
   fix; compared semantically (not by eye) before resolving — byte counts
   differed, content did not.

2. **My declared-table count of 231 was wrong; Cody's 224 was right.** My grep
   counted `create table` occurrences *inside comments*, inventing five phantom
   tables named `alone`, `anywhere`, `for`, `if`, `to` out of prose in file
   headers. **If you regenerate that list, strip SQL comments with a real
   quote-aware state machine first.**

3. **"`anon` is NOT unused" was right about the code and wrong about the
   database.** The browsers do ship a publishable key and the code does call
   `sb.from('intake_submissions').select/update/delete`. Those calls **fail** —
   `42501 permission denied`, confirmed live with the real shipped key. I let
   "the code does X" imply "X works". It did not.

4. **The `NOT RUN` labels on cleanup files no longer describe the database.**
   Six of eight measurable probe rows are **gone**, each verified under the
   licence its own file names and each with a working control so an empty
   result could not be a bad hash. The *file* count is solid; the *row* claim
   is retired. Do not cite those as live debt without re-probing.

5. **My hypothesis about the anon baseline was wrong, and the control caught
   it.** I predicted it sat only on live-but-not-declared tables. Section 3 of
   the ACL check — written specifically so the prediction could be falsified —
   came back dirty on declared tables too. Real root cause: **every
   grant-hardening pass on this platform targeted `service_role` only.**

**Also corrected, smaller:** my own probe-cleanup count (14/10) went stale
within hours (now 15/11); a literal `|` inside backticks broke an index table
row twice (same bug I had fixed earlier that night — the column-count check
caught it both times, not my eyes); and my "13 across 9" app grouping was
reached sloppily and happened to land right.

---

## 4. Open items, prioritized

### 4.1 — Stage B, ready and NOT run ⚠️ **highest**
`sql/anon_authenticated_schema_usage_revoke_stage_b_2026-08-26.sql`.
Stage A ran and verified clean (3a empty, 3b six rows all LOST / zero GAINED,
3c `remaining_rows` 0, 3d `postgres` default ACL clean, 3e empty).

Run order, and **do not reorder it**:
1. Section 0 (before-state) and **Section 1 (Stage-A-still-clean)**. If Section 1
   returns anything, **stop** — the revoke would hide a real grant behind a
   schema-level block rather than removing it.
2. Rollback open in a separate tab first: `grant usage on schema public to anon, authenticated;`
3. `revoke usage on schema public from anon, authenticated;`
4. Verify: 3a (expect zero rows) → the proxy read (expect the **8-row / 200 /
   `provisioned:true`** baseline recorded in §1; any failure = roll back
   immediately) → the Supabase dashboard table view, which is the part no query
   can predict and the reason this statement does not share a run.

### 4.2 — Section 4 cleanup, held, and it settles an open prediction
Both baseline tables (`_anon_grant_baseline_2026_08_26`,
`_anon_nontable_baseline_2026_08_26`) are **still in `public`** and must stay
until Stage B verifies. Section 4 of the Stage B file drops them.

**Open, untested prediction:** the table count must fall by **exactly 2**, landing
on **249, not 248**. (248 measured 2026-08-25 + 2 baselines + `rf_settings`,
genuinely new from another session, = 251.) Anyone expecting 248 will read a
correct result as a discrepancy. **This has not been confirmed — do not write it
up as verified.**

### 4.3 — StoneDesk intake feature, dead at both ends ⚠️ **high, customer-facing**
Two symptoms, one gap, **one repair**:
- **① Ships customers a dead link.** `https://sairn.vercel.app/stonedesk-intake`
  returns **404**. `intakeBuildLink()` (`:31950`) writes it into a copyable
  field, `intakeCopyLink()` (`:31959`) copies it with an *"Intake link copied!"*
  toast. A user sends it to their customer; the customer gets a 404; the app
  reported success. **This one leaves the building.**
- **② Silent read fallback.** `:31984` reads through the anon key inside
  `try{}catch(e){}`, swallows the 42501, and renders `localStorage('sd_intake')`
  — while the line above it comments *"Supabase is the real source of truth
  here"*.

**Do NOT fix by granting `anon` SELECT** — the publishable key is public by
design; that makes the table world-readable. Route through `api/sd-data.js` like
every other table. Decide the write path first; it settles the read path.

### 4.4 — `supabase_admin` default ACL: accepted risk, MONITORED
Proven **inert** — `public` is 100% `postgres`-owned (251 tables, 4 sequences,
11 functions; zero `supabase_admin`-owned objects). Its default ACL grants
`anon`/`authenticated` `arwdDxtm` (full CRUD) but has never fired. Deliberately
not fixed: may need a Supabase support request.

⚠️ **Re-check trigger:** the moment anything creates an object in `public` other
than the SQL editor as `postgres` — an automated migration pipeline or CI
runner, a Supabase-managed feature, a dashboard/Table-Editor create, an
extension install or upgrade, or a restore. **The monitor is one `SELECT`**
(Section 1 of `sql/supabase_admin_default_acl_check_2026-08-26.sql`); a single
non-`postgres` row is the whole alarm.

### 4.5 — `ai_memories` has no unique constraint — product decision, owner Michael
Primary key on `id` and nothing else. The code does not appear to want one:
plain INSERT with no `on_conflict`, read of `order=created_at.desc&limit=10`,
index built for exactly that. Append-only is the behaviour; whether that is
*intended* is unanswered, since the name suggests a per-licence record. The
schema file deliberately adds no constraint and says why.

### 4.6 — Smaller, still open
- **`sairnscape_org_intel`** — the platform's one genuinely unprovisioned
  declared table. Known, inert.
- **22 live-but-not-declared tables** remain undeclared (25 minus the three
  written tonight). Not urgent; the sweep no longer depends on it.
- **`${CLAUDE_PROJECT_DIR}` hook paths** — deliberately deferred, full
  re-derived diff in the index row. Ready to apply cleanly.
- **`SAIRN_INTERNAL_KEY`** is provisioned in Vercel (~67d) and read by zero
  code. Guardian Check 23's retirement stands; the variable is dead config to
  retire deliberately.

### 4.7 — `sairn-contract-drafter` — ~~unlocated~~ **RESOLVED, not an open item**
**Closed 2026-08-26 before this session ended — corrected here so the next
reader does not chase a thread that is already finished.** When first named to
me I could find no trace of it anywhere in this clone (no
`~/.claude/skills/*contract*`, no `.claude/skills/*contract*`, no
case-insensitive hit in any `.md`/`.json`), and recorded it as unverified and
unlocated rather than inventing a status.

That was the right call on the evidence available **and the wrong conclusion
about where to look.** The real master documents were never in the repo at all
— they are in the user's `Downloads` folder, outside every clone, which is why
a repo-wide search returned nothing and would have returned nothing no matter
how thorough it was. Cody has extracted the skill from them; `sairn-contract-
drafter` now exists and is loadable, covering per-app service agreements built
from the four real master documents rather than invented.

**Kept rather than deleted, for the transferable lesson:** a clean search
proves the thing is not *where you searched* — never that it does not exist.
The search was exhaustive within the repo and the repo was the wrong universe.
Same shape as the `anon` correction in §3: right about the artefact examined,
wrong about the world it sat in.

---

## 5. Standard verification reminder

Re-verify `origin/main` HEAD and branch, re-run the relevant checks, and
re-derive every count before trusting any claim in this document — **including
this one**. Three separate counts moved *within hours* tonight (~158→159→160
tables, 224→227 declared, 14→15 cleanup files). Two of those movements were
correctly explained only after being questioned; one is still an untested
prediction (§4.2).

**One habit worth carrying forward, because it earned its place three times
tonight:** write the verification so it prints the *whole* picture rather than
asserting the one thing you changed. Guardian's Check 23 error, the
`anon`/`authenticated` gap across 159 tables, and `supabase_admin`'s second
default ACL were each found by a check that showed everything, and each would
have been missed by a check that only confirmed the intended change.
