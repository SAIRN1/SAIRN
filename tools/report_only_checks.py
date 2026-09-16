"""Run the checkers that have been PROMOTED to report-only, and say what they find.

    python tools/report_only_checks.py            # full sweep, by hand
    python tools/report_only_checks.py --hook     # PostToolUse, reads a payload

── WHY THIS EXISTS ──────────────────────────────────────────────────────────
`docs/2026-09-09-tooling-inventory.md` found 28 working checkers in `tools/`
that nothing runs. Several were written in response to a real production
incident, proved on that incident, committed, and have not looked at the
codebase since. Three of them are named as REQUIRED by `sairn-guardian-v2` or
`CLAUDE.md` and were still unwired.

Wiring each one as its own hook entry would be 28 hook entries, 28 places to
keep in step, and 28 chances to repeat the `"if": "Bash(git push*)"` mistake.
This is ONE runner with a REGISTRY, so promoting the next checker is a registry
entry rather than a new hook -- the same argument
`tests/suite_control_backfill_probe.py` makes for one table instead of five
harnesses.

── REPORT-ONLY, AND WHY THAT IS NOT TIMIDITY (Michael's decision, 2026-09-09)
None of these had ever run against real code, so their real-world
false-positive rate was genuinely unknown. The first run proved that was the
right worry: `nav_panel_check.py` reported ALL 26 of SAIRNfreedom's panels
unreachable, because it scans `<button>` and that app navigates with
`<div class="nitem" onclick="sfNav('x')">`. Wired blocking, it would have
refused every SAIRNfreedom push while the app was fine. It is NOT in the
registry below until that is fixed.

So: same promotion path as push-gate checks 5 and 7 and `run_all_tests.py`
itself -- report-only until quiet in practice, then promoted individually.
**THE HOOK EXITS 0 ALWAYS.** The only thing it can do is say something.

Run by hand it exits 1 on findings, so a person can chain it. That asymmetry is
deliberate and is the whole difference between a report and a gate.

── SILENT ON A CLEAN RUN ────────────────────────────────────────────────────
A notice that fires on every push is a notice nobody reads. But a checker that
COULD NOT RUN does notify, because "could not run" being invisible is the
failure `run_all_tests.py` was built to end.

── NO LOCK, DELIBERATELY, AND THE DIFFERENCE MATTERS ────────────────────────
`run_all_tests.py` takes a per-clone lock because the probes it runs MUTATE
tracked files, and two runs corrupt each other's restores (2026-09-09). Every
checker here is READ-ONLY. Concurrent runs waste a little CPU and cannot
corrupt anything, and adding a lock would be machinery bought for a risk that
does not exist. If a MUTATING tool is ever added to this registry, that
reasoning stops holding -- take the lock then, and say so here.
"""
import json
import os
import re
import subprocess
import time
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
# THE PUSH GATE IS IMPORTED, NOT COPIED. `tools/sairn_claim_hook.py` once
# carried its own copy of a line that had already been fixed in
# `tools/sairn_claim.py`, so the fix reached the tool a human invokes and
# missed the one that runs unattended. One definition, one place to fix.
from run_all_tests import pushes                                  # noqa: E402


def app_files(verbose=False):
    """Every LIVE app HTML file, derived from git rather than a hand list.

    TOP LEVEL ONLY, and that is a rule rather than a convenience: `vercel.json`
    routes every app from a file in the repo root, so a `.html` in a
    subdirectory is by definition not served.

    FOUND BY WIRING IT, 2026-09-09: the first version was a bare
    `git ls-files '*.html'` and it swept
    `archive/branch-lucid-ptolemy-b73vu0/`, the preserved ancestor branch --
    twelve dead 2026-06 snapshots that CLAUDE.md says explicitly are kept for
    provenance and must not be run or recreated. It reported 13 findings, 12 of
    them in code nobody deploys, which is exactly how a report-only checker
    earns the reputation that gets it switched off before it is ever promoted.

    The exclusion is PRINTED rather than silent -- a category quietly dropped
    is how a real file hides, the same argument `run_all_tests.py` makes for
    its UNRUN section. SCOPED HONESTLY, 2026-09-10: printed on the HAND run
    only. `hook_main()` calls `sweep(quiet=True)`, so `verbose` is False there
    and the notice does not appear -- it cannot, because that path's stdout is
    a single JSON payload and a stray line would corrupt it. That is accepted
    rather than fixed, and the reason is that the exclusion is CORRECT in both
    copies: `vercel.json` serves root files only, so an app moved into a
    subdirectory is genuinely not deployed and genuinely should not be scanned.
    The zero-target guard in run_one() is what covers the case that is NOT
    benign.

    GIT FAILING IS NOT AN EMPTY REPO -- added 2026-09-10 by the tools/ half of
    the self-referential-guard sweep. The returncode was never read, so any
    failure of `git ls-files` -- git absent from the hook's PATH, an index
    locked by one of the four clones mid-rebase, a corrupt index -- produced an
    empty stdout, an empty app list, and six promoted checkers reporting
    exactly what they report after scanning all 22 apps and finding nothing.
    Raising is deliberate: run_one() turns it into an `unrun` line, which is
    the "could not run is not a pass" code the rest of this platform uses.
    """
    r = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError(
            'git ls-files failed (exit %d): %s -- the app list could not be '
            'derived, so NOTHING was scanned. This is not a clean sweep.'
            % (r.returncode, (r.stderr or '').strip()[:200]))
    every = sorted(f for f in r.stdout.split('\n') if f.strip())
    live = [f for f in every if '/' not in f]
    if verbose and len(every) != len(live):
        print('   (not scanned: %d non-root .html file(s) -- not routed by '
              'vercel.json, e.g. %s)'
              % (len(every) - len(live),
                 ', '.join(f for f in every if '/' in f)[:70]))
    return live


def by_exit(rc, out):
    """A checker that exits non-zero on a finding. Returns (findings, detail)."""
    return ([l for l in out.splitlines() if l.startswith('  - ') or
             l.startswith('FAIL')] or ['exit %d' % rc], out) if rc else ([], out)


# Sections of sairn_dead_button_audit.py that are DEFECTS, per the tool's own
# labelling. C1/C2 are OPPOSITE fixes and the tool says in its own output that
# they need a human read; D2 it labels "informational, count only".
#
# THIS IS A DELIBERATE NARROWING AND IT IS STATED RATHER THAN QUIET, because a
# silent category exclusion is exactly how a real finding hides -- the argument
# `run_all_tests.py` makes for its own UNRUN section. What it hides: on
# 2026-09-09 the full sweep found C1=1 on stonedesk.html (`notify()`, a
# showToast alias with 111 callers -- a false positive of that heuristic),
# C1=2 on sairnmechanical.html, and D2 on six apps. Run the tool directly to
# see them; `--all-sections` below prints them here.
DEFECT_SECTIONS = ('A.', 'B.', 'C2.', 'D1.')
COUNT_RE = re.compile(r'^([A-E]\d?)\..*?->\s*(\d+)\s*$')


def by_section(rc, out):
    """sairn_dead_button_audit.py ALWAYS exits 0 -- parse its sections.

    That is worth naming: a checker that cannot fail by exit code cannot be
    wired by exit code, which is a fair part of why this one sat unwired while
    being named as required by Guardian check 27.
    """
    findings, info = [], []
    for line in out.splitlines():
        m = COUNT_RE.match(line.strip())
        if not m or m.group(2) == '0':
            continue
        (findings if (m.group(1) + '.') in DEFECT_SECTIONS else info).append(
            line.strip())
    return findings, out


REGISTRY = [
    {
        'tool': 'subprocess_decode_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-15, report-only on its first day. The correct '
                    'number IS zero -- unlike every read-list in this registry '
                    'it is a gate, not a score -- but it is registered rather '
                    'than made blocking on day one, on the same staging this '
                    'file uses everywhere: a week of pushes says whether it is '
                    'quiet, and a check nobody has watched be quiet should not '
                    'be able to refuse a push',
        'catches': 'a text-mode subprocess call with no explicit encoding=, '
                   'which decodes the child output with the LOCALE default '
                   '(cp1252 on this platform) rather than UTF-8',
        'why_it_matters': 'it fails in two ways and the quiet one is worse. '
                          'MOJIBAKE: the call succeeds and returns text that is '
                          'not what the child wrote, so a scanner looking for a '
                          'box-drawing character or an arrow silently stops '
                          'matching and reports clean. HARD FAIL: cp1252 has no '
                          'mapping for 0x81/0x8D/0x8F/0x90/0x9D, four tracked '
                          'files contain one, and the reader THREAD raises -- '
                          'MEASURED 2026-09-15, a git show of one of those '
                          'files returned 0 characters through a bare call and '
                          '76891 through an explicit one. Observed first in '
                          'tier_a_review_gate.py, where the consequence was '
                          'worse than a crash: the push gate maps that tool exit '
                          '1 to a specific Tier A accusation, and an uncaught '
                          'exception also exits 1, so a crash became a credible '
                          'FALSE FINDING about a push that touched no Tier A '
                          'resource. 358 sites in 137 files were fixed in one '
                          'sweep; this keeps the number at zero',
    },
    {
        'tool': 'completeness_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-14, report-only on its first day and deliberately '
                    'not wired into the push gate: it cannot read intent, only '
                    'sites, and a shape that cannot tell a deliberate '
                    'one-direction rule from a forgotten one has no business '
                    'refusing a push',
        'catches': 'a rule declared and consulted NOWHERE in its own file; a '
                   'rule consulted on a read path and on no write path; and a '
                   'dispatch chain over a declared domain with a member '
                   'reaching no arm and no terminal else',
        'why_it_matters': 'item 90 makes a class of bug impossible to WRITE, '
                          'and cannot reach legacy code that never had a '
                          'boundary. The SITES a rule must be applied at are '
                          'not a type -- they are a list somebody has to '
                          'remember, and forgetting one is silent',
        'evidence': 'real run 2026-09-14: S1 found api/sen-portal.js '
                    'MANAGEMENT_ROLES, declared and never consulted, sitting '
                    'beside a branch whose refusal says "ask management" while '
                    'enforcing the WIDER BROAD_ROLES. S3 reports a measured '
                    'zero over 147 files after four narrowings, each one paid '
                    'for by a real false positive and kept as a fixture',
    },
    {
        'tool': 'secrets_inventory.py',
        'mode': 'once',
        'verdict': by_exit,
        'args': ['--check'],
        'promoted': '2026-09-14, and --check rather than the bare report: the '
                    'bare run prints a ranking and exits 0 whatever it finds, '
                    'which in a runner that is silent on a clean run means it '
                    'would never say anything at all',
        'catches': 'docs/SECRETS-INVENTORY.md drifting from the code -- a new '
                   'environment variable, a removed one, or a guard that moved',
        'why_it_matters': 'an unset credential that fails CLOSED is an outage '
                          'and one that fails OPEN is a security incident, and '
                          'they look identical in a list of names. The document '
                          'is the only place that distinction is written down',
        'evidence': 'real run 2026-09-14: 47 variables, 18 CREDENTIAL, and no '
                    'CREDENTIAL left with NO GUARD FOUND. Held by '
                    'tests/run_secrets_inventory_probe.py -- arm 3e fails the '
                    'moment a credential loses its guard, and three mutation '
                    'controls take the suite red',
    },
    {
        'tool': 'dependency_graph.py',
        'mode': 'once',
        'verdict': by_exit,
        # --register, NOT the bare report. The bare run PRINTS a ranking and
        # exits 0 whatever it finds, which in a report-only runner that is
        # silent on a clean run means it would never say anything at all.
        'args': ['--register'],
        'promoted': '2026-09-14, registered REPORT-ONLY on its first day and '
                    'deliberately not wired into the push gate -- its threshold '
                    'is a policy and a policy has no business refusing a push '
                    'until somebody has watched it for a while',
        'catches': 'a component at or above SPOF_THRESHOLD with no row in '
                   'docs/SPOF-REGISTER.md, a row marked OPEN that is no longer '
                   'a chokepoint, and -- the sharp one -- a row marked RETIRED '
                   'while the component is still above the bar',
        'why_it_matters': 'a single-point-of-failure list generated once and '
                          'filed is a document, and a document nobody '
                          're-measures is a claim with a date on it. The '
                          'retirement check is what stops the register becoming '
                          'a reassuring lie',
        'evidence': 'real run 2026-09-14: 10 components at or above the '
                    'threshold, 10 rows, 7 OPEN / 3 ACCEPTED / 0 RETIRED, PASS. '
                    'Held in both directions by tests/run_dependency_graph_probe.py '
                    '(7d refuses an empty register, 7e is the control that the '
                    'same rows marked OPEN pass, 7f refuses a false retirement)',
    },
    {
        'tool': 'vercel_config_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-09',
        'catches': "a buildCommand over Vercel's 256-char schema limit, and a "
                   "route whose destination file no cp copies",
        'why_it_matters': "a failed production deploy KEEPS SERVING the last "
                          "good build, so every later push reports clean while "
                          "production stays on old code -- that really happened "
                          "on 2026-07-30 and is why Guardian names this check",
        'evidence': 'real run 2026-09-09: buildCommand 92/256, PASS',
    },
    {
        'tool': 'sairn_dead_button_audit.py',
        'mode': 'apps',
        'verdict': by_section,
        'promoted': '2026-09-09',
        'catches': 'a handler target never defined (A), an inline handler whose '
                   'only action is a toast (B), a toast-only function with zero '
                   'callers (C2), and a same-scope duplicate definition (D1)',
        'why_it_matters': 'Guardian check 27 says run it against every app file '
                          'before declaring it done, and nothing ever did',
        'evidence': 'real run 2026-09-09 over all 22 app files: A=0 B=0 C2=0 '
                    'across every app, D1=1 on sairnmechanical.html (two '
                    'mechEsc definitions in one script block)',
    },
    {
        'tool': 'nav_panel_check.py',
        'mode': 'apps',
        'verdict': by_exit,
        'promoted': '2026-09-09, AFTER its matcher was fixed -- NOT as it stood',
        'catches': 'a panel no nav control reaches (Guardian checks 16-18), and '
                   'a duplicate id in static markup',
        'why_it_matters': "the safe-editing rules say run it after EVERY edit, "
                          "and nothing ever did",
        'evidence': 'its FIRST real run reported ALL 26 sairnfreedom panels '
                    'unreachable -- it scanned <button> and that app navigates '
                    'with <div class="nitem" onclick="sfNav(...)">. The element '
                    'is now derived like the class, the id and the function name '
                    'already were; re-run over all 22 apps: 22 PASS, 0 FAIL. '
                    'Held in BOTH directions by tests/run_report_only_checks_probe.py',
    },
    {
        'tool': 'cleanup_confirm_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10, written the same day for a rule that existed '
                    'since 2026-08-26 with no mechanism behind it',
        'catches': 'a cleanup or migration file whose destructive statements '
                   'carry no confirm query and no expected answer -- so nobody '
                   'can ever establish what it did',
        'why_it_matters': 'the Supabase editor returns SUCCESS for the '
                          'statements it DID run, so a multi-statement paste '
                          'that stops halfway is indistinguishable from a '
                          'complete one. Two real cases on 2026-08-26',
        'evidence': 'first real run flagged 4 of 26 files; hand-reading every '
                    'one showed 2 real (sairndesign/sairnlegacy synctest, both '
                    'since given confirm blocks) and 2 false positives that '
                    'became fixtures -- a commented "not this run\'s debris" '
                    'delete, and a menu-only file. 26 files, 0 gaps now. Held '
                    'in both directions by tests/run_cleanup_confirm_probe.py',
    },
    # ── SECOND BATCH, 2026-09-10 ────────────────────────────────────────────
    # Same rule as the first: each one RUN against real code, every finding
    # hand-read, and anything the run exposed fixed before promotion rather
    # than promoted broken.
    {
        'tool': 'md_table_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'a markdown row whose prose pipes broke its own columns, so '
                   'trailing cells fall off and an edit-by-index writes into '
                   'the wrong one',
        'why_it_matters': 'docs/SAIRN-OPEN-WORK-INDEX.md is the file every '
                          'session reads to choose work; a status landing where '
                          'an owner belongs is silent. It caught the author of '
                          'this registry doing exactly that on 2026-09-09',
        'evidence': 'real run 2026-09-10: 0 malformed rows across the standing docs',
    },
    {
        'tool': 'div_balance_check.py',
        'mode': 'apps',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'an unbalanced <div> tree -- the safe-editing rules say run '
                   'it after EVERY edit and nothing ever did',
        'why_it_matters': 'an unclosed div silently swallows every panel after '
                          'it into the wrong parent',
        'evidence': 'real run 2026-09-10 over all 22 app files: 0 findings',
    },
    {
        'tool': 'duplicate_global_check.py',
        'mode': 'apps',
        'verdict': by_exit,
        'promoted': '2026-09-10, after its one real-run finding turned out to '
                    'be a deliberate wrapper',
        'catches': 'a second top-level declaration of the same global -- the '
                   'later one silently wins and the earlier becomes dead code '
                   'that still reads correctly (Guardian check 13)',
        'why_it_matters': 'hit four times in one session on StoneDesk, every '
                          'time found by a live browser test rather than by '
                          'reading the code',
        'evidence': 'first real run flagged rBids on sairnbuild.html. HAND-READ: '
                    'a deliberate wrapper -- `var _origRBids = window.rBids;` '
                    'then a redefinition that CALLS it -- with a comment at the '
                    'site saying "Do NOT fix this by deleting either half". '
                    'Acting on the report would have deleted a live feature. The '
                    'checker now tests whether the original is saved AND called, '
                    'prints every pair it excused, and reports 0 across 22 apps',
    },
    {
        'tool': 'panel_nesting_check.py',
        'mode': 'apps',
        'verdict': by_exit,
        'promoted': '2026-09-10, after three defects found by running it',
        'catches': 'a panel that is not a sibling of the others, so the '
                   'show/hide CSS cannot reach it',
        'why_it_matters': 'this is how panel-crm went undetected -- structurally '
                          'present, permanently invisible',
        'evidence': 'first real run FAILED on 7 of 22 files, every one for having '
                    'NOTHING TO CHECK. Three defects: NO_PANELS exited 1 (a '
                    'failure for an empty question); `page-` containers were '
                    'unmatched; and the name part excluded hyphens, so '
                    '`panel-check-register` and every hyphenated id was invisible '
                    'even under the convention it did support. Now 0 failures and '
                    '1 disclosed SKIP (sairncash, 2 camelCase shell containers)',
    },
    {
        'tool': 'fail_open_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'a read that turns "I could not ask" into "there is none" -- '
                   'an absent record and an unreachable server rendering the same',
        'why_it_matters': 'the silent-failure class this platform keeps '
                          'rediscovering; a fail-open read is indistinguishable '
                          'from an honest empty state',
        'evidence': 'real run 2026-09-10: 0 findings, exit 0',
    },
    {
        'tool': 'discarded_verdict_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'a refusal that is computed and then not read -- the gate '
                   'runs and its answer is thrown away',
        'why_it_matters': 'a verdict nobody consults is an authorisation check '
                          'that does not authorise anything',
        'evidence': 'real run 2026-09-10: 0 findings, exit 0. Its own header '
                    'says it cannot see across files; the cross-module half is '
                    'tools/discarded_verdict_crossfile.py, now promoted below',
    },
    # ── THIRD BATCH, 2026-09-10 ─────────────────────────────────────────────
    {
        'tool': 'discarded_verdict_crossfile.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'the CROSS-MODULE half: a verdict returned by a required '
                   'module and dropped in another file',
        'why_it_matters': 'the same-file checker says in its own header that it '
                          'cannot see this, and an unread verdict is an '
                          'authorisation check that authorises nothing',
        'evidence': 'real run 2026-09-10: 83 verdict-shaped exports, 0 dropped',
    },
    {
        'tool': 'literal_drift_check.py',
        'mode': 'apps',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'a duplicated literal whose copies have DIVERGED -- the same '
                   'constant written twice and then changed once',
        'why_it_matters': 'the copy that was not updated keeps working and keeps '
                          'being wrong, which is how a fix reaches one call site',
        'evidence': 'real run 2026-09-10 over all 22 app files: 0 findings',
    },
    {
        'tool': 'orphan_register_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'an open-work row citing something the register records as '
                   'removed -- a task pointing at code that is gone',
        'why_it_matters': 'the index is what every session reads to choose work',
        'evidence': 'real run 2026-09-10: 11 register entries, 36 deleted names, '
                    '82 open rows, RESULT:CLEAN',
    },
    {
        'tool': 'key_collision_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'a localStorage key written by more than one feature, where '
                   'the two writers disagree about the shape',
        'why_it_matters': 'two writers on one key is how one panel silently '
                          'erases another\'s rows',
        'evidence': 'real run 2026-09-10: RESULT:CLEAN -- four collisions, every '
                    'one ACKNOWLEDGED with a hand trace in the tool itself. Its '
                    'own line is the right standard: "a key with two writers is '
                    'a pointer, not a verdict"',
    },
    {
        'tool': 'sairn_strict_args_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10, after its one real-run finding turned out to be '
                    'correct code',
        'catches': 'Guardian check 31 -- a function that mutates a parameter and '
                   'then forwards `arguments` under strict mode, where the '
                   'mutation is silently discarded',
        'why_it_matters': 'six window.fetch patches shipped this way; three were '
                          'live features that had been doing nothing since they '
                          'shipped, with no error and nothing wrong on screen',
        'evidence': 'first real run flagged stonedesk.html:3391. HAND-READ: '
                    'correct code -- its `apply(this, arguments)` is an early '
                    'return for a non-proxy URL, BEFORE anything is touched, and '
                    'the mutating path ends in an explicit '
                    '`saSecureClaudeCall(url, opts, _saInnerFetch)`. Guardian 31 '
                    'says in its own text not to "fix" a pass-through that has '
                    'nothing to forward. The checker now requires the forward to '
                    'come AFTER the mutation; driven both ways, and 0 across 22 '
                    'files',
    },
    # ── FOURTH BATCH, 2026-09-10 ────────────────────────────────────────────
    # Both were held out of earlier batches because CC was editing them. CC has
    # released; run against real code, and one needed a fix first.
    # ── FOURTH BATCH, 2026-09-10 ────────────────────────────────────
    # Held out of earlier batches because CC was editing these two. CC has
    # released. Its sibling local_only_collection_check.py is NOT here -- see
    # NOT_PROMOTED below for why, and it is not because it is broken.
    {
        'tool': 'write_without_readback_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10',
        'catches': 'a resource an app WRITES to the server and never reads back '
                   '-- a backup nobody could restore from',
        'why_it_matters': 'a write path with no read path is indistinguishable '
                          'from a working sync until the day somebody needs the '
                          'data. SAIRNlaw wrote 20 resources and read ONE back',
        'evidence': 'real run 2026-09-10: 0 findings, 0 could-not-tell, exit 0',
    },
    {
        'tool': 'traceability_matrix.py',
        'mode': 'once',
        'args': ['--check'],
        'verdict': by_exit,
        'promoted': '2026-09-10, the day it was built',
        'catches': 'docs/traceability-matrix.md no longer matching the '
                   'sources it is derived from -- a guard test, a gate '
                   'check, a registry entry or an index row moved and the '
                   'matrix did not',
        'why_it_matters': 'docs/SAIRN-PROCESS-RULES.md section 1.8 records that '
                          'a GENERATED artefact which must be regenerated after '
                          'every edit reproduces the silent-failure shape it '
                          'exists to catch -- the distinguishing question being '
                          'what it does when stale, since an inventory is '
                          'visibly wrong and a gate simply passes. This is the '
                          'document an outside auditor would read, so it going '
                          'quietly stale is the worst version of that',
        'evidence': 'built and wired the same day: 21-check probe including the '
                    'one that matters -- add a GUARD_TESTS entry and --check '
                    'goes RED, regenerate and it agrees again',
    },
    {
        'tool': 'master_plan.py',
        'mode': 'once',
        # --check, NOT bare, for the reason the tooling_inventory.py entry below
        # records from having got it wrong: without the flag the hook runs the
        # GENERATOR on every push and rewrites a tracked document, which is the
        # one thing a report-only checker must never do. Third generator, third
        # time this flag is load-bearing.
        'args': ['--check'],
        'verdict': by_exit,
        # NOT "the day it was built", which is the honest difference between this
        # entry and its two siblings. master_plan.py was built on 2026-09-13 and
        # this registration was MISSED, so the one status document on the platform
        # that compounds four gates into a FINISHED verdict was the only derived
        # document with no check on any push.
        'promoted': '2026-09-14, a day after it was built -- see `evidence`',
        'catches': 'docs/MASTER-PLAN.md no longer matching the repo -- a '
                   'resource, a test file, a tier or a trace moved and the '
                   'one document that compounds four gates into a single '
                   'FINISHED verdict was not regenerated',
        'why_it_matters': 'this is the document that answers "is this vertical '
                          'finished?", and the drift it was built to stop is '
                          'the drift it then suffered: docs/2026-09-13-stackup-'
                          'traverse-drift-scoping.md records the hand-maintained '
                          'version reading "86 of 273" while its own cited source '
                          'said "135 of 328", three days apart. Making the '
                          'numbers derived removed the hand-maintenance and left '
                          'the staleness, because nothing asked',
        'evidence': 'the check BIT, observed rather than constructed: on '
                    '2026-09-14 `--check` answered FAIL against the committed '
                    'document and regenerating moved five lines (test files on '
                    'disk 340->342, traced 150->152, worst-case bound 480->482) '
                    'after which it answered OK. It had gone red with nothing '
                    'reporting it, and was found by running the tool by hand. '
                    'tests/run_master_plan_probe.py is 43 arms green -- but '
                    'NOTE, plainly: none of them is a staleness arm, so the '
                    'sibling entry above can cite a fixture proving --check goes '
                    'RED and this one cannot yet',
    },
    {
        'tool': 'invisible_in_pattern_check.py',
        'mode': 'once',
        'verdict': by_exit,
        # REPORT-ONLY FIRST, not blocking, and that is the standing promotion
        # path rather than timidity: nothing here had ever run against real code
        # until today, and the tool that reported ALL 26 of SAIRNfreedom's panels
        # unreachable is the reason this file exists at all. Its real-world
        # false-positive rate is unknown until it has been quiet in practice.
        # control_char_check.py sat report-only from 2026-09-10 and was promoted
        # to push-gate check 11 on 2026-09-13 on a measured track record; this is
        # the same road, and the date it earns the same promotion belongs in a
        # decision, not in this comment.
        'promoted': '2026-09-14, the day it was built',
        'catches': 'an invisible character INSIDE a regex literal or a string '
                   'handed to a regex constructor -- a zero-width space, an '
                   'NBSP, or a bidi override, where it silently changes what '
                   'the pattern matches and no reader can see it',
        'why_it_matters': '2026-09-14 was the THIRD confirmed instance on this '
                          'platform of an invisible character defeating an '
                          'assertion, and ALL THREE WERE PRIVILEGE GUARDS. '
                          'api/sv-auth.test.js asserted "NOTHING in this '
                          'endpoint deletes a credential row" with two literal '
                          '0x08 bytes where word boundaries were meant, so the '
                          'pattern could never match and the guard on a '
                          'DEA-relevant register passed unconditionally for its '
                          'whole life. control_char_check.py closed the C0 half; '
                          'this one closes everything above it, and the bidi '
                          'overrides it also covers are worse in kind -- source '
                          'that READS differently from how it EXECUTES '
                          '(Trojan Source, CVE-2021-42574)',
        'evidence': 'blind lock 10/10 fixtures before any real file is opened, '
                    'two of them being real-world occurrences it must stay '
                    'SILENT about -- the deliberate UTF-8 BOM sairnroofing.html '
                    'writes into its CSV, and a C0 byte, which is the other '
                    "tool's question. tests/run_invisible_in_pattern_probe.py "
                    'drives both directions on real files in a throwaway '
                    'worktree: a planted ZWSP makes it exit 1 naming file, '
                    'codepoint and that it is INSIDE A PATTERN; the untouched '
                    'tree exits 0; a broken fixture exits 2 having judged '
                    'nothing; and a planted C0 leaves it silent WHILE '
                    'control_char_check catches it, so the split between the two '
                    'leaves no hole. First real sweep: 653 files, ZERO findings, '
                    'and a census of 1 -- the CSV BOM',
    },
    {
        'tool': 'checkblocks.py',
        'mode': 'apps',
        'verdict': by_exit,
        'promoted': '2026-09-12, after being given an exit code it never had',
        'catches': 'a <script> block in an app file that no longer PARSES -- '
                   'Guardian Check 0a, extracted per block with an HTML parser '
                   'and run through node --check',
        'why_it_matters': "CLAUDE.md calls this check non-negotiable and says it "
                          "hard blocks everything else, and NOTHING ON THIS "
                          "PLATFORM PARSED APP JAVASCRIPT ON A PUSH. "
                          "html_script_check.py is the PostToolUse hook whose NAME "
                          "suggests it does, and its own header says in capitals "
                          "that it does not -- 'There is no `node --check` here and "
                          "never has been'. So the syntax gate was a habit, not a "
                          "mechanism. Worse, this tool printed FAILED_BLOCKS:1 and "
                          "exited 0, so wiring it on exit code before 2026-09-12 "
                          "would have reported a clean pass on a file that does not "
                          "parse -- proven with a planted `function zz({ {{{ ;`",
        'evidence': 'real run 2026-09-12: all 22 root .html files exit 0; a planted '
                    'SyntaxError exits 1; a file with no script block exits 2, '
                    'which is could-not-tell and NOT a pass',
    },
    {
        'tool': 'comment_sensitivity_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-12, once its one real finding was fixed',
        'catches': "a checker whose ANSWER changes when the target's comments are "
                   'stripped -- it is matching text that describes code rather '
                   'than code',
        'why_it_matters': 'three separate tools were counting their own '
                          'documentation within two days (write_path_fault_scan.py, '
                          'sairn_storage_wrapper_honesty.js, and the two probes '
                          'CLAUDE.md records), and the direction that matters is '
                          'the quiet one: an assertion of PRESENCE goes GREEN when '
                          'the only surviving mention of the thing is a comment '
                          'describing the feature that was deleted',
        'evidence': 'real run 2026-09-12 found ONE: key_collision_check.py counted '
                    '93 key writes on stonedesk.html raw and 92 stripped -- one was '
                    'a line of prose. Verdict unchanged either way, which is why it '
                    'survived. Fixed in the same commit; 0 findings after, across 22 '
                    'targets and 6 checkers',
    },
    {
        'tool': 'metamorphic_check.py',
        'mode': 'once',
        # A SIZE CAP AND ONE TARGET, AND IT WAS EARNED THE HOUR THIS WAS
        # PROMOTED. The full pass is 6 checkers x 22 apps x 5 relations and
        # stonedesk.html alone is ~160s of a ~200s run, which pushed the whole
        # report-only sweep past the 600s budget in its own probe. The deep
        # pass stays a deliberate command: `metamorphic_check.py --all`.
        # The cap and the files it excludes are PRINTED on every run.
        'args': ['--max-bytes', '600000', '--targets', '1'],
        'verdict': by_exit,
        'promoted': '2026-09-13',
        'catches': "a checker whose ANSWER changes under a transform that cannot "
                   "legitimately change it -- a byte-identical copy at another "
                   "path, flipped line endings, trailing whitespace, inserted "
                   "blank lines -- and a finding ERASED by duplicating the file",
        'why_it_matters': 'almost every check here has NO ORACLE, so nobody can '
                          'test it by comparing against the right answer. A '
                          'control pair proves a checker CAN fire; this proves it '
                          'fires for the right REASON. The class is not '
                          'hypothetical: literal_drift_check.py answered '
                          'differently on identical input (PYTHONHASHSEED, fixed '
                          'in ac8f8491) and a CRLF-vs-LF difference produced '
                          'three false alarms in one session on 2026-09-03',
        'evidence': 'first real run 2026-09-13, --all: 660 comparisons (6 checkers '
                    'x 22 app files x 5 relations), 0 violated, 0 could-not-run. '
                    'THAT ZERO IS ONLY WORTH SOMETHING BECAUSE OF THE BLIND LOCK -- '
                    'the criteria are classified against synthetic fixtures first '
                    'and the real run is REFUSED if a relation cannot fire. The '
                    'lock caught its own tool twice on the first two runs: `crlf` '
                    'was unfalsifiable because the fixture read through universal '
                    'newlines, and the fixture later agreed with itself by '
                    'arithmetic accident on a CRLF target (6 bytes removed, 6 '
                    'spaces added). Three more defects were found by running it, '
                    'ALL IN THE HARNESS: reading the target through universal '
                    'newlines made `identity` secretly the `crlf` transform and '
                    'accused key_collision_check.py of nondeterminism; normalising '
                    'the bare basename rewrote a checker\'s PROSE and made two '
                    'identical reports compare unequal; and a position-format list '
                    'that knew `lines [..]` but not `A line(s) [..]` reported '
                    'literal_drift_check.py as violated on all three targets. Held '
                    'in both directions by tests/run_metamorphic_probe.py',
    },
    {
        'tool': 'criticality_tier_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-12',
        'catches': 'a registered resource in a re-tiered app with no criticality '
                   'tier, a tier row naming a resource that no longer exists, and '
                   'a Tier A resource with no evidence line',
        'why_it_matters': 'the tiering is the input to every other priority call '
                          'on this platform, and it is 382 rows maintained by hand '
                          'across 17 apps. A resource added without a tier is '
                          'invisible to that judgement rather than low-priority',
        'evidence': 'real run 2026-09-12: 382 registered, 382 rows, 17 re-tiered '
                    'apps, 78 Tier A, PROBLEMS:0',
    },
    {
        'tool': 'soup_register_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-12',
        'catches': 'a third-party component the product RUNS that is absent from '
                   'the SOUP register, and a register entry for something no '
                   'longer running',
        'why_it_matters': 'SOUP tracking is a standing discipline rather than a '
                          'one-time task, and a register nobody checks is a list '
                          'rather than a control -- the same shape as every other '
                          'hand-maintained claim in this repo',
        'evidence': 'real run 2026-09-12: 3 npm direct dependencies, 3 CDN scripts '
                    'in root apps, CLEAN both directions',
    },
    {
        'tool': 'committer_identity_check.py',
        'mode': 'once',
        'args': [],
        'verdict': by_exit,
        'promoted': '2026-09-13, the day the leak was found',
        'catches': "a clone configured to commit under one of the throwaway "
                   "identities this repo's own probes use -- the list is READ "
                   "out of the probe sources, so a new probe's identity is "
                   "covered with no edit to the checker",
        'why_it_matters': '131 commits reached origin/main authored AND '
                          'committed as `probe <probe@local>` between '
                          '2026-09-10 and 2026-09-13, including an app\'s '
                          'entire per-employee auth endpoint. One clone had '
                          'the identity written into its LOCAL git config '
                          'instead of passed per-invocation with `git -c`. '
                          'NOTHING on the platform reads the committing '
                          'identity -- verified, not assumed: the push gate '
                          'greps clean for %an/%ae/%cn/%ce and user.name/'
                          'user.email -- so nothing said anything for three '
                          'days. Check 8, the one check about probe residue, '
                          'keys on the commit SUBJECT matching ^PROBE and was '
                          'therefore NOT degraded by this and did not catch it '
                          'either; those are two different facts',
        'evidence': 'real run 2026-09-13: CLEAN in all four clones after the '
                    'leak was unset in SAIRN-fourth. It reports the 131 '
                    'already-affected commits as a number and deliberately '
                    'does NOT fail on them -- rewriting published history on a '
                    'repo four clones share is the larger risk. Held in BOTH '
                    'directions by tests/run_committer_identity_probe.py, 20 '
                    'arms, which breaks a THROWAWAY CLONE rather than a '
                    'worktree because user.* is REPOSITORY config a worktree '
                    'shares; 7 mutation controls bite',
    },
    {
        'tool': 'install_git_hooks.py',
        'mode': 'once',
        # --check, NOT bare. Bare INSTALLS: it rewrites .githooks/pre-push to
        # LF and sets core.hooksPath. A report-only checker must not mutate a
        # tracked file or this clone's config -- the same trap tooling_inventory
        # fell into below, read before registering this one.
        'args': ['--check'],
        'verdict': by_exit,
        'promoted': '2026-09-13, the day --check was widened to answer the real question',
        'catches': 'a clone whose pre-push hook is not installed, is CRLF and '
                   'therefore silently skipped by git, or whose gate script or '
                   'shell wrapper does not execute',
        'why_it_matters': "the pre-push hook is the ONLY thing that gates a push "
                          "made by subprocess -- which is how sairn_claim.py "
                          "pushes -- and .git/ is not versioned, so a fresh clone "
                          "has no hooks until somebody runs the installer. On "
                          "2026-09-01 all four clones held a CRLF copy and git was "
                          "skipping it silently on every push; two of them had "
                          "core.hooksPath set, which is all --check looked at, so "
                          "it would have printed OK on a hook that had never once "
                          "executed. Nothing ran --check anyway",
        'evidence': 'real run 2026-09-13: OK in this clone. Held in BOTH '
                    'directions by tests/run_githook_install_probe.py, which '
                    'breaks a THROWAWAY CLONE three ways -- core.hooksPath unset, '
                    'hook rewritten to CRLF with the config left CORRECT, and a '
                    'wrapper that does not execute -- and asserts this clone is '
                    'untouched; 5 mutation controls bite',
    },
    {
        'tool': 'tooling_inventory.py',
        'mode': 'once',
        # --check, NOT bare. Without it the hook runs the GENERATOR on every push
        # and REWRITES the document -- a report-only checker mutating a tracked
        # file, which is the one thing report-only must never do. Caught within
        # the hour by run_all_tests.py's own dirty-tree detector reporting
        # `M docs/TOOLING-INVENTORY.md` after a clean run. traceability_matrix.py
        # carries the same flag for the same reason; I registered this one without
        # reading that entry closely enough.
        'args': ['--check'],
        'verdict': by_exit,
        'promoted': '2026-09-12, the day it was built',
        'catches': 'docs/TOOLING-INVENTORY.md no longer matching the wiring -- a '
                   'tool added, promoted, wired or removed without the inventory '
                   'being regenerated',
        'why_it_matters': "the document it replaces was hand-derived, correct on "
                          "2026-09-09 and STALE BY 2026-09-12: it said 77 tools, 3 "
                          "report-only and 28 unwired checkers, against 97 and 29 "
                          "three days later. A tool that does not run produces no "
                          "output to contradict an inventory, which makes this the "
                          "one document whose staleness is hardest to notice -- so "
                          "the only thing that keeps it true is a check that fails",
        'evidence': 'real run 2026-09-12: OK, and its probe mutates the committed '
                    'document and confirms --check exits non-zero',
    },
    {
        'tool': 'schema_snapshot_freshness.py',
        'mode': 'once',
        'args': [],
        'verdict': by_exit,
        'promoted': '2026-09-11, the day it was built',
        'catches': 'db/schema_snapshot.json no longer knowing a table that sql/ '
                   'creates -- either that SQL has never been run, or the '
                   'snapshot is behind the database',
        'why_it_matters': 'the snapshot is a PASTED capture: run the query, '
                          'copy the JSON cell, save the file. The save step is '
                          'a human action with nothing behind it, and on '
                          '2026-09-11 it was measurably skipped -- the query '
                          'had been run the night before and the committed file '
                          'was still the 2026-09-02 capture, byte-identical to '
                          'HEAD. tools/gate_column_check.py reads this file to '
                          'answer "does this column exist", so a stale capture '
                          'turns into a confident wrong answer one level down',
        'evidence': 'real run 2026-09-11: 444 tables created in sql/, 258 in '
                    'the snapshot, 210 absent and 39 of those queried by api/. '
                    'BOTH readings are real and both were measured live the '
                    'same day -- mech_checks provisioned:true (snapshot behind) '
                    'and grd_rounds provisioned:false (SQL never run), in the '
                    'same list. The tool reports the question and refuses to '
                    'pick, which arm 4 of its probe asserts',
    },
    {
        'tool': 'index_duplicate_check.py',
        'mode': 'once',
        'args': [],
        'verdict': by_exit,
        'promoted': '2026-09-11, the day it was built',
        'catches': 'two rows of docs/SAIRN-OPEN-WORK-INDEX.md describing the '
                   'same subject -- a superseded row that was never removed, so '
                   'the file every session reads to choose work gives two '
                   'answers and the reader cannot tell which is current',
        'why_it_matters': 'this is the CLAIMS problem at the document level. '
                          'sairn_claim.py stops two sessions doing the same '
                          'work; nothing stopped the index describing the same '
                          'work twice. On the day it was built the index held '
                          'TWO such pairs, both Hank rows superseded and left '
                          'in place -- "324 of 389 ... no removal path" beside '
                          '"321 of 389", and "56 TIER A resources" beside "53 '
                          '(was 56)". The tool answers 321 and 53, verified by '
                          'running it rather than trusting either row',
        'evidence': 'both stale rows removed the same day; the checker goes '
                    'from 2 pairs to 0 across 323 rows. Held by a 13-arm probe '
                    'whose arm 2 is the case that prompted it -- a pair '
                    'differing ONLY by a moving count must still match, which '
                    'is why numbers are stripped before comparing',
    },
    {
        'tool': 'gate_column_check.py',
        'mode': 'once',
        'args': [],
        'verdict': by_exit,
        'promoted': '2026-09-11, the day it was built',
        'catches': 'a server file reading a property off a queried row that is '
                   'NOT a column of that table -- a read that can only ever '
                   'produce undefined, and a gate built on it that can never '
                   'fire',
        'why_it_matters': 'three identical entitlement gates read '
                          'lic.trial_ends_at and refuse with 402 on an expired '
                          'trial. trial_ends_at is not a column on '
                          'license_keys, so it is always null and the 402 has '
                          'never been reachable on any licence -- the '
                          'entitlement check for the whole StoneDesk data '
                          'path, the paid render feature and the agent store. '
                          'It survived because the code SAYS so in prose: a '
                          'field initialised to null and a comment calling the '
                          'column "newly-added", which it never was',
        'evidence': 'real run 2026-09-11: 3 files attributed, 1 finding -- the '
                    'known trial_ends_at read -- and 3 multi-table files NAMED '
                    'as not-checked rather than counted clean. Held by a 15-arm '
                    'probe whose arm 2 proves the answer follows the SNAPSHOT '
                    'and not a hardcoded name: add the column to a fixture '
                    'schema and the same read goes silent',
    },
    {
        'tool': 'mutation_anchor_check.py',
        'mode': 'once',
        'args': [],
        'verdict': by_exit,
        'promoted': '2026-09-11, the day it was built',
        'catches': 'a mutation probe whose anchor no longer matches its target '
                   'exactly once -- so the arm plants nothing and the control '
                   'stops testing -- and a probe that mutates a tracked file in '
                   'place without refusing an import',
        'why_it_matters': 'each probe already checks its OWN anchors, but only '
                          'when something runs it, and on 2026-09-11 four of the '
                          'six could not be swept at all because they declare '
                          'their target differently -- so "they pass in the full '
                          'suite" was the strongest claim available, which is '
                          'not the same as "their anchors were verified". The '
                          'import half is worse: importing an unguarded probe '
                          'RUNS it, and an interrupted import leaves a mutated '
                          'source file on disk',
        'evidence': 'real run 2026-09-11: 6 probes, 70 anchors, 0 bad, 0 '
                    'unreadable. The import hazard is not hypothetical -- the '
                    'first version of this very tool imported the probes, hung, '
                    'was killed, and left api/_lib/dental-guardian.js modified '
                    'with an injected probe field. Rewritten to parse with ast',
    },
    {
        'tool': 'comment_quote_check.py',
        'mode': 'once',
        'args': [],
        'verdict': by_exit,
        'promoted': '2026-09-11, the day it was built',
        'catches': 'a probe whose assertion matches the target file COMMENTS '
                   'rather than its code -- a literal that exists only inside '
                   'a comment, undeclared',
        'why_it_matters': 'it happened twice on 2026-09-10, hours apart, in '
                          'the harmless direction: a probe searched for a '
                          'literal the fix own comment quotes and FAILED a '
                          'correct file, which is loud. The dangerous '
                          'direction is silent -- an assertion of PRESENCE '
                          '("the guard is still there") goes GREEN when the '
                          'only surviving mention is a comment describing the '
                          'feature that was deleted. Nothing else would catch '
                          'that',
        'evidence': 'real run 2026-09-11: 5 assertions inspected, 4 '
                    'comment-only and every one of them DELIBERATE and '
                    'declared with a reason, 0 undeclared. Its own first '
                    'version committed the error it hunts -- it blanked from '
                    'any // to end of line, so every https:// swallowed the '
                    'rest of its line and it reported real code as comment',
    },
    {
        'tool': 'defect_register.py',
        'mode': 'once',
        'args': ['--check'],
        'verdict': by_exit,
        'promoted': '2026-09-10, the day it was built',
        'catches': 'a record in docs/defect-density-register.json that has '
                   'stopped being true -- a commit that no longer resolves, '
                   'a detection method outside the vocabulary, or the same '
                   'defect counted twice',
        'why_it_matters': 'the register LENGTH reads as evidence of '
                          'thoroughness, so a record pointing at nothing is '
                          'worse than no register at all -- and a free-text '
                          'detection method makes the coverage matrix, '
                          'which is the only honest signal in it, '
                          'meaningless',
        'evidence': 'built and wired the same day: 24-check probe that '
                    'ATTACKS it -- a nonexistent commit, an invented method, '
                    'an invented layer and a duplicate are each refused, and '
                    'a record whose commit is deleted makes --check go red',
    },
    {
        'tool': 'npm_audit_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10, the day it was built',
        'catches': 'a known advisory against a package in the committed '
                   'lockfile, direct or transitive, with the advisory URL',
        'why_it_matters': 'two moderate Dependabot alerts sat open for at least '
                          'a day and the SOUP register recorded them as '
                          'untriaged BECAUSE `gh` is not installed here. That '
                          'reason was assumed and wrong -- `npm audit` reads '
                          'the lockfile and needs no GitHub credential. The '
                          'blocker was never the missing tool, it was that '
                          'nothing ran the check that did not need one',
        'why_it_is_wired_despite_needing_the_network':
            'MEASURED, not guessed: 8.1s and 8.5s on two runs, against a sweep '
            'that already takes 146s -- about 5%. It was nearly held back on an '
            'assumed 30s cost. Network failure is exit 3 (could-not-tell) and '
            'lands in UNRUN, never in findings and never silently in a pass',
        'evidence': 'real negative control, not a fixture: run against the '
                    'PRE-BUMP lockfile it exits 1 and names both qs advisories '
                    'by URL; against the fixed lockfile it exits 0. Its first '
                    'version reported `SKIPPED: npm is not on PATH` on this '
                    'machine because npm is npm.cmd on Windows -- an honest '
                    'exit 3 that would have printed on every push in every '
                    'clone forever. Caught by running it, not by reading it',
    },
    {
        'tool': 'control_char_check.py',
        'mode': 'once',
        'verdict': by_exit,
        # PROMOTED TO BLOCKING 2026-09-13 as push-gate CHECK 11, and KEPT
        # HERE ON PURPOSE rather than moved. The two runs answer different
        # questions and both are wanted: the gate scans only the files a
        # push SHIPS, so a standing finding cannot refuse everybody's push,
        # while this whole-tree run keeps that standing finding VISIBLE
        # instead of letting it sit unreported until someone touches the
        # file. checkblocks.py is in both lists for the same reason.
        'promoted': '2026-09-10 report-only; BLOCKING 2026-09-13 (Michael) as push-gate check 11',
        'catches': 'a raw C0 control byte in any tracked text file -- an '
                   'escape sequence typed as its literal character',
        'why_it_matters': 'TWO OF THE FOUR FOUND WERE DEAD REGEXES. '
                          '/grant[^;]*<BS>delete<BS>/i is the assertion "the '
                          'schema still grants no delete privilege" and it '
                          'returns false on a grant that includes delete, so '
                          'it could never fail. And a raw NUL makes the file '
                          'UNSEARCHABLE: grep answered "Binary file '
                          'api/sd-data.js matches" with no lines, on the '
                          'central API handler serving every app, which looks '
                          'like "no matches" rather than like a tool giving up',
        'evidence': 'real negative control against the real tree, not a '
                    'fixture: run against the pre-fix files it exits 1 and '
                    'names all SIX bytes with file, line and offset; after the '
                    'fix, 0. 1622 files in 1.3s. NOT a git-diff problem -- '
                    '.gitattributes marks the repo text so diffs were readable '
                    'the whole time, verified rather than assumed, and the '
                    'first draft of the finding had that wrong. THE TRACK RECORD IS WHAT '
                    'PROMOTED IT: two fleet-wide sweeps, zero false positives, and on '
                    '2026-09-13 it caught a FIFTH within hours of the file shipping -- '
                    '/<BS>delete<BS>/i in api/sv-auth.test.js, the assertion that '
                    "SAIRNvet's auth endpoint deletes no credential row, which had "
                    'never been capable of failing. Held as a gate by '
                    'tests/push_gate/check11_probe.py, 20 arms, 5 mutation controls bite',
    },
    {
        'tool': 'truthy_sum_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-11, the day it was built',
        'catches': 'a NEW `+ (x || 0)` in a numeric fold with no Number() '
                   'around it -- the guard never fires on a non-empty string, '
                   'so `+` CONCATENATES instead of adding',
        'why_it_matters': 'measured: 0 + ("500" || 0) is the STRING "0500". '
                          'From a real 350 baseline a total of "abc" renders '
                          '"350abc" and somebody asks; "500" renders "350500", '
                          'a believable $350,500 where the truth is $850, and '
                          'nobody asks. THE PLAUSIBLE CASE IS THE DANGEROUS '
                          'ONE -- and in SAIRNdental that figure was handed to '
                          'Claude by vSpendAI() under a prompt calling it '
                          '"real, already-computed", so the fabrication would '
                          'have propagated into an AI answer as fact',
        'evidence': '82 candidate occurrences across 8 files, 51 distinct '
                    'file+field keys, all grandfathered so a NEW one fails. '
                    'It read 140 on the first real run and 58 of those were '
                    'NOT folds: a STRING LITERAL on the left makes `+` '
                    'concatenate, so `\'$\' + (x || 0)` is a currency label '
                    'and sums nothing. Classified separately 2026-09-13, '
                    'COUNTED AND PRINTED rather than dropped, and the 31 '
                    'baseline keys that existed only to excuse them removed '
                    '-- before that, every price-display line anyone added '
                    'tripped the check and was answered with an exemption. '
                    'The tool now also reports baseline keys nothing matches '
                    'any more. 33-arm probe, and the arms worth having are the '
                    'ones that keep it trustworthy: MULTIPLICATION IS NOT '
                    'REPORTED (2 * ("3"||0) is 6; only + concatenates), '
                    'Number/parseFloat/parseInt go silent, and the pattern '
                    'quoted in a COMMENT or a STRING is not code -- that last '
                    'arm exists because the first version reported 193 and '
                    'FIFTY-TWO were prose explaining the defect, including the '
                    'refusal message of this checker\'s own subject. 3.1s',
    },
    {
        'tool': 'removal_path_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10, the day it was built',
        'catches': 'a NEWLY registered resource the product cannot remove a '
                   'record from -- no delete and no soft_delete verb -- that is '
                   'not in tools/removal_path_baseline.json with a reason',
        'why_it_matters': '324 of 389 registered resources are in that state '
                          'TODAY, and it is not a soft number: sd-data.js '
                          'upserts on (license_hash, id) at 117 call sites '
                          'against THREE single-row collections, so writing the '
                          'collection without an item removes nothing. A row '
                          'the product can create is a row only Michael can '
                          'remove by hand in the SQL editor -- which is what '
                          'the 15+ sql/*_cleanup.sql files across 11 apps are, '
                          'and why that pile keeps growing',
        'evidence': '18-arm probe, and the arm worth having is the FALSE '
                    'EXEMPTION one: a shared registry comment reading "X is '
                    'MUTABLE; Y is APPEND-ONLY" was attributed wholesale by the '
                    'first version, labelling a money record its own comment '
                    'calls MUTABLE as append-only and silently exempting it. '
                    'The probe asserts the mutable sibling still fails. Also: '
                    'a missing baseline turns every stuck resource into a '
                    'finding rather than passing quietly, and an unloadable '
                    'registry is an error rather than CLEAN. 0.3s',
    },
    {
        'tool': 'bypassed_constant_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-14, the day it was built. Report-only: it reports a '
                    'shape that is sometimes deliberate, and a checker whose '
                    'finding might be a considered choice has no business '
                    'refusing a push',
        'catches': 'a declared decimal rate constant that some call site in the '
                   'same app HTML bypasses with the literal value -- so changing '
                   'the rate moves the declaration and leaves those sites '
                   'quietly wrong',
        'why_it_matters': 'sairnbiz declared SB_TAX_FICA_RATE with a careful '
                          'note distinguishing it from the employee half, and '
                          'two call sites multiplied by 0.0765 directly. The '
                          '2026-09-03 competitive-gap audit reached the same '
                          'conclusion from the product side -- "a product that '
                          'needs a deploy to stay legal is a product that is '
                          'quietly wrong between deploys" -- and the 2026-08-28 '
                          'SAIRNsenior pass reached it from the regulatory '
                          'side. completeness_check.py asks a version of this '
                          "question and walks api/ ONLY; every app's rates "
                          'live in the HTML, outside its reach',
        'evidence': 'THE CRITERION WAS NARROWED ONCE AND THE MEASUREMENT IS '
                    'RECORDED IN THE TOOL. "A declared constant whose value '
                    'appears again as a literal" flagged 60 across the platform '
                    'and almost all were noise -- TRIAL_DAYS = 30 against 134 '
                    'unrelated 30s, SD_CTX_MAX_MEMORIES = 10 against 242 '
                    'unrelated 10s. Narrowed to decimals with three or more '
                    'significant digits: 2 findings, both real, both the same '
                    'site. The integer blind spot is therefore DELIBERATE and '
                    'is printed on every clean run. 20-arm probe whose sharpest '
                    'arm is that two constants sharing a value do not accuse '
                    'each other -- employer and employee FICA are different '
                    'money at the same rate, and the first criterion reported '
                    'both forever. Sabotage-verified in both directions. It '
                    'also caught three of its OWN fixtures using a name the '
                    'tool cannot match, two of which were passing vacuously. '
                    '0.4s',
    },
    {
        'tool': 'ownership_evidence_drift.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-14, the day it was built, report-only and NOT a '
                    'push-gate block: it reports that nobody has LOOKED, which '
                    'is not the same as a finding and must never refuse a push',
        'catches': 'the ownership evidence behind an accepted risk drifting away '
                   'from the population it was evidence about',
        'why_it_matters': "docs/SAIRN-OPEN-WORK-INDEX.md carries "
                          "`supabase_admin`'s default ACL -- which grants anon "
                          "and authenticated FULL CRUD on tables it creates -- "
                          "as ACCEPTED RISK, MONITORED. It is accepted on ONE "
                          "measurement: 100% postgres ownership across 251 "
                          "tables on 2026-08-26. The row names its own re-check "
                          "trigger, names the monitor as one SELECT, and "
                          "NOTHING RUNS IT. A tool that exists is not a "
                          "mechanism; a tool that RUNS is",
        'evidence': 'RED on its first run and correctly so: 251 tables when the '
                    'evidence was taken, 380 now, 129 unobserved and 51% growth. '
                    'That is not a claim the ACL has fired -- it almost '
                    'certainly has not, every migration here goes through the '
                    'SQL editor as postgres -- it is a statement that nobody has '
                    'checked, which must not read as a clean result. 18-arm '
                    'probe whose MAIN arm is that it goes GREEN when the '
                    'baseline is refreshed, because a checker that can only be '
                    'red is as useless as one always green; an unreadable '
                    'snapshot is COULD NOT RUN rather than zero drift, verified '
                    'by sabotage. 0.1s',
    },
    {
        'tool': 'eaten_substitution_check.py',
        'mode': 'once',
        'verdict': by_exit,
        # -n 40, NOT the default range and NOT a big one. The default is
        # `@{u}..HEAD`, which is EMPTY by the time this sweep runs after a
        # push -- it would be silent forever and look like a passing check.
        # A large window re-reports the two historical instances on every
        # push, which is a check that cries wolf permanently. 40 is a rolling
        # window: far more than lands between two consecutive sweeps, and
        # short enough that a recorded-and-corrected instance rolls out.
        'args': ['-n', '40'],
        'promoted': '2026-09-14, the day it was built, report-only and NOT '
                    'wired into the push gate: it reports a SHAPE and cannot '
                    'know a shell caused it, and a check that cannot tell a '
                    'stray keystroke from an eaten expression has no business '
                    'refusing a push',
        'catches': 'a commit message whose paragraph has a continuation line '
                   'beginning with a stray single space -- what bash leaves '
                   'behind when a backticked expression inside a double-quoted '
                   '-m evaluates to nothing and is deleted',
        'why_it_matters': 'scrubber item 18 has TWO vehicles and only one had '
                          'a checker. control_char_check.py covers the heredoc '
                          'byte; nothing covered the commit message, and item '
                          '18 records it happening TWICE on 2026-09-14 -- the '
                          'second time in a commit whose subject is about a '
                          'check that silently stops testing anything. The '
                          'shell reports success every time, so the damage is '
                          'visible only to someone who re-reads the message, '
                          'and nobody re-reads a commit message',
        'evidence': 'FALSE POSITIVES MEASURED ON REAL DATA: 0 in 2,998. Over '
                    'the last 3,000 commits it flags exactly 2, and both are '
                    'the instances item 18 already records. RECALL IS NOT '
                    'MEASURED and is not claimed -- the criterion was read off '
                    'those same two commits, so finding them is circular. The '
                    'blind spot is structural and stated on every clean run: a '
                    'substitution that produced OUTPUT leaves no gap at all, so '
                    'only the empty-output case is detectable afterwards and '
                    '`git commit -F` remains the control. 32-arm probe; '
                    'removing the list-item exclusion takes 7 arms red and '
                    'silencing the detector takes 9, each sabotage asserting '
                    'its own anchor matched first. 0.2s',
    },
    {
        'tool': 'temporary_state_check.py',
        'mode': 'once',
        'verdict': by_exit,
        # --check, NOT the bare report. The bare run prints a read-list and
        # exits 0 whatever it finds, which in a runner silent on a clean run
        # means it would never say anything -- the same reason secrets_inventory
        # and dependency_graph were registered with a flag rather than bare.
        'args': ['--check'],
        'promoted': '2026-09-14, report-only and deliberately NOT wired into '
                    'the push gate. What it reports is state that LOOKS '
                    'temporary, and it cannot read intent -- a long-expiry '
                    'session token and a leaked suppression flag are the same '
                    'shape. The only thing --check FAILS on is a declaration '
                    'naming a scope the vocabulary has no word for, because '
                    'that needs no threshold and no policy',
        'catches': 'a `// TEMPORARY-STATE: scope=... released-by=...` comment '
                   'whose scope is not one of command/call/request/session/'
                   'persistent. The UNDECLARED count is printed on every run '
                   'and gates NOTHING',
        'why_it_matters': 'item 34. A checker CANNOT tell a leaked flag from a '
                          'deliberately long-lived one, so the requirement is '
                          'the DECLARATION, not the detection -- item 3/33 '
                          'falsifiable-requirement discipline applied to '
                          'lifetime. Without a stated intended scope there is '
                          'nothing to falsify, and a detector that guesses '
                          'either floods the report or stays silent',
        'evidence': 'real run 2026-09-14: 723 files, 0 declarations, 175 '
                    'undeclared candidates, PASS. TWO REAL DEFECTS IN THE '
                    'SUBJECT were found by building the control first -- a '
                    "case-insensitive /config/ matched storeError('CONFIG', "
                    '...) in api/_lib/sd-store.js, and the Python `= True` '
                    'blind spot was real and undisclosed. And a LIVE finding, '
                    'not historical: stonedesk.html 2286/2299/6350 set '
                    'sdSyncSuppressed=true, call st(), clear it, with no '
                    '`finally` -- a throw between them silences every later '
                    'server write for the session. 24-arm probe; neutering '
                    'FLAG_ON collapses the positive arms, and the sabotage '
                    'asserts its own anchor is present first. 0.4s',
    },
    {
        'tool': 'export_coverage_check.py',
        'mode': 'once',
        'verdict': by_exit,
        # --check, not the bare report, for the same reason as the three above:
        # the bare run prints a table and exits 0 whatever it finds.
        'args': ['--check'],
        'promoted': '2026-09-14, report-only. It FAILED ON ITS FIRST DAY on '
                    'four real gaps and PASSES NOW -- all four were closed the '
                    'same day. NOT wired into the push gate: a missing export '
                    'is a product decision and has no business refusing '
                    "somebody else's push",
        'catches': 'a Class A (append-only by design) resource sitting in an app '
                   'whose CSV export registry ALREADY EXISTS and does not carry '
                   'it. Resources in apps with NO export machinery at all are '
                   'counted separately and are NOT gated -- that is a feature '
                   'nobody built, not a gap in one that exists',
        'why_it_matters': 'item 39. An inspector asks for a RECORD, not a '
                          'screenshot. "Can staff look it up" and "can this '
                          'practice produce what it was asked for" are '
                          'different questions and only the second has a '
                          'deadline. SAIRNdental exports nine datasets and NOT '
                          'dnt_charges or dnt_payments, its two append-only '
                          'money records -- what it exports instead is the '
                          'DERIVED ageing buckets, which read as coverage and '
                          'are not the row-level record',
        'evidence': 'real run 2026-09-14: 11 Class A resources parsed from '
                    'docs/2026-09-13-irreversible-write-witnessing-scoping.md '
                    'rather than hardcoded. FIRST run: 3 exportable, 4 gaps in '
                    'an existing registry, 4 in apps with no export path at '
                    'all. AFTER the fix: 7 exportable, 0 gaps, the same 4 with '
                    'no machinery -- and the probe now drives the FAILING '
                    'direction against a planted registry, so closing the real '
                    'gaps did not disarm it. The '
                    'ON-SCREEN half of item 39 is NOT attempted here and the '
                    'tool says so in its own header: two detectors for it were '
                    'wrong in opposite directions, one missing '
                    'alf_staff_credentials entirely and one binding most of '
                    'SAIRNdental. 21-arm probe; blinding the registry reader '
                    'collapses the EXPORTABLE answers, and section E pins all '
                    'eleven verdicts by name so a registry change flips an arm -- which is '
                    'exactly what happened when the four were fixed, and the table '
                    'was edited in the same commit as the apps. 26 arms. 0.2s',
    },
    {
        'tool': 'hover_separation_audit.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-15, report-only from the first day and it should '
                    'never be anything else: it reports on a role that is not '
                    'this clone, and a tool that could block a build agent\'s '
                    'push over the hover auditor\'s behaviour would be '
                    'punishing the wrong session. Its job is to be READ',
        'catches': 'a commit by the hover auditor -- the fifth, review-only '
                   'role -- that touches platform code, which its own skill '
                   'forbids in terms; and the inverse, a build agent editing '
                   'the auditor\'s own tooling. Cross-checks git history '
                   'against the auditor\'s hash-chained self-log, and '
                   'RE-DERIVES that chain independently rather than calling '
                   'the log\'s own --verify',
        'why_it_matters': 'the auditor is the only role here with no second '
                          'reader -- the four build agents review each other '
                          'and nobody reviews the auditor -- which is the '
                          'exact condition its own skill cites Barings and '
                          'Arthur Andersen for. It is also the DETECT half of '
                          'a two-layer control whose PREVENT half '
                          '(tools/hover_auditor_scope_gate.py) lives in a '
                          'per-clone marker under .git/ and can therefore go '
                          'missing in a fresh clone with nothing announcing '
                          'it. THIS is the layer that would notice. IT '
                          'CANNOT PROVE THE NEGATIVE and says so in its own '
                          'output: all five roles commit through ONE git '
                          'identity, attribution is derived from co-changed '
                          'bookkeeping files, and a commit where the auditor '
                          'DID write platform code would land in the '
                          'unattributed 64%. Exit 2 is could-not-run and is '
                          'never folded into clean. 72-arm probe at '
                          'tests/run_hover_separation_probe.py, including the '
                          'chain verifier shown to FAIL on a tampered entry '
                          'and pass again on the restored one',
        'evidence': '2026-09-15 first run: 5,241 commits, 20 auditor commits, '
                    '0 violations; self-log 105 entries, chain INTACT, 33 SHAs '
                    'claimed, 16 resolve and all 16 in scope. 15 of 15 '
                    '"Committed a, pushed b" pairs have the local sha absent '
                    'and the pushed one present, which is what explains 15 of '
                    'the 17 that do not resolve here rather than a plausible '
                    'story doing it. EXIT 2 TODAY, not 0, on the remaining 2',
    },
    {
        'tool': 'advisory_lock_isolation_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-15, report-only on its first day like every other '
                    'checker here. It reports a SUPERSEDED stale migration '
                    'today, which is a real finding and not one a push should '
                    'be blocked on',
        'catches': 'a plpgsql function that takes a pg_advisory lock, then '
                   'READS state and WRITES based on it, with nothing requiring '
                   'READ COMMITTED. Classifies SELECT ... FOR UPDATE and '
                   'UPDATE ... RETURNING as SAFE_SHAPE rather than flagging '
                   'them -- both raise 40001 under REPEATABLE READ, which is '
                   'loud, and a checker that flags the two correct patterns '
                   'alongside the broken one is one people switch off. Also '
                   'reports an OLDER file defining the same function without '
                   'the guard, because `create or replace` means re-running it '
                   'silently reverts one',
        'why_it_matters': 'THE DEFECT IS INVISIBLE IN THE CODE THAT CONTAINS '
                          'IT. pg_advisory_xact_lock serialises ACQUISITION, '
                          'not the SNAPSHOT: under REPEATABLE READ a caller '
                          'that WAITED on the lock still reads from before the '
                          'holder committed, then writes. The cap over-runs or '
                          'the balance overdraws with the lock working '
                          'perfectly, with no error and no contention symptom '
                          '-- the code is correct and the thing that is wrong '
                          'is a setting in another file, one `alter role` '
                          'statement away and looking like a hardening change',
        'evidence': 'FIRST RUN 2026-09-15 over 9 advisory-lock functions found '
                    'THREE unguarded, and the sharpest was '
                    'law_check_and_insert_disbursement -- attorney IOLTA trust '
                    'money, where two concurrent disbursements each compute the '
                    'balance from before the other committed and BOTH pass the '
                    'sufficiency check. Its sibling law_check_and_void_deposit '
                    'already DESCRIBED the hazard in a comment and nothing '
                    'enforced it. All three guarded the same day; 31-arm probe '
                    'at tests/run_advisory_lock_isolation_probe.py. The blind '
                    'lock runs on EVERY run, not only --self-check, and its own '
                    'fixtures caught two real bugs in the first draft before it '
                    'ever touched sql/',
    },
]

# ── DELIBERATELY NOT PROMOTED, AND WHY ──────────────────────────────────────
# `docs/2026-09-09-tooling-inventory.md` says the decision each unwired checker
# needs is blocking / report-only / deliberately manual, "recorded once rather
# than left unanswered by default". This is that record for the ones that are
# NOT going in, so the next session does not re-derive it. Printed by --list.
NOT_PROMOTED = [
    # ── THE 2026-09-14 BACKLOG PASS, AND WHAT THE COUNT GOT WRONG FIRST ─────
    # The gap was reported as "23 of 64 check-shaped tools have no recorded
    # decision". Cross-referencing against tooling_inventory.classify() cut it
    # to 14: EIGHT of those tools are already wired MORE strongly than
    # report-only -- six BLOCKING (employee_auth_guard_check.py,
    # preauth_oracle_check.py, redaction_check.py, sairn_load_state_check.py,
    # sairn_reachability_check.py, sairn_seam_check.py), one REPORT-ONLY via a
    # PostToolUse hook (html_script_check.py) and one ADVISORY via SessionStart
    # (session_lock_check.py). "We decided not to promote this to report-only"
    # is a meaningless sentence about a tool that already blocks a push, so
    # they get no entry: their wiring IS the decision.
    #
    # That is the same mistake not_promoted() above records being made twice in
    # this file already -- a number that overstated the gap because a source of
    # truth existed and was not read. Third time, so it is written here beside
    # the entries rather than only in a work log.
    #
    # EACH ENTRY BELOW IS A DECISION, NOT A BATCH. Where the reason was already
    # written down in the tool's own PURPOSES line, this transcribes it into the
    # register that can be queried by tool name; where a genuinely new judgement
    # was needed and I could not responsibly make it for somebody else's tool,
    # the entry NAMES THE SPECIFIC BLOCKER instead of guessing. A uniform reason
    # across fourteen tools would be a bulk promotion wearing individual
    # clothes.
    ('accepted_risk_scan.py', 'A READ-LIST WHOSE COUNT IS NOT A SCORE, and its own '
     'PURPOSES line says so: it reads language, not intent, and scored roughly 1 in 3 '
     'on its first weight-3 run. Promoting it would print a list of comments on every '
     'push whose correct length is NOT zero -- zero would mean somebody deleted the '
     'comments that record accepted risks. A report-only entry implies a number to '
     'drive down; this tool has no such number. It belongs where it is, run when the '
     'accepted-risk register is reviewed.'),
    ('tier_a_bypass_check.py', 'SAME SHAPE, and again its own line already says it: a '
     'read-list, not a number to drive to zero. Its interesting column is COULD NOT '
     'TELL -- it cannot see whether a refusal runs BEFORE the write, and naming a '
     'Tier A resource is not writing to one. A push gate needs a verdict; this tool '
     'deliberately produces three states of which the middle one is the useful one. '
     'Promote it only if the GATED column ever becomes a real clearance rather than '
     '"an identity check and a refusal both appear in this file".'),
    ('fmea_prediction_check.py', 'IT REFUSES TO BE QUOTED BARE, which is exactly what a '
     'registry entry would do to it. It prints NO-DRAFT first and carries DO NOT QUOTE '
     'THIS ALONE beside the drafted-only figure, because a hit rate over the subset '
     'somebody happened to draft an FMEA for is not a hit rate. Promotion would put '
     'the unqualified number on every push, which is the one presentation the tool was '
     'built to prevent. It is run by the FMEA loop when a register record is added, '
     'which is the moment its answer can change.'),
    # ── RECORDED BY ITS OWN AUTHOR, 2026-09-15 ────────────────────────────────
    # CC found this tool had no recorded decision and correctly REFUSED TO GUESS
    # at another author's intent. That refusal is the right default and it is
    # why this entry exists rather than a plausible sentence written by somebody
    # else -- a decision register filled in by inference is a register of
    # inferences.
    ('entitlement_freshness_check.py',
     'ITS CURRENT OUTPUT IS A KNOWN-OPEN STATE THAT A PUSH CANNOT CHANGE, the same '
     'reasoning as copy_exactly_check.py below. It exits 1 today because `plan`, '
     '`trial_ends_at`, `stripe_subscription_id` and their neighbours have readers '
     'across api/_lib/license.js, api/_lib/sd-store.js, api/sd-data.js and '
     'api/sd-render.js and NO IN-REPO WRITER. That is not a defect somebody '
     'introduced and it is not fixable by editing this repo: THE WRITER IS STRIPE, '
     'and the whole point of item 100 is that the remedy must not depend on the '
     'counterparty. Wiring it report-only would print the same unchanging block on '
     'every push by every session until a revocation path is BUILT -- a notice '
     'whose content cannot vary with what a push did, which is how a gate gets '
     'read past and then ignored. '
     'IT IS NOT UNWIRED: it is SUITE-ONLY and runs with '
     'tools/entitlement_freshness_control.py, so its criteria are exercised and '
     'its sabotage is verified on every suite run. What is being declined is '
     'PROMOTION TO REPORT-ONLY, not execution. '
     'PROMOTE IT THE DAY A REVOCATION PATH EXISTS -- an in-repo writer that can '
     'clear an entitlement without Stripe cooperating -- because that is the day '
     'its answer starts varying with what the code does, and the day a regression '
     'in it would be a real finding rather than a restatement of a known gap. '
     'Until then the right home for the gap is the open-work index, where a '
     'standing unbuilt thing belongs, and not a per-push notice.'),
    ('copy_exactly_check.py', 'ITS CURRENT OUTPUT IS A KNOWN-OPEN STATE, not a finding: '
     '0 of 5 identical on 2026-09-14, with 4 differing because the APP was fixed and '
     'the must-copy-exactly DOCUMENT was not. Wiring it now means four rows on every '
     'push until somebody updates the document -- a notice whose content cannot change '
     'by pushing. Promote it the day the documented block and the app agree, because '
     'that is the day its output starts varying with what a push actually did. Note '
     'its own caveat too: it does NOT answer disciplines item 7, since agreeing bytes '
     'are precisely what that section warns is not safety.'),
    ('tier_a_replaceability_check.py', 'ITS INPUTS ARE THE REGISTER AND THE '
     'REGISTRY, NOT THE PUSH, so a push-time entry would print the same seven '
     'sc_* names on every push regardless of what the push contained. The two '
     'counts move when a TIER changes or a VERB GRANT changes, neither of which '
     'happens often and neither of which a push-time notice would surface any '
     'sooner than the probe does. AND IT IS NOT A NUMBER TO DRIVE TO ZERO: a '
     'hard delete verb is a decision, not a defect -- the SAIRNcode live probe '
     'depends on that verb to clean up after itself. What it reports is that '
     'the decision was never made per RESOURCE. Read it when a tier is assigned '
     'or a delete verb is granted, which is when its answer can change. Its own '
     'weaker half (how many Tier A evidence cells mention recoverability) reads '
     'LANGUAGE and says so on every run; promoting that to a push-time figure '
     'would turn a documentation-coverage number into an apparent defect count, '
     'which is the presentation the tool is written to prevent.'),
    ('pinned_list_drift_check.py', 'A READ-LIST WHOSE CORRECT LENGTH IS NOT ZERO, '
     'the same shape as accepted_risk_scan.py above and for the same reason. It finds '
     'literal lists of resource names that are a PARTIAL cover of an app Tier A set -- '
     'the shape that hid sc_denial_events behind a hand-written gate of six while the '
     'register said seven. On its first run it produced TWELVE rows and exactly ONE was '
     'a defect; the other eleven are partial on purpose with the reason written beside '
     'them, and two are already pinned to a BETTER population than Tier A by a test it '
     'cannot see. Promoting it would print eleven correct lists on every push forever, '
     'which is how a notice stops being read. Its input is the register and the '
     'registry rather than the push, so the answer changes when a TIER changes and not '
     'when code does. Run it when a tier is assigned or a gate list is written, and '
     'read docs/2026-09-15-pinned-list-drift-sweep.md for the triage of the current '
     'rows so the next reader does not redo it.'),
    ('defect_budget.py', 'ITS INPUT IS THE REGISTER, NOT THE PUSH, so a push-time entry '
     'would print the same five over-budget rules on every push regardless of what the '
     'push contained -- the definition of a notice people stop reading. It ranks which '
     'STANDING RULE has bitten often enough that its next occurrence is predictable '
     '(1.1 seventeen times, 1.5 fourteen, 1.11 ten as of 2026-09-15, over 77 records), '
     'and that ranking changes when a RECORD is added, not when code changes. Same '
     'cadence shape as sabotage_control_check.py above: measured periodically, read by '
     'a person, never gating. AND GATING IT WOULD BE ACTIVELY HARMFUL, which is the '
     'reason that matters rather than the noise: a number somebody is pushed to drive '
     'down rewards NOT CITING A RULE, and `--rule not-citable` exists precisely so a '
     'record can decline honestly. 14 of the 77 records decline today. Run it when the '
     'defect register is reviewed, or before choosing which control to build next, '
     'which is the decision it exists to change.'),
    ('sabotage_control_check.py', 'A BURN-DOWN, AND A BURN-DOWN IS NOT A PASS/FAIL. It '
     'measures how many of THIS REPO\'S OWN negative controls verify that their '
     'sabotage applied -- 16 of 39 when it was written, 20 of 30 later the same week. '
     'That figure moves as other people fix their probes, so a push-time entry would '
     'report somebody else\'s unfinished work as this push\'s finding, on every push, '
     'for weeks. It is the meta-checker equivalent of the flaky-checker ledger and '
     'wants the same treatment: measured on a cadence, read by a person, never gating.'),
    ('checker_control_check.py', 'THE SAME META-CHECKER SHAPE, one level out: it asks '
     'whether every promoted checker has a plant-defect/plant-clean control pair. 31 '
     'test files reference it, which is the tell -- it is infrastructure the suite uses '
     'to judge other tools, not a check on the codebase. Its finding is always "these '
     'N tools still lack a pair", which is a project state rather than a property of '
     'the diff in front of it. Promoting it would make every push report the backlog '
     'it is measuring. Related and deliberately separate: the two EXPIRED '
     'checker-control-registry claims (fourth, 33-53h ago) are the burn-down itself.'),
    ('cron_liveness_check.py', 'IT MAKES A LIVE NETWORK REQUEST, which is the same '
     'reason waf_rule_check.py and sairn_app_map_check.py are already held out on this '
     'list. Its whole subject is whether a scheduled job actually fired, so the network '
     'half is not incidental to it -- there is nothing useful left if you remove it. A '
     'push gate that talks to the outside world makes every push depend on the outside '
     'world being up, and this repo has already recorded what a network-dependent gate '
     'costs when a 403 gets swallowed. It does carry a real three-state exit, so the '
     'blocker is the network dependency alone, not the contract.'),
    ('stonedesk_storefront_live_check.py', 'LIVE BY NAME AND BY DESIGN -- it probes the '
     'deployed StoneDesk storefront. Same network reasoning as cron_liveness_check.py '
     'above, and with one addition specific to it: its correct answer today is that '
     'those tables are NOT provisioned, confirmed by two sources sharing no mechanism '
     '(absent from a schema capture AND answering 503 NOT_PROVISIONED live). A gate '
     'reporting a correct, expected, unchanging 503 on every push teaches people to '
     'skip its output. Run it when the storefront is actually provisioned.'),
    ('schema_provisioning_check.py', 'NEEDS THE LIVE DATABASE, which no clone can '
     'reach: the question it answers is whether a table declared in sql/ exists on the '
     'real instance. That is the same human-relay dependency docs/SOUP and the schema '
     'snapshot already carry -- a person runs a query in the Supabase editor and pastes '
     'the result. A registry entry would therefore report COULD NOT RUN on every push '
     'for reasons no push can fix, which is a log line rather than a check. Promote it '
     'if a read-only credential is ever available to CI.'),
    ('idempotency_check.py', 'NOT REJECTED -- BLOCKED, and the blocker is specific: it '
     'reaches the network, and unlike the two LIVE tools above that dependency looks '
     'removable rather than essential. It already has a FIXTURES block, so the blind '
     'lock is in place. What it needs before promotion is the network half separated '
     'from the static half so the static half can run offline and report a real verdict '
     'instead of COULD NOT RUN. That is a code change with an owner, not a decision, '
     'and it is deliberately not made here because narrowing somebody else\'s checker '
     'to make it promotable is how a criterion gets loosened to produce a number.'),
    ('independence_check.py', 'BLOCKED ON A CONTROL PAIR, which is the one thing that '
     'cannot be waived. It has FIXTURES and no probe anywhere under tests/ references '
     'it, so nothing has ever made it fail on purpose -- and this repo\'s own record is '
     'that literal_drift_check.py was promoted with `verdict: by_exit` and no sys.exit '
     'in it, and checkblocks.py exited 0 for months, both of which a control pair would '
     'have caught on day one. Write tests/run_independence_probe.py with both '
     'directions and a CONTROLS_FOR line, then this is a promotion candidate rather '
     'than a judgement call.'),
    ('restore_coherence_check.js', 'THE BLOCKER I NAMED WAS WRONG, AND THE REAL ONE IS DIFFERENT. Corrected 2026-09-14 after reading the probe instead of the tool description. I wrote that this needs the network, so a gate carrying it would make every push depend on the outside world. BOTH HALVES OF THAT ARE FALSE: tests/run_restore_coherence_probe.js already spins up an http.createServer on 127.0.0.1:0, points SAIRN_TARGET_URL at it and passes 26 arms, so measuring this tool needs no external network at all; and with no target the tool already exits 2 -- COULD NOT RUN, with the words "nothing was checked, and that is not the same as nothing being wrong" -- so a report-only entry would print an honest could-not-run rather than a failure or a network call. TARGET_URL is a plain env var and every read goes through one fetch helper, which is why the mock was easy. **I asserted a blocker from the tool\'s description without checking whether it was true, inside the triage whose entire purpose was to replace vague blockers with specific ones.** Recorded rather than reworded. THE REAL BLOCKER IS THAT ITS SUBJECT DOES NOT EXIST AT PUSH TIME. There is no restored database to point at on an ordinary push; the tool is for the hand restore somebody performs at 3am from whatever copy exists, which its own header states. Pointing it at production instead would check production\'s own audit chain -- a different question, and one that WOULD make every push talk to the live database. So a registry entry would report could-not-run on every push for a reason no push can fix, which is a log line rather than a check. That is the same reasoning schema_provisioning_check.py is held out under, and unlike the network claim it is verified: `node tools/restore_coherence_check.js` with no env set exits 2 today. PROMOTE IT if a restore ever becomes a scheduled, pointable-at artefact -- on Supabase free tier there are no automated backups, which is why there is nothing to point at.'),
    ('shape_antipattern_check.py', 'TRACK RECORD PENDING, AND THAT IS THE AUTHOR\'S OWN '
     'STATED DECISION rather than mine -- its index row says "report-only and '
     'deliberately NOT registered, because promotion is earned on a track record". '
     'Recorded here so the decision is queryable by tool name instead of living only '
     'in a prose row. It is well prepared: FIXTURES, a three-state exit, and a real '
     'control pair in tests/run_shape_antipattern_probe.py. What it lacks is runtime: '
     '12 S1 and 2 S3 findings of which 5 were hand-verified, so 9 are still unread. '
     'Promote it once those are triaged and its steady state is silence.'),
    ('three_way_match_check.py', 'SAME TRACK-RECORD HOLD, and it is the closest of the '
     'fourteen to ready: three-state exit, a declared control pair in '
     'tests/run_three_way_match_probe.py. It has no FIXTURES block, which is the one '
     'gap worth naming rather than waiving -- convention 1 wants the criteria locked '
     'against synthetic cases before real data, and this checker judges MONEY (a '
     'purchase order, a receipt and an invoice agreeing). A money checker promoted '
     'without a blind lock is the combination this platform has least appetite for. '
     'Add the fixtures and it is a promotion candidate.'),
    ('ai_prompt_refusal_check.py', 'ITEM 8, sub-item 7, the no-model-call half. HELD '
     'BACK DELIBERATELY AND THE REASON IS ITS OWN OUTPUT: all four of its current '
     'findings need a human triage decision that has not been made, and one of them '
     '(sairnfreedom bottle-fullness: image in, two-key JSON out) looks DEFENSIBLE '
     'rather than wrong. A runner entry today would print the same four rows on every '
     'push, three of them awaiting somebody who owns SAIRNlaw and one of them arguably '
     'correct as it stands -- which is how a report stops being read. Promote it once '
     'the four are triaged and its steady state is silence. Note also what it CANNOT '
     'say, because a registry entry would imply otherwise: it checks that refusal '
     'WORDS ARE PRESENT in a prompt and cannot show the model obeys them; that half '
     'needs a model call and is deferred by Michael\'s recorded garak decision. Held '
     'by tests/run_ai_prompt_refusal_probe.py, 12 fixtures and 5 mutation controls.'),
    ('pra_event_tree.py', 'ITEM 84. It is an ANALYSIS, not a check: it enumerates which '
     'end state each component failure reaches and has no notion of a finding to report '
     'or a pass to give. Wiring it into a runner would print the same 20-row tree on '
     'every push, which is how a report stops being read. It is run when the SPOF '
     'register or the secrets inventory changes -- both of which ARE checked '
     'mechanically -- and its own inputs are what change its answer. Held by '
     'tests/run_pra_event_tree_probe.py.'),
    ('reliability_growth.py', 'ITEM 80, and it must not be promoted while it REFUSES. '
     'Its verdict today is exit 1 on all three admissibility criteria, and a runner '
     'entry would report that on every push for weeks -- a notice whose content cannot '
     'change until somebody records effort per interval or enough time passes. Promote '
     'it the day the gate ADMITS, because that is the day its output starts varying. '
     'The fitters are proven against synthetic curves with known parameters, so the '
     'refusal is a statement about the data rather than about a fitter nobody has seen '
     'work; held by tests/run_reliability_growth_probe.py.'),
    ('entity_baseline_readiness.py', 'ITEM 51, and it must not be promoted while '
     'its answer cannot change on a push. It exits 1 -- NOT READY -- and will keep '
     'doing so until the register grows by roughly a factor of three on the `app` '
     'dimension, which is months of sessions away, so a runner entry would print '
     'the same notice on every push until nobody read it. That is the same argument '
     'already recorded for reliability_growth.py above. THE REASON IT IS A TOOL AT '
     'ALL is that item 51 had been measured BY HAND twice -- 2026-09-14 at 68 '
     'records and 2026-09-15 at 77 -- and both times the answer was NOT YET, which '
     'is a claim with an expiry date that nothing was watching. Promote it the day '
     'it exits 0, because that is the day its output starts varying and the day a '
     'baseline becomes worth building. AND ONE OF ITS REFUSALS WILL NEVER CLEAR BY '
     'WAITING: `layer` already clears the record bar and is still not ready, because '
     'product/tooling/test is a classification and not a surface, so there is no '
     'exposure to divide by; held by tests/run_baseline_readiness_probe.py.'),
    ('benford_check.py', "ITEM 57, AND THE DECISION IS THE TOOL'S OWN. Its bare run "
     'exits 2 -- COULD NOT RUN -- and that is CORRECT rather than a defect: the '
     'production question needs `--data <export>`, and ledger_entries, ledger_lines '
     'and the StoneDesk invoice and quote amounts live in the database where nothing '
     'in this repo can read them. The only corpora it CAN reach here are the seed '
     'and demo constants, which are OPENLY INVENTED -- stonedesk.html alone carries '
     '29 SEED blocks -- so its one finding (seed:stonedesk.html, first-digit MAD '
     '0.0260, n=219) is the instrument proving it fires, not a finding about '
     'production. Wiring that into a runner would print a could-not-run notice and '
     'a known-expected finding on every push for ever, which is how a notice stops '
     'being read -- the same argument already recorded for cleanup_residue_check.py '
     'above. AND IT MUST STAY A POINTER EVEN WHEN IT CAN RUN: Benford tendency is '
     'not proof in either direction, a conforming distribution is not evidence of '
     'honesty, and real datasets fail it innocently every day (a price list, a tier '
     'table, anything with a floor). Promote it the day somebody hands it a real '
     'export on a cadence -- and even then as report-only, never as a gate. '
     'Registered here on 2026-09-14 once the claim collision with Cody cleared; '
     'held by tests/run_benford_probe.py, which passes.'),
    ('cleanup_residue_check.py', 'it needs a LIVE licence key and a database '
     'reachable from this clone: run 2026-09-12 it exits 2, could-not-tell, with '
     '"CLEAN files, nothing to run". Wiring a tool that reports could-not-tell on '
     'every push trains people to ignore it, and its own output already says a '
     'clean result does NOT mean the file was run. Promote it the day it can tell '
     '"the rows are gone" from "I could not look".'),
    ('verify_review_gates.py', 'it takes a PLAN FILE and a ledger as arguments and '
     '**nothing in this repo references it at all** -- checked by grep across '
     'tools/, tests/, .claude/ and the docs, where the only mention was the old '
     'hand-written inventory claiming the push gate invoked it. It does not. The '
     'workflow it serves either never landed or is gone; deciding that is a '
     'separate call from wiring it, so it is recorded here rather than promoted or '
     'deleted.'),
    ('write_path_fault_scan.py', 'a POINTER, not a gate, and its own output says so '
     'on every run: "THIS IS NOT A LIST OF DEFECTS." Of the eight sites it flagged '
     'in sairngrounds, FIVE were safe, and of the six in stonedesk, FOUR were. '
     'Promoting it would put a standing 25-line report on every push whose entries '
     'are candidates to read. Same class as sairn_ai_fact_scan.py above and '
     'recorded for the same reason.'),
    ('sairn_ai_fact_scan.py', 'a READ-LIST, not a gate. Its own output says '
     '"every one is a candidate to READ, not a confirmed defect: a legitimate '
     'default (role || \'user\') and a fabricated one (city || \'Westlake\') are '
     'the same shape and only a human can tell them apart." 14 hits today.'),
    ('sairn_stale_snapshot_scan.py', 'says in its own output "do not treat this '
     'total as a score, and do not drive it to zero" -- a rising number can mean '
     'the code got better. A gate cannot be built on a number like that.'),
    ('sairn_dead_function_sweep.py', 'a research sweep: 99 dead functions today, '
     'and its own line is "verify each site by hand before deleting". C1 and C2 '
     'are opposite fixes and the caller list decides.'),
    ('sairn_reachability_probe.py', 'its header says "This is a PROBE, not a '
     'gate. It over-reports by construction ... so it prints its own caveat '
     'rather than a verdict."'),
    ('waf_rule_check.py', 'CLEAN today, and gate-shaped -- but it makes a LIVE '
     'API call, so a transient network failure would read as a finding on a '
     'push. That is the false alarm that gets a report-only checker switched '
     'off. Run it by hand, or promote it once it distinguishes "drifted" from '
     '"could not ask" the way the SQL preflight does.'),
    ('licence_recoverability_check.py, rf_claim_gate_live_probe.py, '
     'rf_roundtrip_probe.py, probe_public_book_guardian.py',
     'live probes needing a real licence and a network; correctly manual.'),
    ('sairnlaw_citation_audit.py, va_rule_currency.py, reclassification_sweep.py',
     'one-off audits against a point in time, not standing checks.'),
    ('missing_dom_target_check.py', 'its 137 findings are an OPEN, OWNED row '
     '(Fourth). Promoting it now would fire on every push against work already '
     'in progress.'),
    ('local_only_collection_check.py', 'its EXIT CODE is fixed and shipped -- 3 for could-not-tell, 1 only for a real finding -- but it still reports could-not-tell for sairncash.html and sairnroofing.html, so wiring it now means a notice on EVERY push. HAND-CHECKED: every localStorage.setItem in those two is device state (device id, subscription, trial, usage, licence fingerprint), so there is genuinely nothing to find -- the tool just cannot PROVE it. Classifying those five keys was tried and REVERTED: it broke two arms of tests/local_only_shape_probe.py, and changing a classifier to silence a notice is how a checker starts lying. Promote it when it can tell "nothing to find" from "nothing I can see".'),
    ('sairn_app_map_check.py', 'CLEAN, but it makes a LIVE HTTP request per app '
     'route -- same reason waf_rule_check.py is held out. Its network half is '
     'the point of the tool, so it wants a could-not-tell code before it can '
     'be wired, not just a promotion.'),
    ('trend_alarm.py', 'ITS OWN OUTPUT SAYS IT IS NOT ARMED, and wiring an '
     'unarmed measurement into a push notice would put a number in front of '
     'people that nothing has been tuned to interpret -- which is how a '
     'measurement becomes a threshold by habit. It is also SLOW by construction: '
     'the series are recovered from git history, 221 `git show` calls per run, '
     'about 14 seconds. Promote it when a labelled episode exists AND gains are '
     'recorded, which is the same gate the tool applies to itself.'),
    ('weakness_combination.py', 'IT REPORTS PAIRS AND REFUSES THE VERDICT, on '
     'purpose -- whether two accepted risks compound is a judgement about '
     'consequences. A push notice implies a number to drive to zero and the '
     'right number of shared-property pairs is not zero; a register of four '
     'risks that shared nothing would mean the register was too small, not that '
     'the platform was safe. Its one genuinely mechanical half -- whether a '
     'trigger claimed as MECHANICAL is watched by anything that runs -- COULD '
     'be promoted on its own, and should be split out first rather than '
     'promoting the judgement half alongside it.'),
]


def run_one(entry, show_all, verbose=False):
    tool = entry['tool']
    # ── ZERO TARGETS IS NOT A CLEAN SWEEP (2026-09-10) ──────────────────────
    # The subject list here is DERIVED from the thing being checked -- the app
    # files themselves -- which is the shape the self-referential-guard sweep
    # went looking for. When it came back empty the `for t in targets` loop
    # simply did not execute, findings stayed [], unrun stayed [], and the hook
    # printed nothing. Six of the twenty-one promoted checkers run in this mode
    # across 22 apps, so 132 checker runs could vanish and the report was
    # byte-identical to the report for a clean platform. Proved by forcing
    # app_files() to [] before it was fixed.
    #
    # A DELETED APP IS NOT WHAT THIS GUARDS, and that distinction is the whole
    # per-checker judgement the sweep exists to make: removing an app removes
    # the risk along with the check, and it is loud in a diff. What this guards
    # is the list going empty for a reason NOBODY CHOSE -- git failing, the
    # tool run from the wrong directory, a glob that stopped matching.
    try:
        targets = app_files(verbose) if entry['mode'] == 'apps' else [None]
    except Exception as e:                               # noqa: BLE001
        return [], ['%s -- the target list could not be built: %s' % (tool, e)]
    findings, unrun = [], []
    if not targets:
        return [], ['%s -- ZERO targets. Nothing was scanned, which is not the '
                    'same as nothing being wrong.' % tool]
    for t in targets:
        # `args` lets an entry run a tool in a specific MODE -- the matrix
        # is registered as `--check`, not as a regeneration, because a
        # report-only checker that WRITES is not report-only.
        cmd = ([sys.executable, os.path.join('tools', tool)]
               + list(entry.get('args', [])) + ([t] if t else []))
        try:
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
                               timeout=300)
        except Exception as e:                       # noqa: BLE001
            unrun.append('%s %s -- %s' % (tool, t or '', e))
            continue
        out = (r.stdout or '') + (r.stderr or '')
        # EXIT 3 IS "COULD NOT RUN", NOT A FINDING AND NOT A PASS -- the same
        # code check4_probe and run_all_tests.py use. Added 2026-09-10 with
        # nav_panel_check's SKIPPED path: without this it would land in
        # `findings` as the bare string "exit 3", which reads as a defect in
        # the app rather than as the checker failing to recognise it.
        if r.returncode == 3:
            why = next((l for l in out.splitlines() if l.startswith('SKIPPED')),
                       'SKIPPED')
            unrun.append('%s %s -- %s' % (tool, t or '', why.strip()))
            continue
        got, _ = entry['verdict'](r.returncode, out)
        for g in got:
            findings.append('%s %s -- %s' % (tool, t or '', g.strip()))
        if show_all and out.strip():
            print('    ' + out.strip().replace('\n', '\n    '))
    return findings, unrun


# The cap the hook actually runs under, READ FROM THE SETTINGS FILE rather
# than written down here. A second copy of a number is how the two drift, and
# this one decides whether the sweep completes at all.
def _hook_timeout():
    """The cap the hook really runs under, or None with the reason PRINTED.

    THE FIRST VERSION OF THIS SWALLOWED ITS OWN BUG. It called `io.open` in a
    module that does not import `io`, so every call raised NameError, the bare
    `except Exception: return None` caught it, and the fallback 300 looked like
    a correctly-read value -- while the settings file said 600. A silent except
    that produces a plausible default is the exact shape this sweep exists to
    report, written into the function whose whole purpose is to avoid keeping a
    second copy of the number. It says why now.
    """
    path = os.path.join(REPO, '.claude', 'settings.json')
    try:
        with open(path, encoding='utf-8') as fh:
            cfg = json.load(fh)
        for arr in cfg.get('hooks', {}).values():
            for m in arr:
                for h in m.get('hooks', []):
                    if 'report_only_checks.py' in h.get('command', ''):
                        return int(h.get('timeout', 0)) or None
    except Exception as e:                           # noqa: BLE001
        print('NOTE: could not read the hook timeout from %s (%s: %s), so the '
              'sweep budget below is a FALLBACK and may not match what the hook '
              'enforces.' % (path, type(e).__name__, e))
        return None
    print('NOTE: no report_only_checks.py hook entry found in %s, so the sweep '
          'budget below is a FALLBACK.' % path)
    return None


HOOK_TIMEOUT_SECONDS = _hook_timeout() or 300

# The sweep stops itself a little BEFORE the hook would kill it, so there is
# time to print what it never reached. `--budget N` overrides it, which is how
# the probe exercises the overrun path without waiting six minutes.
SWEEP_BUDGET_SECONDS = HOOK_TIMEOUT_SECONDS


def sweep(show_all=False, quiet=False):
    """Run every promoted checker, TIMING EACH ONE.

    THE TIMING IS NOT DECORATION. This sweep is wired as a PostToolUse hook
    with a 300-SECOND timeout in .claude/settings.json, and on 2026-09-13 it
    exceeded 600s in its own probe -- so it had already stopped completing in
    production, and the only visible symptom was a probe reporting a TIMEOUT
    as a failure. Without a per-checker number nobody can tell a sweep that
    grew from a checker that hangs, and the whole thing reads as one opaque
    duration. CC capped metamorphic_check for exactly this reason hours
    earlier and had to measure it by hand to do it.
    """
    findings, unrun, timings = [], [], []
    budget = SWEEP_BUDGET_SECONDS
    started = time.time()
    skipped = []
    for i, entry in enumerate(REGISTRY):
        # ── THE BUDGET IS SPENT: STOP AND SAY WHAT WAS NOT RUN ──────────────
        # A hook killed at its timeout reports NOTHING -- no partial result, no
        # list of what it never reached, and the only trace is somebody's probe
        # calling it a failure. Stopping ourselves converts a silent kill into a
        # STATED UNKNOWN, which is the whole difference between "clean" and "I
        # did not look". The remaining checkers are named, never just counted.
        if budget and (time.time() - started) >= budget * 0.9:
            skipped = [e['tool'] for e in REGISTRY[i:]]
            break
        if not quiet:
            print('-- %s --' % entry['tool'])
        _t0 = time.time()
        f, u = run_one(entry, show_all, verbose=not quiet)
        _el = time.time() - _t0
        timings.append((_el, entry['tool']))
        findings += f
        unrun += u
        if not quiet:
            print('   %d finding(s), %d could not run   %.1fs' % (len(f), len(u), _el))
    for tool in skipped:
        unrun.append('%s -- NOT RUN, the sweep reached its %ds budget first. '
                     'This is an UNKNOWN, not a clean result.' % (tool, budget))
    if not quiet and timings:
        total = sum(e for e, _ in timings)
        print('')
        print('SWEEP TOOK %.0fs of a %ss budget.' % (total, budget or 'n/a'))
        if skipped:
            print('')
            print('%d CHECKER(S) NEVER RAN, and that is the point of printing this:'
                  % len(skipped))
            for tool in skipped:
                print('    %s' % tool)
            print('A sweep that runs out of time reports an UNKNOWN for these, not')
            print('a clean pass. Raise the budget, or cap whichever checker below')
            print('grew -- but do not read the silence as nothing found.')
        print('Slowest, because a sweep that grew and a checker that hangs are')
        print('different problems and one number cannot tell them apart:')
        for el, name in sorted(timings, reverse=True)[:5]:
            print('  %6.1fs  %s' % (el, name))
    return findings, unrun


def hook_main():
    # THE PAYLOAD IS THE GATE, and it is checked HERE rather than trusted to
    # `.claude/settings.json`. A hook entry's only gate is `matcher`, which
    # matches the TOOL NAME -- an `"if"` key is ignored in silence, which on
    # 2026-09-09 ran the full mutating test suite after every Bash tool call.
    # A HOOK THAT LOOKS GATED IN CONFIG IS UNGATED UNTIL THE HOOK ITSELF
    # CHECKS. Same reasoning and the same imported matcher as run_all_tests.py.
    try:
        payload = json.load(sys.stdin)
    except Exception:                                # noqa: BLE001
        payload = {}
    cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''
    # An absent or unreadable payload falls through and runs: that is this file
    # invoked by hand with --hook, and it is the same fail-open standard the
    # other hooks here hold.
    if payload and not pushes(cmd):
        return 0
    # A DENIED PUSH IS NOT A PUSH -- added 2026-09-10, in the same pass that
    # added it to run_all_tests.py. PostToolUse fires whether or not the
    # command succeeded, so a push the PRE-tool gate refused still ran the
    # whole sweep. This repo denies pushes routinely, so that is not an edge
    # case. Fixed in BOTH copies deliberately: a fix verified on one of two
    # files that carry the same line is not verified, which is the lesson
    # tools/sairn_claim_hook.py taught on 2026-09-04.
    resp = payload.get('tool_response') or {}
    if isinstance(resp, dict) and resp.get('success') is False:
        return 0
    findings, unrun = sweep(quiet=True)
    if not findings and not unrun:
        return 0
    lines = []
    if findings:
        lines.append('%d report-only finding(s) after this push:' % len(findings))
        lines += ['  ' + f for f in findings[:12]]
    if unrun:
        lines.append('%d checker(s) COULD NOT RUN, so they verified nothing:'
                     % len(unrun))
        lines += ['  ' + u for u in unrun[:6]]
    lines.append('Run `python tools/report_only_checks.py` for the whole picture.')
    lines.append('REPORT ONLY -- this hook never blocks a push. These checkers '
                 'are on the same promotion path as push-gate checks 5 and 7: '
                 'blocking only once each has been quiet in practice.')
    print(json.dumps({
        'systemMessage': 'Report-only checkers: %d finding(s), %d unrun.'
                         % (len(findings), len(unrun)),
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': '\n'.join(lines),
        },
    }))
    return 0


def main(argv):
    # `--budget N` overrides the sweep's stop-before-the-hook-kills-us cap.
    # It exists so the overrun path is TESTABLE in seconds instead of only
    # reproducible by waiting for the real six-minute run to grow past 300s.
    if '--budget' in argv:
        globals()['SWEEP_BUDGET_SECONDS'] = float(argv[argv.index('--budget') + 1])
    if '--hook' in argv:
        return hook_main()
    if '--list' in argv:
        for e in REGISTRY:
            print('%-32s promoted %s (%s)' % (e['tool'], e['promoted'], e['mode']))
            print('    catches : %s' % e['catches'])
            print('    matters : %s' % e['why_it_matters'])
            print('    evidence: %s' % e['evidence'])
        print('')
        print('DELIBERATELY NOT PROMOTED (%d) -- the decision, recorded once:'
              % len(NOT_PROMOTED))
        for tool, why in NOT_PROMOTED:
            print('  %s' % tool)
            print('      %s' % why)
        return 0
    findings, unrun = sweep(show_all='--all-sections' in argv)
    print('')
    if unrun:
        print('COULD NOT RUN (%d) -- not a pass:' % len(unrun))
        for u in unrun:
            print('    %s' % u)
    if findings:
        print('FINDINGS (%d):' % len(findings))
        for f in findings:
            print('    %s' % f)
        print('')
        print('REPORT ONLY. Nothing here blocked anything. Read each one before '
              'acting -- these checkers have run against real code exactly once.')
    elif unrun:
        # NOT CLEAN. It said "CLEAN -- 35 promoted checker(s), no findings" over
        # a run where 33 of them never executed, which is the exact sentence
        # this whole file exists to stop anybody writing. A sweep that did not
        # look cannot report nothing found.
        print('NOT CLEAN and NOT a finding either: %d of %d promoted checker(s) '
              'did not run, so this is an UNKNOWN.' % (len(unrun), len(REGISTRY)))
    else:
        print('CLEAN -- %d promoted checker(s), no findings.' % len(REGISTRY))
    return 1 if (findings or unrun) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
