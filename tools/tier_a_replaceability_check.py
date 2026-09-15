"""Is a Tier A resource the irreplaceable artifact, or can it be destroyed?

    python tools/tier_a_replaceability_check.py
    python tools/tier_a_replaceability_check.py --json
    python tools/tier_a_replaceability_check.py --under   # the OTHER direction

ITEM 97 -- THE HALF THE TIER RUBRIC DOES NOT ASK. `docs/CRITICALITY-TIERS.md`
assigns a tier from "the worst consequence of that resource being WRONG". That
is one of the two questions aerospace asks of a serial number. The other is
whether the thing in front of you is the article that flies or a stand-in built
to look like it -- a boilerplate capsule, a mass simulator, a pathfinder. Both
look identical on a bench. Only one of them is unrecoverable if it is lost, and
applying flight rigour to the wrong one is not the expensive mistake; it is the
cheap one. The expensive mistake is the reverse.

SO THIS TOOL ASKS THE SECOND QUESTION AND ONLY THE SECOND. For every Tier A
resource it crosses the register against the LIVE verb grants in
`api/_resources/`, and reports which Tier A artifacts a caller can DESTROY
rather than hide.

WHAT IT MEASURES, and each is a fact from a file rather than a judgement:

  HARD DELETE  the resource grants the `delete` verb -- the row is gone
  SOFT ONLY    it grants `soft_delete` -- marked and hidden, the row survives
  NO DELETE    no delete verb of either kind is reachable at all

AND ONE LANGUAGE MEASUREMENT, REPORTED SEPARATELY BECAUSE IT IS WEAKER. The
register's own rule is that every Tier A row cites something real. This counts
how many of those evidence cells say anything about RECOVERABILITY -- backup,
soft-delete, append-only, only-copy. It reads language, not intent, so a row
that establishes replaceability in words this does not match is a false hit.
It is printed as a documentation coverage figure and never as a defect count.

WHAT IT CANNOT SEE, said plainly:

  * WHETHER A TIER IS RIGHT. criticality_tier_check.py already says nothing
    mechanical can, and that is still true. This adds one axis, not a verdict.
  * ...THE UNDER-ASSIGNMENT DIRECTION WAS THIS TOOL'S NAMED HOLE UNTIL
    2026-09-15, and `--under` now sweeps it. See below. It is still a
    TRIAGE and not a verdict.
  * WHETHER A BACKUP EXISTS. It reads no infrastructure. As of 2026-09-14
    `docs/2026-09-14-nightly-backup-design.md` records that the nightly backup
    has NEVER RUN and Supabase is on a free tier with no automated backups, so
    a hard delete today is unrecoverable -- but that is a dated statement from
    a document, not something this tool checked. Re-read it before quoting it.

REPORT ONLY. Nothing is blocked and nothing should be: a hard delete verb is
not a defect, it is a decision, and this platform has made it deliberately in
both directions (`sv_controlled` has no delete verb ON PURPOSE; SAIRNdental
chose `soft_delete` and its registry says "not 'delete'"). What the tool
surfaces is a Tier A resource whose delete grant was never a per-resource
decision at all.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import criticality_tier_check as ctc                             # noqa: E402

REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')

# Deliberately generous: a false HIT here understates the gap, which is the
# safe direction for a figure reported as "documentation coverage".
RECOVERABILITY = re.compile(
    r'soft.?delete|backup|backed up|recover|restore|only record|only copy|'
    r'irreplace|append-only|additive-only|immutab|cannot be deleted|no delete',
    re.I)


def tier_rows(text):
    """(resource, tier, evidence) for every row that states a tier."""
    out = []
    for line in text.split('\n'):
        if not line.startswith('|'):
            continue
        cells = ctc.cells(line)
        if len(cells) < 4:
            continue
        tier = cells[1].replace('*', '').strip()
        if tier in ('A', 'B', 'C'):
            out.append((cells[0].strip('` '), tier, cells[3]))
    return out


def extra_actions():
    """The LIVE verb grants, read by running the registry rather than by
    re-parsing it. index.js composes eighteen modules and one of them builds
    its grants with a reduce() -- a regex over the source would miss exactly
    the case this tool exists to report."""
    src = ('const i=require("./api/_resources/index.js");'
           'process.stdout.write(JSON.stringify({e:i.EXTRA_ACTIONS,'
           'o:i.OWNER_BY_RESOURCE,n:i.RESOURCE_NAMES}));')
    try:
        r = subprocess.run(['node', '-e', src], cwd=REPO,
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        sys.stderr.write('COULD NOT RUN -- node is required to read the live '
                         'registry: %s: %s\n' % (type(e).__name__, e))
        sys.exit(2)
    if r.returncode != 0:
        sys.stderr.write('COULD NOT RUN -- the resource registry did not load. '
                         'That is a finding about api/_resources/, not a pass '
                         'for this check:\n' + (r.stderr or '')[:800] + '\n')
        sys.exit(2)
    return json.loads(r.stdout)


# ── THE OTHER DIRECTION, ADDED 2026-09-15 ──────────────────────────────────────
# Over-tiering costs rigour. UNDER-tiering is the accident, and this is the half
# that looks for it.
#
# THE REGISTER SAYS SO ITSELF, which is why this is a triage and not an
# accusation: "The B tier is 299 rows and it is the honest weak point of this
# file. Each says the same thing -- auth-gated, not money, not regulated --
# because that is what the rule says, not because 299 files were read. A
# resource misfiled as B is the failure mode that matters."
#
# 274 rows carry the words "Classified by the stated B rule rather than
# individually read". Re-reading 274 files is not the answer; NARROWING them to
# the ones an irreplaceability test flags is.
#
# THREE SIGNALS, and the third is the one the B rule structurally cannot see:
#   HARD-DELETE    a destroying `delete` verb -- it can be removed, not hidden
#   LOG-SHAPED     audit / log / history / trail / events / incidents in the
#                  name. An append-only record's whole value is that it cannot
#                  be reconstructed
#   ATTESTATION    its writer records a SIGNER, a SIGNATURE, a SIGN-OFF or a
#                  content HASH. THE B RULE ASKS "is it money or regulated" AND
#                  NEVER ASKS "is it evidence", so an attestation filed as
#                  operational data is invisible to the rule that filed it
SHAPE = re.compile(r'(?:^|_)(audit|logs?|history|trail|signatures?|consent|events|incidents)(?:$|_)')
# ── THIS PATTERN SHIPPED WITH A LITERAL BACKSPACE AND COULD NEVER MATCH ──────
# Written as \b for a word boundary, it reached the file as the BYTE 0x08.
# `ATTEST.search('signer:signer')` was False and the whole ATTESTATION signal
# reported ZERO hits platform-wide -- a clean result from a dead pattern.
#
# CLAUDE.md ALREADY NAMES THIS EXACT DEFECT as one of the three that made the
# cross-domain disciplines necessary: "a regex that shipped with a literal
# backspace and could never match". It was found here by the positive control
# in the probe -- assert the signal FIRES on a known case -- and not by reading
# the line, which looks correct at every size of font.
#
# Boundaries are written as explicit character classes now, so the pattern
# cannot be silently re-broken by an escape that does not survive being typed.
BOUND = '(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])'
ATTEST = re.compile(BOUND % '(?:signedOffBy|signedOffAt|signer|signature|'
                    'signed_at|signedAt|witness|countersign|attest)', re.I)
# A DEAD PATTERN MUST NOT SHIP AGAIN. This is the cheapest possible control and
# it is at import time: if the signal cannot match the case it was written for,
# the tool refuses to load rather than reporting a confident zero.
assert ATTEST.search('list.push({ signer:signer, typed:typed'), (
    'the ATTESTATION pattern does not match its own reference case -- it is '
    'dead and would report zero hits platform-wide')


def attestation_writers(name):
    """Files whose code mentions this resource AND an attestation field. Read
    from the app sources, because the register cannot see what a writer stores
    -- and what it stores is the whole question."""
    hits = []
    for rel in sorted(os.listdir(REPO)):
        if not rel.endswith('.html'):
            continue
        try:
            body = io.open(os.path.join(REPO, rel), encoding='utf-8',
                           errors='replace').read()
        except OSError:
            continue
        if name not in body:
            continue
        # ── ALIASES, AND WITHOUT THEM THIS SIGNAL FOUND NOTHING ──────────────
        # The first version searched only for the literal resource name and
        # returned ZERO attestation hits across the platform. It was wrong:
        # sairnfreedom.html binds `var K_SIGNATURES='sf_signatures'` and every
        # writer uses the CONSTANT, so sfSignDocument() -- which stores a
        # signer, a typed signature and a document hash -- sits 150 lines away
        # from the only place the string appears. A signal that cannot see
        # through one level of indirection reports clean on the exact resource
        # it was written to find, which is the same shape as everything else
        # found today.
        terms = [name]
        for am in re.finditer(r'([A-Z][A-Z0-9_]{2,})\s*=\s*[\'"]' + re.escape(name)
                              + r'[\'"]', body):
            terms.append(am.group(1))
        # Look near the mentions rather than anywhere in a 2MB file: an app that
        # happens to contain the word "signer" somewhere is not evidence about
        # THIS resource.
        found = False
        for term in terms:
            for m in re.finditer(r'(?<![A-Za-z0-9_])' + re.escape(term)
                                 + r'(?![A-Za-z0-9_])', body):
                # NARROW ON PURPOSE. At +/-1200 this fired on 55 resources,
                # most of them adjacency in a 2MB file rather than the
                # resource's own writer -- dnt_operatories is not an
                # attestation. At +/-300 it keeps the real ones and drops
                # the neighbours. It is still the WEAKEST of the three
                # signals and the report says so.
                window = body[max(0, m.start() - 300):m.start() + 300]
                if ATTEST.search(window):
                    hits.append(rel)
                    found = True
                    break
            if found:
                break
    return hits


def under_assigned(rows, verbs, owner):
    out = []
    for name, tier, ev in rows:
        if tier not in ('B', 'C'):
            continue
        v = verbs.get(name) or []
        signals = []
        if 'delete' in v:
            signals.append('HARD-DELETE')
        if SHAPE.search(name):
            signals.append('LOG-SHAPED')
        att = attestation_writers(name)
        if att:
            signals.append('ATTESTATION(%s)' % ','.join(att))
        by_rule = 'rather than individually read' in ev
        if signals:
            out.append({'resource': name, 'app': owner.get(name), 'tier': tier,
                        'signals': signals, 'classified_by_rule': by_rule})
    return out


def main():
    reg = extra_actions()
    verbs, owner, names = reg['e'], reg['o'], reg['n']
    rows = tier_rows(io.open(REGISTER, encoding='utf-8').read())
    tier_a = [r for r in rows if r[1] == 'A']

    if '--under' in sys.argv:
        found = under_assigned(rows, verbs, owner)
        by_rule = [r for r in found if r['classified_by_rule']]
        print('UNDER-ASSIGNMENT TRIAGE -- the direction that is the accident')
        print('  Tier B/C rows                     : %d'
              % len([r for r in rows if r[1] in ('B', 'C')]))
        print('  ...flagged by at least one signal : %d' % len(found))
        print('  ...AND classified BY RULE, never individually read: %d' % len(by_rule))
        print('')
        for r in sorted(found, key=lambda x: (not x['classified_by_rule'],
                                              x['app'] or '', x['resource'])):
            print('  %-24s %-14s %s  %s%s'
                  % (r['resource'], r['app'], r['tier'], ' '.join(r['signals']),
                     '' if r['classified_by_rule'] else '   (individually read)'))
        print('')
        print('  THIS IS A TRIAGE, NOT A RE-TIERING. The register says of itself')
        print('  that its B tier is "the honest weak point of this file" and that')
        print('  the rows say the same thing "because that is what the rule says,')
        print('  not because 299 files were read". This narrows those rows to the')
        print('  ones an irreplaceability test flags, so a person reads a handful')
        print('  instead of 274. Re-tiering is a judgement and stays one.')
        print('')
        print('  ATTESTATION is the signal the B rule structurally cannot see: it')
        print('  asks whether a resource is money or regulated and never asks')
        print('  whether it is EVIDENCE.')
        return 0

    # A register row naming a resource the registry does not have would make
    # every count below meaningless. criticality_tier_check owns that check;
    # this refuses rather than quietly measuring a subset.
    unknown = [r[0] for r in tier_a if r[0] not in names]
    if unknown:
        sys.stderr.write('COULD NOT MEASURE -- %d Tier A row(s) name a resource '
                         'the live registry does not have: %s\nRun '
                         'criticality_tier_check.py; this tool will not report a '
                         'number over a subset it cannot explain.\n'
                         % (len(unknown), ', '.join(sorted(unknown))))
        sys.exit(2)

    def grants(name):
        return verbs.get(name) or []

    hard = [r for r in tier_a if 'delete' in grants(r[0])]
    soft = [r for r in tier_a if 'soft_delete' in grants(r[0])
            and 'delete' not in grants(r[0])]
    none = [r for r in tier_a if not any(v.endswith('delete') for v in grants(r[0]))]
    silent = [r for r in tier_a if not RECOVERABILITY.search(r[2])]

    if '--json' in sys.argv:
        print(json.dumps({
            'tier_a': len(tier_a),
            'hard_delete': sorted((r[0], owner.get(r[0])) for r in hard),
            'soft_delete_only': sorted(r[0] for r in soft),
            'no_delete_verb': sorted(r[0] for r in none),
            'evidence_silent_on_recoverability': sorted(r[0] for r in silent),
        }, indent=2))
        return 0

    say = print
    say('TIER A REPLACEABILITY -- item 97, report only, nothing is blocked')
    say('  Tier A resources              : %d' % len(tier_a))
    say('  can be HARD DELETED           : %d' % len(hard))
    say('  soft_delete only (row survives): %d' % len(soft))
    say('  no delete verb reachable      : %d' % len(none))
    say('')
    if hard:
        by_app = {}
        for r in hard:
            by_app.setdefault(owner.get(r[0]) or '?', []).append(r[0])
        say('  A TIER A ARTIFACT THAT CAN BE DESTROYED RATHER THAN HIDDEN:')
        for app in sorted(by_app):
            say('    %-14s %s' % (app, ', '.join(sorted(by_app[app]))))
        say('')
        if len(by_app) == 1:
            say('  ALL OF THEM ARE IN ONE APP, which is the finding rather than')
            say('  the total: every other Tier A resource on this platform either')
            say('  hides the row or cannot delete it at all. Check whether that')
            say('  grant was a per-RESOURCE decision or a set-level one.')
            say('')
    say('  DOCUMENTATION COVERAGE, weaker and separate -- this reads LANGUAGE:')
    say('    Tier A rows whose evidence mentions recoverability : %d'
        % (len(tier_a) - len(silent)))
    say('    Tier A rows silent on it                           : %d' % len(silent))
    say('  The register asks for the worst consequence of being WRONG and gets')
    say('  it. Replaceability is a different question and mostly unrecorded.')
    say('  A row that establishes it in words this pattern does not match is a')
    say('  FALSE HIT, so treat this as coverage and never as a defect count.')
    say('')
    say('  NOT SWEPT HERE, and it is the dangerous direction: a Tier B or C')
    say('  resource that is in fact the only copy of something irreplaceable.')
    say('  Over-tiering costs rigour; under-tiering is the accident.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
