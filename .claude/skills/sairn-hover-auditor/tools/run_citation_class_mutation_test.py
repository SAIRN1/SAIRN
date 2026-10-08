#!/usr/bin/env python
"""Mutation test for citation_class_check.py (2026-09-30, item 3 of the
directed queue): copy the real log, inject 20 KNOWN-WRONG citations spread
across all five decidable classes, and confirm the classifier flags every
one exactly as planted. A miss is a defect in the TOOL, reported by name.

'Known-wrong' here means known-CLASS: each injected entry is constructed
so its true class is certain by construction (real files, real recorded
blob shas from the live repo, lines chosen against the actual content).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import citation_class_check as cc  # noqa: E402

REPO = cc.REPO


def sha_of(path):
    r = subprocess.run(['git', 'rev-parse', 'HEAD:' + path], cwd=REPO,
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def old_sha_of(path, back=30):
    r = subprocess.run(['git', 'rev-parse', 'HEAD~%d:%s' % (back, path)],
                       cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def main():
    # Anchor facts derived live, never assumed: leadTime() sits at
    # api/_lib/job-risk.js:65 at HEAD (verified this session), and the file
    # is unchanged for weeks, so HEAD's blob is also a valid derivation sha.
    jr = 'api/_lib/job-risk.js'
    jr_sha = sha_of(jr)
    if not jr_sha:
        print('COULD NOT RUN: cannot resolve %s at HEAD' % jr)
        return 2
    # an OLD stonedesk blob -- stonedesk.html moves constantly, so a
    # 30-commits-ago blob plus a line correct THEN and moved NOW gives a
    # certain MOVED-SINCE... but 'correct then' must be derived, not
    # guessed: find a line in the old blob carrying a stable anchor.
    sd = 'sairnfreedom.html'
    # the blob BEFORE the last commit that touched this file -- stonedesk
    # turned out identical across 200 commits, so the moved-since plant
    # derives its pre-move blob from the file's own change history instead
    # of a fixed depth (the fixed-depth assumption was this test's own
    # first COULD-NOT-RUN).
    prev_commits = subprocess.run(
        ['git', 'log', '--format=%H', '-2', '--', sd], cwd=REPO,
        capture_output=True, text=True).stdout.split()
    sd_old = None
    if len(prev_commits) >= 2:
        r = subprocess.run(['git', 'rev-parse', prev_commits[1] + '~1:' + sd],
                           cwd=REPO, capture_output=True, text=True)
        sd_old = r.stdout.strip() if r.returncode == 0 else None
    old_lines = cc.blob_lines(REPO, sd_old, sd) if sd_old else None
    head_lines = cc.head_lines(REPO, sd)
    moved_line = None
    if old_lines and head_lines:
        for i, ln in enumerate(old_lines, 1):
            if 'function sfAddDocument()' in ln:
                # moved iff HEAD's same index no longer holds it and the
                # real position drifted beyond the +/-3 window
                at_head = any('function sfAddDocument()' in head_lines[j - 1]
                              for j in range(max(1, i - 3),
                                             min(len(head_lines), i + 3) + 1))
                if not at_head:
                    moved_line = i
                break
    plants = []  # (id, entry, expected_class)

    def plant(pid, summary, shas, expect):
        plants.append((pid, {'seq': 900000 + len(plants),
                             'summary': summary,
                             'source_shas': shas}, expect))

    for k in range(4):
        plant('HOLDS-%d' % k,
              '`leadTime` handles supplier rows at %s:%d.' % (jr, 65 + (k % 2)),
              {jr: {'sha': jr_sha}}, 'HOLDS')
    if moved_line:
        for k in range(4):
            plant('MOVED-%d' % k,
                  '`sfAddDocument` builds the record at %s:%d.' % (sd, moved_line),
                  {sd: {'sha': sd_old}}, 'MOVED-SINCE')
    else:
        print('COULD NOT RUN: no certain moved-since anchor derivable')
        return 2
    for k in range(4):
        plant('WRONG-%d' % k,
              '`leadTime` handles supplier rows at %s:%d.' % (jr, 100 + k),  # >10 lines from every real leadTime occurrence (65/191/245) -- :200 plants sat 9 lines from the :191 call and the tool CORRECTLY called them NEAR-MISS, a plant defect not a tool defect
              {jr: {'sha': jr_sha}}, 'WRONG-AT-DERIVATION')
    for k in range(4):
        plant('NOTREPO-%d' % k,
              '`leadTime` sits at not/in/repo_%d.js:50 today.' % k,
              {}, 'NOT-A-REPO-PATH')
    for k in range(4):
        plant('NOSHA-%d' % k,
              '`leadTime` handles supplier rows at %s:%d.' % (jr, 210 + k),
              {}, 'UNVERIFIABLE-NO-SHA')

    misses = []
    for pid, entry, expect in plants:
        got = cc.classify(entry)
        cls = got[0][2] if got else 'NO-CITATION-EXTRACTED'
        ok = cls == expect
        print('%s %-10s expect %-22s got %s'
              % ('ok  ' if ok else 'MISS', pid, expect, cls))
        if not ok:
            misses.append((pid, expect, cls))
    print()
    if misses:
        print('%d of 20 MISSED -- defects in the classifier:' % len(misses))
        for pid, exp, got in misses:
            print('  %s: expected %s, classified %s' % (pid, exp, got))
        return 1
    print('all 20 injected citations classified exactly as planted.')

    # ── PHASE 2 (2026-09-30, directed item 9): 20 further plants across
    # the TS-DERIVED fallback and the register-scoped check, in a DATED
    # throwaway repo so the timestamp fallback resolves a real commit.
    import tempfile
    import shutil
    import register_citation_check as rcc
    print()
    print('PHASE 2 -- TS-DERIVED fallback and register-scoped check '
          '(20 plants):')
    misses2 = []

    def check2(pid, expect, got):
        ok = got == expect
        print('%s %-10s expect %-24s got %s'
              % ('ok  ' if ok else 'MISS', pid, expect, got))
        if not ok:
            misses2.append((pid, expect, got))

    d = tempfile.mkdtemp(prefix='mut_phase2_')
    try:
        def g(date, *a):
            subprocess.run(['git'] + list(a), cwd=d, capture_output=True,
                           check=True,
                           env=dict(os.environ, GIT_AUTHOR_NAME='fx',
                                    GIT_AUTHOR_EMAIL='f@x',
                                    GIT_COMMITTER_NAME='fx',
                                    GIT_COMMITTER_EMAIL='f@x',
                                    GIT_AUTHOR_DATE=date,
                                    GIT_COMMITTER_DATE=date))
        g('2020-01-01T00:00:00Z', 'init', '-q')
        body = (['# pad'] * 9 + ['def frobnicate():', '    return 1']
                + ['# t'] * 15)
        open(os.path.join(d, 'app.py'), 'w').write('\n'.join(body) + '\n')
        g('2020-01-01T00:00:00Z', 'add', '-A')
        g('2020-01-01T00:00:00Z', 'commit', '-q', '-m', 'v1')
        open(os.path.join(d, 'app.py'), 'w').write(
            '\n'.join(['# new'] * 5 + body) + '\n')
        g('2020-06-01T00:00:00Z', 'add', '-A')
        g('2020-06-01T00:00:00Z', 'commit', '-q', '-m', 'v2 shifts by 5')
        TS = '2020-03-01T00:00:00Z'   # resolves v1

        def cls_of(entry):
            got = cc.classify(entry, repo=d)
            return got[0][2] if got else 'NO-CITATION-EXTRACTED'

        # 3x TS-MOVED: correct at the ts-resolved v1 (:10), shifted at HEAD
        for k in range(3):
            check2('TSMOV-%d' % k, 'TS-DERIVED-MOVED', cls_of(
                {'summary': '`frobnicate` sits at app.py:10 today (%d).' % k,
                 'ts': TS}))
        # 3x TS-WRONG: wrong even at the ts-resolved commit
        for k in range(3):
            check2('TSWRG-%d' % k, 'TS-DERIVED-WRONG', cls_of(
                {'summary': '`frobnicate` sits at app.py:%d today.' % (97 + k),
                 'ts': TS}))
        # 2x TS-NEAR-MISS: anchor within 10 of the cite at v1, outside 3
        for k in range(2):
            check2('TSNEAR-%d' % k, 'TS-DERIVED-NEAR-MISS', cls_of(
                {'summary': '`frobnicate` writes the row at app.py:%d '
                            'today.' % (19 + k), 'ts': TS}))
            # :18 was a bad PLANT, not a tool defect: HEAD's shifted def
            # sits at :15, so :18 is inside the 3-line window and HOLDS
            # at HEAD is the CORRECT verdict -- same lesson as phase 1's
            # :200 plants. :19/:20 sit outside HEAD's window and within
            # v1's 10-line near-miss band.
        # 1x TS-QUOTED: reporting syntax on a ts-fallback failure
        check2('TSQUOT-0', 'TS-DERIVED-QUOTED', cls_of(
            {'summary': 'The old cell cites app.py:96 for `frobnicate`.',
             'ts': TS}))
        # 1x control: ts predating every commit stays NO-SHA
        check2('TSNONE-0', 'UNVERIFIABLE-NO-SHA', cls_of(
            {'summary': '`frobnicate` sits at app.py:10 today.',
             'ts': '2019-01-01T00:00:00Z'}))

        # ── register-scoped check: 5 bad rows must be reported, 5 good
        # rows must NOT be -- attribution by row name asserted, not just
        # a count.
        os.makedirs(os.path.join(d, 'docs'))
        bad_lines = [99, 22, 98, 24, 97]     # out of window/bounds at HEAD
        good_lines = [14, 15, 16, 15, 14]    # def sits at :15 at HEAD
        rows = ['| Resource | Evidence |', '|---|---|']
        for k, ln in enumerate(bad_lines):
            rows.append('| `bad_row_%d` | frobnicate() writes at '
                        '`app.py:%d` |' % (k, ln))
        for k, ln in enumerate(good_lines):
            rows.append('| `good_row_%d` | frobnicate() writes at '
                        '`app.py:%d` |' % (k, ln))
        open(os.path.join(d, 'docs', 'REG-MUT.md'), 'w').write(
            '\n'.join(rows) + '\n')
        g('2020-07-01T00:00:00Z', 'add', '-A')
        g('2020-07-01T00:00:00Z', 'commit', '-q', '-m', 'register')
        reported = {r[0] for r in rcc.scan(repo=d, register='docs/REG-MUT.md')}
        for k in range(5):
            check2('REGBAD-%d' % k, 'reported',
                   'reported' if ('bad_row_%d' % k) in reported
                   else 'not-reported')
        for k in range(5):
            check2('REGOOD-%d' % k, 'not-reported',
                   'reported' if ('good_row_%d' % k) in reported
                   else 'not-reported')
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print()
    if misses2:
        print('%d of 20 PHASE-2 plants MISSED -- defects in the tools:'
              % len(misses2))
        for pid, exp, got in misses2:
            print('  %s: expected %s, got %s' % (pid, exp, got))
        return 1
    print('all 20 phase-2 plants caught exactly as planted.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
