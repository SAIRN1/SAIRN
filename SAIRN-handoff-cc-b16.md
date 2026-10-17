# SAIRN handoff — cc batch b16 — 2026-10-17

**b16's code all landed on 2026-10-16 and 2026-10-17 and was pushed. Its
artefacts — this file, the report, the digest, the manifest close, the
active-work entry — did not, because the working session ended after the last
code push and before the wrap.** They were written in a separate fresh session
on 2026-10-17 from the landed commits, the routing document, and re-runs of
every selftest cited below. **Nothing here is reconstructed from memory of the
earlier session**: where a figure could only have come from that session's own
transcript it is named as unrecoverable rather than quoted.

Measured: the b16 working session's last usage record is **692,299 tokens
(69.2% of the 1M window)**, transcript `67ca63b0…jsonl`, 4,701,177 bytes, last
written 2026-10-17 10:13. The wrap session that produced these files is a
different transcript at 145,338 tokens. **Two sessions, one batch**, which is
why the push-attempt count below is given as what the gate recorded rather than
as a tally.

---

## Committed / pushed state

b16's commits, oldest first, all on `main` and all on `origin/main`:

| sha | what |
|---|---|
| `9edf2ae9` | install(branch census) — fourth b26's census becomes `tools/branch_census.py` |
| `5522cfc8` | fix(claims) — `list --all` was 501,182 bytes and nobody had measured it |
| `e05802cf` | fix(scope gate) — a rebase replay skips commit-time enforcement; the push gate DOES refuse it |
| `64ba232d` | fix(inventory) — `hooked()` returned `{}` for four different conditions |
| `75f10079` | record(defects) — three b16 fixes, two summaries damaged by backticks in a CLI body |
| `7290e9cc` | reseat(register) — the rebase rewrote five commits and two citations followed |
| `76a78236` | reseat(register) — an `--amend` preceding the rebase is not in the rewrite map |
| `830f3cd1` | chore(owner) — `branch_census.py` declares its owner |
| `6b6360cd` | fix(owner) — the OWNER line was outside the 40-line window the gate reads |
| `d19498ba` | record(bypass+owner+ledger) — the SCOPED tier-a skip and this push's rows |
| `3fc1b8ae` | reseat(register)+record — three citations follow the shas that actually landed |
| `aea2d0db` | fix(blob coverage) — the scope window was a seven-line count |
| `331cebe3` | fix(claims) — `self_hits` WAS wired to a refusal, to a different input |
| `94ec1209` | fix(matcher) — the exemption is derived from the live corpus |
| `b7d44ef0` | fix(sweep) — the log was ZERO BYTES whenever the run was killed |
| `6921b68c` | record(defects) — four more b16 fixes, every body through `--<flag>-file` |
| `1b53ad4f` | reseat(register) — the rebase rewrote four b16 commits |
| `a60aa1e1` | record(scrutiny) — the ledger rows for the four b16 fixes |
| `b6a2d572` | fmea(drafts) — seven files drafted, and `--save` could overwrite a prediction |
| `afd17c86` | gate(guard tests) — eighteen of hank's b14-b17 api suites wired |
| `f17973ab` | gate(tier a) — `--amend`, because a recorded file set can be wrong |
| `65d4d5d8` | record(defects)+route(b16) — the fmea_draft overwrite and the routing list |
| `eab1cc67` | reseat(register) — the rebase rewrote this batch's commits |
| `b6d20411` | regen(derived) — matrix and master plan follow the eighteen wired guard tests |

**30 distinct files**, of which 10 are `tools/`, 1 is `.githooks/post-rewrite`
and the rest are `docs/` records and generated documents. **No `api/`, no
`sql/`, no app HTML, no `tests/` file was written** — tests/ is cody's and
api/ is hank's, and the eighteen api suites were *registered*, not edited.

**Overrides, audited rather than asserted.** `docs/BYPASS-LOG.jsonl` holds 100
rows. Exactly **three** fall inside b16's window, all `cc`, all
`blanket: false`, all the same **SCOPED tier-a** exemption at
2026-10-16T13:04:58Z / 13:06:03Z / 13:07:32Z — one grant honoured across three
push attempts, with the reason naming the two prose matches (`alf_op_audits` in
a fixture string, `rf_jobs` in a module docstring) inside
`tools/branch_census.py`. **No blanket form in any spelling, and no row at all
dated 2026-10-17** — and because the gate records an override *attempt* before
deciding whether to honour it, an absent row is an unused override rather than
a silence. No `--force` in any spelling. No hook added or restored;
`settings.json` never committed.

---

## What b16 PROVED

- **The scope gate's enforcement moves to push-time for the rebase-replay
  shape, and that is now measured in both directions.** Eight arms in a
  scratchpad sandbox, bare repo plus work clone, script committed as
  `docs/2026-10-16-cc-b16-scope-gate-rebase-replay-sandbox.sh`: a plain
  out-of-scope commit REFUSED; `git rebase` onto a divergent branch SUCCEEDS
  with no refusal (H1's finding, reconfirmed); the replayed commit REFUSED both
  as a new branch and on the `rsha..lsha` path a real `git push origin main`
  takes, which is different code; two CONTROL arms landed clean. **The residual
  gap is TIME, not coverage.** The new `--post-rewrite` notice names the paths
  at the rewrite and **cannot refuse and does not pretend to** — git ignores a
  post-rewrite hook's exit status.
- **`sairn_claim.py`'s two "same" sets were each blind to exactly what the
  other could see.** `cmd_check` built `self_hits` from `origin/main` only;
  `cmd_claim` refused from the local file only — with a comment asserting they
  were the same set. One function over the union of all three sources now,
  every row tagged with where it was seen.
- **The claim matcher gets weaker as the corpus grows, and that was retiring
  live incidents silently.** `common_phrases()` exempts any bigram used by
  three or more distinct sessions; `rebase resolve` reached exactly three
  because everyone names `tools/sairn_rebase_resolve.py`, and the only overlap
  between one live incident's two task strings was that bigram. Pinned from
  `docs/claim-matcher-pinned-phrases.json`; 23 of 23 historical same-work pairs
  still refuse, so nothing was re-opened.
- **Two of cody's probes were right and the tool was wrong, in both cases** —
  including `hoarders` computed with `is_active()`, which expires a row at four
  hours and therefore dropped the *worst* cases of the open-row shape the
  question was about.
- **A line count cannot see a write body.** `blob_conversion_coverage.py`
  decided licence-scoped-write by a seven-line proximity count; the real
  window is 266 sites against the 593 the count gave.
- **Re-drafting an FMEA prediction launders a MISSED verdict.** Measured:
  superseding `sairnsenior.html`'s 2026-09-14 draft while KEEPING the old file
  leaves `missed` at 144; removing the kept copy drops it to 139 and raises
  DRAFT NEWER from 221 to 228. Five real misses on one rename. `--save` now
  refuses the overwrite.
- **Eighteen of hank's api suites cost 4.83s on every code push.** `GUARD_TESTS`
  17 → 35 (31 `api/`, 4 `tests/`), every one run to a known exit code first,
  slowest `b17-trust-lock-hard.test.js` at 1.63s.

## What b16 left UNPROVEN

- **The hover/hover2 claim-name collision DOES NOT REPRODUCE** from any build
  agent's tooling, and that is a negative result rather than a fix:
  `tokens('hover')` is `['hover']`, zero prefix or suffix matching on a session
  name anywhere in the three tools, both claim files exist separately. If it
  exists it is inside the auditor's own tooling, a clone a build agent must not
  enter. **It needs a command and an output from H2, not another cc read.**
- **Whether widening a Tier A file set is CORRECT is not covered** by
  `tier_a_review_gate.py --amend`'s ten arms. The tool refuses to amend a
  REVIEWED record; the judgement lives in `--why`.
- **856 claim phrases sit exactly at the exemption threshold and 2,931 are one
  session away.** Nobody has swept the other historical incidents to find which
  of their blocking phrases are already exempt. Each is a block that has retired
  with no signal.
- **The branch census's criteria version is deliberately NOT bumped**, and the
  inter-procedural walk fourth's b27 claim names is **not** done here.
- **No live deployed-URL check**: this batch changed no `api/`, `sql/` or app
  file, so there is nothing deployed to verify. That is a structural answer,
  not a skipped step.

---

## Claims held

At the time of writing: **one**, `cc` — the wrap claim, declaring only this
file, the report, the digest, `SAIRN-ACTIVE-WORK-cc.md` and
`docs/batch-manifest-cc-b16.json`. Released at the end of the wrap.

The b16 working claim (2026-10-16T11:34:50Z) **expired rather than being
released**, because the session ended before the wrap. Said out loud because an
expired claim is indistinguishable from a dead session and the next reader
should not have to guess which it was.

**A conflict was declared and NOT overridden:** hank b17 held
`docs/tier-a-reviews.json`, so that file was dropped from b16's FILES and no
record was opened or edited in it. `tier_a_review_gate.py --amend` is the
**tool**, which is cc's; the ledger is hank's.

**cody appended one record to `docs/defect-density-register.json` while cc
held it, deliberately, and said so** (`af7309ba`). Union-by-identity is that
file's declared merge policy and a concurrent append is the operation it is
built for. cc agrees and is not reverting it.

---

## Open items — each with why it is open and the exact next step

1. **Michael, one decision — `SAIRN_SKIP=<gate> SAIRN_SKIP_WHY="…" git push`
   grants nothing.** Nothing in the push path calls `gate_skip.grant()`;
   `_scoped_skip()` only honours a record file that already exists; the only
   thing that writes one is running `tools/gate_skip.py` itself with those
   variables set. So the form the gate's own refusal recommends is read by
   nobody, and it cost four pushes to find out. The working sequence is
   `SAIRN_SKIP=tier-a SAIRN_SKIP_WHY="<reason>" python tools/gate_skip.py`
   then `git push`. **The decision is which one to keep** — the gate grants
   from the environment on the spot, or the hint stops recommending a form
   that does nothing. cc changed neither, because those are opposite answers
   to the same question.
2. **cody's SAIRNscape finding is the priority and it is on a file cc holds.**
   `customers` carries name, phone, email and street address and is reachable
   on the licence key alone for read and write, proven live with a control.
   **The root cause is the register, not the gate**: `customers` is carried B/B
   while its confidentiality cell already says the row holds PII, and the
   gating sweep reads the letter. Fix is two lines in `SD_SESSION_GATED` and
   `SD_GATE_APP` in **one** edit, plus the B→A retier. Full account with the
   resource-vs-table name trap in
   `docs/2026-10-05-sairnscape-customers-licence-key-alone.md`. **The assertion
   that matters after: the WRITE path must go 400 → 403, not just the read.**
3. **Both malformed open-work index rows are hank's and both must be fixed in
   one pass.** Rows 355 and 356 each carry 10 pipes where the 7-column table
   needs 8; the cause in both is an inline code span containing literal pipes.
   Fixing 355 alone publishes a half repair. Spell the operator out rather than
   escape it, and rebuild each row WHOLE per PR §2.1.
4. **Three b12 test-file-floor layers are still unarmed** — carried from b14
   and b15 unchanged. `tracked-intersection` is the urgent one.
   `docs/ABLATION-RECORDS.md` Finding 2 names the fixture each needs. `tests/`
   is cody's.
5. **The claim-phrase threshold sweep** (856 at-threshold, 2,931 one away) —
   the pin file is where the answer goes.

---

## Three things that will cost the next session time if nobody says them

1. **A backtick in a CLI body is executed, and it happened THREE times in one
   batch** — two defect-register summaries landed damaged. `--<flag>-file` is
   supported by `tools/defect_register.py` and the fix is the flag, not care.
2. **A count written in prose beside the thing it counts goes stale.** Four
   instances in b16, all cc's own, all caught by re-reading rather than by a
   check: `.githooks/post-rewrite` said "THE MAP IS READ TWICE, BY TWO
   PROGRAMS" while three read it; a selftest header said "five arms require IN"
   where four did. Harmless alone; the shape is not. **There is no detector.**
3. **A blocked push is not a no-op** (cody's, and it is general): a push
   blocked by the generated-document gate leaves an interactive rebase in
   progress, after which `--amend` rewrites the commit being replayed onto
   rather than yours. Read `git status` first, not last.
