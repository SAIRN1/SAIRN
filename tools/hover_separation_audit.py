#!/usr/bin/env python
"""tools/hover_separation_audit.py -- the audit trail for the hover auditor's
separation, built from real history rather than from anybody's account of it.

THE QUESTION: has the fifth role -- which audits the four build agents and is
itself reviewed by nobody -- ever written platform code? Its skill file forbids
it in terms ("Never write, edit, or push platform code"). This asks the
repository and the auditor's own black-box whether that held.

WHY THE OBVIOUS METHOD DOES NOT WORK, MEASURED FIRST RATHER THAN DISCOVERED
HALFWAY THROUGH. `git log --format=%an` is useless here: all five roles commit
through ONE git identity (`Michael Dibert <mikied68@gmail.com>`, verified
across the whole history by this tool's own `--authors` output). There is no
author field to group by. Attribution has to be DERIVED, and derived
attribution is incomplete by construction, so the incomplete fraction is
printed at the top of the report instead of at the bottom.

THE THREE SIGNALS, in the order they are trusted:

  1. A commit touching `.claude/claims/<session>.json` or
     `SAIRN-ACTIVE-WORK-<session>.md` is that session's. These are per-clone
     bookkeeping files no other session writes.
  2. A commit touching ONLY paths inside the auditor's own scope is the
     auditor's.
  3. Everything else is UNATTRIBUTED -- and that word is load-bearing. It does
     NOT mean "a build agent's".

AND THE LIMIT THAT MATTERS MOST, STATED BEFORE ANY RESULT: signal 2 IS
CIRCULAR FOR THE VERY QUESTION BEING ASKED. A commit in which the auditor
touched platform code would, by construction, fail the "only its own scope"
test and land in UNATTRIBUTED. **Git alone cannot prove the negative.** It can
only show that the auditor's KNOWN commits are clean, which is a weaker claim
and is reported as one.

WHAT CLOSES THAT GAP IS A STRUCTURALLY DIFFERENT SOURCE -- the auditor's own
hash-chained self-log, which records what it did entry by entry including the
SHAs it committed. Two independent records that agree are worth more than one
that cannot be cross-examined; that is the same reason this platform requires
a structurally different method for independence. The chain is VERIFIED before
any of it is believed, and if it does not verify, this tool refuses rather
than reporting from a record somebody could have edited.

    python tools/hover_separation_audit.py              # the report
    python tools/hover_separation_audit.py --trail      # per-commit audit trail
    python tools/hover_separation_audit.py --authors    # prove the one-identity claim
    python tools/hover_separation_audit.py --json

EXIT CODES, because "found nothing" and "could not look" are different:
    0  checked, no separation violation found
    1  a violation was found
    2  COULD NOT RUN some part of it -- never reported as clean
"""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, OrderedDict

SESSIONS = ('hank', 'cc', 'cody', 'fourth')
SKILL_DIR = '.claude/skills/sairn-hover-auditor/'
REGISTER = 'docs/defect-density-register.json'
OWN_CLAIM = '.claude/claims/hover.json'

# Kept identical in meaning to tools/hover_auditor_scope_gate.py's ALLOWED, and
# the probe asserts the two agree. They are separate constants on purpose: the
# gate must run with no imports in a hook, and a shared module that one of them
# silently stopped importing is a failure mode neither would report.
#
# OWN_CLAIM added 2026-09-18 with the gate's matching entry. It has to move in
# BOTH halves at once: leaving it out here would turn every claim commit the
# gate now permits into a reported scope VIOLATION in the history audit, which
# is the same defect wearing the opposite sign.
AUDITOR_SCOPE = (SKILL_DIR, REGISTER, OWN_CLAIM)

# ── SCOPE AND SIGNATURE ARE NOT THE SAME SET, AND CONFLATING THEM WAS A REAL
# BUG IN THE FIRST VERSION OF THIS FILE, caught by its own output before it
# shipped. `docs/defect-density-register.json` is in SCOPE -- the auditor is
# told to write findings there. It is NOT a SIGNATURE, because all four build
# agents write it too via tools/defect_register.py --add. Using the scope set
# for attribution credited every register-only commit on the platform to the
# auditor and inflated its commit count from 20 to 46.
#
# The general shape is worth naming: "what this role MAY touch" and "what
# identifies this role" are different questions, and the second must be
# EXCLUSIVE to be worth anything. Only the skill directory is.
AUDITOR_SIGNATURE = (SKILL_DIR,)

GENESIS = 'genesis:hover-auditor-self-log:v1'

CLAIM_RE = re.compile(r'^\.claude/claims/(\w+)\.json$')
WORKLOG_RE = re.compile(r'^SAIRN-ACTIVE-WORK-(\w+)\.md$')
OWN_COMMIT_RE = re.compile(r'(?:[Cc]ommitted|[Pp]ushed)\s+([0-9a-f]{7,40})')
# "Committed <a>, pushed <b>" -- the auditor's own habit of recording BOTH the
# local sha and the one that reached origin. It is the thing that turns most of
# the unresolvable half below from an unknown into an explained gap, so the
# pairing is MEASURED here rather than offered as an explanation.
PAIR_RE = re.compile(r'[Cc]ommitted\s+([0-9a-f]{7,40})[,\s]+pushed\s+([0-9a-f]{7,40})')
SHA_RE = re.compile(r'^[0-9a-f]{7,40}$')


# ── WHOSE COMMIT IS IT: THREE ANSWERS, NOT TWO ───────────────────────────────
# OWN_COMMIT_RE answers "does this text say committed/pushed <sha>". It was
# being read as "does this log CLAIM <sha> as its own", and those are not the
# same question. hover1's entry 404 quotes cody's status line -- cody's status
# now shows "grader importer guard FIXED and pushed 270c60ed..." -- and the
# regex matched inside the quotation, so a sha the auditor CITED was reported
# as a SEPARATION VIOLATION against cc's commit 270c60ed. The multi-log fix did
# not create that; while the tool was refusing it never reached the attribution
# step at all, so the fix un-hid it.
#
# THE OBVIOUS REPAIR IS THE WRONG ONE. Narrowing the regex -- demanding
# sentence-initial "Committed", or the Committed/pushed pair -- would clear the
# one known case and would also stop matching any FUTURE entry phrased
# differently. In an attribution audit a false negative is silent: the auditor
# breaches its scope, the log says so in prose, and nothing reports it. A false
# positive is loud and gets read by a human. So the rule is not narrowed; the
# VERDICT gains a third state.
#
#   OWN       -- nothing contradicts the claim. Eligible for a violation.
#   CITED     -- TWO independent signals agree this is someone else's commit.
#                Not a violation, and PRINTED with its reasons, never dropped.
#   DISPUTED  -- exactly one signal fired. Still checked, still reported if it
#                is out of scope, but labelled as contested rather than
#                asserted as the auditor's own.
#
# TWO SIGNALS ARE REQUIRED TO SUPPRESS because suppression is the direction
# that loses a real violation, and each signal alone is defeasible:
#
#   quoted     -- a quotation is another speaker by construction. Strong in
#                 meaning, weak mechanically: prose quotes unevenly.
#   audited    -- the sha is in this entry's own `ref` list, which is what the
#                 entry EXAMINED. Structural, but an entry may legitimately
#                 reference its own commit.
#
# Measured over hover1's 414 entries at the time of writing: 34 matches, 33
# OWN, 1 CITED with both signals firing. The two signals agree exactly once and
# disagree never -- which is a fact about one corpus and not a validation, so
# the criteria are locked against synthetic fixtures in both directions in
# tests/run_hover_separation_probe.py section G rather than against this count.
def quoted_spans(text):
    """Balanced double-quote spans as (open_index, close_index) pairs.

    An UNMATCHED FINAL QUOTE CLOSES NOTHING and is dropped. A parity test would
    instead let one stray quote reclassify the whole rest of an entry as
    quoted -- the same desync this repo already paid for once, where odd quote
    parity threw off `is_report_only_artefact`'s stripper.
    """
    spans, open_at = [], None
    for i, ch in enumerate(text):
        if ch != '"':
            continue
        if open_at is None:
            open_at = i
        else:
            spans.append((open_at, i))
            open_at = None
    return spans


def _sha_prefix_match(a, b):
    """True when one sha is a prefix of the other. Lengths differ on purpose:
    the log writes short shas and `ref` records whatever length it recorded, so
    an equality test would find nothing and quietly answer OWN."""
    n = min(len(a), len(b))
    return n >= 7 and a[:n] == b[:n]


def ref_shas(ref):
    return [s for s in re.split(r'[,\s]+', ref or '') if SHA_RE.match(s)]


# ── WHOSE QUOTATION IS IT: THE HALF THE FIRST FIX NEVER ASKED ───────────────
# JOINT FINDING BY hover1 AND hover2 (2026-09-22) against the first version of
# this classifier, reproduced here before it was acted on. The two suppression
# signals were `inside a quotation` and `in this entry's ref list`, and NEITHER
# ASKS WHO IS BEING QUOTED. A log quoting ITSELF -- `Entry 311 says "Committed
# <sha>, pushed."` -- satisfies both and was fully suppressed: zero violations
# on a genuinely out-of-scope sha the log claims in its own words.
#
# THE REASON STRING WAS THE DEFECT, WRITTEN DOWN. It read "the text is inside a
# quotation, so it is another session speaking and not this log" -- asserting
# the speaker having never checked one. That is the same shape this whole file
# exists to catch, one level up, and it is why the first fix's own
# recurrence_open already recorded that the two signals were not shown to be
# independent. They are both CONTAINMENT tests, and a self-quotation satisfies
# both at once; position was standing in for identity.
#
# THE FIX IS NOT A THIRD CONTAINMENT TEST. The quote signal now requires
# ATTRIBUTION: the NEAREST speaker marker in the sentence before the opening
# quote must name a session OTHER than the log being read. A first-person
# marker, this log's own name, or no marker at all all mean the quotation
# establishes no other speaker, so it cannot suppress anything -- the match
# falls to DISPUTED, which is reported and still scope-checked.
#
# NEAREST, NOT ANYWHERE, and that distinction is the whole point: "cody flagged
# it; my own log says ..." names another session AND is a self-quote, and an
# any-match rule would suppress it. Taking the last marker before the quote is
# an ownership test rather than a proximity one.
QUOTABLE = ('hank', 'cc', 'cody', 'fourth', 'ted', 'hover', 'hover1', 'hover2',
            'michael')
QUOTABLE_RE = re.compile(r'\b(' + '|'.join(QUOTABLE) + r')\b', re.I)
# Word boundaries matter more than they look: `hover_coverage_ledger.py` must
# NOT read as the word "hover". `_` is a word character, so \bhover\b does not
# match inside it -- which is the behaviour wanted, and is asserted rather than
# assumed by the probe.
# ── THE LEAD-IN BOUNDARY SET, NAMED SO THE RULE AND ITS DESCRIPTION AGREE ───
# FINDING B of hank's review of 467baf74: `: ` used to be in this set. A colon
# is the most common way to INTRODUCE a quotation, so `cody said: "Committed
# <sha>, pushed."` truncated the lead-in to nothing and the attribution came
# back `none` -- DISPUTED where it should be CITED.
#
# IT FAILED SAFE, which is why it was not urgent: under-suppression reports
# more matches, never fewer. What was wrong beyond the behaviour is that the
# docstring said "back to the nearest sentence break or newline" while the code
# was ALSO cutting at a clause introducer. The stated rule and the implemented
# rule were different rules, and only one of them was reviewable.
#
# A semicolon stays: it genuinely separates clauses, and "cody flagged it; my
# own log says ..." lands on `self` either way because the rule takes the
# NEAREST marker. It is kept for the case where the earlier clause is the only
# thing naming a session.
LEAD_IN_BOUNDARIES = ('\n', '. ', '! ', '? ', '; ')

SELF_MARKER = re.compile(
    r'\bI\b|\bmy\b|\bmine\b|\bmyself\b|\bmy own\b|\bthis log\b|\bits own\b|'
    r'\bthis record\b|\bmy earlier\b', re.I)


def short_session(session):
    """'C--Users-marsh-Documents-SAIRN-hover2' -> 'hover2'. Identity comes from
    the directory, as session_of() already establishes, because a log that
    lied about its own name is what this tool exists to be able to detect."""
    s = str(session or '').strip().lower()
    return s.rsplit('-', 1)[-1] if '-' in s else s


def quote_attribution(summary, quote_open, own_session):
    """'other', 'self' or 'none' for the quotation opening at `quote_open`.

    The lead-in is bounded STRUCTURALLY -- back to the nearest of
    LEAD_IN_BOUNDARIES -- rather than by a character count, because the
    attributing phrase is always in the same sentence as the quote it
    introduces, and a fixed window is the defect class this platform named as
    scrubber item 24. The boundary set is a NAMED CONSTANT so this sentence and
    the code cannot describe different rules, which is exactly what happened
    when `: ` was in the set and this docstring said "sentence break".
    """
    lo = 0
    for sep in LEAD_IN_BOUNDARIES:
        k = summary.rfind(sep, 0, quote_open)
        if k >= 0 and k + len(sep) > lo:
            lo = k + len(sep)
    lead = summary[lo:quote_open]
    own = short_session(own_session)
    # hover1 is hover's other spelling; nothing else aliases.
    own_names = {own, 'hover1'} if own == 'hover' else {own}
    marks = [(m.start(), 'self' if m.group(1).lower() in own_names else 'other')
             for m in QUOTABLE_RE.finditer(lead)]
    marks += [(m.start(), 'self') for m in SELF_MARKER.finditer(lead)]
    if not marks:
        return 'none'
    return max(marks, key=lambda t: t[0])[1]


def classify_own_commit(summary, ref, sha, pos, own_session=None):
    """(verdict, reasons) for one OWN_COMMIT_RE hit at `pos` in `summary`.

    verdict is 'own', 'cited' or 'disputed'. `reasons` is empty for 'own' and
    otherwise names every signal that fired, in words, so a suppression can be
    read and disagreed with rather than taken on trust.
    """
    reasons, notes = [], []
    span = next(((a, b) for a, b in quoted_spans(summary) if a < pos < b), None)
    if span:
        who = quote_attribution(summary, span[0], own_session)
        if who == 'other':
            reasons.append('the text is inside a quotation the sentence '
                           'ATTRIBUTES to another session, so it is that '
                           'session speaking and not this log')
        else:
            # A REJECTED SIGNAL IS SAID OUT LOUD, not left as an absence. A
            # reader seeing DISPUTED needs to know the quotation was found and
            # DECLINED, not that there was no quotation.
            notes.append('the match IS inside a quotation, but the sentence '
                         'attributes it to %s rather than to another session, '
                         'so it establishes no other speaker and does not '
                         'suppress anything'
                         % ('this log itself' if who == 'self' else 'nobody'))
    if any(_sha_prefix_match(sha, r) for r in ref_shas(ref)):
        reasons.append("the sha is in this entry's own ref list, which is what "
                       'the entry AUDITED rather than what it wrote')
    if len(reasons) >= 2:
        return 'cited', reasons + notes
    if reasons:
        return 'disputed', reasons + notes
    return 'own', notes


def git(*args):
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, r.stdout, r.stderr


def _under(path, prefixes):
    for p in prefixes:
        if p.endswith('/'):
            if path.startswith(p):
                return True
        elif path == p:
            return True
    return False


def in_auditor_scope(path):
    return _under(path, AUDITOR_SCOPE)


def is_auditor_signature(path):
    return _under(path, AUDITOR_SIGNATURE)


def load_commits():
    """Every commit with its file list. Returns (commits, error)."""
    code, out, err = git('log', '--all', '--format=%x00%H%x00%at%x00%s',
                         '--name-only')
    if code != 0:
        return None, 'git log failed: ' + err.strip()
    commits, cur = [], None
    # PARSED LINE-WISE, NOT BY SPLITTING ON NUL, because a commit SUBJECT may
    # itself contain anything; the NUL PREFIX marks the header line
    # unambiguously and the rest of that line is split only twice.
    #
    # A `for chunk in out.split('\x00'): pass` sat here until 2026-09-16 -- the
    # abandoned first attempt, left behind when the loop below replaced it. It
    # split the ENTIRE multi-megabyte log into a list and threw it away on
    # every run, and the comment above it ("the NUL split above") was the only
    # thing still pointing at it. Guardian check 0d: dead code that reads as
    # intent, and a comment that describes a mechanism the file no longer has
    # is worse than no comment. Found by an independent review of this file.
    for line in out.split('\n'):
        if line.startswith('\x00'):
            parts = line[1:].split('\x00', 2)
            if len(parts) < 3:
                return None, 'unparseable log header: %r' % line[:80]
            cur = {'sha': parts[0], 'ts': int(parts[1]), 'subject': parts[2],
                   'files': []}
            commits.append(cur)
        elif line.strip() and cur is not None:
            cur['files'].append(line.strip().replace('\\', '/'))
    return commits, ''


# ── THE GIT HALF COULD PRINT A VIOLATION AND COULD NOT PRODUCE ONE ──────────
# FINDING A of hank's review of 467baf74, confirmed structurally and then
# measured before it was acted on.
#
# `attribute()` returns 'hover' only when EVERY file is under
# AUDITOR_SIGNATURE, and AUDITOR_SIGNATURE is a STRICT SUBSET of AUDITOR_SCOPE.
# So `who == 'hover'` implied every file was in scope, which implied the
# `outside` list was empty, which made the branch that appends a ('git', ...)
# violation UNREACHABLE. A genuine scope breach -- a hover commit touching
# api/sd-data.js -- came back 'unattributed' and never reached the branch
# written to catch it. MEASURED over all 6,564 commits in this repo: 31
# attributed to hover, ZERO reaching that branch.
#
# WHY NO CONTROL CAUGHT IT, and this is the part worth keeping: arms F12 and
# F14 drive write_report() with a FABRICATED violation tuple. They prove the
# REPORT says "SEPARATION VIOLATION" when handed one. They never ask whether
# anything can produce one. An arm that tests the REPORTING of a finding is not
# an arm that tests its DETECTION.
#
# WHAT CAN ACTUALLY BE DETECTED FROM GIT, and it is narrower than it looks.
# Every commit on this platform carries the same author, so git cannot say who
# made one. The ONLY handle is the exclusive signature: nothing but the auditor
# should be writing `.claude/skills/sairn-hover-auditor/`. A commit touching
# that AND something outside the auditor's scope is the breach shape.
#
# BUT IT IS AMBIGUOUS ON ITS OWN, so it is NOT asserted as a breach. 8165d1ba
# is a real BUILD AGENT commit to that directory -- a skill mirror -- and a
# mirror sweep touching several skill directories at once would produce exactly
# this shape while being nobody's breach. So the self-log is the second signal:
# only when the auditor's own record NAMES the sha is it reported as a
# violation. Otherwise it is a QUESTION, printed and filed as could-not-run,
# never silently dropped and never asserted.
def signature_subset_of_scope():
    """The invariant every line of reasoning above rests on.

    Checked at runtime rather than asserted in a comment, because the whole
    account of why the old branch was dead -- and why the new detection needs
    to exist -- is void if somebody edits the constants so a signature path is
    no longer in scope.
    """
    return all(_under(p, AUDITOR_SCOPE) for p in AUDITOR_SIGNATURE)


def mixed_signature_commits(commits):
    """[(commit, out_of_scope_paths)] for the breach shape git can see.

    Touches the auditor's EXCLUSIVE signature AND something outside its scope.
    A commit with no signature file is not attributable to the auditor at all
    however far out of scope it is, and a pure in-scope auditor commit is not a
    breach -- both are controls in the probe rather than assumptions here.
    """
    out = []
    for k in commits:
        files = k.get('files') or []
        if any(is_auditor_signature(p) for p in files):
            outside = [p for p in files if not in_auditor_scope(p)]
            if outside:
                out.append((k, outside))
    return out


def classify_mixed(mixed, named_shas, violations, could_not_run):
    """Split mixed-signature commits by whether the self-log claims them.

    NAMED BY THE LOG -> a VIOLATION: two independent sources agreeing, the
    auditor's own record and the file list in git.

    NOT NAMED -> a QUESTION, filed as could-not-run so the run cannot exit 0.
    Both readings are printed because only one of them is an accusation, and
    asserting the wrong one about another agent is the failure this file has
    already made twice today.
    """
    for k, outside in mixed:
        sha = k['sha']
        if any(_sha_prefix_match(sha, n) for n in named_shas):
            violations.append(
                ('git', sha[:8],
                 k.get('subject', ''),
                 outside))
        else:
            could_not_run.append(
                'commit %s touches the auditor\'s exclusive signature AND %d '
                'path(s) outside its scope (%s), and the self-log does NOT '
                'name it. That is either a scope breach the auditor did not '
                'record, or a BUILD AGENT touching the skill mirror alongside '
                'its own work -- 8165d1ba is a real commit of the second kind. '
                'This tool cannot tell them apart and is not guessing.'
                % (sha[:8], len(outside), ', '.join(outside[:4])))


def attribute(commit):
    """(who, how). `who` is a session name, 'hover', or None for unattributed."""
    files = commit['files']
    who = set()
    for p in files:
        m = CLAIM_RE.match(p)
        if m and m.group(1) in SESSIONS:
            who.add(m.group(1))
        m = WORKLOG_RE.match(p)
        if m and m.group(1) in SESSIONS:
            who.add(m.group(1))
    if len(who) == 1:
        return who.pop(), 'bookkeeping'
    if len(who) > 1:
        return None, 'multiple-sessions'
    if files and all(is_auditor_signature(p) for p in files):
        return 'hover', 'signature-only'
    return None, 'unattributed'


# ── the auditor's own black box ─────────────────────────────────────────────

def find_hover_log():
    env = os.environ.get('SAIRN_HOVER_LOG')
    if env:
        return env if os.path.isfile(env) else None
    base = os.path.join(os.path.expanduser('~'), '.claude', 'projects')
    if not os.path.isdir(base):
        return None
    hits = []
    for name in sorted(os.listdir(base)):
        p = os.path.join(base, name, 'hover-audit-log', 'hover-audit-log.jsonl')
        if os.path.isfile(p):
            hits.append(p)
    # ── MORE THAN ONE IS NOW THE EXPECTED SHAPE (2026-09-22) ─────────────────
    # This used to return the bare LIST on count > 1, and both callers read that
    # as "none of them is authoritative" and refused. The reasoning was sound
    # when one hover instance existed: two black boxes for one role meant
    # somebody had a second copy.
    #
    # A SECOND INSTANCE IS NOW A DELIBERATE THROUGHPUT DECISION, and the moment
    # hover2 built its own real self-log BOTH tools began refusing for BOTH
    # sessions -- a self-inflicted split-brain caused by the very fix that was
    # wanted. Reproduced live by hover2 before any of this was changed.
    #
    # Each log is still independently OWNED by its directory, which is already a
    # stable identifier, and each is still verified on its own. Nothing is fused:
    # no chain is joined to another and no verdict is averaged with another. The
    # aggregate keeps the precedence both tools already use -- violations beat
    # could-not-run beats clean -- so a second session can never soften a first.
    #
    # find_hover_log() IS KEPT WITH ITS OLD BEHAVIOUR UNCHANGED, deliberately,
    # so any caller still on the single-log contract keeps refusing rather than
    # silently receiving one of several.
    return hits[0] if len(hits) == 1 else (hits or None)


def find_hover_logs():
    """Every self-log on this machine -- 0, 1 or many. The multi-log answer."""
    env = os.environ.get('SAIRN_HOVER_LOG')
    if env:
        return [env] if os.path.isfile(env) else []
    base = os.path.join(os.path.expanduser('~'), '.claude', 'projects')
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        p = os.path.join(base, name, 'hover-audit-log', 'hover-audit-log.jsonl')
        if os.path.isfile(p):
            out.append(p)
    return out


def session_of(path):
    """The owning session, taken from the directory rather than from the file.

    ~/.claude/projects/<session-dir>/hover-audit-log/hover-audit-log.jsonl, so
    the session is two levels up. Derived rather than parsed out of the entries,
    because a log that lied about its own identity is exactly what this tool
    exists to be able to detect.
    """
    d = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    return os.path.basename(d) or path


def _canonical(value):
    """Recursive, sorted-key canonicalisation.

    WRITTEN FROM THE RULE, NOT COPIED FROM hover_log.py. The point of a second
    implementation is that it can DISAGREE; a paste of the first would agree
    with it even when the first is wrong, which is the Ariane 5 lesson CLAUDE.md
    already records -- a second copy is not a second opinion.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return json.dumps(value)
    if isinstance(value, list):
        return '[' + ','.join(_canonical(v) for v in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k) + ':' + _canonical(value[k])
                              for k in sorted(value)) + '}'
    raise TypeError('cannot canonicalise %r' % (value,))


def _digest(prev_digest, entry_without_hash):
    h = hashlib.sha256()
    h.update((prev_digest + '\n').encode('utf-8'))
    h.update((_canonical(entry_without_hash) + '\n').encode('utf-8'))
    return h.hexdigest()


def verify_chain(rows):
    """Re-derive the hash chain. Returns (ok, reason, checked).

    The auditor's own skill sets the standard this implements: "Before trusting
    --verify on a fresh build of this tool, run the negative control ... A
    verifier that has never been shown to fail is not yet a verifier." The
    probe does exactly that to THIS function.

    It recomputes the chain independently rather than calling hover_log.py
    --verify, because a record and its own verifier share a failure: if the
    tool's hashing is wrong, its verifier agrees with it. A second
    implementation is the only thing that can disagree.
    """
    if not rows:
        return False, 'the log is empty', 0
    prev = GENESIS
    for i, r in enumerate(rows):
        if r.get('prev_hash') != prev:
            return False, ('entry %d (seq %s) has prev_hash %r but the previous '
                           'entry hashes to %r'
                           % (i, r.get('seq'), str(r.get('prev_hash'))[:16], prev[:16])), i
        body = {k: v for k, v in r.items() if k != 'hash'}
        if _digest(prev, body) != r.get('hash'):
            return False, ('entry %d (seq %s) does not hash to its stored value '
                           '-- its content was changed after it was written'
                           % (i, r.get('seq'))), i
        prev = r['hash']
    return True, '', len(rows)


def read_hover_log():
    """Returns (rows, path, problem). `problem` non-empty means COULD NOT RUN."""
    path = find_hover_log()
    if path is None:
        return None, None, ('no hover auditor self-log found under '
                            '~/.claude/projects/*/hover-audit-log/. Set '
                            'SAIRN_HOVER_LOG to point at it. Its absence is '
                            'not evidence of anything -- it lives outside this '
                            'repository by design and a clone that is not the '
                            'auditor\'s will not have one.')
    if isinstance(path, list):
        # The single-log contract cannot answer for several, and says so by name
        # rather than picking one. read_hover_logs() is the multi-log answer.
        return None, None, ('MORE THAN ONE self-log found, so the SINGLE-log '
                            'contract cannot answer -- call read_hover_logs() '
                            'instead, which checks each independently. Found '
                            '%d, one per session:\n      %s'
                            % (len(path), '\n      '.join(
                                '%s  (%s)' % (p, session_of(p)) for p in path)))
    try:
        rows = [json.loads(l) for l in io.open(path, encoding='utf-8') if l.strip()]
    except (OSError, ValueError) as exc:
        return None, path, 'the self-log could not be read: %s' % exc
    return rows, path, ''

def read_hover_logs():
    """Every self-log, read independently: [{path, session, rows, problem}].

    One dict per discovered log, never fused. `problem` non-empty on an entry
    means COULD NOT RUN for THAT session and says nothing about the others --
    which is the whole point: hover2 having logged no process pass yet must not
    read as hover1 being stale, and hover1 being fine must not cover for hover2.

    An empty list means no log was found at all, which is the one case that is
    still a single answer. Its absence is not evidence of anything: the logs live
    outside this repository by design and a clone that is not an auditor's has
    none.
    """
    paths = find_hover_logs()
    out = []
    for p in paths:
        try:
            rows = [json.loads(l) for l in io.open(p, encoding='utf-8') if l.strip()]
            problem = ''
        except (OSError, ValueError) as exc:
            rows, problem = None, 'the self-log could not be read: %s' % exc
        out.append({'path': p, 'session': session_of(p),
                    'rows': rows, 'problem': problem})
    return out


def _utc(ts):
    return time.strftime('%Y-%m-%d %H:%M', time.gmtime(ts))


def write_csv(path, trail):
    """Every commit, one row, with how it was attributed and why.

    THE DOCUMENT IS A CLAIM; THIS IS WHAT MAKES IT CHECKABLE. A separation
    report a reader cannot audit is the same thing it is auditing -- an
    assertion. Every row carries the attribution METHOD alongside the verdict,
    so a reader can see which rows rest on a bookkeeping file, which on a
    signature, and which on nothing at all.
    """
    import csv
    with io.open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['sha', 'utc', 'attributed_to', 'attribution_method',
                    'files_changed', 'outside_auditor_scope', 'subject'])
        for r in sorted(trail, key=lambda x: x['ts']):
            w.writerow([r['sha'], _utc(r['ts']), r['who'], r['how'],
                        r['n_files'], len(r.get('outside') or []),
                        r['subject']])


def write_report(path, trail, by_who, hover_commits, violations, could_not_run,
                 log_reports, rc):
    """The evidence document -- the thing somebody is actually shown.

    ── WHY THIS IS NOT JUST THE TERMINAL OUTPUT REDIRECTED ──────────────────
    The stdout report answers an engineer standing at a prompt. This answers
    the different question "what do I hand to a person who was not here", and
    the two need different shapes:

      * It is ANCHORED. A separation claim with no commit tip and no
        generation time is a claim about an unstated moment, and history moves
        every few minutes on this platform. The tip and the timestamp are the
        first two facts in the file.
      * THE AUDITOR'S COMMITS ARE LISTED IN FULL, every one, with its date,
        its subject and its scope verdict. That list IS the proof; a count is
        a summary of the proof and cannot be checked.
      * THE LIMIT COMES FIRST, NOT IN A FOOTNOTE. A reader who takes only the
        headline away must take the caveat with it, so the section saying what
        git CANNOT show sits above every number rather than under them.

    ── WHAT IT DELIBERATELY DOES NOT DO ─────────────────────────────────────
    It does not list all several thousand build-agent commits inline. A
    document nobody reads to the end proves nothing, and the build agents'
    commits are not the claim under test -- the auditor's are. The complete
    table goes to `--csv`, which is named in the document so the reader knows
    the full data exists and where.
    """
    who_rows = by_who.most_common()
    total = sum(n for _w, n in who_rows)
    unattr = by_who.get('UNATTRIBUTED', 0)
    code, tip, _ = git('rev-parse', 'HEAD')
    code2, branch, _ = git('rev-parse', '--abbrev-ref', 'HEAD')
    L = []
    A = L.append
    A('# Hover auditor separation — the audit trail from real git history')
    A('')
    A('Generated **%s UTC** by `tools/hover_separation_audit.py --report`, from'
      % time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()))
    A('`%s` at **`%s`**.' % (branch.strip() or '?', (tip or '?').strip()[:12]))
    A('')
    A('Regenerate it, and check it, with:')
    A('')
    A('```')
    A('python tools/hover_separation_audit.py --report trail.md --csv trail.csv')
    A('```')
    A('')
    A('---')
    A('')
    A('## Read this before any number below')
    A('')
    A('**Git cannot prove the negative here, and this document does not claim '
      'it does.**')
    A('')
    A('All five roles on this platform commit through **one git identity**, so '
      'a commit')
    A('cannot be attributed by its author field. Attribution below is derived '
      'from')
    A('co-changed bookkeeping files — a commit that also touches')
    A('`.claude/claims/<session>.json` or `SAIRN-ACTIVE-WORK-<session>.md` '
      'names its')
    A('session — and from commits that touch **only** the auditor\'s own '
      'directory.')
    A('')
    A('That leaves **%d of %d commits (%.1f%%) UNATTRIBUTED**. A commit in '
      'which the'
      % (unattr, total, 100.0 * unattr / total if total else 0))
    A('auditor wrote platform code would land in exactly that bucket **by '
      'construction**.')
    A('')
    A('So the honest statement of what follows is:')
    A('')
    A('> Of every commit that CAN be attributed, none shows the hover auditor '
      'writing')
    A('> outside its own scope — corroborated by a second, structurally '
      'different')
    A('> source (the auditor\'s own hash-chained log). It is not a proof that '
      'no such')
    A('> commit exists.')
    A('')
    A('---')
    A('')
    A('## Attribution across %d commits' % total)
    A('')
    A('| attributed to | commits | share |')
    A('|---|---:|---:|')
    for who, n in who_rows:
        A('| %s | %d | %.1f%% |' % (who, n, 100.0 * n / total if total else 0))
    A('')
    A('`UNATTRIBUTED` is not a sixth agent. It is the part of history this '
      'method')
    A('cannot speak about, stated as a number rather than omitted.')
    A('')
    A('---')
    A('')
    A('## The auditor\'s commits — all %d, in full' % len(hover_commits))
    A('')
    A('**This list is the proof.** A count would be a summary of it, and a '
      'summary')
    A('cannot be checked. Every commit the auditor is known to have made is '
      'here,')
    A('with what it touched.')
    A('')
    if hover_commits:
        A('| sha | UTC | files | outside its scope | subject |')
        A('|---|---|---:|---:|---|')
        for k in sorted(hover_commits, key=lambda x: x['ts']):
            rec = next((r for r in trail if r['sha'] == k['sha']), {})
            outside = rec.get('outside') or []
            A('| `%s` | %s | %d | **%s** | %s |'
              % (k['sha'][:8], _utc(k['ts']), len(k['files']),
                 ('%d — VIOLATION' % len(outside)) if outside else '0',
                 k['subject'].replace('|', '\\|')[:90]))
        A('')
        A('Span: **%s** to **%s** UTC.'
          % (_utc(min(k['ts'] for k in hover_commits)),
             _utc(max(k['ts'] for k in hover_commits))))
    else:
        A('_No commits attributed to the auditor in this history._')
    A('')
    A('---')
    A('')
    A('## The second source: the auditor\'s own hash-chained log')
    A('')
    A('A record and its own verifier share a failure, so the chain below is '
      're-derived')
    A('independently by this tool rather than by calling the log\'s own '
      '`--verify`.')
    A('')
    # ── ONE SUBSECTION PER SESSION (2026-09-22) ──────────────────────────
    # This rendered ONE table because there was one log, and step 2's rename of
    # the parameter left the body still saying `log_report` -- a latent
    # NameError that only --report would have hit, which is why it was found by
    # reading rather than by running. It now loops, and never merges two
    # sessions into one row: a reader who cannot tell which instance a figure
    # came from cannot use the peer check the second instance exists for.
    if not log_reports:
        A('**COULD NOT RUN.** The self-log was not readable from this clone, '
          'so the')
        A('git half above stands alone — and on its own it cannot prove the '
          'negative.')
        A('This is reported as unanswered, not as a pass.')
    else:
      for _sess in sorted(log_reports):
        log_report = log_reports[_sess]
        A('#### %s' % _sess)
        A('')
        A('| | |')
        A('|---|---|')
        A('| entries | %s |' % log_report.get('entries', '?'))
        A('| hash chain, re-derived independently | **%s** |'
          % str(log_report.get('chain', '?')).upper())
        A('| SHAs the log claims as its own | %s |' % log_report.get('claimed', '?'))
        A('| …that resolve in this clone | %s |' % log_report.get('resolved', '?'))
        A('| …of those, out of scope | **%s** |' % log_report.get('violations', '?'))
        unres = log_report.get('unresolved') or []
        if unres:
            A('| …that do NOT resolve here | %d |' % len(unres))
        A('')
        # THE DOCUMENT IS THE THING A READER IS HANDED, so a suppressed match
        # has to appear HERE too. A row that only counts what was checked reads
        # identically whether nothing was suppressed or something was.
        _cited = log_report.get('cited') or {}
        _disp = log_report.get('disputed') or []
        if _cited:
            A('%d further match(es) of the same phrasing are **not counted as '
              'the auditor\'s own**, and are' % len(_cited))
            A('listed rather than dropped — a silent suppression and a genuine '
              'attribution look the')
            A('same from a count:')
            A('')
            for _sha in sorted(_cited):
                A('- **CITED `%s`** — %s' % (_sha, '; '.join(_cited[_sha])))
            A('')
        if _disp:
            A('%d match(es) are **DISPUTED** — exactly one attribution signal '
              'fired, so they are still' % len(_disp))
            A('scope-checked above and are reported as contested rather than '
              'asserted: %s'
              % ', '.join('`%s`' % s for s in _disp))
            A('')
        if unres:
            A('The unresolvable SHAs are **explained by measurement, not by a '
              'plausible story**:')
            A('the log names both ends of a rewrite ("Committed a, pushed b"), '
              'and in every')
            A('such pair the local sha is absent while the pushed one is '
              'present — which is')
            A('what a rebase-before-push produces. Any that remain unpaired '
              'are listed as')
            A('unexplained in the tool\'s own output and are why it exits 2 '
              'rather than 0.')
        A('')
    A('')
    A('---')
    A('')
    A('## Verdict')
    A('')
    if violations:
        A('**%d SEPARATION VIOLATION(S) FOUND.**' % len(violations))
        A('')
        for src, sha, subj, paths in violations:
            A('- `%s` (%s) — %s' % (sha, src, subj[:80]))
            for p in paths[:8]:
                A('    - `%s`' % p)
    elif could_not_run:
        A('**No violation found in what could be checked — and part of the '
          'check did')
        A('not run.** That is not a clean bill, and it is written this way on '
          'purpose:')
        A('')
        for c in could_not_run:
            A('- %s' % c)
    else:
        A('**No separation violation found by either source**, bounded by the '
          'coverage')
        A('stated at the top.')
    A('')
    A('Tool exit code: **%d** (0 clean, 1 violation, 2 could-not-run).' % rc)
    A('')
    A('---')
    A('')
    A('## Checking this document rather than believing it')
    A('')
    A('`--csv` writes the **complete** per-commit table — every commit, its '
      'attribution')
    A('and the METHOD that attributed it, so a reader can see which rows rest '
      'on a')
    A('bookkeeping file, which on a signature, and which on nothing at all.')
    A('')
    A('The enforcement that sits beside this report, rather than describing '
      'it:')
    A('')
    A('- `tools/hover_auditor_scope_gate.py` — refuses the commit before it '
      'exists (local)')
    A('- `.github/workflows/hover-separation.yml` — the same question on '
      'GitHub\'s side,')
    A('  off the author\'s machine, where its verdict is a status rather than '
      'an honour system')
    A('')
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(L) + '\n')



def _selflog_one(rows, path, session, hover_commits, violations, could_not_run):
    """One session's self-log, checked on its own. Returns its report dict.

    LIFTED VERBATIM FROM main() (2026-09-22) rather than rewritten. The body was
    never the defect -- it verifies a chain and cross-checks claimed SHAs
    correctly, and did so for the single log it was handed. What was wrong was the
    assumption that there is exactly one. So this is the same code called once per
    session, with `violations` and `could_not_run` accumulating across sessions
    exactly as they did for one.

    NOTHING IS FUSED. Each call sees one log: no chain is joined to another and no
    verdict is averaged with another. A session that COULD NOT RUN records that
    for itself and says nothing about the others -- which is the point, because
    hover2 having logged no process pass yet must not read as hover1 being stale,
    and hover1 being fine must not cover for hover2.
    """
    report = {}
    ok, why, checked = verify_chain(rows)
    # The aggregate header is printed once by main(); this used to print its own
    # because it WAS the only one. Left as the path alone so a reader sees which
    # file each per-session block is about.
    print('  %s' % path)
    print('  %d entries; hash chain re-derived independently: %s'
          % (len(rows), 'INTACT' if ok else 'BROKEN'))
    if not ok:
        print('  %s' % why)
        print('')
        print('  REFUSING to report from a record whose chain does not')
        print('  verify. A tampered black box is worse than none, because')
        print('  it reads as evidence.')
        could_not_run.append('self-log chain broken at entry %d: %s' % (checked, why))
    else:
        # ── ATTRIBUTION, PER MATCH, WITH PRECEDENCE PER SHA ──────────────
        # A sha may appear twice in one log: claimed outright in one entry and
        # quoted from somebody else in another. OWN wins over DISPUTED wins
        # over CITED, so one unambiguous claim is never cancelled by a later
        # citation of the same sha.
        RANK = {'own': 2, 'disputed': 1, 'cited': 0}
        seen = {}
        for r in rows:
            summary = r.get('summary') or ''
            blob = summary + ' ' + (r.get('ref') or '')
            for m in OWN_COMMIT_RE.finditer(blob):
                sha = m.group(1)
                # `session` is the OWNING DIRECTORY, not anything the entry
                # says about itself -- the same identity source session_of()
                # already uses, and for the same reason: a log that named its
                # own session could clear its own commits by writing "hover2".
                verdict, why = classify_own_commit(
                    summary, r.get('ref') or '', sha, m.start(), session)
                if sha not in seen or RANK[verdict] > RANK[seen[sha][0]]:
                    seen[sha] = (verdict, r.get('seq'), why)
        claimed = {s for s, v in seen.items() if v[0] in ('own', 'disputed')}
        disputed = {s for s, v in seen.items() if v[0] == 'disputed'}
        cited = {s: v for s, v in seen.items() if v[0] == 'cited'}
        resolved, unresolved = {}, []
        for s in sorted(claimed):
            code, out, _ = git('rev-parse', '--verify', s + '^{commit}')
            if code != 0:
                unresolved.append(s)
            else:
                resolved[s] = out.strip()
        log_bad = []
        for short, full in sorted(resolved.items()):
            code, out, _ = git('show', '--name-only', '--format=', full)
            files = [l.strip().replace('\\', '/') for l in out.split('\n') if l.strip()]
            outside = [p for p in files if not in_auditor_scope(p)]
            if outside:
                log_bad.append((short, outside))
                # THE WORDING CARRIES THE ATTRIBUTION STATE. "Named by the
                # auditor as its own" is an accusation, and asserting it over a
                # one-signal match is what made 270c60ed read as damning.
                how = ('attribution DISPUTED -- matched the auditor\'s own '
                       'phrasing, but %s' % '; '.join(seen[short][2])
                       if short in disputed
                       else 'named by the auditor as its own')
                violations.append(('self-log', short, how, outside))
        git_hover = {k['sha'] for k in hover_commits}
        named_full = set(resolved.values())
        print('  SHAs the log names as its OWN commits/pushes: %d' % len(claimed))
        # A SUPPRESSED MATCH IS PRINTED, ALWAYS. If CITED were silent, the
        # difference between "correctly attributed to another session" and "a
        # real violation the classifier swallowed" would be invisible, which is
        # the failure this whole change exists to avoid repeating in reverse.
        if cited:
            print('    plus %d match(es) NOT counted as the auditor\'s own, '
                  'shown rather than dropped:' % len(cited))
            for sha in sorted(cited):
                _v, _seq, _why = cited[sha]
                print('      CITED %s (entry %s) -- %s'
                      % (sha, _seq, '; '.join(_why)))
        if disputed:
            print('    %d match(es) are DISPUTED -- one attribution signal '
                  'fired, so they are still checked below:' % len(disputed))
            for sha in sorted(disputed):
                print('      DISPUTED %s (entry %s) -- %s'
                      % (sha, seen[sha][1], '; '.join(seen[sha][2])))
        print('    resolve in this clone : %d' % len(resolved))
        print('    of those, in scope    : %d' % (len(resolved) - len(log_bad)))
        print('    of those, VIOLATIONS  : %d' % len(log_bad))
        for short, outside in log_bad:
            print('      VIOLATION %s -> %s' % (short, ', '.join(outside[:6])))
        # ── THE UNRESOLVABLE HALF, EXPLAINED BY MEASUREMENT ─────────────
        # The obvious reading is "a rebase before push rewrote the sha, so
        # the local object never reached this clone." That is a hypothesis,
        # and the log itself can test it: entries of the form "Committed a,
        # pushed b" name both ends of exactly that rewrite. If the
        # hypothesis holds, a is absent and b is present, every time.
        paired, pair_ok = {}, 0
        for r in rows:
            m = PAIR_RE.search(r.get('summary') or '')
            if m:
                local, pushed = m.group(1), m.group(2)
                paired[local] = pushed
                if local not in resolved and pushed in resolved:
                    pair_ok += 1
        explained = [s for s in unresolved if s in paired and paired[s] in resolved]
        unexplained = [s for s in unresolved if s not in explained]
        print('    DO NOT RESOLVE here   : %d' % len(unresolved))
        if unresolved:
            print('      %d of %d are EXPLAINED rather than assumed away: the'
                  % (len(explained), len(unresolved)))
            print('      log names both ends of the rewrite ("Committed a,')
            print('      pushed b"), and the pushed counterpart resolves here')
            print('      and is in scope. Tested over every such pair in the')
            print('      log: %d of %d have the local sha ABSENT and the'
                  % (pair_ok, len(paired)))
            print('      pushed one PRESENT, which is what a rebase-before-')
            print('      push produces and nothing else here does.')
            if unexplained:
                print('      %d are NOT explained and are NOT shown to be clean'
                      % len(unexplained))
                print('      by this tool: %s' % ', '.join(unexplained[:10]))
                could_not_run.append(
                    '%d sha(s) the self-log claims are unresolvable in this '
                    'clone and unpaired: %s'
                    % (len(unexplained), ', '.join(unexplained[:6])))
        only_git = sorted(git_hover - named_full)
        print('    git-visible auditor commits NOT named by the log: %d'
              % len(only_git))
        for s in only_git[:10]:
            code, out, _ = git('log', '-1', '--format=%s', s)
            print('      %s %s' % (s[:8], out.strip()[:58]))
        report = {'entries': len(rows), 'chain': 'intact',
                      'claimed': len(claimed), 'resolved': len(resolved),
                      'unresolved': unresolved, 'violations': len(log_bad),
                      'cited': {s: cited[s][2] for s in cited},
                      'disputed': sorted(disputed),
                      # THE FULL SHAs THIS LOG NAMES AS ITS OWN, already
                      # resolved through `git rev-parse` above. Carried out so
                      # the git half can use them as its SECOND signal rather
                      # than resolving the same shas a second time.
                      'named': sorted(resolved.values()),
                      'git_only': [s[:8] for s in only_git]}
    
    return report

def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--trail', action='store_true',
                    help='print the per-commit audit trail, not just the summary')
    ap.add_argument('--authors', action='store_true',
                    help='print every distinct git author, to prove the one-identity claim')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--report', metavar='PATH', default=None,
                    help='write the evidence DOCUMENT -- the thing you hand to '
                         'somebody, rather than a terminal dump')
    ap.add_argument('--csv', metavar='PATH', default=None,
                    help='write the FULL per-commit table, so a reader can '
                         'check the document rather than believe it')
    args = ap.parse_args(argv)

    could_not_run = []
    violations = []

    if args.authors:
        code, out, err = git('log', '--all', '--format=%an <%ae>')
        if code != 0:
            print('COULD NOT RUN: ' + err.strip())
            return 2
        c = Counter(l for l in out.split('\n') if l.strip())
        print('Distinct git authors across all history:')
        for a, n in c.most_common():
            print('  %6d  %s' % (n, a))
        print('')
        print('ONE identity for five roles is why attribution in this tool is')
        print('derived from co-changed bookkeeping files and is incomplete.')
        return 0

    commits, err = load_commits()
    if commits is None:
        print('COULD NOT RUN: ' + err)
        return 2

    by_who = Counter()
    trail = []
    hover_commits = []
    for k in commits:
        who, how = attribute(k)
        by_who[who or 'UNATTRIBUTED'] += 1
        rec = {'sha': k['sha'], 'short': k['sha'][:8], 'ts': k['ts'],
               'who': who or 'UNATTRIBUTED', 'how': how,
               'subject': k['subject'], 'n_files': len(k['files'])}
        if who == 'hover':
            hover_commits.append(k)
            # KEPT, AND IT IS STRUCTURALLY EMPTY BY THE INVARIANT ABOVE.
            # who == 'hover' means every file is under AUDITOR_SIGNATURE, which
            # is inside AUDITOR_SCOPE, so this list cannot be non-empty while
            # signature_subset_of_scope() holds. The report still prints it, so
            # a constants edit that broke the invariant would show here -- and
            # the invariant itself is checked below rather than assumed.
            rec['outside'] = [p for p in k['files'] if not in_auditor_scope(p)]
            if rec['outside']:
                violations.append(('git', k['sha'][:8], k['subject'], rec['outside']))
        trail.append(rec)

    # ── THE DETECTION THAT REPLACES THE DEAD BRANCH ──────────────────────
    if not signature_subset_of_scope():
        could_not_run.append(
            'AUDITOR_SIGNATURE is no longer inside AUDITOR_SCOPE, so the git '
            'half\'s reasoning about which commits can breach scope does not '
            'hold. Refusing to report from it rather than reasoning from a '
            'premise somebody edited out.')
    mixed = mixed_signature_commits(commits)

    total = len(commits)
    unattr = by_who['UNATTRIBUTED']

    print('')
    print('HOVER AUDITOR SEPARATION -- AUDIT TRAIL FROM REAL HISTORY')
    print('=' * 72)
    print('')
    print('COVERAGE FIRST, because every number below is bounded by it.')
    print('  %d commits examined. %d (%.1f%%) are UNATTRIBUTED -- no bookkeeping'
          % (total, unattr, 100.0 * unattr / total if total else 0))
    print('  file names their session and they touch paths outside the auditor\'s')
    print('  scope. UNATTRIBUTED DOES NOT MEAN "a build agent\'s".')
    print('')
    print('  A commit in which the auditor DID write platform code would land in')
    print('  that bucket by construction. Git alone therefore cannot prove the')
    print('  negative, and this section does not claim to.')
    print('')
    print('ATTRIBUTION')
    for who, n in by_who.most_common():
        print('  %-14s %6d  %5.1f%%' % (who, n, 100.0 * n / total if total else 0))
    print('')

    print('THE AUDITOR\'S KNOWN COMMITS: %d' % len(hover_commits))
    if hover_commits:
        span = (min(k['ts'] for k in hover_commits), max(k['ts'] for k in hover_commits))
        import time
        print('  first %s, last %s (UTC)'
              % (time.strftime('%Y-%m-%d %H:%M', time.gmtime(span[0])),
                 time.strftime('%Y-%m-%d %H:%M', time.gmtime(span[1]))))
    bad_git = [v for v in violations if v[0] == 'git']
    print('  touching anything outside the auditor\'s scope: %d' % len(bad_git))
    for v in bad_git:
        print('    VIOLATION %s %s' % (v[1], v[2][:60]))
        for p in v[3][:8]:
            print('        %s' % p)
    print('')

    # ── the second, structurally different source ────────────────────────
    # ONE LOG PER SESSION, EACH CHECKED INDEPENDENTLY (2026-09-22). This called
    # read_hover_log() and refused outright the moment two logs existed -- which
    # happened the day a second hover instance was deliberately started, so BOTH
    # tools began refusing for BOTH sessions at once. A self-inflicted split-brain
    # caused by the very throughput fix that was wanted.
    #
    # REPRODUCED LIVE BY hover2 BEFORE ANYTHING HERE CHANGED, and routed out to
    # the build side rather than self-applied: tools/ is outside the auditor's own
    # scope gate by design, and this file's own docstring says it is maintained
    # from the build side because an auditor enforcing its own separation proves
    # nothing about the case where the auditor is the problem.
    log_reports = {}
    _logs = read_hover_logs()
    if not _logs:
        problem = ('no hover auditor self-log found under '
                   '~/.claude/projects/*/hover-audit-log/. Set SAIRN_HOVER_LOG '
                   'to point at it. Its absence is not evidence of anything -- '
                   'it lives outside this repository by design and a clone that '
                   "is not the auditor's will not have one.")
        could_not_run.append('self-log cross-reference: ' + problem)
        print('SELF-LOG CROSS-REFERENCE -- COULD NOT RUN')
        print('  %s' % problem)
        print('')
        print('  This is reported as COULD NOT RUN and NOT as a pass. The git')
        print('  half above cannot prove the negative on its own, so without')
        print('  this the question is open, not answered.')
        print('')
    else:
        print('SELF-LOG CROSS-REFERENCE -- %d log(s) found, one per session, '
              'each checked independently:' % len(_logs))
        print('')
        for _lg in _logs:
            print('-- %s --' % _lg['session'])
            if _lg['problem']:
                could_not_run.append('self-log cross-reference (%s): %s'
                                     % (_lg['session'], _lg['problem']))
                print('  COULD NOT RUN: %s' % _lg['problem'])
                print('')
                continue
            log_reports[_lg['session']] = _selflog_one(
                _lg['rows'], _lg['path'], _lg['session'],
                hover_commits, violations, could_not_run)
            print('')

    # ── THE GIT HALF'S SECOND SIGNAL, WHICH IS THE SELF-LOG ─────────────
    # Deliberately AFTER the self-log pass: a mixed-signature commit is only
    # asserted as a breach when the auditor's own record names it, and that
    # set does not exist until the logs have been read.
    print('MIXED-SIGNATURE COMMITS -- the only breach shape git alone can see:')
    _named = set()
    for _r in log_reports.values():
        _named.update(_r.get('named') or [])
    if not mixed:
        print("  0 found. A commit touching the auditor's exclusive signature")
        print('  AND a path outside its scope is what this looks for. There are')
        print('  none in %d commits -- ARMED AND UNEXERCISED, which is not the' % total)
        print('  same as tested: the controls drive it on synthetic commits.')
    else:
        print('  %d found. Each is checked against the self-log, because the'
              % len(mixed))
        print('  shape alone is ambiguous -- a build agent touching the skill')
        print('  mirror alongside its own work produces it too.')
        for _k, _out in mixed:
            print('    %s %s' % (_k['sha'][:8], _k.get('subject', '')[:54]))
            print('       outside scope: %s' % ', '.join(_out[:5]))
    classify_mixed(mixed, _named, violations, could_not_run)
    print('')

    print('=' * 72)
    if violations:
        print('RESULT: %d SEPARATION VIOLATION(S) FOUND.' % len(violations))
        rc = 1
    elif could_not_run:
        print('RESULT: NO VIOLATION FOUND IN WHAT COULD BE CHECKED, and part of')
        print('the check DID NOT RUN. That is not a clean bill:')
        for c in could_not_run:
            print('  - %s' % c)
        rc = 2
    else:
        print('RESULT: no separation violation found by either source.')
        print('Bounded by the coverage stated at the top: the git half cannot')
        print('prove the negative, and the self-log half is as complete as the')
        print('auditor\'s own record-keeping.')
        rc = 0
    print('')

    if args.trail:
        print('PER-COMMIT TRAIL (auditor commits and violations only; the full')
        print('%d-commit table is what --json carries)' % total)
        for rec in trail:
            if rec['who'] == 'hover' or rec.get('outside'):
                print('  %s  %-8s %-12s %s'
                      % (rec['short'], rec['who'], rec['how'], rec['subject'][:52]))
        print('')

    if args.json:
        print(json.dumps({'total': total, 'attribution': dict(by_who),
                          'auditor_commits': [k['sha'][:8] for k in hover_commits],
                          'violations': violations, 'could_not_run': could_not_run,
                          'self_log': log_reports, 'trail': trail if args.trail else []},
                         indent=1))

    if args.report:
        write_report(args.report, trail, by_who, hover_commits, violations,
                     could_not_run, log_reports, rc)
        print('wrote %s' % args.report)
    if args.csv:
        write_csv(args.csv, trail)
        print('wrote %s (%d rows -- the whole table, so a reader can check '
              'rather than believe)' % (args.csv, len(trail)))
    return rc


if __name__ == '__main__':
    sys.exit(main())
