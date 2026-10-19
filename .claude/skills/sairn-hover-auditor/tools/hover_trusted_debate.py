#!/usr/bin/env python
"""hover_trusted_debate.py -- Trusted Debate: two independently-prompted
evaluators argue OPPOSITE verdicts on one finding before a synthesis step
decides, instead of one solo review (this role's own) standing unchallenged.

ONE-LINE CONCEPT (written before this code, per b62 methodology): spawn two
separately-prompted evaluators that must each argue a FIXED, opposite
verdict on the SAME evidence (FOR: the finding is valid; AGAINST: it is
not), citing only the real evidence given; show each side the other's
opening argument and require ONE concrete rebuttal attempt each; synthesize
CONFIRMED only if FOR's load-bearing citations survive AGAINST's rebuttal
attempt, never by averaging two solo opinions into a score.

WHY THIS IS NOT hover_second_opinion.py AGAIN. That tool already exists in
this directory and asks ONE independent model (Haiku, a different family
from this role's own) whether a CRITICAL finding's reasoning holds --
one read, one verdict, agree or disagree. This tool is structurally
different: it forces TWO evaluators into OPPOSED roles on purpose and
requires an actual rebuttal exchange before either verdict counts. A
finding that survives one skeptical read is not the same claim as a
finding that survives being directly attacked and defended against a
counter-argument that has seen it. The adversarial STRUCTURE is the new
safeguard here, not cross-model diversity (second_opinion already covers
that axis) -- consistent with this platform's own repeated lesson that a
second check built the SAME way as the first is not a second opinion.

BOTH SIDES USE THE SAME MODEL (claude-haiku-4-5, matching second_opinion's
own choice) ON PURPOSE for v1: the opposed SYSTEM PROMPTS are what make
this a debate, not a second same-direction read, and running two different
models would double cost and complexity without changing what rebuttal
actually tests. Named as a real design choice, not hidden.

SCOPE: AUDITOR-CLASS TOOLING ONLY. This debates whether one of THIS ROLE'S
OWN findings holds up -- it never judges app/platform logic directly, the
same boundary hover_second_opinion.py already keeps.

COORDINATION WITH H2: checked H2's own external-tooling directory before
writing this -- no existing debate/second-opinion/adversarial TOOL there
(two one-off adversarial-review markdown docs, not reusable code), so this
is new ground, not a duplicate under a different name.

FAILS CLOSED: a missing `anthropic` package, a missing API key, or any API
error raises CouldNotTell -- this tool has never returned CONFIRMED from a
debate it could not actually run, by construction (see run_fixtures()'s
fail-closed arm).

Run:
  python hover_trusted_debate.py --debate --seq 42 [--repo <path>]
  python hover_trusted_debate.py --selftest
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(os.path.expanduser('~'), '.claude', 'projects',
                         'C--Users-marsh-Documents-SAIRN-hover', 'hover-audit-log',
                         'hover-audit-log.jsonl')

MODEL = 'claude-haiku-4-5'

FOR_PROMPT = (
    "You are the FOR evaluator in a structured debate about one software-"
    "audit finding. You will be shown the finding's own written evidence. "
    "Your assigned role is to argue the finding IS VALID -- the cited "
    "evidence genuinely supports the stated conclusion. Build the "
    "strongest honest case you can FOR that position, citing specific "
    "pieces of the given evidence as your load-bearing points. Do not "
    "concede the opposite side exists yet; that comes in a later round. "
    "If the evidence truly cannot support a FOR case at all, say so "
    "plainly rather than inventing support -- your assigned role is an "
    "argument to construct, not license to fabricate."
)

AGAINST_PROMPT = (
    "You are the AGAINST evaluator in a structured debate about one "
    "software-audit finding. You will be shown the same written evidence "
    "the FOR evaluator sees. Your assigned role is to argue the finding "
    "is NOT VALID -- the cited evidence does not actually support the "
    "stated conclusion, or a real alternative explanation is being "
    "missed. Build the strongest honest case you can AGAINST, citing "
    "specific gaps or alternative readings. If the evidence truly leaves "
    "no honest case against it, say so plainly rather than inventing one."
)

REBUTTAL_PROMPT_TEMPLATE = (
    "You argued the {stance} side of this debate. You will now see the "
    "OPPOSING evaluator's opening argument. State whether your position "
    "still holds firm after reading it, and name any of YOUR OWN key "
    "citations that the opposing argument failed to address at all. Do "
    "not invent an unaddressed point that the opponent actually covered."
)

OPENING_TOOL = {
    'name': 'opening_argument',
    'description': 'Record your assigned-side opening argument for this debate.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'verdict': {'type': 'string', 'enum': ['valid', 'not_valid']},
            'confidence': {'type': 'string', 'enum': ['low', 'medium', 'high']},
            'key_citations': {
                'type': 'array', 'items': {'type': 'string'},
                'description': 'The specific evidence points your argument rests on.',
            },
            'reasoning': {'type': 'string'},
        },
        'required': ['verdict', 'confidence', 'key_citations', 'reasoning'],
        'additionalProperties': False,
    },
    'strict': True,
}

REBUTTAL_TOOL = {
    'name': 'rebuttal',
    'description': 'Record whether your position holds after seeing the opposing argument.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'holds_firm': {'type': 'boolean'},
            'unaddressed_points': {
                'type': 'array', 'items': {'type': 'string'},
                'description': 'Your OWN key citations the opponent did not address.',
            },
            'reasoning': {'type': 'string'},
        },
        'required': ['holds_firm', 'unaddressed_points', 'reasoning'],
        'additionalProperties': False,
    },
    'strict': True,
}


class CouldNotTell(Exception):
    pass


def _client(client=None, api_key=None):
    if client is not None:
        return client
    try:
        import anthropic
    except ImportError as e:
        raise CouldNotTell('the anthropic package is not installed: %s' % e)
    try:
        return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    except Exception as e:
        raise CouldNotTell('could not construct an Anthropic client (no API '
                            'key resolvable): %s' % e)


def _forced_call(client, system, tool, user_text):
    try:
        response = client.messages.create(
            model=MODEL, max_tokens=1024, system=system,
            tools=[tool], tool_choice={'type': 'tool', 'name': tool['name']},
            messages=[{'role': 'user', 'content': user_text}],
        )
    except Exception as e:
        raise CouldNotTell('Anthropic API call failed: %s: %s' % (type(e).__name__, e))
    for block in response.content:
        if getattr(block, 'type', None) == 'tool_use' and block.name == tool['name']:
            return dict(block.input)
    raise CouldNotTell('model did not return the forced tool call -- '
                        'stop_reason=%r' % getattr(response, 'stop_reason', None))


def opening(evidence_text, stance, client=None, api_key=None):
    c = _client(client, api_key)
    prompt = FOR_PROMPT if stance == 'for' else AGAINST_PROMPT
    return _forced_call(c, prompt, OPENING_TOOL, evidence_text)


def rebut(my_stance, my_opening, opponent_opening, client=None, api_key=None):
    c = _client(client, api_key)
    system = REBUTTAL_PROMPT_TEMPLATE.format(stance=my_stance.upper())
    user_text = (
        'YOUR OWN opening argument was:\n%s\n\n'
        'THE OPPOSING argument is:\n%s'
        % (json.dumps(my_opening), json.dumps(opponent_opening))
    )
    return _forced_call(c, system, REBUTTAL_TOOL, user_text)


def synthesize(for_open, against_open, for_rebuttal, against_rebuttal):
    """Pure function, no network -- the rule this tool exists to apply
    mechanically rather than leave to a third model's own vibe. Returns
    (verdict, why). verdict is one of CONFIRMED / REFUTED / INCONCLUSIVE.

    CONFIRMED: FOR holds firm AND names at least one of its own citations
      AGAINST's rebuttal failed to address -- the finding survived being
      directly attacked.
    REFUTED: FOR concedes (holds_firm=False), OR FOR holds firm but names
      zero unaddressed points (AGAINST's rebuttal covered everything FOR
      raised) AND AGAINST holds firm itself.
    INCONCLUSIVE: any other combination -- most commonly both sides hold
      firm and both claim the other left something unaddressed, which is
      a real disagreement this tool does not resolve by picking a side.
    """
    for_holds = bool(for_rebuttal.get('holds_firm'))
    against_holds = bool(against_rebuttal.get('holds_firm'))
    for_unaddressed = for_rebuttal.get('unaddressed_points') or []
    against_unaddressed = against_rebuttal.get('unaddressed_points') or []

    if not for_holds:
        return ('REFUTED', 'FOR conceded after seeing the AGAINST argument.')
    if for_holds and for_unaddressed and not against_unaddressed:
        return ('CONFIRMED', 'FOR held firm and named %d of its own citation(s) '
                'that AGAINST\'s rebuttal did not address; AGAINST raised no '
                'equivalent unaddressed point of its own.' % len(for_unaddressed))
    if for_holds and not for_unaddressed and against_holds:
        return ('REFUTED', 'FOR held firm but could not name any citation '
                'AGAINST left unaddressed, and AGAINST itself held firm -- '
                'the rebuttal covered what FOR raised.')
    return ('INCONCLUSIVE', 'Both sides held firm and both named an '
            'unaddressed point of their own (or neither did cleanly) -- a '
            'real disagreement this tool does not resolve by picking a side.')


def build_evidence_text(entry):
    lines = ['FINDING seq=%s, target=%s, severity=%s' % (
        entry.get('seq'), entry.get('target'), entry.get('severity'))]
    if entry.get('ref'):
        lines.append('cited evidence (files/commits/refs): %s' % entry['ref'])
    lines.append('')
    lines.append('SUMMARY (the finding as written):')
    lines.append(entry.get('summary') or '(no summary text)')
    return '\n'.join(lines)


def load_entry(seq, log_path=None):
    path = log_path or LOG_PATH
    if not os.path.isfile(path):
        raise CouldNotTell('self-log not found at %s' % path)
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e.get('seq') == seq:
                return e
    raise CouldNotTell('no entry with seq=%d in %s' % (seq, path))


def run_debate(seq, client=None, api_key=None, log_path=None):
    entry = load_entry(seq, log_path)
    evidence = build_evidence_text(entry)
    for_open = opening(evidence, 'for', client, api_key)
    against_open = opening(evidence, 'against', client, api_key)
    for_rebuttal = rebut('for', for_open, against_open, client, api_key)
    against_rebuttal = rebut('against', against_open, for_open, client, api_key)
    verdict, why = synthesize(for_open, against_open, for_rebuttal, against_rebuttal)
    return {
        'seq': seq, 'verdict': verdict, 'why': why,
        'for_open': for_open, 'against_open': against_open,
        'for_rebuttal': for_rebuttal, 'against_rebuttal': against_rebuttal,
    }


def log_result(result, log_path_override=None):
    etype = 'check' if result['verdict'] == 'CONFIRMED' else 'finding'
    summary = (
        'TRUSTED DEBATE on seq=%s: verdict=%s. %s FOR opened %s (conf %s); '
        'AGAINST opened %s (conf %s). FOR rebuttal holds_firm=%s, unaddressed=%r; '
        'AGAINST rebuttal holds_firm=%s, unaddressed=%r.' % (
            result['seq'], result['verdict'], result['why'],
            result['for_open'].get('verdict'), result['for_open'].get('confidence'),
            result['against_open'].get('verdict'), result['against_open'].get('confidence'),
            result['for_rebuttal'].get('holds_firm'), result['for_rebuttal'].get('unaddressed_points'),
            result['against_rebuttal'].get('holds_firm'), result['against_rebuttal'].get('unaddressed_points'),
        )
    )
    argv = [sys.executable, os.path.join(HERE, 'hover_log.py'), '--add',
            '--type', etype, '--target', 'self',
            '--ref', 'seq=%s' % result['seq'], '--summary', summary]
    if result['verdict'] != 'CONFIRMED':
        argv += ['--severity', 'medium']
    env = dict(os.environ)
    if log_path_override:
        env['HOVER_LOG_PATH_OVERRIDE'] = log_path_override
    r = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                        encoding='utf-8', env=env)
    return r.returncode, r.stdout, r.stderr


class _FakeBlock:
    def __init__(self, name, input_):
        self.type = 'tool_use'
        self.name = name
        self.input = input_


class _FakeResponse:
    def __init__(self, name, input_):
        self.content = [_FakeBlock(name, input_)]
        self.stop_reason = 'tool_use'


class _FakeClient:
    """Injectable stand-in matching the real SDK's shape, queue-driven so a
    fixture can script exactly what each of the four calls returns."""
    def __init__(self, queue):
        self.queue = list(queue)

    class _Messages:
        def __init__(self, outer):
            self.outer = outer

        def create(self, **kwargs):
            name, input_ = self.outer.queue.pop(0)
            return _FakeResponse(name, input_)

    @property
    def messages(self):
        return self._Messages(self)


def run_fixtures():
    ok = True

    def check(name, got, want):
        nonlocal ok
        passed = (got == want)
        ok = ok and passed
        print('  %s   %s  got=%r want=%r' % ('ok' if passed else 'FAIL', name, got, want))

    # 1. FOR survives, names an unaddressed point -> CONFIRMED
    v, why = synthesize(
        {'verdict': 'valid'}, {'verdict': 'not_valid'},
        {'holds_firm': True, 'unaddressed_points': ['cite A']},
        {'holds_firm': True, 'unaddressed_points': []},
    )
    check('FOR survives with an unaddressed point -> CONFIRMED', v, 'CONFIRMED')

    # 2. FOR concedes -> REFUTED
    v, why = synthesize(
        {}, {}, {'holds_firm': False, 'unaddressed_points': []}, {'holds_firm': True, 'unaddressed_points': []},
    )
    check('FOR concedes -> REFUTED', v, 'REFUTED')

    # 3. FOR holds firm but names nothing, AGAINST holds too -> REFUTED
    v, why = synthesize(
        {}, {}, {'holds_firm': True, 'unaddressed_points': []},
        {'holds_firm': True, 'unaddressed_points': []},
    )
    check('FOR holds firm with nothing unaddressed, AGAINST holds -> REFUTED', v, 'REFUTED')

    # 4. Both hold firm, both claim an unaddressed point -> INCONCLUSIVE
    v, why = synthesize(
        {}, {}, {'holds_firm': True, 'unaddressed_points': ['cite A']},
        {'holds_firm': True, 'unaddressed_points': ['cite B']},
    )
    check('both hold firm, both claim unaddressed -> INCONCLUSIVE', v, 'INCONCLUSIVE')

    # 5. KNOWN-BAD CONTROL: fail closed with no client and no anthropic
    #    reachable -- simulate by forcing the import to fail via a client
    #    that is never provided AND no package guarantee in this sandbox;
    #    test the explicit code path instead: _client(None) with a client
    #    object that raises on construction is covered by real ImportError
    #    in this environment already (anthropic is not always installed).
    #    Here we assert the CONTRACT directly: a CouldNotTell must be
    #    raised rather than any verdict dict ever being returned un-asked.
    raised = False
    try:
        _forced_call(_FakeClient([('wrong_tool_name', {})]), 'sys', OPENING_TOOL, 'x')
    except CouldNotTell:
        raised = True
    check('a response with the WRONG tool name raises CouldNotTell, never a verdict', raised, True)

    # 6. End-to-end with the fake client: full debate wiring produces the
    #    same verdict the pure synthesize() arm 1 produces, proving the
    #    plumbing (not just the rule) is correct.
    queue = [
        ('opening_argument', {'verdict': 'valid', 'confidence': 'high',
                               'key_citations': ['line 42'], 'reasoning': 'r1'}),
        ('opening_argument', {'verdict': 'not_valid', 'confidence': 'medium',
                               'key_citations': ['alt theory'], 'reasoning': 'r2'}),
        ('rebuttal', {'holds_firm': True, 'unaddressed_points': ['line 42'], 'reasoning': 'r3'}),
        ('rebuttal', {'holds_firm': True, 'unaddressed_points': [], 'reasoning': 'r4'}),
    ]
    fc = _FakeClient(queue)
    fo = opening('ev', 'for', client=fc)
    ao = opening('ev', 'against', client=fc)
    fr = rebut('for', fo, ao, client=fc)
    ar = rebut('against', ao, fo, client=fc)
    v, why = synthesize(fo, ao, fr, ar)
    check('end-to-end fake-client wiring reaches CONFIRMED via the real functions', v, 'CONFIRMED')

    print('%s -- %d/%d' % ('ALL OK' if ok else 'SOME FAILED', 6, 6))
    return ok


def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1
    if '--debate' in argv:
        if '--seq' not in argv:
            print('usage: hover_trusted_debate.py --debate --seq N [--repo PATH]')
            return 2
        seq = int(argv[argv.index('--seq') + 1])
        try:
            result = run_debate(seq)
        except CouldNotTell as e:
            print('COULD NOT RUN: %s' % e)
            return 2
        print('VERDICT: %s -- %s' % (result['verdict'], result['why']))
        rc, out, err = log_result(result)
        print(out.strip() or err.strip())
        return 0
    print('usage: hover_trusted_debate.py --debate --seq N | --selftest')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
