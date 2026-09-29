#!/usr/bin/env python
"""hover_citation_linter.py -- the standing self-check scoped and justified in
docs/2026-09-29-hover-gap-research-h2.md's third pass: a deterministic,
non-LLM pre-flight check against Class A of this role's own real,
counted mistakes this session (stale-fact reuse -- seq 276, 308, 320),
which by this role's own 3-strikes rule (item 3, same document) already
earned a permanent guard rather than another logged note.

WHAT THIS ACTUALLY CATCHES, STATED NARROWLY, NOT OVERSOLD.

  (1) REPEATED-COUNT STALENESS -- a "N of N" or "N/N" claim (this log's own
      recurring checked/universe phrasing) where N no longer matches either
      of the two real totals this tool can independently recompute: the
      current B/C pool size (parsed fresh from docs/CRITICALITY-TIERS.md,
      same TIER_ROW rule as hover_cold_scan_pool.py) and the current total
      entry count of THIS log. This is the exact, complete shape of seq
      308's real mistake ("123 of 123" written when the real, current pool
      was already 122) -- tested below against seq 307's own real, byte-
      faithful historical text, not a paraphrase.

  (2) BACKWARD SEQ-REFERENCE TARGET MISMATCH -- for every "seq N" citation
      in a draft, if N refers to an ALREADY-EXISTING entry, does that
      entry's own real `target` field share at least one token with the
      CURRENT entry's own `--target`. This generalises the exact mechanical
      check append_entry()'s own --contradicts field already uses (ref_tokens
      & cur_tokens) to EVERY seq citation, not only that one field. Tested
      below against real seq 274/275 (leg_insurance's real filed seq versus
      the sweep-summary's real, different target) -- the same underlying
      shape as seq 276's real correction.

  WHAT THIS DOES NOT CATCH, NAMED HONESTLY RATHER THAN LEFT IMPLIED. Seq
  276's OWN real incident was a FORWARD SELF-REFERENCE: the sweep-summary
  entry cited "seq 275" for itself, guessing its own not-yet-assigned
  number, before append_entry() had assigned it -- structurally uncheckable
  by ANY tool at write time, because the real number literally does not
  exist yet to compare against. Check (2) above catches the common,
  backward-reference form of the same MISTAKE SHAPE (citing an existing
  entry for the wrong topic); it does not and cannot catch this narrower,
  forward-looking sub-case. The real fix for that one is procedural: file
  the OTHER entry first, then cite its real, already-assigned number
  afterward -- never guess your own next seq number in a draft.

  Seq 320's real incident (a stale premise about a THIRD-PARTY file's
  CURRENT state, reused from an earlier turn's memory instead of re-checked
  at the moment of writing) is a different failure class entirely -- no
  seq or count pattern is involved at all, so this tool has nothing to say
  about it. That gap is real and is not this tool's to close; the existing
  --source staleness guard in hover_log.py already covers the platform
  repo's own files for type=finding, and has no way to reach a file in a
  different repo (H1's directory) at all -- a genuinely separate, harder
  problem this tool does not pretend to solve.

TWO NAMED LIMITS, closed or bounded on 2026-09-29 after real end-to-end
runs against this session's own drafts surfaced both live, not
hypothetically.

  LIMIT 1, CLOSED: CROSS-LOG CITATIONS READ AS NOT-FOUND. A citation to
  H1's log (e.g. "seq 603", "seq 427" -- real numbers from real entries
  this session cited) previously read identically to a genuine typo or a
  citation to a seq that plain does not exist anywhere -- a real false-
  negative shape, since a citation that IS real (just not in THIS log)
  deserves a different, calmer verdict than one that is simply wrong.
  FIXED: check_seq_refs() now also loads H1's real log (read-only, this
  role already has read access to it all session) and, for any seq NOT
  FOUND in this log, checks whether it exists there instead. If so, the
  verdict is UNVERIFIED-CROSS-LOG, a THIRD state, never folded into either
  OK or NOT-FOUND -- it means exactly what it says: this tool cannot check
  a citation into a log it does not own, and says so, rather than guessing
  clean or guessing wrong. Counted and reported separately in every run.

  LIMIT 2, BOUNDED, NOT ELIMINATED: SAME-BATCH SIBLING FALSE POSITIVES.
  A sweep-summary entry legitimately citing several sibling findings by
  seq (each about a DIFFERENT resource than the summary's own umbrella
  --target) used to read as TARGET-MISMATCH for every sibling, every time
  -- a real, disclosed nuisance rate confirmed live against real seq
  274/275/270/273 text. PARTIALLY FIXED: extract_seq_refs() now also
  captures the resource-name-SHAPED words (lowercase, underscore-
  containing) in the ~80 characters immediately BEFORE each citation --
  cheap local context, not a full parse. check_seq_refs() checks that
  local context against the referenced entry's real target FIRST; a match
  there downgrades the verdict to OK-LOCAL-MATCH (a fourth, distinct
  state, so a reader can tell "matched by local wording" apart from
  "matched by the whole entry's own --target"). This closes the exact
  case demonstrated in this file's own selftest (citing "sv_financials --
  FILED seq 270" from within a sweep-summary entry). It does NOT close
  every case -- a citation with no resource-name-shaped word nearby, or
  phrased differently, still falls back to the original whole-entry-target
  check and can still read TARGET-MISMATCH. Named honestly as bounded, not
  claimed as solved.

USAGE, THE "WIRED TO RUN EVERY ROUND" COMMITMENT. This is a standalone
advisory tool, not a hard gate inside hover_log.py's own append_entry() --
its checks are heuristic (a token-overlap match can be a false positive on
a legitimate cross-topic citation, the same disclosed trade-off this
directory's other heuristic scanners already carry, e.g.
peer_authority_trace_scan.py) and mixing a soft warning into a function
whose entire existing contract is hard ValueError refusals would blur two
genuinely different risk profiles. From this point forward, every
`hover_log.py --append` in this role's own practice is preceded by a
`--lint` pass on the draft text -- a practice commitment backed by a real,
always-available tool, not a code-level gate on a probabilistic heuristic.

Run:
  python hover_citation_linter.py --lint --target "..." --file DRAFT.txt
  python hover_citation_linter.py --lint --target "..." --text "..."
  python hover_citation_linter.py --selftest
"""
import hashlib
import io
import os
import re
import subprocess
import sys

LINT_TOKEN_LEN = 16


def lint_token_for(text):
    """Same formula as hover_log.py's own lint_token_for(), kept
    independently defined here rather than imported (the same not-imported
    discipline current_pool_size() already states) -- --lint prints this
    token so it can be pasted straight into hover_log.py --append
    --rotation-batch --lint-token, proving a real lint pass ran against
    this EXACT summary text."""
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()[:LINT_TOKEN_LEN]

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, 'hover-audit-log.jsonl')
DEFAULT_TIERS = os.path.join(
    r'C:\Users\marsh\Documents\SAIRN-hover2', 'docs', 'CRITICALITY-TIERS.md')
# H1's real log, read-only -- this role has had read access to this exact
# path all session (every cross-instance validation this role has done
# reads it). Used ONLY to distinguish a genuine typo from a citation into
# a log this tool does not own; never written to, never trusted as this
# tool's own chain (that would need re-implementing verify_chain(), which
# is deliberately out of scope -- see load_rows()'s own docstring).
H1_LOG_PATH = (r'C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-'
              r'SAIRN-hover\hover-audit-log\hover-audit-log.jsonl')

TIER_ROW = re.compile(r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|\s*\*{0,2}([ABC])\*{0,2}\s*\|")
SEQ_REF = re.compile(r'\bseqs?[\s-]+(\d+(?:\s*[/,]\s*\d+)*)', re.I)
REPEATED_OF = re.compile(r'\b(\d+)\s+of\s+(\d+)\b', re.I)
REPEATED_SLASH = re.compile(r'\b(\d+)\s*/\s*(\d+)\b')
# lowercase, underscore-containing -- the real shape of every resource name
# and every mistake-class label in this log's own vocabulary (sv_financials,
# stale-fact-reuse); a cheap, real proxy for "a topic word sits right here",
# not a claim to understand English.
RESOURCE_WORD = re.compile(r'\b([a-z][a-z0-9]*[_-][a-z0-9_-]+)\b')
LOCAL_CONTEXT_WINDOW = 80


def load_rows(path=LOG_PATH):
    """[dict] -- every entry, parsed as plain JSON lines. Pure text read;
    does NOT verify the chain (that is hover_log.py --verify's job, not
    this tool's -- a citation linter checking citations should not also
    silently re-implement chain verification and risk disagreeing with the
    real verifier)."""
    import json
    rows = []
    if not os.path.isfile(path):
        return rows
    with io.open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def current_pool_size(tiers_path=DEFAULT_TIERS):
    """The Integrity-axis Tier-B row count, re-derived fresh from the real
    register text -- same rule as hover_cold_scan_pool.py's own
    _parse_tier_rows, kept independent (not imported) so a bug in one
    cannot silently propagate into the other's answer."""
    if not os.path.isfile(tiers_path):
        return None
    n = 0
    with io.open(tiers_path, encoding='utf-8') as f:
        for line in f:
            m = TIER_ROW.match(line.strip())
            if m and m.group(2) == 'B':
                n += 1
    return n


def extract_seq_refs(text):
    """[(seq, local_context_frozenset)] -- every seq number cited in TEXT:
    'seq 123', 'seq-123', 'seqs 123/124', 'seqs 123, 124', '(seq 123)'.
    Order preserved, duplicates kept. local_context is the set of
    resource-name-SHAPED words found in the LOCAL_CONTEXT_WINDOW characters
    immediately before the match -- e.g. 'sv_financials' in "sv_financials
    -- FILED seq 270" -- a cheap proxy for what topic the citation is
    actually about, independent of the whole entry's own --target."""
    text = text or ''
    out = []
    for m in SEQ_REF.finditer(text):
        window_start = max(0, m.start() - LOCAL_CONTEXT_WINDOW)
        local = frozenset(w.lower() for w in
                          RESOURCE_WORD.findall(text[window_start:m.start()]))
        for part in re.split(r'[/,]', m.group(1)):
            part = part.strip()
            if part.isdigit():
                out.append((int(part), local))
    return out


def extract_repeated_count_claims(text):
    """[(n, matched_text)] -- every 'N of N' or 'N/N' pattern (same number
    both sides) in TEXT, the exact recurring shape of this log's own
    checked/universe claims. A differing pair ('107 of 122', a genuine
    partial-coverage claim) is deliberately NOT flagged -- this tool has no
    way to know what partial total is intended, so second-guessing it would
    be noise, not signal."""
    out = []
    for m in REPEATED_OF.finditer(text or ''):
        if m.group(1) == m.group(2):
            out.append((int(m.group(1)), m.group(0)))
    for m in REPEATED_SLASH.finditer(text or ''):
        if m.group(1) == m.group(2):
            out.append((int(m.group(1)), m.group(0)))
    return out


def check_seq_refs(seq_refs, current_target, rows, other_rows=None):
    """[(seq, verdict, detail)] -- verdict one of OK / OK-LOCAL-MATCH /
    UNVERIFIED-CROSS-LOG / TARGET-MISMATCH / NOT-FOUND. seq_refs is
    [(seq, local_context_frozenset), ...], extract_seq_refs()'s own output
    shape -- a bare [int] list also works (local context defaults to empty,
    same as passing no context at all).

    TARGET-MISMATCH is a CANDIDATE for human review, not a proven error --
    the same disclosed false-positive risk every other heuristic scanner in
    this directory already carries; a legitimate cross-topic citation (e.g.
    citing a general process-rule entry from a resource-specific one) can
    still trigger this even with local-context checking, and must be read
    in context, never treated as an automatic fail.

    OK-LOCAL-MATCH means the WHOLE-ENTRY target did not overlap, but a
    resource-name-shaped word sitting right next to the citation in the
    draft DID match the referenced entry's real target -- a distinct,
    weaker-confidence pass than plain OK, reported separately so a reader
    can tell which kind of match resolved it.

    UNVERIFIED-CROSS-LOG means the seq does not exist in THIS log but DOES
    exist in other_rows (H1's real log, by default) -- a real citation into
    a log this tool does not own, never folded into NOT-FOUND (which means
    the seq exists nowhere this tool can check) or into OK (which would
    silently claim a check that was never actually performed)."""
    by_seq = {r.get('seq'): r for r in rows}
    other_seqs = ({r.get('seq') for r in other_rows} if other_rows is not None
                  else set())
    cur_tokens = {t.strip().lower() for t in (current_target or '').split(',') if t.strip()}
    out = []
    for item in seq_refs:
        s, local = item if isinstance(item, tuple) else (item, frozenset())
        r = by_seq.get(s)
        if r is None:
            if s in other_seqs:
                out.append((s, 'UNVERIFIED-CROSS-LOG',
                           'seq %d exists in the OTHER auditor\'s log, not '
                           'this one -- this tool cannot check a citation '
                           'it does not own; read it there before trusting '
                           'this citation' % s))
            else:
                out.append((s, 'NOT-FOUND', 'no entry with seq %d exists in '
                           'this log or the other auditor\'s' % s))
            continue
        ref_tokens = {t.strip().lower() for t in (r.get('target') or '').split(',') if t.strip()}
        if cur_tokens and ref_tokens and not (cur_tokens & ref_tokens):
            if local and (local & ref_tokens):
                out.append((s, 'OK-LOCAL-MATCH',
                           'the whole-entry target did not overlap, but the '
                           'nearby word(s) %r match seq %d\'s real target '
                           '%r -- weaker-confidence pass, still worth a '
                           'glance' % (sorted(local & ref_tokens), s, r.get('target'))))
            else:
                out.append((s, 'TARGET-MISMATCH',
                           'seq %d target=%r shares no token with this entry\'s '
                           'target %r (nor with any nearby word) -- read seq %d '
                           'before trusting this citation'
                           % (s, r.get('target'), current_target, s)))
        else:
            out.append((s, 'OK', ''))
    return out


def check_count_claims(count_claims, pool_size, entry_count):
    """[(n, verdict, detail)] -- verdict one of FRESH / STALE / UNVERIFIABLE.
    FRESH: n matches the current pool size or the current entry count
    exactly. STALE: n is close to one of those (within 10, a real stale-
    count signature -- a small register or log drift, not a wildly
    unrelated number) but does not match it exactly. UNVERIFIABLE: n is not
    close to either known total -- this tool has no idea what it refers to,
    and says so rather than guessing."""
    out = []
    for n, matched in count_claims:
        near_pool = pool_size is not None and abs(n - pool_size) <= 10
        near_entries = entry_count is not None and abs(n - entry_count) <= 10
        if n == pool_size or n == entry_count:
            out.append((n, 'FRESH', '%r matches the current total exactly' % matched))
        elif near_pool or near_entries:
            which = 'pool size' if near_pool else 'log entry count'
            real = pool_size if near_pool else entry_count
            out.append((n, 'STALE',
                       '%r does not match the current %s (%d) -- recompute '
                       'before logging' % (matched, which, real)))
        else:
            out.append((n, 'UNVERIFIABLE',
                       '%r matches neither the current pool size (%s) nor '
                       'entry count (%s) -- not flagged, this tool cannot '
                       'tell what total it refers to'
                       % (matched, pool_size, entry_count)))
    return out


def lint(text, target, rows=None, tiers_path=DEFAULT_TIERS, log_path=LOG_PATH,
        other_rows=None, other_log_path=H1_LOG_PATH):
    """The whole pass over one draft. Returns (seq_results, count_results).
    other_rows defaults to a real, read-only load of H1_LOG_PATH -- pass
    other_rows=[] explicitly to disable cross-log lookup (e.g. if that path
    is ever unreachable; load_rows() itself already returns [] rather than
    raising when a path does not exist, so this degrades to NOT-FOUND for
    every cross-log citation rather than crashing)."""
    rows = rows if rows is not None else load_rows(log_path)
    other_rows = other_rows if other_rows is not None else load_rows(other_log_path)
    seq_results = check_seq_refs(extract_seq_refs(text), target, rows, other_rows)
    count_results = check_count_claims(
        extract_repeated_count_claims(text), current_pool_size(tiers_path), len(rows))
    return seq_results, count_results


def _print_report(seq_results, count_results):
    flagged = False
    cross_log = 0
    for s, verdict, detail in seq_results:
        if verdict == 'UNVERIFIED-CROSS-LOG':
            cross_log += 1
        elif verdict not in ('OK',):
            flagged = True
        print('  seq %-6d %-18s %s' % (s, verdict, detail))
    for n, verdict, detail in count_results:
        if verdict != 'FRESH':
            flagged = True
        print('  count %-5d %-14s %s' % (n, verdict, detail))
    if not seq_results and not count_results:
        print('  (no seq citations or repeated-count claims found in this draft)')
    if cross_log:
        print('  (%d citation(s) UNVERIFIED-CROSS-LOG -- counted separately, '
              'never passed as clean or failed as missing)' % cross_log)
    return flagged


def main(argv):
    if '--selftest' in argv:
        return selftest()
    if '--lint' in argv:
        def opt(flag, default=None):
            if flag in argv:
                i = argv.index(flag)
                if i + 1 < len(argv):
                    return argv[i + 1]
            return default
        target = opt('--target', '')
        text = opt('--text')
        file_path = opt('--file')
        # FAIL-CLOSED, PR SS1.11, covering the WHOLE --lint path from here
        # down -- reading the draft file is as much a way this tool can
        # fail to run as the lint logic itself is, and a bad --file path
        # crashing with a raw traceback (exit 1, no "COULD NOT RUN" text)
        # was a real gap found live while testing this exact requirement,
        # fixed here rather than left as a narrower try around lint() alone.
        try:
            if file_path:
                with io.open(file_path, encoding='utf-8') as f:
                    text = f.read()
            if text is None:
                print('COULD NOT RUN: missing --text or --file'); return 2
            # STRIPPED, matching hover_log.py's OWN --summary-file read
            # (`f.read().strip()`) exactly -- a REAL bug found live while
            # testing the --rotation-batch --lint-token flow (item 2 of the
            # same dispatch this tool's own second-limit round came from):
            # without this, --file always reads a trailing newline that
            # --summary-file's own strip() then removes before hover_log.py
            # computes ITS copy of the token, so the two tokens silently
            # never matched for any real file -- every real draft has one.
            # Stripping here means the lint pass also checks the EXACT text
            # that will actually be stored, not a slightly different one.
            text = text.strip()
            seq_results, count_results = lint(text, target)
        except Exception as e:
            print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
            return 2
        flagged = _print_report(seq_results, count_results)
        if flagged:
            print('ADVISORY: one or more candidates above -- read them in '
                  'context before trusting this draft; this is a heuristic, '
                  'not a verdict.')
        else:
            print('clean: no seq/count staleness candidates found')
        # LINT-TOKEN, printed on EVERY real --lint run regardless of
        # ADVISORY vs clean -- a flagged-but-read pass is still a real run
        # of the mandatory check, not a failure to run it. Paste this into
        # hover_log.py --append --rotation-batch --lint-token <this>.
        print('LINT-TOKEN: %s' % lint_token_for(text))
        return 0
    print(__doc__)
    return 0


# -- selftest, tests-first, with a known-bad control per check --------------

def selftest():
    bad = []
    total = [0]

    def ck(name, cond):
        total[0] += 1
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    # -- extraction fixtures --
    ck('extract_seq_refs: plain form (seq numbers, ignoring local context)',
       [s for s, _ in extract_seq_refs('per seq 123 this holds')] == [123])
    ck('extract_seq_refs: hyphen and parens',
       [s for s, _ in extract_seq_refs('(seq-45) confirms it')] == [45])
    ck('extract_seq_refs: slash-joined list',
       [s for s, _ in extract_seq_refs('seqs 291/305')] == [291, 305])
    ck('extract_seq_refs: comma-joined list',
       [s for s, _ in extract_seq_refs('seqs 270, 273, 274')] == [270, 273, 274])
    ck('extract_seq_refs: none present',
       extract_seq_refs('no citation here at all') == [])
    ck('extract_seq_refs: LOCAL CONTEXT -- a resource-shaped word right '
       'before the citation is captured',
       'sv_financials' in extract_seq_refs(
           'sv_financials -- FILED seq 270 (variance KPI)')[0][1])
    ck('extract_seq_refs: LOCAL CONTEXT -- no resource-shaped word nearby '
       'gives an empty context, not a crash',
       extract_seq_refs('per seq 123 this holds')[0][1] == frozenset())

    ck('extract_repeated_count_claims: "N of N" caught',
       extract_repeated_count_claims('122 of 122 confirmed') == [(122, '122 of 122')])
    ck('extract_repeated_count_claims: "N/N" caught',
       (326, '326/326') in extract_repeated_count_claims('log stands at 326/326'))
    ck('extract_repeated_count_claims: differing pair NOT caught '
       '(partial coverage, not this tool\'s call)',
       extract_repeated_count_claims('9 of 124 checked in depth') == [])

    # -- check_seq_refs fixtures, synthetic rows, fully controlled --
    rows = [
        {'seq': 1, 'target': 'alpha,beta'},
        {'seq': 2, 'target': 'gamma'},
    ]
    ck('check_seq_refs: OK when referenced seq shares a token',
       check_seq_refs([1], 'alpha', rows)[0][1] == 'OK')
    ck('check_seq_refs: TARGET-MISMATCH when no shared token',
       check_seq_refs([2], 'alpha', rows)[0][1] == 'TARGET-MISMATCH')
    ck('check_seq_refs: NOT-FOUND for a seq that does not exist',
       check_seq_refs([999], 'alpha', rows)[0][1] == 'NOT-FOUND')
    ck('check_seq_refs: no current target -> no opinion (OK), not a false flag',
       check_seq_refs([2], '', rows)[0][1] == 'OK')

    # KNOWN-BAD CONTROL: a checker that always says OK must be shown wrong
    def broken_check(refs, target, rows):
        return [(s, 'OK', '') for s in refs]
    real = check_seq_refs([2], 'alpha', rows)
    fake = broken_check([2], 'alpha', rows)
    ck('KNOWN-BAD CONTROL: a checker that always says OK disagrees with the '
       'real TARGET-MISMATCH verdict on this fixture',
       real[0][1] == 'TARGET-MISMATCH' and fake[0][1] == 'OK' and real != fake)

    # -- LIMIT 1 fixtures: UNVERIFIED-CROSS-LOG, a real third state, never
    # folded into NOT-FOUND or OK.
    other = [{'seq': 500, 'target': 'somewhere-else'}]
    ck('check_seq_refs: a seq absent from THIS log but present in the '
       'OTHER log reads UNVERIFIED-CROSS-LOG, not NOT-FOUND',
       check_seq_refs([500], 'alpha', rows, other)[0][1] == 'UNVERIFIED-CROSS-LOG')
    ck('check_seq_refs: a seq absent from BOTH logs still reads NOT-FOUND '
       '(the cross-log check only ever ADDS a state, never removes one)',
       check_seq_refs([999], 'alpha', rows, other)[0][1] == 'NOT-FOUND')
    ck('check_seq_refs: with no other_rows supplied at all, behaviour is '
       'unchanged from before this limit was closed (NOT-FOUND, not a crash)',
       check_seq_refs([500], 'alpha', rows)[0][1] == 'NOT-FOUND')

    # KNOWN-BAD CONTROL: a checker that never distinguishes cross-log from
    # genuinely-nowhere must be shown disagreeing with the real distinction.
    def broken_cross_log_check(refs, target, rows, other_rows=None):
        by_seq = {r.get('seq'): r for r in rows}
        out = []
        for s in refs:
            if by_seq.get(s) is None:
                out.append((s, 'NOT-FOUND', ''))  # never looks at other_rows
            else:
                out.append((s, 'OK', ''))
        return out
    real_cl = check_seq_refs([500], 'alpha', rows, other)
    fake_cl = broken_cross_log_check([500], 'alpha', rows, other)
    ck('KNOWN-BAD CONTROL: a checker that ignores other_rows entirely '
       'reports NOT-FOUND where the real checker correctly reports '
       'UNVERIFIED-CROSS-LOG',
       real_cl[0][1] == 'UNVERIFIED-CROSS-LOG' and fake_cl[0][1] == 'NOT-FOUND'
       and real_cl != fake_cl)

    # -- LIMIT 2 fixtures: OK-LOCAL-MATCH, the same-batch-sibling downgrade,
    # driven against a synthetic fixture shaped exactly like the real
    # seq-270-from-within-a-sweep-summary case.
    sib_rows = [{'seq': 10, 'target': 'sv_financials'}]
    sib_text = 'sv_financials -- FILED seq 10 (variance KPI); more prose after.'
    sib_refs = extract_seq_refs(sib_text)
    ck('check_seq_refs: a whole-entry TARGET-MISMATCH is downgraded to '
       'OK-LOCAL-MATCH when a nearby word matches the referenced entry\'s '
       'real target',
       check_seq_refs(sib_refs, 'upstream-of-money-sweep', sib_rows)[0][1]
       == 'OK-LOCAL-MATCH')
    ck('check_seq_refs: the SAME citation with no local context at all '
       'still reads plain TARGET-MISMATCH -- the downgrade only fires on a '
       'real nearby word, never by default',
       check_seq_refs([10], 'upstream-of-money-sweep', sib_rows)[0][1]
       == 'TARGET-MISMATCH')
    unrelated_text = 'grd_vendors keeps a directory. Elsewhere, per seq 10 something else.'
    unrelated_refs = extract_seq_refs(unrelated_text)
    ck('check_seq_refs: a nearby word that does NOT match the referenced '
       'entry\'s target does not trigger a false downgrade',
       check_seq_refs(unrelated_refs, 'upstream-of-money-sweep', sib_rows)[0][1]
       == 'TARGET-MISMATCH')

    # KNOWN-BAD CONTROL: a checker that downgrades to OK-LOCAL-MATCH
    # unconditionally (ignoring whether the local word actually matches)
    # must be shown disagreeing with the real, discriminating verdict.
    def broken_local_match(refs, target, rows):
        by_seq = {r.get('seq'): r for r in rows}
        cur = {t.strip().lower() for t in (target or '').split(',') if t.strip()}
        out = []
        for item in refs:
            s, _local = item if isinstance(item, tuple) else (item, frozenset())
            r = by_seq.get(s)
            ref_t = {t.strip().lower() for t in (r.get('target') or '').split(',')} if r else set()
            if cur and ref_t and not (cur & ref_t):
                out.append((s, 'OK-LOCAL-MATCH', 'always downgrades'))  # BUG: no real check
            else:
                out.append((s, 'OK', ''))
        return out
    real_lm = check_seq_refs(unrelated_refs, 'upstream-of-money-sweep', sib_rows)
    fake_lm = broken_local_match(unrelated_refs, 'upstream-of-money-sweep', sib_rows)
    ck('KNOWN-BAD CONTROL: a checker that downgrades to OK-LOCAL-MATCH '
       'unconditionally disagrees with the real TARGET-MISMATCH verdict on '
       'a fixture with no genuine local match',
       real_lm[0][1] == 'TARGET-MISMATCH' and fake_lm[0][1] == 'OK-LOCAL-MATCH'
       and real_lm != fake_lm)

    # -- check_count_claims fixtures --
    ck('check_count_claims: exact match is FRESH',
       check_count_claims([(122, '122 of 122')], 122, 999)[0][1] == 'FRESH')
    ck('check_count_claims: near-miss against pool is STALE',
       check_count_claims([(123, '123 of 123')], 122, 999)[0][1] == 'STALE')
    ck('check_count_claims: far from both totals is UNVERIFIABLE, not FRESH '
       'and not silently ignored',
       check_count_claims([(4000, '4000 of 4000')], 122, 326)[0][1] == 'UNVERIFIABLE')

    # -- FAIL-CLOSED REGRESSION, item-3 requirement: a bad --file path used
    # to crash with a raw, uncaught traceback (exit 1, no "COULD NOT RUN"
    # text) -- a real gap found live while testing this exact requirement,
    # fixed by widening the try/except to cover the file read too. Driven
    # via a real subprocess, not a direct function call, because the bug
    # lived in main()'s own CLI wiring, not in any importable function.
    r1 = subprocess.run(
        [sys.executable, os.path.abspath(__file__), '--lint', '--target', 'x',
         '--file', os.path.join(os.sep, 'definitely-does-not-exist-xyz.txt')],
        capture_output=True, text=True)
    ck('FAIL-CLOSED: a bad --file path prints COULD NOT RUN and exits 2, '
       'never a raw traceback (exit 1) or a silent pass (exit 0)',
       r1.returncode == 2 and 'COULD NOT RUN' in r1.stdout)
    r2 = subprocess.run(
        [sys.executable, os.path.abspath(__file__), '--lint', '--target', 'x'],
        capture_output=True, text=True)
    ck('FAIL-CLOSED: --lint with neither --text nor --file prints COULD '
       'NOT RUN and exits 2', r2.returncode == 2 and 'COULD NOT RUN' in r2.stdout)

    # -- LINT-TOKEN / hover_log.py CROSS-TOOL REGRESSION: a real bug found
    # live driving the actual --rotation-batch --lint-token flow end to end
    # (not caught by any direct-function-call fixture, because those never
    # went through a real file with a real trailing newline). --file used
    # to read the RAW text (keeping a trailing "\n"), while hover_log.py's
    # own --summary-file always strips before computing ITS copy of the
    # token -- the two tokens silently never matched for any real file.
    # Fixed by stripping here too. Driven via a real subprocess against a
    # real temp file with a real trailing newline, and cross-checked
    # against hover_log.py's own lint_token_for() (imported directly,
    # read-only, not re-derived by hand, so this regression fails if EITHER
    # side's stripping convention ever drifts from the other's again).
    import tempfile as _tf2
    tmp2 = _tf2.mkdtemp()
    draft_path = os.path.join(tmp2, 'draft.txt')
    with io.open(draft_path, 'w', encoding='utf-8') as f:
        f.write('a real draft with a real trailing newline\n')
    r3 = subprocess.run(
        [sys.executable, os.path.abspath(__file__), '--lint', '--target', 'x',
         '--file', draft_path], capture_output=True, text=True)
    printed_token = None
    for line in r3.stdout.splitlines():
        if line.startswith('LINT-TOKEN: '):
            printed_token = line.split('LINT-TOKEN: ', 1)[1].strip()
    sys.path.insert(0, HERE)
    import hover_log as _hl
    with io.open(draft_path, encoding='utf-8') as f:
        as_hover_log_would_read_it = f.read().strip()
    expected = _hl.lint_token_for(as_hover_log_would_read_it)
    ck('LINT-TOKEN cross-tool regression: the token --lint prints for a '
       'real --file with a real trailing newline matches what hover_log.py '
       'would independently recompute from the SAME file via its own '
       '--summary-file read -- these must never silently diverge again',
       printed_token is not None and printed_token == expected)

    # -- REAL HISTORICAL REGRESSION: seq 307's own byte-faithful closing
    # sentence, the exact shape of the real seq-308 mistake. The real
    # current pool size is whatever CRITICALITY-TIERS.md says RIGHT NOW
    # (re-derived fresh, not hardcoded), so this fixture stays a real
    # regression test even as the register continues to change.
    real_308_text = ('RESULT: 6 individual first reads, 6 confirmed B, 0 '
                     'findings. CHECKED/UNIVERSE: 123 of 123 B/C pool '
                     'resources now read at least once by this role '
                     '(target-token basis) -- the never-read list is empty.')
    pool_now = current_pool_size()
    if pool_now is not None and pool_now != 123:
        _, cr = lint(real_308_text, 'self')
        ck('REAL REGRESSION (seq 307/308 shape): the real historical "123 '
           'of 123" claim is flagged against the CURRENT real pool size '
           '(%s), not hardcoded -- verdict %s'
           % (pool_now, cr[0][1] if cr else 'NONE'),
           bool(cr) and cr[0][1] in ('STALE', 'UNVERIFIABLE'))
    else:
        ck('REAL REGRESSION (seq 307/308 shape): (skipped -- current pool '
           'size happens to equal 123 today, which would make a FRESH '
           'verdict correct rather than a bug; counted as FAIL rather than '
           'silently skipped, since an undriven regression proves nothing)',
           False)

    # -- REAL HISTORICAL DATA: seq 274/275, the underlying shape behind the
    # real seq-276 correction (a backward reference, not the narrower
    # forward self-reference the docstring discloses as out of scope).
    real_rows = load_rows()
    by_seq = {r.get('seq'): r for r in real_rows}
    if 274 in by_seq and 275 in by_seq:
        seq275_target = by_seq[275].get('target', '')
        result = check_seq_refs([275], 'leg_insurance', real_rows)
        ck('REAL DATA (seq 274/275): citing seq 275 while discussing '
           'leg_insurance is TARGET-MISMATCH against the real log -- '
           'seq 275\'s real target is %r, which does not contain '
           '"leg_insurance"' % seq275_target,
           result[0][1] == 'TARGET-MISMATCH')
        result2 = check_seq_refs([274], 'leg_insurance', real_rows)
        ck('REAL DATA (seq 274/275): citing the REAL correct seq (274) for '
           'leg_insurance is OK against the real log',
           result2[0][1] == 'OK')
    else:
        ck('REAL DATA (seq 274/275): (seq 274 or 275 not present in this '
           'log -- counted as FAIL rather than silently skipped)', False)

    print('%d ok, %d failed' % (total[0] - len(bad), len(bad)))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
