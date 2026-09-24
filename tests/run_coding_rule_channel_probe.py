#!/usr/bin/env python
"""tests/run_coding_rule_channel_probe.py

Run:  python tests/run_coding_rule_channel_probe.py

Exit 0 every arm holds, 1 an arm failed, 2 COULD NOT RUN.

── WHAT THIS IS THE CONTROL ON ────────────────────────────────────────────────
tools/tier_a_review_gate.py grew a second subject kind on 2026-09-24: a named
CODING RULE, alongside the stored Tier A resource it has always keyed on. It
grew one because the gate REFUSED a real obligation and was right to --
"Nothing in this change names a Tier A resource, so there is no obligation to
record" -- on a change to the GP therapy-discipline modifier, whose absence
makes a therapy claim UNPROCESSABLE. A rule decides whether a claim is
ADJUDICATED; a row decides what is REMEMBERED, and only the second had a
channel. Six other shipped rules were in the same position.

── THE FIXTURES ARE SYNTHETIC DIFFS, AND NOTHING ON DISK IS TOUCHED ──────────
Every arm hands check() a unified diff built in memory against line numbers
DERIVED from the real registry and the real file. No tracked file is written,
no git state is changed, and the ledger is never saved -- so this probe cannot
lose another session's work on a tree four clones share, and it cannot leave a
fabricated obligation behind.

── THE ARMS THAT MATTER ARE 3 AND 5 ──────────────────────────────────────────
3 is the direction the channel was BUILT for: a changed line inside a rule's
body, naming nothing a grep could find, must be caught. 5 is the direction that
makes the first one worth anything: a changed line one line OUTSIDE the same
rule's range must not be. A detector that says yes to everything is worth less
than none, and a range check is exactly the shape that quietly widens.
"""

import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

try:
    import tier_a_review_gate as g                                # noqa: E402
except Exception as e:                                            # noqa: BLE001
    sys.stderr.write('COULD NOT RUN: tier_a_review_gate.py did not import: %s\n' % e)
    sys.exit(2)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:500]))
    if not cond:
        fails.append(name)


def diff_at(path, line, added='            var __probe = 1;'):
    """A one-added-line unified diff whose ADDED line lands exactly on `line`.

    The `+` comes FIRST in the hunk on purpose. The first version put a context
    line ahead of it, so the added line landed on `line + 1` and three arms
    failed off by one -- the probe measuring its own fixture rather than the
    containment check. Worth the comment because an off-by-one in a RANGE test
    is the one error that can look like a correct result.
    """
    return ('--- a/%s\n+++ b/%s\n@@ -%d,1 +%d,2 @@\n+%s\n context\n'
            % (path, path, line, line, added))


def diff_delete_at(path, line, removed='            var __gone = 1;'):
    """A one-deleted-line diff at new-file position `line`."""
    return ('--- a/%s\n+++ b/%s\n@@ -%d,2 +%d,1 @@\n-%s\n context\n'
            % (path, path, line, line, removed))


print('\n1. the registry loads and every anchor resolves EXACTLY once')
try:
    RULES = g.coding_rules()
except g.CouldNotTell as e:
    sys.stderr.write('COULD NOT RUN: %s\n' % e)
    sys.exit(2)
check('docs/coding-rule-registry.json yields rules (%d)' % len(RULES),
      len(RULES) >= 1, RULES)

RANGES = {}
for r in RULES:
    try:
        text = io.open(os.path.join(REPO, r['file']), encoding='utf-8').read()
        RANGES[r['rule']] = (r['file'],) + g._anchor_range(text, r['anchor'])
    except Exception as e:                                        # noqa: BLE001
        check('anchor resolves: %s' % r['rule'], False, e)
check('every registered anchor resolved to a range', len(RANGES) == len(RULES),
      sorted(set(x['rule'] for x in RULES) - set(RANGES)))

# The arms below need one rule with a body of real width to land inside and
# outside of. Picked by MEASUREMENT rather than by name, so renaming a rule
# does not silently pick a one-line constant whose "outside" arm proves nothing.
WIDE = max(RANGES.items(), key=lambda kv: kv[1][2] - kv[1][1])
WIDE_NAME, (WIDE_FILE, WIDE_LO, WIDE_HI) = WIDE
check('a rule with a multi-line body exists to test containment with (%s, %d lines)'
      % (WIDE_NAME, WIDE_HI - WIDE_LO + 1), WIDE_HI - WIDE_LO >= 4,
      'every registered rule is one line, so arms 3 and 5 could not tell a '
      'containment check from a line-equality check')

print('\n2. the degenerate anchor -- a bare constant covers its own line')
ONE = [k for k, v in RANGES.items() if v[1] == v[2]]
check('at least one rule is a single-line constant (%d of %d)'
      % (len(ONE), len(RANGES)), bool(ONE),
      'the no-brace branch of _anchor_range is unexercised by the real registry')
if ONE:
    f, lo, hi = RANGES[ONE[0]]
    hits = g.touched_rules(diff_at(f, lo), RULES)
    check('a change ON that line is attributed to it', ONE[0] in hits, sorted(hits))
    hits = g.touched_rules(diff_at(f, lo + 1), RULES)
    check('a change on the NEXT line is not', ONE[0] not in hits, sorted(hits))

print('\n3. THE ARM THIS WAS BUILT FOR -- a changed line INSIDE a rule body')
mid = (WIDE_LO + WIDE_HI) // 2
hits = g.touched_rules(diff_at(WIDE_FILE, mid), RULES)
check('a line in the middle of %s is attributed to it' % WIDE_NAME,
      WIDE_NAME in hits, sorted(hits))
# ...AND IT NAMES NOTHING. This is the whole difference from the resource half:
# the added line mentions no resource, no rule name, nothing greppable.
res = g.tier_a_resources()
check('CONTROL: the same diff names NO Tier A resource, so the resource half '
      'is silent on it -- which is the gap this channel closes',
      not g.touched_tier_a(diff_at(WIDE_FILE, mid), res),
      sorted(g.touched_tier_a(diff_at(WIDE_FILE, mid), res)))

print('\n3b. a pure DELETION inside a rule body counts as a change')
# The edit this gate most needs to see, and the one a `+`-only reader misses:
# gutting a rule's body deletes lines and adds none. The first version of
# changed_lines_by_file() skipped `-` lines entirely.
hits = g.touched_rules(diff_delete_at(WIDE_FILE, mid), RULES)
check('deleting a line inside %s is attributed to it' % WIDE_NAME,
      WIDE_NAME in hits, sorted(hits))

print('\n4. the boundaries are inclusive')
for label, ln in (('first', WIDE_LO), ('last', WIDE_HI)):
    hits = g.touched_rules(diff_at(WIDE_FILE, ln), RULES)
    check('the %s line of the range is INSIDE it' % label, WIDE_NAME in hits,
          sorted(hits))

print('\n5. THE OTHER DIRECTION -- one line outside is NOT attributed')
for label, ln in (('just before', WIDE_LO - 1), ('just after', WIDE_HI + 1)):
    hits = g.touched_rules(diff_at(WIDE_FILE, ln), RULES)
    check('a line %s the range does not hit %s' % (label, WIDE_NAME),
          WIDE_NAME not in hits, sorted(hits))
# A FILE NOBODY REGISTERED IS SILENT, not "everything".
hits = g.touched_rules(diff_at('README.md', 3), RULES)
check('a change to an unregistered file attributes to no rule', not hits, sorted(hits))

print('\n6. the GATE blocks on an uncovered rule, and says which')
# ── THE LEDGER IS STRIPPED FOR THIS ARM, AND IT HAD TO LEARN THAT ─────────
# The first version read the real ledger. It passed, and then FAILED the
# moment a real obligation was opened for this very rule an hour later --
# because the gate correctly reported it as covered. The arm was measuring
# the QUEUE, not the GATE, and it would have gone green or red with whatever
# state four clones happened to leave behind. Every rule-naming record is
# removed so this measures one thing: does an UNCOVERED rule change block.
_real_load = g.load_reviews
_data = _real_load()
_me = g.session_name()


def _no_rule_records():
    import copy
    d = copy.deepcopy(_data)
    d['records'] = [r for r in d['records'] if not (r.get('rules') or [])]
    return d


g.load_reviews = _no_rule_records
try:
    code, lines = g.check(diff_at(WIDE_FILE, mid), verbose=False)
    body = '\n'.join(lines)
    check('exit 1 on a rule change with no open obligation', code == 1, code)
    check('...and the refusal names the rule', WIDE_NAME in body, body[:300])
    check('...and says CODING RULE rather than Tier A resource',
          'A CODING RULE CHANGED' in body, body[:200])
    check('...and marks it [coding rule] in the list', '[coding rule]' in body,
          body[:400])
    # CONTROL: the stripping is what makes the arms above mean anything, so
    # prove it actually removed something on the tree this ran against.
    check('CONTROL: the real ledger DOES hold rule-naming records, so the '
          'stripping above is not a no-op',
          any(r.get('rules') for r in _data['records']),
          'no record names a rule yet -- arms above would pass identically '
          'against the unstripped ledger and prove less than they claim')
finally:
    g.load_reviews = _real_load

print('\n7. an OPEN obligation naming that rule clears it -- and only it')
# THE LEDGER IS NEVER WRITTEN. load_reviews/save_reviews are left alone; the
# record is injected into the in-memory dict the gate reads, which is what
# `check()` consults. A probe that had to append a real obligation to test the
# covered path would leave a fabricated review in a file four clones merge.
_real_load = g.load_reviews
_data = _real_load()
_me = g.session_name()


def _patched():
    import copy
    d = copy.deepcopy(_data)
    d['records'].append({
        'author_session': _me, 'opened_at': '2026-09-24T00:00:00Z',
        'resources': [], 'rules': [WIDE_NAME], 'files': [WIDE_FILE],
        'what': 'probe fixture, never written to disk', 'status': 'open',
        'reviewer_owner': None, 'owner_assigned_at': None,
        'reviewer_session': None, 'reviewed_at': None, 'verdict': None,
    })
    return d


g.load_reviews = _patched
try:
    code, lines = g.check(diff_at(WIDE_FILE, mid), verbose=True)
    check('exit 0 once an open obligation names the rule', code == 0,
          '%s\n%s' % (code, '\n'.join(lines)[:300]))
    check('...and it says so, naming the rule', 'Coding rules changed' in '\n'.join(lines),
          '\n'.join(lines)[:200])
    # ...AND COVERAGE IS PER RULE. An obligation for one rule must not clear a
    # different one riding along in the same push -- the exact defect hover #270
    # found on the resource half, which cleared a whole change on one shared name.
    other = [k for k in RANGES if k != WIDE_NAME]
    if other:
        f2, lo2, hi2 = RANGES[other[0]]
        two = diff_at(WIDE_FILE, mid) + diff_at(f2, lo2)
        code2, lines2 = g.check(two, verbose=False)
        check('CONTROL: a SECOND, unnamed rule in the same push still blocks',
              code2 == 1 and other[0] in '\n'.join(lines2),
              '%s\n%s' % (code2, '\n'.join(lines2)[:300]))
finally:
    g.load_reviews = _real_load

print('\n8. FAIL CLOSED -- an anchor that stops matching is COULD NOT TELL')
# NOT "untouched". This is the stale-anchor failure this platform has recorded
# six times, and the one shape that would let the registry decay in silence.
_real_rules = g.coding_rules
g.coding_rules = lambda: [{'rule': 'probe_broken', 'app': 'sairncode',
                           'file': WIDE_FILE,
                           'anchor': 'function __no_such_anchor_exists__('}]
try:
    code, lines = g.check(diff_at(WIDE_FILE, mid), verbose=False)
    body = '\n'.join(lines)
    check('exit 2, not 0 and not 1', code == 2, '%s\n%s' % (code, body[:300]))
    check('...and it says COULD NOT TELL', 'COULD NOT TELL' in body, body[:200])
    check('...and names the anchor that could not be found',
          '__no_such_anchor_exists__' in body, body[:400])
finally:
    g.coding_rules = _real_rules

print('\n9. an AMBIGUOUS anchor is refused too -- the other half of uniqueness')
g.coding_rules = lambda: [{'rule': 'probe_ambiguous', 'app': 'sairncode',
                           'file': WIDE_FILE, 'anchor': 'var '}]
try:
    code, lines = g.check(diff_at(WIDE_FILE, mid), verbose=False)
    body = '\n'.join(lines)
    check('an anchor matching many lines is exit 2, not a guess', code == 2,
          '%s\n%s' % (code, body[:300]))
    check('...and says it cannot tell WHICH site a change hit',
          'which site' in body, body[:400])
finally:
    g.coding_rules = _real_rules

print('\n10. an EMPTY registry is refused, never read as "no rules changed"')
g.coding_rules = _real_rules
_real_path = g.RULE_REGISTRY
g.RULE_REGISTRY = os.path.join(REPO, 'tools', '__probe_missing_registry.json')
try:
    code, lines = g.check(diff_at(WIDE_FILE, mid), verbose=False)
    body = '\n'.join(lines)
    check('a registry that cannot be read is exit 2', code == 2,
          '%s\n%s' % (code, body[:300]))
finally:
    g.RULE_REGISTRY = _real_path

print('\n11. --rules answers, and answers 0 on the real registry')
rc = g.cmd_rules()
check('cmd_rules() exits 0 with every anchor resolving', rc == 0, rc)

print('\n12. NOTHING ON DISK WAS TOUCHED')
check('the ledger still parses and is the size this probe found it',
      len(_real_load()['records']) == len(_data['records']),
      'the probe appended a record to the real file -- it must only ever patch '
      'the in-memory copy')
check('the registry path is restored', g.RULE_REGISTRY == _real_path, g.RULE_REGISTRY)
check('coding_rules is restored', g.coding_rules is _real_rules, g.coding_rules)
check('load_reviews is restored', g.load_reviews is _real_load, g.load_reviews)

print('')
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('ALL ARMS PASS')
sys.exit(0)
