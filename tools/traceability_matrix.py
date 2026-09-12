"""traceability_matrix.py -- which requirement is proved by which test, DERIVED.

    python tools/traceability_matrix.py            # regenerate the document
    python tools/traceability_matrix.py --check    # fail if it is out of date

── WHAT THIS IS FOR ────────────────────────────────────────────────────────
The aviation-grade standard adopted 2026-09-04 calls for a requirements-to-test
matrix: each requirement mapped to the specific test proving it, auditable by
somebody who was not present when it was built. This is that, and the design
decision that matters is that it is DERIVED rather than written.

A HAND-WRITTEN MATRIX IN THIS REPO WOULD BE WRONG WITHIN HOURS. That is not a
guess -- the app map in sairn-guardian-v2 has been corrected six times, the
skill count twice, and CLAUDE.md carries a standing instruction to re-count
rather than trust its own numbers. A matrix is a claim about 158 test files and
299 index rows, which is the largest claim in the repo and the least likely to
be maintained by hand.

── WHAT AN AUDITOR ACTUALLY NEEDS, AND WHY THE GAPS ARE THE POINT ──────────
A matrix that lists only what IS covered reads as complete and cannot be
audited. Every section below therefore ends with what could NOT be mapped:
tests with no stated requirement, and requirements with no test. Those two
lists are the honest denominator, and they are the first thing an outside
reader should look at.

── THE FOUR SOURCES, IN DESCENDING AUTHORITY ───────────────────────────────
 1. GUARD_TESTS in tools/sairn_push_gate_hook.py -- (test, what it guards, the
    recorded defect). A requirement with a real incident behind it, and the
    only class that can BLOCK a push. Highest authority because the file's own
    rule is that a test with no real defect behind it does not belong there.
 2. The numbered checks in the push gate -- mechanically enforced requirements.
 3. REGISTRY in tools/report_only_checks.py -- (catches, why_it_matters,
    evidence). Enforced, report-only.
 4. docs/SAIRN-OPEN-WORK-INDEX.md rows that cite a test file -- the row's Item
    is the requirement and the cited file is the proof.

Nothing here is invented. Every row carries the source it came from so a reader
can check the claim against the file rather than against this document.

── THE STALENESS TRAP, AND HOW THIS AVOIDS IT ──────────────────────────────
docs/SAIRN-PROCESS-RULES.md section 1.8 is explicit that a GENERATED gate which
must be regenerated after every edit reproduces the silent-failure shape it
exists to catch -- see the superseded header on tools/sairn_build_load_gates.py.
The distinguishing question that section names: what does the artefact do when
it is out of date? A stale inventory is visibly wrong; a stale gate PASSES. So
generate the first and never the second. Accordingly this ships with
`--check`, which regenerates in memory and compares: if the committed document
no longer matches its sources, that is a finding, not a document somebody
forgot. It is registry-shaped so it can be promoted to report-only.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
OUT = os.path.join('docs', 'traceability-matrix.md')
INDEX = os.path.join('docs', 'SAIRN-OPEN-WORK-INDEX.md')
TEST_RE = re.compile(r'(?:tests?/[\w/.-]+\.(?:js|py)|api/[\w/.-]+\.test\.js)')

# App attribution is DERIVED from the app files git knows about, so a new app
# is covered the day it lands rather than the day somebody remembers this list.
def apps():
    r = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                       capture_output=True, text=True)
    return sorted(os.path.splitext(f)[0] for f in r.stdout.split('\n')
                  if f.strip() and '/' not in f)


def app_of(text, app_names):
    """Which app does this row or test belong to? PLATFORM when it is not one.

    Deliberately conservative: a row naming two apps is PLATFORM, because
    filing it under the first one mentioned would be a guess presented as a
    fact -- and a matrix that guesses is worse than one that says it does not
    know.
    """
    low = text.lower()
    hits = [a for a in app_names if a in low]
    # `stonedesk` also matches `stonedesk-hr`; prefer the longest single match.
    if hits:
        hits = sorted(set(hits), key=len, reverse=True)
        top = [h for h in hits if not any(h != o and h in o for o in hits)]
        if len(top) == 1:
            return top[0]
    return 'PLATFORM'


def all_tests():
    found = []
    for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            if f.endswith(('.js', '.py')):
                found.append(os.path.relpath(os.path.join(root, f), REPO)
                             .replace(os.sep, '/'))
    api = os.path.join(REPO, 'api')
    for f in sorted(os.listdir(api)):
        if f.endswith('.test.js'):
            found.append('api/' + f)
    lib = os.path.join(api, '_lib')
    if os.path.isdir(lib):
        for f in sorted(os.listdir(lib)):
            if f.endswith('.test.js'):
                found.append('api/_lib/' + f)
    return sorted(set(found))


def rows_citing_tests():
    """(requirement, [tests], status) for every index row that names a test."""
    out = []
    for line in io.open(os.path.join(REPO, INDEX), encoding='utf-8').read().split('\n'):
        if not line.startswith('|') or line.startswith('|---') or '| App |' in line:
            continue
        cells = re.split(r'(?<!\\)\|', line)
        if len(cells) < 5:
            continue
        item, status = cells[2].strip(), cells[3].strip()
        tests = sorted(set(TEST_RE.findall(line)))
        if tests:
            out.append((cells[1].strip(), item, status, tests))
    return out


def guard_tests():
    import sairn_push_gate_hook as g
    return list(getattr(g, 'GUARD_TESTS', []))


def registry():
    import report_only_checks as r
    return list(getattr(r, 'REGISTRY', [])), list(getattr(r, 'NOT_PROMOTED', []))


def gate_checks():
    src = io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
                  encoding='utf-8').read()
    seen, out = set(), []
    for m in re.finditer(r'#\s*[─-]+\s*CHECK (\d+):\s*([^\n─]+)', src):
        n = m.group(1)
        if n in seen:
            continue
        seen.add(n)
        out.append((int(n), m.group(2).strip().rstrip('-─ ').strip()))
    return sorted(out)


def strip_md(s):
    """Cells are prose with markdown. Flatten so a row cannot break the table."""
    s = re.sub(r'\s+', ' ', s)
    return s.replace('|', '\\|').strip()


def build():
    app_names = apps()
    tests = all_tests()
    cited, L = {}, []
    W = L.append

    W('# Requirements-to-test traceability matrix')
    W('')
    W('**GENERATED by `python tools/traceability_matrix.py`. Do not hand-edit '
      '-- your edit will be overwritten and, worse, will look authoritative '
      'until it is.** Run `--check` to find out whether this file still matches '
      'its sources; a mismatch is a finding, not a document somebody forgot.')
    W('')
    W('Every row names the SOURCE it was derived from, so an auditor checks the '
      'claim against that file rather than against this one. Nothing here is '
      'written by hand and nothing is inferred beyond what the source states.')
    W('')
    W('**The gaps are the point.** A matrix listing only what is covered reads '
      'as complete and cannot be audited, so every section ends with what could '
      'NOT be mapped. Read those first.')
    W('')

    # ── 1. GUARD tests: a requirement with a recorded defect behind it ───────
    W('## 1. Blocking guards -- a requirement with a recorded defect behind it')
    W('')
    W('Source: `GUARD_TESTS` in `tools/sairn_push_gate_hook.py`. These are the '
      'only tests that can BLOCK a push. The registry\'s own rule is that a '
      'test with no real defect behind it does not belong here.')
    W('')
    W('| App | Requirement (what it guards) | Proved by | The defect that put it here |')
    W('|---|---|---|---|')
    for t, guards, why in guard_tests():
        cited.setdefault(t, []).append('GUARD_TESTS')
        W('| %s | %s | `%s` | %s |'
          % (app_of(t + ' ' + guards + ' ' + why, app_names),
             strip_md(guards), t, strip_md(why)))
    W('')

    # ── 2. mechanically enforced push-gate checks ───────────────────────────
    W('## 2. Mechanically enforced at the push gate')
    W('')
    W('Source: the numbered `CHECK n:` blocks in '
      '`tools/sairn_push_gate_hook.py`. Derived from the source, not listed by '
      'hand, so a check added tomorrow appears here without anyone remembering.')
    W('')
    W('| # | Requirement |')
    W('|---|---|')
    for n, title in gate_checks():
        W('| %d | %s |' % (n, strip_md(title)))
    W('')

    # ── 3. report-only checkers ─────────────────────────────────────────────
    reg, notprom = registry()
    W('## 3. Enforced report-only')
    W('')
    W('Source: `REGISTRY` in `tools/report_only_checks.py`. Each entry carries '
      'the evidence from the run that promoted it.')
    W('')
    W('| Requirement (what it catches) | Tool | Evidence at promotion |')
    W('|---|---|---|')
    for e in reg:
        W('| %s | `%s` | %s |' % (strip_md(e.get('catches', '')),
                                  e.get('tool', ''), strip_md(e.get('evidence', ''))))
    W('')
    W('**Deliberately NOT enforced, with the reason recorded** -- a decision, '
      'not an oversight:')
    W('')
    for tool, why in notprom:
        W('- `%s` -- %s' % (tool, strip_md(why)))
    W('')

    # ── 4. requirements traced through the open-work index ──────────────────
    W('## 4. Requirements traced through the open-work index')
    W('')
    W('Source: rows of `docs/SAIRN-OPEN-WORK-INDEX.md` that name a test file. '
      'The row states the requirement; the cited file is the proof.')
    W('')
    by_app = {}
    for app, item, status, ts in rows_citing_tests():
        key = app_of(app + ' ' + item, app_names)
        by_app.setdefault(key, []).append((item, status, ts))
        for t in ts:
            cited.setdefault(t, []).append('index')
    for key in sorted(by_app):
        W('### %s' % key)
        W('')
        W('| Requirement | Status | Proved by |')
        W('|---|---|---|')
        for item, status, ts in by_app[key]:
            W('| %s | %s | %s |'
              % (strip_md(item)[:400], strip_md(status)[:200],
                 ', '.join('`%s`' % t for t in ts)))
        W('')

    # ── 5. THE GAPS ─────────────────────────────────────────────────────────
    untraced = [t for t in tests if t not in cited]
    W('## 5. THE GAPS -- read this section first')
    W('')
    W('**%d of %d test files are traced to a stated requirement. %d are not.**'
      % (len(tests) - len(untraced), len(tests), len(untraced)))
    W('')
    W('An untraced test is not a bad test. It means no source in this repo '
      'states what it is for in a form this can read, so an auditor cannot '
      'tell what would be lost if it were deleted. The fix is one line in the '
      'open-work index or a `GUARD_TESTS` entry -- not a new document.')
    W('')
    for t in untraced:
        W('- `%s`' % t)
    W('')
    # ── A CITATION POINTING AT NOTHING IS A BROKEN LINK ─────────────────
    # An auditor following a row to its proof and finding no file is exactly
    # the claim-versus-reality failure this repo keeps recording. Found on the
    # first run: two of them.
    absent = sorted(t for t in cited if not os.path.isfile(os.path.join(REPO, t)))
    W('### Citations pointing at a file that does not exist')
    W('')
    if absent:
        W('**%d.** A row names a test as its proof and the file is not there, '
          'so the requirement is UNPROVED however the row reads. Some of these '
          'are prose placeholders rather than real citations -- this cannot '
          'tell the difference, so it reports both and says so.' % len(absent))
        W('')
        for t in absent:
            W('- `%s`' % t)
    else:
        W('None. Every cited test file exists.')
    W('')
    W('### What this matrix cannot tell you')
    W('')
    W('- **That a traced test actually PROVES its requirement.** It reports '
      'that a source names the two together. Whether the assertion is strong '
      'enough is what the mutation probes answer, and only some tests have one.')
    W('- **That an untraced test proves nothing.** Only that nothing says what '
      'it is for.')
    W('- **Anything about code with no test at all.** A requirement nobody has '
      'written down anywhere is invisible here by construction, and that is '
      'the largest unknown on this page.')
    W('')
    return '\n'.join(L) + '\n'


def main(argv):
    doc = build()
    path = os.path.join(REPO, OUT)
    if '--check' in argv:
        try:
            have = io.open(path, encoding='utf-8', newline='').read()
        except IOError:
            print('FAIL: %s does not exist. Run: python tools/traceability_matrix.py'
                  % OUT)
            return 1
        if have.replace('\r\n', '\n') != doc.replace('\r\n', '\n'):
            print('FAIL: %s no longer matches its sources.' % OUT)
            print('A requirement, a guard test or a registry entry has changed '
                  'and the matrix was not regenerated. That is a finding: the '
                  'document an auditor would read is not the one the repo '
                  'supports. Regenerate with:')
            print('    python tools/traceability_matrix.py')
            return 1
        print('OK: %s matches its sources.' % OUT)
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, 'w', encoding='utf-8', newline='').write(doc)
    print('wrote %s (%d lines)' % (OUT, doc.count('\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
