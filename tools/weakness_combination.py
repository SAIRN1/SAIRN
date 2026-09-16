"""Item 53 -- each risk was accepted ON A BOUND. Does another risk remove that bound?

    python tools/weakness_combination.py
    python tools/weakness_combination.py --fixtures   # blind lock, reads no register
    python tools/weakness_combination.py --json

Exit 0 when no pair shares a bound, 1 when one does, 2 when the register could
not be read. REPORT ONLY. Whether a pair actually compounds is a judgement and
this refuses to make it.

── THE PRECEDENT, AND WHY IT IS NOT AN ANALOGY ────────────────────────────────
Citicorp Center, 1978. The tower was designed for perpendicular winds and
checked against them. Separately, the welded joints of the chevron bracing were
value-engineered to BOLTED joints -- a normal, approved substitution, fine on
its own. Neither decision was wrong. Together, under a quartering wind nobody
had run, the building was one storm from collapse, and it was found by a student
asking a question about a case that had never been combined.

The lesson is precise and it is NOT "review harder". Each decision was accepted
because something bounded it. The second decision removed the first one's bound,
and no review looked at both, because each had already been signed off ALONE.

── SO THE MECHANICAL QUESTION IS NARROW ───────────────────────────────────────
`docs/ACCEPTED-RISKS.md` requires every entry to say WHAT BOUNDS IT and WHAT
TRIGGER means re-read this. That structure is the thing that makes a combination
check possible at all: a risk with a stated bound can be asked whether anything
else touches that bound.

  DOES ANY OTHER ENTRY NAME THE SAME MECHANISM THIS ENTRY'S BOUND RESTS ON?

That is answerable from the register. Whether the overlap actually compounds is
not, and this prints the pair and the shared mechanism rather than a verdict.

── FOUR SIGNALS, DECLARED BEFORE THE REGISTER WAS READ ────────────────────────
  SHARED MECHANISM     both entries name the same file, module, env var or
                       service.
  BOUND NAMES THE OTHER  one entry's WHAT BOUNDS IT names a mechanism the other
                       entry is ABOUT. This is the literal Citicorp shape and
                       the strongest of the four: A was accepted because X holds
                       it, and B is a recorded weakness IN X.
  NEITHER ANNOUNCES    both triggers are non-mechanical. Neither weakness will
                       tell anybody it changed, so their COMBINATION cannot be
                       noticed either -- and a pair of silent risks is worse
                       than the sum, because the first news of both is the
                       consequence.
  BOTH UNOWNED         neither entry has a named person. Not a technical
                       coupling; an ATTENTION coupling, and the register's own
                       rule is that a trigger nobody watches is not a trigger.

── ONE SIGNAL WAS REMOVED AFTER ITS FIRST REAL RUN, AND THE REASON IS THE ─────
── POINT OF HAVING RUN IT ─────────────────────────────────────────────────────
"BOUND IS NOT A CONTROL" was originally a fifth pair signal. On the real
register it fired on SIX PAIRS OUT OF SIX, because it is not a property of a
PAIR at all -- it is a property of ONE entry, which then propagates to every
pair that entry appears in. A signal that fires on everything is noise with a
table, which is the exact thing this file's own fixture lock asserts against.
It is now reported per ENTRY, where it belongs, and the pair signals are only
things that are genuinely about two.

── WHAT IT CANNOT DO, AND THE SECOND ONE IS THE LIMIT THAT MATTERS ────────────
  * Tell you a pair compounds. It tells you they share a mechanism.
  * SEE A RISK NOBODY WROTE DOWN. The register is four entries long. The
    Citicorp failure was a combination of two decisions that WERE both recorded;
    a combination involving something nobody recorded is invisible here and no
    amount of pair analysis over a register will find it. That is the real
    residual and it is stated on every run rather than implied by a clean exit.
  * Rank by severity. Both halves of a compounding pair can be `low`.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'ACCEPTED-RISKS.md')

CRITERIA_VERSION = '2026-09-15.1'

# A mechanism is a thing the platform can NAME: a file, a module, an env var, a
# service. Deliberately not "any shared word" -- two entries both containing the
# word "session" is not a shared mechanism, it is English.
MECHANISM_RX = [
    re.compile(r'`([a-zA-Z0-9_\-/\.]+\.(?:js|py|json|sql|md|html|yml))`'),
    re.compile(r'`([A-Z][A-Z0-9_]{5,})`'),
]

NOT_A_CONTROL = re.compile(
    r'that is a bound, not a control|nothing bounds|is not a control', re.I)
MECHANICAL_TRIGGER = re.compile(r'trigger\s*[-—–]*\s*\**mechanical', re.I)
NO_MECHANISM = re.compile(r'nothing mechanical', re.I)


def parse(path=None):
    """The entries, as fields. Returns None when the register cannot be read --
    never an empty list, because an empty list is indistinguishable from a
    register with nothing in it and would report CLEAN."""
    path = path or REGISTER
    if not os.path.exists(path):
        return None
    src = io.open(path, encoding='utf-8').read()
    body = src.split('## The entries', 1)
    if len(body) != 2:
        return None
    chunks = re.split(r'\n### ', body[1])
    out = []
    for c in chunks[1:]:
        c = c.split('\n---', 1)[0]
        title = c.splitlines()[0].strip()
        # The id is the leading token, not "everything before the dash": the
        # real register separates with an em-dash and a fixture written in
        # ASCII uses a hyphen, and splitting on a punctuation mark that varies
        # is how a parser silently returns a different key on real data.
        mid = re.match(r'([A-Za-z]+-\d+)', title)
        ident = mid.group(1) if mid else title.strip()[:12]
        fields, labelled = {}, []
        for m in re.finditer(r'^- \*\*(.+?):?\*\*(.*?)(?=^- \*\*|\Z)',
                             c, re.M | re.S):
            label = m.group(1).strip()
            key = re.split(r'[-—–,:]', label)[0].strip().lower()
            fields[key] = m.group(2).strip()
            labelled.append((label, m.group(2).strip()))
        mechs = set()
        for rx in MECHANISM_RX:
            mechs.update(rx.findall(c))
        owner = fields.get('open with', '')
        # SCOPED TO THE TRIGGER FIELD, not the whole entry. An entry can say
        # "nothing mechanical closes this" in its Why-accepted paragraph while
        # having a perfectly real mechanical trigger, and a whole-entry search
        # would silently downgrade it -- the same class of error as reading
        # "Nothing mechanical will announce it" as a mechanical trigger, in the
        # other direction.
        trig = [(lab, val) for lab, val in labelled
                if lab.lower().startswith('trigger')]
        trig_text = ' '.join(lab + ' ' + val for lab, val in trig)
        mech_trigger = bool(MECHANICAL_TRIGGER.search(trig_text)) \
            and not NO_MECHANISM.search(trig_text)
        trig_mechs = set()
        for rx in MECHANISM_RX:
            trig_mechs.update(rx.findall(trig_text))
        bound_text = fields.get('what bounds it', '')
        bound_mechs = set()
        for rx in MECHANISM_RX:
            bound_mechs.update(rx.findall(bound_text))
        where_mechs = set()
        for rx in MECHANISM_RX:
            where_mechs.update(rx.findall(fields.get('where', '')))
        out.append({
            'id': ident, 'title': title, 'text': c,
            'mechanisms': sorted(mechs),
            'bound_mechanisms': sorted(bound_mechs),
            'where_mechanisms': sorted(where_mechs),
            'trigger_mechanisms': sorted(trig_mechs),
            'bound_is_not_a_control': bool(NOT_A_CONTROL.search(c)),
            'mechanical_trigger': mech_trigger,
            'owner': owner,
            'unowned': 'unassigned' in owner.lower() or not owner,
        })
    return out or None


# ── IS A "MECHANICAL" TRIGGER ACTUALLY WATCHED BY ANYTHING? ───────────────────
# The register's OWN rule: "a trigger nobody watches is not a trigger." A
# mechanical trigger names a mechanism that PRODUCES a signal. That is not the
# same as something CONSUMING it, and the difference is invisible in the entry.
RUNNERS = [
    os.path.join('tools', 'report_only_checks.py'),
    os.path.join('tools', 'sairn_push_gate_hook.py'),
    os.path.join('tools', 'run_all_tests.py'),
    os.path.join('.claude', 'settings.json'),
]


def runner_text():
    """Everything that actually RUNS things on this platform, concatenated.
    Returns None when none of it could be read -- an empty string would make
    every trigger look unwatched, which is a finding invented by a missing
    file."""
    parts = []
    for r in RUNNERS:
        p = os.path.join(REPO, r)
        if os.path.exists(p):
            parts.append(io.open(p, encoding='utf-8', errors='replace').read())
    wf = os.path.join(REPO, '.github', 'workflows')
    if os.path.isdir(wf):
        for f in sorted(os.listdir(wf)):
            parts.append(io.open(os.path.join(wf, f), encoding='utf-8',
                                 errors='replace').read())
    return '\n'.join(parts) if parts else None


def unwatched_triggers(entries, runners):
    """Entries claiming a MECHANICAL trigger whose named mechanism appears in
    nothing that runs. Returns None when the runners could not be read."""
    if runners is None:
        return None
    out = []
    for e in entries:
        if not e['mechanical_trigger']:
            continue
        named = e['trigger_mechanisms']
        if not named:
            out.append((e['id'], [], 'the trigger is called MECHANICAL and names '
                                     'no mechanism at all'))
            continue
        missing = [m for m in named
                   if m not in runners and os.path.basename(m) not in runners]
        if missing:
            out.append((e['id'], missing,
                        'nothing that runs on this platform mentions %s, so the '
                        'signal is PRODUCED and never CONSUMED'
                        % ', '.join('`%s`' % m for m in missing)))
    return out


def pairs(entries):
    """Every unordered pair, with the signals each one trips. A pair that trips
    nothing is still RETURNED -- an analysis that only emits hits cannot be
    checked for having looked."""
    out = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            a, b = entries[i], entries[j]
            shared = sorted(set(a['mechanisms']) & set(b['mechanisms']))
            sig = []
            if shared:
                sig.append(('SHARED MECHANISM',
                            'both name %s' % ', '.join('`%s`' % s for s in shared)))
            # THE CITICORP SHAPE, and the only signal here that is about the
            # SUBSTANCE of the two rather than their paperwork: A was accepted
            # because X holds it, and B is a recorded weakness in X.
            for one, other in ((a, b), (b, a)):
                held_by = sorted(set(one['bound_mechanisms'])
                                 & set(other['where_mechanisms']))
                if held_by:
                    sig.append(('BOUND NAMES THE OTHER',
                                '%s is accepted because %s holds it, and %s is a '
                                'recorded weakness in exactly that'
                                % (one['id'],
                                   ', '.join('`%s`' % h for h in held_by),
                                   other['id'])))
            if not a['mechanical_trigger'] and not b['mechanical_trigger']:
                sig.append(('NEITHER ANNOUNCES',
                            'neither trigger is mechanical, so nothing will say '
                            'either one changed -- and the first news of the '
                            'combination is the consequence'))
            if a['unowned'] and b['unowned']:
                sig.append(('BOTH UNOWNED',
                            'no named person on either, and this register\'s own '
                            'rule is that a trigger nobody watches is not a trigger'))
            out.append({'a': a['id'], 'b': b['id'], 'shared': shared,
                        'signals': sig})
    return out


# ── THE BLIND LOCK ────────────────────────────────────────────────────────────
# Synthetic entries whose answer is known by construction, in BOTH directions
# for every signal. Written before the real register was parsed: a pair analysis
# that fires on everything and one that fires on nothing both look like a clean
# run from the outside.
FIXTURE = """# x

## The entries

### AX-1 - a thing

- **Where:** `alpha.js`
- **What bounds it:** `gamma.js` validates every call before it lands. That is a bound, not a control.
- **Trigger - MECHANICAL:** `tools/thing.py` says so, via a `warnings` entry.
- **Open with:** Michael, 2026-01-01.

### AX-2 - another thing

- **Where:** `gamma.js`
- **What bounds it:** nothing much.
- **Trigger - an EVENT WITH AN OWNER:** somebody notices. Nothing mechanical will announce it.
- **Open with:** unassigned.

### AX-3 - unrelated

- **Where:** `zulu.js`
- **What bounds it:** `never_referenced.js` is a real control, tested.
- **Trigger - MECHANICAL:** `tools/other.py`.
- **Open with:** Michael, 2026-01-01.

### AX-4 - a quiet orphan

- **Where:** `delta.js`
- **What bounds it:** nothing much either, though it also logs a `warnings` entry.
- **Trigger - an EVENT WITH AN OWNER:** somebody notices. Nothing mechanical will announce it.
- **Open with:** unassigned.

### AX-5 - a trigger that PRODUCES and nothing CONSUMES

- **Where:** `epsilon.js`
- **What bounds it:** nothing.
- **Trigger - MECHANICAL:** `tools/nobody_runs_this.py` emits it. Nothing mechanical reads it.
- **Open with:** Michael, 2026-01-01.
"""


def fixtures():
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '  <- ' + str(detail)[:220]))
        if not cond:
            bad += 1

    import tempfile
    d = tempfile.mkdtemp(prefix='weakcomb-fixture-')
    p = os.path.join(d, 'f.md')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(FIXTURE)
    try:
        ents = parse(p)
        ck('the register parses into one entry per ### heading',
           ents is not None and len(ents) == 5, ents and len(ents))
        by = {e['id']: e for e in ents}
        ck('a file in backticks is picked up as a mechanism',
           'alpha.js' in by['AX-1']['mechanisms'], by['AX-1']['mechanisms'])
        ck('CONTROL: an ordinary English word shared by two entries is NOT a '
           'mechanism -- "thing" appears in both titles and must not pair them',
           'thing' not in by['AX-1']['mechanisms'] + by['AX-2']['mechanisms'])
        ck('CONTROL: an ordinary word IN BACKTICKS is not a mechanism either. '
           '`warnings` appears in AX-1 and AX-4 and pairing them on it would '
           'be pairing on a common noun -- the real register says `warnings` '
           'in exactly this way',
           'warnings' not in by['AX-1']['mechanisms']
           and 'warnings' not in by['AX-4']['mechanisms'],
           (by['AX-1']['mechanisms'], by['AX-4']['mechanisms']))
        ck('the WHAT BOUNDS IT field is read separately from the whole entry, '
           'or "the thing that holds this up" cannot be told from "the thing '
           'this is about"',
           by['AX-1']['bound_mechanisms'] == ['gamma.js']
           and by['AX-1']['where_mechanisms'] == ['alpha.js'], by['AX-1'])
        ck('"that is a bound, not a control" is detected',
           by['AX-1']['bound_is_not_a_control'])
        ck('CONTROL: an entry with a real control is NOT flagged',
           not by['AX-3']['bound_is_not_a_control'])
        ck('a MECHANICAL trigger is detected', by['AX-1']['mechanical_trigger'])
        ck('CONTROL: "Nothing mechanical will announce it" is NOT read as a '
           'mechanical trigger -- the substring is present and the meaning is '
           'the opposite, which is exactly how an anchor stops testing anything',
           not by['AX-2']['mechanical_trigger'])
        ck('CONTROL: an entry whose trigger says MECHANICAL and then says '
           'nothing mechanical reads it is NOT mechanical. Both phrases are '
           'present and the second one is the truth',
           not by['AX-5']['mechanical_trigger'], by['AX-5'])
        ck('CONTROL: and that check is scoped to the TRIGGER field -- an entry '
           'saying "nothing mechanical" anywhere else keeps its real trigger',
           by['AX-1']['mechanical_trigger'])
        ck('an unassigned owner is detected', by['AX-2']['unowned'])
        ck('CONTROL: a named owner is not unowned', not by['AX-3']['unowned'])

        ps = {(p_['a'], p_['b']): p_ for p_ in pairs(ents)}
        ck('every unordered pair is returned, including the quiet ones -- an '
           'analysis that only emits hits cannot be checked for having looked',
           len(ps) == 10, sorted(ps))
        names = lambda k: [s[0] for s in ps[k]['signals']]
        ck('THE CITICORP ARM: A is accepted because gamma.js holds it and B is '
           'a recorded weakness in gamma.js -- BOUND NAMES THE OTHER',
           'BOUND NAMES THE OTHER' in names(('AX-1', 'AX-2')), names(('AX-1', 'AX-2')))
        ck('...and the signal names WHICH mechanism, so it can be checked',
           any('gamma.js' in why for k, why in ps[('AX-1', 'AX-2')]['signals']
               if k == 'BOUND NAMES THE OTHER'))
        ck('CONTROL: a bound naming a mechanism NO other entry is about does '
           'not fire. AX-3 is held up by never_referenced.js and that is not a '
           'combination, it is a dependency',
           all('BOUND NAMES THE OTHER' not in names(k) for k in ps
               if 'AX-3' in k), [k for k in ps if 'AX-3' in k and
                                 'BOUND NAMES THE OTHER' in names(k)])
        ck('two entries naming the same file trip SHARED MECHANISM',
           'SHARED MECHANISM' in names(('AX-1', 'AX-2')), names(('AX-1', 'AX-2')))
        ck('CONTROL: two entries in DIFFERENT files do not',
           'SHARED MECHANISM' not in names(('AX-1', 'AX-3')), names(('AX-1', 'AX-3')))
        ck('CONTROL: NEITHER ANNOUNCES needs BOTH triggers non-mechanical, not '
           'one -- one mechanical trigger is still somebody being told',
           'NEITHER ANNOUNCES' not in names(('AX-1', 'AX-2')), names(('AX-1', 'AX-2')))
        ck('two silent, unowned entries trip both attention signals',
           names(('AX-2', 'AX-4')) == ['NEITHER ANNOUNCES', 'BOTH UNOWNED'],
           names(('AX-2', 'AX-4')))
        ck('CONTROL: BOTH UNOWNED needs both, not one',
           'BOTH UNOWNED' not in names(('AX-2', 'AX-3')), names(('AX-2', 'AX-3')))
        ck('CONTROL: a pair of unrelated, owned, mechanically-triggered entries '
           'trips NOTHING AT ALL. A signal that fires on every pair is noise '
           'with a table, and the first version of this tool did exactly that '
           'on six pairs out of six', names(('AX-1', 'AX-3')) == [],
           names(('AX-1', 'AX-3')))
        ck('CONTROL: not every pair trips something -- if it did, the analysis '
           'would be a list of pairs',
           any(not ps[k]['signals'] for k in ps),
           {k: names(k) for k in ps})
        ck('an unreadable register returns None, never an empty list -- empty '
           'would report CLEAN', parse(os.path.join(d, 'nope.md')) is None)
        uw = {i: (m, w) for i, m, w in unwatched_triggers(ents, 'tools/thing.py runs here')}
        ck('a MECHANICAL trigger whose mechanism NOTHING runs is reported -- '
           'the register\'s own rule is that a trigger nobody watches is not '
           'one, and PRODUCING a signal is not CONSUMING it',
           'AX-3' in uw, uw)
        ck('CONTROL: a MECHANICAL trigger whose mechanism IS mentioned by a '
           'runner is NOT reported, so the check is about the wiring and not '
           'about the words', 'AX-1' not in uw, uw)
        ck('CONTROL: entries with no mechanical trigger are not reported as '
           'unwatched -- they never claimed to be watched',
           'AX-2' not in uw and 'AX-4' not in uw, uw)
        ck('CONTROL: unreadable runners give None, NOT an empty list. An empty '
           'list here would read as "every trigger is watched"',
           unwatched_triggers(ents, None) is None)
        g = os.path.join(d, 'g.md')
        io.open(g, 'w', encoding='utf-8', newline='\n').write('# x\nno entries\n')
        ck('a file with no entries section returns None too', parse(g) is None)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    return out, bad


def main(argv):
    if '--fixtures' in argv:
        lines, bad = fixtures()
        print('WEAKNESS COMBINATION -- blind lock, %d arms, no real register read'
              % len(lines))
        for l in lines:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad
                        else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    lines, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- the real register was not read.')
        for l in lines:
            print(l)
        return 2

    ents = parse()
    if ents is None:
        print('COULD NOT READ %s -- this is NOT a clean run.' % REGISTER)
        return 2
    ps = pairs(ents)
    hits = [p for p in ps if p['signals']]
    runners = runner_text()
    unwatched = unwatched_triggers(ents, runners)

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'entries': [e['id'] for e in ents],
                          'pairs': ps}, indent=2))
        return 1 if hits else 0

    print('WEAKNESS COMBINATION -- item 53, criteria %s' % CRITERIA_VERSION)
    print('  %d fixture arms passed before the register was read.' % len(lines))
    print('  %d accepted risk(s), %d pair(s) examined, %d with a shared property.'
          % (len(ents), len(ps), len(hits)))
    print('')
    print('  PER-ENTRY, because these are properties of ONE risk and belong')
    print('  here rather than smeared across every pair it appears in:')
    for e in ents:
        # ASCII only: stdout here is cp1252 and the register is full of
        # em-dashes. A tool that crashes on its own subject's punctuation is
        # the same class as tools/subprocess_decode_check.py's mojibake.
        t = e['title'].encode('ascii', 'replace').decode('ascii')
        marks = []
        if e['bound_is_not_a_control']:
            marks.append('BOUND IS NOT A CONTROL')
        if not e['mechanical_trigger']:
            marks.append('no mechanical trigger')
        if e['unowned']:
            marks.append('unowned')
        print('  %-6s %s' % (e['id'], t[:86]))
        if marks:
            print('         %s' % '; '.join(marks))
    print('')
    for p in ps:
        if not p['signals']:
            continue
        print('  %s x %s' % (p['a'], p['b']))
        for kind, why in p['signals']:
            print('    %-24s %s' % (kind, why))
        print('')
    if unwatched is None:
        print('  COULD NOT CHECK whether the mechanical triggers are watched --')
        print('  none of the runner files could be read. NOT a pass.')
        rc_unwatched = 2
    elif unwatched:
        rc_unwatched = 1
        print('  A TRIGGER NOBODY WATCHES IS NOT A TRIGGER -- this register\'s own')
        print('  rule, checked against it. A MECHANICAL trigger names something')
        print('  that PRODUCES a signal; that is not the same as anything')
        print('  CONSUMING it, and the entry cannot show the difference:')
        for ident, _m, why in unwatched:
            print('    %-6s %s' % (ident, why))
        print('')
    else:
        rc_unwatched = 0
        print('  Every MECHANICAL trigger names something that at least one')
        print('  runner mentions. That is necessary, not sufficient -- mentioned')
        print('  is not the same as acted on.')
        print('')

    print('  NONE OF THE ABOVE IS A FINDING. Each pair shares a property; whether')
    print('  it COMPOUNDS is a judgement about consequences and this tool does')
    print('  not make it. What the tool removes is the excuse that nobody looked')
    print('  at the two together.')
    print('')
    print('  AND THE RESIDUAL, WHICH IS THE REAL LIMIT: this can only pair risks')
    print('  SOMEBODY WROTE DOWN. %d entries is the whole register. The Citicorp'
          % len(ents))
    print('  combination was two decisions that were both on the record; a pair')
    print('  where one half was never recorded is invisible here, and a clean')
    print('  exit from this tool is not evidence against one.')
    return max(rc_unwatched, 1 if hits else 0)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
