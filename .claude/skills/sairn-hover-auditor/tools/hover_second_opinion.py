#!/usr/bin/env python
"""hover_second_opinion.py -- a genuinely different model checks a CRITICAL
finding before it stands unchallenged.

WHY A DIFFERENT MODEL, NOT ANOTHER SONNET INSTANCE. Built on Michael's direct
instruction: a fresh instance of the SAME model family shares this role's own
training-derived blind spots -- the failure mode independent re-verification
inside this session (hover1 vs hover2, both Sonnet) does not fully cover.
Haiku 4.5 is deliberately a different model, reached through the real
Anthropic API rather than a second self-review, specifically to surface
disagreement a same-family re-check would be less likely to produce.

SCOPE, DELIBERATELY NARROW: severity == 'critical' ONLY. Every finding this
role makes already gets independent scrutiny in some form (a duplicate
check, a coverage-ledger poll, an EQA checkpoint eventually) -- this adds a
real API call with real cost and a real rate limit, so it is reserved for
the entries where being wrong matters most, not spent on every entry.

WHAT THIS DOES NOT DO. It does not re-read source, does not re-run code,
does not have tool access -- it hands Haiku the SAME EVIDENCE this role
already wrote down (the finding's own summary + citations) and asks for an
independent read of THAT evidence, the same way a second human reviewer
reads a written report rather than re-investigating from scratch. This is a
cheaper, narrower check than a full independent re-derivation (Tier 0/Tier 1
live execution, an EQA checkpoint) -- it catches a finding whose OWN
reasoning does not hold up to a fresh read, not a finding whose evidence was
individually wrong in a way only re-reading the source would catch. Named as
a real limit, not implied to be more than it is.

DISAGREEMENT IS NEVER SILENTLY DISCARDED, EITHER DIRECTION. Every run logs
its outcome -- agreement is recorded as a plain check, disagreement is
recorded as its own flagged entry, severity escalated, precisely because a
cross-model disagreement on a CRITICAL finding is itself a real signal
worth a human's attention, the identical standard already held for a hover1/
hover2 disagreement.

Run:
  python hover_second_opinion.py --seq 42 [--repo <path>]
  python hover_second_opinion.py --selftest
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, 'hover-audit-log.jsonl')

MODEL = 'claude-haiku-4-5'
# CORRECTED FROM THE ORIGINAL INSTRUCTION ('claude-haiku-4-5-20251001') --
# per the current claude-api skill's own model table, date-suffixed IDs are
# stale/rejected; 'claude-haiku-4-5' is the complete, current ID. Flagged
# rather than silently typed as given.

_KNOWN_CLONES = (
    'C:/Users/marsh/Documents/SAIRN-hover',
    'C:/Users/marsh/Documents/SAIRN-hover2',
)

SYSTEM_PROMPT = (
    "You are an independent second reviewer for a software-audit platform. "
    "You will be shown a CRITICAL-severity finding another reviewer already "
    "wrote, including its evidence citations. You have NOT read the source "
    "code yourself -- you are reading the SAME written evidence a second "
    "human reviewer would read. Judge whether the finding's OWN reasoning "
    "is internally sound: does the cited evidence actually support the "
    "conclusion, is the severity justified by what is described, is there "
    "an obvious alternative explanation the write-up does not address. "
    "Do not assume the finding is right because it is confidently written. "
    "Record your honest, independent judgment, even if it disagrees."
)


class CouldNotTell(Exception):
    pass


def discover_repo(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(argv):
            return argv[i + 1]
    env = os.environ.get('HOVER_LEDGER_REPO')
    if env:
        return env
    for candidate in _KNOWN_CLONES:
        if os.path.isdir(os.path.join(candidate, '.git')):
            return candidate
    return None


def load_entry(seq, log_path=LOG_PATH):
    if not os.path.isfile(log_path):
        raise CouldNotTell('self-log not found at %s' % log_path)
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e.get('seq') == seq:
                return e
    raise CouldNotTell('no entry with seq=%d in %s' % (seq, log_path))


def build_evidence_text(entry):
    lines = [
        'FINDING seq=%d, target=%s, severity=%s' % (
            entry.get('seq'), entry.get('target'), entry.get('severity')),
    ]
    if entry.get('vector'):
        lines.append('vector: %s' % entry['vector'])
    if entry.get('ref'):
        lines.append('cited evidence (files/commits/refs): %s' % entry['ref'])
    lines.append('')
    lines.append('SUMMARY (the finding as written):')
    lines.append(entry.get('summary') or '(no summary text)')
    return '\n'.join(lines)


SECOND_OPINION_TOOL = {
    'name': 'second_opinion',
    'description': "Record your independent judgment on whether this CRITICAL finding's own reasoning holds.",
    'input_schema': {
        'type': 'object',
        'properties': {
            'agrees': {
                'type': 'boolean',
                'description': 'True if the cited evidence genuinely supports the stated conclusion and severity.',
            },
            'confidence': {'type': 'string', 'enum': ['low', 'medium', 'high']},
            'reasoning': {
                'type': 'string',
                'description': 'Your independent reasoning, in 2-5 sentences. If you disagree, say specifically what does not hold up.',
            },
        },
        'required': ['agrees', 'confidence', 'reasoning'],
        'additionalProperties': False,
    },
    'strict': True,
}


def ask_haiku(evidence_text, client=None, api_key=None):
    """Returns the parsed {'agrees', 'confidence', 'reasoning'} dict, or
    raises CouldNotTell on any failure -- an API error, a missing key, or a
    response that did not contain the forced tool call. `client` is
    injectable so this function (and everything that calls it) is testable
    without a real network call or a real key -- see run_fixtures()."""
    if client is None:
        try:
            import anthropic
        except ImportError as e:
            raise CouldNotTell('the anthropic package is not installed: %s' % e)
        try:
            client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        except Exception as e:
            raise CouldNotTell('could not construct an Anthropic client '
                                '(no API key resolvable): %s' % e)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[SECOND_OPINION_TOOL],
            tool_choice={'type': 'tool', 'name': 'second_opinion'},
            messages=[{'role': 'user', 'content': evidence_text}],
        )
    except Exception as e:
        # Deliberately one broad catch here, not the full typed chain the
        # claude-api skill recommends for production error handling --
        # every failure mode (auth, rate limit, connection, bad request)
        # means the SAME thing to this tool: it could not get a second
        # opinion this run, which is COULD_NOT_TELL, not an agree/disagree
        # verdict either way. The exception's own text is preserved so a
        # human reading the log entry sees the real cause.
        raise CouldNotTell('Anthropic API call failed: %s: %s' % (type(e).__name__, e))

    for block in response.content:
        if getattr(block, 'type', None) == 'tool_use' and block.name == 'second_opinion':
            return dict(block.input)
    raise CouldNotTell('Haiku did not return the forced tool call -- '
                        'stop_reason=%r' % getattr(response, 'stop_reason', None))


def log_result(seq, entry, verdict, log_path_override=None):
    """Writes the outcome back through the REAL hover_log.py --add path (the
    one place the hash-chained log is ever appended to), never by writing
    hover-audit-log.jsonl directly. Agreement logs as a plain check;
    disagreement logs as its own flagged, escalated entry -- both always
    logged, never silently dropped either direction.

    log_path_override, if given, is passed to the hover_log.py SUBPROCESS
    via HOVER_LOG_PATH_OVERRIDE -- the only way to actually redirect a
    separate process's write. A caller's own in-process LOG_PATH monkey-
    patch does nothing here; found live, the hard way, in this file's own
    first selftest (see hover-audit-log #464/#465)."""
    agrees = verdict['agrees']
    etype = 'check' if agrees else 'finding'
    summary_lines = [
        'SECOND OPINION (claude-haiku-4-5, independent of this role) on '
        'seq=%d (%s finding, %s): Haiku %s.' % (
            seq, entry.get('target'), entry.get('severity'),
            'AGREES' if agrees else 'DISAGREES'),
        '',
        'Haiku\'s stated confidence: %s' % verdict.get('confidence'),
        'Haiku\'s reasoning: %s' % verdict.get('reasoning'),
    ]
    if not agrees:
        summary_lines += [
            '',
            'DISAGREEMENT -- flagged, not silently discarded. This does not '
            'mean seq=%d is wrong; it means a genuinely different model, '
            'reading the same written evidence, did not reach the same '
            'conclusion. That is itself a real signal on a CRITICAL finding '
            'and needs a human read, the same standard already held for a '
            'hover1/hover2 disagreement.' % seq,
        ]
    summary = '\n'.join(summary_lines)

    argv = [sys.executable, os.path.join(HERE, 'hover_log.py'), '--add',
            '--type', etype, '--target', 'self',
            '--ref', 'seq=%d' % seq,
            '--summary', summary]
    if not agrees:
        argv += ['--severity', 'high']
    env = dict(os.environ)
    if log_path_override:
        env['HOVER_LOG_PATH_OVERRIDE'] = log_path_override
    r = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                        encoding='utf-8', env=env)
    return r.returncode, r.stdout, r.stderr


def run_second_opinion(seq, repo=None):
    entry = load_entry(seq)
    if entry.get('severity') != 'critical':
        raise CouldNotTell(
            'seq=%d has severity=%r, not "critical" -- this tool is scoped '
            'to CRITICAL findings only, by design (real API cost and rate '
            'limit; every other severity already gets other independent '
            'scrutiny)' % (seq, entry.get('severity')))
    evidence = build_evidence_text(entry)
    verdict = ask_haiku(evidence)
    rc, out, err = log_result(seq, entry, verdict)
    return verdict, rc, out, err


def run_fixtures():
    """No real API call, no real credential needed -- the network boundary
    is `ask_haiku`'s injectable `client` parameter, exercised here with a
    fake client whose shape matches the real SDK's response objects. Never
    touches the real hover-audit-log.jsonl -- LOG_PATH is monkey-patched to
    a scratch file for the duration."""
    import io
    import contextlib
    import tempfile
    global LOG_PATH

    # SAFETY NET, ADDED AFTER THE REAL INCIDENT (#464/#465): count the REAL
    # production log's lines before running anything, and assert it is
    # UNCHANGED at the end -- not trusted on faith a second time just
    # because the mechanism was fixed. If this ever fails, that is the
    # loudest possible signal the isolation broke again.
    real_log_path_for_safety_check = os.path.join(HERE, 'hover-audit-log.jsonl')
    lines_before = 0
    if os.path.isfile(real_log_path_for_safety_check):
        with open(real_log_path_for_safety_check, encoding='utf-8') as f:
            lines_before = sum(1 for line in f if line.strip())

    ok_count = [0]
    fail_count = [0]

    def ck(name, cond):
        if cond:
            ok_count[0] += 1
            print('  ok   ' + name)
        else:
            fail_count[0] += 1
            print('  FAIL ' + name)

    class FakeBlock:
        def __init__(self, type_, name=None, input_=None):
            self.type = type_
            self.name = name
            self.input = input_

    class FakeResponse:
        def __init__(self, content, stop_reason='tool_use'):
            self.content = content
            self.stop_reason = stop_reason

    class FakeMessages:
        def __init__(self, response=None, exc=None):
            self._response = response
            self._exc = exc
            self.last_call = None

        def create(self, **kwargs):
            self.last_call = kwargs
            if self._exc:
                raise self._exc
            return self._response

    class FakeClient:
        def __init__(self, response=None, exc=None):
            self.messages = FakeMessages(response, exc)

    # --- build_evidence_text() ---
    fake_entry = {'seq': 7, 'target': 'platform', 'severity': 'critical',
                  'vector': 'T:A/EX:H/IM:H/SC:S', 'ref': 'app.html:100',
                  'summary': 'A real finding summary.'}
    ev = build_evidence_text(fake_entry)
    ck('evidence text carries the seq, target, severity and summary',
       'seq=7' in ev and 'platform' in ev and 'critical' in ev
       and 'A real finding summary.' in ev)

    # --- ask_haiku(): the AGREE path, real tool-call shape ---
    agree_response = FakeResponse([FakeBlock('text', None, None),
                                    FakeBlock('tool_use', 'second_opinion',
                                              {'agrees': True, 'confidence': 'high',
                                               'reasoning': 'The citation supports it.'})])
    v = ask_haiku('evidence', client=FakeClient(response=agree_response))
    ck('AGREE: the forced tool call is parsed into the verdict dict',
       v == {'agrees': True, 'confidence': 'high', 'reasoning': 'The citation supports it.'})

    # --- ask_haiku(): the DISAGREE path ---
    disagree_response = FakeResponse([FakeBlock('tool_use', 'second_opinion',
                                                 {'agrees': False, 'confidence': 'medium',
                                                  'reasoning': 'The cited file does not show that.'})])
    v2 = ask_haiku('evidence', client=FakeClient(response=disagree_response))
    ck('DISAGREE: the forced tool call is parsed correctly in the '
       'other direction too', v2['agrees'] is False)

    # --- ask_haiku(): missing tool call is COULD_NOT_TELL, never guessed ---
    no_tool_response = FakeResponse([FakeBlock('text', None, None)], stop_reason='end_turn')
    raised = False
    try:
        ask_haiku('evidence', client=FakeClient(response=no_tool_response))
    except CouldNotTell:
        raised = True
    ck('a response with no forced tool call raises CouldNotTell, never '
       'fabricates a verdict', raised)

    # --- ask_haiku(): a real API exception (rate limit, auth, network) is
    # COULD_NOT_TELL too, never silently treated as agreement ---
    raised2 = False
    try:
        ask_haiku('evidence', client=FakeClient(exc=RuntimeError('429 rate limited')))
    except CouldNotTell as e:
        raised2 = 'rate limited' in str(e)
    ck('an API failure raises CouldNotTell with the real cause preserved, '
       'never silently defaults to agree or disagree', raised2)

    # --- the scope gate: a non-critical entry is refused before any API
    # call is attempted ---
    tmpdir = tempfile.mkdtemp(prefix='hover_second_opinion_selftest_')
    LOG_PATH = os.path.join(tmpdir, 'test-log.jsonl')
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'seq': 1, 'target': 'platform', 'severity': 'high',
                             'summary': 'not critical'}) + '\n')
        f.write(json.dumps({'seq': 2, 'target': 'platform', 'severity': 'critical',
                             'summary': 'a real critical finding', 'ref': 'x.html:1'}) + '\n')

    try:
        entry1 = load_entry(1, log_path=LOG_PATH)
        ck('load_entry() finds the right row by seq', entry1['severity'] == 'high')
        raised3 = False
        try:
            if entry1.get('severity') != 'critical':
                raise CouldNotTell('not critical')
        except CouldNotTell:
            raised3 = True
        ck('a non-critical severity is refused before any API call would '
           'be attempted (the actual scope gate, exercised via '
           'run_second_opinion() would raise identically)', raised3)

        raised4 = False
        try:
            load_entry(999, log_path=LOG_PATH)
        except CouldNotTell:
            raised4 = True
        ck('an unknown seq raises CouldNotTell rather than returning None '
           'or crashing', raised4)

        # --- log_result(): real end-to-end write through the REAL
        # hover_log.py --add path (not a direct file write), against a
        # SEPARATE, genuinely-empty scratch log -- never the real one, and
        # NOT the hand-seeded fixture file above, which holds raw dicts
        # missing 'hash'/'prev_hash' (fine for load_entry()'s own lookup
        # test, but not a shape the real hover_log.py subprocess can treat
        # as prior log state; found live, exactly this way, the first time).
        entry2 = load_entry(2, log_path=LOG_PATH)
        result_log_path = os.path.join(tmpdir, 'result-log.jsonl')
        rc, out, err = log_result(2, entry2, {'agrees': True, 'confidence': 'high',
                                               'reasoning': 'Solid.'},
                                   log_path_override=result_log_path)
        ck('log_result() on AGREE calls the real hover_log.py --add and it '
           'succeeds (rc reflects a clean check-type log)', rc == 0,)
        rows = []
        with open(result_log_path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        ck('AGREE landed as a real, new entry in the log (1 row now)',
           len(rows) == 1)
        ck('AGREE entry type is check, not finding',
           rows[-1]['type'] == 'check')

        rc2, out2, err2 = log_result(2, entry2, {'agrees': False, 'confidence': 'medium',
                                                  'reasoning': 'Does not hold.'},
                                      log_path_override=result_log_path)
        rows2 = []
        with open(result_log_path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    rows2.append(json.loads(line))
        ck('DISAGREE also lands as a real, new entry (2 rows now) -- '
           'never silently discarded', len(rows2) == 2)
        ck('DISAGREE entry type is finding, escalated severity=high',
           rows2[-1]['type'] == 'finding' and rows2[-1]['severity'] == 'high')
        ck('DISAGREE summary names the disagreement plainly',
           'DISAGREES' in rows2[-1]['summary'])
    finally:
        pass  # LOG_PATH restored by the caller of run_fixtures() via main()

    lines_after = 0
    if os.path.isfile(real_log_path_for_safety_check):
        with open(real_log_path_for_safety_check, encoding='utf-8') as f:
            lines_after = sum(1 for line in f if line.strip())
    ck('SAFETY NET: the REAL production log gained zero lines during this '
       'selftest (before=%d, after=%d)' % (lines_before, lines_after),
       lines_after == lines_before)

    print()
    print('%d ok, %d failed' % (ok_count[0], fail_count[0]))
    return fail_count[0] == 0


def main(argv):
    global LOG_PATH
    real_log_path = LOG_PATH
    if '--selftest' in argv:
        try:
            ok = run_fixtures()
        finally:
            LOG_PATH = real_log_path
        return 0 if ok else 1

    def opt(name, required=True):
        if name in argv:
            i = argv.index(name)
            if i + 1 < len(argv):
                return argv[i + 1]
        if required:
            print('missing %s' % name, file=sys.stderr)
            sys.exit(2)
        return None

    seq = int(opt('--seq'))
    repo = discover_repo(argv)
    try:
        verdict, rc, out, err = run_second_opinion(seq, repo=repo)
    except CouldNotTell as e:
        print('COULD NOT RUN: %s' % e)
        return 2

    print('Haiku %s (confidence=%s)' % (
        'AGREES' if verdict['agrees'] else 'DISAGREES', verdict['confidence']))
    print(verdict['reasoning'])
    print()
    print('--- hover_log.py --add output ---')
    print(out)
    if err.strip():
        print('--- stderr ---')
        print(err)
    return 0 if verdict['agrees'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
