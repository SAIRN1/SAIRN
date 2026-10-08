# OWNER: cc
"""tools/exit_status_attributable.py -- does the exit status this command
returns actually belong to the program you are about to judge?

── THE PATTERN THIS EXISTS FOR, MEASURED TWICE IN TWO DAYS ───────────────────
Both errors were the same shape: A STATUS READ OFF THE WRONG SUBJECT.

  1. 2026-10-04. I ran `python tools/md_table_check.py 2>&1 | tail -8` inside an
     `&&` chain, saw exit 2, and wrote "md_table_check.py EXITS 2 (COULD NOT
     RUN) while reporting 0 malformed rows" into the standing open-work index
     AND a commit message. THE TOOL EXITS 0 and has no code path that returns 2
     at all. The 2 belonged to the last element of the chain.

  2. 2026-10-05. After a push had already succeeded, a SUBSEQUENT no-op push
     printed "Blocked: this gate could not tell what is being pushed -- no ref
     lines on stdin". I read it as a refusal OF MY PUSH. `git rev-list
     --left-right --count origin/main...HEAD` answered `0 0`: there was nothing
     to send, so the hook was invoked with no refs.

The first cost a false accusation against a working checker in a standing
document. The second cost a wrong conclusion that I nearly acted on.

── WHY A CHECK IS POSSIBLE AT ALL, when "did you misread it" sounds subjective
The hazardous half is NOT subjective and needs no intent inference: **a shell
pipeline or an `&&` / `||` chain returns ONE status, and it is not the status of
the program you named.** That is decidable from the command text alone.

So this does not try to know what you believe. It answers one mechanical
question -- IS THE STATUS THIS COMMAND RETURNS ATTRIBUTABLE TO A SINGLE NAMED
PROGRAM -- and when the answer is no, it names which element the status will
actually come from and what to run instead.

── WHAT IT DOES NOT DO ────────────────────────────────────────────────────────
It does not say a pipeline is wrong. Piping into `tail` to keep output short is
correct and common, and the overwhelming majority of commands here do it. THE
OUTPUT IS A LIST TO READ, and the judgement -- am I about to quote this status
as a fact about that program -- stays with the person. A gate here would be
cleared by dropping the `| tail`, which makes output unreadable and buys
nothing.

It also cannot see the SECOND half of error 2: that a no-op push produces a
refusal-shaped message. Nothing in the command text says whether there is
anything to push. That half is named here and NOT claimed.

── FAILS CLOSED (PR 1.11) ─────────────────────────────────────────────────────
Exit 2 COULD NOT RUN -- never 0 -- when the command cannot be tokenised at all.
A linter that silently passed an unparseable command would be the same class of
defect it exists to find.

Exit 1 only with `--strict`. Default is report-only, exit 0.

CLI:
    python tools/exit_status_attributable.py 'python tools/x.py | tail -3'
    python tools/exit_status_attributable.py --stdin   < command.txt
    python tools/exit_status_attributable.py --selftest
"""
import io
import json
import os
import re
import shlex
import sys

COULD_NOT_RUN = 2
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Separators after which the FINAL element owns the status. Split on raw text
# rather than shlex tokens: shlex splits on whitespace only, so `a;b` arrives as
# one token -- the same reason tools/git_push_master_guard.py splits on text.
SEPARATORS = re.compile(r'\|\||&&|;|\||\n')

# A pipeline whose last element is one of these is the classic "I read the
# filter's status" shape. Named so the message can be specific rather than
# generic.
FILTERS = ('tail', 'head', 'grep', 'sed', 'awk', 'cut', 'sort', 'uniq', 'wc',
           'tr', 'cat', 'tee', 'jq', 'xargs')


SEPARATORS_CAP = re.compile(r'(\|\||&&|;|\||\n)')


def elements(cmd):
    """The command text split into the pieces a shell would sequence."""
    return elements_and_seps(cmd)[0]


def elements_and_seps(cmd):
    """(parts, seps) where seps[i] is the separator that FOLLOWS parts[i].

    ── FALSE POSITIVE 5: A SEPARATOR INSIDE A QUOTED ARGUMENT IS NOT A
    SEPARATOR (2026-10-06) ─────────────────────────────────────────────────
    Found the way the other four were -- the hook firing on my own command,
    which was:

        python tools/sairn_status.py set --task "...both ways; writing the
        inventory" > /tmp/st.txt 2>&1; echo "RC=$?"; cat /tmp/st.txt

    That is the remedy shape and should have been silent. The `;` INSIDE the
    quoted `--task` value split the command, so the element holding the tool no
    longer contained the redirect, and the suppression could not fire.

    THIS WAS NEVER ONLY A SUBJECT-HALF PROBLEM. `SEPARATORS.split()` is also
    what `analyse()` uses, so EVERY command carrying a quoted semicolon --
    a commit message, a `--task`, a sed script -- was being decomposed wrongly
    by the attribution half too, and the wrong decomposition then decided which
    element "owns" the status. A tool whose subject is reading a status off the
    wrong subject was itself reading the wrong text.

    So the separators are located in the QUOTE-MASKED text and the slices are
    taken from the RAW text. `mask_quoted` preserves length exactly, which is
    what makes the offsets interchangeable -- that property was written for the
    subject matcher and is load-bearing here.

    seps[i] is '' for the last part when the command does not end in a
    separator; callers index defensively.
    """
    masked = mask_quoted(cmd)
    parts, seps, pos = [], [], 0
    for m in SEPARATORS_CAP.finditer(masked):
        text = cmd[pos:m.start()].strip()
        if text:
            parts.append(text)
            seps.append(m.group(0))
        pos = m.end()
    tail = cmd[pos:].strip()
    if tail:
        parts.append(tail)
        seps.append('')
    return parts, seps


def program(piece):
    """The program a single command piece invokes, best effort.

    Skips leading VAR=value assignments -- `SAIRN_SEED_GATE=off git push` runs
    git, not an assignment -- and skips `cd`, which is almost never the subject.
    """
    try:
        toks = shlex.split(piece, posix=True)
    except ValueError:
        toks = piece.split()
    for t in toks:
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):
            continue
        return t
    return ''


def analyse(cmd):
    """(attributable, owner, parts, note)."""
    if not cmd.strip():
        return None, '', [], 'empty command'
    parts = elements(cmd)
    if not parts:
        return None, '', [], 'nothing to analyse'
    if len(parts) == 1:
        return True, program(parts[0]), parts, ''
    owner = program(parts[-1])
    note = ''
    if owner in FILTERS:
        note = ('the status will come from `%s`, a text filter, which exits 0 '
                'for "I ran" and says NOTHING about the program before it'
                % owner)
    elif '&&' in cmd or '||' in cmd:
        note = ('an `&&` / `||` chain returns the status of whichever element '
                'ran LAST, which may not be the one you are judging')
    else:
        note = 'the status will come from the LAST element, `%s`' % owner
    return False, owner, parts, note


def selftest():
    """Both directions, and the two real commands that caused the errors."""
    ok = True

    def case(label, cmd, want_attributable):
        nonlocal ok
        att, owner, parts, note = analyse(cmd)
        good = (att is want_attributable)
        print('%s %-54s -> attributable=%s owner=%r'
              % ('ok  ' if good else 'FAIL', label, att, owner))
        if not good:
            ok = False

    # THE TWO REAL ONES, verbatim in shape.
    case('error 1: tool piped into tail inside an && chain',
         'node --check api/x.js && python tools/md_table_check.py 2>&1 | tail -8',
         False)
    case('error 2: git push piped through sed/grep/tail',
         'git push origin main 2>&1 | sed "s/^remote: //" | grep -v To | tail -4',
         False)
    # The safe shape the lesson produced.
    case('the fix: redirect, then read the status alone',
         'python tools/md_table_check.py > /tmp/out.txt 2>&1', True)
    # Controls in the other direction, so it is not simply "everything is bad".
    case('a bare command', 'python tools/fail_open_scan.py', True)
    case('a command with an env assignment is still attributable',
         'PYTHONIOENCODING=utf-8 python tools/x.py', True)
    case('a semicolon sequence is NOT attributable', 'echo a; echo b', False)

    # ── THE SUBJECT HALF, added after two FALSE POSITIVES (2026-10-05) ─────
    # Reported against H2's hover_log.py calls with comma-separated --source
    # arguments. The commas were never the cause; these are. Held here because
    # a report-only notice that cries wolf stops being read, and then the real
    # one is invisible too.
    # ── AND A SECOND, STRUCTURALLY DIFFERENT METHOD MUST AGREE (2026-10-06) ──
    # Discipline 6: independence needs a structurally different method, not a
    # second run of the same one. Every subject arm is therefore decided TWICE --
    # once by the shipped positional match over quote-MASKED text, and once by
    # `shlex` with punctuation_chars, a real shell lexer that keeps a quoted run
    # as ONE token and emits the control operators as their own. The two
    # implementations share no code, and an arm where they disagree FAILS.
    #
    # WHY THE LEXER IS A CROSS-CHECK AND NOT THE IMPLEMENTATION, measured before
    # deciding rather than argued: a tokenised version was built and run against
    # all 23 subject arms and AGREED ON EVERY ONE -- so it is not better on
    # anything the arms cover. On eight real hard command shapes it then REFUSED
    # one outright, `python tools/x.py --note "open | tail -1`, an UNMATCHED
    # DOUBLE QUOTE, which the shipped regex handles correctly and which ordinary
    # prose in a --note or a commit message produces. A lexer cannot guess at an
    # unbalanced quote; the regex degrades gracefully. Replacing would have traded
    # a true positive for nothing, and going quiet is the failure this file names
    # as the worse of the two. Cost of running both: 0.022ms against 0.081ms per
    # call, so the cross-check is free and only the selftest pays it.
    def _lex_subject(cmd):
        """The same answer, derived by LEXING. None when the lexer refuses."""
        try:
            lx = shlex.shlex(cmd, posix=True, punctuation_chars=True)
            lx.whitespace_split = True
            toks = list(lx)
        except ValueError:
            return None
        groups, cur, gseps = [], [], []
        for t in toks:
            if t in (';', '&&', '||', '|', '\n'):
                if cur:
                    groups.append(cur)
                    gseps.append(t)
                cur = []
            else:
                cur.append(t)
        if cur:
            groups.append(cur)
            gseps.append('')
        if len(groups) < 2:
            return ''
        for gi, g in enumerate(groups[:-1]):
            i = 0
            while i < len(g) and '=' in g[i] and not g[i].startswith('-'):
                i += 1
            if i < len(g) and os.path.basename(g[i]).split('.')[0] in INTERPRETERS:
                i += 1
                while i < len(g) and g[i].startswith('-'):
                    i += 1
            if i >= len(g) or not SUBJECT_DIRS.fullmatch(g[i]):
                continue
            joined = ' '.join(g)
            nxt = groups[gi + 1] if gi + 1 < len(groups) else []
            if REDIRECTS_OUT.search(joined) and gseps[gi] in SEQUENCING \
                    and any(STATUS_READ.search(t) for t in nxt):
                continue
            return g[i]
        return ''

    def subj(label, cmd, want):
        nonlocal ok
        p_only = elements(cmd)
        p, s = elements_and_seps(cmd)
        if p != p_only:
            print('FAIL elements() and elements_and_seps() disagree on %r' % cmd)
            ok = False
        got = subject_at_risk(p, s)
        good = (bool(got) is want)
        lexed = _lex_subject(cmd)
        if lexed is not None and bool(lexed) is not bool(got):
            print('FAIL the LEXER and the positional match disagree on %r: '
                  'lexer=%r shipped=%r' % (cmd, lexed, got))
            ok = False
        print('%s %-56s subject=%r' % ('ok  ' if good else 'FAIL', label, got))
        if not good:
            ok = False

    subj('a tool named only inside a QUOTED body is not an invocation',
         "python - <<'EOF'\nprint('tools/hover_log.py --source a,b')\nEOF\ncat /tmp/x",
         False)
    subj('a tool in the LAST element owns its own status',
         'echo start && python tools/hover_log.py --source a,b,c', False)
    subj('...including the auditor path with commas, the reported shape',
         'cd /x && python .claude/skills/sairn-hover-auditor/tools/hover_log.py --source a,b,c',
         False)
    subj('a tool path in a quoted ARG, real tool last',
         "python tools/md_table_check.py --note 'see tools/other.py'", False)
    subj('TRUE POSITIVE: piped into a filter',
         'python tools/md_table_check.py | tail -3', True)
    subj('TRUE POSITIVE: non-final element of an && chain',
         'python tools/fail_open_scan.py | tail -2 && echo done', True)

    # ── FALSE POSITIVES 3 AND 4, both found by the hook firing on my own
    # commands while I was fixing it (2026-10-05) ──────────────────────────
    subj('a tool path as grep\'s FILE OPERAND is not an invocation',
         'grep -n import tools/exit_status_attributable.py | head -20', False)
    subj('...nor as sed\'s, nor wc\'s',
         'sed -n 1,20p tools/x.py | tail -3', False)
    subj('THE RECOMMENDED FIX ITSELF: redirect, then read $? alone',
         'python tools/x.py > /tmp/out 2>&1; echo RC=$?; cat /tmp/out', False)
    subj('...and the QUOTED spelling, which is the one actually typed',
         'python tools/x.py > /tmp/out 2>&1; echo "RC=$?"; cat /tmp/out', False)
    subj('an interpreter flag before the path is still an invocation',
         'python -u tools/x.py | tail -1', True)
    subj('an env assignment before the interpreter is still an invocation',
         'PYTHONIOENCODING=utf-8 python tools/x.py | tail -1', True)
    subj('a bare ./tools path as the first token is an invocation',
         'tools/x.py | tail -1', True)
    subj('REDIRECTED but the status is NEVER read -- still at risk',
         'python tools/x.py > /tmp/out 2>&1; cat /tmp/out', True)

    # ── FOURTH'S THREE SHAPES, verbatim from
    # docs/2026-10-05-exit-status-attributable-false-positive.md section 3.
    # Shape 3 is the one my FIRST fix silently blessed: it accepted `$?`
    # ANYWHERE after the tool, so a `tail` running in between made the hook
    # approve a reading of TAIL's status -- the tool's own defect, in its fix.
    subj("Fourth shape 1: `tool > f 2>&1; echo \"exit=$?\"` is CORRECT",
         'node tests/sairnlegacy_item_price_lists.js > /tmp/t1 2>&1; '
         'echo "price-lists exit=$?"', False)
    subj('Fourth shape 2: a pipeline is the real defect',
         'node tests/sairnlegacy_item_price_lists.js | tail -3', True)
    subj('Fourth shape 3: something RAN in between, so $? is tail\'s',
         'node tests/x.js > /tmp/o 2>&1; tail -3 /tmp/o; echo "exit=$?"', True)
    subj('a PIPE to the $? reader is never a measurement',
         'python tools/x.py > /tmp/o 2>&1 | echo "$?"', True)
    subj('&& to the $? reader still measures the tool',
         'python tools/x.py > /tmp/o 2>&1 && echo "rc=$?"', False)
    subj('PowerShell $LASTEXITCODE counts as a status read',
         'python tools/x.py > out.txt 2>&1; echo $LASTEXITCODE', False)

    # ── FALSE POSITIVE 5 (2026-10-06): a separator INSIDE a quoted argument.
    # The real command that exposed it, reduced. Silent is correct here.
    subj('a `;` inside a quoted --task value is not a shell separator',
         'python tools/sairn_status.py set --task "both ways; writing it" '
         '> /tmp/st.txt 2>&1; echo "RC=$?"; cat /tmp/st.txt', False)
    subj('...and a `|` inside one does not make a pipeline either',
         'python tools/x.py --note "a|b" > /tmp/o 2>&1; echo "RC=$?"', False)
    subj('a REAL separator after a quoted one still splits',
         'python tools/x.py --note "a;b" | tail -3', True)

    # ── THE CROSS-CHECK MUST BE LOAD-BEARING, OR IT IS DECORATION ───────────
    # Every subject arm above is decided twice. If `_lex_subject` returned None
    # for everything -- a lexer that always refuses -- the comparison would never
    # fire and 23 arms would be back to one method each, SILENTLY. So the lexer is
    # required to produce a real answer on a plain case, and required to refuse the
    # one shape that is the reason it is not the implementation.
    _probe = _lex_subject('python tools/md_table_check.py | tail -3')
    if _probe != 'tools/md_table_check.py':
        print('FAIL the lexer cross-check produced %r on a plain pipeline, so it '
              'is not actually deciding anything' % (_probe,))
        ok = False
    else:
        print('ok   the LEXER cross-check really answers (not None for '
              'everything), so the arms above are decided TWICE')
    _refused = _lex_subject('python tools/x.py --note "open | tail -1')
    if _refused is not None:
        print('FAIL the lexer did not refuse an unmatched quote, so the reason it '
              'is a cross-check rather than the implementation no longer holds')
        ok = False
    else:
        print('ok   ...and it REFUSES an unmatched double quote, which is exactly '
              'why the regex stays the implementation')

    # The SEPARATOR half had the same defect, because analyse() splits the same
    # text. These two pin it directly rather than through subject_at_risk.
    _p, _s = elements_and_seps('python tools/x.py --m "a;b;c" > /tmp/o 2>&1')
    if _p != ['python tools/x.py --m "a;b;c" > /tmp/o 2>&1']:
        print('FAIL a quoted-semicolon command splits into %r' % (_p,))
        ok = False
    else:
        print('ok   elements(): a command that is ONE element stays one')
    _att, _o, _pp, _n = analyse('python tools/x.py --m "a;b" 2>&1')
    if _att is not True:
        print('FAIL analyse() calls a single quoted-semicolon command '
              'non-attributable')
        ok = False
    else:
        print('ok   analyse(): quoted `;` no longer costs attributability')

    # The owner must be NAMED, not merely "not attributable".
    _att, owner, _p, note = analyse('python tools/x.py 2>&1 | tail -3')
    if owner != 'tail' or 'text filter' not in note:
        print('FAIL the filter owner is not named in the note')
        ok = False
    else:
        print('ok   the owning element is NAMED (%r) and the note says why' % owner)

    # Fails closed on something it cannot tokenise.
    att, _o, _p, note = analyse('   ')
    if att is not None:
        print('FAIL an empty command should not be called attributable')
        ok = False
    else:
        print('ok   an empty command is a refusal, not a pass')

    # ── THE --post OBSERVER'S COULD-NOT-READ LEGS ─────────────────────────
    # Driven against a stubbed _git, because the branch that matters cannot be
    # produced in a healthy clone: a clone with no comparable `origin/main`.
    # Without these arms that branch is code nothing has ever executed, and the
    # defect it replaced was a SILENT return -- the one failure mode that leaves
    # no trace to find later.
    import io
    import json
    global _git
    real_git, real_stdin = _git, sys.stdin

    def stub(answers):
        def fake(*args):
            for prefix, val in answers:
                if args[0] == prefix:
                    return val
            raise AssertionError('unstubbed git call %r' % (args,))
        return fake

    def post_case(label, answers, musts, must_nots=()):
        nonlocal ok
        globals()['_git'] = stub(answers)
        sys.stdin = io.StringIO(json.dumps(
            {'tool_input': {'command': 'g' 'it push'}}))
        buf, sys.stdout = sys.stdout, io.StringIO()
        try:
            post_hook()
            out = sys.stdout.getvalue()
        finally:
            sys.stdout = buf
        bad = ([m for m in musts if m not in out]
               + ['NOT:' + m for m in must_nots if m in out])
        print('%s %-56s %s' % ('ok  ' if not bad else 'FAIL', label,
                               '' if not bad else 'missing %r' % bad))
        if bad:
            ok = False

    post_case('a healthy clone reports all three legs',
              [('log', (0, 'abc1234 a subject')),
               ('rev-list', (0, '4\t0')),
               ('status', (0, 'M a.txt'))],
              ['abc1234', 'ahead 0 / behind 4', '1 uncommitted'])
    post_case('the ahead/behind names the LOCAL ref and that it does not fetch',
              [('log', (0, 'abc1234 a subject')),
               ('rev-list', (0, '0\t1')),
               ('status', (0, ''))],
              ['LOCAL origin/main ref', 'does NOT fetch'])
    post_case('NO origin/main: says so, and still reports HEAD',
              [('log', (0, 'abc1234 a subject')),
               ('rev-list', (128, '')),
               ('status', (0, ''))],
              ['abc1234', 'AHEAD/BEHIND COULD NOT BE READ',
               'Do NOT read this as'],
              must_nots=['ahead 0 /'])
    post_case('git status unreadable: named, not folded into a 0 count',
              [('log', (0, 'abc1234 a subject')),
               ('rev-list', (0, '0\t2')),
               ('status', (1, ''))],
              ['ahead 2 / behind 0', 'UNCOMMITTED COUNT COULD NOT BE READ'],
              must_nots=['0 uncommitted path'])
    post_case('a TOTAL blackout is the only silence',
              [('log', (1, '')), ('rev-list', (1, '')), ('status', (1, ''))],
              [], must_nots=['exit_status_attributable(post)'])

    globals()['_git'], sys.stdin = real_git, real_stdin
    return 0 if ok else 1


# ── TOOLS WHOSE STATUS GETS QUOTED. The hook speaks only about these ────────
# Wired 2026-10-05. A non-attributable status is only a HAZARD when somebody is
# about to quote it as a fact about a checker -- `git log | head` does not
# matter and warning about it would make the hook noise, which is how a
# report-only check stops being read. So the hook fires only when the command
# both (a) returns a status nobody can attribute AND (b) invokes something
# under tools/ or tests/, which is where this platform's verdicts come from.
#
# NARROW ON PURPOSE AND IT MISSES THINGS. `git push` piped through a filter --
# the second of the two real errors -- does NOT match this, because git is not
# under tools/. That is the cost of not being noise, it is stated rather than
# hidden, and the full check is still one command away for any pipeline.
#
# ── THIS LINE SHIPPED WITH A LITERAL BACKSPACE AND COULD NEVER MATCH ────
# First written as '\b(tools|tests)/...\b' through a shell heredoc, which ate
# one backslash. `\b` in a NON-RAW Python string is U+0008 BACKSPACE, not a
# regex word boundary, so the compiled pattern began and ended with \x08 and
# MATCHED NOTHING -- the hook was silent on every command including the one it
# exists for, and silence from a report-only hook is indistinguishable from
# "nothing to report".
#
# CLAUDE.md names this exact shape as one of its six paid-for lessons: "a
# regex that shipped with a literal backspace and could never match". Found
# here by printing repr(pattern) after the hook stayed quiet on a case I had
# just proven should fire -- the same move as reading an exit code off the
# program instead of off the pipeline, which is what this tool is about.
#
# The boundaries are DELETED rather than re-escaped: / and . already bound
# this pattern, and a word boundary beside / was never doing anything.
SUBJECT_DIRS = re.compile(r'(tools|tests)/[^\s|;&]+\.(py|js)')


QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def mask_quoted(text):
    """`text` with single- and double-quoted runs blanked, same length.

    A tool path inside a quoted argument, a commit message, or a heredoc body
    is not an invocation. Length is preserved so nothing downstream shifts.
    """
    return QUOTED.sub(lambda m: ' ' * len(m.group(0)), text)


INTERPRETERS = ('python', 'python3', 'py', 'node', 'sh', 'bash', 'pwsh')


def invoked_tool(piece):
    """The tool path this element RUNS, or '' if it only names one.

    ── THE THIRD AND FOURTH FALSE POSITIVES (2026-10-05) ───────────────────
    Both were found the only way that counts: by the hook firing on my own
    commands, over and over, while I was fixing it.

      3. A TOOL PATH AS A FILE OPERAND OF ANOTHER PROGRAM.
         `grep -n foo tools/x.py | head` was reported as "runs tools/x.py,
         status comes from head". grep runs. x.py is a file being read. The
         path was matched anywhere in the element, so any sed/cat/grep/wc over
         a tool's source tripped it -- which is most of what reading a tool
         looks like. This one fired four times in the session that fixed it.

    So the path must stand in INVOCATION POSITION: the element's first token,
    or the first token after an interpreter and any leading `VAR=value`
    assignments. Everything else is an operand or an argument.
    """
    toks = mask_quoted(piece).split()
    i = 0
    while i < len(toks) and '=' in toks[i] and not toks[i].startswith('-') \
            and '/' not in toks[i].split('=')[0]:
        i += 1                                   # leading env assignments
    if i < len(toks) and os.path.basename(toks[i]).split('.')[0] in INTERPRETERS:
        i += 1
        while i < len(toks) and toks[i].startswith('-'):
            i += 1                               # interpreter flags: -u, -X ...
    if i >= len(toks):
        return ''
    m = SUBJECT_DIRS.fullmatch(toks[i].strip('"\''))
    return m.group(0) if m else ''


STATUS_READ = re.compile(r'\$\?|\$LASTEXITCODE', re.I)
REDIRECTS_OUT = re.compile(r'>\s*\S')


SEQUENCING = (';', '\n', '&&')


def status_was_measured(parts, seps, idx):
    """True when `$?` at `idx` read THE TOOL'S status and not something else's.

    ── FALSE POSITIVE 4, AND THE FIRST FIX FOR IT WAS TOO LOOSE ─────────────
    The note tells you to run `<tool> > /tmp/out 2>&1` and then read `$?` on its
    own line. The hook fired on exactly that -- advising a remedy and then
    flagging the remedy. Reported independently the same day in
    `docs/2026-10-05-exit-status-attributable-false-positive.md` (Fourth), whose
    discriminator is sharper than the one I wrote first and is the one used here:

      THE QUESTION IS NOT WHAT SITS LAST ON THE LINE. It is whether ANYTHING
      EXECUTED between the tool and the `$?` expansion.

    My first fix accepted `$?` ANYWHERE after the tool, which silently blessed
    the real defect in that document's shape 3:

        tool > /tmp/o 2>&1; tail -3 /tmp/o; echo "exit=$?"   # $? is TAIL'S

    That is the same mistake the tool exists to catch, made by its own fix, so
    the read must be in the element IMMEDIATELY after the tool, reached by a
    SEQUENCING separator -- `;`, a newline or `&&`. A pipe is never a
    measurement: `tool | echo $?` runs both at once and `$?` is the pipeline's.

    `$?` is searched on RAW text, not masked text: the ordinary spelling is
    `echo "RC=$?"`, inside double quotes, and masking it first blanked it. My
    own arm used the unquoted `echo RC=$?` and passed while the hook kept firing
    on the quoted form in the same session -- a fixture that agreed with the
    code instead of with the world. Masking decides what RUNS; a status read is
    a mention, and a mention inside quotes still counts.
    """
    if not REDIRECTS_OUT.search(mask_quoted(parts[idx])):
        return False                      # stdout still flows somewhere else
    if idx >= len(seps) or seps[idx] not in SEQUENCING:
        return False
    nxt = idx + 1
    return nxt < len(parts) and bool(STATUS_READ.search(parts[nxt]))


def subject_at_risk(parts, seps=None):
    """The tool whose exit status is actually being discarded, or ''.

    Only the NON-FINAL elements can have their status thrown away -- the last
    element's status IS the command's status. Quotes are masked first so a
    mere mention is never read as an invocation, and the path must stand in
    invocation position rather than merely appear (see `invoked_tool`).
    """
    if len(parts) < 2:
        return ''
    if seps is None:
        # UNKNOWN SEPARATORS MEAN "COULD NOT ESTABLISH A MEASUREMENT", and that
        # resolves towards firing rather than towards silence -- a caller that
        # did not supply separators must not get the suppression for free.
        seps = [''] * len(parts)
    for idx, piece in enumerate(parts[:-1]):
        tool = invoked_tool(piece)
        if not tool:
            continue
        if status_was_measured(parts, seps, idx):
            continue
        return tool
    return ''


def hook():
    """PreToolUse/Bash. NEVER blocks: prints a note or says nothing.

    Fails open on anything it cannot read. A linter about misreading statuses
    must not be the thing that stops a legitimate command.
    """
    import json
    try:
        payload = json.load(sys.stdin)
        cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''
    except Exception:                                             # noqa: BLE001
    # DELIBERATE, and in the SAFE direction: a report-only hook must not
    # be the thing that stops a legitimate command. An unreadable payload
    # means this notice says nothing, never that the command is blocked.
    #
    # THE WORD IS IN THE FIRST LINE ON PURPOSE -- fail_open_scan.py reads a
    # window of ln-6 .. ln+3 around the `except`, so a reason written five
    # lines down is invisible to it. Learned on gh_token.py:296 earlier in
    # the same batch, where exactly that mistake left the site classified
    # DEPENDENCY-shaped through a first attempt at this comment.
        return 0
    if not cmd.strip():
        return 0
    att, owner, parts, note = analyse(cmd)
    if att is not False:
        return 0
    # ── TWO FALSE POSITIVES, BOTH DRIVEN BEFORE BEING FIXED (2026-10-05) ───
    # Reported against H2's hover_log.py invocations carrying comma-separated
    # --source arguments. The commas were NOT the cause -- analyse() classifies
    # those as attributable correctly. Reproducing it found two different
    # defects, both in the SUBJECT half rather than the separator half:
    #
    #   1. THE TOOL PATH WAS MATCHED ANYWHERE IN THE COMMAND TEXT, including
    #      inside a quoted string or a heredoc body. A command whose heredoc
    #      merely MENTIONS tools/hover_log.py, and which happens to end in
    #      `cat something`, was reported as "runs hover_log.py, status comes
    #      from cat". Nothing ran hover_log.py at all. My own test harness
    #      tripped it, which is how it surfaced.
    #
    #   2. THE TOOL IN THE LAST ELEMENT WAS STILL REPORTED. In
    #      `echo start && python tools/hover_log.py --source a,b,c` the tool IS
    #      the last element, so its status IS the command's status and there is
    #      nothing to warn about. That is the H2 shape: a compound command whose
    #      final element is the tool.
    #
    # So the subject is now resolved from the NON-FINAL elements only, with
    # quotes and heredoc bodies masked first. If the only mention of a tool is
    # in the last element, or inside a string, the hook says nothing -- which is
    # correct in both cases and is the direction a report-only notice must err,
    # because a notice that cries wolf stops being read and then the real one is
    # invisible too.
    subj = subject_at_risk(*elements_and_seps(cmd))
    if not subj:
        return 0
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'additionalContext':
            'exit_status_attributable: this command runs `%s` but its exit '
            'status will come from `%s` -- %s. Do NOT quote the status as a '
            'fact about that tool; measure it alone:  <tool> > /tmp/out 2>&1  '
            'then read $? on its own line. (Recorded because that misreading '
            'put a false "EXITS 2 (COULD NOT RUN)" accusation against a '
            'working checker into a standing document on 2026-10-04.)'
            % (subj, owner, note)}}))
    return 0


GIT_WRITE = re.compile(r'\bgit\s+(?:-C\s+\S+\s+)?(commit|push)\b')


def _git(*args):
    """Run git and return (rc, stdout). Never raises."""
    import subprocess
    try:
        r = subprocess.run(('git',) + args, cwd=REPO_ROOT, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=30)
        return r.returncode, (r.stdout or '').strip()
    except Exception:                                             # noqa: BLE001
        # DELIBERATE, and in the safe direction: if git cannot be read this
        # observer says nothing. It must never be the reason a command is
        # reported as having failed.
        return 1, ''


def _ref_age():
    """', last fetched Nm ago' for origin/main, or '' if that cannot be read.

    Reads the newest of FETCH_HEAD and the packed/loose ref, because a fetch
    touches FETCH_HEAD even when the ref does not move. Returns '' rather than a
    guess: an invented age is worse than no age, which is the whole subject here.
    """
    import time
    newest = None
    for rel in ('FETCH_HEAD', 'refs/remotes/origin/main', 'packed-refs'):
        p = os.path.join(REPO_ROOT, '.git', rel)
        try:
            m = os.path.getmtime(p)
        except OSError:
            continue
        if newest is None or m > newest:
            newest = m
    if newest is None:
        return ''
    mins = (time.time() - newest) / 60.0
    if mins < 1:
        return ', last fetched under a minute ago'
    if mins < 90:
        return ', last fetched %dm ago' % int(mins)
    return ', LAST FETCHED %.1fh AGO -- treat the behind-count as unknown' % (
        mins / 60.0)


def post_hook():
    """PostToolUse/Bash. After a `git commit` or `git push`, report the
    OBSERVED repository state instead of letting the message be inferred from.

    ── WHY THIS EXISTS: FOUR WRONG-SUBJECT READS IN TWO DAYS ────────────────
    The attribution notice above covers the PIPELINE half of the pattern. It
    cannot cover the other half, and two of the four instances were that half:

      * A NO-OP push printed "could not tell what is being pushed -- no ref
        lines on stdin" and it was read as a refusal OF MY PUSH. There was
        nothing to send; `rev-list --left-right --count` answered `0 0`.
      * A `git commit -F` exited 128 on a MISSING MESSAGE FILE, and the push
        gate's unrelated refusal -- printed in the same block -- was read as
        the cause. No commit was created.

    BOTH WERE DECIDABLE BY OBSERVATION AND NEITHER WAS OBSERVED. Did HEAD move?
    Is the branch ahead? That is two git reads and no inference, and this hook
    does them every time rather than when somebody remembers to.

    IT REPORTS STATE, NEVER A VERDICT. It does not say the command failed or
    succeeded -- it says what is true now, because the failure of all four
    instances was substituting a plausible story for a cheap measurement.
    """
    import json
    try:
        payload = json.load(sys.stdin)
        cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''
    except Exception:                                             # noqa: BLE001
        # DELIBERATE and safe: an unreadable payload means silence, never a
        # claim about the repository.
        return 0
    if not GIT_WRITE.search(mask_quoted(cmd)):
        return 0

    rc_head, head = _git('log', '--format=%h %s', '-1')
    rc_ab, ab = _git('rev-list', '--left-right', '--count', 'origin/main...HEAD')
    rc_st, st = _git('status', '--porcelain')

    # EVERY LEG REPORTS ITS OWN OUTCOME, AND "COULD NOT READ" IS SAID OUT LOUD.
    # This was `if rc_head != 0 or rc_ab != 0: return 0` -- a silent skip, and
    # the shape is the one this whole file exists to kill: a clone with no
    # `origin/main` ref makes rev-list exit non-zero, the observer vanishes, and
    # nothing downstream can tell that from "nothing worth saying". PR 1.11: a
    # check that could not run must name what it could not read and still report
    # what it could. Only a total blackout -- no leg readable -- is silence,
    # because then there is no observation to offer.
    if rc_head != 0 and rc_ab != 0 and rc_st != 0:
        return 0

    fields = ab.split()
    bits = []
    bits.append('HEAD is now %s' % head[:72] if rc_head == 0 else
                'HEAD COULD NOT BE READ (git log exited %d)' % rc_head)
    if rc_ab == 0 and len(fields) == 2:
        # ── THE AGE OF THE REF IS PART OF THE OBSERVATION (found by this hook
        # misleading me, within an hour of being wired) ──────────────────────
        # `origin/main` is a LOCAL ref, only as fresh as the last fetch. On the
        # first real push after wiring, this printed "ahead 1 / behind 0" and the
        # push was refused because origin had moved SIX commits -- the number was
        # right about the ref and wrong about the remote. An observer that
        # presents a stale reading as OBSERVED state is discipline 8 exactly:
        # nothing announces the day a measurement stops measuring. It does NOT
        # fetch -- a report-only hook must not touch the network or mutate refs --
        # so it says WHAT it compared against and HOW OLD that is, and the
        # reader decides.
        bits.append('ahead %s / behind %s of the LOCAL origin/main ref%s (this '
                    'hook does NOT fetch -- a fresh behind-count needs one)'
                    % (fields[1], fields[0], _ref_age()))
    else:
        bits.append('AHEAD/BEHIND COULD NOT BE READ -- no comparable '
                    'origin/main (rev-list exited %d, output %r). Do NOT read '
                    'this as "nothing to push"' % (rc_ab, ab))
    if rc_st == 0:
        bits.append('%d uncommitted path(s)'
                    % len([l for l in st.split('\n') if l.strip()]))
    else:
        bits.append('UNCOMMITTED COUNT COULD NOT BE READ (git status exited '
                    '%d)' % rc_st)
    note = ('exit_status_attributable(post): OBSERVED state after a git '
            'commit/push -- ' + '; '.join(bits) + '. '
            'Read THIS, not the message, to decide whether the commit or push '
            'happened. Two of four wrong-subject reads on 2026-10-04/05 were '
            'exactly this: a no-op push whose gate message was read as a '
            'refusal, and a commit that exited 128 on a missing message file '
            'while an unrelated gate refusal printed in the same block.')
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PostToolUse', 'additionalContext': note}}))
    return 0


# ════════════════════════════════════════════════════════════════════════════
# SCRUTINY CLASSIFIER -- does this diff change the thing that checks the work?
# Added 2026-10-06 (cc). Design note: docs/2026-10-06-cc-batch-11-design-notes.md
# ════════════════════════════════════════════════════════════════════════════
#
# WHY IN THIS FILE RATHER THAN A NEW ONE. This file already owns the question
# "read a command or a diff and say what it REALLY does" and is already in
# `report_only_checks.REGISTRY`, so a flag it emits has an existing cadence. A
# third program parsing a push's outgoing diff was rejected on a measured cost:
# `84eb61ea` records a conflict pre-flight that duplicated an existing push
# gate, and the batch-10 inventory rejected a parallel re-seater on the same
# ground. Two diff parsers drift, and the drift is silent because both keep
# passing.
#
# WHAT IT ANSWERS, and it is narrow on purpose: AN AGENT MUST NOT QUIETLY
# WEAKEN THE THING THAT CHECKS ITS OWN WORK. The gate's 15 numbered checks all
# ask "is this push's CONTENT wrong". None asks "is this push's content a
# change to the thing that answers that question". Check 13 comes closest and
# opens a review obligation on Tier A RESOURCE code -- a gate check is not a
# Tier A resource, so a diff deleting a gate check opens nothing.
#
# IT NEVER BLOCKS, and that is a design constraint rather than caution. A
# control that could block its own author's gate edits could not be installed:
# this very build touches `tools/sairn_push_gate_hook.py`, so the control flags
# its own landing commit. Flag, record, hand off -- the human read is the
# control, and the ledger is what makes the hand-off possible.

CRITERIA_VERSION_SCRUTINY = '2026-10-06.1'

SCRUTINY_LEDGER = 'docs/scrutiny-flags.json'

# Path classes. ORDER MATTERS: the first match wins, so the named-tool class
# sits above the broad `tools/` one it would otherwise be swallowed by.
SELF_CHECKING = (
    ('push-gate logic', (
        'tools/sairn_push_gate_hook.py',
        'tools/exit_status_attributable.py',
        'tools/report_only_checks.py',
        'tools/run_all_tests.py',
        'tools/tier_a_review_gate.py',
        'tools/hook_integrity_check.py',
        'tools/sairn_claim_hook.py',
    )),
    ('CI / hook configuration', (
        '.github/workflows/',
        '.githooks/',
        '.claude/settings.json',
        '.claude/settings.local.json',
    )),
    ('test file', (
        'tests/',
    )),
)

# A `.test.js` anywhere counts as a test file; `api/` holds its own.
TEST_SUFFIXES = ('.test.js', '_probe.py', '_fault_probe.py',
                 '_mutation_control.js')

# Lines whose REMOVAL is the shape worth a second read. Deliberately
# syntactic: this file's whole premise is that a decidable question beats an
# intent inference.
_ASSERTION_HINTS = (
    'assert', 'ok(', 'expect(', 'strictEqual', 'notStrictEqual', 'deepEqual',
    'throws(', 'rejects(', 'case(', 'arm(', 'deny(', 'refuse', 'COULD_NOT_RUN',
    'sys.exit(1', 'sys.exit(2', 'fail(',
)
# Bounds and exemptions: a RISE or an ADDITION here is the weakening shape.
_BOUND_HINTS = ('timeout', 'max_', '--max', 'threshold', 'ceiling', 'limit',
                'RUNS_PER_', 'STALE_AFTER')
_EXEMPTION_HINTS = ('skip', 'xfail', 'exempt', 'allowlist', 'whitelist',
                    'KNOWN_RED', 'known-red', 'GRANDFATHER', 'ignore')

SCRUTINY_BLIND_SPOTS = (
    'An assertion that still EXISTS and no longer tests anything. The count '
    'holds, the sense is inverted, and nothing here can see it.',
    'A fixture quietly made easier. The arms all still run and all still pass.',
    'A weakening spread across two pushes, where neither diff alone matches a '
    'shape. This reads one outgoing range at a time.',
    'Intent. It reports SHAPE. A deleted arm may be a correct deletion of a '
    'wrong arm -- which is exactly why this flags and does not block.',
    # ── SCRUBBER ITEM 24, NAMED RATHER THAN DISCOVERED ─────────────────────
    # The hints are SUBSTRINGS over diff lines, so they cannot tell CODE from
    # PROSE ABOUT CODE. A docstring paragraph in a test file that says the word
    # "assert" counts as an assertion line: delete that paragraph and this
    # reports "assertions NET REMOVED" on a comment-only edit. The scrubber's
    # own rule is to match structure before prose, and this layer deliberately
    # does not -- an AST pass would be blind to .js, .sh and .json in the same
    # classes, so the limit is DECLARED instead of engineered away.
    'CODE versus PROSE ABOUT CODE, and this is MEASURED rather than feared. '
    'On its own landing commit -- the first real diff it ever saw -- the '
    'WEAKENING level was 3 of 3 FALSE: the word "ignored" inside a probe '
    'assertion label, a comment saying "silent skip", and this file\'s own '
    '_BOUND_HINTS tuple. Dropping comment lines took it to 2 of 3, and BOTH '
    'SURVIVORS ARE STILL FALSE -- prose inside a STRING LITERAL, which is real '
    'code by every syntactic test. SO THE WEAKENING LEVEL IS A TRIAGE PROMPT '
    'AND NOT A FINDING, on an n of 1 real push. It is left matching rather '
    'than narrowed, per scrubber item 24: narrowing clears the known instance '
    'and fails silently on the next phrasing, and in a detector a false '
    'negative is invisible where a false positive is loud and gets read. The '
    'rate on a larger sample is still unmeasured.',
    # ── SCRUBBER ITEM 24 PART 2: the residue must be visible ───────────────
    # "Did not match a shape" is NOT "safe", so a path in a self-checking
    # class with no shape match is still reported, at level CHANGE. Nothing
    # that reaches this classifier is silently dropped. What IS dropped is a
    # path in no class at all, and that is the real coverage question:
    'COVERAGE OF THE CLASS LIST ITSELF. A path in no SELF_CHECKING class is '
    'not examined and is not reported. The push-gate-logic class is a NAMED '
    'LIST of seven files, not a glob -- a new checker nobody adds to it is '
    'invisible here, which is the same staleness this platform keeps paying '
    'for one level up.',
)


def scrutiny_class(path):
    """Which self-checking class this path belongs to, or None.

    `None` is not "safe"; it is "not in a class this control knows about".
    """
    p = str(path or '').replace(chr(92), '/')
    for label, prefixes in SELF_CHECKING:
        for pre in prefixes:
            if p == pre or p.startswith(pre):
                return label
    if p.endswith(TEST_SUFFIXES):
        return 'test file'
    return None


def weakening_shapes(diff_body):
    """Shapes in one file's unified diff that read as a WEAKENING.

    Returns a list of (shape, detail) and never a verdict. An empty list means
    "no shape matched", which is a different statement from "this edit is
    fine" -- see SCRUTINY_BLIND_SPOTS.
    """
    # ── COMMENT LINES ARE DROPPED, AND THE FIRST REAL PUSH IS WHY ──────────
    # MEASURED on this classifier's own landing commit, which is the first
    # real diff it ever saw: 3 of 3 WEAKENING flags were PROSE, not code. One
    # matched the word "ignored" inside a probe's assertion label; one matched
    # a comment containing "silent skip"; one matched this file's own
    # `_BOUND_HINTS` declaration. **A 100% false-positive rate on the WEAKENING
    # level at first contact**, which would have made the loud half of this
    # control worthless by its third push.
    #
    # The blind spot was DECLARED before the push (see SCRUTINY_BLIND_SPOTS)
    # and declaring it was not sufficient -- it fired immediately and at full
    # strength. Scrubber item 24's rule is to match STRUCTURE before prose, so
    # a line whose stripped form opens a comment is not a code line and does
    # not count.
    #
    # WHAT THIS STILL CANNOT DO is see inside a docstring or a multi-line
    # string: `_BOUND_HINTS`'s own tuple of words is real code by every
    # syntactic test and is left matching. That residual is measured below
    # rather than argued away, and an AST pass is not the answer -- the same
    # classifier has to read .js, .sh and .json in the same path classes.
    _COMMENT_OPENERS = ('#', '//', '*', '/*', '--')

    def _is_comment(s):
        t = s.strip()
        return bool(t) and t.startswith(_COMMENT_OPENERS)

    added, removed = [], []
    for line in (diff_body or '').split('\n'):
        if line.startswith('+++') or line.startswith('---'):
            continue
        if line.startswith('+') and not _is_comment(line[1:]):
            added.append(line[1:])
        elif line.startswith('-') and not _is_comment(line[1:]):
            removed.append(line[1:])

    def hits(lines, hints):
        return [l.strip() for l in lines
                if any(h in l for h in hints)]

    out = []
    a_as, r_as = hits(added, _ASSERTION_HINTS), hits(removed, _ASSERTION_HINTS)
    if len(r_as) > len(a_as):
        out.append(('assertions NET REMOVED',
                    '%d removed, %d added; first removed: %s'
                    % (len(r_as), len(a_as), (r_as[0] or '')[:80])))
    a_b, r_b = hits(added, _BOUND_HINTS), hits(removed, _BOUND_HINTS)
    if a_b and r_b:
        out.append(('a bound or threshold CHANGED',
                    'was: %s  now: %s'
                    % ((r_b[0] or '')[:60], (a_b[0] or '')[:60])))
    elif a_b and not r_b:
        out.append(('a bound or threshold ADDED', (a_b[0] or '')[:80]))
    a_e = hits(added, _EXEMPTION_HINTS)
    if len(a_e) > len(hits(removed, _EXEMPTION_HINTS)):
        out.append(('a skip / exemption / allowlist entry ADDED',
                    (a_e[0] or '')[:80]))
    r_d = [l for l in removed if 'deny(' in l]
    a_d = [l for l in added if 'deny(' in l]
    if len(r_d) > len(a_d):
        out.append(('a deny() was REMOVED',
                    '%d removed, %d added' % (len(r_d), len(a_d))))
    return out


def scrutiny_flags(per_file_diffs):
    """The flags for one outgoing range.

    `per_file_diffs` is {path: unified diff body for that path}. Returns a list
    of dicts, highest-level first: WEAKENING before CHANGE, because "a test
    file moved" and "an assertion was deleted" are not the same claim and
    collapsing them is how a non-blocking control becomes noise.
    """
    flags = []
    for path in sorted(per_file_diffs):
        cls = scrutiny_class(path)
        if not cls:
            continue
        # ── AN EMPTY DIFF IS NOT A CHANGE (2026-10-08) ─────────────────────
        # Without this, a path whose diff body is empty still got a row at
        # level CHANGE -- a flag asserting a commit touched a file it did not
        # touch, invented from nothing.
        #
        # IT WAS INVISIBLE TO THE ORIGINAL CALLER AND FATAL TO THE NEW ONE.
        # The range caller only ever passed paths it had already selected as
        # changed, so every diff had content. The per-commit caller added the
        # same day passes ALL in-class paths per commit, and most are empty
        # for any given commit. MEASURED ON A REAL PUSH, not a probe: 20 rows
        # written across 4 commits and 5 paths, of which 15 named a
        # (commit, path) pair with no diff between them. Only 5 were real --
        # one per commit.
        #
        # Guarded HERE as well as in the caller, because a row invented from
        # an empty diff is wrong from every caller, and the caller is the
        # thing a future change is likeliest to get wrong again.
        if not (per_file_diffs[path] or '').strip():
            continue
        shapes = weakening_shapes(per_file_diffs[path])
        flags.append({
            'path': path,
            'class': cls,
            'level': 'WEAKENING' if shapes else 'CHANGE',
            'shapes': [{'shape': s, 'detail': d} for s, d in shapes],
        })
    flags.sort(key=lambda f: (f['level'] != 'WEAKENING', f['path']))
    return flags


def scrutiny_render(flags, sha=''):
    """The stderr block. Names the file and the reason, never a bare count."""
    if not flags:
        return ''
    weak = [f for f in flags if f['level'] == 'WEAKENING']
    out = []
    out.append('EXTRA SCRUTINY -- this push changes things that CHECK the '
               'work (criteria %s)' % CRITERIA_VERSION_SCRUTINY)
    out.append('  %d path(s) in a self-checking class; %d match a WEAKENING '
               'shape.' % (len(flags), len(weak)))
    out.append('  NOT A REFUSAL. An agent must not quietly weaken the thing '
               'that checks its own')
    out.append('  work -- so this is written down and handed to a reviewer '
               'rather than blocked,')
    out.append('  because a control that could block gate edits could never '
               'have been installed.')
    out.append('')
    for f in flags:
        out.append('  [%-9s] %-58s %s' % (f['level'], f['path'], f['class']))
        for s in f['shapes']:
            out.append('              %s -- %s' % (s['shape'], s['detail']))
    out.append('')
    out.append('  RECORDED IN %s under %s, so a review obligation can pick it '
               'up.' % (SCRUTINY_LEDGER, sha[:12] or '<no sha>'))
    out.append('  WHAT THIS CANNOT SEE:')
    for b in SCRUTINY_BLIND_SPOTS:
        out.append('    - %s' % b)
    return '\n'.join(out)


def scrutiny_record(repo, sha, flags):
    """Append to the ledger. Returns (written, note) and NEVER raises.

    APPEND-ONLY WITH A UNION-BY-IDENTITY MERGE POLICY, identity `(sha, path)`.
    That is the shape `docs/tier-a-reviews.json` already uses and that
    `tools/sairn_rebase_resolve.py` already knows how to merge, which matters
    because four clones push into one branch and a hand-merged ledger is a
    write race with extra steps.

    KEYED BY COMMIT, NOT BY PUSH ATTEMPT, so a refused-and-retried push does
    not write the same flag three times. A rebase that rewrites the commit
    writes a new entry -- and `.githooks/post-rewrite` plus
    `tools/doc_sha_reseat.py` exist for exactly that, so this ledger joins the
    set the rewrite map already repairs rather than inventing its own.
    """
    if not flags:
        return False, 'no flags'
    # ── THE KEY MUST BE A SHA, CHECKED HERE AND NOT ONLY AT THE CALLER ─────
    # The caller resolves it now, and this is the second place because the
    # first version trusted whatever it was handed and recorded `"sha":
    # "main"` from the gate's prepush `tip`. The ledger's identity is
    # (sha, path): a ref NAME breaks dedup silently, so every push re-adds
    # the same rows, and no rewrite map can re-seat a key that is not a
    # commit. Refusing is the only safe answer -- an entry keyed by a
    # non-sha LOOKS like a record.
    if not re.fullmatch(r'[0-9a-f]{7,40}', str(sha or '')):
        return False, ('refusing to record under %r -- not a sha. The '
                       'ledger identity is (sha, path) and a ref name '
                       'breaks it silently.' % (sha,))
    path = os.path.join(repo, SCRUTINY_LEDGER)
    base = {
        '_what_this_is':
            'Diffs that changed something which CHECKS the work -- test files, '
            'CI/hook configuration, or push-gate logic. A flag is NOT a '
            'finding and NOT a refusal. It is a record that an agent edited '
            'its own checker, written so a reviewer can ask why without '
            'having to notice it first.',
        '_what_it_does_NOT_claim':
            'That the edit was wrong, or that an unflagged edit was fine. See '
            'blind_spots: an assertion that still exists and tests nothing is '
            'invisible here.',
        'blind_spots': list(SCRUTINY_BLIND_SPOTS),
        'merge_policy': {
            'strategy': 'union-by-identity',
            'records_key': 'flags',
            'identity': ['sha', 'path'],
        },
        'criteria_version': CRITERIA_VERSION_SCRUTINY,
        'flags': [],
    }
    try:
        if os.path.isfile(path):
            cur = json.load(io.open(path, encoding='utf-8'))
            if not isinstance(cur, dict) or 'flags' not in cur:
                return False, ('%s exists and is not this ledger -- NOT '
                               'overwritten' % SCRUTINY_LEDGER)
            base = cur
                                                    # keep the hand-written half
            base['criteria_version'] = CRITERIA_VERSION_SCRUTINY
            base['blind_spots'] = list(SCRUTINY_BLIND_SPOTS)
    except Exception as e:                                     # noqa: BLE001
        return False, 'could not read %s: %s' % (SCRUTINY_LEDGER, e)

    have = set((f.get('sha'), f.get('path')) for f in base['flags'])
    added = 0
    for f in flags:
        key = (sha, f['path'])
        if key in have:
            continue
        rec = dict(f)
        rec['sha'] = sha
        rec['criteria_version'] = CRITERIA_VERSION_SCRUTINY
        base['flags'].append(rec)
        have.add(key)
        added += 1
    if not added:
        return False, 'every flag for %s was already recorded' % sha[:12]
    base['flags'].sort(key=lambda f: (f.get('sha', ''), f.get('path', '')))
    try:
        # THE DIRECTORY IS CREATED RATHER THAN ASSUMED. The first version did
        # not, and the probe's arm D failed in a scratch repo with no `docs/`
        # -- the flags printed to stderr and the ledger silently did not
        # appear. In THIS repo `docs/` always exists, so the defect would have
        # shipped invisible and surfaced only in whatever clone or CI checkout
        # lacked it. A ledger whose whole purpose is that somebody can read it
        # later does not get to depend on a directory existing.
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        io.open(tmp, 'w', encoding='utf-8', newline='').write(
            json.dumps(base, indent=1, sort_keys=False) + '\n')
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp, path)
    except Exception as e:                                     # noqa: BLE001
        return False, 'could not write %s: %s' % (SCRUTINY_LEDGER, e)
    return True, '%d flag(s) recorded under %s' % (added, sha[:12])


def scrutiny_selftest():
    """Planted diffs, both directions. Reads no real file.

    EVERY ARM IS PAIRED. A control that only proves "the weakening is caught"
    cannot tell a working classifier from one that flags everything, which is
    the failure the ninth cross-domain discipline is about.
    """
    ok, n = [], 0

    def case(label, got, want):
        nonlocal n
        n += 1
        good = got == want
        ok.append(good)
        print('%s %-72s' % ('ok  ' if good else 'FAIL', label))
        if not good:
            print('       want %r' % (want,))
            print('       got  %r' % (got,))

    # ── the path classifier, both directions ────────────────────────────────
    case('tests/ is a test file',
         scrutiny_class('tests/run_x_probe.py'), 'test file')
    case('api/_lib/x.test.js is a test file by SUFFIX, not by directory',
         scrutiny_class('api/_lib/x.test.js'), 'test file')
    case('.githooks/pre-push is CI / hook configuration',
         scrutiny_class('.githooks/pre-push'), 'CI / hook configuration')
    case('.claude/settings.json is CI / hook configuration',
         scrutiny_class('.claude/settings.json'), 'CI / hook configuration')
    case('the push gate is push-gate logic, NOT swallowed by a tools/ class',
         scrutiny_class('tools/sairn_push_gate_hook.py'), 'push-gate logic')
    case('THIS file is push-gate logic too -- it must flag its own edits',
         scrutiny_class('tools/exit_status_attributable.py'),
         'push-gate logic')
    case('an ordinary app file is in NO class',
         scrutiny_class('stonedesk.html'), None)
    case('an ordinary tool is in NO class -- the list is named, not a glob',
         scrutiny_class('tools/dead_rule_sweep.py'), None)
    case('a backslash path is normalised before matching',
         scrutiny_class('tests' + chr(92) + 'run_x_probe.py'), 'test file')

    # ── the weakening shapes, each with its NEGATIVE control ───────────────
    d_removed = '-    assert x == 1\n-    assert y == 2\n+    pass\n'
    case('two assertions removed and none added is NET REMOVED',
         [s for s, _ in weakening_shapes(d_removed)],
         ['assertions NET REMOVED'])
    d_added = '+    assert x == 1\n+    assert y == 2\n'
    case('CONTROL: assertions ADDED is not a weakening shape',
         weakening_shapes(d_added), [])
    d_even = '-    assert x == 1\n+    assert x == 2\n'
    case('CONTROL: one assertion rewritten is not NET REMOVED',
         weakening_shapes(d_even), [])
    d_bound = '-    timeout = 60\n+    timeout = 600\n'
    case('a bound changed is flagged',
         [s for s, _ in weakening_shapes(d_bound)],
         ['a bound or threshold CHANGED'])
    d_skip = '+    KNOWN_RED.append("tests/x.py")\n'
    case('an allowlist entry added is flagged',
         [s for s, _ in weakening_shapes(d_skip)],
         ['a skip / exemption / allowlist entry ADDED'])
    d_deny = '-        deny(reason)\n+        report(reason)\n'
    case('a deny() removed is flagged',
         'a deny() was REMOVED' in [s for s, _ in weakening_shapes(d_deny)],
         True)
    case('CONTROL: an empty diff matches no shape',
         weakening_shapes(''), [])
    case('CONTROL: a diff of only context lines matches no shape',
         weakening_shapes('     assert x == 1\n     assert y == 2\n'), [])

    # ── THE FALSE POSITIVE MEASURED ON THE FIRST REAL PUSH, BOTH WAYS ──────
    # 3 of 3 WEAKENING flags on this classifier's own landing commit were
    # PROSE. These arms pin the filter that fixed it AND the arm that proves
    # the filter did not simply disarm the detector -- without that last one,
    # "no false positives" and "finds nothing" are the same measurement.
    case('CONTROL: a removed COMMENT mentioning assert is NOT a weakening',
         weakening_shapes('-    # we assert x here\n-    # and assert y\n'), [])
    case('CONTROL: a removed // comment naming a threshold is not a bound '
         'change',
         weakening_shapes('-    // raise the timeout threshold\n'), [])
    case('CONTROL: an added comment containing the word skip is not an '
         'exemption',
         weakening_shapes('+    # a silent skip would be PR 1.11\n'), [])
    case('...and REAL code with those same words STILL fires, so the comment '
         'filter did not disarm the detector',
         [s for s, _ in weakening_shapes('-    assert x == 1\n-    assert y\n')],
         ['assertions NET REMOVED'])

    # ── the aggregate, and the ordering contract ───────────────────────────
    flags = scrutiny_flags({
        'stonedesk.html': '+<div>\n',
        'tests/run_a_probe.py': '+    assert z\n',
        'tests/run_b_probe.py': d_removed,
    })
    case('an out-of-class path produces NO flag',
         [f['path'] for f in flags],
         ['tests/run_b_probe.py', 'tests/run_a_probe.py'])
    case('WEAKENING sorts before CHANGE',
         [f['level'] for f in flags], ['WEAKENING', 'CHANGE'])
    case('the render names the file and the shape, never a bare count',
         'run_b_probe.py' in scrutiny_render(flags, 'deadbeef1234')
         and 'assertions NET REMOVED' in scrutiny_render(flags, 'x'), True)
    case('the render says NOT A REFUSAL in its own words',
         'NOT A REFUSAL' in scrutiny_render(flags, 'x'), True)
    case('the render states its blind spots rather than implying coverage',
         'WHAT THIS CANNOT SEE' in scrutiny_render(flags, 'x'), True)
    case('CONTROL: no flags renders to the empty string, so a clean push '
         'prints nothing', scrutiny_render([], 'x'), '')

    # ── THE LEDGER KEY, FOUND BY READING THE LEDGER AND NOT THE CODE ───────
    import tempfile as _tf
    _d = _tf.mkdtemp(prefix='scr_key_')
    _f = [{'path': 'tests/x.py', 'class': 'test file', 'level': 'CHANGE',
           'shapes': []}]
    _w, _n = scrutiny_record(_d, 'main', _f)
    case('a REF NAME is refused as a ledger key -- the gate hands `tip`, '
         'which is a ref name in prepush mode', _w, False)
    case('...and the refusal says why rather than going quiet',
         'not a sha' in _n, True)
    _w2, _n2 = scrutiny_record(_d, 'deadbeefcafe', _f)
    case('CONTROL: a real sha IS accepted, so the guard did not simply '
         'refuse everything', _w2, True)
    _w3, _n3 = scrutiny_record(_d, 'deadbeefcafe', _f)
    case('...and the SAME sha twice adds nothing, which is the dedup the '
         'ref-name key was silently breaking', _w3, False)
    import shutil as _sh
    _sh.rmtree(_d, ignore_errors=True)

    passed = sum(1 for x in ok if x)
    print('\nscrutiny selftest: %d passed, %d failed, of %d arms'
          % (passed, n - passed, n))
    return 0 if passed == n else 1


def main(argv):
    if '--scrutiny-selftest' in argv:
        return scrutiny_selftest()
    if '--post' in argv:
        return post_hook()
    if '--hook' in argv:
        return hook()
    if '--selftest' in argv:
        return selftest()
    if '--stdin' in argv:
        cmd = sys.stdin.read()
    else:
        pos = [a for a in argv if not a.startswith('--')]
        if not pos:
            print(__doc__.strip().split('CLI:')[-1].strip())
            return COULD_NOT_RUN
        cmd = pos[0]

    att, owner, parts, note = analyse(cmd)
    if att is None:
        print('COULD NOT RUN -- this is not a pass.')
        print('  %s' % note)
        return COULD_NOT_RUN

    print('EXIT STATUS ATTRIBUTION')
    print('  elements: %d' % len(parts))
    for p in parts:
        print('    %s' % p[:140])
    print()
    if att:
        print('  ATTRIBUTABLE. The status belongs to `%s`, so quoting it as a '
              'fact about that program is sound.' % owner)
        return 0
    print('  NOT ATTRIBUTABLE -- %s.' % note)
    print()
    print('  So do NOT quote this exit code as a fact about any program you '
          'named earlier in the line. Measure the one you mean:')
    print('    <that program> > /tmp/out.txt 2>&1')
    print('    echo $?          # on its own line')
    print()
    print('  THIS IS A LIST TO READ, NOT A VERDICT. Piping into a filter to '
          'keep output short is correct and usual; the hazard is only in '
          'ATTRIBUTING the resulting status.')
    return 1 if '--strict' in argv else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
