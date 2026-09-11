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
    its UNRUN section.
    """
    r = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                       capture_output=True, text=True)
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
        'why_it_matters': 'CLAUDE.md records that a GENERATED artefact which '
                          'must be regenerated after every edit reproduces the '
                          'silent-failure shape it exists to catch. This is the '
                          'document an outside auditor would read, so it going '
                          'quietly stale is the worst version of that',
        'evidence': 'built and wired the same day: 21-check probe including the '
                    'one that matters -- add a GUARD_TESTS entry and --check '
                    'goes RED, regenerate and it agrees again',
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
        'promoted': '2026-09-10, the day it was built',
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
                    'first draft of the finding had that wrong',
    },
]

# ── DELIBERATELY NOT PROMOTED, AND WHY ──────────────────────────────────────
# `docs/2026-09-09-tooling-inventory.md` says the decision each unwired checker
# needs is blocking / report-only / deliberately manual, "recorded once rather
# than left unanswered by default". This is that record for the ones that are
# NOT going in, so the next session does not re-derive it. Printed by --list.
NOT_PROMOTED = [
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
]


def run_one(entry, show_all, verbose=False):
    tool = entry['tool']
    targets = app_files(verbose) if entry['mode'] == 'apps' else [None]
    findings, unrun = [], []
    for t in targets:
        # `args` lets an entry run a tool in a specific MODE -- the matrix
        # is registered as `--check`, not as a regeneration, because a
        # report-only checker that WRITES is not report-only.
        cmd = ([sys.executable, os.path.join('tools', tool)]
               + list(entry.get('args', [])) + ([t] if t else []))
        try:
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
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


def sweep(show_all=False, quiet=False):
    findings, unrun = [], []
    for entry in REGISTRY:
        if not quiet:
            print('-- %s --' % entry['tool'])
        f, u = run_one(entry, show_all, verbose=not quiet)
        findings += f
        unrun += u
        if not quiet:
            print('   %d finding(s), %d could not run' % (len(f), len(u)))
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
    else:
        print('CLEAN -- %d promoted checker(s), no findings.' % len(REGISTRY))
    return 1 if (findings or unrun) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
