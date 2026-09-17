"""The negative control for tools/known_red_check.py.

    python tests/run_known_red_probe.py

The tool's own `--fixtures` classify synthetic six-line logs. This drives it
against THE REAL REGISTRY and a REAL 396-file run log, because a correct
classifier pointed at a registry it cannot read reports the same clean green.

── THE FOUR STATES, EACH DRIVEN ───────────────────────────────────────────
A registry of known failures is only worth having if it can distinguish four
answers, and three of them are easy to get wrong:

  NEW        the one the tool exists for
  CHANGED    recorded red, now failing on a DIFFERENT arm -- a second defect
             hiding inside an entry that says the file is expected to fail
  RECOVERED  recorded red and now GREEN -- a STALE entry, which swallows the
             next real failure of that file
  KNOWN      and it must NOT become CHANGED when a count in the message moves,
             or every entry goes stale on the first flake and nobody keeps the
             registry current

── IT WRITES NOTHING AND NEEDS NO SUITE RUN ───────────────────────────────
Every arm edits a COPY of a captured run log in the system temp directory. The
suite itself takes about an hour; requiring that to test the comparison would
mean the comparison is never tested.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['tools/known_red_check.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'known_red_check.py')
REGISTRY = os.path.join(REPO, 'docs', 'known-red-suites.json')

FAILS = []


def arm(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAILS.append(label)


def run(log_text):
    p = os.path.join(tempfile.gettempdir(), 'known-red-probe-%d.txt' % os.getpid())
    io.open(p, 'w', encoding='utf-8', newline='').write(log_text)
    try:
        r = subprocess.run([sys.executable, TOOL, '--from-run', p], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    finally:
        try:
            os.remove(p)
        except OSError:
            pass


def synth_log(entries, green_extra=(), stated=None):
    """A run log built FROM THE REAL REGISTRY, so the arms exercise real rows."""
    lines = ['RAN: 197 JS + 199 PY = 396 files (0 skipped)']
    for e in entries:
        lines.append('  FAIL %-5s %-52s %s' % (e['kind'], e['file'], e['tail']))
    for g in green_extra:
        lines.append('  ok   py    %s' % g)
    lines.append('')
    lines.append('%d FAILING TEST FILE(S)' % (len(entries) if stated is None else stated))
    return '\n'.join(lines) + '\n'


def main():
    if not os.path.isfile(REGISTRY):
        print('COULD NOT RUN: no registry at %s -- NOTHING WAS VERIFIED, and '
              'that is not a pass.' % REGISTRY)
        return 3
    reg = json.load(io.open(REGISTRY, encoding='utf-8'))
    entries = reg['entries']
    arm('the real registry has entries to drive against', len(entries) > 0,
        len(entries))

    # ── 0. THE BASELINE: the registry against its own measured run ─────────
    rc, out = run(synth_log(entries))
    arm('the registry reproduces itself: every recorded row reads KNOWN',
        rc == 0 and 'KNOWN (%d)' % len(entries) in out, 'exit %s\n%s' % (rc, out[-400:]))
    arm('...and nothing is NEW, CHANGED or RECOVERED in that run',
        'NEW (' not in out and 'CHANGED (' not in out and 'RECOVERED (' not in out,
        out[-400:])

    # ── 1. NEW -- the one the tool exists for ─────────────────────────────
    extra = dict(kind='py', file='tests/zz_brand_new_regression.py', tail='boom')
    rc, out = run(synth_log(entries + [extra]))
    arm('a red suite nobody recorded is reported NEW, by name',
        rc == 1 and 'NEW (1)' in out and 'zz_brand_new_regression' in out,
        'exit %s\n%s' % (rc, out[:600]))

    # ── 2. CHANGED -- a second defect hiding inside an expected entry ─────
    mutated = [dict(e) for e in entries]
    mutated[0]['tail'] = 'a completely different arm than the one recorded'
    rc, out = run(synth_log(mutated))
    arm('the SAME file failing on a DIFFERENT arm is CHANGED, not KNOWN',
        rc == 1 and 'CHANGED (1)' in out, 'exit %s\n%s' % (rc, out[:700]))
    arm('...and the report shows both the recorded and the observed arm',
        'recorded:' in out and 'observed:' in out, out[:700])

    # ── 3. KNOWN SURVIVES A MOVING COUNT ─────────────────────────────────
    # Without this the registry goes stale on the first flake and stops being
    # maintained, which is the slow way a known-red list dies.
    digits = [dict(e) for e in entries]
    moved = None
    for e in digits:
        if any(ch.isdigit() for ch in e['tail']):
            moved = e
            e['tail'] = ''.join('9' if ch.isdigit() else ch for ch in e['tail'])
            break
    if moved is None:
        arm('a recorded tail with digits exists to move', False, 'none found')
    else:
        rc, out = run(synth_log(digits))
        arm('a recorded failure whose COUNT moved is still KNOWN -- the same '
            'defect getting worse is not a new one',
            'CHANGED (' not in out, 'exit %s\n%s' % (rc, out[:600]))

    # ── 4. RECOVERED -- the stale entry that swallows the next failure ────
    minus = entries[1:]
    rc, out = run(synth_log(minus, green_extra=[entries[0]['file']]))
    arm('a recorded suite that has gone GREEN is reported RECOVERED',
        rc == 1 and 'RECOVERED (1)' in out, 'exit %s\n%s' % (rc, out[:700]))
    # ASSERTED AGAINST WHAT THE TOOL PRINTS, not against its docstring. The
    # first version of this arm required the word "swallows", which appears in
    # the module header explaining WHY a stale entry is dangerous and not in the
    # RECOVERED message itself -- so it went red against correct output. An
    # assertion about documentation wearing the costume of one about behaviour.
    arm('...and it says the entry must be REMOVED and why, not merely that it '
        'passed',
        'STALE' in out and 'must be removed' in out
        and 'reads as KNOWN' in out, out[:700])

    # ── 5. THE LOG-TRUST REFUSALS, on real-shaped input ──────────────────
    rc, out = run('  FAIL py    tests/a.py    boom\n')
    arm('a TRUNCATED log is COULD NOT RUN, never a clean platform',
        rc == 2 and 'NOTHING WAS COMPARED' in out.upper(),
        'exit %s\n%s' % (rc, out[:300]))
    rc, out = run(synth_log(entries, stated=len(entries) + 5))
    arm('a log whose own summary disagrees with its FAIL lines is refused',
        rc == 2, 'exit %s\n%s' % (rc, out[:300]))

    # ── 6. THE UNDIAGNOSED BACKLOG IS REPORTED ON EVERY RUN ──────────────
    rc, out = run(synth_log(entries))
    blank = sum(1 for e in entries if not (e.get('why') or '').strip())
    arm('the undiagnosed count is printed even on a clean run -- a backlog '
        'that only shows when something else is wrong is a backlog nobody '
        'reads', 'UNDIAGNOSED: %d' % blank in out, out[-600:])

    # ── 7. THE BLIND LOCK IS REACHABLE ───────────────────────────────────
    r = subprocess.run([sys.executable, TOOL, '--fixtures'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    arm('the tool\'s own --fixtures pass', r.returncode == 0,
        (r.stdout or r.stderr)[-300:])

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
