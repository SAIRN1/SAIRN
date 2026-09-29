#!/usr/bin/env python
"""hover_watchlist.py -- a durable list of "not a mismatch TODAY, but check
again on the next real read" items. Built 2026-09-28 for the first real
case: leg_memorials.service_details_visible looks like a disclosure-control
field but currently has no consumer; the cell is correct AS OF THIS READ,
and the only way to catch the day that stops being true is to force the
same question again the next time this role actually reads the resource --
not to remember to, which is exactly the kind of thing a session forgets
across a handoff.

WHY A SEPARATE FILE RATHER THAN A LOG-TEXT REMINDER: the self-log is
append-only prose: a note buried in entry #640 is not surfaced again unless
someone re-reads that exact entry. This file is CONSULTED, not just
written -- hover_cold_scan_pool.py's draw()/undirected_sweep() check every
drawn resource against it and print a WATCH line inline, so the reminder
fires at the moment it is useful (a draw just picked the resource) rather
than depending on memory of a past entry.

Run:
  python hover_watchlist.py --add <resource> --field <name> --note "<why>"
  python hover_watchlist.py --list
  python hover_watchlist.py --check <resource>   -- exit 0 + print if watched, exit 1 if not
  python hover_watchlist.py --resolve <resource> --field <name> --outcome "<what changed>"
  python hover_watchlist.py --selftest
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WATCH_FILE = os.path.join(HERE, 'hover-watchlist.json')
EXIT_CLEAN, EXIT_NOT_FOUND, EXIT_COULD_NOT_RUN = 0, 1, 2


def load(path=None):
    # path=None, resolved to the MODULE-LEVEL WATCH_FILE at CALL time, not
    # bound at def time -- a mutable default (def load(path=WATCH_FILE))
    # freezes whatever WATCH_FILE was when the module first loaded, so the
    # fixtures' own monkeypatch of WATCH_FILE (the standard way every other
    # tool in this directory redirects itself for a test) would silently
    # keep writing to the REAL file underneath the swap. Caught by this
    # module's own selftest on first run (2026-09-28) before it shipped.
    path = path or WATCH_FILE
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise RuntimeError('watchlist %s exists but does not parse: %s -- '
                           'refusing to treat a broken file as an empty '
                           'list (that would silently drop every open item)'
                           % (path, e))
    if not isinstance(data, list):
        raise RuntimeError('watchlist %s is not a JSON list' % path)
    return data


def save(items, path=None):
    path = path or WATCH_FILE
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=1, sort_keys=True)
        f.write('\n')


def active_items(resource, path=None):
    """Every OPEN (not resolved) watch entry for this resource name."""
    return [w for w in load(path) if w.get('resource') == resource
            and not w.get('resolved_at')]


def check_line(resource, path=None):
    """A one-line reminder string for this resource, or None if nothing is
    watched on it. This is what hover_cold_scan_pool.py calls inline."""
    items = active_items(resource, path)
    if not items:
        return None
    parts = ['%s: %s (added #%s, %s)' % (w.get('field', '?'), w.get('note', ''),
                                         w.get('added_seq', '?'), w.get('added_at', ''))
             for w in items]
    return 'WATCH (%s): %s -- re-check whether a consumer now exists' % (
        resource, '; '.join(parts))


def cmd_add(resource, field, note, seq=None):
    from datetime import datetime, timezone
    items = load()
    for w in items:
        if w.get('resource') == resource and w.get('field') == field \
                and not w.get('resolved_at'):
            print('already watched: %s.%s' % (resource, field))
            return EXIT_CLEAN
    items.append({
        'resource': resource, 'field': field, 'note': note,
        'added_seq': seq, 'added_at': datetime.now(timezone.utc)
        .strftime('%Y-%m-%dT%H:%M:%SZ'),
        'resolved_at': None, 'resolved_outcome': None,
    })
    save(items)
    print('watching: %s.%s -- %s' % (resource, field, note))
    return EXIT_CLEAN


def cmd_resolve(resource, field, outcome):
    from datetime import datetime, timezone
    items = load()
    hit = False
    for w in items:
        if w.get('resource') == resource and w.get('field') == field \
                and not w.get('resolved_at'):
            w['resolved_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            w['resolved_outcome'] = outcome
            hit = True
    if not hit:
        print('no OPEN watch entry for %s.%s' % (resource, field))
        return EXIT_NOT_FOUND
    save(items)
    print('resolved: %s.%s -- %s' % (resource, field, outcome))
    return EXIT_CLEAN


def run_fixtures():
    import tempfile
    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    scratch = os.path.join(tempfile.mkdtemp(prefix='hover_watchlist_'), 'w.json')
    ck('empty/missing file loads as []', load(scratch) == [])

    global WATCH_FILE
    real = WATCH_FILE
    WATCH_FILE = scratch
    try:
        cmd_add('res_x', 'flag_y', 'looks like a gate, has none yet', seq=999)
        ck('after add, check_line() fires', check_line('res_x') is not None
           and 'flag_y' in check_line('res_x'))
        ck('an unwatched resource returns None, not an empty-string false '
           'positive', check_line('res_never_watched') is None)
        cmd_add('res_x', 'flag_y', 'duplicate add of the same open item')
        ck('a duplicate add does not create a second open row',
           len(active_items('res_x')) == 1)
        cmd_resolve('res_x', 'flag_y', 'a consumer now reads it, filed as finding #999')
        ck('after resolve, check_line() goes quiet -- a resolved item stops '
           'nagging on every future draw', check_line('res_x') is None)
        ck('KNOWN-BAD CONTROL, MUST KEEP FAILING: reading the RESOLVED row '
           'directly (bypassing active_items()) still shows it happened -- '
           'resolving must not ERASE history, only silence the live nag',
           any(w['resource'] == 'res_x' and w['resolved_at'] for w in load(scratch)))
        cmd_add('res_x', 'flag_y', 're-opened after the resolution regressed')
        ck('a new watch on the same resource+field after resolution opens a '
           'FRESH entry, not reusing the resolved one',
           len([w for w in load(scratch) if w['resource'] == 'res_x']) == 2)
    finally:
        WATCH_FILE = real

    # --- F-MUTDEFAULT-CONTROL, 2026-09-28: reproduces the GENERAL BUG CLASS ---
    # --- this module's own first run caught in itself (def load(path=      ---
    # --- WATCH_FILE): binds WATCH_FILE's value ONCE, at module import,     ---
    # --- not at call time -- so a later reassignment of the module global  ---
    # --- (exactly what every fixture's own monkeypatch does, and the same  ---
    # --- pattern hover_log.py/hover_cold_scan_pool.py already use to       ---
    # --- redirect themselves under test) is silently invisible to it.      ---
    # --- This does not test load() (already fixed to path=None) -- it      ---
    # --- reproduces the BANNED PATTERN ITSELF via exec'd source, so the    ---
    # --- control still exists and still demonstrably fails even after     ---
    # --- every real call site in this file is clean, which is the whole   ---
    # --- point of a control: it must keep failing on its own account,     ---
    # --- not become vacuous the moment the real bug is fixed.              ---
    scratch_a = os.path.join(tempfile.mkdtemp(prefix='hover_watchlist_mutdef_a_'), 'a.json')
    scratch_b = os.path.join(tempfile.mkdtemp(prefix='hover_watchlist_mutdef_b_'), 'b.json')
    with open(scratch_a, 'w', encoding='utf-8') as f:
        json.dump([{'marker': 'FILE-A'}], f)
    with open(scratch_b, 'w', encoding='utf-8') as f:
        json.dump([{'marker': 'FILE-B'}], f)

    ns = {'WATCH_FILE': scratch_a, 'json': json, 'os': os}
    # THE BANNED PATTERN, reproduced verbatim in a throwaway namespace: the
    # default is evaluated RIGHT NOW, while ns['WATCH_FILE'] == scratch_a.
    exec('def buggy_load(path=WATCH_FILE):\n'
         '    with open(path, encoding="utf-8") as f:\n'
         '        return json.load(f)\n', ns)
    ns['WATCH_FILE'] = scratch_b   # the exact move every fixture in this file makes
    buggy_result = ns['buggy_load']()
    ck('F-MUTDEFAULT-CONTROL, KNOWN-BAD, MUST KEEP FAILING: a function '
       'defined with the banned "path=WATCH_FILE" default still reads '
       'FILE-A after WATCH_FILE is reassigned to FILE-B -- the exact class '
       'of staleness this module\'s own load()/save()/active_items()/'
       'check_line() were rewritten to path=None to avoid',
       buggy_result[0]['marker'] == 'FILE-A')
    fixed_result = load(scratch_b)
    ck('the FIXED pattern (path=None, resolved at call time) reads FILE-B '
       'against the identical reassignment sequence -- proves the fix, not '
       'just the absence of the bug', fixed_result[0]['marker'] == 'FILE-B')

    corrupt = os.path.join(tempfile.mkdtemp(prefix='hover_watchlist_bad_'), 'w.json')
    with open(corrupt, 'w', encoding='utf-8') as f:
        f.write('{not valid json')
    raised = False
    try:
        load(corrupt)
    except RuntimeError as e:
        raised = 'does not parse' in str(e)
    ck('a corrupt watchlist file RAISES rather than silently returning [] '
       '-- a parse failure must never look identical to "nothing watched"',
       raised)

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


def main(argv):
    if '--selftest' in argv:
        return EXIT_CLEAN if run_fixtures() else EXIT_COULD_NOT_RUN
    if '--list' in argv:
        items = load()
        open_items = [w for w in items if not w.get('resolved_at')]
        print('%d open watch item(s) of %d total:' % (len(open_items), len(items)))
        for w in open_items:
            print('  %s.%s -- %s (added #%s, %s)' % (
                w['resource'], w['field'], w['note'], w.get('added_seq'), w.get('added_at')))
        return EXIT_CLEAN
    if '--add' in argv:
        i = argv.index('--add')
        resource = argv[i + 1]
        field = argv[argv.index('--field') + 1] if '--field' in argv else '?'
        note = argv[argv.index('--note') + 1] if '--note' in argv else ''
        seq = argv[argv.index('--seq') + 1] if '--seq' in argv else None
        return cmd_add(resource, field, note, seq)
    if '--resolve' in argv:
        i = argv.index('--resolve')
        resource = argv[i + 1]
        field = argv[argv.index('--field') + 1] if '--field' in argv else '?'
        outcome = argv[argv.index('--outcome') + 1] if '--outcome' in argv else ''
        return cmd_resolve(resource, field, outcome)
    if '--check' in argv:
        i = argv.index('--check')
        line = check_line(argv[i + 1])
        if line:
            print(line)
            return EXIT_CLEAN
        return EXIT_NOT_FOUND
    print('usage: --add <resource> --field <f> --note "<why>" [--seq N] | '
          '--resolve <resource> --field <f> --outcome "<what>" | --list | '
          '--check <resource> | --selftest')
    return EXIT_COULD_NOT_RUN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
