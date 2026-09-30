"""Device-local stored data that carries a real tier and cannot have a register row.

    python tools/stored_data_criticality_check.py            # report, exit 1 on a problem
    python tools/stored_data_criticality_check.py --quiet     # exit code only

WHY THIS EXISTS, AND WHY IT IS A SECOND TABLE RATHER THAN MORE ROWS IN THE FIRST
──────────────────────────────────────────────────────────────────────────────
`docs/CRITICALITY-TIERS.md` tiers RESOURCES. That is mechanical, not a
preference: `tools/criticality_tier_check.py` enforces a bijection in both
directions against `api/_resources/*.js`, and its own refusal text says
`The unit of this table is the registry.` A device-local `localStorage` key
therefore cannot have a row there -- adding one prints `NOT A RESOURCE` and
turns `tests/run_criticality_tier_probe.py` RED on main.

Two such keys carry an A-class risk anyway:

  sen_evv_queue    while a device is offline this is the ONLY copy of
                   wage-determining, EVV-regulated clock events joined to a
                   client's home coordinate.
  law_strike_log   a contemporaneous peremptory-strike record, which is what a
                   Batson challenge is answered from. One cache clear removes it.

The existing venue with teeth -- an app's `notSynced` declaration plus
`tools/local_only_collection_check.py` -- records that a key is device-local and
carries NO TIER. So the platform could say *"this lives on one device"* and
could not say *"and losing it loses a wage-determining record."* That gap is
what this table closes.

THE NARROW OPTION WAS CHOSEN FOR WHAT IT DOES NOT TOUCH. The other honest route
was extending the register's unit to stored data, which changes the unit for all
391 rows -- and tiering the wrong unit is the mistake that register already made
once, at app granularity, and corrected by measurement. So the register's
bijection is left exactly as it is, and the BOUNDARY is enforced from this side
instead: a row here whose key IS a registered resource is refused. The two
tables are disjoint by arm, not by good intentions.

WHAT IT CAN AND CANNOT SEE, said plainly because a checker that overstates its
reach is worse than none:

  IT CAN SEE    a row whose key is a registered resource and so belongs in the
                other table; a key that appears nowhere in the app source the
                row names; a tier outside A/B/C; a Tier A row whose evidence
                cell carries no citation; a venue cell naming no recognised
                venue; a venue cell whose CLAIM is false against the app's real
                `notSynced` list; and a table that has dropped the sentence
                stating its own unit.

  IT CANNOT SEE whether a tier is RIGHT. Nothing mechanical can -- that is what
                the evidence column is for. **AND IT IS NOT A COMPLETENESS
                CHECK.** It cannot enumerate every `localStorage` key on the
                platform and then ask which ones are missing a row, so a clean
                run says the rows PRESENT are well-formed and says nothing about
                rows that should exist and do not. A reader who takes a silence
                here for coverage has been misled by this tool, which is why the
                sentence is printed on every run rather than left in a docstring.

IT REPORTS AND NEVER REWRITES A JUDGEMENT. The tier and its sentence are a
judgement; a tool that regenerated this file would delete exactly the part that
matters and leave a table that looks authoritative because a machine made it.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, 'docs', 'STORED-DATA-CRITICALITY.md')
RESDIR = os.path.join(REPO, 'api', '_resources')

# Bumped when any criterion below changes shape. Stamped because
# tools/sabotage_control_check.py measured that an unversioned lock cannot tell
# a criterion that was rewritten from one that rotted.
CRITERIA_VERSION = 1

# The full clause, not the prefix. `The unit of this table is` alone also matches
# the register's own refusal message, which this file QUOTES verbatim two
# paragraphs later -- so the short form would be satisfied by the quotation and
# would pass a table that had dropped its own header sentence.
UNIT_SENTENCE = 'The unit of this table is a `localStorage` KEY'
VENUES = ('notSynced', 'EXCLUSION', 'UNDECLARED')


# ── CRITERION 1: CELLS ──────────────────────────────────────────────────────
# AN ESCAPED PIPE IS CONTENT, NOT A COLUMN BOUNDARY. The register's own index
# row tripped exactly this, and a bare `|| 0` inside a cell leaked a 6-cell row
# into 8 three separate times in one session. Every read below is positional, so
# getting this wrong shifts every column silently.
def cells(line):
    out, buf, i = [], [], 0
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s) and s[i + 1] == '|':
            buf.append('|')
            i += 2
            continue
        if s.startswith('&#124;', i):
            buf.append('|')
            i += 6
            continue
        if c == '|':
            out.append(''.join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    out.append(''.join(buf).strip())
    return out


# ── CRITERION 2: VENUE ──────────────────────────────────────────────────────
# Returns the declared venue token, or None when the cell names none. UNDECLARED
# is an ALLOWED answer and must be SAID -- for both rows shipping today it is the
# true one and is itself the finding. What is refused is a cell that says
# neither, because that is where a silence goes.
#
# THE EARLIEST TOKEN WINS, AND THAT RULE WAS PAID FOR BEFORE THIS FILE SHIPPED.
# The first version scanned VENUES in declaration order, so a cell reading
# "**UNDECLARED** -- sairnsenior.js has no `notSynced` list at all" was
# classified notSynced: the cell was refused as a FALSE declaration on the
# strength of the word it used to explain that there was none. An honest venue
# cell names its venue and then says why, so position is the criterion -- the
# cell must LEAD with its venue. Both directions are locked in the fixtures.
def venue_token(cell):
    hits = []
    for v in VENUES:
        m = re.search(r'(?<![A-Za-z])%s(?![A-Za-z])' % re.escape(v), cell)
        if m:
            hits.append((m.start(), v))
    return min(hits)[1] if hits else None


# ── CRITERION 3: EVIDENCE CARRIES A CITATION ────────────────────────────────
# `file.html:1234` or a short `:1234` continuation. A tier asserted with no
# evidence is a label, which is the rule the register already states.
CITE = re.compile(r'`(?:[\w./-]+\.(?:html|js|sql|md|json))?:\d{1,7}(?:-\d{1,7})?`')


def has_cite(cell):
    return bool(CITE.search(cell))


# ── THE KNOWN-POSITIVE FIXTURE SET ──────────────────────────────────────────
# Every criterion locked in BOTH directions against hand-built strings, before
# the tool is pointed at the real table. Discipline 1: a criterion validated on
# the data it will judge cannot be distinguished from one tuned to flatter it.
FIXTURE_CASES = (
    ('cells', r'| `k` | `a.html` | **A** | **A** | i | c | v | e |',
     8, 'an ordinary eight-cell stored-data row'),
    ('cells', r'| `k` | `a.html` | **A** | **A** | cap 200 \| FIFO | c | v | e |',
     8, 'AN ESCAPED PIPE IS CONTENT. Counting it as a boundary makes nine cells '
        'and every positional read after it is off by one'),
    ('cells', r'| `k` | `a.html` | **A** | **A** | a &#124; b | c | v | e |',
     8, 'the HTML-entity pipe this repo uses inside register cells is content too'),
    ('venue', 'notSynced in `api/_resources/sairnvet.js`', True,
     'a declared notSynced venue is recognised'),
    ('venue', '**UNDECLARED** -- in neither list, and that is the finding', True,
     'UNDECLARED IS AN ALLOWED ANSWER. Refusing it would push the table towards '
        'claiming a declaration that does not exist'),
    ('venue', 'the declared EXCLUSION block', True,
     'the third venue, used for signing-key material'),
    ('venue', 'see the notes below', False,
     'A CELL NAMING NO VENUE IS THE FINDING. This is the silence the column '
        'exists to refuse'),
    ('venue', 'notSyncedish', False,
     'a word that merely CONTAINS a venue name is not that venue -- the bound '
        'is there so a near-miss cannot pass as a declaration'),
    # ── THE AMBIGUITY THAT ACTUALLY BIT, LOCKED IN BOTH DIRECTIONS ──────────
    # The first version of venue_token scanned VENUES in declaration order and
    # classified the real sen_evv_queue cell as notSynced, then refused it as a
    # FALSE declaration -- on the strength of the word it used to say there was
    # none. Both cells below are the two readings of the same sentence pair.
    ('venue_which', '**UNDECLARED** -- `api/_resources/sairnsenior.js` has no '
                    '`notSynced` list at all', 'UNDECLARED',
     'THE EARLIEST TOKEN WINS. A cell that leads with UNDECLARED and then names '
        'notSynced to explain the absence is UNDECLARED, not a false claim'),
    ('venue_which', 'notSynced in `api/_resources/sairnvet.js`, so it is not '
                    'UNDECLARED any more', 'notSynced',
     'THE OTHER DIRECTION, which is the half a one-sided fixture would miss: a '
        'cell that leads with notSynced and mentions UNDECLARED in passing is a '
        'real declaration'),
    ('cite', 'written at `sairnlaw.html:7157`', True,
     'a full file:line citation'),
    ('cite', 'and the flush at `:3047`', True,
     'a short continuation cite, the shape the register already uses'),
    ('cite', 'It is a device-local FIFO outbox capped at 200 entries.', False,
     'PROSE WITH A NUMBER IN IT IS NOT A CITATION, and treating it as one is how '
        'an uncited tier reads as an evidenced one'),
    ('cite', 'described in `docs/SAIRN-OPEN-WORK-INDEX.md`', False,
     'a file reference with no line is not a citation this tool can re-derive'),
)


def run_fixtures():
    """[] when every hand-built case classifies correctly."""
    bad = []
    for kind, src, want, why in FIXTURE_CASES:
        if kind == 'cells':
            got = len(cells(src))
        elif kind == 'venue':
            got = venue_token(src) is not None
        elif kind == 'venue_which':
            got = venue_token(src)
        else:
            got = has_cite(src)
        if got != want:
            bad.append('EXPECTED %r, got %r -- %s' % (want, got, why))
    return bad


# ── THE REGISTRY, READ FAIL-CLOSED ──────────────────────────────────────────
def _strip_comments(src):
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return re.sub(r'(?m)//.*$', '', src)


def registry():
    """(registered_names, not_synced_by_app) or None when it cannot be read.

    None means COULD NOT RUN, never "clean". Without the registry this tool
    cannot tell an overlap with the register from a table with none, and a gate
    wrapped in `if isfile(...)` does not skip one check -- it reports a pass it
    never performed (PR §1.11).
    """
    if not os.path.isdir(RESDIR):
        return None
    names, notsynced = set(), {}
    files = [f for f in sorted(os.listdir(RESDIR))
             if f.endswith('.js') and not f.endswith('.test.js') and f != 'index.js']
    if not files:
        return None
    for fn in files:
        src = _strip_comments(io.open(os.path.join(RESDIR, fn),
                                     encoding='utf-8', errors='replace').read())
        app = fn[:-3]
        m = re.search(r'resources:\s*(RESOURCES|\[(?:[^][]|\[[^][]*\])*\])', src)
        if m:
            body = m.group(1)
            if body == 'RESOURCES':
                body = src
            names.update(re.findall(r"""['"]([a-z][a-z0-9_]{2,60})['"]""", body))
        m2 = re.search(r'notSynced:\s*\[((?:[^][]|\[[^][]*\])*)\]', src)
        notsynced[app] = set(re.findall(r"""['"]([a-z][a-z0-9_]{2,60})['"]""",
                                        m2.group(1))) if m2 else set()
    if not names:
        return None
    return names, notsynced


def parse(text):
    """[(key, app_src, integ, conf, venue_cell, evidence_cell, lineno, ncells)]"""
    rows = []
    for n, line in enumerate(text.split('\n'), 1):
        if not line.startswith('| `'):
            continue
        c = cells(line)
        m = re.match(r'^`([a-z][a-z0-9_]{2,60})`$', c[0])
        if not m:
            continue
        rows.append((m.group(1),
                     c[1].strip('`') if len(c) > 1 else '',
                     c[2] if len(c) > 2 else '',
                     c[3] if len(c) > 3 else '',
                     c[6] if len(c) > 6 else '',
                     c[7] if len(c) > 7 else '',
                     n, len(c)))
    return rows


def tier_of(cell):
    m = re.match(r'^\*\*([A-Z])\*\*$', cell.strip())
    return m.group(1) if m else cell.strip()


def main(argv):
    quiet = '--quiet' in argv

    # ── THE LOCK RUNS ON THE REAL RUN AND PRINTS ───────────────────────────
    # Not behind a flag. A self-test that runs when somebody asks is a control
    # with a shorter name, and the reader of a clean table is not asking. A
    # failing lock is exit 2 and prints NO row count: a verdict printed beside
    # a broken lock is the verdict a reader keeps.
    bad = run_fixtures()
    if bad:
        print('CRITERIA LOCK FAILED -- %d of %d fixtures misclassified. NOTHING '
              'REAL WAS JUDGED:' % (len(bad), len(FIXTURE_CASES)))
        for b in bad:
            print('  ! %s' % b)
        return 2
    if not quiet:
        print('criteria lock: %d/%d fixtures classify correctly (CRITERIA_VERSION '
              '%d), on hand-built rows only'
              % (len(FIXTURE_CASES), len(FIXTURE_CASES), CRITERIA_VERSION))

    if not os.path.isfile(DOC):
        print('docs/STORED-DATA-CRITICALITY.md is missing -- that is the finding, '
              'not a reason to pass.')
        return 1

    text = io.open(DOC, encoding='utf-8', errors='replace').read()

    reg = registry()
    if reg is None:
        print('COULD NOT RUN -- api/_resources is unreadable or holds no parsable '
              'resources array, so the boundary against '
              'docs/CRITICALITY-TIERS.md could not be checked at all.')
        print('  NOT A PASS. Without api/_resources this tool cannot tell a row '
              'that belongs in the register from one that belongs here.')
        return 2
    registered, notsynced = reg

    problems = []
    rows = parse(text)

    if UNIT_SENTENCE not in text:
        problems.append(
            'NO UNIT STATED   the table does not contain the sentence "%s ...". '
            'Tiering a new unit has to be said out loud in the header, because '
            'tiering the wrong unit is the mistake docs/CRITICALITY-TIERS.md '
            'already made once and corrected.' % UNIT_SENTENCE)

    if not rows:
        problems.append(
            'NO ROWS          the table parsed to zero rows. An empty table and a '
            'table whose row shape stopped matching look identical from the exit '
            'code, so this is a problem rather than a clean run.')

    for key, app_src, integ, conf, venue_cell, evid, ln, ncells in rows:
        where = '%s (:%d)' % (key, ln)

        if ncells != 8:
            problems.append(
                'BAD SHAPE        %s has %d cells, not 8. Every read below is '
                'positional, so a leaked pipe moves the tier into the app column '
                'and the check would judge the wrong string.' % (where, ncells))
            continue

        if key in registered:
            problems.append(
                'IS A RESOURCE    %s is in an api/_resources resources array, so '
                'it belongs in docs/CRITICALITY-TIERS.md and having it in both '
                'tables is how two tables start disagreeing about one thing. '
                'This table is for stored data that CANNOT have a register row.'
                % where)

        src_path = os.path.join(REPO, app_src)
        if not app_src or not os.path.isfile(src_path):
            problems.append(
                'NO SOURCE        %s names app source %r, which does not exist. '
                'The key cannot be re-derived, so the row cannot be re-checked '
                'against anything.' % (where, app_src))
        elif key not in io.open(src_path, encoding='utf-8', errors='replace').read():
            problems.append(
                'GHOST KEY        %s does not appear anywhere in %s. A tier for a '
                'key nothing writes protects nothing while looking like it does '
                '-- the sd_owner_pin shape.' % (where, app_src))

        for axis, cell in (('integrity', integ), ('confidentiality', conf)):
            t = tier_of(cell)
            if t not in ('A', 'B', 'C'):
                problems.append(
                    'BAD TIER         %s has %s tier %r, which is not A, B or C.'
                    % (where, axis, t))

        v = venue_token(venue_cell)
        if v is None:
            problems.append(
                'NO VENUE         %s names no declaration venue. One of %s is '
                'required and UNDECLARED is an allowed answer -- what is refused '
                'is a cell that says neither, because that is where the finding '
                'goes missing.' % (where, ', '.join(VENUES)))
        else:
            app = os.path.splitext(os.path.basename(app_src))[0] if app_src else ''
            declared = key in notsynced.get(app, set())
            if v == 'notSynced' and not declared:
                problems.append(
                    'VENUE FALSE      %s claims a notSynced declaration and %s is '
                    'not in api/_resources/%s.js\'s notSynced list. A venue cell '
                    'nothing verifies is the claim this column exists to make '
                    'checkable.' % (where, key, app))
            if v == 'UNDECLARED' and declared:
                problems.append(
                    'VENUE FALSE      %s says UNDECLARED and %s IS in '
                    'api/_resources/%s.js\'s notSynced list. The finding has been '
                    'closed and the row still reports it open.' % (where, key, app))

        if 'A' in (tier_of(integ), tier_of(conf)) and not has_cite(evid):
            problems.append(
                'NO EVIDENCE      %s is Tier A on an axis and its evidence cell '
                'carries no citation. A tier asserted with no evidence is a '
                'label -- the same rule docs/CRITICALITY-TIERS.md states.' % where)

    if not quiet:
        print()
        print('STORED_DATA_ROWS:%d' % len(rows))
        for key, app_src, integ, conf, venue_cell, evid, ln, nc in rows:
            print('  %-18s %s/%s  %-11s  %s'
                  % (key, tier_of(integ), tier_of(conf),
                     venue_token(venue_cell) or '(none)', app_src))
        print('PROBLEMS:%d' % len(problems))

    if problems:
        print()
        for p in problems:
            print('  %s' % p)

    if not quiet:
        print()
        print('NOTE: this says the rows PRESENT are well-formed, that none of them '
              'belongs in the resource register, and that each Tier A cites '
              'something. It does not say the tier is right -- nothing mechanical '
              'can. AND IT IS not a completeness check: it cannot enumerate every '
              'localStorage key on the platform, so a clean run is silent about '
              'rows that should exist and do not.')

    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
