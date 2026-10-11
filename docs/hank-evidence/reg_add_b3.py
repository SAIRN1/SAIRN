# -*- coding: utf-8 -*-
"""Batch-19 defect-register records, appended THROUGH THE TOOL.

RULE F: the shas come in on the command line, AFTER the final rebase, because a
rebase rewrites them and a record whose `commit` resolves to nothing is the
vacuous row this register exists to prevent.

docs/defect-density-register.json is in CODY'S live FILES. It is APPENDED to only
via tools/defect_register.py --add; neither it nor the tool is edited.
"""
import json
import subprocess
import sys

REPO = r'C:\Users\marsh\Documents\SAIRN-hank'
SHA_STATUS = sys.argv[1]      # the cron/audit status-doc fix
SHA_SWEEP = sys.argv[2]       # the widened bare-run detector

RECS = []

RECS.append(dict(
    commit=SHA_STATUS, app='tooling', layer='tooling', severity='high',
    method='code-review', phase='design', phase_confidence='stated',
    summary=(
        'tools/cron_liveness_check.py and tools/audit_checkpoint_status.py '
        'DESTROYED A GOOD RECORD whenever CRON_SECRET was absent. Measured '
        '2026-10-07: a bare run in a clone without the secret REPLACED a real OK '
        'in docs/CRON-LIVENESS-STATUS.md -- four cron jobs, all ok, measured '
        '09:18:44Z -- with COULD NOT TELL, and nothing anywhere recorded that an '
        'OK had ever existed. The same path overwrote '
        'docs/AUDIT-CHECKPOINT-STATUS.md. Both exited 2 CORRECTLY, after writing. '
        'THE REASONING BEHIND IT WAS SOUND AND THE SCOPE WAS WRONG: "say so '
        'rather than keeping a stale OK" is right when the tool ASKED and could '
        'not get an answer -- a 401, a timeout, an unparseable body are facts '
        'about the subject -- and wrong when it could not ask at all. A missing '
        'environment variable is a fact about the CLONE, and five of the six '
        'clones on this box do not carry CRON_SECRET, so every sweep that drove '
        'every tool bare erased the record again.'),
    rule='1.11',
    rule_note=(
        'ARGUABLE AND INVERTED. 1.11 is about a could-not-run reported as a pass. '
        'This is a could-not-run reported LOUDLY AND CORRECTLY while destroying '
        'the last real answer on its way out. The exit code was never wrong; the '
        'side effect was. That inversion is why the fix is a FOURTH exit code '
        'rather than a change to the message, and why it is also the first cited '
        'instance of RULE G (routed in docs/2026-10-07-hank-routed.md section 4): '
        'test and probe infrastructure must not mutate the state it runs in.'),
    injection_unknown=(
        'Both tools have written their status document on every path since they '
        'were written; there is no commit that removed a guard. The behaviour was '
        'deliberate and documented in the tools themselves, which is why no '
        'review caught it -- it reads as a feature until you notice which of the '
        'two could-not-tell states it is applied to.'),
    factors=[
        dict(kind='technical',
             factor=('The missing-credential path called write_status() before '
                     'returning the could-not-run code, so the document was '
                     'already overwritten by the time the exit code was chosen.'),
             action_status='done',
             action=('EXIT_NO_SECRET = 3 in both tools. That path now writes '
                     'NOTHING and says so: "NOTHING WAS WRITTEN. <doc> is '
                     'UNCHANGED and still holds whatever the last run that COULD '
                     'ask recorded." Every OTHER could-not-tell path is '
                     'unchanged and still records COULD NOT TELL, because those '
                     'ran.')),
        dict(kind='process',
             factor=('A rule written for one state was applied to a second state '
                     'that looked like it -- "could not get an answer" and "could '
                     'not ask" were treated as one thing.'),
             action_status='done',
             action=('The distinction is now carried by the exit code itself, so '
                     'the two states cannot be collapsed again without deleting '
                     'a constant. This is RULE E (a refusal is scoped to the case '
                     'that justified it) arriving from the other direction.')),
        dict(kind='detection',
             factor=('Nothing compared a status document before and after a tool '
                     'ran. tools/bare_run_write_check.py checks the REPO, and '
                     'these documents ARE in the repo -- but both tools are in '
                     'the bare_run_writers.py allowlist as INTENDED writers, so '
                     'the one check that could have seen it was exempting them.'),
             action_status='done',
             action=('tests/run_status_doc_secret_probe.py: four arms per tool '
                     '(exit 3 not 2; the document BYTE-IDENTICAL; the output says '
                     'nothing was written; a planted sentinel survives) plus '
                     'THREE SABOTAGE ARMS per tool that restore the old '
                     'behaviour in a copy and prove arms A and B would have '
                     'failed on it. Driven in a synthetic sandbox, so the real '
                     'documents are untouched by the probe itself.')),
    ],
    recurrence_open=(
        'THE ALLOWLIST STILL EXEMPTS BOTH TOOLS and that is still correct -- with '
        'a secret set they do write their document. So the general case is open: '
        'nothing stops a DIFFERENT declared writer from overwriting its declared '
        'path with a could-not-tell. The probe pins these two tools by name, not '
        'the class. And the other could-not-tell paths (401, timeout, unparseable '
        'body) still overwrite a dated OK by design -- a defensible choice that '
        'nobody has re-examined.')))

RECS.append(dict(
    commit=SHA_SWEEP, app='tooling', layer='tooling', severity='moderate',
    method='code-review', phase='design', phase_confidence='stated',
    summary=(
        'tools/bare_run_write_check.py -- the tool built to catch a bare run that '
        'mutates -- could not see any write OUTSIDE the working tree, and three '
        'real mutations lived there. It compared `git status` only. So '
        'tools/session_lock_check.py acquiring a session lock in '
        '~/SAIRN-SESSION-LOCKS on a bare run was reported CLEAN; a `git config` '
        'write from inside a linked worktree landing in the owning clone\'s '
        'SHARED .git/config was reported CLEAN (that is how core.bare=true '
        'reached a live working clone); and a tool registering a worktree and '
        'leaving it registered was reported CLEAN. THE SCOPE WAS THE DEFECT, NOT '
        'THE COMPARISON.'),
    rule='1.11',
    rule_note=(
        'ARGUABLE. The collapse here is not pass-vs-could-not-run but '
        'CLEAN-vs-NOT-LOOKED-AT: every tool outside the watched scope was '
        'reported as not writing, which is the same shape as a check reporting a '
        'pass it never performed. Cited as 1.11 with that difference stated '
        'rather than stretched. The general statement is RULE G, routed in '
        'docs/2026-10-07-hank-routed.md section 4.'),
    injection_unknown=(
        'The tool has compared `git status` since it was written. Nothing removed '
        'a wider scope -- it never had one, because the shared-state write was '
        'not known about when the tool was built.'),
    factors=[
        dict(kind='technical',
             factor=('The only comparison was `git status --porcelain`, which by '
                     'construction cannot see ~/SAIRN-SESSION-LOCKS, '
                     '.git/config or the worktree registration list.'),
             action_status='done',
             action=('A shared_snapshot() over all three, diffed before and '
                     'after every bare and --help run, reported in its own '
                     'WRITES(SHARED) column and NEVER exempted by the '
                     'allowlist -- bare_run_writers.py declares REPO paths and '
                     'reading its silence as permission is how the gap stayed '
                     'open.')),
        dict(kind='detection',
             factor=('The tool had no selftest for the half it was missing, so '
                     'there was nothing that could have gone red.'),
             action_status='done',
             action=('--selftest with 8 arms: a created/edited/deleted lock, a '
                     'git config write, a worktree registration, THE PAIRED '
                     'NEGATIVE (nothing planted, nothing reported) and an '
                     'END-TO-END arm where a planted tool writes a lock on a '
                     'bare run and is caught with exit 0 and a clean git '
                     'status -- exactly the combination that was invisible. '
                     'SAIRN_LOCKS_DIR redirects the watched registry so the real '
                     'one is never written to, and run_tool propagates it to '
                     'every child, because a detector that needs the caller to '
                     'remember two variables is one somebody runs with only '
                     'the first.')),
        dict(kind='latent-condition',
             factor=('The repo-shaped assumption is everywhere: the lock '
                     'registry is deliberately OUTSIDE every clone so it is '
                     'current without a fetch, and that same property makes it '
                     'invisible to every repo-scoped check.'),
             action_status='planned',
             action=('Named in docs/handoff-hank-2026-10-08.md. Whether other '
                     'checks need the same widening is not decided here; this '
                     'one tool was widened and the principle was routed as '
                     'RULE G.')),
    ],
    recurrence_open=(
        'THE WATCHED LIST IS HAND-KEPT -- three locations, chosen because three '
        'real incidents named them. A fourth kind of shared state (a cache under '
        '~/.claude, a file on the Drive mount) is still invisible, and nothing '
        'derives the list from anything. The sweep is also NOT A GATE: it ran '
        'once by hand over 164 tools at a 25s bound, 19 of which had no verdict '
        'at all, and nothing re-runs it.')))

def main():
    worst = 0
    for r in RECS:
        argv = [sys.executable, 'tools/defect_register.py', '--add',
                '--commit', r['commit'], '--app', r['app'],
                '--layer', r['layer'], '--severity', r['severity'],
                '--method', r['method'], '--summary', r['summary'],
                '--rule', r['rule'], '--rule-note', r['rule_note'],
                '--phase', r['phase'],
                '--phase-confidence', r['phase_confidence'],
                '--injection-unknown', r['injection_unknown'],
                '--factors', json.dumps(r['factors']),
                '--recurrence-open', r['recurrence_open']]
        p = subprocess.run(argv, cwd=REPO, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
        print('=== %s exit=%d' % (r['commit'], p.returncode))
        print(p.stdout.decode('utf-8', 'replace').strip()[:900])
        if p.returncode:
            worst = p.returncode
    return worst


if __name__ == '__main__':
    sys.exit(main())
