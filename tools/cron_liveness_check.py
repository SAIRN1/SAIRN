#!/usr/bin/env python
"""cron_liveness_check.py -- ask the watchdog, OUT OF BAND, and write it down.

    CRON_SECRET=... python tools/cron_liveness_check.py

── WHY THIS EXISTS SEPARATELY FROM api/cron-watchdog.js ────────────────────
The watchdog runs on the SAME Vercel cron scheduler as the jobs it watches. If
that scheduler stops, the watchdog stops with it and reports nothing -- two
units sharing a failure mode, which is convention 7's exact lesson: a second
copy is not a second opinion.

THIS RUNS OUTSIDE VERCEL. It is what survives a total scheduler outage.

── AND SINCE 2026-09-15 IT NO LONGER DEPENDS ON SOMEBODY REMEMBERING ───────
This file used to say the remaining gap needed "a third-party monitor pinging
the endpoint on its own schedule", and that this was "a decision about spend
and vendors rather than something to invent quietly in a file". **That was
true when written and is now out of date in the cheapest possible direction:**
`.github/workflows/cron-liveness.yml` runs this tool hourly on GitHub's
infrastructure, which is a genuinely different scheduler from Vercel's, at no
spend, using a workflow pattern this repository already runs twice.

The correction is recorded rather than quietly overwritten because the OLD
sentence was the reason nobody built it, and a future reader who finds only the
new one cannot tell a decision from an oversight.

**WHAT IS STILL TRUE:** GitHub Actions is not an uptime vendor. Scheduled
workflows can be delayed under load and are disabled on repositories with no
activity for 60 days. So this is a second INDEPENDENT scheduler, not a
guaranteed one, and the workflow says the same thing in its own header.

── THE RULE THAT MATTERS ───────────────────────────────────────────────────
**A STATUS DOC THAT CANNOT BE UPDATED MUST NOT KEEP SAYING OK.** Unreachable
endpoint, absent secret, unparseable answer, a 503 because the migration has not
been run -- every one of them overwrites the previous verdict with COULD NOT
TELL and exits 2. Leaving yesterday's clean answer in place would be a document
asserting a check that never happened, which is the failure every convention in
docs/2026-09-13-cross-domain-disciplines.md defends against and the single worst
thing a liveness check could do.

Exit 0 every job ok, 1 at least one job is not, 2 could not run.
"""
import io
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2
DOC = os.path.join(REPO, 'docs', 'CRON-LIVENESS-STATUS.md')
DEFAULT_URL = 'https://sairn.vercel.app/api/cron-watchdog'


def watchdog_url():
    """The endpoint to ask, with EMPTY treated as ABSENT.

    ── THE SIX SILENT FAILURES THIS CAUSED (found 2026-09-17) ──────────────
    This was `os.environ.get('SAIRN_WATCHDOG_URL', DEFAULT_URL)`, which is the
    ordinary Python idiom and is WRONG in the one environment this tool exists
    to run in. GitHub Actions materialises

        env:
          SAIRN_WATCHDOG_URL: ${{ secrets.SAIRN_WATCHDOG_URL }}

    as an EMPTY STRING when the secret does not exist -- it does not leave the
    name unset. `get(name, default)` returns the default only when the key is
    ABSENT, so `url` became `''`, the request went nowhere, and the tool exited
    2 COULD NOT TELL on every run.

    MEASURED, NOT INFERRED. The workflow had run six times, every one a
    failure, and the failures looked like the platform being unhealthy. They
    were not: the `Refuse to run blind` step PASSED on every run, which means
    CRON_SECRET was set the whole time; `Soft recovery` was SKIPPED, which
    happens only for exit code 2 and never for a finding; and Vercel's own
    runtime log shows 24 requests to /api/cron-watchdog in 24 hours, all 200,
    all of them Vercel's own scheduler. NOT ONE REQUEST FROM THE RUNNER EVER
    ARRIVED. The second scheduler -- the whole point of which is to survive a
    Vercel outage -- had never once asked the question.

    THE WORKFLOW'S OWN SHELL STEP GETS THIS RIGHT, which is what makes it worth
    writing down rather than just fixing: the soft-recovery step uses
    `${SAIRN_WATCHDOG_URL:-...}`, and bash's `:-` treats empty as absent. Two
    languages, one variable, opposite defaults -- and the header of that file
    calls the variable "optional; defaults to the production URL in the tool".
    It did not.
    """
    # STRIPPED, which makes this marginally STRICTER than the shell's `:-`
    # (bash treats a space as a value). A whitespace URL is never a real
    # endpoint and is a plausible paste into a secret box, so falling back
    # to the production URL is the only outcome that asks anything at all.
    return (os.environ.get('SAIRN_WATCHDOG_URL') or '').strip() or DEFAULT_URL


# What each non-ok status MEANS and what it points at. Written here rather than
# in the endpoint because this is the document a human reads, and a status code
# with no sentence beside it makes the reader go and find the source.
MEANING = {
    'DEAD': 'has missed three or more intervals. The job is not running -- check '
            'the deploy and the vercel.json cron entry before anything else.',
    'LATE': 'has missed two intervals. One slow run does not explain this; two '
            'in a row usually means the last deploy or an upstream timeout.',
    'NEVER_BEAT': 'has NO heartbeat row at all. It has never completed a run -- '
                  'this is usually a job that was scheduled but never deployed, '
                  'or one that predates sql/cron_heartbeat_schema.sql.',
    'FAILING': 'ran on time and reported FAILED. The scheduler is fine; the job '
               'is not. Its own log line carries the reason.',
    'PARTIAL': 'ran on time and did only part of its work. On the alert sweeps '
               'this is the shape that matters most: alive, on schedule, and '
               'notifying nobody.',
    'UNDECLARED': 'is beating but is not in the watchdog EXPECTED_JOBS list -- '
                  'either it was removed from vercel.json and still runs, or its '
                  'name does not match the one being watched.',
}


def write_status(state, lines, payload=None):
    stamp = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())
    out = [
        '# Cron liveness status',
        '',
        '**GENERATED by `tools/cron_liveness_check.py`. Do not hand-edit.**',
        'Rewritten whole on every run; a hand-edit is lost and, worse, would make',
        'this file assert a check that did not happen.',
        '',
        '| | |',
        '|---|---|',
        '| **State** | **%s** |' % state,
        '| Last run | %s |' % stamp,
        '| Endpoint | `%s` |' % watchdog_url(),
        '',
    ] + lines + [
        '',
        '---',
        '',
        '**COULD NOT TELL is a third state and is never folded into OK.** If this',
        'file says COULD NOT TELL, nothing was checked -- that is not a clean run,',
        'and the previous clean verdict was deliberately overwritten rather than',
        'left standing.',
        '',
        '**WHAT THIS CANNOT SEE.** `api/cron-watchdog.js` runs on the same Vercel',
        'cron scheduler as the jobs it watches, so a total scheduler outage',
        'silences both. THIS tool runs outside Vercel and is what survives that.',
        'Since 2026-09-15 it also runs hourly from',
        '`.github/workflows/cron-liveness.yml` — a genuinely different scheduler,',
        'at no spend — so it no longer depends on somebody remembering to run it.',
        '',
        '**AND WHAT THAT STILL IS NOT.** GitHub Actions is not an uptime vendor:',
        'scheduled workflows can be delayed under load, and GitHub disables them',
        'on a repository with no activity for 60 days. A second INDEPENDENT',
        'scheduler is a real improvement over one; it is not a guaranteed one,',
        'and the difference is stated here rather than implied by the word',
        '"automated".',
    ]
    if payload is not None:
        out += ['', '<details><summary>Raw response</summary>', '',
                '```json', json.dumps(payload, indent=2)[:8000], '```', '',
                '</details>']
    io.open(DOC, 'w', encoding='utf-8', newline='').write('\n'.join(out) + '\n')


def cannot_tell(lines, payload=None, msg=''):
    write_status('COULD NOT TELL', lines, payload)
    print('COULD NOT RUN: %s %s says so rather than keeping a stale OK.'
          % (msg, os.path.relpath(DOC, REPO)))
    return EXIT_COULD_NOT_RUN


def main(argv):
    url = watchdog_url()
    secret = os.environ.get('CRON_SECRET')
    if not secret:
        return cannot_tell([
            '**CRON_SECRET is not set in this environment, so the watchdog was not',
            'called and no job was checked.**',
            '',
            'This is not a finding about the jobs. It is this tool being unable to ask.',
        ], msg='CRON_SECRET is not set.')

    try:
        from sairn_http import fetch_json
    except Exception as e:
        return cannot_tell([
            '**`tools/sairn_http.py` could not be imported (%s).**' % type(e).__name__,
            '',
            'Bare `curl` is deliberately not used as a fallback: an edge challenge',
            'returns a 403 that a naive client reads as a page, which is how a check',
            'reports a success it never had.',
        ], msg=str(e))

    try:
        # ── fetch_json RETURNS Response(status, body), NOT THE BODY ─────────
        # FOUND 2026-09-17, and it means this tool could never once have said
        # anything but COULD NOT TELL. `payload` was the namedtuple; the
        # `isinstance(payload, dict)` guard below is therefore ALWAYS true, so
        # every run took the unreadable-answer branch and exited 2 -- including
        # the runs where the watchdog answered 200 with all four jobs `ok`.
        #
        # It survived because it was never REACHED. Locally the tool stopped at
        # `CRON_SECRET is not set`; in Actions it stopped at an empty
        # SAIRN_WATCHDOG_URL. The first time a real answer ever arrived was
        # 2026-09-17T06:40:53Z, after the URL fix -- and the run still failed,
        # which is what exposed this. Two defects stacked, and the outer one
        # hid the inner one for the tool's entire life.
        resp = fetch_json(url, method='POST', payload={},
                          headers={'Authorization': 'Bearer ' + secret})
    except Exception as e:
        return cannot_tell([
            '**The watchdog could not be reached or did not answer usefully.**',
            '',
            '    %s: %s' % (type(e).__name__, str(e)[:400]),
            '',
            'No job was checked. A 403 is UNREACHED, not verified-good -- and an',
            'unreachable watchdog is itself consistent with the outage it exists to',
            'report, so this is the one COULD NOT TELL worth acting on immediately.',
        ], msg='%s: %s' % (type(e).__name__, e))

    # THE HTTP STATUS IS READ RATHER THAN ASSUMED. fetch_json does NOT raise on
    # an HTTP error -- it returns the parsed error body with its code -- so a
    # 401 from a stale CRON_SECRET would otherwise be parsed as an answer. A
    # monitor that reads its own rejection as data is the failure this file's
    # header is about.
    status, payload = resp.status, resp.body
    if status != 200:
        return cannot_tell([
            '**The watchdog rejected or could not serve this request: HTTP %s.**'
            % status,
            '',
            '`401` means the `CRON_SECRET` this tool sent does not match the one',
            'the deployment holds -- the secret is SET and WRONG, which looks',
            'identical to a healthy monitor from the outside. No job was checked.',
        ], payload if isinstance(payload, dict) else None,
           msg='HTTP %s from the watchdog.' % status)
    if not isinstance(payload, dict):
        return cannot_tell(['**The watchdog answered something this tool cannot read.**'],
                           msg='unreadable answer.')
    if payload.get('error'):
        code = payload['error'].get('code', 'error')
        return cannot_tell([
            '**The watchdog refused: `%s`**' % code,
            '',
            '> %s' % payload['error'].get('message', ''),
            '',
            '`NOT_PROVISIONED` means `sql/cron_heartbeat_schema.sql` has never been',
            'run, so there are no heartbeats to check and nothing is being watched.',
        ], payload, msg='the watchdog refused.')

    jobs = payload.get('jobs')
    if not isinstance(jobs, list):
        return cannot_tell(['**The watchdog answered without a job list.**'], payload,
                           msg='no job list.')

    lines = ['| Job | Status | Last run | Age (s) | Headroom (s) |', '|---|---|---|---|---|']
    for j in sorted(jobs, key=lambda x: str(x.get('job'))):
        lines.append('| `%s` | **%s** | %s | %s | %s |' % (
            j.get('job'), j.get('status'), j.get('last_run_at', '—'),
            j.get('age_seconds', '—'), j.get('seconds_until_late', '—')))
    # ── WHAT WAS DONE ABOUT IT (item 55) ───────────────────────────────────
    # Reported separately from what was FOUND, because a reader who cannot tell
    # them apart cannot tell a suppressed alert from an alert that was never
    # planned -- and UNDELIVERED is the state that matters most here: detection
    # worked and nobody was told, which is the shape a watchdog is supposed to
    # make impossible rather than produce.
    actions = payload.get('actions') or []
    undelivered = [a for a in actions if a.get('delivered') is False]
    if actions:
        lines += ['', '## Response', '',
                  '| Job | Status | Action | Delivered | Why |', '|---|---|---|---|---|']
        for a in actions:
            d = a.get('delivered')
            lines.append('| `%s` | %s | **%s** | %s | %s |' % (
                a.get('job'), a.get('status'), a.get('action'),
                '—' if d is None else ('yes' if d else '**NO**'),
                str(a.get('reason', ''))[:160]))
    if undelivered:
        lines += ['', '### A response could NOT be delivered', '',
                  '**Detection worked and nobody was told.** This is worse than a',
                  'missing watchdog, because the existence of one is an assurance',
                  'somebody is relying on.', '']
        for a in undelivered:
            lines.append('- `%s` %s **%s** — %s' % (
                a.get('job'), a.get('status'), a.get('action'),
                (a.get('detail') or {}).get('error', 'no reason given')))

    # ── CAN THE WATCHDOG TELL ANYBODY ANYTHING? (added 2026-09-15) ─────────
    # `undelivered` only appears when there was something to send, so a platform
    # where every job is healthy and the alert channel is DEAD reported OK here
    # -- and that is precisely the state production was in on 2026-09-15, with
    # SAIRN_OPS_EMAIL unset and every planned alert ending "nobody was told".
    # The channel is now a standing fact on its own axis in the watchdog's
    # answer, and this reads it. AN ABSENT FIELD IS NOT A PASS: an older
    # deployment that does not report it is a COULD NOT TELL, because "the
    # channel is fine" and "this deployment cannot say" are different answers.
    channel = payload.get('notify_channel')
    channel_lines = []
    if channel is None:
        return cannot_tell([
            '**The watchdog did not report `notify_channel`.**',
            '',
            'That field says whether an alert could reach anybody at all. A',
            'deployment predating it cannot answer, and a silent alert channel is',
            'invisible until the day a real job fails -- so this is COULD NOT TELL',
            'rather than OK. Redeploy `api/cron-watchdog.js`.',
        ], payload, msg='no notify_channel field.')
    if not channel.get('configured'):
        channel_lines = [
            '', '### The watchdog CANNOT NOTIFY ANYBODY', '',
            '**Missing: %s.** Detection is running and every alert it plans will'
            % ', '.join(channel.get('missing') or ['(not stated)']),
            'end *"nobody was told"*. This is a CONFIGURATION state, not a failed',
            'run -- it does not clear by itself and it will not announce itself on',
            'the day it matters.', '']

    bad = [j for j in jobs if j.get('status') != 'ok'] + undelivered
    if channel_lines:
        lines += channel_lines
    if bad or channel_lines:
        lines += ['', '## Not ok', '']
        for j in bad:
            lines.append('- **`%s` — %s**: %s' % (
                j.get('job'), j.get('status'),
                MEANING.get(j.get('status'), j.get('why', 'no explanation available'))))
        write_status('NOT OK', lines, payload)
        print('FINDING: %d job(s) not ok%s. See %s'
              % (len(bad),
                 '' if not channel_lines else
                 (' and the alert channel is DEAD (missing %s)'
                  % ', '.join(channel.get('missing') or ['?'])),
                 os.path.relpath(DOC, REPO)))
        return EXIT_FINDING

    if not jobs:
        # A CLEAN SWEEP OVER AN EMPTY LIST IS NOT A CLEAN SWEEP. It is what a
        # watchdog watching nothing looks like, and it is identical in shape to
        # every job being healthy.
        return cannot_tell([
            '**The watchdog checked ZERO jobs.** That is not "everything is fine" --',
            'it is what a watchdog watching nothing looks like, and the two are',
            'indistinguishable from the outside.',
        ], payload, msg='zero jobs checked.')

    write_status('OK', lines, payload)
    print('OK: %d job(s) healthy. %s updated.' % (len(jobs), os.path.relpath(DOC, REPO)))
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
