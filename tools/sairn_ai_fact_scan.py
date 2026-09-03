"""tools/sairn_ai_fact_scan.py -- find facts asserted to Claude that nothing derives.

WHY THIS EXISTS. Two independent findings a day apart, in two apps, same class:

  * StoneDesk [0039] (CC, 2026-09-02): the system prompt of EVERY AI call carried
    `'City: ' + (p.city || 'Westlake') + ', Ohio'` and `'Headcount: ' + (p.headcount || 1)`.
    A shop that had not filled in a city was described to the model as being in
    Westlake; a shop in Dallas that HAD filled one in was still stamped Ohio, and
    then asked for advice on pricing, labour and permitting for the wrong state.
  * SAIRNbiz get_payroll_anomalies (Cody, 2026-09-03): the tool description told
    Claude, as fact, "benefits cost is always $0 in this app", "no enrollment UI
    exists", "no payroll-run history is persisted anywhere". All three were true
    when written and false by the time they shipped.

Those are TWO DIFFERENT SHAPES and only one of them is a stale comment:

  SHAPE A -- a stale ASSERTION baked into a literal. Says the same wrong thing
             to every customer. Caught by reading the string.
  SHAPE B -- a fabricated FALLBACK inside an interpolation, `x || 'Westlake'`.
             Says something specific and false about THIS customer, looks live
             because there is a variable right next to it, and is invisible to
             any scan that treats "contains an interpolation" as "derived".

SHAPE B IS THE DANGEROUS ONE and it is the one a naive scanner misses. The first
version of this scan skipped any sentence containing `'+`, on the theory that an
interpolation meant the value was live. That theory would have missed CC's
finding entirely. The skip is gone; fallbacks are now the primary target.

WHAT IT DOES NOT DO. It cannot tell a legitimate default from a fabricated one:
`(role || 'user')` is fine and `(city || 'Westlake')` is not, and the difference
is semantic. It reports both and a human decides. It also only sees strings it
can recognise as AI-facing -- tool descriptions, schema descriptions, and
prompts assigned to a `system:` field or opening with "You are". A prompt
assembled somewhere it cannot see is invisible to it, which is a false-negative
direction and is stated here rather than discovered later.

PROVEN AGAINST BOTH REAL POSITIVES before being committed, because a checker
that has only ever returned clean is unproven rather than proven:

    python tools/sairn_ai_fact_scan.py --prove

replays the two commits above from git and asserts the scan flags what they
fixed. Run plain to scan the working tree.
"""
import re
import io
import os
import sys
import glob
import json
import subprocess

# ---------------------------------------------------------------------------
# Extraction: every string this file can identify as reaching a model.
# ---------------------------------------------------------------------------

def _line_of(src, pos):
    return src.count('\n', 0, pos) + 1


def ai_strings(src):
    """[{kind, name, line, start, end, text}] for each AI-facing literal.

    Ranges are returned as well as text because SHAPE B lives in the
    CONCATENATION around a literal, not inside it.
    """
    out = []

    for m in re.finditer(r"RegisterTool\(\s*\n?\s*'([^']+)'\s*,\s*\n?\s*('(?:[^'\\]|\\.)*')", src):
        out.append({'kind': 'tool_description', 'name': m.group(1),
                    'line': _line_of(src, m.start(2)), 'text': m.group(2)})

    for m in re.finditer(r"description:\s*('(?:[^'\\]|\\.)*')", src):
        out.append({'kind': 'schema_description', 'name': '',
                    'line': _line_of(src, m.start(1)), 'text': m.group(1)})

    for m in re.finditer(r"(['\"`])(You are (?:[^'\"`\\]|\\.){20,})\1", src, re.S):
        out.append({'kind': 'system_prompt', 'name': '',
                    'line': _line_of(src, m.start()), 'text': m.group(2)})

    return out


# A prompt is usually built by concatenation across many lines, so the literal
# extractor above cannot see the assembled whole. These capture the ASSEMBLY:
# any expression appending into a variable whose name says it is a prompt or
# context, plus anything handed to a `system:` field.
# Prompt building happens across many lines -- the real StoneDesk case was
#     profileBlock = '(header)' +
#       'City: ' + (p.city || 'Westlake') + ', Ohio(newline)' +
#       'Headcount: ' + (p.headcount || 1) + ' employees(newline)' + ...
# so the fallback usually sits on a CONTINUATION line that carries no assignment
# and no prompt-ish variable name at all. The first version of this scan looked
# at single lines and MISSED StoneDesk 0039 for exactly that reason -- the miss
# is why --prove exists. It now looks BACKWARDS from each fallback for the
# nearest marker that the surrounding code is assembling something a model will
# read: a builder function name, a prompt-ish variable, or a literal that opens
# a persona.
PROMPT_MARKER = re.compile(
    r"(?:function\s+\w*(?:[Pp]rompt|[Pp]ersona|[Ss]ystem|[Cc]ontext)\w*\s*\("
    r"|(?:ctx|sys|sysPrompt|systemPrompt|basePrompt|persona|profileBlock|memBlock"
    r"|baseBlock|promptBlock)\s*\+?="
    r"|system\s*:"
    r"|messages\s*:"
    r"|['\"`]You are )")
PROMPT_LOOKBACK = 40

# A line is part of a string-concatenation expression if it joins literals.
CONCAT = re.compile(r"\+\s*$|'\s*\+|\+\s*'|\"\s*\+|\+\s*\"")

# SHAPE B: a hardcoded fallback standing in for a real value.
#   (p.city || 'Westlake')      -> a place
#   (p.headcount || 1)          -> a count
#   (x.name || "Pinnacle")      -> a name
FALLBACK = re.compile(
    r"""\|\|\s*(?P<lit>'(?:[^'\\]|\\.){1,60}'|"(?:[^"\\]|\\.){1,60}"|\d+(?:\.\d+)?)""")

# PRECISION MATTERS MORE THAN RECALL HERE, and that is a deliberate trade.
# The first tightened-up run produced 58 hits of which about five were even
# AI-facing; the rest were badge classes, error strings and innerHTML defaults.
# A checker that over-reports ten to one gets ignored, and an ignored checker
# protects nothing -- the same conclusion the 2026-08-30 raw-HTML sweep reached
# about its own 1,192-hit method. Two exclusions do almost all the work:

# (1) A fallback that ANNOUNCES ITSELF as absent is the opposite of this bug.
#     "(name not recorded)", "no diagnosis on file", "unknown", "Error: ..." --
#     every one of those tells the model the value is missing, which is exactly
#     what 'Westlake' failed to do.
BENIGN_LITERAL = re.compile(
    r"^['\"]?\s*[\(\)\-\?\[\]\{\}]*\s*"
    r"(?:n/a|none|null|unknown|not\b|no\b|error\b|could not|cannot|can't|unable"
    r"|unavailable|failed|nothing|tbd|pending|empty|0['\"]?$|['\"]$)", re.I)

# (2) A line building markup is rendering to a screen, not talking to a model.
HTML_BUILD = re.compile(
    r"innerHTML|outerHTML|<div|<span|<td|<tr|<p|<b>|<strong|class=|style=|badge")

# SHAPE A: an assertion about what the app is or has.
ASSERTION = re.compile(
    r"\b(?:there (?:is|are) no|has no|have no|this app has no|no (?:[a-z_ -]{3,30}) (?:exists?|is persisted|is stored|is recorded)"
    r"|is always (?:\$?\d|zero|empty|null)|never (?:persisted|stored|recorded)|nothing is (?:persisted|stored|recorded)"
    r"|not (?:yet )?(?:built|implemented|wired|live|persisted))\b", re.I)


def scan_source(src, path):
    hits = []

    # --- SHAPE B: fabricated fallback inside AI-facing string assembly ----
    lines = src.split('\n')
    for i, line in enumerate(lines):
        fallbacks = [fm for fm in FALLBACK.finditer(line)
                     if not BENIGN_LITERAL.match(fm.group('lit').strip())]
        if not fallbacks:
            continue
        if not CONCAT.search(line):
            continue
        if HTML_BUILD.search(line):
            continue
        window = '\n'.join(lines[max(0, i - PROMPT_LOOKBACK):i + 1])
        mk = PROMPT_MARKER.search(window)
        if not mk:
            continue
        hits.append({
            'app': path, 'line': i + 1, 'shape': 'B',
            'why': 'hardcoded fallback stands in for a real value in AI-facing text',
            'evidence': line.strip()[:220]})

    for item in ai_strings(src):
        # --- SHAPE A ------------------------------------------------------
        for am in ASSERTION.finditer(item['text']):
            start = max(0, am.start() - 90)
            hits.append({
                'app': path, 'line': item['line'], 'shape': 'A',
                'why': 'asserts app state as fact in a ' + item['kind'] +
                       (' (' + item['name'] + ')' if item['name'] else ''),
                'evidence': item['text'][start:am.end() + 90].strip()[:220]})

    # de-duplicate identical (line, shape, evidence)
    seen, uniq = set(), []
    for h in hits:
        k = (h['app'], h['line'], h['shape'], h['evidence'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(h)
    return uniq


def scan_paths(paths):
    out = []
    for p in paths:
        src = io.open(p, encoding='utf-8', errors='replace').read()
        out.extend(scan_source(src, p))
    return out


# ---------------------------------------------------------------------------
# Proof: replay the two real positives out of git.
# ---------------------------------------------------------------------------

def _show(rev, path):
    r = subprocess.run(['git', 'show', rev + ':' + path],
                       capture_output=True)
    if r.returncode:
        return None
    return r.stdout.decode('utf-8', 'replace')


def prove():
    """Both known true positives must be caught, and both fixes must be clean."""
    cases = [
        # (label, bad-rev, good-rev, path, shape, must appear in evidence)
        ('StoneDesk 0039 fabricated city/headcount fallbacks',
         '34f8085^', '34f8085', 'stonedesk.html', 'B', 'Westlake'),
        ('SAIRNbiz payroll-anomalies stale assertions',
         'c4ea4e9^', 'c4ea4e9', 'sairnbiz.html', 'A', 'no payroll-run history'),
    ]
    ok = True
    for label, bad, good, path, shape, needle in cases:
        src_bad = _show(bad, path)
        if src_bad is None:
            print('  SKIP  %s -- %s:%s not reachable from this clone' % (label, bad, path))
            continue
        hits = [h for h in scan_source(src_bad, path)
                if h['shape'] == shape and needle.lower() in h['evidence'].lower()]
        if hits:
            print('  ok    CAUGHT  %s (line %d)' % (label, hits[0]['line']))
        else:
            print('  FAIL  MISSED  %s -- the scan does not detect a defect it is meant to' % label)
            ok = False

        src_good = _show(good, path)
        if src_good is not None:
            still = [h for h in scan_source(src_good, path)
                     if h['shape'] == shape and needle.lower() in h['evidence'].lower()]
            if still:
                print('  FAIL  the fixed revision still flags %s -- fix or scan is wrong' % label)
                ok = False
            else:
                print('  ok    CLEAN   %s after its fix' % label)
    return ok


def _safe_print(x):
    """Windows consoles are cp1252 and these files carry em-dashes and glyphs.
    A scanner that crashes on its own output is worse than one that transliterates."""
    try:
        print(x)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, 'encoding', None) or 'ascii'
        print(x.encode(enc, 'replace').decode(enc, 'replace'))


def main():
    if '--prove' in sys.argv:
        print('Proving the scan against both known real positives:')
        sys.exit(0 if prove() else 1)

    paths = [a for a in sys.argv[1:] if not a.startswith('-')] or sorted(glob.glob('*.html'))
    hits = scan_paths(paths)
    if '--json' in sys.argv:
        print(json.dumps(hits, indent=1))
        return
    if not hits:
        print('No AI-facing fabricated fallbacks or stale state assertions found in %d file(s).'
              % len(paths))
        print('NOTE: this is "none found by these two shapes", not "none exist" -- a prompt')
        print('assembled where this scan cannot see it is invisible to it.')
        return
    by_shape = {}
    for h in hits:
        by_shape.setdefault(h['shape'], []).append(h)
    for shape in sorted(by_shape):
        print('--- SHAPE %s: %d hit(s) ---' % (shape, len(by_shape[shape])))
        for h in by_shape[shape]:
            _safe_print('%s:%d  %s' % (h['app'], h['line'], h['why']))
            _safe_print('    ' + h['evidence'])
    print('\n%d hit(s). Every one is a candidate to READ, not a confirmed defect:' % len(hits))
    print('a legitimate default (role || \'user\') and a fabricated one (city || \'Westlake\')')
    print('are the same shape and only a human can tell them apart.')


if __name__ == '__main__':
    main()
