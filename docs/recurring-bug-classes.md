# Recurring bug classes — a 3-level cause tag per confirmed defect

**Started 2026-10-06 (fourth).** Every confirmed defect gets one row:

    PHASE  ->  SUB-PHASE  ->  CAUSE ("due to X")

`unknown` is allowed at any level and is better than a plausible guess — a
cause column full of confident wrong answers is worse than one that admits
what nobody established. A row whose cause is `unknown` says so *and* says
what was tried.

**Why three levels and not a free-text note.** A note is searchable by whoever
remembers the words in it. A tag is countable: when the same SUB-PHASE appears
four times in a month, that is the finding, and no amount of good prose adds
up to it on its own.

**PHASES:** `requirement`, `design`, `coding`, `config`, `unknown` — the same
five `tools/defect_register.py` uses, so a row here and a register record
cannot drift into different vocabularies.

---

## 2026-10-06 — batch 10 (fourth)

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | `tests/seam_check/run_delegation_probe.py` left `api/sd-data.js` and `api/_lib/subcontractor-compliance.js` carrying planted sabotage, one of which does not parse | coding | error handling | **due to** a destructive mutation written as a straight line — `write()`, then work, then `git checkout --` — with no `finally`, so every exception, assertion and kill between the two kept the plant | this batch |
| 2 | The same probe's baseline read the LAST LINE of `tools/sairn_seam_check.py`'s output | coding | anchor selection | **due to** a positional anchor (`splitlines()[-1]`) on another tool's output, which moved the day that tool gained a three-line closing explanation | this batch |
| 3 | The same probe's baseline required `0 could-not-tell` — a PLATFORM total — while printing "canAssign resolves at baseline" | requirement | criterion definition | **due to** a proxy standing in for the property actually named: the platform figure is 19 today, every one a different seam, and none of them canAssign | this batch |
| 4 | `tests/push_gate/check8_probe.py` leaves `.git/config` with `core.bare = true` and a fixture identity, after which every git command in the clone fails | design | sandbox isolation | **due to** the fixture being a LINKED WORKTREE, which shares `.git/config` with the clone that owns it — so any `git config` write made with cwd inside it lands in the real clone. cody's class name: `SHARED_CONFIG_WRITE_FROM_WORKTREE`. **The writer is still unidentified and is cc's**; this row is about why the write REACHED this clone, which is a separate and fixable thing | **FIXED 2026-10-06** (batch 11): the fixture is a throwaway `git clone --local` with its own config. 9 driven runs, config byte-identical on 9 of 9 |
| 5 | My own first version of the fix for #1: `--check-residue` DELETED the sentinel it had just reported | design | lifecycle | **due to** a cleanup handler registered at module import, so a read-only invocation ran it — a detector erasing its own evidence. Caught by the control on its first run, not by reading | this batch |

### What the five say together

**Three of the five (1, 2, 5) are the same shape one level apart: something
that was supposed to happen at the END did not happen on a path nobody
pictured.** A restore after an exception, an anchor after the output grew, a
cleanup on a read-only call. None is a logic error inside the thing being
tested; all three are about what happens on the way out.

**Two of the five are mine, from this batch, and #5 is mine from the fix for
#1.** That is the expected rate rather than an embarrassment: a fix written
and then controlled catches its own defect in the same hour. The rate worth
watching is fixes that ship WITHOUT a control, and that number is zero here.

## 2026-10-06 — batch 11 (fourth)

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 6 | My own clone cleanup leaked a 68 MiB hardlinked directory per run, silently | coding | error handling | **due to** `shutil.rmtree(..., ignore_errors=True)` over a cloned object store whose pack files are READ-ONLY on Windows — the removal failed and the flag swallowed it. Measured: three directories left in `%TEMP%` across the first three runs while the probe reported `ok` | this batch |
| 7 | The config snapshot resolved `MAIN/.git/config`, which does not exist in a linked worktree | coding | path resolution | **due to** assuming `.git` is a directory. It is a FILE in a worktree, so the first run from a dev worktree SKIPPED with "config could not be read". Fixed with `git rev-parse --git-common-dir`, which also returns the SHARED dir — the one a worktree write would reach | this batch |
| 8 | The dry-push retry fetched `MAIN` after the fixture became a clone | coding | state ownership | **due to** a line that was correct while the fixture shared MAIN's object store and became a no-op when it stopped. Measured: three consecutive runs SKIPPED on "could not read the outgoing range" | this batch |
| 9 | Convention 11's heading in `docs/2026-09-13-cross-domain-disciplines.md` had NO BODY | process | document structure | **due to** its body sitting forty lines lower under a heading left over from when the file had eight items. Found and routed by cc, not by me, while working on an unrelated file | this batch |

**All four are mine and three of the four were caught by RUNNING the thing, not
by reading it** — which is the same ratio batch 10 recorded. Number 9 is the
exception and it was caught by somebody else reading my file.

## 2026-10-29 — batch 65 (cody)

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | `tests/sd_data_mech_write_unconfirmed.js` never looked at the request's `Prefer` header, so a mech upsert switched to ignore-duplicates would have made every RE-save a false 502 with no arm red; and its ablation copy `api/.sd-data-ablate-*.js` was not gitignored | coding | test coverage | **due to** arms written against the RESPONSE only, with a mock that echoed whatever was sent, so the request shape was never a variable; the ablation file was cleaned up in `finally`, and nobody pictured the killed run (cc b70) | `e0e732364` |
| 2 | `sairnfreedom.html` `sfLicenceGuard` adopted any new key on a device with no fingerprint, so licence B opened licence A's local records and A's server-confirmed set | design | first-run state | **due to** a premise stated in the design comment ("no way to know which licence its data belongs to") that was false: the app stores the key itself under `sf_license_key`, beside the data (cc b70) | `f4d8c29fa` |
| 3 | `sairndental.html` `addCredential` leaked `dntCredWriting` when `rCredentials(null)` threw, and the b64 one-at-a-time guard then refused every later add until a reload | coding | error handling | **due to** a hold acquired OUTSIDE the try/finally that releases it, with a call between the two; b64's throw arm threw from inside the `try` and so could not reach the gap (cc b73) | `f4d8c29fa` |
| 4 | `sairngrounds.html` `gcdPlaceOrder` / `gcdMarkShotEnd`: a second press during the GPS fix sent a second (empty, $0) Pro Shop order, or threw on the cleared shot start | coding | concurrency | **due to** a live trigger over an await on a DEVICE API; the b64 sweep's shape was "awaits a server write", so a device wait was outside the net that found the other 47 | `f6a127280` |
| 5 | `stonedesk.html` `posCompleteSale` without a slab: a second press inside the 2.5 s before the form reset recorded the same sale again | coding | concurrency | **due to** a completion that cleared its inputs on a TIMER rather than at once, with the hold scoped to the awaited reservation only; and the suite's CONTROL arm asserted "one invoice per press", so the duplicate was pinned as correct | `03ad3006b` |

**Rows 1-3 were found by somebody else's review, not by me.** Two of those three (1, 3) are the same shape that batch 10 named: something meant to happen on the way OUT — a cleanup, a release — skipped on a path the author's own arm did not drive. Row 2 is a different shape: a design comment's premise taken as fact and never re-checked against what the file itself stores.
Rows 4 and 5 are b64's own leftovers, and both sit just outside the shape the b64 sweep searched for -- the sweep's predicate, not the handlers, decided what was found.

**All three were found by somebody else's review, not by me.** Two of the three (1, 3) are the same shape that batch 10 named: something meant to happen on the way OUT — a cleanup, a release — skipped on a path the author's own arm did not drive. Row 2 is a different shape: a design comment's premise taken as fact and never re-checked against what the file itself stores.

## 2026-10-29 — batch 68 (hank), the four H1 findings routed to hank

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | `sairnlegacy.html` keepsake order table wrote `o.quantity` into `innerHTML` unescaped, while the cells beside it used `H()` (H1 #1734) | coding | output encoding | **due to** a value assumed numeric because the CLIENT coerces it (`Number(..)||1`), while the server write branch accepts any type, so a direct API write stores markup | this batch |
| 2 | `docs/CRITICALITY-TIERS.md` cells for `leg_memorials` and `leg_liveryvendors` said "no PII" (H1 #1740) | requirement | register classification | **due to** a row classified by the stated B rule without reading its write site; same shape as the `leg_guestbook` cell corrected 2026-09-30 | this batch |
| 3 | `sairnvet.html` `saveWildlifeEdit()` accepted a closing status with a blank outcome date, so the case left Active Cases and never reached Released YTD / Release Rate (H1 #1744) | coding | input validation | **due to** a required pairing (closing status ⇒ date) stated only in help text under the form, not enforced on save | this batch |
| 4 | `tools/sql_placeholder_check.py` lexer: E-string backslash escape ignored (false negative), apostrophe in a quoted identifier opened a string (false COULD NOT RUN), declaration matched by substring and on raw lines (H1 #1747) | design | hand-written lexer | **due to** a lexer modelling fewer quoting forms than the grammar has, and an exemption matched more loosely than the sentence granting it; the fixtures did not reach these shapes | this batch |
| 5 | `api/agent/poll.js` PATCHed a command `delivered` by id alone, so two concurrent polls of one agent could both deliver it (b67 S3 candidate, S4) | design | concurrency | **due to** a read-then-write with no compare-and-set: the read filtered `status=eq.pending`, the write did not, and the PATCH's failure was ignored | this batch |
| 6 | `tools/push_retry.py` `_regenerate_and_fold()` logged "derived-docs commit failed:" with an empty error when only untracked files were present (b67 S6) | coding | error handling | **due to** "the tree is dirty" (porcelain non-empty, which counts untracked files) standing in for "something is staged", and `git commit`'s refusal going to stdout while only stderr was reported | this batch |

## 2026-10-29 — batch 66 (cody)

Every routed finding below names its source inline: session, commit and, for an auditor finding, the seq.

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | `tools/sairn_done_line.py` Stop hook (cc b66, `a367bd0c2`) let a hand-typed `done b<n> <id>` end the session when it had recorded nothing this turn | design | state coupling | **due to** the check being keyed on the tool's OWN state file, so "the tool never ran" read as "not a final step" instead of "an unverified claim" | `23421fd51` |
| 2 | Twelve more licence guards adopted a different licence on a legacy device (b65 found it in sairnfreedom, `f4d8c29fa`) | design | first-run state | **due to** one false premise, "nothing says whose data this is", copied into thirteen guards from `343c5a327`; and `licence_rekey_isolation` pinned the flaw as its requirement | `862ed3591` |
| 3 | `sf_server_confirmed` entries never expired (cc b70 gap (a), on cody b61 `7ae231b47`) | design | data lifecycle | **due to** a record of THAT the server answered, with no WHEN, so nothing could age it | `0f8c36e10` |
| 4 | sairnmechanical `mechCredAdd` / `mechAssetAdd` swallowed a rejected write (cc b73 R-12, `69c36d5ff`) | coding | error handling | **due to** a `.then().finally()` chain with no rejection handler; the `finally` made the hold correct, which hid that the failure was silent | `824bab9dd` |

**Rows 2 and 4 are the same shape at two scales:** a check that held for the case its author drove (one app; a hold released) and said nothing about the case next to it (twelve apps; the user told). Row 2's arm pinned the wrong answer as the right one, which is the second time this batch pair has found that (b65 row 5, stonedesk S4).
