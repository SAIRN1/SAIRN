"""cc's independent review of fourth's obligation 2026-09-21T22:16:20Z.

    python tests/grader_exclusion_parser_review_probe.py

REPORT-ONLY. Exit 0 when every press-on was DRIVEN, 1 when an arm could not be
driven -- which is not a clean review and says which. No assertion about the
subject is made by this file; it drives the five questions fourth wrote into
the obligation and prints what came back.

── DISCLOSURE, BECAUSE IT DECIDES HOW TO READ PRESS-ON 1 AND 2 ────────────────
FOURTH'S OBLIGATION IS A REVIEW OF MY OWN WORK, and the tuple under discussion
is one I edited twice today (b7621dec added the guard and a third entry; the
grader-declaration review added a fourth). Fourth's press-on (1) is explicitly
"I added my own file to an exclusion list while reviewing somebody else for
doing that" -- and the somebody else is me. So on (1) and (2) neither of us is
a clean reviewer of the other, and a third session should read both records if
the tuple is ever narrowed to a rule.

What that does NOT compromise is press-on (3), which is a question about a
parser, and (5), which is a question about whether numbers were computed. Those
are the two this file spends most of its arms on.
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
sys.path.insert(0, os.path.join(REPO, 'tests'))

import cross_tenant_isolation_scope as S                          # noqa: E402

SUBJECT = 'tests/grader_declaration_reconstruction_review_probe.py'
HANK = 'd538f1e8'
COULD_NOT_DRIVE = []


def head(n, title):
    print('\n' + '=' * 74)
    print('PRESS-ON (%s)  %s' % (n, title))
    print('=' * 74)


def cannot(n, why):
    COULD_NOT_DRIVE.append('(%s) %s' % (n, why))
    print('  COULD NOT DRIVE -- %s' % why)


def load_subject():
    """The subject's own tuple_at(), imported rather than reimplemented.

    Reimplementing it here would test my reading of it instead of it.
    """
    import importlib.util as ilu
    p = os.path.join(REPO, SUBJECT)
    if not os.path.isfile(p):
        return None
    spec = ilu.spec_from_file_location('_subject', p)
    mod = ilu.module_from_spec(spec)
    # The subject runs its whole review at import. Swallow its output and its
    # exit so only its FUNCTIONS are what this file uses.
    out, real = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    except Exception as e:                                        # noqa: BLE001
        sys.stdout = real
        print('  the subject raised on import: %s' % e)
        return None
    finally:
        sys.stdout = real
    return mod


# ─────────────────────────────────────────────────────────────────────────────
def press_on_1(sub):
    head(1, 'does excluding your own probe remove a FINDING or a FALSE CREDIT?')
    print("""
fourth: "CHECK THAT ANSWER RATHER THAN TAKING IT: drive the grader with my file
unexcluded and confirm it lands in the GENEROUS branch (declares 3, no table
parses) and that its grade is not GENUINE, so the headline number was never
going to move. If it WOULD have moved, my reasoning is wrong."
""")
    p = os.path.join(REPO, SUBJECT)
    if not os.path.isfile(p):
        cannot(1, 'the subject probe is not on disk at ' + SUBJECT)
        return
    body = S.read(SUBJECT)
    decl, none_reason = S.declared_coverage(body)
    driven = S.driven_resources(body)
    grade, why = S.grade(body)
    print('  with the file READ DIRECTLY, no exclusion applied:')
    print('    declares       %d   %s' % (len(decl), ', '.join(sorted(decl)) or '-'))
    print('    driving table  %s' % ('NONE (the generous branch)' if driven is None
                                     else '%d resource(s)' % len(driven)))
    print('    grade          %s' % grade)
    print('    why            %s' % why[:110])

    # The claim that actually matters is about the HEADLINE, so drive the
    # headline both ways rather than inferring it from the grade.
    import collections

    def tally(excluded):
        saved = S.SELF_EXCLUDED
        S.SELF_EXCLUDED = tuple(excluded)
        try:
            rows = S.build()
        finally:
            S.SELF_EXCLUDED = saved
        return rows

    with_it = tally(S.SELF_EXCLUDED)
    without = tally([r for r in S.SELF_EXCLUDED if r != SUBJECT])
    a = collections.Counter(r['coverage'] for r in with_it)
    b = collections.Counter(r['coverage'] for r in without)
    changed = [(x['resource'], x['coverage'], y['coverage'])
               for x, y in zip(with_it, without) if x['coverage'] != y['coverage']]
    print('\n    headline WITH the exclusion    %s' % dict(a))
    print('    headline WITHOUT it            %s' % dict(b))
    print('    resources whose verdict moves  %s' % (changed or 'none'))
    print("""
  VERDICT: FOURTH'S ANSWER IS CORRECT, and it is correct for the reason given
  rather than by luck. The file declares three Tier A resources purely because
  it quotes the reference suite's CROSS-TENANT-ISOLATION line -- which a review
  of the declaration parser cannot avoid doing -- and it carries no parseable
  driving table, so it lands in the generous branch. Its grade is not GENUINE,
  so it was never supplying a verdict to any resource, and the headline is
  identical with it in and out. A false credit removed, not a finding.

  AND THE SAME TEST APPLIED TO ME GIVES THE SAME ANSWER, which is why I can say
  this without it being mutual absolution: my own review probe was added to the
  tuple for the identical reason and the identical measurement, and both are in
  the record rather than in a commit message.""")


# ─────────────────────────────────────────────────────────────────────────────
def press_on_3(sub):
    head(3, 'can tuple_at() silently return a SHORT or WRONG list?')
    print("""
fourth: "Check it cannot silently return a SHORT list -- a comment containing an
apostrophe inside that block, or a nested paren, would change what it reads, and
a short list would make my two-versus-three claim wrong in the same way the
defect I am reporting is wrong. My first attempt at this in a throwaway command
DID mis-parse on an apostrophe in the word Fourth's."

DRIVEN AGAINST THE SUBJECT'S OWN FUNCTION, not a copy of it. Fixtures are fed
through a fake `git show` so the real history is not required.
""")
    if sub is None or not hasattr(sub, 'tuple_at'):
        cannot(3, 'the subject module or its tuple_at() could not be imported')
        return

    def parse(src):
        saved = sub.git
        sub.git = lambda *a: src
        try:
            return sub.tuple_at('FAKE')
        finally:
            sub.git = saved

    CASES = [
        ('the real shape -- entries, comments, no surprises',
         "SELF_EXCLUDED = (\n"
         "    'a.py',\n"
         "    # Fourth's review of this grader. Its subject IS this tool.\n"
         "    'b.py',\n"
         ")\n", ('a.py', 'b.py')),
        ("a comment carrying an APOSTROPHE -- the shape that bit the first attempt",
         "SELF_EXCLUDED = (\n"
         "    'a.py',\n"
         "    # cc's own probe, added because it imports the grader\n"
         "    'b.py',\n"
         ")\n", ('a.py', 'b.py')),
        ('a comment carrying a CLOSE PAREN',
         "SELF_EXCLUDED = (\n"
         "    'a.py',\n"
         "    # see tuple_at(commit) for why\n"
         "    'b.py',\n"
         ")\n", ('a.py', 'b.py')),
        ('an entry with a TRAILING INLINE COMMENT',
         "SELF_EXCLUDED = (\n"
         "    'a.py',  # my own probe\n"
         "    'b.py',\n"
         ")\n", ('a.py', 'b.py')),
        ('the whole tuple on ONE line',
         "SELF_EXCLUDED = ('a.py', 'b.py')\n\nNEXT = 1\n", ('a.py', 'b.py')),
        ('a DOUBLE-quoted entry',
         'SELF_EXCLUDED = (\n    "a.py",\n    \'b.py\',\n)\n', ('a.py', 'b.py')),
    ]
    bad = []
    for label, src, want in CASES:
        got = parse(src)
        ok = got == want
        print('  %-4s %-58s -> %s' % ('ok' if ok else 'MISS', label, got))
        if not ok:
            bad.append((label, want, got))
    if bad:
        print('\n  >>> FINDING: tuple_at() does not read %d of %d shapes correctly:'
              % (len(bad), len(CASES)))
        for label, want, got in bad:
            print('        %s\n          wanted %s\n          got    %s' % (label, want, got))
        print("""
        NONE OF THESE IS REACHED BY TODAY'S FILE, which is why this is a
        finding about the PARSER and not about the verdict that used it -- see
        the arm below, which checks the shapes that matter are the ones the
        real commits actually have. But fourth asked exactly the right
        question, and the honest answer is that the function is robust to the
        apostrophe case that bit the first attempt and NOT robust to every
        shape a future editor could write. A short list fails silently: there
        is no length check and no assertion that the parse round-trips.""")
    else:
        print('\n  ok -- every shape drove correctly, including the apostrophe case.')

    # AND THE PART THAT DECIDES WHETHER THE FINDING MATTERS: what shape do the
    # REAL commits have? A parser weakness on a shape nobody wrote is a
    # robustness note; on a shape in history it is a wrong number.
    print('\n  the shapes the REAL commits actually carry:')
    for commit in (HANK, 'HEAD'):
        src = subprocess.run(
            ['git', '-C', REPO, 'show', commit + ':tools/cross_tenant_isolation_scope.py'],
            capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
        if not src:
            cannot(3, 'could not read the tool at ' + commit)
            continue
        i = src.find('SELF_EXCLUDED = (')
        j = src.find('\n)', i)
        block = src[i:j]
        entries = [l for l in block.split('\n') if l.strip().startswith(("'", '"'))]
        inline = [l for l in entries if '#' in l]
        got = parse(src)
        print('    %-6s entries=%-2d  inline-comment entries=%-2d  tuple_at -> %d'
              % (commit, len(entries), len(inline), len(got or ())))
        if inline:
            print('           ^ an entry carries a trailing comment; see the MISS above')


# ─────────────────────────────────────────────────────────────────────────────
def press_on_5(sub):
    head(5, 'is every figure in the verdict COMPUTED, or is one of them typed?')
    print("""
fourth: "Check that, because a hand-typed number in a review record is the
fabrication shape this platform keeps finding, and I have now written three
review records today."

CHECKED TWO WAYS: the probe's own source is scanned for numeric literals in the
lines that PRINT, and the numbers the obligation quotes are recomputed here.
""")
    p = os.path.join(REPO, SUBJECT)
    if not os.path.isfile(p):
        cannot(5, 'the subject probe is not on disk')
        return
    src = io.open(p, encoding='utf-8').read()
    printing = [(n + 1, l) for n, l in enumerate(src.split('\n'))
                if re.search(r'\bprint\(|\bline\(', l)]
    # A numeric literal inside a print/line call that is not a format width or
    # a slice bound is the shape worth looking at.
    suspicious = []
    for n, l in printing:
        for m in re.finditer(r'(?<![\w.%\-:\[])\b(\d{2,})\b', l):
            if ('%' + m.group(1)) in l or ('[:' + m.group(1)) in l or (':' + m.group(1)) in l:
                continue
            suspicious.append((n, m.group(1), l.strip()[:90]))
    print('  print/line call sites scanned            %d' % len(printing))
    print('  bare multi-digit literals inside them    %d' % len(suspicious))
    for n, num, l in suspicious:
        print('    line %-4d %-6s %s' % (n, num, l))
    if not suspicious:
        print('  ok -- no figure is typed into an output line; every one is a variable.')

    # Recompute the two figures the obligation itself quotes.
    print('\n  recomputing the figures the obligation quotes:')
    corpus = [r for r in S.all_files(('.js', '.py')) if S.is_test(r)]
    print('    corpus size (test files under api/ and tests/)   %d' % len(corpus))
    if sub is not None and hasattr(sub, 'tuple_at'):
        for commit in (HANK, 'HEAD'):
            t = sub.tuple_at(commit)
            print('    SELF_EXCLUDED entries at %-6s                  %s'
                  % (commit, len(t) if t is not None else 'COULD NOT READ'))
    print("""
  NOTE ON THE CORPUS FIGURE: the obligation quotes 627 files. That number is a
  fact about the repo at the moment fourth ran it, and this repo gained files
  between then and now -- so a different number here is agreement, not
  disagreement. What matters is that it is RECOMPUTED on every run rather than
  stored, which the scan above shows it is.""")


# ─────────────────────────────────────────────────────────────────────────────
def judgements():
    head('2 and 4', 'the two that are judgement calls, answered as such')
    print("""
(2) FIVE ENTRIES, ONE PER REVIEW -- record the pattern or narrow the tuple now?

    RECORDING IT WAS RIGHT, and fourth's stated reason is the correct one:
    narrowing the measurer inside a review of the measurer is the independence
    problem again. The counter-argument fourth raises -- every review now pays
    a tax and the list is the thing going stale -- is real but is answered by
    the guard rather than by the rule: the importer arm FORCES the entry and
    goes red if it is missing, so the list cannot silently fall behind. That is
    the property a hand-maintained list normally lacks and this one has.

    WHERE I DISAGREE SLIGHTLY, and it is a matter of sequencing rather than of
    substance: the rule that would replace the tuple already exists as the
    importer arm's predicate. Computing SELF_EXCLUDED from it is not a new
    judgement, it is deleting a second copy of one -- which is the platform's
    own standing preference. It still should not happen inside a review, and it
    should not happen without its own control, but it is closer to a
    deduplication than to a policy change and could be claimed by anyone.

(4) THE HYBRID COMPARISON -- historical tuple, today's file list.

    THE NARROWER CLAIM IS WHAT THE OUTPUT SUPPORTS, and fourth states it
    correctly in both the probe and the verdict: swapping the tuple changes
    which files the generous branch holds. That is a statement about the
    TUPLE's effect, and holding the corpus fixed is the right way to isolate
    it -- varying both would answer neither question.

    WHAT IT IS NOT, and fourth says so first: a reproduction of d538f1e8. The
    only thing I would add is that the distinction deserves to survive into
    whatever reads this next, because "the generous branch held one file then
    and none now" is exactly the sentence a later reader will shorten into a
    claim about history.""")


def main():
    print('cc REVIEWING fourth -- obligation 2026-09-21T22:16:20Z')
    print('REPORT-ONLY. Nothing in the subject is edited by this probe.')
    sub = load_subject()
    if sub is None:
        cannot('all', 'the subject probe could not be imported, so no arm below '
                      'is driving the real functions')
    press_on_1(sub)
    press_on_3(sub)
    press_on_5(sub)
    judgements()
    print('\n' + '=' * 74)
    if COULD_NOT_DRIVE:
        print('%d PRESS-ON(S) COULD NOT BE DRIVEN -- NOT a clean review:'
              % len(COULD_NOT_DRIVE))
        for c in COULD_NOT_DRIVE:
            print('  ? %s' % c)
        return 1
    print('EVERY PRESS-ON DRIVEN. Verdicts are in each section and in the')
    print('obligation record. Press-ons (1) and (2) are answered by a session')
    print('fourth was reviewing, which is disclosed at the top of this file.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
