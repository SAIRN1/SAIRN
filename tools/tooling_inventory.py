#!/usr/bin/env python
r"""tooling_inventory.py -- GENERATE docs/TOOLING-INVENTORY.md from the wiring.

    python tools/tooling_inventory.py            # write the document
    python tools/tooling_inventory.py --check    # is the document still true?

WHY THIS IS A GENERATOR AND NOT A DOCUMENT.

docs/2026-09-09-tooling-inventory.md was hand-derived, correct on the day, and
STALE WITHIN THREE DAYS. Its headline said 77 tools, 3 report-only and 28
unwired checkers. Measured 2026-09-12: 97 tools and 26 report-only. Nine
checkers were promoted and twelve more were built in between, and nothing about
the document knew. That is the same claim-in-two-places failure this repo keeps
recording -- applied to the inventory of the safety net, which is the one
document whose staleness is hardest to notice, because a tool that does not run
produces no output to contradict it.

So the only honest version is derived, and `--check` is what makes it stay true.
Same treatment as docs/traceability-matrix.md for the same reason.

WHAT IS DERIVED AND WHAT IS NOT.

Derived, every run, from the repo:
  * the tool list          -- `git ls-files tools/`
  * BLOCKING               -- PreToolUse hooks in .claude/settings.json, plus
                              every tools/<name> the push gate shells out to
                              (it is the thing that can call deny())
  * REPORT-ONLY            -- REGISTRY in tools/report_only_checks.py, plus
                              PostToolUse hooks
  * ADVISORY               -- SessionStart / UserPromptSubmit hooks
  * SUITE-ONLY             -- referenced by something under tests/, so it runs,
                              but only ever against fixtures
  * UNWIRED                -- referenced by none of the above
  * `catches`              -- for the 26 report-only tools it is read straight
                              out of REGISTRY, which already carries it

NOT derived, and it cannot be: what a tool catches, for everything that is not
in REGISTRY. That is judgement and lives in PURPOSES below. The generator
REFUSES to run if a tool has no entry, and refuses if PURPOSES names a tool
that no longer exists -- so the hand-written half cannot drift in either
direction without failing loudly.

LIMIT, stated rather than discovered: "BLOCKING" means the tool is reachable
from something that can refuse. It does not mean every one of its findings
blocks -- the push gate has report-only checks INSIDE it (5 and 7 were promoted
from exactly that state), and this cannot see which. Read the gate for that.
"""
import ast
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import closing_error                                          # noqa: E402
import jscomments                                             # noqa: E402

DOC = os.path.join('docs', 'TOOLING-INVENTORY.md')
SETTINGS = os.path.join('.claude', 'settings.json')
GATE = os.path.join('tools', 'sairn_push_gate_hook.py')

# ── THE HAND-WRITTEN HALF ───────────────────────────────────────────────────
# One line per tool that REGISTRY does not already describe. Kept here rather
# than in the document so the document stays fully generated, and so a missing
# entry is an ERROR rather than a blank cell nobody notices.
#
# `kind` is the thing a reader most needs: CHECKER means it answers a
# pass/fail question about this codebase; LIBRARY means it is imported or
# shelled out to by something else; GENERATOR means it writes a file;
# LIVE means it makes a real network or database request, so it cannot be wired
# into a hook without making every push talk to the outside world.
PURPOSES = {
    'sairn_status.py': ('REPORTER',
        'what every agent on this machine says it is doing, RIGHT NOW, without a '
        'push/pull. The gap tools/session_lock_check.py names in its own header '
        'and puts out of scope: the lock answers "is somebody else in THIS '
        'directory", this answers "what is every agent doing". '
        'tools/dispatch_state.py already joins the open-work index against the '
        'claims, but both of its inputs are in git, so its answer is only as '
        'fresh as the last fetch and an unpushed claim is invisible. This is the '
        'live half: ~/SAIRN-SESSION-LOCKS/status, outside every clone. '
        'ONE FILE PER AGENT, NOT ONE FILE WITH SECTIONS -- a shared file needs a '
        'read-modify-write and two interleaved readers silently erase each '
        'other, which the control measures at 5 of 6 agents lost. Writes are '
        'atomic (temp + os.replace) with a Windows retry on both sides of the '
        'rename. Read at SessionStart by a hook that FAILS OPEN. It refuses to '
        'call two task strings the same work -- that judgement scored 38% with '
        'five false positives out of five'),
    'landing_verification.py': ('CHECKER',
        'three things that get ASSUMED rather than measured: (a) whether what '
        'is PUSHED is actually LIVE, for every route in vercel.json rather '
        'than the one url deploy_verify_notify.py watches; (b) whether each '
        "clone's on-disk .claude/skills matches origin/main, plus the repo's "
        'mirror against the user skill store -- a structurally different '
        'second opinion, because clones that are all wrong the same way agree '
        'with each other; (c) whether any npm or pip package has a real '
        'available upgrade. Report-only and NOT on the push path: it needs the '
        'network and answers questions the diff in front of a push cannot '
        'change. The clone list is DISCOVERED, never written down -- CLAUDE.md '
        'names four and there are five on disk. A Vercel bot challenge is '
        'UNVERIFIED, never a match; an absent npm is COULD NOT TELL, never '
        '"nothing outdated"; and CRLF-vs-LF is not drift'),
    'ai_prompt_refusal_check.py': ('CHECKER',
        "an app's own named *_RULE / *_REFUSAL constant is missing from one of "
        "that app's AI call sites, or replaced there by a hand-written rule "
        "block that only LOOKS equivalent -- sairnlaw's constant forbids case "
        "citations outright while one site's inline rule permits real ones. "
        'Item 8 sub-item 7, the half that needs NO MODEL CALL. It counts WORDS '
        'PRESENT IN A PROMPT and cannot show the model obeys them; that half is '
        'deferred. Report-only, and a divergence is not automatically a bug'),
    'bypass_log.py': ('CHECKER',
        'item 86, the battleshort pattern -- every push-gate override recorded in '
        'its OWN log, and a REPEATEDLY bypassed check reported as a defect in the '
        'CHECK rather than a discipline problem in whoever keeps bypassing it. '
        'Until this, SAIRN_SEED_GATE=off returned from the hook before a single '
        'check ran and NOTHING recorded that it happened. Both override sites now '
        'record, FAIL-SAFE: a push is never blocked because its logging failed, '
        'proven by driving the hook with the logger deliberately broken. A '
        'STANDING bypass with no expires_at is INVALID rather than permanent -- '
        'that is the switch nobody flips back. An empty log is evidence about the '
        'HOOK, not the platform: --no-verify never reaches it'),
    'ooda_phases.py': ('CHECKER',
        'item 67 -- WHICH OODA phase is the bottleneck, and it refuses to '
        'publish an aggregate because three of the four boundaries are not '
        'recorded anywhere. Measured 2026-09-15: detect-to-fix is SAME DAY on '
        '73 of 73 resolvable records, so the only phase this repo times is '
        'already as fast as it can be and every second of real exposure lives '
        'in a phase nothing times -- the cron incident, silent 24 hours, and '
        'send-reminder.js returning 500 hourly FOR MONTHS. A negative duration '
        'is reported as an ANOMALY rather than averaged away. Needs the same '
        'injection-date field item 66 is blocked on; the two are one field apart'),
    'nhi_register.py': ('GENERATOR',
        'every NON-HUMAN IDENTITY with a named OWNER and a real SCOPE, because '
        'an env-var scan structurally cannot answer that -- a GitHub PAT, a '
        'Postgres LOGIN role and four clones credentialed by the Windows '
        'credential manager are not `process.env` reads. REFUSES when a '
        'credential secrets_inventory calls a CREDENTIAL belongs to no identity, '
        'or when sql/ creates a role with no entry. Its first run found ELEVEN '
        'credentials with no recorded owner. Complements '
        'docs/SECRETS-INVENTORY.md rather than replacing it: that one answers '
        'what a variable unlocks, this one answers who owns it'),
    'sabotage.py': ('LIBRARY',
        'the negative-control recombination: plant a defect so that FAILING to '
        'plant it is LOUD. Four approaches already existed here and each was '
        'right about a different failure -- PRESENCE catches a rename, '
        'UNIQUENESS catches hitting the wrong site, MATERIALISATION catches the '
        'write not landing, and LINE-NUMBER ablation avoids ambiguous anchors '
        'entirely. This applies the first three to both planting strategies, '
        'and raises CouldNotSabotage as an EXCEPTION rather than returning None '
        'so a caller cannot reproduce the silent no-op. It does NOT migrate the '
        'remaining unguarded controls -- a mechanical rewrite of somebody '
        'else\'s control is how a working one breaks. Companion to '
        'sabotage_control_check.py, which MEASURES the class'),
    'line_endings.py': ('LIBRARY',
        'the CRLF-vs-LF recombination: 52 files here handle line endings '
        'independently and most are RIGHT, because they had already converged '
        'on `newline=\'\'` for round-tripping. What none of them wrote down is '
        'that COMPARING is a different job with THREE answers -- IDENTICAL, '
        'ENDINGS_ONLY and DIFFERS -- and that collapsing the first two is what '
        'produced the false "files differ" alarms four times in one session. '
        'Validated against the real case: repo vs user-store skills, a bare '
        'byte compare reports 11 diverged, the true answer is 0. Does NOT '
        'migrate the 52 -- it exists so the next one is not a 53rd '
        'implementation'),
    'ai_action_approval_audit.py': ('CHECKER',
        'an AI-PROPOSED action that reaches storage with no human approval -- '
        'the mechanical half of a rule that is currently only written down. '
        'Measured 2026-09-15: 74 AI call sites across all 17 apps, 39 gated BY '
        'CONSTRUCTION (render-only), 14 that write in the same handler, and '
        'ZERO carrying an explicit approval gate. A LOCATOR, not a detector: a '
        'chat-transcript write reads the same as an invoice write, and a '
        'confirm() one function away reads as absent. Its first real run was '
        'WRONG TWICE and both are recorded in its header -- it missed ten apps '
        'that hold the proxy URL in a constant, and it counted the AI call\'s '
        'own POST as a data write, inflating the headline from 14 to 59'),
    'accepted_risk_scan.py': ('CHECKER',
        'a risk somebody deliberately ACCEPTED in a comment and recorded '
        'nowhere central -- the shape that got api/sairncash/portal.js read as '
        'an unrecognised gap twice in one afternoon. A LOCATOR, not a detector: '
        'it reads language, not intent, and scored roughly 1 in 3 on its first '
        'weight-3 run. A read-list whose count is not a score; zero would mean '
        'deleting comments'),
    'tier_a_review_gate.py': ('CHECKER',
        'a change to code serving a Tier A resource that carries no recorded '
        'independent-review obligation, and a review record signed by its own '
        'author -- push-gate check 13, BLOCKING. Scoped by diff HUNK and not by '
        'file: the same question asked per FILE reported 78 Tier A resources '
        'for a one-line edit to api/sd-data.js, because that file names every '
        'resource on the platform. It cannot read a review and says so; what it '
        'refuses is a Tier A change nobody was told about and a self-signed one'),
    'pinned_list_drift_check.py': ('CHECKER',
        'a hand-written list of resource names that is a PARTIAL cover of an '
        'app Tier A set with nothing comparing the two -- the shape that left '
        'sc_denial_events accepting a write from the licence key alone while a '
        'gate list of six sat beside a register that said seven. A DERIVED list '
        'produces no row, which is the fix. A read-list rather than a score: '
        'its first run gave 12 rows and 1 defect, and the one was inside the '
        'live probe built to catch this'),
    'conflict_marker_check.py': ('CHECKER',
        'an unresolved VCS conflict marker at the start of a line, in any file '
        'in any language -- push-gate check 14, BLOCKING on day one because the '
        'false-positive baseline is MEASURED: all four shapes across 2,069 '
        'tracked files, zero hits, including the bare seven equals signs that '
        'ASCII banners would be expected to produce. Markers reached '
        'origin/main THREE TIMES in five days, once into a Tier A source file, '
        'while md_table_check carried a conflict regex the whole time -- it '
        'reads only markdown tables, is report-only, and gates on the wrong '
        'number'),
    'tier_a_replaceability_check.py': ('CHECKER',
        'item 97 -- whether a Tier A resource is the real irreplaceable '
        'artifact or a stand-in: which Tier A resources grant a HARD delete '
        'rather than soft_delete or none, read from the LIVE registry because '
        'SAIRNcode builds its grants with a reduce() that a source scrape '
        'would miss. Reports the count, never a verdict; the under-assignment '
        'direction (a Tier B/C resource that is the only copy of something '
        'irreplaceable) is deliberately NOT swept and says so on every run'),
    'defect_budget.py': ('CHECKER',
        'which STANDING RULE has bitten often enough that its next occurrence '
        'is predictable rather than incidental. The RANKING is deliberately not '
        'quoted here: the same figures were written into '
        'docs/2026-09-14-item20-and-entity-split-sweep.md and four of them were '
        'wrong within a day, because a hand-typed copy of a generated number '
        'has no way to announce that it moved. Run the tool. Per RULE because '
        'per APP cannot work: item '
        '51 measured 9 of 11 apps at three records or fewer, and a per-app '
        'budget would punish looking, since the app audited hardest looks '
        'worst. Report-only and must stay so -- a gate here would reward not '
        'citing a rule'),
    'defect_budget_policy.py': ('CHECKER',
        'item 20 -- a defect budget that FORBIDS rather than informs, and the '
        'ways that gate quietly stops forbidding anything: a band that flips on '
        'noise at a boundary (held inside a 3-point margin, in BOTH directions, '
        'because declaring recovery early is the tempting half), a decision '
        'recorded without the number that produced it (every stamp carries the '
        'criteria version and a digest of the register CONTENTS, so a later '
        'reader can separate "the number changed" from "the reading was '
        'wrong"), a recount silently reversing a recorded decision (it raises '
        'REVISIT and rewrites nothing), a binary in-or-out budget that forbids '
        'everything the day it flips (four graduated bands), and an override '
        'used habitually (counted at the top of every run; past 3 in a window '
        'the MECHANISM is reported failed, and the override is still accepted, '
        'because a policy that cannot be overridden in an emergency gets '
        'disabled entirely). ROLLING vs PERMANENT aging is a REAL OPEN '
        'QUESTION, deliberately not defaulted: both numbers are printed, '
        'nothing is gated until --decide records a choice with a reason. On its '
        'first run both windows read zero remaining and the most extreme band, '
        'which the tool reads as the BUDGET being wrong rather than the platform '
        'being in crisis -- it reports UNCALIBRATED and prints the observed rate '
        'instead of tuning BUDGET_PER_WINDOW until the output flatters the corpus'),
    'trend_alarm.py': ('CHECKER',
        'item 45 -- the two things a THRESHOLD cannot see, because a threshold '
        'is the P term of a controller and nothing else: a metric parked '
        'slightly bad for a long time that never crosses (the integral blind '
        'spot) and one comfortably inside the line but moving toward it fast '
        '(the derivative blind spot). Both are reported as MEASUREMENTS on '
        'every run because a slope and an accumulated exceedance need no gain; '
        'the word ALARM is gated on a tuning record this platform does not yet '
        'have, and the missing half is named -- with zero LABELLED EPISODES '
        'only the false-positive rate is measurable, and an alarm wired to '
        '`return` scores perfectly on that one too. FOUND LIVE ON ITS FIRST '
        'RUN: `traceability-ratio` and `traceability-untraced` are the same '
        'generated document and the same 221 readings, and they disagree -- '
        'the headline ratio improves monotonically while the absolute untraced '
        'count rises, so a P-term threshold on the headline reads better every '
        'day for five days while the backlog grows'),
    'weakness_combination.py': ('CHECKER',
        'item 53 -- a pair of separately-accepted risks where the SECOND one '
        'removes the bound the FIRST was accepted on. Citicorp Center: '
        'perpendicular-wind design was fine, substituting bolted joints for '
        'welded was fine, and nobody ran the quartering wind because each half '
        'had already been signed off alone. Four pair signals over '
        'docs/ACCEPTED-RISKS.md, the strongest being BOUND NAMES THE OTHER (A '
        'is held up by X, B is a recorded weakness in X). It reports pairs and '
        'refuses the verdict: whether a pair compounds is a judgement. TWO '
        'THINGS IT FOUND ABOUT ITSELF AND ABOUT THE REGISTER. Its own first '
        'version fired on 6 real pairs out of 6 because "bound is not a '
        'control" is a property of ONE entry that propagates into every pair it '
        'appears in -- now reported per entry, with the regression arm that '
        'catches it coming back. And the register\'s own rule (a trigger nobody '
        'watches is not a trigger) applied TO the register finds that its one '
        'MECHANICAL trigger names a module no runner on this platform '
        'mentions: the signal is PRODUCED and never CONSUMED. RESIDUAL, stated '
        'on every run: it can only pair risks somebody wrote down'),
    'first_article_inspection.py': ('CHECKER',
        'item 47 -- a NEW artefact that was SPOT-CHECKED rather than verified '
        'against every claim its own header makes. Two layers and only one gets '
        'a verdict: whether the artefact has a suite AT ALL is answered outright '
        '(zero arms verify zero claims, and knowing that needs no matching), '
        'while the claim list and the arm list are printed side by side and '
        'DELIBERATELY NOT MATCHED -- pairing prose to prose is word-overlap '
        'scoring and that returned 38%% with five false positives out of five '
        'here, which is why the FAI document says the two lists must not be '
        'matched automatically. FOUND: 7 of 27 artefacts added on 2026-09-15 '
        'have no suite, carrying 83 stated claims between them. AND IT '
        'COMMITTED BOTH OF ITS OWN FAILURE MODES FIRST: hardcoded arm helpers '
        'read a real suite as ZERO arms because that file names its helper '
        '`t()`, a top-anchored regex read three shebanged tools as ZERO claims, '
        'and a loose stem search matched tools/sabotage.py to 34 files. The arm '
        'dialect is now DISCOVERED per file and an unrecognised one reports '
        'COULD NOT TELL rather than zero'),
    'rotation_blast_radius.py': ('CHECKER',
        'item 61 -- a credential that is rotated but overprivileged, or scoped '
        'tightly but never rotated. TWO independent columns, never combined '
        'into a posture score, because the documented failure is treating one '
        'as the other: rotation shortens the window a leaked secret works and '
        'does nothing about what it reaches; scope bounds the blast radius and '
        'says nothing about how long the access lasts. A third list is the '
        'INTERSECTION, not an average and not a union -- the identities where '
        'neither control is doing anything. MEASURED over the 22 NHI '
        'identities: 20 have no attested date and no schedule, 7 hold broad '
        'standing access, and ZERO record what to do if that credential is '
        'known to have leaked. Every identity has a PROCEDURE for rotation, '
        'which says HOW and never WHEN. UNATTESTED IS NOT "NEVER ROTATED" -- no '
        'clone holds these credentials, so a missing date is the absence of a '
        'note; what IS a fact is that nothing here would notice either way'),
    'blind_review.py': ('CHECKER',
        'item 79 -- a reviewer anchoring on an automated verdict they saw '
        'before forming their own. The mitigation is an ORDERING and not a '
        'warning: `--start` writes a worksheet of EVIDENCE ONLY with the '
        'recorded severity removed and sealed in a file the worksheet never '
        'names; `--submit` takes the reviewer\'s own severities and only THEN '
        'reveals. Every judgment must carry a DEFEATER -- what would have to be '
        'true for that severity to be WRONG -- refused below a substance floor, '
        'because an accept with no engagement is re-anchored by the reveal '
        'anyway. WHAT IS MECHANICAL: the worksheet is SCANNED for every '
        'withheld value and the round is REFUSED if one appears; a submission '
        'modified before the round opened is refused; the sealed file is '
        'gitignored. WHAT IS NOT, and is printed on every round: nothing stops '
        'a reviewer opening the seal -- the control is that doing so is a '
        'deliberate act rather than the default reading order. FIRST REAL '
        'ROUND: 3 of 6 agreed with the recorded severity. ONE ROUND MEASURES '
        'NOTHING ABOUT AUTOMATION BIAS -- the experiment needs the same '
        'reviewers under a SCORE-FIRST ordering and that arm does not exist'),
    'accepted_risk_trigger_check.py': ('CHECKER',
        'an accepted risk whose trigger is labelled MECHANICAL and is watched '
        'by nothing. The register\'s own rule -- a trigger nobody watches is '
        'not a trigger -- checked against the register. The distinction it '
        'turns on is narrow and is the whole tool: PRODUCING a signal is not '
        'CONSUMING one, and an entry cannot show the difference. Split out of '
        'weakness_combination.py exactly as that tool\'s NOT_PROMOTED entry '
        'said it should be, and it IMPORTS that module\'s functions rather than '
        're-implementing them so the two cannot disagree about what the '
        'register says. A mechanism counts as watched when a runner names the '
        'SUITE that guards it, not only the module -- requiring the module '
        'itself reported a genuinely guarded mechanism as unwatched. It says '
        'plainly that a suite is NOT a consumer: this answers whether anything '
        'holds the mechanism, never whether anything reads its signal'),
    'optimistic_success_scan.py': ('CHECKER',
        'a write whose promise the caller DROPS, followed by a toast that '
        'therefore cannot depend on whether the write succeeded. '
        'write_path_fault_scan.py matches the DATA WRAPPER by name and so '
        'reported sairngrounds clean while addCoursePoint() announced "Point '
        'captured" for writes that never left the device -- the fire-and-forget '
        'had moved one level up, into a LOCAL ASYNC HELPER. The rule is '
        'structural and uses NO word list: a dropped promise cannot be read in '
        'that scope, so any later toast is unconditional by construction, and '
        'the message text is printed for a human. FIRST SWEEP: 14 candidates '
        '-- THREE REAL AND FIXED (sairndental addSupply and vPlaceOrder, '
        'sairndesign markRoomARPoint), four an ACCEPTED decision recorded at '
        'the site, four the branch false positive it names with a measured '
        'number, and three a rule defect of its own (an element of an awaited '
        'array takes its result). A CLEAN RUN IS A FLOOR: it follows ONE hop, '
        'which is the same limit that hid this class from the narrower tool, '
        'moved further out rather than removed'),
    'tier_a_bypass_check.py': ('CHECKER',
        'an HTTP handler that names a Tier A resource IN CODE without both an '
        'identity check and a refusal. Three states, never two -- COULD NOT '
        'TELL is the interesting column. GATED is not a clearance: it cannot '
        'tell whether the refusal runs BEFORE the write, and a name is not a '
        'write. A read-list, not a number to drive to zero'),
    'copy_exactly_check.py': ('CHECKER',
        'whether the one literal must-copy-exactly block still matches the app '
        'it was copied from -- 0 of 5 identical on 2026-09-14, 4 differing '
        'because the APP was fixed and the document was not. Four states, '
        'never collapsed: identical / reflowed (NOT drift) / differs / absent. '
        'It does NOT answer disciplines 7 -- agreeing bytes are what that '
        'section warns is not safety'),
    # --- invoked by a hook or by the push gate -----------------------------
    # NO COUNT HERE, DELIBERATELY. This said "the ten numbered push checks" and
    # the gate has eleven; the gate's own header says "DO NOT TRUST THAT NUMBER
    # -- count the `CHECK n:` markers". The closing-error block of this very tool
    # prints the live figure, so a number written here is a second source that
    # can only ever drift away from it. Removed rather than corrected -- a
    # corrected count goes stale again on the next check.
    'sairn_push_gate_hook.py': ('CHECKER', 'the numbered push checks; the only tool that calls deny()'),
    'git_push_master_guard.py': ('CHECKER', 'a push aimed at `master`, which is stale'),
    # The PREVENT half of the hover auditor separation control. Its DETECT half
    # is hover_separation_audit.py, which is in report_only_checks.REGISTRY and
    # must therefore NOT be described here as well.
    'hover_separation_ci.py': ('CHECKER', 'a commit that touches the HOVER AUDITOR\'s own skill directory AND code outside its scope, checked on GitHub\'s side of the push where a local hook cannot be switched off. The ENFORCE layer under the existing PREVENT (hover_auditor_scope_gate.py, a per-clone hook that is silent whenever its marker is absent, --no-verify is used, or the clone was never armed) and DETECT (hover_separation_audit.py). Keys on COMMIT SHAPE, not on attribution: its first version asked "is this the auditor\'s commit and did it leave scope", which could never fire, because a commit in which the auditor also touches platform code is unattributable by construction -- the exact commit the gate exists to refuse was the one it could not see. Catches the boundary in both directions, including a build agent reaching into the auditor\'s directory. Cannot see a commit that touches ONLY platform code and says so on every run'),
    'hover_auditor_scope_gate.py': ('CHECKER', 'a commit, push or working tree in the HOVER AUDITOR\'s clone that touches platform code -- the role reviews the four build agents and is reviewed by nobody, and its own skill forbids it writing platform code in terms. Armed per-clone by a marker under .git/, so no build clone can inherit it by pulling and each pays one shell file-test per commit. Fails OPEN where the marker is absent (a scope condition: not that clone\'s rule) and CLOSED everywhere else, including when the core-rule sentence is no longer in the skill file -- a gate enforcing a repealed rule reads as coverage'),
    'redaction_check.py': ('CHECKER', 'credential shapes in what is about to be written, and in what a push ships'),
    'html_script_check.py': ('CHECKER', 'a script block that no longer parses, after a Write or Edit'),
    'deploy_verify_notify.py': ('CHECKER', 'a push whose deploy never reached the live site'),
    # Same reason as the line above: this said "the 26 entries above" and the
    # registry holds thirty-six. The count is printed by the closing-error block.
    'report_only_checks.py': ('LIBRARY', 'the report-only registry and its runner -- the entries above'),
    # A LIBRARY, NOT A CHECKER, and it is listed for exactly the reason this
    # refusal exists: it has no findings of its own and would otherwise sit in
    # tools/ as a blank cell. It is the three things every checker here has had
    # to get right -- the three-state exit contract, comment-stripped parsing,
    # and the control-pair declaration -- so the next one is built THROUGH them.
    #
    # THIS ENTRY IS THE OTHER SESSION'S, KEPT OVER MINE IN A REBASE (2026-09-14).
    # We wrote one each within the same hour because the generator was REFUSING
    # over the missing line and both of us hit the refusal independently. Theirs
    # names the three things; mine summarised them. One survives, and which one
    # is recorded so the duplicate work is visible rather than looking like a
    # single authorship.
    'checker_kit.py': ('LIBRARY', 'the exit-code contract, comment-stripped parsing and the '
                                  'control-pair declaration, extracted so the next checker '
                                  'is built through them rather than re-deriving them'),
    # UNWIRED ON PURPOSE, and the reason belongs here rather than in a commit
    # message: a digit-distribution result is a POINTER, never a verdict, so
    # there is nothing for a gate to do with it. Registration also waits on
    # Cody's report-only sweep-timeout work, because a registry entry is what
    # blew that budget last time.
    'three_way_match_check.py': ('CHECKER', 'a goods receipt or a vendor bill written with no '
                                            'join key back to its purchase order, and a PO '
                                            'number derived from a row count (which reuses '
                                            'itself after a delete). Structural half runs from '
                                            'the repo; the PO-vs-receipt-vs-bill comparison '
                                            'needs an export and is COULD-NOT-RUN without one'),
    'checker_confidence.py': ('CHECKER', 'a promoted checker whose answer is not worth much -- the CONTINUOUS flip-rate signal and the INFREQUENT control-pair signal fused by MINIMUM, so a perfect flip rate with no control caps at LOW rather than averaging to MEDIUM. The corrector proves its own safety exhaustively before reporting anything'),
    'defect_dispersion.py': ('CHECKER', 'whether defect causation is concentrated in a few commits, files, apps or sessions or spread evenly -- every figure reported BOTH over the affected units and over the full population including the zeros, because the first alone always looks uniform and is the flattering one'),
    'retry_backoff_check.py': ('CHECKER', 'a loop that calls something we do not control and neither pauses nor trips a breaker between attempts -- the shape that turns a dependency\'s bad minute into a worse one. Brace-matches every api/*.js and every <script> block in the app HTML into a block tree and asks whether the enclosing construct is a loop, rather than looking for the word "retry" (88 hits in stonedesk.html, almost all comments, user-facing messages and a failed-LOGIN counter). Distinguishes a RETRY from pagination and work-list ITERATION by asking whether the loop rebinds anything the call reads, not by comparing source text. Also reports how many files import api/_lib/resilience.js, because a clean retry sweep on a platform whose only breaker has no callers is not reassurance'),
    'suite_control_triage.py': ('CHECKER', 'which of the UNCONTROLLED suites to sabotage first -- it joins suite_control_coverage.py to docs/CRITICALITY-TIERS.md so the 142 suites nobody has ever tried to break are ranked by whether they guard money or a regulated record, rather than worked alphabetically. Catches the suite whose assertion power is unmeasured while the thing it guards is the most expensive kind to get wrong. Reports UNCLASSIFIED apart from Tier C, because a suite that names no registered resource is unranked and not low'),
    'assurance_case.py': ('CHECKER', 'item 5 -- the structured argument from the Tier A claims to the evidence that exists, GSN goal/strategy/solution with every leaf a COMMAND run on each invocation rather than a sentence. Undeveloped goals are DRAWN, assumptions are named so they can be rejected, and a goal is supported only if every child is -- no weighting, because a weighted score lets a strong branch carry a weak one'),
    'risk_event_tree.py': ('CHECKER', 'item 84 -- items 6, 19, 35 and 65 as four barriers in series against one initiating event, with the worst end state (corrupted, undetected, unrecoverable) computed as a RANGE over judgement bands rather than a point. Reports which band is widest and whether the importance RANKING is stable across every corner; today it is not, and the tool says so instead of ranking anyway'),
    'dora_metrics.py': ('CHECKER', 'deployment frequency, lead time, change failure rate and time to restore measured from this repository. Separates commits that touch a DEPLOYABLE SURFACE from the claim files and worklogs that deploy and change nothing, refuses to present a trunk-topology lead time as an elite result, and computes CFR only over the records that really link a failure to a deployment -- with the coverage as the headline'),
    'retry_policy_audit.py': ('CHECKER', 'item 81 -- every LOOP or CATCH that re-issues a remote call, classified RETRY / POLL / AGENT-LOOP by structure rather than by the word "retry", with its backoff, its bound and its jitter measured from the extracted body. Two earlier attempts were retracted: a regex that matched comments, and a first version of this tool that called iteration and pagination retries'),
    'suite_control_coverage.py': ('CHECKER', 'which JavaScript test suites have a NEGATIVE CONTROL -- a probe that breaks the source and asserts the suite goes red -- and which have only ever been green. Applied, unique, EFFECTIVE: sabotage_control_check.py asks the first, mutation_anchor_check.py the second, and both name this third as a gap they cannot close'),
    'first_article_check.py': ('CHECKER', 'item 47 -- whether a new artefact has had a First Article Inspection against every claim its own header makes, and whether that inspection still describes the bytes on disk. The claim-to-arm mapping is human by design; what is mechanised is completeness, currency, and that every cited arm still exists'),
    'entity_baseline_readiness.py': ('CHECKER', 'whether a PER-ENTITY defect baseline is buildable yet and on which entity -- two bars, records per unit AND a measurable exposure denominator, because a dimension with enough records and no denominator produces a count wearing a rate. Re-answered from the register every run so the day it flips, something says so'),
    'benford_check.py': ('CHECKER', 'money figures whose leading-digit distribution does not '
                                    'look measured -- a LOOK HERE pointer for the '
                                    'fabricated-KPI class, with a shape pre-check that '
                                    'REFUSES any dataset too small, too narrow, too rounded '
                                    'or too repetitive to carry the test'),
    'session_lock_check.py': ('CHECKER', 'a second session in the same clone -- warns at SessionStart, and REFUSES Write/Edit/Bash when the other session is confirmed live by CLAUDE_PID plus its process start time. Liveness that cannot be determined falls back to the 2h staleness rule and blocks nothing'),
    'sairn_claim_hook.py': ('CHECKER', "another session's active claim on the work about to start"),
    'employee_auth_guard_check.py': ('CHECKER', 'a SQL file writing credential rows with no recoverability guard (gate check 2)'),
    'sairn_sql_preflight.py': ('CHECKER', 'SQL referencing a column or table the live schema does not have (gate check 3)'),
    # LIVE because it calls the DEPLOYED endpoint -- it cannot be wired into a
    # hook without making every push talk to the outside world, which is the
    # exact reason this `kind` exists. It is the NAMED STOPGAP reader for the
    # audit checkpoints (Michael, 2026-09-14) until item 54's liveness monitor
    # takes over; a run that cannot reach the endpoint overwrites the previous
    # clean verdict with COULD NOT TELL rather than leaving a document
    # asserting a check that never ran.
    # LIVE for the same reason, and it is the OUT-OF-BAND half of item 54:
    # api/cron-watchdog.js runs on the same Vercel scheduler as the jobs it
    # watches, so a total scheduler outage silences both. This runs outside
    # Vercel and is the only thing here that survives that -- but only when
    # somebody runs it, which is why the doc it writes says so.
    # LIVE: it talks to whatever database it is pointed at. Item 65a, and it
    # exists BECAUSE there is no backup to restore -- Supabase free tier,
    # confirmed 2026-09-14 -- so the realistic restore is the hand one
    # somebody does at 3am, and this is what asks whether the result is
    # coherent. Needs no scratch environment and no baseline capture: the
    # audit checkpoint chain is a fingerprint carried inside the data.
    # A GENERATOR, and item 28's fold-in. checker_kit.py holds the three
    # things every checker here has had to get right; what a library cannot
    # do is make anyone USE them. Every defect that file's header lists was
    # a checker that skipped one -- their authors had the library, not a
    # starting point with the wiring already in it.
    # Item 90. REPORT-ONLY and not registered: each shape is narrowed to the
    # SIGNATURE a real platform bug had, not to the textbook concept, because
    # a checker that reported the concepts would be a design opinion on most
    # of the tree and switched off inside a day.
    'shape_antipattern_check.py': ('CHECKER', "Number(x) on an outside value with no guard (Number('') is 0), a guard collapsing several distinct failure reasons into one bit, and three-plus nullable fields carrying one either/or state"),
    'new_checker.py': ('GENERATOR', 'scaffolds a checker and its control pair, wired through checker_kit -- and what it emits REFUSES (exit 2) until its rule is written, so a fresh checker can never report clean'),
    # Item 78's runnable half. docs/spec/RoleGates.tla states the properties
    # formally; this checks the REAL exported role sets still have them.
    # Neither alone is enough -- a spec that drifts from its code is a
    # document asserting properties nobody holds.
    # Item 78's second target. A MODEL, not a checker of this repo: it
    # enumerates every interleaving of the rate limiter's count-then-insert
    # and exhibits the schedule that breaks the cap. The defect is not in any
    # single execution, which is why a test cannot find it.
    'rate_limit_race_model.js': ('CHECKER', "the AI rate limiter's count-then-insert breaking its own cap under concurrency -- enumerated over EVERY interleaving, with the violating schedule printed, against docs/spec/RateLimitConsume.tla"),
    'role_gate_invariants.js': ('CHECKER', 'a cross-app role gate that has stopped satisfying docs/spec/RoleGates.tla -- a provisioner who is not management, a management role that cannot sign in, or an empty allowed-set that is a door with no key. Reads three sources and NEVER fuses their counts: what a module exports, what it declares internally (read by executing it, because `sb-auth.js` carries the text MANAGEMENT_ROLES inside a comment saying the app has no such concept and any text scraper is wrong there), and AUTHENTICATED_ROLES derived from ROLES_BY_APP -- that last licensed by invariant I6 and WITHDRAWN PLATFORM-WIDE if I6 fails, because a derivation whose control lapsed must stop answering rather than keep answering. Distinguishes a constant that is absent from one this tool could not read, and separates the remainder that is a fact about an app from the remainder anyone can close'),
    'restore_coherence_check.js': ('LIVE', 'a restored or hand-recovered database that is NOT coherent -- audit windows that lost, gained or changed rows, and orphaned references the database has no foreign key to complain about'),
    'cron_liveness_check.py': ('LIVE', 'a scheduled job that stopped, ran late, or ran and failed -- asked from OUTSIDE Vercel and written to docs/CRON-LIVENESS-STATUS.md'),
    'audit_checkpoint_status.py': ('LIVE', 'a daily audit checkpoint that FAILED, or could not be asked -- written to docs/AUDIT-CHECKPOINT-STATUS.md instead of a log line nobody opens'),
    'sairn_load_state_check.py': ('LIVE', 'live seed content differing from the repo seed (gate check 1)'),
    'sairn_seam_check.py': ('CHECKER', 'an endpoint dropping a field the engine reads (gate check 4)'),
    'sairn_reachability_check.py': ('CHECKER', 'a feature no user can reach (gate check 5), plus three REPORT-ONLY rungs that never gate and never suggest removal: R4 is the route still served in production, R5 is the function inside it invoked, and R6 is the RESOURCE asked for by name, and R7 the ACTION -- neither answerable by R4 or R5, because they measure at the ROUTE: /api/sd-data is ONE route carrying 385 registered resources, and 182 individually addressable actions sit behind 27 routes, 19 of them behind api/law-auth.js alone'),
    'preauth_oracle_check.py': ('CHECKER', 'an endpoint that answers before it authenticates (gate check 7)'),
    # NOT gate check 9, and the stale inventory said it was. Check 9 runs the
    # test files named in the gate's own GUARD_TESTS list directly; nothing in
    # the repo references this tool at all. Corrected here because a wrong claim
    # about what guards a push is the exact failure this document exists to stop.
    'verify_review_gates.py': ('CHECKER', 'review-gate evidence in a claims ledger -- referenced by NOTHING in this repo'),
    # --- checkers nothing invokes ------------------------------------------
    # Landed 2026-09-12 by another session, directly out of the checkblocks.py
    # finding: a checker that always exits 0 looks exactly like a codebase that
    # is always clean.
    # master_plan.py MOVED TO THE REGISTRY when its --check was promoted to
    # report-only. A REGISTRY tool must not also be described here: two
    # descriptions of one tool can disagree, and this file exists to stop that.
    # Same removal install_git_hooks.py needed on 2026-09-13, for the same
    # reason, caught by the same assertion.
    'closing_error.py': ('LIBRARY', 'not a checker: the CLOSING-ERROR guard every generated document uses -- one row per derivation source, and a REFUSAL if any source contributes nothing, because --check compares a document to its own generator and cannot see a source that went silent'),
    'checker_control_check.py': ('CHECKER', 'a promoted checker with no control proving it can FIRE -- one direction evidenced is not two'),
    'cleanup_residue_check.py': ('CHECKER', 'rows a cleanup SQL file claims to have removed and did not'),
    'claim_provenance.py': ('LIVE', 'not a checker and deliberately not one: it RECORDS how a Tier A claim was established -- what was observed, WHEN it was observed as distinct from when it was typed, by what method, and how somebody else could redo it -- and refuses a record that could not later be checked. Judging staleness is a separate build, after the chain has something in it, because the two tools that shipped able to judge with nothing to judge are the pattern this avoids. Subjects derive from docs/CRITICALITY-TIERS.md plus `migration:<file>.sql` validated against sql/, never a second hand-maintained list, and a zero-subject parse is treated as a broken reader rather than an empty register'),
    'sabotage_control_check.py': ('CHECKER', 'a negative control that never verifies its sabotage APPLIED -- when the anchor stops matching, str.replace silently does nothing and the control runs the checker against an unmodified file; the loud outcome is an arm failing against a working tool, the quiet one is an expect-no-findings arm passing forever'),
    'independence_check.py': ('CHECKER', 'an index row claiming an INDEPENDENT review that names only a second READER, or names no method at all -- a second read shares the assumptions of the first, so it cannot break a shared blind spot; also reports that the defect register is not capturing independent-review at all, which blocks the fraction-caught measurement'),
    'pra_event_tree.py': ('CHECKER', 'which END STATE a component failure reaches -- fails closed or not, announced or not, reconstructible or not -- for every chokepoint in docs/SPOF-REGISTER.md and every secret with no guard. Top-down and per-system, the complement of fmea_draft.py which is bottom-up and per-file. REFUSES to produce a frequency or a fused risk score: the only candidate population is defects-found-in-code over six days, which is not a component-failure rate. A branch that took one value on the input set is reported as not having discriminated'),
    'reliability_growth.py': ('CHECKER', 'whether the defect discovery series may be fitted by a reliability growth model AT ALL -- enough intervals, a FALLING rate, and effort recorded. Goel-Okumoto and Musa-Okumoto are implemented and locked against synthetic curves with known parameters, so the refusal is a statement about the data rather than about a fitter nobody has seen work. Today it refuses on all three criteria and names each measured value'),
    'condition_coverage.py': ('CHECKER', 'an operand of a compound condition in a Tier A financial engine that the suite does NOT notice being wrong -- mutation-derived condition coverage, deliberately NOT called MC/DC since it proves the suite would catch a wrong operand rather than that a test merely touched it'),
    'idempotency_check.py': ('CHECKER', 'a retryable write path that checks no caller key, or checks one against an IN-MEMORY store -- which looks idempotent and is not across processes; its POSITIVE fixture is the real api/ledger.js and its negative one is synthetic, disclosed on every run'),
    'invariant_runner.js': ('CHECKER', 'the three financial invariants -- double-entry, rollup, conservation -- property-tested against the real pure engines, reporting ACCURACY and STABILITY as two numbers and margin only where the invariant is an inequality'),
    'invariant_registry.js': ('CHECKER', 'not a checker itself: the LOCKED hand-derived classification of which invariant applies to which engine, the evidence it was read from, and the synthetic fixtures invariant_runner.js must satisfy before touching a real engine'),
    'testability_criteria.py': ('CHECKER', 'not a checker itself: the LOCKED pass/fail criteria and the hand-decided fixtures that testability_gate.py must satisfy before it may judge anything'),
    'fmea_draft.py': ('CHECKER', 'a FIRST-DRAFT risk analysis for one file, seeded only from confirmed prior defects and the standing lessons whose detector fires on it -- every risk cites the record or rule it matched, or it is not emitted'),
    'fmea_prediction_check.py': ('CHECKER', 'whether a saved FMEA draft actually predicted the defect that then landed in that file -- the loop-closing half, and the cadence: the answer changes every time the defect register grows'),
    'load_schema_snapshot.py': ('CHECKER', 'a candidate db/schema_snapshot.json that is empty, malformed, not newer, or has LOST tables -- the last being a truncated transfer, which is indistinguishable downstream from tables genuinely dropped'),
    'licence_recoverability_check.py': ('LIVE', 'a licence with credential rows and zero active provisioners'),
    "checker_estimate_fusion.py": ("CHECKER", "a checker whose reliability estimate rests on a CORRECTOR THAT FAILS ITS OWN SANITY CHECK -- it fuses the always-on drifting flip rate with the accurate infrequent control evidence, and REFUSES to apply the correction when the control does not verify its own sabotage applied, because a compromised corrector makes a fused estimate worse than no fusion"),
    "sairn_rebase_resolve.py": ("CHECKER", "a rebase conflict about to be resolved by the WRONG STRATEGY FOR ITS FILE CLASS -- it regenerates and stages a self-declared GENERATED document, REFUSES a source file outright, and refuses the whole run rather than doing a mixed set by halves; written after a --theirs loop put literal conflict markers on origin/main"),
    "entitlement_freshness_check.py": ("CHECKER", "an entitlement field with readers and NO in-repo writer -- a mirror nothing here can ever revoke -- and, separately, a paid-tier gate decided from an external identifier's PRESENCE rather than its state, which a cancelled subscription keeps forever"),
    'guard_ablation.py': ('CHECKER', 'a role gate in api/sd-data.js whose REMOVAL no suite notices -- reported as a question (redundant or untested, it cannot tell) and never folded into a pass'),
    'local_only_collection_check.py': ('CHECKER', 'a collection written only to localStorage that never reaches a server'),
    'missing_dom_target_check.py': ('CHECKER', 'a getElementById target that appears as no id in the file'),
    'reclassification_sweep.py': ('LIVE', 'a statutory rule whose source has been reclassified'),
    'rf_claim_gate_live_probe.py': ('LIVE', "SAIRNroofing's claim gate, against the deployed endpoint"),
    'sc_tier_a_write_gate_live_probe.py': ('LIVE', 'a SAIRNcode Tier A billing resource accepting a WRITE from the licence key alone, or refusing one from a role that should be allowed -- measured on the DEPLOYED function, and reporting absent credentials as UNVERIFIED rather than as a pass'),
    'rf_roundtrip_probe.py': ('LIVE', 'a SAIRNroofing write read back through the real API'),
    'probe_public_book_guardian.py': ('LIVE', "the public booking endpoint's guards, live"),
    'stonedesk_storefront_live_check.py': ('LIVE', 'whether sql/stonedesk_public_surface_schema.sql was really run, by probing the three public endpoints -- the instruction "confirm by re-probing, not by the editor reporting success", mechanised'),
    'sairn_ai_fact_scan.py': ('CHECKER', 'a number an AI panel states that no function computes'),
    'sairn_app_map_check.py': ('LIVE', "an app absent from Guardian's own app map, and a route that 404s"),
    'sairn_dead_function_sweep.py': ('CHECKER', 'a function with no caller anywhere'),
    'sairn_reachability_probe.py': ('CHECKER', 'the rendered-DOM half of reachability, from a browser snapshot'),
    'sairn_stale_snapshot_scan.py': ('CHECKER', 'a panel rendering from a snapshot nothing refreshes'),
    'sairnlaw_citation_audit.py': ('LIVE', 'a legal citation whose source no longer says what the rule claims'),
    'schema_provisioning_check.py': ('LIVE', 'a resource the app writes to whose table was never created'),
    'va_rule_currency.py': ('LIVE', 'a Virginia rule whose published source has moved on'),
    'waf_rule_check.py': ('LIVE', 'a WAF rule that would block a real request the product makes'),
    'write_path_fault_scan.py': ('CHECKER', 'a server write whose result is read on the success path only, or not at all'),
    'sairn_build_load_gates.py': ('GENERATOR', 'SUPERSEDED -- its header says so; a generated gate goes stale by design'),
    # --- libraries and generators -----------------------------------------
    'jscomments.py': ('LIBRARY', 'the one comment stripper every scanner should use'),
    'sairn_http.py': ('LIBRARY', 'browser-shaped HTTP, raising Challenged rather than letting a 403 look like an answer'),
    'sairn_source_fetch.py': ('LIBRARY', 'fetching a primary source with its retrieval date recorded'),
    'extract_scripts.py': ('LIBRARY', 'script blocks out of an app file, HTML-parser based'),
    'extract_panels.py': ('LIBRARY', 'panel containers out of an app file'),
    'outline.py': ('LIBRARY', 'a function/section outline of a large file'),
    'js_code_only_diff.py': ('LIBRARY', 'a diff with comment-only changes removed'),
    'run_all_tests.py': ('LIBRARY', 'every .js and .py under tests/, plus api/**/*.test.js'),
    'run_semgrep.py': ('LIBRARY', 'the .semgrep rules, when semgrep is installed'),
    # install_git_hooks.py MOVED TO THE REGISTRY 2026-09-13. Its `--check` is now
    # a report-only checker, and a REGISTRY tool must not also be described here
    # -- two descriptions of one tool can disagree, which is the whole failure
    # this document exists to stop. tests/run_tooling_inventory_probe.py asserts
    # the disjointness and caught this within the hour of the promotion.
    'sairn_claim.py': ('LIBRARY',
        'claim / release / check / list on the work-claim files -- plus `audit`, '
        'which catches a duplicate claim recorded AFTER the guard that covers '
        'it and, just as importantly, reports one recorded BEFORE as HISTORY. '
        'Released claims are kept on purpose, so every duplicate ever recorded '
        'stays in the file and a reader concludes the bug is live -- WHICH HAS '
        'NOW HAPPENED TWICE. Measured 2026-09-16: 631 claims, 6 duplicate '
        'groups, EVERY ONE predating its guard (the fourth triple by 43 minutes, '
        'the cc pair by 22) and zero in the ~150 claims since. It also counts, '
        'APART, the shape that IS live: claims never released, which is not a '
        'duplicate and needs the opposite fix. It refuses to decide that two '
        'DIFFERENT task strings are the same work -- exact means exact'),
    'gh_push.py': ('LIBRARY', 'a push whose arrival on the remote is queried back'),
    'gh_verify.py': ('LIBRARY', 'whether a commit is really on the remote'),
    'load_deadline_seed.py': ('LIVE', 'loads a deadline seed into a live licence'),
    'sairn_dom_snapshot.js': ('LIBRARY', 'a rendered-DOM snapshot, run in the browser'),
    'strict_args_harness.js': ('LIBRARY', 'proves the engine really discards a mutated parameter under strict mode'),
    'verify-session-token-app-scope.js': ('LIBRARY', 'the semgrep rule body for the app-scope check'),
    'posthook.cjs': ('LIBRARY', 'the Node half of a PostToolUse hook'),
    'fetch_blocked_doc.sh': ('LIBRARY', 'fetches a document a plain request cannot reach'),
    # DELETED from here 2026-09-12: it is in report_only_checks.py's REGISTRY,
    # which already carries its `catches`. Two descriptions of one tool can
    # disagree, and REGISTRY is the copy that actually runs. Found by this file's
    # own probe, section C -- the duplication existed for one commit.
}
for _p in ('gen_ma_calendar.py', 'gen_ma_seed.py', 'gen_mn_calendar.py', 'gen_mn_seed.py',
           'gen_mo_calendar.py', 'gen_mo_seed.py', 'gen_nj_calendar.py', 'gen_nv_calendar.py',
           'gen_ok_calendar.py', 'gen_or_calendar.py', 'gen_sc_calendar.py',
           'gen_ut_calendar.py', 'gen_va_calendar.py', 'gen_va_seed.py'):
    PURPOSES[_p] = ('GENERATOR', 'a court-holiday calendar or deadline seed for one state')


def git(*args):
    r = subprocess.run(['git', '-C', REPO] + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout if r.returncode == 0 else ''


def tool_files():
    out = []
    for f in git('ls-files', 'tools/').split('\n'):
        f = f.strip()
        if f.endswith(('.py', '.js', '.cjs', '.sh')) and '__pycache__' not in f:
            out.append(os.path.basename(f))
    return sorted(set(out))


def hooked():
    """{tool: [event, ...]} from .claude/settings.json."""
    out = {}
    try:
        d = json.load(io.open(os.path.join(REPO, SETTINGS), encoding='utf-8'))
    except Exception:
        return out
    for ev, lst in (d.get('hooks') or {}).items():
        for entry in lst:
            for hk in entry.get('hooks', []):
                for m in re.finditer(r'tools/([\w.\-]+)', hk.get('command', '') or ''):
                    out.setdefault(m.group(1), []).append(ev)
    return out


def gate_invokes():
    """Tools the push gate shells out to -- reachable from deny()."""
    src = io.open(os.path.join(REPO, GATE), encoding='utf-8', errors='replace').read()
    return sorted(set(re.findall(r"'([\w.\-]+\.py)'", src))
                  & set(tool_files()))


def gate_checks():
    src = io.open(os.path.join(REPO, GATE), encoding='utf-8', errors='replace').read()
    found = {}
    for m in re.finditer(r'#\s*──+\s*CHECK (\d+):\s*(.+?)\s*[─]*\s*$', src, re.M):
        found[int(m.group(1))] = m.group(2).strip().rstrip('-').strip()
    return [(n, found[n]) for n in sorted(found)]


def _roc():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'roc', os.path.join(REPO, 'tools', 'report_only_checks.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def registry():
    return [(r['tool'], r.get('promoted', '?'), ' '.join(str(r.get('catches', '')).split()))
            for r in _roc().REGISTRY]


def not_promoted():
    r"""{tool: why} from report_only_checks.py's NOT_PROMOTED list.

    ADDED 2026-09-12, because the first version of this file DID NOT READ IT and
    the headline number was wrong as a result. It counted 13 checkers as "pointed
    at by nobody"; SIX of those are on this list with a recorded reason -- a
    read-list whose own output refuses to be quoted bare, a tool needing a browser
    snapshot, two with open owned findings. Somebody had already decided each one,
    in writing, in the file this generator was already importing.

    That is the mirror of the SUITE-ONLY mistake in the same file: there the count
    OVERSTATED coverage, here it OVERSTATED the gap. Same root cause both times --
    a source of truth that existed and was not read. A number that calls a
    deliberate decision an unaddressed gap is how a reader stops believing the
    number.

    Entries can name several tools separated by commas; split so each is findable.
    """
    out = {}
    for tools_str, why in _roc().NOT_PROMOTED:
        for name in [s.strip() for s in tools_str.split(',')]:
            if name:
                out[name] = ' '.join(str(why).split())
    return out


def _prose_removed(name, src):
    """Source with COMMENTS and DOCSTRINGS blanked, and nothing else.

    Not all string literals: an invocation genuinely IS a string literal here --
    `subprocess.run([sys.executable, 'tools/x.py'])`,
    `os.path.join(REPO, 'tools', 'x.py')`. Blanking those would turn this
    document's optimistic failure into a pessimistic one, which is not an
    improvement, only a different lie.

    A DOCSTRING is the one string that is never an argument to anything, so it
    can be removed with no such cost. `tests/key_collision_probe.py` opens with
    "`tools/checker_control_check.py` asked every promoted checker for a file
    that declares itself its control" -- prose about a tool, read as running it.
    Length and newlines are preserved so nothing downstream shifts.
    """
    if not name.endswith('.py'):
        return jscomments.strip_comments(src)
    src = '\n'.join('' if l.lstrip().startswith('#') else l
                    for l in src.splitlines())
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    lines = src.split('\n')
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for i in range(node.lineno - 1, min(node.end_lineno, len(lines))):
                lines[i] = ''
    return '\n'.join(lines)


_SHELLS = ('subprocess.', 'check_output', 'Popen', 'execFileSync')
# The same declaration tools/checker_control_check.py reads, read the same way.
_DECL_RE = re.compile(r"CONTROLS_FOR\s*=\s*[\[\(]([^\]\)]*)[\]\)]", re.S)
_DECL_NAME_RE = re.compile(r"['\"]([\w.-]+\.py)['\"]")


def _call_arg_names(src):
    """Tool filenames passed as a direct argument to a call that RUNS things.

    THE SHAPE THE PATTERN LIST COULD NOT SEE, found 2026-09-13 once prose
    stopped providing false cover. A control that drives several checkers binds
    the directory once and passes the filename:

        TOOLS = os.path.join(REPO, 'tools')
        def run(tool, *args):
            subprocess.run([sys.executable, os.path.join(TOOLS, tool)] + ...)
        run('checkblocks.py', p)                      <-- the invocation

    `tests/run_uncontrolled_checkers_probe.py` drives FIVE promoted checkers
    that way, and the inventory credited it for none of them. They had looked
    covered only because other files MENTIONED them in prose, so removing the
    prose turned a false "covered" into a false "no probe" -- a different lie,
    not a fix.

    THE RULE IS A WHITELIST, NOT A BLACKLIST, and the first draft got this
    wrong. "Any direct call argument" also credited
    `cls.get('md_table_check.py')` -- a DICTIONARY LOOKUP naming a tool inside
    `tests/run_tooling_inventory_probe.py`, which asserts what this very file
    classifies things as. Four tools were credited to a probe that reads their
    NAME and never runs them. Blacklisting `get` would have been the start of
    an endless list, so the question is inverted: which calls turn a string
    into a PATH or a COMMAND?

      * `os.path.join(...)` -- the string becomes a path
      * a function DEFINED IN THIS FILE whose body shells out. That is the
        `run(tool, *args)` helper above, and it is why the earlier
        INVOCATION-proximity model failed: real controls wrap the subprocess
        call, so the tool name never appears near it.

    Anything else naming a tool is naming it, not running it.

    `tests/sairn_http_challenge.py` names three tools inside `WIRED = [...]` and
    a `for f in [...]` -- collection elements, never an argument to either kind
    of call -- and that list is exactly the false positive the earlier
    tightening removed. It stays removed.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()

    # Functions in THIS file that shell out. A control that drives several
    # checkers has exactly one of these and passes the filename to it.
    shells = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = ast.unparse(node)
            if any(s in body for s in _SHELLS):
                shells.add(node.name)

    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        runs = (
            (isinstance(fn, ast.Attribute) and fn.attr == 'join'
             and isinstance(fn.value, ast.Attribute) and fn.value.attr == 'path')
            or (isinstance(fn, ast.Name) and fn.id in shells)
            or (isinstance(fn, ast.Attribute) and fn.attr in shells))
        if not runs:
            continue
        for a in list(node.args) + [k.value for k in node.keywords]:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                out.add(a.value)
    return out


def suite_refs(tools):
    r"""Tools a file under tests/ actually INVOKES or IMPORTS -- not merely names.

    The first version accepted any mention, and that over-classified in the
    OPTIMISTIC direction, which is the one this document must never fail in:
    SUITE-ONLY reads as "this runs", UNWIRED reads as "nothing runs it". Measured
    before tightening -- three tools moved, all three LIVE and all three named
    only inside a LIST of tools in tests/sairn_http_challenge.py:
    licence_recoverability_check.py, load_deadline_seed.py, sairn_app_map_check.py.
    Their verdict is unchanged (unwired is correct for a LIVE tool) but the COUNT
    was wrong, and the count is what this file exists to state.

    COMMENTS ARE STRIPPED FIRST, added 2026-09-13, same direction and same
    reason. `tools/checker_control_check.py` asks every control to declare
    itself, and the standard declaration carries a comment naming the tool:

        # Declares, for tools/checker_control_check.py, which checker(s) this
        # file is the control for.

    The `'tools/' + t in txt` rule read that as an invocation, so all
    twenty-five declaring controls became "files that run the meta-checker" --
    and the two it printed as that tool's probes were the two that sort first
    alphabetically, neither of which is its probe. A comment naming a tool is a
    MENTION. Only code invokes.
    """
    refs = {}
    for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if not f.endswith(('.py', '.js')):
                continue
            try:
                txt = io.open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
            except IOError:
                continue
            txt = _prose_removed(f, txt)
            call_args = _call_arg_names(txt) if f.endswith('.py') else set()
            # A DECLARATION BEATS EVERY HEURISTIC HERE, and one already exists.
            # tools/checker_control_check.py made a control state which checkers
            # it is the control for, in code, precisely because inferring it
            # failed three different ways. `orphan_register_check.py` is driven
            # through a generated shim -- its name appears only inside a string
            # that BECOMES source -- so no amount of reading this file's calls
            # can see it, while `CONTROLS_FOR` says it outright. Reading the
            # declaration also stops this document and that one disagreeing
            # about the same fact, which is the drift both exist to prevent.
            for _decl in _DECL_RE.findall(txt):
                call_args |= set(_DECL_NAME_RE.findall(_decl))
            for t in tools:
                # THE PRE-FILTER IS ON THE STEM, NOT THE FILENAME. `import
                # checker_control_check as M` never writes the `.py`, so a
                # filename pre-filter dropped the file before the import
                # pattern below could look -- and the tool came back UNWIRED
                # while its own probe imported it. It passed only because the
                # DOCSTRING happened to spell out `tools/<name>.py`, which is
                # the prose this function now removes.
                if t.rsplit('.', 1)[0] not in txt:
                    continue
                stem = re.escape(t.rsplit('.', 1)[0])
                esc = re.escape(t)
                invoked = (
                    ('tools/' + t) in txt
                    or re.search(r"'tools'\s*,\s*'" + esc + r"'", txt)
                    or re.search(r'(?:^|' + chr(10) + r')\s*import\s+' + stem + (chr(92) + 'b'), txt)
                    or re.search(r'spec_from_file_location\([^)]*' + esc, txt)
                    or re.search(r"require\(['\"][^'\"]*" + stem, txt)
                    or t in call_args)
                if invoked:
                    refs.setdefault(t, set()).add(f)
    return {k: sorted(v) for k, v in refs.items()}


def classify():
    tools = tool_files()
    hk = hooked()
    gi = set(gate_invokes())
    reg = dict((t, (p, c)) for t, p, c in registry())
    suite = suite_refs(tools)

    nop = not_promoted()

    cls = {}
    for t in tools:
        evs = hk.get(t, [])
        if 'PreToolUse' in evs or t in gi:
            cls[t] = 'BLOCKING'
        elif t in reg or 'PostToolUse' in evs:
            cls[t] = 'REPORT-ONLY'
        elif evs:
            cls[t] = 'ADVISORY'
        elif t in nop:
            # A RECORDED DECISION IS NOT A GAP. Checked before SUITE-ONLY and
            # UNWIRED on purpose: several of these also have a probe, and
            # reporting one as "the suite runs it on fixtures" buries the fact
            # that somebody already decided not to wire it, and why.
            cls[t] = 'DECIDED'
        elif t in suite:
            cls[t] = 'SUITE-ONLY'
        else:
            cls[t] = 'UNWIRED'
    return tools, cls, hk, gi, reg, suite


def purpose(t, reg):
    if t in reg:
        return 'CHECKER', reg[t][1]
    return PURPOSES[t]


def missing_purposes(tools, reg):
    absent = [t for t in tools if t not in reg and t not in PURPOSES]
    extra = [t for t in PURPOSES if t not in tools]
    return absent, extra


def build():
    tools, cls, hk, gi, reg, suite = classify()

    # ── THE TRAVERSE MUST CLOSE BEFORE ANYTHING IS WRITTEN ──────────────────
    # `--check` compares this document to what this generator produces TODAY --
    # both ends from the same instrument. It cannot see a source that has gone
    # silent. On 2026-09-13 the pre-filter in suite_refs() tested a FILENAME
    # while `import x as M` never writes the `.py`, and five promoted checkers
    # with thorough controls briefly reported NO PROBE. `--check` was byte-clean
    # throughout. The diff caught it; the check never could have.
    tv = closing_error.Traverse(DOC)
    tv.leg('tools on disk', len(tools), 'git ls-files tools/')
    tv.leg('hook entries', len(hk), SETTINGS)
    tv.leg('push-gate invocations', len(gi), GATE)
    tv.leg('report-only registry', len(reg), 'report_only_checks.REGISTRY')
    tv.leg('tools invoked by tests/', len(suite), 'tests/**/*.py, *.js')
    tv.leg('recorded NOT-promoted decisions', len(not_promoted()),
           'report_only_checks.NOT_PROMOTED')
    tv.leg('numbered gate checks', len(dict(gate_checks())), GATE)
    try:
        traverse_rows = tv.close()
    except closing_error.EmptyLeg as e:
        return None, 'REFUSING to generate -- the traverse did not close: %s' % e

    absent, extra = missing_purposes(tools, reg)
    # ── THE THIRD DRIFT DIRECTION, WHICH WENT UNREFUSED FOR FOUR INSTANCES ──
    # This block already refused a tool with NO description and a description
    # for NO tool. It did not refuse a tool described TWICE -- once in REGISTRY
    # (which carries `catches`) and once in PURPOSES -- which is two sources
    # that can disagree: the claim-in-two-places failure this whole document
    # exists to prevent, inside the generator meant to prevent it.
    #
    # It was not harmless, and it was not caught here. It surfaced as a RED
    # TEST instead: tests/run_tooling_inventory_probe.py failing on "no
    # REGISTRY tool is also described in PURPOSES", which is a long way from
    # the line that caused it.
    #
    # FOUR INSTANCES, and the fourth is why this is a refusal rather than four
    # deletions. completeness_check.py, secrets_inventory.py and
    # dependency_graph.py were all half-registered -- REGISTRY entry added,
    # PURPOSES entry left behind, never measured for flakiness either. Those
    # three were cleaned up on 2026-09-14; eaten_substitution_check.py arrived
    # with the SAME defect in the next rebase, from a different session, within
    # the hour. A mistake two sessions make independently is a missing guard,
    # not carelessness -- so the generator now stops the next one at the line
    # that causes it.
    # `reg` here is a DICT keyed by tool name (line 568), not the 3-tuple list
    # registry() returns. Got that wrong once and it raised rather than
    # reporting -- which is the right direction for a mistake in a refusal, but
    # worth the comment so the next reader does not repeat it.
    dup = sorted(t for t in reg if t in PURPOSES)
    if absent or extra or dup:
        lines = ['REFUSING to generate -- the hand-written half has drifted.', '']
        if absent:
            lines += ['%d tool(s) in tools/ with no PURPOSES entry. A blank cell in this'
                      % len(absent),
                      'document is exactly how the last one went stale, so this is an error:']
            lines += ['    ' + t for t in absent]
        if extra:
            lines += ['', '%d PURPOSES entr(y/ies) naming a tool that no longer exists:' % len(extra)]
            lines += ['    ' + t for t in extra]
        if dup:
            lines += ['',
                      '%d tool(s) described in BOTH REGISTRY and PURPOSES:' % len(dup)]
            lines += ['    ' + t for t in dup]
            lines += ['',
                      'A report-only tool\'s `catches` comes from REGISTRY, which already carries',
                      'it. A second description in PURPOSES is a second source that can disagree --',
                      'the claim-in-two-places failure this document exists to prevent. DELETE THE',
                      'PURPOSES LINE; do not reword it to match. This is usually a half-finished',
                      'promotion, so check the same tool has ledger evidence too:',
                      '    python tools/flaky_checker_quarantine.py']
        return None, '\n'.join(lines)

    order = ['BLOCKING', 'REPORT-ONLY', 'ADVISORY', 'DECIDED', 'SUITE-ONLY', 'UNWIRED']
    counts = dict((k, sum(1 for t in tools if cls[t] == k)) for k in order)
    kinds = {}
    for t in tools:
        kinds.setdefault(purpose(t, reg)[0], []).append(t)

    W = []
    A = W.append
    A('# The tooling inventory -- what exists, what it catches, what actually runs')
    A('')
    A('**GENERATED by `python tools/tooling_inventory.py`. Do not hand-edit.**')
    A('Run `--check` to find out whether it still matches the repo; a mismatch is a')
    A('finding, not a document somebody forgot.')
    A('')
    A('Every classification below is derived from `.claude/settings.json`,')
    A('`tools/sairn_push_gate_hook.py`, `tools/report_only_checks.py`\'s own REGISTRY,')
    A('`tests/`, and `git ls-files tools/` -- never from a prior inventory.')
    A('')
    A('**Why it is generated.** `docs/2026-09-09-tooling-inventory.md` was')
    A('hand-derived, correct on the day, and **stale within three days**: it said 77')
    A('tools, 3 report-only and 28 unwired checkers. Nine checkers were promoted and')
    A('twelve more built in the three days after. Nothing about the document knew,')
    A('and a tool that does not run produces no output to contradict it -- which')
    A('makes this the one inventory whose staleness is hardest to notice.')
    A('')
    A('---')
    A('')
    A('## The headline')
    A('')
    A('**%d files in `tools/`.** By what actually invokes them:' % len(tools))
    A('')
    A('| Status | Count | Meaning |')
    A('|---|---:|---|')
    MEAN = {
        'BLOCKING': 'reachable from something that can refuse a push or a tool call',
        'REPORT-ONLY': 'runs automatically on every push, never blocks',
        'ADVISORY': 'session-start or prompt hooks, informational',
        'SUITE-ONLY': 'run by `tests/`, so proved to WORK -- on fixtures. Never pointed at the codebase',
        'DECIDED': 'deliberately NOT promoted, with a reason recorded in report_only_checks.py',
        'UNWIRED': 'nothing runs these at all',
    }
    for k in order:
        A('| **%s** | %d | %s |' % (k, counts[k], MEAN[k]))
    A('')
    A('By what they are, independent of wiring:')
    A('')
    A('| Kind | Count |')
    A('|---|---:|')
    for k in sorted(kinds):
        A('| %s | %d |' % (k, len(kinds[k])))
    A('')
    unwired_checkers = [t for t in tools if cls[t] == 'UNWIRED'
                        and purpose(t, reg)[0] == 'CHECKER']
    suite_checkers = [t for t in tools if cls[t] == 'SUITE-ONLY'
                      and purpose(t, reg)[0] == 'CHECKER']
    live_unwired = [t for t in tools if cls[t] in ('UNWIRED', 'SUITE-ONLY')
                    and purpose(t, reg)[0] == 'LIVE']
    A('**%d tool(s) are DECIDED -- deliberately not promoted, with the reason'
      % counts['DECIDED'])
    A('recorded in `report_only_checks.py`.** They are listed below with those')
    A('reasons and are NOT counted as gaps. The first version of this document did')
    A('not read that list and reported six of them as unaddressed.')
    A('')
    _act = len(unwired_checkers) + len(suite_checkers)
    if _act == 0:
        # THE ZERO CASE GETS ITS OWN WORDING. A document that reads as broken at
        # zero -- "The 0, by name" under a sentence about which group is worse --
        # is one people stop trusting at exactly the moment it has good news.
        A('**The number to act on: ZERO.** Every checker that answers a question')
        A('about this codebase is now either promoted to report-only or carries a')
        A('recorded reason for not being. That was 13 on 2026-09-12 before the')
        A('pass that closed it: four were promoted (`checkblocks.py`,')
        A('`comment_sensitivity_check.py`, `criticality_tier_check.py`,')
        A('`soup_register_check.py`), three were recorded as deliberate, and six')
        A('had already been decided in a list this document was not reading.')
        A('')
        A('**That is not the same as being covered.** It means nothing is')
        A('unexamined. A promoted checker reports; it does not block, and several')
        A('of the DECIDED entries are decisions to look later.')
        A('')
    else:
        A('**The number to act on: %d checker(s) that answer a question about this'
          % _act)
        A('codebase and are pointed at it by nobody** -- %d wired nowhere at all, and %d'
          % (len(unwired_checkers), len(suite_checkers)))
        A('that the suite runs against FIXTURES only. The second group is the worse one:')
        A('a green probe on an unpointed checker is the most convincing possible form of')
        A('"we are covered", and it is coverage of the tool rather than of the code.')
        A('')
    if _act:
        A('The %d, by name, so this is actionable rather than a statistic:' % _act)
        A('')
        A('| Tool | Status | What it catches |')
        A('|---|---|---|')
        for t in sorted(unwired_checkers + suite_checkers):
            A('| `%s` | %s | %s |' % (t, cls[t], purpose(t, reg)[1]))
        A('')
    A('**Separately, %d tool(s) make a LIVE network or database request.** Those are' % len(live_unwired))
    A('correctly manual: wiring one into a hook would make every push talk to the')
    A('outside world. Unwired is the right state for them and is not a finding.')
    A('')
    A('---')
    A('')
    A('## BLOCKING (%d)' % counts['BLOCKING'])
    A('')
    A('Two entry points, and they are not the same one. `.claude/settings.json`')
    A('PreToolUse fires on a Claude Code **tool call**; `.githooks/pre-push` fires on')
    A('the **git operation**, so a push from a Python subprocess cannot spell its way')
    A('around it. The second exists because the first missed exactly that on')
    A('2026-09-01. Per clone, once: `python tools/install_git_hooks.py`.')
    A('')
    A('| Tool | Kind | What it catches |')
    A('|---|---|---|')
    for t in sorted(t for t in tools if cls[t] == 'BLOCKING'):
        k, c = purpose(t, reg)
        A('| `%s` | %s | %s |' % (t, k, c))
    A('')
    A('### The push gate\'s own numbered checks')
    A('')
    A('Derived from the `CHECK n:` blocks in `tools/sairn_push_gate_hook.py`, which is')
    A('the only source that moves when one is added.')
    A('')
    A('| # | Check |')
    A('|---:|---|')
    for n, title in gate_checks():
        A('| %d | %s |' % (n, title))
    A('')
    A('---')
    A('')
    A('## REPORT-ONLY (%d)' % counts['REPORT-ONLY'])
    A('')
    A('Run by `tools/report_only_checks.py` as a PostToolUse hook on every push.')
    A('`catches` is read out of that file\'s own REGISTRY, so it cannot disagree with')
    A('what runs. They are on a promotion path: blocking only once each has been')
    A('quiet in practice.')
    A('')
    A('| Tool | Promoted | What it catches |')
    A('|---|---|---|')
    for t, p, c in sorted(registry()):
        A('| `%s` | %s | %s |' % (t, p, c))
    A('')
    # THE COUNT ABOVE IS NOT THE LENGTH OF THAT TABLE, and saying so beats letting
    # a reader add it up and find 26 under a heading that says 29. Three tools are
    # PostToolUse hooks in their own right rather than registry entries.
    _ro_hooks = sorted(t for t in tools if cls[t] == 'REPORT-ONLY' and t not in reg)
    A('And %d that are PostToolUse hooks in their own right, not registry entries:'
      % len(_ro_hooks))
    A('')
    A('| Tool | Kind | What it catches |')
    A('|---|---|---|')
    for t in _ro_hooks:
        k, c = purpose(t, reg)
        A('| `%s` | %s | %s |' % (t, k, c))
    A('')
    A('---')
    A('')
    A('## DECIDED -- not promoted, on purpose (%d)' % counts['DECIDED'])
    A('')
    A('**These are not gaps.** Each carries a recorded reason in')
    A("`tools/report_only_checks.py`'s `NOT_PROMOTED` list -- a read-list whose own")
    A('output refuses to be quoted bare, a tool needing a browser snapshot, one with')
    A('an open owned finding, a live network probe. The first version of this')
    A('document did not read that list and counted six of them as unaddressed, which')
    A('is how a reader stops believing the number.')
    A('')
    A('| Tool | Kind | Why not promoted |')
    A('|---|---|---|')
    _nop = not_promoted()
    for t in sorted(t for t in tools if cls[t] == 'DECIDED'):
        kind = purpose(t, reg)[0]
        A('| `%s` | %s | %s |' % (t, kind, _nop.get(t, '?')))
    A('')
    A('---')
    A('')
    for k in ('ADVISORY', 'SUITE-ONLY', 'UNWIRED'):
        A('## %s (%d)' % (k, counts[k]))
        A('')
        if k == 'SUITE-ONLY':
            A('`tests/` names these, so they are executed on every push -- against')
            A('fixtures. Nothing points them at the real codebase.')
            A('')
        if k == 'UNWIRED':
            A('Nothing runs these. Read the Kind column before calling any of it a')
            A('finding: a LIBRARY is imported by something else and a LIVE tool is')
            A('correctly manual. Only `CHECKER` rows here are a gap.')
            A('')
        A('| Tool | Kind | What it catches | Probe under tests/ |')
        A('|---|---|---|---|')
        for t in sorted(t for t in tools if cls[t] == k):
            kind, c = purpose(t, reg)
            pr = ', '.join('`%s`' % f for f in suite.get(t, [])[:2]) or '&mdash;'
            A('| `%s` | %s | %s | %s |' % (t, kind, c, pr))
        A('')
        A('---')
        A('')
    A('## How to re-derive this')
    A('')
    A('    python tools/tooling_inventory.py --check   # does the doc still match?')
    A('    python tools/tooling_inventory.py           # rewrite it')
    A('')
    A('The generator refuses to run if a tool in `tools/` has no entry in its')
    A('`PURPOSES` map, and refuses if `PURPOSES` names a tool that is gone. A blank')
    A('cell is how the last inventory went stale, so both directions are errors')
    A('rather than omissions.')
    A('')
    A('**What this cannot tell you**, said here rather than found out: `BLOCKING`')
    A('means a tool is reachable from something that can refuse. It does not mean')
    A('every one of its findings blocks -- the push gate carries report-only checks')
    A('INSIDE it, and checks 5 and 7 were promoted out of exactly that state.')
    A('')
    A('### Closing error -- what this document was derived FROM')
    A('')
    A('`--check` compares this file to what the generator produces today. Both')
    A('ends of that comparison come from the same instrument, so it proves nobody')
    A('hand-edited the file and proves nothing about whether the generator still')
    A('reads what it used to. These are the sources it read on the run that wrote')
    A('this, one row each. **Any of them reaching zero is a refusal, not a')
    A('thinner document** -- a broken reader and an empty repo produce the same')
    A('number, and only one of them is a document.')
    A('')
    A('```')
    for row in traverse_rows:
        A(row.rstrip())
    A('```')
    A('')
    A('A closed traverse is **not** a correct survey: it means no source is')
    A('MISSING, not that any source is RIGHT. On 2026-09-13 the probe column here')
    A('named the wrong test file for 27 tools, and that was a non-zero count the')
    A('whole time. Each source needs its own control; this is the floor.')
    return '\n'.join(W) + '\n', None


# ── DRIFT MARGIN, added 2026-09-13 ──────────────────────────────────────────
# The cadence question for this document, answered with its own history rather
# than a chosen number. Measured over its 16 regenerations:
#
#     hours between regenerations   min 0.0   median 0.5   max 20.3
#     source commits in between     min 0     median 2     max 5
#
# SO THE INTERESTING ANSWER IS THAT A SCHEDULE WOULD ADD LITTLE. `--check` is
# already in the report-only registry and runs on every push, and the worst
# staleness this document has ever reached is FIVE source commits. A cron that
# re-derived it hourly would mostly re-derive an already-current file.
#
# What was missing is CONVENTION 4: an alarm tighter than the failure point.
# `--check` only speaks once the document is already wrong. This reports the
# margin -- how many source commits have landed since it was last regenerated
# -- so the drift is visible BEFORE it becomes a finding. The band comes from
# the measurement above: warn at 3, which is inside the observed maximum of 5
# and outside the median of 2, so it fires on unusual drift and not on normal
# work.
DRIFT_WARN_COMMITS = 3
DRIFT_OBSERVED_MAX = 5


def _commits_since(path_spec, since_epoch):
    r = subprocess.run(['git', 'log', '--format=%ct', '--', path_spec],
                       cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return len([t for t in r.stdout.split()
                if t.strip() and int(t) > since_epoch])


def drift():
    """How far behind its sources is the committed document, right now?"""
    r = subprocess.run(['git', 'log', '-1', '--format=%ct', '--', DOC],
                       cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if not r.stdout.strip():
        print('DRIFT: %s has no commit history here -- nothing to measure '
              'against. That is not a clean answer.' % DOC)
        return 2
    last = int(r.stdout.strip())
    behind = _commits_since('tools/', last) + _commits_since(SETTINGS, last)
    print('DRIFT MARGIN -- %s' % DOC)
    print('  source commits since it was last regenerated : %d' % behind)
    print('  warn at                                      : %d' % DRIFT_WARN_COMMITS)
    print('  worst ever observed, over 16 regenerations   : %d' % DRIFT_OBSERVED_MAX)
    print('')
    if behind >= DRIFT_WARN_COMMITS:
        print('%d source commit(s) have landed since this document was last'
              % behind)
        print('regenerated. It may still MATCH -- run --check for that. This is')
        print('the margin, not the violation: the alarm is set tighter than the')
        print('failure point on purpose, because a check that only speaks once')
        print('the document is wrong has already shipped the wrong document.')
        print('    python tools/tooling_inventory.py')
        return 1
    print('within the band. Regenerating is cheap and this document has never')
    print('been more than %d source commits behind; the report-only --check on'
          % DRIFT_OBSERVED_MAX)
    print('every push is what has kept it there, not a schedule.')
    return 0


def main(argv):
    if '--drift' in argv:
        return drift()
    doc, err = build()
    if err:
        print(err)
        return 2
    path = os.path.join(REPO, DOC)
    if '--check' in argv:
        try:
            cur = io.open(path, encoding='utf-8').read()
        except IOError:
            print('FAIL: %s does not exist. Run the generator.' % DOC)
            return 1
        if cur == doc:
            print('OK: %s matches the repo.' % DOC)
            return 0
        print('FAIL: %s no longer matches the repo -- a tool was added, promoted, '
              'wired or removed and the document was not regenerated. That is a '
              'finding, not a document somebody forgot.\n    python tools/tooling_inventory.py' % DOC)
        return 1
    io.open(path, 'w', encoding='utf-8', newline='').write(doc)
    print('wrote %s (%d lines)' % (DOC, doc.count('\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
