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

## 2026-10-29 — batch 69 (hank)

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | `api/_lib/law-trust-reconcile.js` counted any uncleared deposit as "in transit" with no age limit, so a trust shortfall carried as a 91-day-old deposit balanced the bank leg and read Reconciled (cc b55 stress M5) | design | domain model | **due to** the outstanding-items model (2026-09-18) encoding the timing difference without the property that makes it a timing difference: that it resolves within days | this batch |
| 2 | `sairnlegacy.html` passed 33 stored record ids raw between `\'` quotes into inline handlers, and the employee-id argument as `&#39;+H(id)+&#39;`, so an id holding a quote closed the JS string (H1x, from H1 #1734) | coding | output encoding | **due to** escaping for the wrong layer: an inline handler is HTML-decoded and THEN parsed as JS, so neither a raw value nor H() alone is safe there; the server accepts any id format | this batch |

## 2026-10-30 — batch 70 (hank)

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | The b69 sairnlegacy inline-handler shape in four more owned apps: sairnvet 61 raw values plus an `&#39;+escHtml()+&#39;` builder, sairncode 32 raw, sairnbiz 5 HTML-only values plus 3 HTML-only builders, stonedesk 2 HTML-only (the rest of StoneDesk already used `escAttrJs`) | coding | output encoding | **due to** the same wrong-layer escape copied app to app; StoneDesk shows the right helper existed on the platform and did not propagate | this batch |
| 2 | My first H1y fix (a new global `JA()` in sairnbiz/stonedesk) broke 5 of their suites: they load app functions by hand-kept lists, pin `fn('ID')` markup, and one string scanner treats a quote inside a regex literal as a string | coding | test coupling | **due to** a helper added without reading how each app's suites load it; caught by running all 62 suites against a base worktree, before commit | this batch |

## 2026-10-30 — batch 68 (cody)

Sources cited by record and commit. These are cc b76's verdicts on cody b65's Tier A records, in `docs/tier-a-reviews.json`; no line number stands alone.

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | `sairngrounds.html` `gcdMarkShotEnd` measured a shot from a START pressed during its own pending GPS fix, then discarded that start (cc b76 F1, record 2026-10-29T19:34:54Z) | coding | concurrency | **due to** a module variable shared by two handlers, read AFTER an `await` by one and written by the other; b65's hold covered END against END only | `569ab9bc4` |
| 2 | All 13 licence guards compared keys case-sensitively; the server treats a case-only difference as the same licence (cc b76 F1, record 2026-10-29T19:12:48Z) | design | identity definition | **due to** the client's notion of "same licence" (exact string) never being checked against the server's (`api/_lib/license.js` upper-case retry); every b65/b66 fixture used one case | `aadab627c` |
| 3 | `stonedesk.html` POS hold release on a throwing reset was TRUE but UNGUARDED (cc b76 F2, record 2026-10-29T19:34:54Z) | coding | test coverage | **due to** a `finally` with no arm that throws through it; ablation left the suite green | `42b1050e1` (test only) |

**Two of the three were in my own b65/b66 work, and an independent reviewer found both.** Row 2 is the sharper lesson. The b66 fix copied one block into 13 files after checking only that each app has a single key writer that upper-cases, and sairnfreedom's does not.

## 2026-10-30 — batch 71 (hank)

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | `api/sd-sub-data.js` said the America/New_York day "can never call a still-valid document expired" in the fifty states; Eastern rolls over FIRST, so western shops see a document expire 1-6 hours early (H1 #1817) | design | stated invariant | **due to** reasoning about which zone is "easternmost" instead of which zone's date changes first; the claim went into the comment and the commit message unchecked by any test | this batch |
| 2 | stonedesk.html `sdDrawingsLoad` / `sdDrawingsDelete` passed `x.id` as `escHtml(String(x.id))` between quotes (the H1y shape, parked in b70 behind fourth's claim) | coding | output encoding | **due to** the same HTML-only escape in a JS context as b70 row 1; the rest of StoneDesk already used `escAttrJs` | this batch |

## 2026-10-30 — batch 72 (hank)

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | The SAIRNlegacy write branch in `api/sd-data.js` required only a non-empty `payload.id`, so a quote or markup could be stored as an id (H1 #1734, server half) | design | input validation | **due to** an identifier treated as opaque text at the boundary; the client escape (af2db16b3) protected one reader, the server protected none | this batch |

## 2026-10-30 — batch 70 (cody)

Sources: index row `B69-REENTRY-14-CODY-2026-10-30` (found by `tools/reentry_hold_check.py`, criteria `cody-b69.4`) and Michael's b70 items.

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | sairngrounds `sendDesignToQuote`, `grdUploadProgressPhoto` | coding | concurrency | **due to** a new record per press with the trigger live across the await (b64's shape) | `414794471` |
| 2 | sairnscape `scpSendDesignToQuote`, `scpSendIrrZoneToQuote`, `scpSendWfToQuote`, `scpUploadProgressPhoto` | coding | concurrency | **due to** the same shape; these are the scape twins of the grounds handlers b64 fixed, and b64's fix never propagated | `3a133ef2f` |
| 3 | sairnsenior `generateClaim` | coding | concurrency | **due to** no already-claimed refusal; the row's removal before the await was the only guard, and it fails when `st()` fails | `fb10f57f3` |
| 4 | stonedesk `intakeAccept`, `sdAIQGenerate` | coding | concurrency | **due to** the same shape | `bb2a99a20` |
| 5 | sairnvet and sairnmechanical had no licence re-key guard | process | sweep population | **due to** the 2026-09-03 sweep enumerating the apps that existed then; apps built later never joined its list | `3cbfa6d2d` |
| 6 | `tests/sd_data_write_attribution_three_apps.js` red on correct code | coding | test currency | **due to** arms pinned to the RETIRED blob form after `d7773533f` moved the stamp to columns; a source-string arm (D3) outlived the code it matched | `e514c26af` |

**5 of the 14 checker candidates were NOT re-entrant.** `addProcedureType`, `saveGfe`, `msbCheckout`, `generateAftercareSchedule` and `sdLocAdd` each empty their source, refuse an existing row, or prompt for input before the wait. **And the harness itself would have hidden that:** `H.drive` refills the form before every press, so it reports a duplicate a real double press cannot make. Every b70 fix was proven by a NO-REFILL double press, and scape and senior carry it as a permanent arm.
