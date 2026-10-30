# OWNER: cody
r"""A save that waits must hold its trigger -- the b64 re-entry sweep as a standing check.

    python tools/reentry_hold_check.py               # every top-level *.html
    python tools/reentry_hold_check.py --fixtures    # the criteria lock alone
    python tools/reentry_hold_check.py --json

REPORT ONLY. Exit 0 clean, 1 findings, 2 COULD NOT RUN. It writes nothing.

-- WHY ---------------------------------------------------------------------
cody b64 found 47 user-triggered handlers that awaited before their visible
step while the trigger stayed live, so a second press made a second record.
They were found by a scanner that lived in one session's scratchpad and was
lost. b65 then found three MORE just outside its shape (a GPS wait, a timer
reset, a hold taken outside its try). This is that scanner as a tool, with its
criteria locked against synthetic fixtures first (disciplines section 1), so
the next handler written in the old shape is reported rather than rediscovered.

-- THE PREDICATE, with its span (disciplines section 35) --------------------
UNIVERSE: every function in a top-level *.html that an inline event attribute
(on<event>="NAME(") in the same file calls, and that is declared as
`async function NAME(` or `NAME = async function (`.
SPAN: the function body, from its `{` to the matching `}`, with braces inside
strings, template literals and comments skipped.
  A = the first real `await` in the body (not one inside a string or comment).
  WRITE anywhere in the body: st( / localStorage.setItem( / .push( /
       .unshift( / <x>Data('write' -- before the wait it is a record written
       while the trigger is live, after it the visible step comes late.
  DISMISSED before A: close*( / hide*( / .style.display='none' / .value='' /
       .reset() -- the trigger is gone, so there is nothing to press twice.
  HOLD: an identifier H that is CHECKED in an early return before A
       (`if(H)` / `if(H>0)` ... `return`) AND SET before A (`H=true` / `H++`)
       -- or a call to a declared shared hold helper (HOLD_HELPERS).
VERDICT per function:
  NOT-SUBJECT    no real await, no write, or the trigger dismissed before A
  HELD           a hold as defined
  RE-ENTRANT     awaits, writes after, no hold        <- the finding
  COULD-NOT-PARSE  the body's braces do not balance   <- never folded into clean

-- WHAT IT DOES NOT SEE, said so a clean run is not read as more ----------
  * .then()-style handlers with no `await` (b64's .then saves were read by hand)
  * addEventListener / delegated handlers with no inline on<event> attribute
  * the TIMER-RESET shape (stonedesk posCompleteSale's 2.5 s window, b65): no
    await at all, so no predicate here can reach it
  * whether the hold is RELEASED on every path (b65 R-11 was a release gap)
  * whether a write is a real record or a UI list -- a .push into a render
    array is counted as a write, so a finding is a CANDIDATE to read
"""
import json
import os
import re
import sys

CRITERIA_VERSION = '2026-10-30.cody-b69.4'   # .4: disabled-button hold, named dismissals, creation required
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLD_HELPERS = ('scHoldWhile', 'scSaveBusy')
WRITE_RE = re.compile(r"(?<![\w$])st\(|localStorage\.setItem\(|\.push\(|\.unshift\(")
# The <x>Data('write' form is matched on RAW text -- its 'write' is a string,
# which masking blanks -- and counts only where `Data(` itself is code.
DISMISS_RE = re.compile(r"[\w$]*(?:[cC]lose|[hH]ide)\w*\(|\.style\.display\s*=\s*['\"]none['\"]|\.value\s*=\s*''|\.value\s*=\s*\"\"|\.reset\(\)")
# A NEW record per press, or an amount applied per press. An update of an
# existing row by its own id writes the same thing twice, which is not b64's
# duplicate. (b64's real ones: newId()/Date.now() ids, amount_paid applied twice.)
CREATES_RE = re.compile(r"newId\(|Date\.now\(\)|\+=\s*[\w$(]")
DISABLED_RE = re.compile(r"\.disabled\s*=\s*true\b")
DATA_WRITE_RE = re.compile(r"[A-Za-z]Data\(\s*['\"]write['\"]")
INLINE_RE = re.compile(r"""\bon[a-z]+\s*=\s*["']\s*(?:return\s+)?(?:window\.)?([A-Za-z_$][\w$]*)\s*\(""")
DECL_RES = (re.compile(r'async\s+function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{'),
            re.compile(r'(?:window\.)?([A-Za-z_$][\w$]*)\s*=\s*async\s+function\s*[\w$]*\s*\([^)]*\)\s*\{'))


REGEX_PREV = set('(,=:[!&|?{};+-*%<>~^')


def mask(src, stop_at_balance=False):
    """Same length as src; strings, template literals, regex literals and
    comments become spaces. Returns None when one of them never closes.
    With stop_at_balance, scanning ends at the `}` that closes src[0]'s `{`
    and the masked prefix up to it is returned -- so text AFTER the function
    (later scripts, HTML prose with apostrophes) can never poison the span."""
    out, i, n, depth = list(src), 0, len(src), 0
    last = ''                                   # last significant code char

    def blank(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '
    while i < n:
        c = src[i]
        if c in '"\'`':
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == '\\' else 1
            if j >= n:
                return None
            blank(i, j + 1)
            i, last = j + 1, 'x'
        elif src.startswith('//', i):
            j = src.find('\n', i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2)
            if j < 0:
                return None
            blank(i, j + 2)
            i = j + 2
        elif c == '/' and (last == '' or last in REGEX_PREV):
            j, in_class = i + 1, False                 # a regex literal
            while j < n and src[j] != '\n':
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == '[':
                    in_class = True
                elif src[j] == ']':
                    in_class = False
                elif src[j] == '/' and not in_class:
                    break
                j += 1
            if j >= n or src[j] != '/':
                return None
            blank(i, j + 1)
            i, last = j + 1, 'x'
        else:
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if stop_at_balance and depth == 0:
                    return ''.join(out[:i + 1])
            if not c.isspace():
                last = c
            i += 1
    return None if stop_at_balance else ''.join(out)


def body_span(masked, open_at):
    """(start, end) of the body whose `{` is at open_at, or None if unbalanced."""
    depth = 0
    for i in range(open_at, len(masked)):
        if masked[i] == '{':
            depth += 1
        elif masked[i] == '}':
            depth -= 1
            if depth == 0:
                return open_at, i + 1
    return None


def classify(raw_body):
    """Verdict for one function body (the text from `{` to `}`)."""
    m = mask(raw_body)
    if m is None or body_span(m, 0) is None or body_span(m, 0)[1] != len(m):
        return 'COULD-NOT-PARSE', ''
    a = re.search(r'(?<![\w$])await\b', m)
    if not a:
        return 'NOT-SUBJECT', 'no await'
    w = WRITE_RE.search(m)
    token = m[w.start():w.end()] if w else ''
    if not w:
        for d in DATA_WRITE_RE.finditer(raw_body):
            if m[d.start():d.start() + 5] == raw_body[d.start():d.start() + 5]:
                token = "Data('write'"
                break
    if not token:
        return 'NOT-SUBJECT', 'writes nothing'
    if not CREATES_RE.search(m):
        return 'NOT-SUBJECT', 'no new record or applied amount (a re-press rewrites the same row)'
    before = m[:a.start()]
    # THE TRIGGER IS GONE BEFORE THE WAIT: a modal closed, a panel hidden or the
    # form cleared before the first await leaves nothing to press twice.
    # Matched on RAW text because `'none'` and `''` are strings, which masking
    # blanks; the match must start at a code position.
    for d in DISMISS_RE.finditer(raw_body, 0, a.start()):
        if m[d.start()] == raw_body[d.start()]:
            return 'NOT-SUBJECT', 'trigger dismissed before the wait (%s)' % d.group(0).strip()
    if DISABLED_RE.search(before):
        return 'HELD', 'trigger disabled before the wait'
    for helper in HOLD_HELPERS:
        if re.search(r'(?<![\w$])' + helper + r'\s*\(', m):
            return 'HELD', 'shared helper ' + helper
    for chk in re.finditer(r'if\s*\(\s*([A-Za-z_$][\w$]*)\s*(?:>\s*0\s*)?\)\s*(?:\{[^{}]*?\breturn\b|[^;{}]*?\breturn\b)', before):
        h = chk.group(1)
        if re.search(r'(?<![\w$.])' + re.escape(h) + r'\s*(?:=\s*true\b|\+\+)', before):
            return 'HELD', h
    return 'RE-ENTRANT', 'awaits, then writes (%s) with no hold' % token.strip()


# -- THE CRITERIA LOCK: hand-built bodies, each with the verdict it must get --
# A fixture whose EXPECTED verdict was wrong may be corrected; a fixture is
# never changed to match what the tool produced. None has been changed yet.
FIXTURES = [
    # .4: the bodies below gained the `newId(` / `Date.now()` the defect needs
    # (a NEW record per press); their expected verdicts did not change.
    ('F1 awaits then st(, no hold', "{ var r = await save(x); list.push({id:newId('A')}); st('k', list); }", 'RE-ENTRANT'),
    ('F2 flag checked, set before, released in finally',
     "{ if(busy){toast('Still');return;} busy=true; try{ await save(x); }finally{busy=false;} l.push({id:newId('A')}); st('k',l); }", 'HELD'),
    ('F3 flag checked but never SET -- a check is not a hold',
     "{ if(busy){return;} await save(x); l.push({id:newId('A')}); st('k',l); }", 'RE-ENTRANT'),
    # F4 CORRECTED in .3 -- its expected verdict was WRONG, not changed to fit
    # output: b64's defect is a record written while the trigger stays live
    # across the wait, and a write BEFORE the await with nothing dismissed is
    # exactly that (a second press writes a second record during the wait).
    ('F4 writes BEFORE the await, trigger left live', "{ l.push({id:newId('A')}); st('k',l); await save(x); }", 'RE-ENTRANT'),
    ('F5 shared helper', "{ return scHoldWhile('k', async function(){ await save(x); l.push({id:newId('A')}); st('k',l); }); }", 'HELD'),
    ('F6 await only inside a string or comment',
     "{ toast('please await the result'); // await later\n st('k',l); }", 'NOT-SUBJECT'),
    ('F7 flag SET after the await', "{ if(busy)return; await save(x); busy=true; l.push({id:newId('A')}); st('k',l); }", 'RE-ENTRANT'),
    ('F8 unbalanced braces', "{ if (x) { await save(x); st('k',l); }", 'COULD-NOT-PARSE'),
    ('F9 counter form, b65 dental', "{ if(n>0){toast('Still');return;} n++; try{ await w(); }finally{n--;} rows.push({id:newId('A')}); }", 'HELD'),
    ('F10 write through <x>Data(\'write\'', "{ var rec={id:'CO-'+Date.now()}; await gps(); var r = await grdData('write','t',rec); }", 'RE-ENTRANT'),
    ('F11 a dotted flag is not the bare identifier', "{ if(o.busy)return; o.busy=true; await s(); l.push({id:newId('A')}); st('k',l); }", 'RE-ENTRANT'),
    # ADDED after the first real run, which reported 118 COULD-NOT-PARSE: the
    # scanner read a regex literal's quote as an open string. The expected
    # verdicts are what the bodies plainly are, not taken from tool output.
    ('F12 a regex literal holding a quote and a brace', "{ var t = s.replace(/['{]/g, ''); await save(t); l.push({id:newId('A')}); st('k',l); }", 'RE-ENTRANT'),
    ('F14 modal closed before the wait, the awaited sync is the last step',
     "{ list.push(rec); st('k',list); closeModal(); var r = await xData('write','t',rec); toast(r?'ok':'no'); }", 'NOT-SUBJECT'),
    ('F15 form cleared before the wait', "{ st('k',l); $('f').value=''; await save(x); }", 'NOT-SUBJECT'),
    ('F16 dismissal AFTER the wait does not count', "{ list.push({id:newId('A')}); await save(rec); closeModal(); }", 'RE-ENTRANT'),
    # .4, each a gap against b64's definition found in a judged sample of 10:
    ('F17 button disabled before the wait', "{ btn.disabled = true; var r = await post(x); rows.push({id:newId('E')}); }", 'HELD'),
    ('F18 a dismissal named inside an identifier', "{ list.push({id:'I-'+Date.now()}); st('k',list); scpCloseInvModal(); await w(); }", 'NOT-SUBJECT'),
    ('F19 an update of an existing row by its id', "{ var s=list.find(f); s.price=p; st('k',list); await xData('write','t',s); }", 'NOT-SUBJECT'),
    ('F20 an amount applied per press', "{ c.amount_paid += amt; st('k',list); await xData('write','t',c); toast('ok'); }", 'RE-ENTRANT'),
    ('F13 division is not a regex', "{ var r = a / b; var q = c / d; await save(r); l.push({id:newId('A')}); st('k',l); }", 'RE-ENTRANT'),
]


def run_fixtures():
    bad = []
    for name, body, want in FIXTURES:
        got = classify(body)[0]
        if got != want:
            bad.append((name, want, got))
    return bad


def scan(paths):
    rows, unreadable = [], []
    for p in paths:
        try:
            src = open(p, encoding='utf-8', errors='strict').read()
        except (OSError, UnicodeDecodeError) as e:
            unreadable.append((p, str(e)))
            continue
        wired = set(INLINE_RE.findall(src))
        seen = set()
        for rx in DECL_RES:
            for m in rx.finditer(src):
                name = m.group(1)
                if name not in wired or (name, m.start()) in seen:
                    continue
                seen.add((name, m.start()))
                open_at = m.end() - 1
                # Span from the declaration's `{` to the `}` that balances it,
                # found by the same scanner that masks strings and regexes, so
                # nothing before OR after the function can shift the count.
                body = mask(src[open_at:], stop_at_balance=True)
                if body is None:
                    rows.append((p, name, src.count('\n', 0, m.start()) + 1, 'COULD-NOT-PARSE', ''))
                    continue
                verdict, why = classify(src[open_at:open_at + len(body)])
                rows.append((p, name, src.count('\n', 0, m.start()) + 1, verdict, why))
    return rows, unreadable


def main(argv):
    bad = run_fixtures()
    print('RE-ENTRY HOLD CHECK -- criteria %s -- fixtures %d/%d' % (CRITERIA_VERSION, len(FIXTURES) - len(bad), len(FIXTURES)))
    for name, want, got in bad:
        print('  FIXTURE FAIL %s: expected %s, got %s' % (name, want, got))
    if bad:
        print('COULD NOT RUN: the criteria lock failed, so nothing real was judged.')
        return 2
    if '--fixtures' in argv:
        return 0
    paths = sorted(os.path.join(REPO, f) for f in os.listdir(REPO) if f.endswith('.html'))
    if not paths:
        print('COULD NOT RUN: no *.html at the repo root.')
        return 2
    rows, unreadable = scan(paths)
    if '--json' in argv:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'rows': rows, 'unreadable': unreadable}, indent=1))
    counts = {}
    for r in rows:
        counts[r[3]] = counts.get(r[3], 0) + 1
    print('%d files, %d inline-wired async handlers: %s' % (
        len(paths), len(rows), ', '.join('%s %d' % kv for kv in sorted(counts.items()))))
    for p, name, line, verdict, why in rows:
        if verdict in ('RE-ENTRANT', 'COULD-NOT-PARSE'):
            print('  %-15s %s:%d %s -- %s' % (verdict, os.path.relpath(p, REPO), line, name, why))
    for p, e in unreadable:
        print('  UNREADABLE %s: %s' % (os.path.relpath(p, REPO), e))
    print('NOT CHECKED (see the docstring): .then() handlers, addEventListener/delegated handlers, '
          'the timer-reset shape, release-on-every-path.')
    if unreadable or counts.get('COULD-NOT-PARSE'):
        return 2 if not counts.get('RE-ENTRANT') else 1
    return 1 if counts.get('RE-ENTRANT') else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
