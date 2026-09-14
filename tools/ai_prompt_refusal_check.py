#!/usr/bin/env python
"""ai_prompt_refusal_check.py -- an app's own named refusal/rule constant is absent from one of its AI call sites

    python tools/ai_prompt_refusal_check.py                 # sweep
    python tools/ai_prompt_refusal_check.py --fixtures      # the blind lock alone
    python tools/ai_prompt_refusal_check.py <file>...       # scope to a file list

Item 8, sub-item 7 of docs/2026-09-13-ai-red-teaming-scoping.md: *"stated
refusals hold -- SAIRNfreedom refusing VA claim-strategy questions is a written
requirement, and nothing tests it."* This is the half of that which needs NO
MODEL CALL: does the refusal text this app wrote for itself actually ship in the
system prompt of every AI call site, or only some of them.

── WHAT THIS CHECKS, AND THE LIMIT SAID FIRST ──────────────────────────────
It checks the PRESENCE OF TEXT. It cannot tell you the model obeys it. Whether
Claude honours a refusal is a question only a model call answers, and that half
is DEFERRED by Michael's recorded decision (garak, separate approval, dry-run
cost first). So a CLEAN run here means "every site carries the words", never
"the refusal holds". Those are different claims and this tool only makes the
first.

── THE SIGNATURE IS STRUCTURAL, NOT A TOPIC GUESS ──────────────────────────
The tempting rule is "does this site's prompt cover the same SUBJECT as the
constant". That is topic inference, it is a design opinion on every prompt in
the tree, and `tools/shape_antipattern_check.py` already recorded what happens
to those: switched off inside a day. So the rule infers nothing.

  R1  the app DEFINES at least one `*_RULE` / `*_REFUSAL` constant, and an AI
      call site in that same file builds its system prompt without referencing
      ANY of them.

  R2  an R1 site that ALSO writes its own `HARD RULES` / `CRITICAL RULE` block
      inline. This is the finding worth having, because it is the one that LOOKS
      covered: the site did not forget rules, it wrote a second set beside the
      named one, and nothing keeps the two in step. Measured on sairnlaw: the
      constant forbids case citations outright, while one site's hand-written
      rule PERMITS them if real -- materially different rules for one app, and
      no record that the divergence is intentional.

R2 is reported as a strictly more serious subset of R1, not as a separate count,
because one site is one site -- two numbers over one population is the
double-count this repo's own uncertainty tables warn about.

── AN APP WITH NO NAMED CONSTANT IS NOT A FINDING ──────────────────────────
Most apps have none, and "you should have written a refusal constant" is exactly
the design opinion above. The rule fires only where the app has already made the
commitment itself -- then asks whether it kept it everywhere. That keeps the
denominator honest: 2 of 22 apps define one, and those 2 are all this can speak
about.

── FOUR FALSE POSITIVES FOUND WHILE CALIBRATING, EACH PINNED AS A FIXTURE ──
Every one of these was hit for real against this tree, not imagined:

  1. `var system=document.getElementById('dx-system').value` in sairnvet is a
     BODY-SYSTEM filter on a diagnoses search. "System" is overloaded --
     anatomical system, HVAC system, "5-tab system" -- so a rule keyed on the
     variable name flags a `<select>` that has nothing to do with AI. Keyed on
     the `system:` PROPERTY of an object that also carries `messages`, which is
     the shape every real call site has and no filter does.
  2. `// ... 400 INVALID_COVERAGE_RULE` in sairndental is an ERROR CODE in a
     comment. It matched the constant-name pattern and would have invented a
     constant the app does not define. Comment-stripped both when finding
     constants and when reading sites.
  3. `<!-- Safety 5-tab system: Training / Daily Checklist -->` in stonedesk --
     same comment problem from the other direction.
  4. sairnfreedom's bottle-fullness site omits VA_CLAIM_REFUSAL, and that
     omission is DEFENSIBLE: an image in, a two-key JSON object out, no channel
     for a VA claim-strategy question to arrive on or a prose answer to leave
     by. It is still REPORTED -- suppressing it would make the tool decide the
     triage -- but the report says which sites look like this one, so a reader
     spends their attention on the rest.

── WHY IT IS REPORT-ONLY AND NAMES NO VERDICT ──────────────────────────────
A divergence is not automatically a bug. sairnlaw's adversary simulator plausibly
NEEDS to discuss citations, so forbidding them there could break the feature.
The tool states the divergence and who owns it; whether to converge the two
rules is a judgement with an owner, which is the same standing rule the
quarantine ledger and the propagation gate both carry.

Exit 0 clean, 1 finding, 2 could not run.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402
from checker_kit import tracked, strip_comments, finish                # noqa: E402

# ── THE BLIND LOCK ──────────────────────────────────────────────────────────
# (label, filename, source, must_flag). Judged in ISOLATION, before any real
# file is opened -- a lock that rides beside live data can be satisfied by the
# data.
#
# WRITTEN BEFORE THE RULE, AND NO FIXTURE HERE WAS EVER CHANGED TO MATCH TOOL
# OUTPUT. Convention 1 requires saying which kind of correction was made: the
# answer for this file is NONE -- every fixture below classified as written on
# the first run of the finished rule. What DID change during calibration is the
# RULE, four times, each time because a real false positive on this tree named
# the flaw (see the four pinned NOT-flagged cases and the module docstring).
FIXTURES = [
    # ── MUST FLAG ──────────────────────────────────────────────────────────
    ('R1 a literal system prompt omits the app\'s own constant', 'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "fetch(P,{body:JSON.stringify({app_id:'a',system:'You help.',"
     "messages:[{role:'user',content:q}]})});", True),

    ('R1 an identifier-valued prompt, built above, omits it', 'a.html',
     "var X_REFUSAL='CRITICAL RULE: refuse that.';\n"
     "function go(){ var sys='You help with things.';\n"
     "  call({app_id:'a',system:sys,messages:[{role:'user',content:q}]}); }", True),

    ('R2 the site writes its OWN rule block instead -- looks covered', 'a.html',
     "var X_RULE='CRITICAL RULE: never output a citation.';\n"
     "function go(){ var sys='You argue.'+'\\n\\nHARD RULES:\\n1. Cite only "
     "real cases.\\n';\n"
     "  call({app_id:'a',system:sys,messages:[{role:'user',content:q}]}); }", True),

    # ── MUST NOT FLAG -- the four real false positives, pinned ─────────────
    ('every site references the constant', 'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "fetch(P,{body:JSON.stringify({app_id:'a',system:'You help.'+X_RULE,"
     "messages:[{role:'user',content:q}]})});", False),

    ('FP1 a body-system <select>, not an AI call (sairnvet dx-system)', 'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "function searchDiagnoses(){ var system=document.getElementById"
     "('dx-system').value; return rows.filter(function(r){return "
     "r.system===system;}); }", False),

    ('FP2 a constant name that is an ERROR CODE in a comment (sairndental)',
     'a.html',
     "// lookupCoverage() decides by row order), 400 INVALID_COVERAGE_RULE\n"
     "fetch(P,{body:JSON.stringify({app_id:'a',system:'You help.',"
     "messages:[{role:'user',content:q}]})});", False),

    # ── THE ONLY FIXTURE HERE THAT DISCRIMINATES COMMENT-STRIPPED FROM RAW ──
    # Added because the mutation control for the strip_comments fix did NOT
    # bite: reverting the lock to raw text still gave 11/11, which means the
    # fix was correct in principle and UNPROVEN by the fixtures that were
    # supposed to hold it. FP2 above is the weaker version -- its comment has
    # no `var` and no `=`, so CONST_RE never matched it in either mode and it
    # was never testing comment handling at all.
    #
    # This one does: a constant DEFINITION inside a comment. On raw text
    # CONST_RE matches it, the app appears to have made a commitment, and the
    # real site below is flagged for breaking a promise that exists only in
    # prose. Comment-stripped, there is no constant and nothing to report.
    # So the expected verdict differs by mode, which is what makes it a lock.
    ('a constant DEFINED only inside a comment is not a commitment', 'a.html',
     "// var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "fetch(P,{body:JSON.stringify({app_id:'a',system:'You help.',"
     "messages:[{role:'user',content:q}]})});", False),

    ('FP3 a comment mentioning a system: and a rule (stonedesk 5-tab)', 'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "// Safety 5-tab system: Training / Daily Checklist / Incidents\n"
     "fetch(P,{body:JSON.stringify({app_id:'a',system:'You help.'+X_RULE,"
     "messages:[{role:'user',content:q}]})});", False),

    ('an app that defines NO constant is not told to write one', 'a.html',
     "fetch(P,{body:JSON.stringify({app_id:'a',system:'You help.',"
     "messages:[{role:'user',content:q}]})});", False),

    ('a system: property with no messages sibling is not an AI call', 'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "var cfg={system:'linux',arch:'x64'};", False),

    # ── THE SHAPE THE FIRST NINE FIXTURES ALL MISSED ───────────────────────
    # Added after the first real sweep reported two compliant sairnfreedom
    # sites as missing their own refusal. Every prompt in this tree is English
    # and English has commas; none of the fixtures above had one inside a
    # string, so the lock was silent on the commonest shape in the repo while
    # reporting 9/9. The fixture set was the thing that was wrong here, not a
    # verdict in it -- so this is an ADDITION, not a fixture bent to match
    # output.
    # ── R3: THE BLIND SPOT THIS TOOL WAS REGISTERED AS HAVING ──────────────
    # A site with no constant but a real control on its OUTPUT is still
    # reported -- suppressing it would let a genuine omission hide behind any
    # nearby verifier -- but it must be reported as a DIFFERENT KIND. These two
    # fixtures differ in one thing only: whether a verification call follows.
    ('R3 a site with a post-call control is still flagged, but as R3', 'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "function go(){ call({app_id:'a',system:'You argue.',"
     "messages:[{role:'user',content:q}]}).then(function(r){"
     " var c=mtExtractCitations(r.text); mtVerifyCitations(c); }); }", True, 'R3'),

    ('...and the SAME site without the control is R1, not R3', 'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "function go(){ call({app_id:'a',system:'You argue.',"
     "messages:[{role:'user',content:q}]}).then(function(r){"
     " show(r.text); }); }", True, 'R1'),

    ('a comma INSIDE the prompt prose does not end the expression', 'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "fetch(P,{body:JSON.stringify({app_id:'a',"
     "system:'You read a page, and you always name it.'+X_RULE,"
     "messages:[{role:'user',content:q}]})});", False),

    ('...and a comma in the prose still cannot hide a MISSING constant',
     'a.html',
     "var X_RULE='CRITICAL RULE: never do the thing.';\n"
     "fetch(P,{body:JSON.stringify({app_id:'a',"
     "system:'You read a page, and you always name it.',"
     "messages:[{role:'user',content:q}]})});", True),
]

# A constant this app has committed to. Deliberately narrow: the SUFFIX is the
# commitment. A name like `LAW_CITATION_RULE` or `VA_CLAIM_REFUSAL` says the
# author wrote a rule meant to be reused; `SYSTEM_PROMPT` or `SEED` does not.
CONST_RE = re.compile(
    r'\b(?:var|let|const)\s+([A-Z][A-Z0-9_]*(?:_RULE|_REFUSAL))\s*=')

# An AI call site: the `system:` PROPERTY of an object literal. Keyed on the
# property rather than on any variable named `system` -- FP1 above is why.
SITE_RE = re.compile(r'\bsystem\s*:\s*')

# ...and the sibling that proves it is an AI envelope rather than a config
# object. Every real call site on this platform carries it; FP4's `{system:
# 'linux', arch:'x64'}` does not.
ENVELOPE_RE = re.compile(r'\bmessages\s*:')
ENVELOPE_WINDOW = 600

# The site wrote its own rule block. Literal markers, not topic inference.
OWN_RULES_RE = re.compile(r'HARD RULES|CRITICAL RULE', re.I)

# ── R3: A MECHANICAL CONTROL AFTER THE CALL (added 2026-09-14) ─────────────
# THE BLIND SPOT THIS CLOSES IS RECORDED AS A DEFECT AGAINST THIS TOOL. A
# prompt-level rule is an INSTRUCTION; a check on the model's OUTPUT is a
# CONTROL. This checker could only see the first, so it reported sairnlaw's
# critique step -- whose every citation is extracted and verified against
# CourtListener and badged -- identically to the trust-accounting explainer,
# which at the time had no rule AND no check. Same finding text, opposite
# severity. "A text-presence checker over-implies severity on exactly the
# best-protected site."
#
# WHAT IS DETECTED IS A CALL, NOT AN INTENTION. No inference about whether the
# control is adequate: either the result handler invokes a verification of the
# model's output within the window, or it does not. The three shapes below are
# every one this tree actually contains, and each is a function that takes
# model output and answers a question about it:
#
#   *VerifyCitations / citatorFetch('verify')  -- resolve a citation against a
#                                                 real reporter
#   mtAssertNo<Thing>                          -- refuse output containing a
#                                                 forbidden construct
#   mtExtractCitations                          -- pull the citations OUT, which
#                                                 is what any of the above needs
#
# DELIBERATELY NOT A GENERIC `verify|check|validate` GREP. That would match
# `checkAiRateLimit` and every unrelated helper, and a rule that matches by
# word-shape is the design opinion this file refuses to be elsewhere. Add a
# name here when a real control appears, not in anticipation.
POSTCALL_CONTROL_RE = re.compile(
    r'\b(?:\w*VerifyCitations|mtExtractCitations|mtAssertNo[A-Z]\w*)\s*\('
    r"|citatorFetch\s*\(\s*['\"]verify['\"]")

# Forward from the `system:` property. Wider than ENVELOPE_WINDOW because the
# control lives in the RESULT HANDLER -- after the await or inside .then() --
# which on this platform sits a few hundred to a couple of thousand characters
# past the request. Bounded anyway: an unbounded forward scan finds the NEXT
# feature's verifier and credits this site with somebody else's control.
POSTCALL_WINDOW = 2500

# How far above a call site to look for the assignment of an identifier used as
# the system value. Bounded on purpose: an unbounded search up the file finds a
# same-named variable in an unrelated function, which is FP1 wearing a
# different hat.
ASSIGN_WINDOW = 12000


def _value_expr(src, at):
    """The system: property's value expression, to the end of that property.

    ── THE SEMICOLON STOP IS NOT COSMETIC, AND A FIXTURE CAUGHT IT ─────────
    Without it this walked past the end of the property and kept going until it
    happened to find a top-level comma -- which on fixture FP3 dragged in the
    NEXT STATEMENT and picked up the constant reference from there. The fixture
    still passed, for entirely the wrong reason: the site looked compliant
    because text from unrelated code below it mentioned the constant.

    That is the shape this platform has already paid for once -- an assertion
    that holds while measuring something other than its subject. A run-on
    expression makes the tool UNDER-report (it borrows compliance from its
    neighbours), which is the direction that matters.
    """
    depth, out, i, quote = 0, [], at, ''
    while i < len(src) and len(out) < 8000:
        c = src[i]
        if quote:
            # ── INSIDE A STRING, PUNCTUATION IS PROSE ──────────────────────
            # THE DEFECT THIS FIXES WAS LIVE IN THE FIRST SWEEP, and it read as
            # a finding rather than as a crash. Every system prompt here is
            # English, English has commas, and a comma-terminated walk that
            # does not know it is inside a quote ENDS THE EXPRESSION MID-
            # SENTENCE. sairnfreedom.html:4066 really does end
            # `...'+extra+VA_CLAIM_REFUSAL`, and the walk stopped at the comma
            # in "on a page you read, and always name the page" -- so the tool
            # reported a compliant site as missing its own refusal.
            #
            # Two false positives of three in sairnfreedom, and the direction
            # is the bad one for a checker nobody has promoted yet: a tool
            # whose first real output is wrong gets switched off, which is
            # exactly what `tools/shape_antipattern_check.py` warns about.
            # Caught by reading the findings against a file I had already read
            # by hand, NOT by the fixtures -- none of them had a comma inside a
            # prompt, so the lock was silent on the commonest shape in the
            # tree. A fixture for it is pinned now.
            if c == '\\':
                out.append(c)
                i += 1
                if i < len(src):
                    out.append(src[i])
                    i += 1
                continue
            if c == quote:
                quote = ''
            out.append(c)
            i += 1
            continue
        if c in '\'"`':
            quote = c
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:
                break
            depth -= 1
        elif c in ',;' and depth == 0:
            break
        out.append(c)
        i += 1
    return ''.join(out).strip()


def _resolve(src, at, expr):
    """Expand an identifier-valued system prompt to the text that built it.

    Returns the expression itself for a literal. For a bare identifier, the
    nearest PRECEDING assignment within ASSIGN_WINDOW characters, plus any
    `name +=` appends between there and the call site -- sairnlaw builds its
    chat prompt that way (`sys+='\\n\\n'+sharedCtx`) and reading only the
    first assignment would miss half the prompt.
    """
    m = re.match(r'^([A-Za-z_$][\w$]*)\s*$', expr)
    if not m:
        return expr
    name = m.group(1)
    lo = max(0, at - ASSIGN_WINDOW)
    window = src[lo:at]
    asg = list(re.finditer(
        r'(?:(?:var|let|const)\s+)?' + re.escape(name) + r'\s*\+?=\s*', window))
    if not asg:
        return expr
    return ' '.join(_value_expr(window, a.end()) for a in asg)


# ── THE DENOMINATOR, CARRIED RATHER THAN LEFT TO THE READER ────────────────
# Convention 3: a rate over the subset you looked at is not a rate. "4 findings"
# against `files scanned: 465` invites exactly the wrong reading, because 463 of
# those files could not have produced a finding at all -- they define no
# constant, so the rule is silent on them BY DESIGN rather than because they are
# clean. The population this tool can speak about is: AI call sites inside files
# that define at least one rule constant. Everything else is out of scope, and
# saying so is the difference between a measurement and a number.
POP = {'files_with_consts': 0, 'sites_in_those_files': 0, 'sites_compliant': 0,
       'sites_with_postcall_control': 0}


def rule(path, src):
    """Return a list of finding strings for one file. `src` is comment-stripped."""
    consts = sorted(set(CONST_RE.findall(src)))
    if not consts:
        # The app made no commitment, so there is none to have broken. Telling
        # it to write one would be the design opinion this rule refuses to be.
        return []
    POP['files_with_consts'] += 1

    out = []
    for m in SITE_RE.finditer(src):
        near = src[max(0, m.start() - ENVELOPE_WINDOW):
                   m.start() + ENVELOPE_WINDOW]
        if not ENVELOPE_RE.search(near):
            continue                      # a config object, not an AI envelope
        POP['sites_in_those_files'] += 1
        expr = _resolve(src, m.start(), _value_expr(src, m.end()))
        if any(re.search(r'\b%s\b' % re.escape(c), expr) for c in consts):
            POP['sites_compliant'] += 1
            continue                      # the commitment is kept here
        line = src[:m.start()].count('\n') + 1
        own = bool(OWN_RULES_RE.search(expr))
        # R3: is there a MECHANICAL CONTROL on the output, after the call? If
        # so this site is a different finding from one with no control at all,
        # and collapsing the two is the defect recorded against this tool.
        after = src[m.end():m.end() + POSTCALL_WINDOW]
        ctrl = POSTCALL_CONTROL_RE.search(after)
        if ctrl:
            POP['sites_with_postcall_control'] += 1
        kind = 'R3' if ctrl else ('R2' if own else 'R1')
        note = ''
        if ctrl:
            note = ('. A MECHANICAL CONTROL RUNS ON ITS OUTPUT (%s) within %d '
                    'chars, so the missing constant is NOT the only thing '
                    'standing between this site and a bad answer. Read this as '
                    'a SCOPE QUESTION -- is the exception deliberate and named '
                    '-- rather than as an unguarded surface. R1 and R2 are the '
                    'ones with nothing downstream.'
                    % (ctrl.group(0).rstrip('('), POSTCALL_WINDOW))
        elif own:
            note = ('. IT WRITES ITS OWN RULE BLOCK INSTEAD, so it reads as '
                    'covered -- two rule sets for one app and nothing keeps '
                    'them in step')
        out.append(
            '%s:%d  %s -- this AI call site\'s system prompt references NONE of '
            'the %d rule constant(s) this file defines (%s)%s'
            % (path, line, kind, len(consts), ', '.join(consts), note))
    return out


def run_fixtures(verbose=True):
    """── THE LOCK MUST RUN THE SAME PATH THE SWEEP RUNS ──────────────────────

    CHANGED FROM THE GENERATED SCAFFOLD, and this is a real defect in it rather
    than a preference. The scaffold called `rule(name, src)` on the RAW fixture
    text while `main()` calls `rule(f, strip_comments(src))` on every real file.
    So the blind lock validated a transformation the sweep never applies, and
    the two fixtures whose whole subject is comment handling could not test
    anything: FP2 and FP3 exist BECAUSE grep cannot tell code from prose about
    code, and the lock was reading the prose.

    A lock that exercises a different code path from the thing it locks is the
    instrument-drift shape from disciplines item 8, present on the day the
    checker is written rather than arriving later. Worth reporting back to
    `tools/new_checker.py`, which will emit this same mismatch into every
    checker scaffolded from it.
    """
    wrong = []
    for fx in FIXTURES:
        # A FIFTH ELEMENT IS THE EXPECTED KIND, and it exists because two
        # fixtures differ ONLY in kind: a site with a post-call control (R3)
        # and the same site without one (R1) are BOTH flagged, so a
        # flag/no-flag lock is satisfied by either verdict and discriminates
        # nothing. That is the pass-for-the-wrong-reason shape this file has
        # already recorded twice.
        label, name, src, must_flag = fx[0], fx[1], fx[2], fx[3]
        want_kind = fx[4] if len(fx) > 4 else None
        try:
            got_list = rule(name, strip_comments(src))
            got = bool(got_list)
            if want_kind and got:
                kinds = [f.split()[1] for f in got_list if len(f.split()) > 1]
                if want_kind not in kinds:
                    wrong.append('%s -- expected kind %s, got %s'
                                 % (label, want_kind, kinds or '(none)'))
                    continue
        except NotImplementedError:
            wrong.append('%s -- rule() is not implemented, so NOTHING was judged'
                         % label)
            continue
        if got != must_flag:
            wrong.append('%s -- expected %s, got %s'
                         % (label, 'FLAG' if must_flag else 'SILENT',
                            'FLAG' if got else 'SILENT'))
        elif verbose:
            print('  ok   %s' % label)
    return wrong


def main(argv):
    only_fixtures = '--fixtures' in argv
    args = [a for a in argv if not a.startswith('--')]

    print('BLIND LOCK -- %d fixture(s), judged before any real file is opened'
          % len(FIXTURES))
    wrong = run_fixtures(verbose=only_fixtures)
    if wrong:
        print('')
        print('REFUSING: the criteria do not classify their own fixtures.')
        for w in wrong:
            print('  x %s' % w)
        print('')
        print('NOTHING REAL WAS JUDGED. Fix the criteria, or fix a fixture whose')
        print('expected verdict was itself wrong -- and say in this file which')
        print('one you did. A fixture changed to match the tool output is how a')
        print('lock stops locking.')
        return EXIT_COULD_NOT_RUN
    print('  %d/%d fixtures correct.' % (len(FIXTURES), len(FIXTURES)))
    if only_fixtures:
        return EXIT_CLEAN

    # ── THE LOCK MUST NOT BE IN THE MEASUREMENT ────────────────────────────
    # rule() increments POP, and run_fixtures() has just called it 11 times, so
    # the population carried the fixtures' own synthetic call sites: the first
    # run printed 18 sites against 10 compliant + 4 flagged, which does not
    # add up and was the only reason this was noticed at all. Disciplines item
    # 5 says a validation must not ride alongside the live data; this is that
    # rule pointing the other way -- the validation contaminating the
    # measurement rather than the measurement satisfying the validation.
    # An arithmetic identity is asserted below and in the probe, because a
    # denominator nobody checks is how the first version got published.
    for _k in POP:
        POP[_k] = 0

    if args:
        files, notes = [os.path.relpath(a, REPO).replace(chr(92), '/') for a in args], []
    else:
        files, notes = tracked('*.js', '*.html')

    findings, could_not_run, scanned = [], [], 0
    for f in files:
        p = os.path.join(REPO, f)
        try:
            src = io.open(p, encoding='utf-8').read()
        except Exception as e:
            # A FILE YOU COULD NOT READ IS NOT A FILE WITH NO FINDINGS.
            could_not_run.append('%s -- unreadable (%s), so it was NOT scanned'
                                 % (f, type(e).__name__))
            continue
        scanned += 1
        try:
            findings.extend(rule(f, strip_comments(src)))
        except NotImplementedError:
            could_not_run.append('%s -- rule() is not implemented' % f)

    print('')
    print('  files scanned : %d' % scanned)
    for n in notes:
        print('  not scanned   : %s' % n)
    # THE POPULATION, not just the count. 463 of those 465 files are silent
    # BY DESIGN -- they define no constant -- so quoting a rate against the
    # scanned figure would flatter the platform by two orders of magnitude.
    print('')
    print('  POPULATION THIS CAN SPEAK ABOUT (convention 3 -- publish the '
          'denominator):')
    print('    files defining a rule constant   : %d'
          % POP['files_with_consts'])
    print('    AI call sites inside those files : %d'
          % POP['sites_in_those_files'])
    print('    ...of which carry a constant     : %d'
          % POP['sites_compliant'])
    print('    ...of which do not               : %d' % len(findings))
    # PRINTED, because a counter that is incremented and never shown is a
    # measurement nobody can act on -- and this one is the whole point of R3.
    # It splits the findings a reader should worry about from the ones where
    # something downstream is already checking the model's output.
    print('    ...and of THOSE, how many have a')
    print('       mechanical control on the OUTPUT: %d  <- R3; the rest have '
          'nothing downstream'
          % POP['sites_with_postcall_control'])
    print('       (R3 detects a named VERIFICATION of content. A purely '
          'STRUCTURAL output contract --')
    print('        e.g. accept nothing but a two-key JSON object -- is a real '
          'control and is NOT')
    print('        counted here, deliberately: conflating the two would make '
          'R3 mean "something')
    print('        happens afterwards", which is not a useful thing to be told.)')
    # THE IDENTITY, ASSERTED RATHER THAN PRESENTED. compliant + flagged must
    # equal the sites examined; any gap means the population is counting
    # something the verdicts are not, which is what the fixture contamination
    # looked like from the outside.
    if POP['sites_compliant'] + len(findings) != POP['sites_in_those_files']:
        could_not_run.append(
            'THE POPULATION DOES NOT ADD UP: %d compliant + %d flagged != %d '
            'sites examined. The denominator is counting sites the verdicts are '
            'not, so neither figure can be quoted.'
            % (POP['sites_compliant'], len(findings),
               POP['sites_in_those_files']))
    if POP['files_with_consts'] == 0 and not args:
        # A SOURCE THAT YIELDS ZERO IS A REFUSAL, NOT A QUIET ZERO. If no file
        # in the tree defines a rule constant, this tool did not find nothing
        # -- it lost its subject, most likely because the naming convention
        # moved. Reporting CLEAN there is the dead-anchor shape from
        # disciplines item 8.
        could_not_run.append(
            'NO file in the tree defines a *_RULE / *_REFUSAL constant, so this '
            'checker had no subject. That is a REFUSAL, not a clean run: either '
            'the convention this rule keys on has been renamed, or the two apps '
            'that used it have been removed. Re-read CONST_RE against a real '
            'app before believing any verdict from this tool.')
    print('')
    print('  AND THE LIMIT, RESTATED WHERE IT CANNOT BE MISSED: this counts '
          'WORDS PRESENT IN A PROMPT.')
    print('  It does not and cannot show the model obeys them. That half needs '
          'a model call and')
    print('  is deferred by Michael\'s recorded decision. A clean run here is '
          'NOT "the refusal holds".')
    return finish(findings, could_not_run,
                  clean_line='CLEAN -- every AI call site in every app that '
                             'defines a rule constant references one')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
