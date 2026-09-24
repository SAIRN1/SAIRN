#!/usr/bin/env python
"""verification_plan_staleness_check.py -- derive what is ACTUALLY done, and
diff it against what the verification-methodology implementation plan claims.

Usage:
  python tools/verification_plan_staleness_check.py [--plan <path>] [--json]

Exit codes: 0 clean / 1 drift found / 2 COULD NOT TELL

── WHY THIS EXISTS ─────────────────────────────────────────────────────────
A plan document carries three things a repo can contradict: what is DONE, what
is CLAIMED by somebody right now, and what is UNCLAIMED and waiting. All three
have a tense, and this platform's standing rule is that a fact with a tense
needs a read. Nothing read this one.

Same shape as tools/sairn_app_map_check.py, and for the same stated reason:
"the map is a claim about the repo, not derived from it, so it drifts exactly
like any other unverified claim."

── THE THREE SOURCES, IN ORDER OF AUTHORITY ────────────────────────────────
  1. `git log`                  -- what actually landed, and when
  2. `.claude/claims/*.json`    -- what is claimed RIGHT NOW, by whom
  3. the agent self-logs        -- SAIRN-ACTIVE-WORK-*.md, what a session says
                                   it did

Authority runs 1 > 2 > 3. A commit is a fact; a claim is a live intention; a
self-log is a session's own account and is the weakest of the three, which is
why it is read LAST and never used to contradict a commit.

── THE THREE DRIFTS IT LOOKS FOR ───────────────────────────────────────────
  STALE-UNCLAIMED  the plan says unclaimed / not started, and a commit whose
                   subject matches has already landed
  STALE-INFLIGHT   the plan says in flight / claimed, and no claim by that
                   name is active, and the claim that closed it released
                   hours ago
  STALE-DONE       the plan says done, and NOTHING in the git history matches
                   -- the direction that flatters, and the one worth the
                   most suspicion

── WHAT IT DOES NOT DO, DELIBERATELY ───────────────────────────────────────
It does not rewrite the plan. Whether an item is genuinely finished is a
judgement about scope, and a tool that edited the document would destroy the
sentence explaining why. It reports drift. A human still edits the plan.

It also does not GUESS at a match. An item is matched to a commit only by an
explicit marker the plan itself carries -- see MATCHING below -- because two
heuristics were tried on this platform for exactly this shape (proximity, then
a tightened anchor) and BOTH scored the better-structured document worse. A
declaration a person can be held to beats a regex that cannot.

── MATCHING: THE PLAN SAYS WHAT EACH ITEM IS ───────────────────────────────
An item line may carry one or both of:

    <!-- verify: commit=<sha-or-subject-substring> -->
    <!-- verify: claim=<claim subject> -->

Items with neither are reported as UNVERIFIABLE -- a third state, in its own
column, never folded into clean. A plan that describes its work in prose
instead of marking it is not a plan this tool can check, and saying so is the
whole point: an unverifiable item is exactly where drift hides.

── AND IT FAILS CLOSED WHEN THE PLAN IS ABSENT ─────────────────────────────
Exit 2, naming the path it looked for. A staleness checker that reports a
clean plan it never opened is the defect it exists to prevent, one level up.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the plan might live. Ordered; the first that exists wins, and the list
# is printed on failure so the reader can point it somewhere else rather than
# guessing what the tool wanted.
CANDIDATES = [
    os.path.join('docs', 'verification-methodology-implementation-plan.md'),
    os.path.join('docs', 'VERIFICATION-METHODOLOGY-IMPLEMENTATION-PLAN.md'),
    'verification-methodology-implementation-plan.md',
]

MARKER = re.compile(r'<!--\s*verify:\s*([^>]*?)\s*-->')
# The words a plan uses for state. Kept small and explicit: a wider list would
# start matching prose about other things.
STATE_WORDS = [
    ('done', re.compile(r'\b(done|complete|completed|landed|shipped)\b', re.I)),
    ('inflight', re.compile(r'\b(in flight|in-flight|claimed|underway|in progress)\b', re.I)),
    ('unclaimed', re.compile(r'\b(unclaimed|not started|not yet started|open|todo|to do)\b', re.I)),
]


class CouldNotTell(Exception):
    pass


def run(cmd, cwd=REPO):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '')


def find_plan(explicit=None):
    if explicit:
        p = explicit if os.path.isabs(explicit) else os.path.join(REPO, explicit)
        if not os.path.isfile(p):
            raise CouldNotTell('--plan %r does not exist' % explicit)
        return p
    for rel in CANDIDATES:
        p = os.path.join(REPO, rel)
        if os.path.isfile(p):
            return p
    raise CouldNotTell(
        'no verification-methodology implementation plan found. Looked for:\n'
        + '\n'.join('    ' + c for c in CANDIDATES)
        + '\n  Pass --plan <path> if it lives somewhere else.\n'
        '  NOTHING WAS CHECKED. This is exit 2 and not exit 0 on purpose: a\n'
        '  staleness checker that reports a clean plan it never opened is the\n'
        '  defect it exists to prevent, one level up.')


# ── SOURCE 1: what actually landed ────────────────────────────────────────
def commits():
    """(sha, subject) for the whole history, newest first."""
    rc, out = run(['git', 'log', '--format=%H%x1f%s'])
    if rc != 0:
        raise CouldNotTell('git log failed -- no history to measure against')
    rows = []
    for line in out.split('\n'):
        if '\x1f' in line:
            sha, subj = line.split('\x1f', 1)
            rows.append((sha.strip(), subj.strip()))
    if not rows:
        raise CouldNotTell(
            'git log returned ZERO commits. An empty history would make every '
            'plan item look unstarted, which is the safe-sounding answer and '
            'the wrong one.')
    return rows


# ── SOURCE 2: what is claimed right now ───────────────────────────────────
def claims():
    """subject -> {'session':..., 'active':bool, 'age_h':float} from the claim
    files, which are the live record every clone shares."""
    d = os.path.join(REPO, '.claude', 'claims')
    out = {}
    if not os.path.isdir(d):
        # Not fatal: a repo with no claims directory has no claims, which is a
        # real answer. Said out loud in the report rather than silently empty.
        return out, False
    for f in sorted(os.listdir(d)):
        if not f.endswith('.json'):
            continue
        try:
            rec = json.load(io.open(os.path.join(d, f), encoding='utf-8'))
        except ValueError:
            continue
        for c in (rec if isinstance(rec, list) else [rec]):
            if not isinstance(c, dict):
                continue
            subj = str(c.get('subject') or c.get('task') or '').strip()
            if not subj:
                continue
            out[subj] = {
                'session': c.get('session') or f[:-5],
                'active': str(c.get('state', 'active')).lower() == 'active',
                'task': c.get('task', ''),
            }
    return out, True


# ── SOURCE 3: the self-logs, read LAST and never against a commit ─────────
def self_logs():
    found = {}
    for f in sorted(os.listdir(REPO)):
        m = re.match(r'^SAIRN-ACTIVE-WORK-([a-z0-9]+)\.md$', f)
        if m:
            try:
                found[m.group(1)] = io.open(os.path.join(REPO, f),
                                            encoding='utf-8', errors='replace').read()
            except OSError:
                pass
    return found


# ── THE PLAN ──────────────────────────────────────────────────────────────
def parse_plan(path):
    """Every line carrying a verify marker, with the tier heading above it and
    the state word the line uses."""
    text = io.open(path, encoding='utf-8', errors='replace').read()
    items, tier = [], None
    for n, line in enumerate(text.split('\n'), 1):
        h = re.match(r'^#{1,6}\s+(.*)$', line)
        if h:
            t = re.search(r'\bTier\s*([0-9]+)\b', h.group(1), re.I)
            tier = ('Tier ' + t.group(1)) if t else h.group(1).strip()[:40]
            continue
        m = MARKER.search(line)
        if not m:
            # An item line with no marker still counts, so the UNVERIFIABLE
            # column is a real measurement rather than a filter.
            if re.match(r'^\s*[-*|]\s*\S', line) and any(p.search(line) for _k, p in STATE_WORDS):
                items.append({'line': n, 'tier': tier, 'text': line.strip(),
                              'commit': None, 'claim': None, 'state': _state(line)})
            continue
        spec = {}
        for part in m.group(1).split(','):
            if '=' in part:
                k, v = part.split('=', 1)
                spec[k.strip()] = v.strip()
        items.append({'line': n, 'tier': tier, 'text': line.strip(),
                      'commit': spec.get('commit'), 'claim': spec.get('claim'),
                      'state': _state(line)})
    if not items:
        raise CouldNotTell(
            'the plan at %s yielded ZERO item lines. Either it uses a shape '
            'this parser does not know, or it is empty -- and an empty set '
            'would report the whole plan as clean, which is the failure this '
            'tool exists to avoid.' % os.path.relpath(path, REPO))
    return items


def _state(line):
    for key, pat in STATE_WORDS:
        if pat.search(line):
            return key
    return None


def matches_commit(item, hist):
    token = (item.get('commit') or '').strip()
    if not token:
        return None
    for sha, subj in hist:
        if sha.startswith(token) or token.lower() in subj.lower():
            return (sha[:12], subj)
    return None


def build(path):
    hist = commits()
    live, have_claims = claims()
    logs = self_logs()
    items = parse_plan(path)

    findings, unverifiable = [], []
    for it in items:
        if not it['commit'] and not it['claim']:
            unverifiable.append(it)
            continue
        hit = matches_commit(it, hist)
        claim = live.get(it['claim']) if it.get('claim') else None

        if it['state'] == 'unclaimed' and hit:
            findings.append(('STALE-UNCLAIMED', it,
                             'the plan says unclaimed, but %s "%s" has landed'
                             % (hit[0], hit[1][:70])))
        elif it['state'] == 'inflight' and it.get('claim') and not (claim and claim['active']):
            findings.append(('STALE-INFLIGHT', it,
                             'the plan says in flight, and no ACTIVE claim named %r '
                             'exists%s' % (it['claim'],
                                           '' if have_claims else
                                           ' -- AND THERE IS NO CLAIMS DIRECTORY, so '
                                           'this is could-not-tell rather than a fact')))
        elif it['state'] == 'done' and it.get('commit') and not hit:
            findings.append(('STALE-DONE', it,
                             'the plan says done, and NOTHING in the history matches '
                             '%r. This is the direction that flatters.' % it['commit']))

    # The self-logs are read but never used to contradict a commit. They are
    # reported only where they are the ONLY evidence, so a reader can see how
    # thin that is.
    log_only = []
    for it in items:
        if it['state'] == 'done' and not it.get('commit'):
            who = [s for s, body in logs.items()
                   if it['text'][:40] and it['text'][:40].lower() in body.lower()]
            if who:
                log_only.append((it, who))

    return {'items': items, 'findings': findings, 'unverifiable': unverifiable,
            'log_only': log_only, 'have_claims': have_claims,
            'commits': len(hist), 'claims': len(live)}


def main(argv):
    explicit = None
    if '--plan' in argv:
        explicit = argv[argv.index('--plan') + 1]
    try:
        path = find_plan(explicit)
        res = build(path)
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL: %s\n' % e)
        return 2

    if '--json' in argv:
        print(json.dumps({
            'plan': os.path.relpath(path, REPO),
            'items': len(res['items']),
            'findings': [{'kind': k, 'line': it['line'], 'tier': it['tier'],
                          'why': why} for k, it, why in res['findings']],
            'unverifiable': [it['line'] for it in res['unverifiable']],
        }, indent=2))
        return 1 if res['findings'] else 0

    print('VERIFICATION-PLAN STALENESS -- %s' % os.path.relpath(path, REPO))
    print('  measured against %d commit(s) and %d claim record(s)%s'
          % (res['commits'], res['claims'],
             '' if res['have_claims'] else '  [NO CLAIMS DIRECTORY]'))
    print('')
    print('  plan items with a verify marker   %3d'
          % (len(res['items']) - len(res['unverifiable'])))
    print('  UNVERIFIABLE -- no marker at all  %3d   <- a THIRD state, not clean'
          % len(res['unverifiable']))
    print('  drift found                       %3d' % len(res['findings']))
    print('')
    for kind, it, why in res['findings']:
        print('  %-16s %s:%d  [%s]' % (kind, os.path.basename(path), it['line'],
                                       it['tier'] or '-'))
        print('      %s' % it['text'][:100])
        print('      %s' % why)
    if res['unverifiable']:
        print('')
        print('  UNVERIFIABLE ITEMS -- this tool cannot check these, and that is')
        print('  where drift hides. Add `<!-- verify: commit=... -->` or')
        print('  `<!-- verify: claim=... -->` to make one checkable:')
        for it in res['unverifiable'][:20]:
            print('    %s:%-5d %s' % (os.path.basename(path), it['line'],
                                      it['text'][:80]))
        if len(res['unverifiable']) > 20:
            print('    ... and %d more' % (len(res['unverifiable']) - 20))
    if res['log_only']:
        print('')
        print('  DONE ON A SELF-LOG ALONE -- the weakest of the three sources,')
        print('  reported so the thinness is visible rather than assumed:')
        for it, who in res['log_only'][:10]:
            print('    %s:%-5d  claimed by %s' % (os.path.basename(path),
                                                  it['line'], ', '.join(who)))
    print('')
    print('NOTE: this says the plan DISAGREES with the repo, never that an item')
    print('is genuinely finished. Whether the scope is met is a judgement, and')
    print('nothing here edits the plan.')
    return 1 if res['findings'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
