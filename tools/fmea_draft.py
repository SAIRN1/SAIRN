"""A FIRST-DRAFT risk analysis for a file, seeded entirely from what has
already gone wrong here.

    python tools/fmea_draft.py <path> [<path> ...]
    python tools/fmea_draft.py <path> --json
    python tools/fmea_draft.py <path> --save        # writes docs/fmea/<slug>.json

── WHAT THIS IS, AND THE ONE THING IT MUST NEVER BECOME ──────────────────
A generator that emits plausible-sounding risks is a FABRICATION ENGINE. It
would read as insight, nobody could check it, and the first person to act on a
made-up risk would be worse off than with no document at all. This platform has
a name for that shape -- a number no function computes -- and a checker for it.

So the rule here is absolute: EVERY EMITTED RISK CITES THE SPECIFIC RECORD OR
RULE IT MATCHED. No citation, no risk. When nothing matches, it says so and
emits nothing, and it always reports how many candidates it considered so a
short answer cannot be mistaken for a clean one.

Two evidence sources, both already in the repo and both maintained for their
own reasons:

  docs/defect-density-register.json   46 confirmed defects with the files they
                                      touched, the layer, the severity and how
                                      each was detected.
  docs/SAIRN-PROCESS-RULES.md         the numbered standing lessons. Each one
                                      below carries a DETECTOR -- a mechanical
                                      test over the target -- so a lesson only
                                      fires when something about this file
                                      actually matches it. A rule that fired on
                                      everything would be a horoscope.

── WHY HISTORY AND NOT A CHECKLIST ───────────────────────────────────────
A generic FMEA checklist asks what could fail in the abstract and gets abstract
answers. Every risk here has already happened, in this repo, with a commit
behind it. That is a much narrower claim and a much more useful one: not "this
could be wrong" but "this went wrong before, here, and here is the commit".

── WHAT IT CANNOT SEE, said here rather than discovered later ────────────
  * a risk with no precedent. This is seeded from history and cannot invent a
    first instance -- it is a FIRST DRAFT, and the un-precedented risks are
    exactly the part a human still has to add;
  * severity. It reports the severity of the PRIOR defect, never a prediction
    for this one;
  * the rules with no detector yet. They are listed by number on every run
    rather than silently skipped -- an undisclosed gap in a risk tool is the
    same failure one level up.

Exit 0 always, unless a source is unreadable (2). This reports; it never gates.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')
RULES = os.path.join(REPO, 'docs', 'SAIRN-PROCESS-RULES.md')
FMEA_DIR = os.path.join(REPO, 'docs', 'fmea')


def _today():
    """The date a draft is written. Read from HEAD's commit date, not the
    system clock: every other date in this pipeline comes from git, and mixing
    two clocks is how a draft ends up looking a day older than the defect it is
    being scored against."""
    import subprocess
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cI'], cwd=REPO,
                             capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
        return out[:10]
    except Exception:
        return ''

# ── THE DETECTORS ─────────────────────────────────────────────────────────
# Each maps a standing lesson to a MECHANICAL test over the target's source.
# The test is deliberately narrow: a detector that fires on every Python file
# turns the whole report into noise and the tool gets switched off, which is
# the nav_panel_check failure (it reported all 26 SAIRNfreedom panels
# unreachable because it scanned <button> and that app navigates with divs).
#
# Each entry: (rule id, one-line risk, what to check, detector)
# ── CALIBRATION, AND WHY EVERY DETECTOR CARRIES A FIRE RATE ───────────────
# The first version of this table was measured across all 150 files in tools/
# and tests/ before it was trusted, and it was BADLY tuned: 2.3 fired on 90% of
# files, 1.10 on 57%, 1.4 on 51%. A rule that fires on half the repo is a
# horoscope -- it is right often enough to feel insightful and carries no
# information. Worse, 1.1 fired on 48% and still MISSED md_table_check.py,
# which is unmistakably a checker: too broad and wrong at the same time.
#
# So each detector below encodes the SPECIFIC shape from the incident rather
# than a generic idiom, and `--rates` measures every one against the real tree
# so the calibration is a number anybody can re-derive rather than a claim.
def _probe_exists(path):
    """Is there a plant-the-defect probe for this checker?"""
    stem = os.path.basename(path)[:-3]
    for cand in ('tests/run_%s_probe.py' % stem,
                 'tests/%s_probe.py' % stem,
                 'tests/run_%s_probe.py' % stem.replace('_check', ''),
                 'tests/claims/run_%s_probe.py' % stem.replace('_check', '')):
        if os.path.exists(os.path.join(REPO, cand)):
            return True
    return False


def _d_checker_without_probe(src, path):
    # The risk is not "this is a checker". It is a checker WITH NO CONTROL
    # proving it can fire -- which is the only half of 1.1 a single file can
    # answer.
    if not path.startswith('tools/') or not path.endswith('.py'):
        return False
    looks_like = bool(re.search(r'REPORT ONLY|report-only|findings|\bCLEAN\b|'
                                r'sys\.exit\(1 if|return 1 if', src))
    return looks_like and not _probe_exists(path)


def _d_greps_source(src, path):
    # Pattern-matches the TEXT of a source file it opened -- including via a
    # compiled pattern (`PAT.match(line)`), which the first version missed.
    reads = bool(re.search(r"io\.open\(|open\([^)]*encoding|readFileSync", src))
    matches = bool(re.search(r're\.(search|findall|finditer|match|compile)\(|'
                             r'\b[A-Z_]{3,}\.(search|match|findall|finditer)\(', src))
    strips = bool(re.search(r'strip_comments|comment_quote_check|COMMENT-STRIPPED', src))
    return reads and matches and not strips


def _d_string_anchor(src, path):
    # A literal anchor used to LOCATE a position in another file.
    return bool(re.search(r'\bMUTATIONS\b|\.index\(\s*[\'"]|indexOf\(\s*[\'"]', src))


def _d_git_write_verb(src, path):
    # 1.4 is not "shells out". It is a command that writes while sounding like
    # a read -- `git checkout <ref> -- path` writes AND stages.
    return bool(re.search(r"['\"]checkout['\"]|['\"]reset['\"]|['\"]stash['\"]|"
                          r"['\"]add['\"]|git checkout|git reset", src)) and \
        'subprocess' in src


def _d_falsy_from_except(src, path):
    # Returns a falsy value from inside an error handler -- the shape where the
    # caller prints success anyway.
    return bool(re.search(r'except[^\n]*:\s*\n(?:[^\n]*\n){0,4}?\s*return (None|False)\b', src))


def _d_fixed_window(src, path):
    return bool(re.search(r'\[\s*:\s*\d{3,}\s*\]|'
                          r'\b(WINDOW|LIMIT|MAX_[A-Z_]+|_CHARS|SAMPLE)\s*=\s*\d{3,}', src))


def _d_generates_a_gate(src, path):
    # Writes a document that something else then READS to decide -- the
    # generated-gate shape. Writing a report is fine; writing an input to a
    # gate is not.
    writes_doc = bool(re.search(r"open\([^)]*['\"]w['\"]", src)) and 'docs/' in src
    return writes_doc and bool(re.search(r'--check\b|regenerat|matches its sources', src))


def _d_unordered_iteration(src, path):
    # dict.items()/keys() are insertion-ordered in modern Python; SETS are not.
    return bool(re.search(r'for \w+ in set\(|for \w+ in \{[^}]|in sorted\(set\(', src)) or \
        bool(re.search(r'\bset\([^)]*\)\s*[-|&]', src))


def _d_reads_dated_artefact(src, path):
    # A timestamp FIELD, not the word "snapshot" -- 1.10 is about reasoning
    # from a dated input, not about the subject's name.
    return bool(re.search(r'_generated_at|getmtime|st_mtime|captured_when|'
                          r'capture_age|--date=', src))


def _d_markdown_table(src, path):
    return bool(re.search(r"split\(\s*['\"]\|['\"]", src))


def _d_hardcoded_expected_count(src, path):
    # The storage-quota shape: an expected COUNT pinned in a second file, which
    # goes stale on the next correct change and then reads as a defect.
    return bool(re.search(r'(check|assert\w*)\([^\n]{0,120}(match|len)\([^\n]{0,60}\)\s*,\s*\d+\s*\)', src))


def _d_sql_credentials(src, path):
    return path.endswith('.sql') and bool(re.search(r'_employee_auth|credential', src, re.I))


DETECTORS = [
    ('1.1', 'a check that cannot fail is indistinguishable from one that is not running',
     'make it fail on purpose before trusting it; add the plant-the-defect probe in the same commit',
     _d_checker_without_probe),
    ('1.2', 'matching a source file by TEXT cannot tell code from a comment or string describing code',
     'search a comment-stripped copy, or parse; if the subject IS the comment, declare it',
     _d_greps_source),
    ('1.3', 'an exact-string anchor verifies UNIQUENESS, never that it still points at the right code',
     'assert the anchor matches exactly once AND read what it matched before acting',
     _d_string_anchor),
    ('1.4', 'a read-only-sounding command can write -- `git checkout <ref> -- path` writes AND stages',
     'confirm each shelled command writes nothing; prefer `git show <ref>:<path>`',
     _d_git_write_verb),
    ('1.5', 'a function reporting failure by return value needs a caller that reads it',
     'check every caller; the expensive part of a false success is the confident line after it',
     _d_falsy_from_except),
    ('1.7', 'a fixed window or limit silently exempts whatever it does not reach',
     'report what was NOT looked at; a scan that covered 31% and says "clean" is a wrong answer',
     _d_fixed_window),
    ('1.8', 'a GENERATED artefact is safe; a generated GATE passes when stale',
     'ask what this does when out of date -- visibly wrong, or quietly passing?',
     _d_generates_a_gate),
    ('1.9', 'set and dict iteration order makes a checker answer differently on identical input',
     'sort before emitting; run it twice under different PYTHONHASHSEED',
     _d_unordered_iteration),
    ('1.10', 'a verdict from a dated input is only true as of that input, not as of now',
     'scope the output to the input instant and print its age',
     _d_reads_dated_artefact),
    ('2.1', 'splitting a markdown row on `|` breaks on a pipe that is content',
     'rebuild the row whole, anchored on a unique substring',
     _d_markdown_table),
    ('2.3', 'a count printed here and elsewhere becomes two live numbers',
     'name the single source that moves when the thing changes, and point at it',
     _d_hardcoded_expected_count),
    ('3.4', 'SQL writing credential rows can leave a licence unrecoverable through the API',
     'zero rows, or at least one ACTIVE provisioner -- read the app\'s own PROVISIONING_ROLES',
     _d_sql_credentials),
]

# Rules with NO detector yet. Listed on every run rather than silently skipped:
# an undisclosed gap in a risk tool is the failure one level up.
NO_DETECTOR = {
    '1.6': 'a fix verified on one copy is not verified if a second copy exists '
           '(needs a whole-repo duplicate scan, not a single-file test)',
    '2.2': 'not written until committed (a property of the workflow, not of a file)',
    '3.1': 'run every guardian check before pushing',
    '3.2': 'live-verify after pushing',
    '3.3': 'seed files must already match the live licence',
    '4.1': 'claim a gate before running it',
    '4.2': 'a claim is not a lock',
    '4.3': 'a block is a claim to verify, not a fact',
    '5': 'verification discipline (a property of the report, not of a file)',
}


def load_register():
    with io.open(REGISTER, encoding='utf-8') as fh:
        return json.load(fh).get('records', [])


def rule_titles():
    """{id: heading} from the process rules, so a citation names the real section."""
    out = {}
    try:
        for line in io.open(RULES, encoding='utf-8'):
            m = re.match(r'^###\s+(\d+(?:\.\d+)?)\s+(.*?)\s*$', line)
            if m:
                out[m.group(1)] = m.group(2)
    except Exception:
        pass
    return out


# A draft for a WORKLOG or an index is a category error: those files RECORD
# defects rather than having them, so every risk-matching word appears in them
# and any scorer reading them produces confident nonsense. Learned by doing it
# -- the first prediction run scored 38% and all five hits came from one
# worklog draft. Section 1.2 of the process rules, one level up.
NOT_A_CODE_TARGET = re.compile(r'(^|/)SAIRN-ACTIVE-WORK|^docs/|\.md$')


def analyse(path, records, titles):
    rel = path.replace(os.sep, '/')
    if rel.startswith('./'):
        rel = rel[2:]
    full = os.path.join(REPO, rel)
    src = ''
    if os.path.isfile(full):
        try:
            src = io.open(full, encoding='utf-8', errors='replace').read()
        except Exception:
            src = ''

    if NOT_A_CODE_TARGET.search(rel):
        return {'target': rel, 'exists': bool(src), 'app_matched': None, 'risks': [],
                'refused': 'this file RECORDS defects rather than having them -- a '
                           'draft for a worklog or an index matches prose about '
                           'failures, not code that can fail',
                'considered': {'defect_records': len(records), 'matched_this_file': 0,
                               'detectors_run': 0, 'detectors_fired': []},
                'no_detector_yet': sorted(NO_DETECTOR.keys())}

    risks = []

    # ── evidence 1: this exact file has a history ──────────────────────
    same_file = [r for r in records if rel in (r.get('files') or [])]
    for r in same_file:
        risks.append({
            'source': 'defect-register',
            'basis': 'THIS FILE has a confirmed defect on record',
            # The SUMMARY, not the commit subject. One commit can fix several
            # distinct defects -- three of sairnvet's share 6fde9cea7b84 -- and
            # printing the subject three times reads as padding while hiding
            # that they are different failures.
            'risk': (r.get('summary') or r.get('subject') or '').strip(),
            'cite': r.get('commit', ''),
            'date': r.get('date', ''),
            'prior_severity': r.get('severity', ''),
            'detected_by': r.get('detection_method', ''),
            # ── CARRIED SO THE RISK CAN EVER BE SCORED (2026-09-14) ────────
            # fmea_prediction_check.matched() scores ONLY on a rule citation
            # and skips any risk whose cite is a commit SHA -- which is every
            # risk in this block. MEASURED over the 12 drafts on disk before
            # this line existed: 19 of 274 risks, 6.9%, could EVER produce a
            # PREDICTED. Drafting more files would have grown coverage while
            # the scoreable surface stayed flat.
            #
            # The rule id is the register's own, set deliberately per record
            # with a confidence flag, so this is exact-id equality and not the
            # word-overlap matcher that scored 38% with five false positives.
            # A `not-citable` record carries [] and still contributes nothing,
            # which is the escape hatch that stops manufactured agreement.
            'rules': list(r.get('rules') or [])
        })

    # ── evidence 2: the same app, different file ───────────────────────
    # DELIBERATELY NOT GIVEN `rules`, and this is the load-bearing half of the
    # change above. A PLATFORM file inherits ~34 same-app risks; if their rule
    # ids counted, almost every PLATFORM draft would carry the commonest few
    # and any later defect citing one would score PREDICTED. That prediction
    # would mean "this platform has had a defect of this kind before", which is
    # true of everything and is cheap agreement. A rule that has already bitten
    # THIS FILE is a real prediction; the same rule biting a sibling is
    # background.
    app = None
    base = os.path.basename(rel)
    for r in records:
        for f in (r.get('files') or []):
            if os.path.basename(f) == base:
                app = r.get('app')
    if app is None:
        stem = base.split('.')[0].lower()
        for r in records:
            if str(r.get('app', '')).lower() == stem:
                app = r.get('app')
                break
    if app:
        same_app = [r for r in records
                    if r.get('app') == app and rel not in (r.get('files') or [])]
        for r in same_app:
            risks.append({
                'source': 'defect-register',
                'basis': 'the same app (%s) has this defect on record' % app,
                'risk': (r.get('summary') or r.get('subject') or '').strip(),
                'cite': r.get('commit', ''),
                'date': r.get('date', ''),
                'prior_severity': r.get('severity', ''),
                'detected_by': r.get('detection_method', '')
            })

    # ── evidence 3: a standing lesson whose DETECTOR fires on this file ─
    fired = []
    for rid, risk, action, det in DETECTORS:
        if not src:
            continue
        try:
            hit = det(src, rel)
        except Exception:
            hit = False
        if hit:
            fired.append(rid)
            risks.append({
                'source': 'process-rules',
                'basis': 'section %s applies -- %s' % (rid, titles.get(rid, '')),
                'risk': risk,
                'cite': 'docs/SAIRN-PROCESS-RULES.md section ' + rid,
                'action': action
            })

    return {
        'target': rel,
        'exists': bool(src),
        'app_matched': app,
        'risks': risks,
        'considered': {
            'defect_records': len(records),
            'matched_this_file': len(same_file),
            'detectors_run': len(DETECTORS) if src else 0,
            'detectors_fired': fired
        },
        'no_detector_yet': sorted(NO_DETECTOR.keys())
    }


def render(a):
    L = []
    L.append('FMEA FIRST DRAFT -- %s' % a['target'])
    if a.get('refused'):
        L.append('  REFUSED: %s' % a['refused'])
        return '\n'.join(L)
    if not a['exists']:
        L.append('  !! the file does not exist or could not be read. Nothing was')
        L.append('     analysed from its source; only its defect history was used.')
    L.append('  considered: %d defect records, %d detector(s) run'
             % (a['considered']['defect_records'], a['considered']['detectors_run']))
    if not a['risks']:
        L.append('')
        L.append('  NOTHING MATCHED. That is not a clean bill of health -- this tool is')
        L.append('  seeded from history and cannot invent a first instance. The')
        L.append('  un-precedented risks are the part a human still has to add.')
    for i, r in enumerate(a['risks'], 1):
        L.append('')
        L.append('  %d. [%s] %s' % (i, r['source'], r['basis']))
        L.append('     RISK : %s' % r['risk'])
        L.append('     CITE : %s%s' % (r['cite'],
                                       ('  (%s, prior severity %s, found by %s)'
                                        % (r.get('date', ''), r.get('prior_severity', ''),
                                           r.get('detected_by', '')))
                                       if r['source'] == 'defect-register' else ''))
        if r.get('action'):
            L.append('     DO   : %s' % r['action'])
    L.append('')
    L.append('  RULES WITH NO DETECTOR YET, named rather than skipped: %s'
             % ', '.join(a['no_detector_yet']))
    L.append('  A risk tool with an undisclosed gap is the failure one level up.')
    return '\n'.join(L)


def fire_rates():
    """How discriminating is each detector, measured against the real tree?

    A detector firing on half the repo is a horoscope: right often enough to
    feel insightful, carrying no information. This is printed rather than
    claimed so the calibration can be re-derived by anyone, and so a detector
    that drifts broad becomes visible instead of quietly filling reports.
    """
    import glob
    files = []
    for pat in ('tools/*.py', 'tests/*.py', 'tests/**/*.py'):
        files.extend(p.replace(os.sep, '/') for p in
                     glob.glob(os.path.join(REPO, pat), recursive=True))
    files = sorted(set(files))
    hits = dict((d[0], 0) for d in DETECTORS)
    for p in files:
        rel = os.path.relpath(p, REPO).replace(os.sep, '/')
        try:
            src = io.open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        for rid, _, _, det in DETECTORS:
            try:
                if det(src, rel):
                    hits[rid] += 1
            except Exception:
                pass
    return len(files), hits


def main(argv):
    if '--rates' in argv:
        n, hits = fire_rates()
        print('DETECTOR FIRE RATES over %d files in tools/ and tests/' % n)
        print('  A rate near 100% is a horoscope; a rate of 0% is a detector')
        print('  nothing has exercised. Neither is evidence on its own.')
        for rid, risk, _, _ in DETECTORS:
            pct = (100.0 * hits[rid] / n) if n else 0.0
            flag = '  <- TOO BROAD' if pct > 35 else ('  <- never fires here' if hits[rid] == 0 else '')
            print('  %-5s %4d  %5.1f%%%s' % (rid, hits[rid], pct, flag))
        return 0
    paths = [a for a in argv if not a.startswith('--')]
    if '--asof' in argv:
        i = argv.index('--asof')
        if i + 1 < len(argv) and argv[i + 1] in paths:
            paths.remove(argv[i + 1])
    if not paths:
        print('usage: python tools/fmea_draft.py <path> [--json] [--save] [--rates]')
        return 2
    try:
        records = load_register()
    except Exception as e:
        print('docs/defect-density-register.json could not be read: %s. NOT a pass.' % e)
        return 2
    # --asof <date>: seed ONLY from defects known by that date. This exists for
    # RETROACTIVE VALIDATION -- drafting a file as of last week and checking
    # whether it predicted this week's defects is the only way to measure
    # whether the method works at all, rather than whether the plumbing runs.
    # Without it, a draft is seeded from the very defects it is then scored
    # against, which is circular and would report a flattering nonsense.
    asof = None
    if '--asof' in argv:
        i = argv.index('--asof')
        asof = argv[i + 1] if i + 1 < len(argv) else None
        if not asof:
            print('--asof needs a date (YYYY-MM-DD)')
            return 2
        before = len(records)
        records = [r for r in records if str(r.get('date', '')) <= asof]
        print('AS OF %s -- seeded from %d of %d records; the later %d are hidden '
              'so this is a real prediction rather than a restatement.\n'
              % (asof, len(records), before, before - len(records)))
    titles = rule_titles()

    out = [analyse(p, records, titles) for p in paths]
    if '--json' in argv:
        print(json.dumps(out, indent=1, sort_keys=True))
    else:
        print('\n\n'.join(render(a) for a in out))

    if '--save' in argv:
        if not os.path.isdir(FMEA_DIR):
            os.makedirs(FMEA_DIR)
        for a in out:
            if a.get('refused'):
                # A refused target must not leave an empty draft behind: it
                # would inflate drafts_on_disk in the prediction check and make
                # coverage look better than it is.
                print('\nNOT saved (%s): %s' % (a['target'], a['refused']))
                continue
            slug = a['target'].replace('/', '_').replace('\\', '_')
            p = os.path.join(FMEA_DIR, slug + '.json')
            # ── drafted_on, added 2026-09-13, AND IT IS NOT COSMETIC ────────
            # tools/fmea_prediction_check.py needs to know a draft was written
            # BEFORE the defect it claims to predict. Without this field it
            # falls back to "the newest defect the draft cites", which is only
            # a LOWER bound -- and its own comment says so. The first run that
            # ever had drafts on disk immediately scored one PREDICTION that
            # was a BACKDATING ARTEFACT: a draft saved today, citing a defect
            # from today, matching that same defect. A risk tool scoring itself
            # right on a defect that had already happened is the fabrication
            # shape fmea_draft.py's own docstring is written against, arriving
            # through the TIMESTAMP instead of through the generator.
            a['drafted_on'] = _today()
            io.open(p, 'w', encoding='utf-8', newline='\n').write(
                json.dumps(a, indent=1, sort_keys=True))
            print('\nsaved %s' % os.path.relpath(p, REPO).replace(os.sep, '/'))
        print('A SAVED DRAFT IS A PREDICTION. tools/fmea_prediction_check.py '
              'scores it against what actually went wrong.')
    return 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
