#!/usr/bin/env python
"""Which coding/billing rules exist, and which has nobody registered?

    python tools/coding_rule_discovery.py
    python tools/coding_rule_discovery.py --json

Exit 0 report-only always; 2 COULD NOT RUN.

── WHY THIS EXISTS ────────────────────────────────────────────────────────────
docs/coding-rule-registry.json is hand-written, and its own header says so: no
property of a function tells you it encodes a federal billing rule. That was
true of the JUDGEMENT and it was never true of the CANDIDATE SET. Eight rules
were registered on the day the registry was built; SAIRNcode alone holds more
than twenty `scValidate*` functions, and a registry nobody can be prompted to
extend has a failure mode this platform has paid for repeatedly: a MISSING
entry and a REVIEWED entry look identical from the outside.

THE PATTERN IS ALREADY PROVEN TWICE HERE. tools/sairn_app_map_check.py derives
the App File Map from `git ls-files` + vercel.json + a live request and refuses
to rewrite the hand-decided columns; tools/tooling_inventory.py derives its own
listing. Both keep the judgement in human hands and take the ENUMERATION out of
them. This is the third instance of that split, applied to rules.

── THE TWO SIGNALS, AND BOTH ARE THE CODEBASE'S OWN CONVENTIONS ───────────────
Neither is invented for this tool. Both are read out of how SAIRNcode already
writes rules, which is why they cannot drift from it without the drift showing.

  S1  THE FINDING CONVENTION. Every graded rule on this platform emits through
      a `*Finding(severity, rule, detail, sourceKey)` builder -- scPtFinding,
      scEdFinding, scChiroFinding and seven more. A function that CALLS one
      produces graded findings, which is what a rule is. Strong and almost
      noiseless: 14 hits in sairncode.html, every one a real validator.

  S2  THE CITATION CONVENTION, ONE HOP OUT. Some rules do not use a finding
      builder -- the DMEPOS family returns its own shape -- but their PANEL
      HANDLER cites a `*_SOURCES` map when it renders the answer. So: a
      locally-defined function CALLED from inside a function that cites a
      source map is a candidate. That alone would sweep in every DOM helper on
      the same line, so it is narrowed by a property a rule actually has:

      A RULE IS PURE. It takes inputs and returns findings. It does not touch
      `document.`, `localStorage` or `innerHTML`. dmeValidateSwo passes;
      dmeBox, which renders the box the answer goes in, does not. That test is
      structural rather than a list of names to keep up to date.

      AND THE CITING FUNCTION MUST BE A PANEL HANDLER -- wired from an
      `onclick=`/`onchange=` in the markup. Without that narrowing S2 reported
      70 candidates on sairncode.html and most were dragged in by ONE generic
      helper: scCsvCell cites a source map and calls `csvField`, `isMobileNav`,
      `authBadgeClass` and a dozen more, none of which is a rule. A rule is
      reached by a control somebody clicks, through a handler that cites the
      source it renders -- and "is this name in an onclick" is read out of the
      HTML rather than guessed from a naming convention.

── WHAT IT DOES NOT DO, AND WILL NOT ──────────────────────────────────────────
It does not register anything. Whether a candidate IS a coding rule -- and what
its harm sentence and citation are -- is the judgement the registry exists to
hold, and a tool that auto-registered would fill it with guesses. It also does
not claim completeness: a rule written in neither convention is invisible here,
and that limit is printed on every run rather than left to be discovered.

THE FALSE-POSITIVE DIRECTION IS DELIBERATE. Showing a candidate that turns out
not to be a rule costs somebody thirty seconds. Missing one costs a federal
billing rule nobody outside its author has ever read, which is the state all
eight registered rules were in on the day the registry was created.
"""

import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(REPO, 'docs', 'coding-rule-registry.json')

# A rule is PURE. These are the marks of a function that renders or persists,
# which is the other half of every panel and never the rule itself.
IMPURE = re.compile(r'\bdocument\.|localStorage|innerHTML|\bsessionStorage\b'
                    r'|\bshowToast\s*\(|\bfetch\s*\(')
FUNC = re.compile(r'^[ \t]*(?:async[ \t]+)?function[ \t]+([A-Za-z0-9_$]+)[ \t]*\(', re.M)


def die(msg):
    sys.stderr.write('COULD NOT RUN: %s\n' % msg)
    sys.exit(2)


def block_after(text, idx):
    """Brace-matched body starting at the first `{` at or after idx."""
    i = text.find('{', idx)
    if i < 0:
        return ''
    depth, q, start = 0, None, i
    while i < len(text):
        c, p = text[i], text[i - 1] if i else ''
        if q:
            if c == q and p != '\\':
                q = None
        elif c in ('"', "'", '`'):
            q = c
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = len(text) if j < 0 else j
        elif text.startswith('/*', i):
            j = text.find('*/', i)
            i = len(text) if j < 0 else j + 1
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return text[start:]


def functions(text):
    """name -> (line, body). Last definition wins, which matches JS."""
    out = {}
    for m in FUNC.finditer(text):
        out[m.group(1)] = (text.count('\n', 0, m.start()) + 1,
                           block_after(text, m.end()))
    return out


def discover(path):
    text = io.open(os.path.join(REPO, path), encoding='utf-8', errors='replace').read()
    return discover_text(text)


# SPLIT OUT SO THE PROBE CAN LOCK THE CRITERIA AGAINST SYNTHETIC FIXTURES
# WITHOUT WRITING A FILE. Same reason scan_text() is split out of scan() in
# pinned_list_drift_check.py: a probe that must write into the repo to test a
# scanner is a probe that can lose another session's work on a shared tree.
def discover_text(text):
    funcs = functions(text)
    source_maps = sorted(set(re.findall(
        r'\b(?:var|const|let)\s+([A-Z][A-Z0-9_]*_SOURCES)\s*=', text)))
    builders = sorted(set(re.findall(
        r'function\s+([A-Za-z0-9_$]*[Ff]inding)\s*\(', text)))

    hits = {}
    if builders:
        call_builder = re.compile(r'\b(?:%s)\s*\(' % '|'.join(map(re.escape, builders)))
        for name, (line, body) in funcs.items():
            if name in builders:
                continue
            if call_builder.search(body):
                hits[name] = {'line': line, 'why': 'S1 emits graded findings via '
                              + '/'.join(b for b in builders if b + '(' in body)}

    # Wired from the markup. Read out of the HTML, so it cannot drift from what
    # the panel actually calls.
    wired = set(re.findall(
        r'on(?:click|change|input|blur|submit)\s*=\s*["\']\s*([A-Za-z0-9_$]+)\s*\(',
        text))
    if source_maps:
        cites = re.compile(r'\b(?:%s)\b' % '|'.join(map(re.escape, source_maps)))
        local = re.compile(r'\b([A-Za-z0-9_$]+)\s*\(')
        for name, (line, body) in funcs.items():
            if name not in wired or not cites.search(body):
                continue
            for callee in set(local.findall(body)):
                if callee == name or callee not in funcs or callee in hits:
                    continue
                if callee in builders:
                    continue
                cline, cbody = funcs[callee]
                if not cbody or IMPURE.search(cbody):
                    continue
                hits[callee] = {'line': cline,
                                'why': 'S2 pure, called from the wired handler %s '
                                       'which cites a source map' % name}
    return source_maps, builders, hits


def registered():
    try:
        data = json.load(io.open(REGISTRY, encoding='utf-8'))
    except OSError as e:
        die('docs/coding-rule-registry.json could not be read: %s' % e)
    except ValueError as e:
        die('docs/coding-rule-registry.json is not valid JSON: %s' % e)
    rules = data.get('rules') if isinstance(data, dict) else None
    if not isinstance(rules, list) or not rules:
        die('the registry yielded ZERO rules, so every candidate below would '
            'read as unregistered and the number would mean nothing.')
    # A rule is registered against an ANCHOR, and an anchor names a construct.
    # Matching on "the anchor mentions this function" is what connects the two
    # without the registry having to repeat a function name in a second field.
    return rules


def main(argv):
    rules = registered()
    files = sorted(set(r['file'] for r in rules if r.get('file')))
    # Every file the registry already points at, PLUS every app file -- a rule
    # in an app nobody has registered yet is exactly what this is for.
    for f in sorted(os.listdir(REPO)):
        if f.endswith('.html') and f not in files:
            files.append(f)

    out, total, unreg = [], 0, 0
    for path in files:
        if not os.path.isfile(os.path.join(REPO, path)):
            continue
        maps, builders, hits = discover(path)
        if not hits:
            continue
        anchors = ' '.join(r['anchor'] for r in rules
                           if r.get('file') == path)
        for name, info in sorted(hits.items()):
            total += 1
            is_reg = (name + '(') in anchors or (name + ' ') in anchors
            if not is_reg:
                unreg += 1
            out.append({'file': path, 'function': name, 'line': info['line'],
                        'registered': is_reg, 'why': info['why']})

    if '--json' in argv:
        print(json.dumps({'candidates': out, 'total': total,
                          'unregistered': unreg}, indent=2))
        return 0

    print('CODING RULE DISCOVERY -- report only, derived from the codebase\'s '
          'own conventions\n')
    by_file = {}
    for c in out:
        by_file.setdefault(c['file'], []).append(c)
    for path in sorted(by_file):
        rows = by_file[path]
        print('%s -- %d candidate(s), %d unregistered'
              % (path, len(rows), sum(1 for r in rows if not r['registered'])))
        for c in sorted(rows, key=lambda x: (x['registered'], x['function'])):
            print('  %-4s %-36s :%-7d %s'
                  % ('reg' if c['registered'] else 'NEW', c['function'],
                     c['line'], c['why'][:70]))
        print('')

    print('%d candidate rule(s); %d are NOT in docs/coding-rule-registry.json.'
          % (total, unreg))
    if unreg:
        print('\nEach is a JUDGEMENT, not a finding. Registering one means '
              'deciding what\nit DECIDES, what the HARM is when it is wrong, and '
              'which source says so --\nwhich is the work this tool deliberately '
              'does not do. Add an entry with an\nanchor naming the construct, '
              'then `python tools/tier_a_review_gate.py --rules`\nwill locate it '
              'and the review obligation can name it.')
    print('\nWHAT THIS CANNOT SEE, and it is not a small caveat: a rule written '
          'in\nNEITHER convention -- no finding builder, and no source map cited '
          'by its\ncaller -- is invisible here. The two signals are read out of '
          'how this\ncodebase already writes rules, so they cover what it does '
          'today and say\nnothing about what somebody writes tomorrow in a third '
          'shape.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
