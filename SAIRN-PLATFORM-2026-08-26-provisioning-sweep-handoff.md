# SAIRN-PLATFORM — Handoff, 2026-08-26 (unprovisioned-migration sweep)

Written at a natural stopping point: all eleven gaps the sweep opened are
closed and live-verified. Claims below are independently verified against the
real repo and the real deployed site, not assumed from memory — same standard
as prior sessions in this series. Session ran in the **Cody** clone.

## 1. Verified current state

- `origin/main` HEAD: **`bb32a59c518aadb9a90ff5bc70c639be03257b7f`** — via
  `git rev-parse origin/main`, after a rebase pull. Local HEAD equals it.
- Branch: `main`, the repo default. Other sessions pushed to it throughout;
  this handoff's SHA will already be stale by the time you read it. Re-derive.
- All five of this session's commits confirmed present on `origin/main` via
  `git merge-base --is-ancestor` — not inferred from `git push` exiting 0.
- **224** distinct tables declared across `sql/*.sql` (comments stripped,
  multi-line DDL handled, two transient sweep baselines excluded). **186**
  `RESOURCE_NAMES` in `api/_resources/index.js`. **238** live `public` base
  tables per Michael's `information_schema` run.
- **Zero unprovisioned migrations remain.** Eleven were found; all eleven are
  now live and, except where noted below, exercised end to end.

## 2. Commits this session, in order

| SHA | Summary |
|---|---|
| `9ca7bc4` | `fix:` SAIRNcash waitlist upsert needed UPDATE it was never granted; two disclosure gaps |
| `aa45fc4` | `docs:` reconcile 224 vs 186 independently; three live tables declared nowhere |
| `5b8f4b0` | `seed:` disposable SAIRNcode admin, so the delete path can be verified at all |
| `b0044bd` | `seed:` SAIRNsenior demo license — the last thing blocking the app entirely |
| `392ac37` | `verify:` SAIRNsenior end-to-end, 30/30 against production + scoped cleanup |

## 3. What was CORRECTED, not just added

Five corrections. Three are to this session's own claims.

**3.1 — I reported four probe emails in `sairncash_waitlist`. There were two.**
Four addresses were POSTed, but the first two hit the very 502 being diagnosed
and never reached the table; a refused insert leaves nothing behind. Corrected
in `sql/sairncode_verify_admin_seed.sql`'s cleanup block, with a `select`
written before the `delete` so the count is checked rather than trusted.

**3.2 — I claimed `hank-admin` / `hank-coder` existed on `SC-PINNACLE-2026`.
They never did.** I cited `SAIRN-ACTIVE-WORK-cc.md:52` as evidence. Re-reading
it, that line is a **plan** — *"starting a fresh full audit pass… and real
click-through with hank-admin/hank-coder"* — written before the work, not a
record of accounts created. The real accounts were `owner` and
`zz-lifecycle-admin`. I repeated the claim twice as established and
recommended resetting a PIN on an account that does not exist. **General
lesson, and the reason this is in section 3 rather than a footnote:
`SAIRN-ACTIVE-WORK-*.md` mixes intentions and results as sibling bullets with
no marker distinguishing them.** The tell is tense and a commit SHA — real
results name a pushed commit and say "verified"; plans say "starting", "will",
"ahead of". Treat a line from those files as a lead, never as evidence.

**3.3 — I verified the waitlist cleanup by POSTing to it, creating fresh
debris minutes after confirming the table was clean.** One row,
`postcleanup-check@sairn-verify.test`. Flagged rather than left silent; see
open items.

**3.4 — The Fourth session's `231` declared-table count was wrong, and so was
the first version of mine.** A naive `grep 'create table'` counts matches
inside comments and invents phantom tables named `alone`, `anywhere`, `for`,
`if` and `to` out of prose in file headers. Comment-stripped with a
quote-aware pass gives 226; minus two transient sweep baselines, **224**. Both
sessions hit this independently. Reconciled in `aa45fc4`.

**3.5 — `docs/SAIRN-OPEN-WORK-INDEX.md` row 42 (`dnt_referrals`) was closed by
the Fourth session with better evidence than mine, and I dropped my edit.** I
had written a closure based on the read path only; theirs verified all four
legs. Rather than merge or clobber, `git checkout --` on the file and take
theirs. Worth recording because the reflex in a rebase conflict is to keep
your own version.

## 4. Open items, prioritized

**4.1 — SAIRNroofing and SAIRNlaw's deadline engine need an IP screen. IN
PROGRESS, and the premise needs correcting first.** The request that opened
this item described both as "never had one." **That is not true of
SAIRNroofing** — `docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md`
carries a full "Patent position" section (`:43`), a trademark finding
(`:100`, recorded as *inconclusive, not cleared*), and a summary at
`:319-320`. Dated 2026-08-24. What genuinely has no screen is **the Phases 1-5
work built after that spec**, and SAIRNlaw's `resolve_periods` /
`terminal_day_rule` and anything added since the citator's original screen.
Scope the screen to the delta, not to the app. **Nothing about a public-web
prior-art search is a clearance** — the roofing spec already says an attorney
is required before launch, and that standing caveat is not weakened by any
screen a session runs.

**4.2 — One stray row.** `delete from public.sairncash_waitlist where email =
'postcleanup-check@sairn-verify.test';` Inert data on a pre-launch table.

**4.3 — `SEN-PINNACLE-2026` has no employee credentials, deliberately.** All
three verification accounts were deleted, which re-arms `action:bootstrap`
(`api/sen-auth.js:182` refuses only when a row already exists). The first real
user creates their own owner. **This is inferred, not tested** — calling
`bootstrap` to prove it would consume the re-arm by creating the account it is
being held open for. The `401` on the deleted owner proves no rows exist,
which is the condition the guard reads.

**4.4 — 41 declared tables remain unreachable by any API probe**, and three
live tables are declared nowhere in `sql/`. See `docs/SAIRN-OPEN-WORK-INDEX.md`
rows 44-45. The three are `business_profiles`, `ai_memories` and `employees`,
reached via resources `profile` / `memory` / `employees`; `grep -rl "create
table.*<name>" sql/` returns nothing for any of them, so a rebuild from `sql/`
alone would silently omit them. Another session has since landed
`1fc72de feat(sql): read-only introspection for the three live-but-undeclared
tables` — check that before re-deriving.

**4.5 — Two behaviours worth not rediscovering.**
- **`ON CONFLICT DO UPDATE` requires UPDATE privilege at PLAN time**, whether
  or not a conflict occurs. `sairncash_waitlist` was granted `select, insert`
  only, so every public signup 502'd from the day the table was provisioned.
  A grant check that asks only "is INSERT present?" comes back clean. Fixed by
  switching to `resolution=ignore-duplicates` (`ON CONFLICT DO NOTHING`, needs
  INSERT alone) rather than widening the grant — a waitlist row has nothing to
  update, and the 2026-08-24/25 sweep had just narrowed these grants
  deliberately. **Do not "fix" a future failure there by granting UPDATE.**
- **A `NOT_PROVISIONED` message that names the wrong migration file is worse
  than a vague one.** `api/sd-data.js`'s SC branch hardcoded
  `sql/sairncode_data_schema.sql` for ~29 resources spread across a dozen
  files. Following it re-runs an applied migration whose `create table if not
  exists` is a silent no-op, so the operator concludes the table is fine. That
  is precisely why `sc_specialty_checks`, `sc_anesthesia_base_units` and
  `sc_pctc` sat unprovisioned from 2026-08-20 to 2026-08-25.

## 5. Method, so the sweep is repeatable

The left side is code-side and needs no credentials: extract every
`create table` target from `sql/*.sql` **with comments stripped** (see 3.4).
The right side needs one `information_schema` query from Michael — no session
in this project can read the service-role key, because `vercel env pull`
writes `[SENSITIVE]` for all 42 secrets on disk, there is no `DATABASE_URL`,
and no anon key is embedded in any client (everything routes through the API
proxy). A `left join … where is null` against a generated `VALUES` list
returns only the misses, plus a live-count guard so a truncated paste is
detectable rather than silently wrong.

Cheaper follow-up that needs no DB access at all: `api/sd-data.js` maps a
PostgREST 404/400 to `{"ok":true,"data":[],"provisioned":false}`, so a **read**
is a live table-existence check that writes nothing. That covers the 186
registered resources but is structurally blind to the other 41 tables.

## 6. Standard verification reminder for whoever reads this next

Verify `origin/main` HEAD, verify the branch, and re-run the relevant checks
before trusting any claim in this document — **including this one, and
including section 3**. Three of this session's five corrections were to its
own earlier statements, made confidently at the time.
