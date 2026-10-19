#!/usr/bin/env python
# OWNER: cc
# written 2026-10-19, batch b18 item 2 -- evidence, not a gate
r"""Does an ESCAPED PIPE inside a code span inside a table render the backslash?
Asked of GITHUB'S OWN RENDERER, which is the target that actually serves
docs/SAIRN-OPEN-WORK-INDEX.md.

    python docs/2026-10-19-cc-b18-github-render-confirmation.py

WHY THIS EXISTS. cc b17 told hank his premise was false -- that `\|` inside a
backtick span "renders the backslash literally in this table" -- on the
strength of markdown-it-py agreeing with the GFM spec in two presets. That left
a real gap, named in b17's own UNVERIFIED: a library and a spec are one
opinion about a renderer, not the renderer. Convention 6 of
docs/2026-09-13-cross-domain-disciplines.md is explicit that independence needs
a STRUCTURALLY DIFFERENT method, and a third local library would have been a
second copy of the same opinion. GitHub's /markdown API is the different
method: it IS the render target.

MEASURED 2026-10-19, HTTP 200, 534 bytes:

    GitHub      <td>six inert <code class="notranslate">||</code> alias ...
    markdown-it <td>six inert <code>||</code> alias ...
    code spans agree on all three rows, and NEITHER emits a backslash

So the b17 verdict is CONFIRMED against the real target and the UNVERIFIED
closes. hank's routed note can be retired for good, and the repair it
recommended -- spelling the operator out in words -- would have removed the
operator the row is about.

ONE TRAP WORTH KEEPING. The first version of the comparator matched `<code>`
exactly. GitHub emits `<code class="notranslate">`, so it found zero spans on
GitHub's side and printed AGREE: False -- a difference about DECORATION
reported as a difference about the escape, which is the exact failure the
comment above the comparison warns about. It is kept in the code as a comment
rather than tidied away.

NEEDS NETWORK AND NO TOKEN (/markdown is unauthenticated, 60 requests an hour
per IP). Exit 0 both renderers agree and neither emits a backslash, 1 if they
disagree -- which would mean b17 was wrong and hank was right -- and 2 COULD
NOT RUN on any non-200 or a missing markdown-it, because a failed request is
not a measurement.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

BS = chr(92)
PIPE = '|'
NL = chr(10)

# The two spans hank quoted, plus the real row cc measured at index line 645.
# Built from chr() rather than typed, because a backslash in a source literal
# is one more place for it to be eaten -- which happened twice in b17.
ESC = BS + PIPE + BS + PIPE
FRAGMENT = (
    '| app | item | status |' + NL +
    '|---|---|---|' + NL +
    '| Platform | six inert `' + ESC + '` alias fallbacks | open |' + NL +
    '| Platform | `x ' + ESC + ' new Date().toISOString()` | open |' + NL +
    '| Platform | **`(x ' + ESC + ' 0)`** in a numeric fold | open |' + NL
)

# GitHub adds class="notranslate"; markdown-it does not. Match the open tag
# with optional attributes, or a decoration difference reads as a disagreement
# about the escape. See the docstring -- this is the trap, kept.
CODE_RE = re.compile(r'<code[^>]*>(.*?)</code>', re.S)


def main():
    try:
        from markdown_it import MarkdownIt
    except Exception as exc:                                     # noqa: BLE001
        print('COULD NOT RUN: markdown-it-py is not importable (%s), so there '
              'is nothing to compare GitHub against.' % exc)
        return 2
    try:
        import sairn_http as H
    except Exception as exc:                                     # noqa: BLE001
        print('COULD NOT RUN: tools/sairn_http.py would not import (%s). Bare '
              'curl is not the substitute -- see the push protocol.' % exc)
        return 2

    md = MarkdownIt('gfm-like')
    md.options['linkify'] = False
    try:
        md.disable('linkify')
    except Exception:                                            # noqa: BLE001
        pass
    mi_html = md.render(FRAGMENT)

    payload = json.dumps({'text': FRAGMENT, 'mode': 'gfm'}).encode('utf-8')
    try:
        status, raw = H.fetch(
            'https://api.github.com/markdown', method='POST', data=payload,
            headers={'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28',
                     'Content-Type': 'application/json'})
    except Exception as exc:                                     # noqa: BLE001
        print('COULD NOT RUN: the request to GitHub failed (%s). A failed '
              'request is not a measurement and is NOT reported as '
              'agreement.' % str(exc)[:160])
        return 2
    if status != 200:
        print('COULD NOT RUN: GitHub answered HTTP %s, so nothing was '
              'measured.' % status)
        print(raw.decode('utf-8', 'replace')[:300])
        return 2
    gh_html = raw.decode('utf-8', 'replace')

    gh = CODE_RE.findall(gh_html)
    mi = CODE_RE.findall(mi_html)
    print('GITHUB RENDER CONFIRMATION -- the real target, HTTP %s, %d bytes'
          % (status, len(gh_html)))
    print('  code spans, GitHub      : %r' % gh)
    print('  code spans, markdown-it : %r' % mi)
    print('  backslash in GitHub     : %s' % (BS in gh_html))
    print('  backslash in markdown-it: %s' % (BS in mi_html))
    print('')
    agree = (gh == mi)
    clean = (BS not in ''.join(gh) and BS not in ''.join(mi))
    if not gh:
        print('COULD NOT RUN: GitHub returned 200 but no code span was found, '
              'so the comparator is measuring nothing. Check CODE_RE against '
              'the HTML before trusting any verdict from here.')
        return 2
    if agree and clean:
        print('CONFIRMED: GitHub and markdown-it agree on every code span, and '
              'NEITHER emits a backslash. b17\'s verdict holds against the '
              'real render target and hank\'s premise is false.')
        return 0
    print('DISAGREEMENT: b17 told hank his premise was false on the strength '
          'of a library, and the real renderer does not agree. That is a '
          'CORRECTION owed to hank, not a footnote.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
