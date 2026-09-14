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
import closing_error                                          # noqa: E402
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


# ── DECLARED FILE-PREFIX ALIASES (2026-09-14) ──────────────────────────────
# app_of() above finds an app by looking for its FULL NAME in the text. That is
# right for prose and wrong for test filenames, because this repo does not name
# its test files after the app -- it names them after the app's API PREFIX or
# its trade. Measured: 27 of 27 SAIRNroofing tests are `roofing-*` or
# `roofing_*` and none contains the string `sairnroofing`, so the vertical read
# 0 suites / 0 traced and docs/MASTER-PLAN.md told an auditor that a built
# vertical with 27 test files had none.
#
# EVERY ENTRY IS DECLARED AND WAS READ, NEVER INFERRED. The temptation is to
# derive this from `ls api/*-auth.js` and stop; that would be a source rather
# than a guess, and it still would not do. `rf` is SAIRNroofing's auth prefix
# and matches ZERO test files, while `roofing` matches 27 -- a derivation from
# the prefix list alone finds none of them.
#
# MATCHED AS AN EXACT FIRST TOKEN OF THE BASENAME, never as a substring. This
# is the whole reason short aliases are safe: `sv` as a substring matches `csv`,
# and `sc` matches `scp_quotes`. Splitting the basename on -, _ and . and
# comparing the FIRST token to the alias makes `scp` and `sc` different answers
# rather than overlapping ones.
#
# THE ALIAS ALWAYS LOSES TO app_of(). Nothing already attributed changes, and a
# file that names a DIFFERENT app in its path stays where app_of() put it.
APP_ALIASES = {
    # alias        app                 why this one, in one line
    'roofing': ('sairnroofing',   'every roofing test is roofing-* or roofing_*; 27 files, none naming another app'),
    'rf':      ('sairnroofing',   'SAIRNroofing\'s API prefix (api/rf-auth.js). Matches nothing TODAY -- declared because the prefix is real and a future rf_* test must not land in PLATFORM the way the roofing-* ones did'),
    'dental':  ('sairndental',    'api/_lib/dental-*.test.js -- the BI, credential, GFE, photo and reminder halves'),
    'dnt':     ('sairndental',    'SAIRNdental\'s API prefix (api/dnt-auth.js)'),
    'sv':      ('sairnvet',       'SAIRNvet\'s API prefix (api/sv-auth.js) -- safe only because the match is token-exact, since `sv` is a substring of `csv`'),
    'mech':    ('sairnmechanical', 'SAIRNmechanical\'s API prefix (api/mech-auth.js)'),
    'alf':     ('sairncare',      'SAIRNcare\'s API prefix (api/alf-auth.js) -- the app is sairncare, the prefix is alf, and nothing in either name suggests the other'),
    'law':     ('sairnlaw',       'SAIRNlaw\'s API prefix (api/law-auth.js)'),
    'sc':      ('sairncode',      'SAIRNcode\'s API prefix (api/sc-auth.js). Token-exact, so it does NOT claim scp_* (SAIRNscape)'),
    'grd':     ('sairngrounds',   'SAIRNgrounds\' API prefix (api/grd-auth.js)'),
    'sb':      ('sairnbiz',       'SAIRNbiz\'s API prefix (api/sb-auth.js)'),
}

# ── WHAT IS DELIBERATELY *NOT* AN ALIAS, AND WHY ────────────────────────────
# Both of these are the largest app-shaped groups left in PLATFORM, and both
# would have been wrong. Written down so the next person does not have to
# re-derive the refusal -- and so that "PLATFORM" here is read as an answer
# rather than as a gap nobody got to.
REFUSED_ALIASES = {
    'sd': ('stonedesk', 25,
           'api/sd-data.js is the SHARED endpoint 17 apps write through. '
           'sd-data-dental-financial-tier, sd-data-mech-assets and '
           'sd-data-rf-supplier are tests about OTHER apps\' branches of it, so '
           'attributing the group to StoneDesk would be wrong in most of it.'),
    'deadline': ('sairnlaw', 37,
                 'MEASURED, not assumed: `grep -rln "legal-deadlines" '
                 '--include=*.html` returns sairnlaw.html AND sairnroofing.html. '
                 'TWO apps consume the deadline engine, so PLATFORM is the '
                 'CORRECT answer for these 37 files and not an artefact -- '
                 'exactly the case app_of() returns PLATFORM for on purpose.'),
    'run': (None, 81,
            'a harness prefix, not an app. tests/run_*_probe.py is this repo\'s '
            'naming for a probe runner and spans every subject there is.'),
}


def first_token(path):
    """The first -, _ or . delimited token of a path's basename."""
    return re.split(r'[-_.]', os.path.basename(path))[0].lower()


def app_of_test(path, app_names):
    """app_of() for a test FILE PATH, with the declared prefix aliases applied.

    Separate from app_of() on purpose. app_of() is also used on index-row PROSE,
    where "dental" in a sentence is not evidence the row is about SAIRNdental --
    applying the alias table there would turn a conservative answer into a
    guess. The aliases are a fact about how this repo NAMES FILES, so they only
    ever see a filename.

    THE CONFLICT CASE IS THE ONE THE PROBE CAUGHT (2026-09-14). app_of() decides
    "this names two apps, so PLATFORM" by counting FULL APP NAMES ONLY. Once
    aliases exist a path can name two apps with one of them by alias --
    `roofing_vs_stonedesk_probe.js` names SAIRNroofing by alias and StoneDesk
    outright -- and app_of() sees one app and answers confidently. Letting the
    alias simply "lose" there would attribute a two-app file to one of them,
    which is precisely the guess-presented-as-fact app_of() exists to refuse. So
    a disagreement between the two is PLATFORM, not a precedence question.
    """
    direct = app_of(path, app_names)
    hit = APP_ALIASES.get(first_token(path))
    alias = hit[0] if (hit and hit[0] in app_names) else None
    if direct != 'PLATFORM' and alias and alias != direct:
        return 'PLATFORM'
    if direct != 'PLATFORM':
        return direct
    return alias or 'PLATFORM'


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


def traced():
    """{test file: [sources that cite it]} -- the ONE definition of "traced".

    EXTRACTED 2026-09-13 SO A SECOND DOCUMENT CANNOT DISAGREE WITH THIS ONE.
    `docs/MASTER-PLAN.md` quoted this matrix as its source and said
    "Traceability is 86 of 273"; three days later the matrix said "135 of 328",
    and the plan's own totals line said "53 of 186" -- a third population
    presented as the same measurement. It had been computed by hand, once,
    against a numerator and a denominator that both then moved. This repo's own
    rule is to eliminate duplication at the SOURCE rather than to copy more
    carefully, so there is one function and both documents call it.

    Two citing sources, in the same order as this file's own authority list:
    GUARD_TESTS in the push gate (a requirement with a recorded defect behind
    it), and any open-work row that names a test file.
    """
    cited = {}
    for t, _guards, _why in guard_tests():
        cited.setdefault(t, []).append('GUARD_TESTS')
    for _app, _item, _status, ts in rows_citing_tests():
        for t in ts:
            cited.setdefault(t, []).append('index')
    return cited


def build():
    app_names = apps()
    tests = all_tests()

    # ── THE TRAVERSE MUST CLOSE BEFORE ANYTHING IS WRITTEN ──────────────────
    # `--check` here compares this document to what this generator produces
    # today -- both ends from the same instrument. It cannot see a source that
    # has gone silent, and this matrix's headline is a RATIO, so a source
    # returning nothing does not make the document obviously wrong: it makes
    # the denominator smaller and the percentage better.
    tv = closing_error.Traverse(OUT)
    # EVERY COUNT IS THE THING ITSELF, not the container holding it.
    # registry() returns a PAIR -- (REGISTRY, NOT_PROMOTED) -- so `len()` on it
    # is 2 whatever the registry contains, and a leg that reads 2 forever is a
    # leg that cannot go empty. Caught while writing this, which is the whole
    # argument for the counts being printed in the document.
    _reg, _not_promoted = registry()
    tv.leg('app files', len(app_names), "git ls-files '*.html'")
    tv.leg('test files on disk', len(tests), 'tests/**, api/*.test.js')
    tv.leg('open-work rows citing a test', len(rows_citing_tests()), INDEX)
    tv.leg('GUARD_TESTS entries', len(guard_tests()),
           'sairn_push_gate_hook.GUARD_TESTS')
    tv.leg('report-only registry', len(_reg),
           'report_only_checks.REGISTRY')
    tv.leg('recorded NOT-promoted decisions', len(_not_promoted),
           'report_only_checks.NOT_PROMOTED')
    tv.leg('numbered gate checks', len(dict(gate_checks())),
           'sairn_push_gate_hook.py')
    try:
        traverse_rows = tv.close()
    except closing_error.EmptyLeg as e:
        return None, 'REFUSING to generate -- the traverse did not close: %s' % e

    # `cited` comes from traced(), which docs/MASTER-PLAN.md also calls. The
    # sections below still APPEND to it as they render, which is harmless --
    # the same keys, from the same two sources -- and the point is that the
    # headline ratio and the one in the master plan now come from one function
    # rather than from one function and one afternoon of hand-counting.
    cited, L = traced(), []
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
    W('### Closing error -- what this document was derived FROM')
    W('')
    W('The headline on this page is a RATIO, which is the reason this section '
      'exists. A source that goes silent does not make the document look '
      'wrong -- it makes the denominator smaller and the percentage BETTER. '
      '`--check` cannot see it either, because it compares this file to what '
      'the generator produces today and both ends come from the same '
      'instrument. These are the sources the run that wrote this actually '
      'read; **any of them reaching zero is a refusal, not a smaller matrix.**')
    W('')
    W('```')
    for row in traverse_rows:
        W(row.rstrip())
    W('```')
    W('')
    W('A closed traverse is **not** a correct survey: it means no source is '
      'MISSING, not that any source is RIGHT.')
    W('')
    return '\n'.join(L) + '\n', None


def main(argv):
    doc, err = build()
    if err:
        print(err)
        return 2
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
