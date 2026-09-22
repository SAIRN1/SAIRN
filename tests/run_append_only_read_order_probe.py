"""tools/append_only_read_order_scan.py must REFUSE and must DISCRIMINATE.

Run: python tests/run_append_only_read_order_probe.py

# REQUIREMENT: a scanner that has only ever been run on real data, and has only
#   ever agreed with the person who wrote it, is not known to be a scanner. Every
#   arm below drives a SYNTHETIC repo built from the rule rather than copied from
#   the real one, and every positive arm is PAIRED with a control that requires
#   the opposite answer -- because an arm that only ever says "found it" is
#   satisfied by a tool that says "found it" about everything.

THE CRITERIA ARE LOCKED AGAINST FIXTURES BEFORE THE TOOL IS BELIEVED ON REAL
DATA. That is the first of the cross-domain disciplines and it is the one this
file exists for: the scan's first real run produced six unordered reads, of
which exactly ONE was a defect, and the difference was decided by reading
consumers rather than by the scanner. A scanner whose population or key-list is
quietly wrong would produce a list of the same SHAPE and nobody would know.

FOUR OF THESE ARMS FAILED WHEN THEY WERE FIRST WRITTEN, all against the real
file, and each one is the reason its pair exists:

  * The own-key exclusion started as a `&\\w*_id=eq\\.` wildcard, which threw
    away rf_claim_photos and rf_proposals -- real LIST reads keyed on a PARENT
    -- and hid four reads from the count. C5/C6 are the pair that pins the
    distinction between a row's own id and its parent's.
  * `agreement_id` was missing from the own-key list, so a single-row existence
    check came out as a finding. C5 covers it by name.
  * A single grant-based derivation MISSES alf_incidents and alf_op_audits,
    which are append-only by contract and carry UPDATE for merge-duplicates.
    C3/C4 require the contract derivation to carry real weight on its own.
  * An empty population reports every app clean, which is the worst output this
    tool can produce. C9 requires that to exit 2 instead.
"""
import io
import os
import importlib.util
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'append_only_read_order_scan.py')

passed = failed = 0


def ok(name, cond, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   ' + name)
    else:
        failed += 1
        print('  FAIL ' + name + ('\n         ' + str(detail) if detail else ''))


def load():
    spec = importlib.util.spec_from_file_location('aoros', TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def build(tmp, grants, dispatcher):
    """A synthetic repo: sql/fixture.sql plus api/sd-data.js, nothing else."""
    os.makedirs(os.path.join(tmp, 'sql'), exist_ok=True)
    os.makedirs(os.path.join(tmp, 'api'), exist_ok=True)
    io.open(os.path.join(tmp, 'sql', 'fixture.sql'), 'w',
            encoding='utf-8').write(grants)
    io.open(os.path.join(tmp, 'api', 'sd-data.js'), 'w',
            encoding='utf-8').write(dispatcher)
    return tmp


def run(grants, dispatcher):
    m = load()
    tmp = tempfile.mkdtemp(prefix='aoro-')
    try:
        m.REPO = build(tmp, grants, dispatcher)
        return m.scan(), None
    except Exception as e:                      # noqa: BLE001 -- the arm reads it
        return None, e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


GRANT_APPEND = "grant select, insert on public.fx_trail to service_role;\n"
GRANT_MUTABLE = "grant select, insert, update on public.fx_trail to service_role;\n"
READ = ("    const r = await fetch(rest('fx_trail?license_hash=eq.' + "
        "enc(licHash) + '&select=entry_id,data%s'), { headers });\n")


def main():
    print('append_only_read_order_scan.py -- discriminate, and refuse when it '
          'cannot run\n')

    # ── C1/C2: does an order= clause actually move the answer? ──────────────
    r, e = run(GRANT_APPEND, READ % '')
    ok('C1 an append-only table read WITHOUT order= is reported unordered',
       r and [u['table'] for u in r['unordered']] == ['fx_trail'], e or r)
    r2, e2 = run(GRANT_APPEND, READ % '&order=created_at.desc')
    ok('C2 CONTROL: the SAME read WITH order= is reported ORDERED and is absent '
       'from the unordered list -- so C1 discriminates on the clause and not on '
       'the table',
       r2 and not r2['unordered'] and [o['table'] for o in r2['ordered']] == ['fx_trail'],
       e2 or r2)

    # ── C3/C4: the contract derivation must carry weight ON ITS OWN ─────────
    contract_disp = (READ % '') + (
        "    const rows = await appendOnlyExisting(res, existingR, 'fx_trail');\n")
    r3, e3 = run(GRANT_MUTABLE, contract_disp)
    ok('C3 a table with an UPDATE grant is still in the population when the '
       'dispatcher enforces append-only in code -- the grant test alone MISSES '
       'alf_incidents and alf_op_audits',
       r3 and 'fx_trail' in r3['population'] and 'fx_trail' in r3['by_contract']
       and 'fx_trail' not in r3['by_grant'], e3 or r3)
    r4, e4 = run(GRANT_MUTABLE, READ % '')
    ok('C4 CONTROL: the same UPDATE-granted table with NO contract marker is '
       'NOT in the population, so C3 is discriminating on the marker rather '
       'than admitting everything',
       r4 is None or 'fx_trail' not in r4['population'], e4 or r4)

    # ── C5/C6: a row's OWN key is not a list; a PARENT key is ───────────────
    own = ("    const r = await fetch(rest('fx_trail?license_hash=eq.' + "
           "enc(licHash) + '&agreement_id=eq.' + enc(id) + '&select=entry_id'), "
           "{ headers });\n")
    r5, e5 = run(GRANT_APPEND, own)
    ok('C5 a read keyed on the row\'s OWN id (agreement_id) is not a list read '
       'and is not reported -- ordering one row is meaningless',
       r5 and not r5['unordered'] and not r5['ordered'], e5 or r5)
    parent = ("    const r = await fetch(rest('fx_trail?license_hash=eq.' + "
              "enc(licHash) + '&claim_id=eq.' + enc(cid) + '&select=entry_id,data'), "
              "{ headers });\n")
    r6, e6 = run(GRANT_APPEND, parent)
    ok('C6 CONTROL: a read keyed on a PARENT id IS a list read and IS reported '
       '-- this is the distinction a `_id=eq.` wildcard got wrong and hid four '
       'real reads behind',
       r6 and [u['table'] for u in r6['unordered']] == ['fx_trail'], e6 or r6)

    # ── C7: the tool's own prose must not satisfy it ────────────────────────
    commented = ("    // const r = await fetch(rest('fx_trail?license_hash=eq.' "
                 "+ enc(licHash) + '&select=entry_id,data'), { headers });\n"
                 + (READ % '&order=created_at.desc'))
    r7, e7 = run(GRANT_APPEND, commented)
    ok('C7 a COMMENTED-OUT unordered query does not count -- a fix\'s own '
       'header quotes the query it replaced, and a raw scan reads that as code',
       r7 and not r7['unordered'], e7 or r7)

    # ── C8/C9/C10: could-not-run is a THIRD STATE, never a clean sweep ──────
    m = load()
    tmp = tempfile.mkdtemp(prefix='aoro-')
    try:
        m.REPO = build(tmp, GRANT_APPEND, READ % '')
        shutil.rmtree(os.path.join(tmp, 'sql'))
        try:
            m.scan()
            ok('C8 an absent sql/ directory REFUSES rather than reporting a '
               'population of zero', False, 'scan() returned normally')
        except m.CouldNotRun:
            ok('C8 an absent sql/ directory REFUSES rather than reporting a '
               'population of zero', True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    r9, e9 = run("-- no grants here at all\n", READ % '')
    ok('C9 an EMPTY population refuses -- "no append-only table matched either '
       'derivation" is a broken scanner, and reporting it as a clean platform '
       'is the worst output this tool can produce',
       r9 is None and isinstance(e9, Exception), e9 or r9)

    m = load()
    tmp = tempfile.mkdtemp(prefix='aoro-')
    try:
        m.REPO = build(tmp, GRANT_APPEND, READ % '')
        os.remove(os.path.join(tmp, 'api', 'sd-data.js'))
        try:
            m.scan()
            ok('C10 an unreadable dispatcher REFUSES, naming the file',
               False, 'scan() returned normally')
        except m.CouldNotRun as e:
            ok('C10 an unreadable dispatcher REFUSES, naming the file',
               'sd-data.js' in str(e), e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── C11: the third state is a SET, not a silence ────────────────────────
    r11, e11 = run(GRANT_APPEND + "grant select, insert on public.fx_unread to "
                   "service_role;\n", READ % '&order=created_at.desc')
    ok('C11 a table in the population with NO read in the dispatcher lands in '
       'no_read_located, not in ordered -- could-not-tell is never folded into '
       'a pass',
       r11 and r11['no_read_located'] == ['fx_unread']
       and not any(u['table'] == 'fx_unread' for u in r11['ordered']), e11 or r11)

    print('\n%d passed, %d failed' % (passed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
