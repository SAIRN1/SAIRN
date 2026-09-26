#!/usr/bin/env python
"""Re-seat the sha citations in docs/tier-a-reviews.json after a rebase.

    python tools/review_ledger_reseat.py                # --check, read-only
    python tools/review_ledger_reseat.py --adopt        # declare LIVE citations
    python tools/review_ledger_reseat.py --reseat       # write the repairs

── WHY THIS EXISTS, AND WHY IT IS NOT A COPY OF defect_register.py --reseat ──
The defect register has carried `--reseat` since 2026-09-11 and the review
ledger has not, so the same rebase that a register repairs automatically leaves
a review record pointing at nothing. Hank's 2026-09-26 review of cody's
2026-09-25T15:08:08Z obligation says it in the record itself: *"The commit is
47220a5d, found by message. Your clone rebased and the record was never
reseated -- the same reseat the defect register does automatically and the
review ledger does not."* Twelve dead citations had accumulated by then, and
every one of them arrived as a COULD-NOT-TELL on somebody's review.

THE REGISTER'S DESIGN DOES NOT TRANSPLANT, and that is the whole reason this is
a separate tool rather than a second caller of the same function. Per
docs/2026-09-13-cross-domain-disciplines.md item 7 -- byte-identical is not
safe-in-context -- the two differ in three ways that each change the answer:

  1. ONE FIELD vs PROSE. A register record has `commit`, a single 12-char sha
     field, so a re-seat is an assignment. A review record embeds its shas in
     `what` and `verdict` -- paragraphs a reviewer wrote -- and the checker that
     reports the drift (tools/register_freshness_check.py) reads that prose. A
     field-only repair would leave the dead sha on the page for every human
     reader and would not clear the finding.

  2. THE DURABLE HALF IS MISSING. The register re-seats by SUBJECT, because a
     rebase rewrites the hash and preserves the message. A review record carries
     no subject for the commit it cites -- so there is nothing to look the new
     sha up by, and this tool's first job is to create that field (`cites`)
     rather than to use one.

  3. A SHA LITERAL'S ROLE DEPENDS ON THE SENTENCE IT IS IN, which has no
     analogue in the register at all and is the finding that shaped this file.
     THREE ROLES, ALL THREE PRESENT IN THE REAL DATA TODAY:

       * A CITATION -- "Fixed in a49edd00" -- must be re-seated.
       * A QUOTATION OF A DEAD POINTER -- "This record cites a49edd00 and no
         such commit exists in the repo. The change is 5c781b99" -- must NOT be
         re-seated. That sentence is a reviewer's finding ABOUT the dead sha;
         rewriting the literal makes the sentence assert the opposite of what
         its author verified.
       * NOT A SHA AT ALL -- `1234abcd`, quoted inside a finding narrative as an
         illustrative example, and reported as citation drift ever since.

     THE SAME LITERAL IS BOTH ROLES IN ONE RECORD. `a49edd00` is a citation in
     that record's `what` and a quotation in its `verdict`; `ec9ef9af` is the
     same. So the role is recorded PER FIELD, and a blind find-and-replace
     across a record -- which is what "re-seat the prose" sounds like -- would
     have corrupted two reviews while fixing them.

── THE DEDICATED FIELDS ─────────────────────────────────────────────────────
    "cites": [{"sha": "...", "subject": "<the commit's message subject>",
               "in": ["what", "verdict"], "reseated_from": ["..."]}]
    "frozen_shas": [{"literal": "...", "in": ["verdict"], "why": "..."}]

`cites` is what makes a re-seat possible: the subject is the half a rebase
preserves. `frozen_shas` is what makes it SAFE, and it is deliberately not
something this tool can infer -- deciding that a sentence is ABOUT a pointer
rather than citing one is a reading of somebody's prose, so it is authored into
the record by a person and this tool only obeys it.

── THE THIRD STATE IS THE POINT OF --check ──────────────────────────────────
A prose sha declared in neither field is UNDECLARED. That is not a pass and not
a re-seat failure: it is "this citation has no recorded subject, so the next
rebase will strand it and nothing here can repair it". `--adopt` closes it while
the sha is still alive, which is the only time the subject can be read.

Exit 0 every citation is live and declared, 1 something needs a re-seat or is
undeclared, 2 could not run. Three states, never two.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(REPO, 'docs', 'tier-a-reviews.json')
PROSE_FIELDS = ('what', 'verdict', 'note', 'owner_note')
SHA = re.compile(r'\b[0-9a-f]{7,40}\b')

EXIT_OK, EXIT_WORK, EXIT_COULD_NOT_RUN = 0, 1, 2


class CouldNotRun(Exception):
    pass


# ── THE PURE HALF ───────────────────────────────────────────────────────────
# Every decision below is a function of the ledger and a resolver callback. No
# git, no filesystem, no clock -- so the whole verdict table is drivable from
# fixtures, which is how the criteria get locked before they touch real records
# (docs/2026-09-13-cross-domain-disciplines.md item 1).

def record_id(rec):
    return '%s@%s' % (rec.get('author_session'), rec.get('opened_at'))


def prose_shas(rec):
    """-> {literal: [field, ...]}. Every hex run in the prose, with the fields
    it appears in. All-digit runs are skipped: a 7-digit number is a count, not
    a sha, and treating one as a citation is how `4111111111111111` ends up in a
    drift report."""
    out = {}
    for field in PROSE_FIELDS:
        for m in SHA.finditer(rec.get(field) or ''):
            lit = m.group(0)
            if lit.isdigit():
                continue
            fields = out.setdefault(lit, [])
            if field not in fields:
                fields.append(field)
    return out


def _declared(entries, key):
    """-> {literal: [field, ...]} from a cites/frozen_shas list."""
    out = {}
    for e in entries or []:
        lit = e.get(key)
        if not lit:
            continue
        out.setdefault(lit, [])
        for f in (e.get('in') or []):
            if f not in out[lit]:
                out[lit].append(f)
    return out


def plan_record(rec, resolve):
    """-> list of (action, literal, field_or_None, detail).

    action in:
      'live'        the cited sha resolves and is reachable. Nothing to do.
      'reseat'      dead, and its recorded subject resolves to exactly one
                    reachable commit. Carries the new sha.
      'stuck'       dead, and it cannot be repaired -- no subject recorded, the
                    subject matches nothing, or it matches more than one. NEVER
                    a guess: the detail says which of the three.
      'frozen'      declared as a literal the prose is ABOUT. Skipped on purpose.
      'undeclared'  in the prose and in neither field. The third state.
      'conflict'    declared as BOTH a citation and frozen in the SAME field.
                    Refused rather than resolved in either direction.
      'orphan'      declared in `cites` but absent from every field it names.

    `resolve(spec)` is the only outside contact and it is injected. It takes
    {'sha': ...} or {'subject': ...} and answers
    {'state': 'reachable'|'dead'|'none'|'ambiguous', 'sha': <40-char or None>}.
    """
    acts = []
    found = prose_shas(rec)
    cited = _declared(rec.get('cites'), 'sha')
    frozen = _declared(rec.get('frozen_shas'), 'literal')

    for lit in sorted(set(list(cited) + list(frozen))):
        both = sorted(set(cited.get(lit, [])) & set(frozen.get(lit, [])))
        for f in both:
            acts.append(('conflict', lit, f,
                         'declared as a citation AND as frozen in the same '
                         'field -- one of the two declarations is wrong and '
                         'this tool will not pick'))

    for entry in rec.get('cites') or []:
        lit = entry.get('sha')
        if not lit:
            continue
        fields = [f for f in (entry.get('in') or []) if f not in frozen.get(lit, [])]
        missing = [f for f in fields if lit not in (rec.get(f) or '')]
        if missing:
            acts.append(('orphan', lit, ','.join(missing),
                         'declared as cited in %s, and the literal is not there '
                         '-- the prose was edited without the field moving'
                         % ', '.join(missing)))
            continue
        if not fields:
            continue
        r = resolve({'sha': lit})
        if r['state'] == 'reachable':
            acts.append(('live', lit, ','.join(fields), r['sha'][:12]))
            continue
        subject = entry.get('subject')
        if not subject:
            acts.append(('stuck', lit, ','.join(fields),
                         'does not resolve and NO subject was recorded, so '
                         'there is nothing durable to look it up by. Run '
                         '--adopt on a clone where it is still alive, or add '
                         'the subject by hand from the commit you verified'))
            continue
        s = resolve({'subject': subject})
        if s['state'] == 'reachable':
            acts.append(('reseat', lit, ','.join(fields), s['sha']))
        elif s['state'] == 'ambiguous':
            acts.append(('stuck', lit, ','.join(fields),
                         'the recorded subject matches MORE THAN ONE commit, so '
                         'which one this cited cannot be told apart -- exactly '
                         'the case the register\'s reseat refuses too'))
        else:
            acts.append(('stuck', lit, ','.join(fields),
                         'the recorded subject matches NO commit: %r'
                         % (subject[:70],)))

    for lit in sorted(frozen):
        for f in frozen[lit]:
            if f in cited.get(lit, []):
                continue
            acts.append(('frozen', lit, f, 'declared as a literal this prose is '
                                           'ABOUT, not a pointer to follow'))

    for lit, fields in sorted(found.items()):
        for f in fields:
            if f in cited.get(lit, []) or f in frozen.get(lit, []):
                continue
            r = resolve({'sha': lit})
            acts.append(('undeclared', lit, f,
                         'in the prose and declared nowhere. It resolves today'
                         if r['state'] == 'reachable' else
                         'in the prose, declared nowhere, and ALREADY DEAD -- '
                         'nothing recorded what it was'))
    return acts


def apply_reseat(rec, literal, fields, new_sha):
    """Rewrite one citation in the named fields and in the `cites` entry.

    THE CITED LENGTH IS PRESERVED. A record that cited 8 characters gets 8, one
    that cited 40 gets 40 -- the prose reads as its author wrote it, and a
    12-character sha appearing where the sentence had 8 is a diff nobody asked
    for. The caller is responsible for having checked that the abbreviation is
    unambiguous; this function is the edit, not the decision.
    """
    n = len(literal)
    short = new_sha[:n]
    for f in fields:
        if rec.get(f):
            rec[f] = rec[f].replace(literal, short)
    for entry in rec.get('cites') or []:
        if entry.get('sha') == literal:
            entry['sha'] = short
            hist = entry.setdefault('reseated_from', [])
            if literal not in hist:
                hist.append(literal)
    return short


# ── THE SHELL ───────────────────────────────────────────────────────────────

def git(*args):
    r = subprocess.run(('git',) + args, cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return None if r.returncode else r.stdout


def base_ref():
    """origin/main when it exists, HEAD otherwise -- and a REFUSAL when neither
    does. Copied in shape from defect_register.reseat_base() for the reason
    stated there: with no ref to measure reachability against, every citation
    looks dead and this would re-seat the whole ledger on the strength of not
    being able to look."""
    for ref in ('origin/main', 'HEAD'):
        if git('rev-parse', '--verify', ref) is not None:
            return ref
    raise CouldNotRun('neither origin/main nor HEAD could be read, so '
                      'reachability cannot be measured and NOTHING was changed')


def make_resolver(base):
    subjects = {}
    out = git('log', '--format=%H%x1f%s', base) or ''
    for line in out.split('\n'):
        if '\x1f' in line:
            h, s = line.split('\x1f', 1)
            subjects.setdefault(s.strip(), []).append(h)
    memo = {}

    def resolve(spec):
        if 'sha' in spec:
            lit = spec['sha']
            if lit in memo:
                return memo[lit]
            # RESOLVABLE IS NOT REACHABLE, and this tool needs the second
            # question -- the same distinction defect_register.reachable()
            # records: a rebased commit survives as a dangling object and keeps
            # resolving for as long as the reflog holds it, so `cat-file` alone
            # would call a stranded citation live.
            ok = (git('cat-file', '-t', lit) or '').strip() == 'commit'
            state = 'dead'
            full = None
            if ok:
                full = (git('rev-parse', lit + '^{commit}') or '').strip()
                if git('merge-base', '--is-ancestor', lit, base) is not None:
                    state = 'reachable'
            memo[lit] = {'state': state, 'sha': full}
            return memo[lit]
        hits = subjects.get((spec.get('subject') or '').strip()) or []
        if len(hits) == 1:
            return {'state': 'reachable', 'sha': hits[0]}
        if len(hits) > 1:
            return {'state': 'ambiguous', 'sha': None}
        return {'state': 'none', 'sha': None}

    return resolve


def unambiguous(short):
    """Does this abbreviation still name exactly one object? A re-seat that
    shortens a 40-character citation to 8 has to be checked, not assumed."""
    return git('rev-parse', '--verify', '--quiet', short + '^{commit}') is not None


def load():
    try:
        return json.load(io.open(LEDGER, encoding='utf-8'))
    except Exception as e:
        raise CouldNotRun('%s is unreadable (%s). Nothing was changed.'
                          % (os.path.relpath(LEDGER, REPO), e))


def save(data):
    with io.open(LEDGER, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


def cmd_check(data, resolve, base):
    print('reachability measured against %s' % base)
    tally = {}
    lines = []
    for rec in data.get('records') or []:
        for action, lit, field, detail in plan_record(rec, resolve):
            tally[action] = tally.get(action, 0) + 1
            if action == 'live':
                continue
            lines.append('  %-11s %-14s %-22s %s'
                         % (action.upper(), lit, record_id(rec)[:22], detail))
    for a in ('live', 'frozen', 'reseat', 'undeclared', 'stuck', 'conflict',
              'orphan'):
        print('  %-11s %d' % (a, tally.get(a, 0)))
    if lines:
        print('')
        for l in lines:
            print(l)
    # The dead pointers this tool deliberately does NOT touch, named rather than
    # silently out of scope.
    dead_stamps = []
    for rec in data.get('records') or []:
        for field in ('opened_at_sha', 'commit'):
            v = rec.get(field)
            if not v or not re.fullmatch(r'[0-9a-f]{7,40}', str(v)):
                continue
            if resolve({'sha': v})['state'] != 'reachable':
                dead_stamps.append((record_id(rec), field, v))
    if dead_stamps:
        print('\nOUT OF SCOPE AND SAID SO -- %d dead stamp(s) in '
              'opened_at_sha/commit:' % len(dead_stamps))
        for rid, field, v in dead_stamps:
            print('    %-22s %-14s %s' % (rid[:22], field, v[:12]))
        print('  NOT re-seatable by subject, and not a citation. `opened_at_sha`'
              ' is the AUTHOR\'S HEAD when the obligation was opened -- the')
        print('  baseline a reviewer\'s diff is relative to -- not the commit')
        print('  the change landed in, so pointing it at a commit found by')
        print('  message would put a DIFFERENT FACT in the field. The repair')
        print('  for these is the timestamp reconstruction that')
        print('  tools/tier_a_review_gate.py already implements (backfill_shas,'
              ' which stamps opened_at_sha_backfilled: true).')
    bad = sum(tally.get(a, 0) for a in ('reseat', 'undeclared', 'stuck',
                                        'conflict', 'orphan'))
    if bad:
        print('\n%d citation(s) need attention. --reseat writes the repairable '
              'ones; UNDECLARED needs --adopt while the sha is still alive; '
              'STUCK and CONFLICT need a person.' % bad)
        return EXIT_WORK
    print('\nEvery citation is live and declared.')
    return EXIT_OK


def cmd_adopt(data, resolve, base):
    """Record the subject of every LIVE prose sha that has no declaration.

    ONLY THE LIVE ONES, and that is the whole value: the subject can be read
    exactly while the commit is still reachable, and a citation adopted today is
    one a rebase tomorrow cannot strand. A dead undeclared sha is left alone --
    there is nothing to read, and inventing a subject would make it look
    repairable.
    """
    added = 0
    for rec in data.get('records') or []:
        frozen = _declared(rec.get('frozen_shas'), 'literal')
        cited = _declared(rec.get('cites'), 'sha')
        for lit, fields in sorted(prose_shas(rec).items()):
            want = [f for f in fields
                    if f not in cited.get(lit, []) and f not in frozen.get(lit, [])]
            if not want:
                continue
            r = resolve({'sha': lit})
            if r['state'] != 'reachable':
                continue
            subj = (git('log', '-1', '--format=%s', r['sha']) or '').strip()
            if not subj:
                continue
            entries = rec.setdefault('cites', [])
            existing = next((e for e in entries if e.get('sha') == lit), None)
            if existing is None:
                entries.append({'sha': lit, 'subject': subj, 'in': want})
            else:
                existing.setdefault('subject', subj)
                for f in want:
                    if f not in existing.setdefault('in', []):
                        existing['in'].append(f)
            added += 1
            print('  adopted %-14s %-22s %s' % (lit, record_id(rec)[:22], subj[:60]))
    if not added:
        print('Nothing to adopt: every live prose sha is already declared.')
        return EXIT_OK
    save(data)
    print('\n%d citation(s) now carry the subject a rebase preserves.' % added)
    print('%s is MODIFIED AND NOT STAGED -- a tool does not commit on your '
          'behalf.' % os.path.relpath(LEDGER, REPO))
    return EXIT_OK


def cmd_reseat(data, resolve, base):
    print('reachability measured against %s' % base)
    moved, refused = [], []
    for rec in data.get('records') or []:
        for action, lit, field, detail in plan_record(rec, resolve):
            if action in ('stuck', 'conflict', 'orphan'):
                refused.append((record_id(rec), action, lit, detail))
                continue
            if action != 'reseat':
                continue
            short = detail[:len(lit)]
            if not unambiguous(short):
                refused.append((record_id(rec), 'ambiguous-abbrev', lit,
                                'the %d-character abbreviation of %s no longer '
                                'names one object -- re-seating to it would '
                                'create a pointer that does not resolve'
                                % (len(lit), detail[:12])))
                continue
            apply_reseat(rec, lit, field.split(','), detail)
            moved.append((record_id(rec), lit, short, field))
    if moved:
        save(data)
        print('\nre-seated %d citation(s):' % len(moved))
        for rid, old, new, field in moved:
            print('  %-22s %s -> %s  in %s' % (rid[:22], old, new, field))
        print('%s is MODIFIED AND NOT STAGED.' % os.path.relpath(LEDGER, REPO))
    else:
        print('\nNothing was re-seatable.')
    if refused:
        print('\nREFUSED, and each says why -- a citation this cannot repair is '
              'NOT re-seated to a guess:')
        for rid, action, lit, detail in refused:
            print('  %-22s %-17s %-14s %s' % (rid[:22], action, lit, detail))
    return EXIT_WORK if refused else (EXIT_OK if moved else EXIT_WORK)


def main(argv):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--check', action='store_true',
                   help='read-only report (the default)')
    g.add_argument('--adopt', action='store_true',
                   help='record the subject of every LIVE undeclared prose sha')
    g.add_argument('--reseat', action='store_true',
                   help='write the repairs a subject match can prove')
    args = ap.parse_args(argv)
    try:
        base = base_ref()
        data = load()
    except CouldNotRun as e:
        sys.stderr.write('COULD NOT RUN: %s\n' % e)
        return EXIT_COULD_NOT_RUN
    resolve = make_resolver(base)
    if args.adopt:
        return cmd_adopt(data, resolve, base)
    if args.reseat:
        return cmd_reseat(data, resolve, base)
    return cmd_check(data, resolve, base)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
