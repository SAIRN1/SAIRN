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
    def subj(label, cmd, want):
        nonlocal ok
        p_only = elements(cmd)
        p, s = elements_and_seps(cmd)
        if p != p_only:
            print('FAIL elements() and elements_and_seps() disagree on %r' % cmd)
            ok = False
        got = subject_at_risk(p, s)
        good = (bool(got) is want)
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


def main(argv):
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
