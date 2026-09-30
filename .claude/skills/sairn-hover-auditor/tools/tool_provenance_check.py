#!/usr/bin/env python
"""tool_provenance_check.py -- before any hover tool's findings count as
confirmed, a DIFFERENT hover instance has to run it against a real
historical holdout set of already-confirmed findings and reproduce them.
Not synthetic fixtures, not the tool's own author, not same-session. This
tracks, per tool, whether that has ever actually happened.

Built 2026-09-23, direct instruction, after checking and finding the exact
gap twice. sabotage_closed_system_check.py was only ever run by the session
that wrote it, against fixtures that same session also wrote, in the same
sitting -- a tool grading its own homework with an answer key it also
authored. hover_tool_index.py shipped with ZERO self-check of any kind, not
even a synthetic one -- the weaker, more basic version of the same gap.

THE PRECEDENT, STATED RATHER THAN INVENTED. A third-party security auditor
is itself required to be independently audited before its own findings are
trusted -- an audit of the auditor, by someone who did not write the
original audit. An ML pipeline refuses to promote a new model until it
beats the CURRENT PRODUCTION BASELINE on a REAL HOLDOUT SET, never on "it
passed its own training-time tests" -- passing your own tests is necessary
and is not the bar. Both share the same shape this tool exists to enforce:
correctness claimed by the thing under test is not evidence: correctness
demonstrated against real, external, already-settled cases by someone else
is.

WHAT THIS TOOL DOES NOT DO, STATED PLAINLY SO NOBODY OVERTRUSTS IT. It
cannot perform the validation itself -- "does tool X correctly reproduce
historical finding Y" is a judgement call specific to what X checks, and
automating that away would just move the self-grading problem one layer
down. This is a TRACKER, not a validator: it records that a real event
happened (who, against what, whether it reproduced) and reports which
tracked tools have never had one recorded. The validation itself still has
to be done by an actual different session, by hand, against real cases.

REGISTRY IS GENERATED, NOT HAND-WRITTEN -- same discipline hover_tool_index
already uses and for the identical reason: scans the real .py files on
disk right now rather than trusting a list written about them once. A tool
deleted from disk drops off the registry; a new one picked up automatically
next run.

FAIL-CLOSED ON EVERY UNKNOWN, PR SS1.11's rule applied to this tool's own
--record path, not just read to other tools:
  - validator_session == author_session is REFUSED, not silently accepted
    with a note -- self-validation is not validation, the entire reason
    this tool exists.
  - an empty --holdout-refs is REFUSED -- a validation that cites nothing
    real to reproduce against did not happen.
  - a --holdout-refs entry that does not resolve to a real seq in
    hover-audit-log.jsonl is REFUSED -- catches a typo'd or invented
    citation before it is trusted forever in an append-only ledger.
  - --tool naming a file not currently present in this directory is
    REFUSED -- no phantom entries for tools that do not exist.

Run:
  python tool_provenance_check.py [--log PATH]
  python tool_provenance_check.py --record --tool NAME.py
      --validator-session S --author-session S --holdout-refs seq[,seq...]
      --reproduced true|false [--notes TEXT]
  python tool_provenance_check.py --selftest
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEDGER = os.path.join(HERE, 'tool_provenance_validations.jsonl')
DEFAULT_LOG = os.path.join(HERE, 'hover-audit-log.jsonl')

# This tool and the ledger/index files themselves are not tools that
# produce or verify findings -- nothing to hold to this standard.
SKIP = {'tool_provenance_check.py', 'hover_tool_index.py', 'hover_log.py',
        '__pycache__'}
SELFTEST_MARKERS = ('--selftest', '--self-test')


def discover_tools(here=HERE):
    """The real .py files on disk right now, same scan hover_tool_index.py
    already does, for the identical reason a hand-maintained list goes
    stale the moment a tool is added and nobody remembers to update it."""
    try:
        return sorted(f for f in os.listdir(here)
                       if f.endswith('.py') and f not in SKIP)
    except OSError as e:
        return None if str(e) else []


def has_own_selftest(path):
    """Best-effort, disclosed as exactly that: greps the tool's own source
    for a --selftest/--self-test flag string. A tool that does not even
    have this is the WEAKER, more basic gap hover_tool_index.py was --
    below the bar this tool exists to track, not the same bar."""
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            text = f.read()
    except OSError:
        return None
    return any(m in text for m in SELFTEST_MARKERS)


def load_jsonl(path):
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def check_tool_provenance(tools, validations, log_entries):
    """Pure function, the same shape every other hover_self_health.py
    check already uses: takes data in, returns a dict with FAIL_ flags,
    no I/O of its own so it can be driven by a selftest with fixtures."""
    real_seqs = {e['seq'] for e in log_entries if 'seq' in e}
    by_tool = {}
    for t in tools:
        by_tool[t] = {
            'has_own_selftest': None,
            'validations': [],
            'ever_validated': False,
            'ever_reproduced': False,
        }
    for v in validations:
        t = v.get('tool')
        if t not in by_tool:
            continue  # a validation for a tool no longer on disk -- ignored, not an error
        by_tool[t]['validations'].append(v)
        by_tool[t]['ever_validated'] = True
        if v.get('reproduced') is True:
            by_tool[t]['ever_reproduced'] = True

    # NEVER_VALIDATED IS ABOUT CONFIRMATION, NOT ATTEMPT COUNT: a tool with
    # one validation event that did NOT reproduce is not yet confirmed --
    # its findings still are not backed by an independent holdout pass, so
    # it belongs in this list exactly as much as a tool nobody has tried.
    # Folding "attempted, failed" into "validated" would be the identical
    # mistake bar_drift's own weak-language rate discipline exists to catch
    # elsewhere: a near-miss word is not the same as the real thing.
    never_validated = sorted(t for t, d in by_tool.items() if not d['ever_reproduced'])
    validated_not_reproduced = sorted(
        t for t, d in by_tool.items()
        if d['ever_validated'] and not d['ever_reproduced'])
    no_selftest_and_never_validated = sorted(
        t for t, d in by_tool.items()
        if not d['ever_reproduced'] and d.get('has_own_selftest') is False)

    return {
        'total_tools': len(tools),
        'by_tool': by_tool,
        'never_validated': never_validated,
        'validated_not_reproduced': validated_not_reproduced,
        'no_selftest_and_never_validated': no_selftest_and_never_validated,
        'real_seqs_known': len(real_seqs),
        'FAIL_any_never_validated': len(never_validated) > 0,
    }


def cmd_record(args):
    if args.validator_session == args.author_session:
        print('REFUSED: --validator-session and --author-session are the same '
              '(%r). Self-validation is not validation -- the entire reason '
              'this tool exists. Nothing was appended.' % args.validator_session)
        return 2
    if not args.holdout_refs:
        print('REFUSED: --holdout-refs is empty. A validation that cites no '
              'real prior case to reproduce against did not happen. Nothing '
              'was appended.')
        return 2
    try:
        refs = [int(x) for x in args.holdout_refs.split(',') if x.strip()]
    except ValueError:
        print('REFUSED: --holdout-refs must be comma-separated integers '
              '(hover-audit-log.jsonl seq numbers). Got %r. Nothing was '
              'appended.' % args.holdout_refs)
        return 2
    log_entries = load_jsonl(args.log)
    real_seqs = {e['seq'] for e in log_entries if 'seq' in e}
    unknown = [r for r in refs if r not in real_seqs]
    if unknown:
        print('REFUSED: --holdout-refs cites seq(s) %r that do not exist in '
              '%s. A citation to a case that is not real is worse than no '
              'citation -- it would look verified forever in an append-only '
              'ledger. Nothing was appended.' % (unknown, args.log))
        return 2
    tools = discover_tools()
    if tools is None:
        print('COULD NOT RUN: could not list tools in %s' % HERE)
        return 2
    if args.tool not in tools:
        print('REFUSED: %r is not a .py file currently present in %s. No '
              'phantom validation entries for tools that do not exist. '
              'Nothing was appended.' % (args.tool, HERE))
        return 2
    if args.reproduced not in ('true', 'false'):
        print('REFUSED: --reproduced must be exactly "true" or "false", not '
              'a guess in between. Got %r. Nothing was appended.'
              % args.reproduced)
        return 2
    event = {
        'tool': args.tool,
        'validator_session': args.validator_session,
        'author_session': args.author_session,
        'date': datetime.date.today().isoformat(),
        'holdout_description': args.holdout,
        'holdout_refs': refs,
        'reproduced': args.reproduced == 'true',
        'notes': args.notes or '',
    }
    with open(args.ledger, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, sort_keys=True) + '\n')
    print('RECORDED: %s validated by %s (author %s) against seq %r, '
          'reproduced=%s' % (args.tool, args.validator_session,
                              args.author_session, refs, event['reproduced']))
    return 0


def _selftest():
    failures = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    tools = ['sabotage_closed_system_check.py', 'hover_second_opinion.py',
             'hover_duplicate_finding_check.py']
    log_entries = [{'seq': 100, 'type': 'finding'}, {'seq': 101, 'type': 'finding'}]

    r = check_tool_provenance(tools, [], log_entries)
    check('zero validations ever -- all three tools flagged, none silently passed',
          r['FAIL_any_never_validated']
          and set(r['never_validated']) == set(tools))

    one_real_validation = [{
        'tool': 'sabotage_closed_system_check.py',
        'validator_session': 'hover2', 'author_session': 'hover',
        'holdout_refs': [100], 'reproduced': True,
    }]
    r = check_tool_provenance(tools, one_real_validation, log_entries)
    check('a real validation clears exactly that tool, not the others',
          'sabotage_closed_system_check.py' not in r['never_validated']
          and set(r['never_validated']) == {'hover_second_opinion.py',
                                             'hover_duplicate_finding_check.py'})

    validated_but_failed_repro = [{
        'tool': 'hover_second_opinion.py',
        'validator_session': 'hover2', 'author_session': 'hover',
        'holdout_refs': [101], 'reproduced': False,
    }]
    r = check_tool_provenance(tools, validated_but_failed_repro, log_entries)
    check('a validation attempt that did NOT reproduce is tracked separately, '
          'not folded into "validated" as though it were a pass',
          'hover_second_opinion.py' in r['validated_not_reproduced']
          and 'hover_second_opinion.py' in r['never_validated'])
    # NOTE: an attempted-but-failed reproduction still counts as
    # "never validated" for the FAIL gate -- a failed reproduction is not
    # a pass, and the tool's findings are not yet confirmed by it.

    stale_validation_for_deleted_tool = [{
        'tool': 'a_tool_that_no_longer_exists.py',
        'validator_session': 'hover2', 'author_session': 'hover',
        'holdout_refs': [100], 'reproduced': True,
    }]
    r = check_tool_provenance(tools, stale_validation_for_deleted_tool, log_entries)
    check('a validation event for a tool no longer on disk is ignored, '
          'not crashed on and not counted toward a tool that does not exist',
          set(r['by_tool'].keys()) == set(tools)
          and set(r['never_validated']) == set(tools))

    print()
    if failures:
        print('%d SELFTEST FAILURE(S): %s' % (len(failures), failures))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--record', action='store_true')
    ap.add_argument('--log', default=DEFAULT_LOG)
    ap.add_argument('--ledger', default=DEFAULT_LEDGER)
    ap.add_argument('--tool')
    ap.add_argument('--validator-session')
    ap.add_argument('--author-session')
    ap.add_argument('--holdout')
    ap.add_argument('--holdout-refs')
    ap.add_argument('--reproduced')
    ap.add_argument('--notes')
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.record:
        missing = [n for n in ('tool', 'validator_session', 'author_session',
                                'holdout', 'holdout_refs', 'reproduced')
                   if not getattr(args, n)]
        if missing:
            print('missing required --%s' % ', --'.join(m.replace('_', '-') for m in missing))
            return 2
        return cmd_record(args)

    tools = discover_tools()
    if tools is None:
        print('COULD NOT RUN: could not list tools in %s' % HERE)
        return 2
    if not tools:
        print('COULD NOT RUN -- no .py files found in %s. An empty registry '
              'is not the same as a checked-and-genuinely-empty one.' % HERE)
        return 2
    validations = load_jsonl(args.ledger)
    log_entries = load_jsonl(args.log)
    r = check_tool_provenance(tools, validations, log_entries)
    for t in tools:
        d = r['by_tool'][t]
        path = os.path.join(HERE, t)
        d['has_own_selftest'] = has_own_selftest(path)

    import freshness_stamp as _fs
    print(_fs.stamp())
    print('TOOL PROVENANCE -- %d tool(s) tracked, %d validation event(s) in %s'
          % (r['total_tools'], len(validations), args.ledger))
    print()
    for t in tools:
        d = r['by_tool'][t]
        if d['ever_reproduced']:
            status = 'INDEPENDENTLY VALIDATED (%d event(s))' % len(d['validations'])
        elif d['ever_validated']:
            status = 'ATTEMPTED, DID NOT REPRODUCE -- not confirmed'
        elif d['has_own_selftest']:
            status = 'never independently validated (has its own --selftest only)'
        else:
            status = 'NEVER VALIDATED, NO SELF-TEST EITHER'
        print('  %-42s %s' % (t, status))
    print()
    if r['FAIL_any_never_validated']:
        print('DUE: %d of %d tools have never had an independent holdout '
              'validation recorded. Not a synthetic fixture, not the '
              "author's own session -- a different hover instance, "
              'against real already-confirmed findings, reproducing them, '
              'then python tool_provenance_check.py --record ...'
              % (len(r['never_validated']), r['total_tools']))
        return 1
    print('OK: every tracked tool has at least one reproduced independent '
          'validation on record.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
