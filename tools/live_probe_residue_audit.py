"""Every live probe that WRITES must say where its residue goes.

Run:  python tools/live_probe_residue_audit.py
      python tools/live_probe_residue_audit.py --json

── THE INCIDENT ────────────────────────────────────────────────────────────
2026-09-28. Verifying that `add_rule` strips forged identity fields needs a
write, because you cannot see what an endpoint STORES by reading it. One probe
rule went to LAW-TEST-2026 -- and DELETE was revoked platform-wide on
law_deadline_rules in August, so the row cannot be removed by the API, by
`service_role`, or by me. It needs a human in the SQL editor.

One probe. One un-deletable row. On a licence somebody may be shown.

THE ARGUMENT WAS ALREADY SETTLED AND NOT APPLIED.
sql/stonedesk_recovery_admin_seed.sql says *"THE FIX IS THE LICENCE, NOT THE
PIN"*; SAIRNroofing followed it on 2026-09-02 and two roofing probes correctly
use RF-AUDIT-2026 today. Nothing made the others do the same, because the rule
lived in a comment in a SQL file rather than anywhere a writing probe would meet
it.

── THE THREE OBLIGATIONS ON A WRITING LIVE PROBE ───────────────────────────
  1. It writes only to an AUDIT licence -- enforced in code by
     tools/audit_licence.py, not by a convention in a header.
  2. It CLEANS UP what it wrote, or records a NAMED residue with the exact path
     that removes it.
  3. It FAILS ITS OWN RUN when residue remains -- because a probe that writes,
     notices, and still exits 0 has told you the subject is fine and said
     nothing about the mess.

── WHAT THIS TOOL DECIDES, AND WHAT IT REFUSES TO GUESS ────────────────────
It finds every file under `tools/ tests/ scripts/` that addresses
`sairn.vercel.app` and sends a WRITE action, then checks each DECLARES its class:

    LIVE_PROBE_CLASS = 'VERIFICATION'   # must obey all three obligations
    LIVE_PROBE_CLASS = 'LOADER'         # writes to REAL licences by design
    LIVE_PROBE_CLASS = 'FIXTURE'        # the write is a string, not a request

**THE CLASS IS DECLARED, NEVER INFERRED, and that is the load-bearing decision.**
`tools/load_deadline_seed.py` writes reference rules to real customer licences
because that is its entire job -- gating it on an audit licence would break
seeding on 48 jurisdictions. A tool that guessed from the filename, the directory
or the action name would either break the loaders or exempt the probes.
tools/checker_control_check.py records that three inference models were tried for
an equivalent question and all three were wrong within an hour:
*"WHICH CHECKER A TEST IS A CONTROL FOR IS A FACT ITS AUTHOR KNOWS AND NOTHING
ELSE RELIABLY DOES."* Same here.

An undeclared writing probe is a FINDING -- not because the class is wrong, but
because nobody has said which it is.

── WHAT IT CANNOT SEE ──────────────────────────────────────────────────────
* Whether the residue path it names actually WORKS. It checks that a path is
  named and that the file exists; it cannot run a DELETE it has no grant for.
* A write reached through a helper that builds the action name dynamically.
* A probe outside this repo.
* Whether `require_audit_licence` is called on the path that actually writes, as
  opposed to somewhere in the file. Presence is necessary, not sufficient, and
  that is the honest limit of a source scan.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker_kit import (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN,  # noqa: E402
                         REPO, read, finish)

CRITERIA_VERSION = '2026-09-28.1'

SCAN_DIRS = ('tools/', 'tests/', 'scripts/')
SCAN_EXT = ('.py', '.js')
LIVE_HOST = 'sairn.vercel.app'

# Actions that CHANGE STORED STATE. Read as a list rather than inferred from the
# verb, because `evaluate` writes nothing and `verify` on api/audit-checkpoint
# does. Additions belong here with the reason in the commit.
WRITE_ACTIONS = frozenset((
    'write', 'write_batch', 'add_rule', 'add_holidays', 'setup', 'bootstrap',
    'set_active', 'soft_delete', 'delete', 'propose_clock_correction',
    'reconcile', 'append', 'record', 'submit', 'book', 'enqueue', 'checkpoint'))
# `verify` WAS in this list and is removed, measured rather than assumed:
# api/audit-checkpoint.js branches `action === 'verify' ? verifyTable : checkpointTable`,
# and only `checkpointTable` issues a POST. So `verify` re-reads and compares
# stored hashes and writes nothing, while `checkpoint` is the write -- which is
# why the verb is not a reliable guide and this list is read rather than inferred.
# Removing it took tools/audit_checkpoint_status.py out of the writer set, where
# it never belonged.

CLASSES = ('VERIFICATION', 'LOADER', 'FIXTURE')
CLASS_RE = re.compile(r'''LIVE_PROBE_CLASS\s*=\s*["']([A-Z]+)["']''')
RESIDUE_RE = re.compile(r'''LIVE_PROBE_RESIDUE\s*=\s*["']([^"']*)["']''')
AUDIT_GUARD_RE = re.compile(r'require_audit_licence\s*\(')
DEMO_KEY_RE = re.compile(r'\b[A-Z]{2,6}-(?:PINNACLE|TEST|DEMO|PARTNER)-\d{4}\b')


def _strip_comments(src, path):
    """Blank comments so a licence key DISCUSSED in prose is not read as one USED.

    Python gets a quote-aware `#` scan; JS delegates to the canonical stripper.
    Offsets are not preserved and do not need to be -- this feeds a set
    membership test, not a line number.
    """
    if path.endswith('.js'):
        from checker_kit import strip_comments as js_strip
        return js_strip(src)
    BACKSLASH, NEWLINE = chr(92), chr(10)
    QUOTES = (chr(39), chr(34))
    out, i, n, quote = [], 0, len(src), None
    while i < n:
        c = src[i]
        if quote:
            if c == BACKSLASH and i + 1 < n:
                out.append(src[i:i + 2])
                i += 2
                continue
            if c == quote:
                quote = None
            out.append(c)
            i += 1
            continue
        if c in QUOTES:
            quote = c
            out.append(c)
            i += 1
            continue
        if c == '#':
            j = src.find(NEWLINE, i)
            i = n if j < 0 else j
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def action_literals(src):
    names = set()
    for m in re.finditer(r'''["']action["']\s*:\s*["']([a-z0-9_]+)["']''', src):
        names.add(m.group(1))
    for m in re.finditer(r'''\baction\s*=\s*["']([a-z0-9_]+)["']''', src):
        names.add(m.group(1))
    return names


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    out = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True,
                         text=True, encoding='utf-8', errors='replace')
    if out.returncode != 0:
        print('COULD NOT RUN: `git ls-files` failed, so the probe universe is '
              'unknown. A residue audit built from a failed enumeration is worse '
              'than none.')
        return EXIT_COULD_NOT_RUN

    cands = [f.strip() for f in out.stdout.split('\n') if f.strip()
             and f.strip().startswith(SCAN_DIRS) and f.strip().endswith(SCAN_EXT)
             and not f.strip().startswith('archive/')]

    unreadable, live, writers, findings = [], 0, [], []
    for f in cands:
        try:
            src = read(os.path.join(REPO, f))
        except (IOError, OSError) as e:
            unreadable.append('%s could not be read (%s) -- NOT scanned, so a '
                              'writing probe in it is MISSING from this answer'
                              % (f, e))
            continue
        if LIVE_HOST not in src:
            continue
        live += 1
        writes = sorted(action_literals(src) & WRITE_ACTIONS)
        if not writes:
            continue
        cm = CLASS_RE.search(src)
        rm = RESIDUE_RE.search(src)
        # ── THE DEMO-KEY CHECK READS CODE, NOT PROSE ──────────────────────────
        # Its first run flagged three probes for "hardcoding a demo-facing
        # licence" -- and every hit was MY OWN COMMENT explaining which licence
        # the probe was being moved AWAY from. A check that fires on its own
        # documentation is PR 1.2, and this repo has now paid for it twice in one
        # session: tools/ghost_field_read_scan.py was blinded by prose in exactly
        # the mirror-image way. The class and residue declarations are real
        # assignments, so they survive stripping; a licence key named in a comment
        # does not, and should not.
        code = _strip_comments(src, f)
        writers.append({
            'file': f, 'writes': writes,
            'declared': cm.group(1) if cm else None,
            'residue': rm.group(1) if rm else None,
            'guarded': bool(AUDIT_GUARD_RE.search(src)),
            'demo_keys': sorted(set(DEMO_KEY_RE.findall(code))),
        })

    for w in writers:
        f, cls = w['file'], w['declared']
        if cls is None:
            findings.append('%s sends a WRITE action (%s) to the live platform and '
                            'declares no LIVE_PROBE_CLASS. Add one of %s -- the '
                            'class is a fact its author knows and nothing else '
                            'reliably does.'
                            % (f, ', '.join(w['writes']), '/'.join(CLASSES)))
            continue
        if cls not in CLASSES:
            findings.append('%s declares LIVE_PROBE_CLASS %r, which is not one of '
                            '%s.' % (f, cls, '/'.join(CLASSES)))
            continue
        if cls == 'VERIFICATION':
            if not w['guarded']:
                findings.append('%s is VERIFICATION and writes (%s) but never calls '
                                'require_audit_licence -- so it will write to '
                                'whatever licence it is handed, including a '
                                'demo-facing one.' % (f, ', '.join(w['writes'])))
            if not w['residue']:
                findings.append('%s is VERIFICATION and writes (%s) but declares no '
                                'LIVE_PROBE_RESIDUE. Say "none -- <why>" if it '
                                'cleans up after itself; an empty declaration is '
                                'the silence this audit exists to remove.'
                                % (f, ', '.join(w['writes'])))
            elif w['residue'].lower().startswith('none'):
                pass
            elif not os.path.exists(os.path.join(REPO, w['residue'].split()[0])):
                findings.append('%s names residue path %r and that file does not '
                                'exist -- a deletion path nobody can run is a '
                                'named residue with no way out.'
                                % (f, w['residue']))
            if w['demo_keys']:
                findings.append('%s is VERIFICATION, writes, and hardcodes a '
                                'DEMO-FACING licence: %s. That is the licence a '
                                'prospect is shown.'
                                % (f, ', '.join(w['demo_keys'])))

    print('LIVE PROBE RESIDUE AUDIT')
    print('  criteria                    : %s' % CRITERIA_VERSION)
    print('  CHECKED / UNIVERSE          : %d / %d files under %s'
          % (live, len(cands), ' '.join(SCAN_DIRS)))
    print('  of those, WRITE to the live platform: %d' % len(writers))
    print('  write actions counted       : %s' % ', '.join(sorted(WRITE_ACTIONS)))
    print()
    for w in sorted(writers, key=lambda x: x['file']):
        print('  %-11s %-48s %s' % (w['declared'] or 'UNDECLARED', w['file'],
                                    ', '.join(w['writes'])[:34]))
        if w['declared'] == 'VERIFICATION':
            print('              guard=%s  residue=%s'
                  % ('yes' if w['guarded'] else 'NO', w['residue'] or 'NONE DECLARED'))
    print()
    print('  A PROBE OUTSIDE THIS REPO IS INVISIBLE HERE, and so is a write reached')
    print('  through a dynamically built action name. Presence of the guard is')
    print('  NECESSARY, NOT SUFFICIENT -- a source scan cannot tell whether it is')
    print('  called on the path that actually writes.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'checked': live,
                          'universe': len(cands), 'writers': writers,
                          'findings': findings, 'could_not_run': unreadable},
                         indent=2))

    return finish(findings, could_not_run=unreadable, clean_line=(
        '\nEVERY writing live probe declares its class, and every VERIFICATION one '
        'is\nguarded to an audit licence and says where its residue goes.'))


if __name__ == '__main__':
    sys.exit(main())
