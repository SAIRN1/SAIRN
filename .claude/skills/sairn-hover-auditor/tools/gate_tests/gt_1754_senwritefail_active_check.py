#!/usr/bin/env python
"""gate test for H1 finding #1754 (b108). CLAIM asserted, so exit 0 means the claim held and the finding SURVIVES:
at the pinned commit, (a) sairnsenior.html senWriteFail() keeps a failed write only for the empty code, NOT_PROVISIONED,
NO_LICENSE, HTTP_5xx and UPSTREAM and does NOT name ACTIVE_CHECK_FAILED or ACTIVE_CHECK_UNREADABLE; (b) senSweepLocalDrafts
still decides withdraw-or-keep with senWriteFail(...).kept; (c) api/sd-data.js still answers an unfinished credential-active
check with HTTP 502 carrying preActive.code and api/_lib/auth.js still emits both ACTIVE_CHECK codes. Together: a transient
outage of that check reaches the sweep as a 'refusal' and the drafts are withdrawn.

Exit 0 claim holds (survives). Exit 1 it does not (killed: a code was added to the kept list, or the trigger is gone).
Exit 2 could not run. It READS files as data with git show and executes none of them.

usage: python gt_1754_senwritefail_active_check.py REV [HTML_OVERRIDE]
"""
import os
import re
import subprocess
import sys

REPO = os.path.expanduser('~/Documents/SAIRN-hover')


def show(rev, path):
    r = subprocess.run(['git', '-C', REPO, 'show', '%s:%s' % (rev, path)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print('COULD NOT RUN: git show %s:%s failed: %s' % (rev, path, r.stderr.strip()[:100]))
        sys.exit(2)
    return r.stdout


def main(argv):
    if not argv:
        print('COULD NOT RUN: no rev given')
        return 2
    rev = argv[0]
    html = open(argv[1], encoding='utf-8', errors='replace').read() if len(argv) > 1 else show(rev, 'sairnsenior.html')
    m = re.search(r'function senWriteFail\(resource\)\{.*?\n\}', html, re.S)
    if not m:
        print('COULD NOT RUN: senWriteFail not found in the expected shape')
        return 2
    fn = m.group(0)
    kept_cond = re.search(r"if\(code==='NOT_PROVISIONED'.*?\)\s*\n\s*return \{kept:true", fn, re.S)
    if not kept_cond:
        print('COULD NOT RUN: the kept-list condition is not in the expected shape')
        return 2
    names_check = 'ACTIVE_CHECK' in fn
    sweep = re.search(r'async function senSweepLocalDrafts\(.*?\n\}', html, re.S)
    sweep_uses = bool(sweep and re.search(r"senWriteFail\('sen_claims'\)\.kept", sweep.group(0)))
    sd = show(rev, 'api/sd-data.js')
    au = show(rev, 'api/_lib/auth.js')
    trigger = (bool(re.search(r"preActive\.code === 'ACTIVE_CHECK_FAILED'", sd))
               and bool(re.search(r"res\.status\(502\)\.json\(\{ error: \{ code: preActive\.code", sd))
               and "'ACTIVE_CHECK_FAILED'" in au and "'ACTIVE_CHECK_UNREADABLE'" in au)
    print('senWriteFail names an ACTIVE_CHECK code: %s; sweep decides with senWriteFail().kept: %s; '
          '502 ACTIVE_CHECK trigger still emitted by the server: %s' % (names_check, sweep_uses, trigger))
    if names_check or not sweep_uses or not trigger:
        print('CLAIM DOES NOT HOLD')
        return 1
    print('CLAIM HOLDS: the sweep withdraws on any code outside the kept list, and the two transient 502 codes are outside it')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
