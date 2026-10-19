#!/usr/bin/env python
r"""hover_deterministic_sink_scan.py -- a DETERMINISTIC, non-AI source-to-sink
scanner in the Semgrep / ESLint-security / gitleaks class, for two defect
shapes this role has already confirmed by hand on real code.

Built H1 b69 item 2(c). Own tool, own clone, nothing shared with H2.

-- WHY A NON-AI CHECKER, WITH THE REAL NUMBERS ---------------------------
Research pass this batch, sources cited in the batch report:

 * An empirical comparison of deterministic quality gates (pytest, strict
   typing, Semgrep SAST) against an LLM-as-judge found the LLM judge had a
   44% FALSE-NEGATIVE rate, attributed to "syntactic plausibility bias" --
   it assumed outer error handlers mitigated defects -- while the
   deterministic harness caught 25/25.
 * Semgrep's own standalone precision in a published empirical study was
   35.7%; LLM-only (GPT-4) reached 65.5%; the hybrid reached 89.5%.

So the two classes fail in OPPOSITE directions: the deterministic checker
is noisy (low precision, many false positives) but cannot be talked into
anything; the model is cleaner per-report but misses almost half of real
defects when a plausible-looking wrapper is present.

-- THE FAILURE MODE THIS ROLE MEASURED ITSELF, THIS BATCH -----------------
Not borrowed from the literature. b69's own negative controls (log #1610)
put three fabricated findings to a real LLM reviewer over its real API:
a line number beyond end of file, false content at a real line, and a
path that has never existed. It AGREED with all three, twice at HIGH
confidence, and for the nonexistent file it stated "The cited line directly
shows the implementation uses an in-memory plain object" -- describing a
line in a file that does not exist.

THAT IS THE PROPERTY THIS TOOL HAS AND THE MODEL CANNOT: every line it
reports was read off disk by this process. It cannot cite a file that is
absent, because it enumerates files rather than being told about them, and
it cannot cite a line past end of file, because it reports the index of a
line it actually iterated. Fabrication is not a failure mode available to
it. It has a different and worse one: it over-reports, and the 35.7%
figure above is the honest expectation for precision, not an aspiration.

-- THE TWO RULES, BOTH FROM CONFIRMED REAL FINDINGS ----------------------
Written because both shapes were already found by hand and are therefore
known to exist, which makes a measured recall against them meaningful:

 RULE raw-body-to-client (from finding #1606, 9 sites across 3 shapes):
   a variable assigned from `await <resp>.text()` or `await <resp>.json()`
   later reaching a `res.status(...).json(...)` payload. The defect is
   returning an upstream error body verbatim to the caller.

 RULE unescaped-filter-interpolation (from finding #1599):
   a PostgREST filter built by string concatenation where the interpolated
   expression is NOT wrapped in an encoder (encodeURIComponent/enc/esc).
   The defect is an attacker-controlled identifier reaching a query filter
   unescaped.

-- MEASURED ON THE REAL REPO, b69, FIRST RUN -- not projected ------------
186 non-test files under api/ enumerated and read.

 RULE unescaped-filter-interpolation: 14 hits. RECALL 4/4 against the sites
 confirmed by hand in finding #1599. PRECISION, by spot-reading the 10
 extras: roughly 4-5 of 14, about 29-36%, because most extras interpolate a
 value that is NOT attacker-controlled -- a server-computed sha256 hex
 digest (tokenHash at poll.js:63, register.js:47; submissionKey at
 public-complaint-submit.js:88), a Number()-coerced regex capture
 (clusterId at legal-citator.js:467), or an id read back from the database.
 A hex digest cannot carry the `&` the injection needs. ONE extra is worth
 real tracing rather than dismissing: agentId at stripe-webhook.js:177
 originates in a webhook payload, so its provenance is not obviously safe.

 RULE raw-body-to-client: 49 hits after the precision fix below (235
 before). RECALL 7/7 against the sites confirmed in finding #1606.
 PRECISION roughly 7 of 49, about 14%: the extras are overwhelmingly
 `res.status(200).json({ data: rows })` -- returning a parsed upstream body
 as the endpoint's INTENDED payload, which this rule cannot distinguish
 from leaking an upstream ERROR body. That distinction needs intent, not
 syntax, and is named here as the rule's ceiling rather than left implied.

THAT 29-36% LANDS ON TOP OF THE PUBLISHED 35.7% STANDALONE FIGURE FOR THIS
TOOL CLASS, measured independently on this platform's own code. The number
in the literature is not an excuse for this tool being noisy; it is the
expected operating point, and it is why every hit must be read before it
is filed and why nothing here files anything automatically.

-- WHAT THIS IS NOT, STATED PLAINLY --------------------------------------
NOT a parser and NOT taint analysis. It is line-oriented, scoped to a
window inside one function-ish block, and it has no notion of types,
aliasing, reassignment or control flow. It will miss a flow that crosses a
helper boundary (a real false negative) and will flag a variable that was
sanitised in a way it does not recognise (a real false positive). Both are
reported as counts rather than implied absent. It is a cheap, exhaustive
first pass whose value is that it reads EVERY file every time and never
invents one -- not a replacement for reading code.

Run:
  python hover_deterministic_sink_scan.py [--repo DIR] [--rule NAME] [--json]
  python hover_deterministic_sink_scan.py --selftest
"""

import argparse
import io
import json
import os
import re
import sys

EXIT_CLEAN = 0
EXIT_FOUND = 1
EXIT_COULD_NOT_RUN = 2

DEFAULT_REPO = os.path.join(os.path.expanduser('~'), 'Documents', 'SAIRN-hover')

# How far after an assignment the sink is still considered "the same flow".
# 60 lines is REASONED, not measured: the real #1606 sites put the text()
# read and the res.status() return 1-6 lines apart, so 60 is an order of
# magnitude of headroom while still refusing to link a read at the top of a
# 300-line handler to a response at the bottom. Widening it trades recall
# for precision in a tool already expected to sit near 35% precision.
FLOW_WINDOW_LINES = 60

ENCODERS = ('encodeURIComponent', 'encodeURI', 'enc(', 'esc(', 'escape(')

# `const bt = await r.text()` / `= await resp.json()`
_BODY_READ = re.compile(
    r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*await\s+[\w$.]+\.(?:text|json)\s*\(')
# a res.status(...).json(...) line
_RES_JSON = re.compile(r'\bres\s*\.\s*status\s*\([^)]*\)\s*\.\s*json\s*\(')
# a PostgREST-shaped filter being concatenated: ...=eq.' + expr
_FILTER_CONCAT = re.compile(
    r"""=(?:eq|neq|gt|gte|lt|lte|like|ilike|in|is)\.(?:'|")\s*\+\s*([^,;)]+)""")


class CouldNotRun(Exception):
    pass


def js_files(repo):
    """Every non-test .js under api/. Enumerated from disk -- this is the
    step that makes a fabricated path impossible: the tool is never told
    which files to look at."""
    base = os.path.join(repo, 'api')
    if not os.path.isdir(base):
        raise CouldNotRun('no api/ directory under %s' % repo)
    out = []
    for root, _dirs, names in os.walk(base):
        for n in sorted(names):
            if not n.endswith('.js') or n.endswith('.test.js'):
                continue
            out.append(os.path.join(root, n))
    if not out:
        raise CouldNotRun('no non-test .js files found under %s' % base)
    return sorted(out)


def _strip_line_comment(line):
    """Remove a trailing // comment, but not one inside a string literal.
    Deliberately simple and deliberately disclosed: a // inside a template
    literal spanning lines is not handled, and that is a known false-
    negative source rather than a solved problem."""
    out = []
    in_s = None
    i = 0
    while i < len(line):
        c = line[i]
        if in_s:
            if c == '\\':
                i += 2
                out.append('  ')
                continue
            if c == in_s:
                in_s = None
            out.append(c)
        else:
            if c in '"\'`':
                in_s = c
                out.append(c)
            elif c == '/' and i + 1 < len(line) and line[i + 1] == '/':
                break
            else:
                out.append(c)
        i += 1
    return ''.join(out)


def scan_raw_body_to_client(path, lines):
    """Findings for the #1606 shape. Each carries the REAL 1-based line
    number of the sink, read from enumeration rather than asserted."""
    found = []
    reads = []  # (var, lineno)
    for idx, raw in enumerate(lines, 1):
        code = _strip_line_comment(raw)
        m = _BODY_READ.search(code)
        if m:
            reads.append((m.group(1), idx))
        if not _RES_JSON.search(code):
            continue
        for var, rline in reads:
            if idx - rline < 0 or idx - rline > FLOW_WINDOW_LINES:
                continue
            # THE VARIABLE MUST BE IN A PAYLOAD VALUE POSITION, not merely
            # present on the line. MEASURED, not guessed: the first version
            # tested only `\bvar\b` anywhere on the res.status line and
            # returned 235 hits against 7 confirmed-true sites -- about 3%
            # precision, far below even the 35.7% this class of tool is
            # expected to manage, and unusable to file from. The reason was
            # visible in the output: it flagged the two lines ABOVE each real
            # site, which are the CORRECT remediation (test the body for a
            # known pattern, return a mapped message) and mention the
            # variable only inside a regex test. So the match now requires
            # the variable to sit in a `key: var` value position, and a line
            # that is a conditional test is excluded outright.
            if re.match(r'\s*(?:\}\s*)?(?:else\s+)?if\s*\(', code):
                continue
            if re.search(r':\s*%s\b' % re.escape(var), code):
                found.append({
                    'rule': 'raw-body-to-client',
                    'file': path, 'line': idx,
                    'trigger': ('a request whose upstream call fails, so the '
                                 'raw body read at line %d is returned to the '
                                 'caller' % rline),
                    'evidence': raw.strip()[:160],
                    'source_line': rline,
                    'variable': var,
                })
                break
    return found


def scan_unescaped_filter(path, lines):
    """Findings for the #1599 shape: a PostgREST filter concatenated with an
    expression that is not wrapped in a recognised encoder."""
    found = []
    for idx, raw in enumerate(lines, 1):
        code = _strip_line_comment(raw)
        for m in _FILTER_CONCAT.finditer(code):
            expr = m.group(1).strip()
            if any(e in expr for e in ENCODERS):
                continue
            # a bare string literal is not attacker-controlled
            if re.match(r'^[\'"`]', expr):
                continue
            found.append({
                'rule': 'unescaped-filter-interpolation',
                'file': path, 'line': idx,
                'trigger': ('a crafted value in %s reaching the query filter '
                             'unescaped (an embedded & can add a filter '
                             'parameter)' % expr[:40]),
                'evidence': raw.strip()[:160],
                'expression': expr[:80],
            })
    return found


RULES = {
    'raw-body-to-client': scan_raw_body_to_client,
    'unescaped-filter-interpolation': scan_unescaped_filter,
}


def scan(repo=DEFAULT_REPO, rule=None):
    paths = js_files(repo)
    chosen = RULES if rule is None else {rule: RULES[rule]}
    findings = []
    read = 0
    for p in paths:
        try:
            with io.open(p, encoding='utf-8', errors='replace') as f:
                lines = f.read().split('\n')
        except OSError as e:
            raise CouldNotRun('could not read %s: %s' % (p, e))
        read += 1
        rel = os.path.relpath(p, repo).replace('\\', '/')
        for fn in chosen.values():
            findings.extend(fn(rel, lines))
    return {'files_scanned': read, 'findings': findings,
            'rules': sorted(chosen), 'repo': repo}


def render(res):
    L = ['DETERMINISTIC SOURCE-TO-SINK SCAN (non-AI, Semgrep class)',
         '  %d file(s) under api/ enumerated from disk and read; rule(s): %s'
         % (res['files_scanned'], ', '.join(res['rules'])), '']
    by_rule = {}
    for f in res['findings']:
        by_rule.setdefault(f['rule'], []).append(f)
    for rule in sorted(by_rule):
        hits = by_rule[rule]
        L.append('RULE %s -- %d hit(s)' % (rule, len(hits)))
        for f in hits:
            L.append('  %s:%d' % (f['file'], f['line']))
            L.append('      %s' % f['evidence'])
            L.append('      trigger: %s' % f['trigger'])
        L.append('')
    if not res['findings']:
        L.append('No hit for any enabled rule. A measured zero over %d real '
                 'files, not a check that did not run.' % res['files_scanned'])
        L.append('')
    L.append('HOW THIS FAILS, and it is the opposite of how a model fails:')
    L.append('  * It CANNOT fabricate. Every path came from walking api/ and '
             'every line number is the index of a line this process read. '
             'b69 measured a real LLM reviewer agreeing at HIGH confidence '
             'with a finding about a file that does not exist (log #1610); '
             'that failure mode is unavailable here.')
    L.append('  * It over-reports instead. Published standalone precision for '
             'this class of tool is 35.7 percent, so expect false positives '
             'and read every hit before filing it. It has no types, no '
             'aliasing, no control flow, and a %d-line flow window.'
             % FLOW_WINDOW_LINES)
    L.append('  * It under-reports across helper boundaries. A flow that '
             'leaves the function is invisible to it -- a real false '
             'negative, counted as unknown rather than reported as absent.')
    return '\n'.join(L)


def _selftest():
    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    # ── RULE 1: raw body to client ───────────────────────────────────────
    pos = [
        "      const r = await fetch(rest('t'), { headers });",
        "      if (r.status === 400) {",
        "        const bt = await r.text();",
        "        res.status(400).json({ error: { message: 'rejected', detail: bt } });",
        "      }",
    ]
    hits = scan_raw_body_to_client('api/x.js', pos)
    ck('R1a the real #1606 shape is found, at the SINK line (4)',
       len(hits) == 1 and hits[0]['line'] == 4)
    ck('R1b the finding records the real SOURCE line too (3)',
       hits[0]['source_line'] == 3)

    neg_generic = [
        "        const bt = await r.text();",
        "        res.status(400).json({ error: { message: 'rejected' } });",
    ]
    ck('R1c KNOWN-BAD CONTROL: a response that does NOT include the body '
       'variable is not flagged -- this is the fix for the shape, and a '
       'checker that flagged it anyway would be useless after remediation',
       len(scan_raw_body_to_client('api/x.js', neg_generic)) == 0)

    far = ["        const bt = await r.text();"] + ['' for _ in range(80)] + \
          ["        res.status(400).json({ detail: bt });"]
    ck('R1d KNOWN-BAD CONTROL: a sink %d+ lines after the read is NOT linked '
       '-- the flow window is real, not decorative' % FLOW_WINDOW_LINES,
       len(scan_raw_body_to_client('api/x.js', far)) == 0)

    commented = [
        "        // const bt = await r.text();",
        "        // res.status(400).json({ detail: bt });",
    ]
    ck('R1e KNOWN-BAD CONTROL: a commented-out flow is not a finding',
       len(scan_raw_body_to_client('api/x.js', commented)) == 0)

    # R1f/R1g lock the PRECISION FIX measured on the real repo: the loose
    # first version returned 235 hits against 7 confirmed sites (~3%) by
    # flagging the correct remediation lines, which mention the body
    # variable only inside a pattern test.
    remediation = [
        "        const bt = await r.text();",
        "        if (/does not exist/i.test(bt)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'not set up' } }); return; }",
    ]
    ck('R1f KNOWN-BAD CONTROL: the CORRECT remediation -- test the body for '
       'a pattern, return a MAPPED message -- is not flagged, even though '
       'the body variable appears on the same line inside the test',
       len(scan_raw_body_to_client('api/x.js', remediation)) == 0)
    ck('R1g the real defect shape is still caught after that tightening '
       '(the fix must not have cost the true positive)',
       len(scan_raw_body_to_client('api/x.js', pos)) == 1)

    # ── RULE 2: unescaped filter interpolation ───────────────────────────
    bad_filter = ["  const r = await fetch(SUPABASE_URL + '/rest/v1/t?id=eq.' + agent_id + '&select=id');"]
    h2 = scan_unescaped_filter('api/y.js', bad_filter)
    ck('R2a the real #1599 shape is found at its real line',
       len(h2) == 1 and h2[0]['line'] == 1)

    good_filter = ["  const r = await fetch(rest('t?id=eq.' + encodeURIComponent(agent_id)));"]
    ck('R2b KNOWN-BAD CONTROL: an encodeURIComponent-wrapped value is NOT '
       'flagged -- again, the remediated form must come back clean',
       len(scan_unescaped_filter('api/y.js', good_filter)) == 0)
    ck('R2c an enc()-wrapped value (this platform\'s own helper name) is not '
       'flagged either',
       len(scan_unescaped_filter('api/y.js',
                                  ["fetch(rest('t?id=eq.' + enc(x)))"])) == 0)
    ck('R2d KNOWN-BAD CONTROL: a bare string literal is not attacker-'
       'controlled and is not flagged',
       len(scan_unescaped_filter('api/y.js',
                                  ["fetch(rest('t?app=eq.' + 'stonedesk'))"])) == 0)

    # ── the no-fabrication property, asserted directly ───────────────────
    ck('NF1 every finding\'s line number indexes a line that really exists '
       'in the input (the property an LLM reviewer provably lacks)',
       all(1 <= f['line'] <= len(pos) for f in hits))

    import tempfile
    import shutil
    tmp = tempfile.mkdtemp(prefix='hover_sink_fx_')
    try:
        raised = False
        try:
            js_files(tmp)
        except CouldNotRun:
            raised = True
        ck('CNR1 FAIL-CLOSED: a repo with no api/ directory raises '
           'CouldNotRun, never reports a clean scan of nothing', raised)

        os.makedirs(os.path.join(tmp, 'api'))
        raised2 = False
        try:
            js_files(tmp)
        except CouldNotRun:
            raised2 = True
        ck('CNR2 FAIL-CLOSED: an api/ directory with no .js files raises '
           'rather than reporting zero findings as clean', raised2)

        with io.open(os.path.join(tmp, 'api', 'a.js'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(pos))
        with io.open(os.path.join(tmp, 'api', 'a.test.js'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(pos))
        got = js_files(tmp)
        ck('F1 .test.js files are excluded from enumeration',
           len(got) == 1 and got[0].endswith('a.js'))
        r = scan(repo=tmp)
        ck('F2 scan() end-to-end finds the planted shape in a real file on '
           'disk and reports a relative path',
           len(r['findings']) == 1 and r['findings'][0]['file'] == 'api/a.js')
        ck('F3 render always states both failure directions, over- and '
           'under-reporting, rather than only the flattering one',
           'over-reports' in render(r) and 'under-reports' in render(r))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=DEFAULT_REPO)
    ap.add_argument('--rule', choices=sorted(RULES))
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)
    if args.selftest:
        return EXIT_CLEAN if _selftest() else 1
    try:
        res = scan(repo=args.repo, rule=args.rule)
    except CouldNotRun as e:
        print('COULD NOT RUN: %s' % e)
        return EXIT_COULD_NOT_RUN
    except KeyError as e:
        print('COULD NOT RUN: unknown rule %s' % e)
        return EXIT_COULD_NOT_RUN
    print(json.dumps(res, indent=1) if args.json else render(res))
    return EXIT_FOUND if res['findings'] else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
