"""Control pair for tools/literal_drift_check.py -- can it FIRE, and stay quiet?

    python tests/run_literal_drift_control_probe.py     (exit 0 pass, 1 fail)

WHY THIS EXISTS AND WHY THE OTHER PROBE IS NOT IT.
`tests/run_literal_drift_determinism_probe.py` already declares itself a
control for this checker, and it is a good one -- it proves the output is
byte-identical across `PYTHONHASHSEED` values, and that the OLD sort really was
detectably unstable on a reverted copy. Neither of those is a clean-vs-finding
pair. Until 2026-09-13 that gap was invisible, because `checker_control_check.py`
was counting DOCSTRING PROSE as evidence and this checker's entire silent half
came from prose. With evidence read from a parse tree, the real state showed:
**nothing had ever watched this checker go from quiet to reporting.**

So: plant the defect, demand it is REPORTED; plant clean input, demand SILENCE.
One section per pass, because the tool runs three and a pair proved on one says
nothing about the other two.

── IT CANNOT FAIL BY EXIT CODE, AND THAT IS A FINDING, NOT A QUIRK ─────────
`literal_drift_check.py` ALWAYS EXITS 0. It has no `sys.exit` at all -- it
prints its three sections and falls off the end. **It is promoted in
`tools/report_only_checks.py` with `'verdict': by_exit`**, and `by_exit`
returns no findings whenever the return code is 0. So every finding this
checker has ever produced has been invisible to the registry that runs it, and
the registry's own evidence line -- *"real run 2026-09-10 over all 22 app
files: 0 findings"* -- is what a checker that CANNOT report looks like.

That is the `checkblocks.py` class exactly: a checker wired by an exit code it
does not have. `sairn_dead_button_audit.py` has the same always-0 property and
is read with `by_section` for precisely this reason, and says so in the
registry.

**This file does not change the wiring.** Which sections should count as a
finding is a real decision with a real cost -- measured across the 22 app
files, section B is dominated by demo phone numbers, which the tool's own
docstring names as noise -- and it belongs to whoever owns that registry. What
this file does is make the property mechanical instead of a surprise: the
always-0 exit is ASSERTED here, so the next person to wire this tool cannot
reach for `by_exit` without a red arm.

FIXTURES ARE WRITTEN TO A TEMP DIRECTORY AND NEVER TO A REAL APP FILE.
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['literal_drift_check.py']

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'literal_drift_check.py')
fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def on(body):
    """Run the checker against one planted file. Returns (rc, output)."""
    d = tempfile.mkdtemp(prefix='ldrift-probe-')
    p = os.path.join(d, 'app.html')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    try:
        q = subprocess.run([sys.executable, TOOL, p], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=600)
        return q.returncode, (q.stdout or '') + (q.stderr or '')
    finally:
        shutil.rmtree(d, ignore_errors=True)


def section(out, letter):
    """The body of one printed section, so an arm cannot be satisfied by another."""
    parts = re.split(r'=== ([A-C]\d?)\. ', out)
    for i in range(1, len(parts) - 1, 2):
        if parts[i] == letter:
            return parts[i + 1]
    return ''


CLAUSE = ('The governing law of this agreement is the State of Ohio, '
          '%s County, and all disputes shall be resolved there.')


def page(body):
    return '<html><body><script>\n%s\n</script></body></html>\n' % body


# ── 1. PASS A2 -- NEAR-DUPLICATE PROSE ───────────────────────────────────────
# The real case: two copies of the base system prompt, 1,793 vs 2,086 chars,
# identical up to the shorter one's end. One had been corrected; the live
# Drawing Tool used the stale copy.
print('1. A2 -- two long literals that are ALMOST the same')
rc, out = on(page('var A = "%s";\nvar B = "%s";' % (CLAUSE % 'Cuyahoga',
                                                    CLAUSE % 'Summit')))
a2 = section(out, 'A2')
check(a2.count('\n  pair ') == 1, 'a near-duplicate pair is REPORTED (got %d)'
      % a2.count('\n  pair '))
check('Cuyahoga County' in a2 and 'Summit County' in a2,
      '...and the first difference is printed, not just the count')

print('')
print('2. CONTROL: the same two literals, IDENTICAL')
rc, out = on(page('var A = "%s";\nvar B = "%s";' % (CLAUSE % 'Cuyahoga',
                                                    CLAUSE % 'Cuyahoga')))
a2 = section(out, 'A2')
check(a2.count('\n  pair ') == 0, 'an exact duplicate is NOT a drift (got %d)'
      % a2.count('\n  pair '))
check('none' in a2, '...and the section says so in its own words')

# ── 3. PASS B -- A FACT WITH MORE THAN ONE VALUE ─────────────────────────────
print('')
print('3. B -- one fact, two values')
rc, out = on(page('var A = "%s";\nvar B = "%s";' % (CLAUSE % 'Cuyahoga',
                                                    CLAUSE % 'Summit')))
b = section(out, 'B')
check('!! county' in b, 'a county with two values is REPORTED')
check('2 distinct values' in b, '...and the count is stated')

print('')
print('4. CONTROL: the same fact with ONE value')
rc, out = on(page('var A = "%s";\nvar B = "%s";' % (CLAUSE % 'Cuyahoga',
                                                    CLAUSE % 'Cuyahoga')))
b = section(out, 'B')
check('!! county' not in b, 'one value is not a divergence')
# AND IT DID LOOK. A pass that reports nothing because it found nothing to read
# is indistinguishable from a clean one -- the whole shape this repo keeps
# finding -- so the arm demands the positive statement, not just the absence.
check('ok county' in b and 'Cuyahoga County' in b,
      '...and it says so POSITIVELY: one value, named')

# ── 5. PASS C -- SAME LABEL, DIFFERENT VALUE ─────────────────────────────────
print('')
print('5. C -- one label, two values')
LABEL = ('<span>%s</span><span class="rv">%s</span>\n')
rc, out = on('<html><body>\n' + LABEL % ('Waste Allowance', '12%')
             + LABEL % ('Waste Allowance', '15%') + '</body></html>\n')
c = section(out, 'C')
check('!! Waste Allowance' in c, 'a label with two values is REPORTED')
check("'12%'" in c and "'15%'" in c, '...and both values are printed')

print('')
print('6. CONTROL: the same label, the SAME value twice')
rc, out = on('<html><body>\n' + LABEL % ('Waste Allowance', '12%')
             + LABEL % ('Waste Allowance', '12%') + '</body></html>\n')
c = section(out, 'C')
check('!! Waste Allowance' not in c, 'one value repeated is not a divergence')
check('none' in c, '...and the section says none')

# ── 7. A COMMENTED-OUT STALE COPY IS NOT A SECOND PLACE ──────────────────────
# The 2026-09-11 fix, found by tools/comment_sensitivity_check.py and never
# pinned. Measured on sairnbiz.html at the time: 370 literals >= 30 chars raw
# vs 358 with comments blanked. The dangerous case is not the inflated count --
# it is a live literal plus an out-of-date commented-out copy reading as two
# places that disagree, which is EXACTLY what this tool reports.
print('')
print('7. the 2026-09-11 comment fix: prose describing old code is not code')
rc, out = on(page('// Was: "%s"\nvar A = "%s";'
                  % (CLAUSE % 'Summit', CLAUSE % 'Cuyahoga')))
b = section(out, 'B')
check('!! county' not in b, 'a commented-out stale copy is not a second value')
check('Summit' not in out, '...and the dead value is never named anywhere')
check('ok county' in b and 'x1' in b,
      '...while the LIVE copy is still counted, exactly once')

# ── 8. THE EXIT CODE, PINNED ─────────────────────────────────────────────────
print('')
print('8. it ALWAYS exits 0 -- the property the registry is wired against')
rc_defect, _ = on(page('var A = "%s";\nvar B = "%s";' % (CLAUSE % 'Cuyahoga',
                                                         CLAUSE % 'Summit')))
rc_clean, _ = on(page('var A = "%s";' % (CLAUSE % 'Cuyahoga')))
check(rc_defect == 0, 'a fixture FULL of drift still exits 0 (got %d)' % rc_defect)
check(rc_clean == 0, 'and a clean fixture exits 0 too (got %d)' % rc_clean)
check(rc_defect == rc_clean,
      'THE TWO ARE INDISTINGUISHABLE BY EXIT CODE -- so report_only_checks.py '
      'reading this tool with by_exit can never see a finding')

# The registry entry is read rather than described, so this arm cannot go stale
# quietly if somebody fixes the wiring.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import report_only_checks as R                                  # noqa: E402
entry = [e for e in R.REGISTRY if e['tool'] == 'literal_drift_check.py']
check(len(entry) == 1, 'the checker is in the report-only registry exactly once')
if entry:
    verdict = entry[0]['verdict'].__name__
    print('     registry reads it with: %s()' % verdict)
    # NOT an assertion that it is by_exit. Pinning the BUG would mean this arm
    # goes red the moment somebody fixes it, which is the wrong way round.
    # What is asserted is the thing that must hold either way.
    check(verdict != 'by_exit' or rc_defect == 0,
          'if it is still wired by_exit, the exit code is still 0 -- i.e. the '
          'gap is real and has not silently closed')

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
