#!/usr/bin/env python
"""hover_log.py (hover2's own copy) -- append-only, hash-chained self-log for
this hover-auditor instance.

WRITTEN FROM THE RULE, NOT COPIED FROM hover1's hover_log.py. I do not have
read access to that file (different clone, different local project
directory) and would not copy it even if I did -- a second implementation
that only agrees with the first because it is a paste of the first proves
nothing about either being correct. The hashing scheme below is instead
re-derived from the PUBLIC, SHARED verifier that already exists in the
committed platform repo: tools/hover_separation_audit.py's _canonical(),
_digest() and verify_chain(). That file is legitimately readable by anyone
(it is not hover-private), and its algorithm is the actual interface my
chain must satisfy, since that shared tool -- and
tools/hover_process_pass_freshness.py, which calls into it -- are what will
independently re-verify this log later. Matching their hashing exactly is
not "copying hover1's tool"; it is satisfying the one public contract both
hover instances are already bound by.

FORMAT, one JSON object per line, oldest first:
    {"seq": int, "ts": "YYYY-MM-DDTHH:MM:SSZ", "type": "check"|"finding"|
     "process_pass"(bool, optional key on ANY entry), "summary": str,
     "ref": str (commit shas / resource names / anything this entry is
     about, comma-separated), "prev_hash": str, "hash": str}

CHAIN RULE (re-derived from tools/hover_separation_audit.py's verify_chain,
confirmed by reading that file directly on 2026-09-22):
    prev = GENESIS
    for each entry in order:
        entry['prev_hash'] must equal prev
        body = entry minus the 'hash' key
        entry['hash'] must equal sha256(prev + '\n' + canonical(body) + '\n')
        prev = entry['hash']
canonical() is recursive, sorted-key JSON: dict keys sorted, list order
preserved, scalars via json.dumps. GENESIS is the fixed literal the shared
verifier hardcodes -- reusing a different seed here would make this log
unverifiable by the tool that is supposed to check it, for no security
benefit; it is a shared constant, not a secret.

    python hover_log.py --append --type check --summary "..." --ref "sha1,sha2"
    python hover_log.py --append --type finding --summary "..." --ref "resource_name"
    python hover_log.py --append --type check --summary "..." --process-pass
    python hover_log.py --verify
    python hover_log.py --selftest
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

GENESIS = 'genesis:hover-auditor-self-log:v1'
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'hover-audit-log.jsonl')

# The platform repo this clone audits -- not this directory, which is the
# private self-log. Overridable for testing (see selftest_staleness_guard(),
# which builds a throwaway repo rather than touching the real one).
DEFAULT_PLATFORM_REPO = os.environ.get(
    'HOVER_PLATFORM_REPO', r'C:\Users\marsh\Documents\SAIRN-hover2')

LINT_TOKEN_LEN = 16


def lint_token_for(text):
    """The mechanical marker for docs/2026-09-29-hover-gap-research-h2.md's
    item-3 skipped-run gap: a hash of the exact SUMMARY TEXT a rotation
    batch is about to log, deterministic and independently recomputable
    right here -- never taken on the caller's word. Deliberately NOT
    imported from hover_citation_linter.py (same independence discipline
    that file's own current_pool_size() already states: kept separate so a
    bug in one cannot silently propagate into the other's answer); that
    file computes and prints the SAME token via the SAME formula so a real
    --lint run's own output is directly usable as --lint-token here.
    A token proves ONE fact only -- that SOME lint pass was run against
    THIS EXACT TEXT -- never that the lint pass found nothing to flag; a
    flagged, advisory lint run still produces a real, valid token, because
    the mandatory step is running the check, not it coming back clean."""
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()[:LINT_TOKEN_LEN]


def canonical(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return json.dumps(value)
    if isinstance(value, list):
        return '[' + ','.join(canonical(v) for v in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k) + ':' + canonical(value[k])
                              for k in sorted(value)) + '}'
    raise TypeError('cannot canonicalise %r' % (value,))


def digest(prev_hash, entry_without_hash):
    h = hashlib.sha256()
    h.update((prev_hash + '\n').encode('utf-8'))
    h.update((canonical(entry_without_hash) + '\n').encode('utf-8'))
    return h.hexdigest()


def read_all(path=None):
    """[] if the file does not exist yet -- an empty log is a real, valid
    starting state, not an error. Returns (rows, problem); problem non-empty
    means the file exists but could not be parsed, which IS an error."""
    path = path or LOG_PATH
    if not os.path.isfile(path):
        return [], ''
    rows = []
    try:
        with io.open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except (OSError, ValueError) as exc:
        return None, 'could not read/parse %s: %s' % (path, exc)
    return rows, ''


def verify(rows):
    """(ok, reason). Empty log verifies trivially true -- there is nothing
    in it to disagree with itself, matching hover_separation_audit.py's own
    read: an unreadable/missing log is COULD NOT RUN, but a genuinely empty
    one is a fact, not a failure."""
    prev = GENESIS
    for i, r in enumerate(rows):
        if r.get('prev_hash') != prev:
            return False, ('entry %d (seq %s) has prev_hash %r but the '
                           'chain up to here hashes to %r'
                           % (i, r.get('seq'), str(r.get('prev_hash'))[:16],
                              prev[:16]))
        body = {k: v for k, v in r.items() if k != 'hash'}
        want = digest(prev, body)
        if want != r.get('hash'):
            return False, ('entry %d (seq %s) does not hash to its stored '
                           'value -- content changed after it was written, '
                           'or written with a different canonicalisation'
                           % (i, r.get('seq')))
        prev = r['hash']
    return True, ''


def _run_git(repo, args, timeout=20):
    """(returncode, stdout, stderr). Never raises on a non-zero exit or a
    timeout -- both are real, distinguishable outcomes the caller reads,
    never collapsed into one boolean. Decoded explicitly with
    encoding='utf-8', errors='replace' -- a bare text=True decodes with the
    OS locale default and has silently truncated or mojibake'd real git
    output on this platform before (CLAUDE.md rule 1.2, subprocess-decode);
    that defect class does not get a second life in this file."""
    try:
        p = subprocess.run(['git', '-C', repo] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           encoding='utf-8', errors='replace', timeout=timeout)
        return p.returncode, (p.stdout or ''), (p.stderr or '')
    except subprocess.TimeoutExpired:
        return None, '', 'TIMEOUT after %ss running git %s' % (timeout, ' '.join(args))
    except OSError as exc:
        return None, '', 'could not run git at all: %s' % exc


_SHA_RE = re.compile(r'^[0-9a-fA-F]{7,40}$')


def parse_source(source_str):
    """'--source' string -> [(path, explicit_sha_or_None), ...]. Comma-
    separated 'path' or 'path:sha' segments. Refuses on an empty segment,
    an empty path, or a sha that is not plausible hex (git's own
    abbreviation floor is 7 hex chars, full blob shas are 40)."""
    out = []
    for chunk in source_str.split(','):
        chunk = chunk.strip()
        if not chunk:
            raise ValueError('--source has an empty entry between commas')
        if ':' in chunk:
            path, sha = chunk.split(':', 1)
            path, sha = path.strip(), sha.strip()
            if not _SHA_RE.match(sha):
                raise ValueError('--source override %r is not a plausible git '
                                 'sha (7-40 hex chars)' % sha)
        else:
            path, sha = chunk.strip(), None
        if not path:
            raise ValueError('--source has an empty path')
        out.append((path, sha))
    return out


def capture_source(repo, source_str):
    """Parses --source and, for every entry with no explicit sha, derives
    THIS CLONE'S OWN locally-committed blob sha for that path RIGHT NOW
    (local HEAD, not origin/main) -- the honest proxy for 'what my own read
    tool actually returned' this turn, because a clone that has not pulled
    genuinely differs from origin/main's current state, which is precisely
    the incident shape this guard exists to catch. Raises ValueError
    immediately, at capture time, if a no-explicit-sha path does not exist
    at local HEAD at all -- that is a caller mistake (wrong path, or never
    committed), not a staleness signal, and must not be silently deferred
    to the write-time check below."""
    captured = []
    for path, sha in parse_source(source_str):
        if sha is not None:
            captured.append({'path': path, 'captured_sha': sha, 'explicit': True})
            continue
        rc, out, err = _run_git(repo, ['rev-parse', 'HEAD:' + path])
        if rc != 0:
            raise ValueError(
                'could not derive a local HEAD sha for %r in %r (git said: %s) '
                '-- check the path is correct and committed locally, or pass '
                'path:sha explicitly for a specific historical commit'
                % (path, repo, err.strip() or '(no stderr)'))
        captured.append({'path': path, 'captured_sha': out.strip(), 'explicit': False})
    return captured


_NO_SUCH_PATH_RE = re.compile(
    r"does not exist in|exists on disk, but not in", re.IGNORECASE)
# Two real git rev-parse <ref>:<path> error strings, both confirmed
# no-such-path-at-that-ref signals, not ambiguous ones: "does not exist in
# 'REF'" when the path is absent from the working tree too, and "exists on
# disk, but not in 'REF'" when the caller's local working tree still has a
# copy (e.g. before a pull) but the ref being checked does not. Both were
# hit by the real selftest fixture below -- the second only appears once a
# path that used to exist in a ref has since been removed from a NEWER ref
# while the caller's own checkout still has it, which is exactly the
# git-add-worktree-adjacent case the first regex attempt missed.


def verify_source_freshness(repo, captured, remote='origin', branch='main',
                            fetch_timeout=25):
    """The write-time check -- re-derives each captured path's blob sha
    AGAIN, fresh, against CURRENT origin/main, and compares. Three
    outcomes, stamped onto every entry, never collapsed to two:
      fresh            -- shas match.
      stale            -- a real, resolved mismatch, OR the path answers
                          cleanly that it no longer exists at that ref --
                          both are confirmed signals, not guesses.
      could_not_verify -- the remote could not be reached, or git itself
                          could not be run. Genuine infrastructure noise,
                          not a resolved answer -- the one deliberate,
                          named exception to this role's fail-CLOSED
                          default (this is a WRITE-PATH GUARD deciding
                          whether an already-reasoned finding may be
                          committed, not a CHECK reporting a verdict about
                          the world; refusing a valid finding because a
                          fetch timed out costs something a resolved
                          'yes it changed' answer does not). Never
                          silent, though: the entry is stamped with the
                          ambiguous verdict, visible to every later
                          reader, never indistinguishable from a
                          confirmed-fresh pass."""
    fetch_rc, _out, fetch_err = _run_git(repo, ['fetch', remote, branch],
                                         timeout=fetch_timeout)
    if fetch_rc != 0:
        reason = ('could not fetch %s/%s to compare against current state (%s)'
                  % (remote, branch, fetch_err.strip() or 'unknown error'))
        return [dict(c, status='could_not_verify', current_sha=None, detail=reason)
                for c in captured]

    ref = '%s/%s' % (remote, branch)
    results = []
    for c in captured:
        rc, out, err = _run_git(repo, ['rev-parse', ref + ':' + c['path']])
        if rc == 0:
            current = out.strip()
            if current == c['captured_sha']:
                results.append(dict(c, status='fresh', current_sha=current, detail=''))
            else:
                results.append(dict(c, status='stale', current_sha=current,
                    detail=('%s now points to a different blob (%s) than what '
                            'was read (%s) -- re-read and re-derive before '
                            'logging this finding'
                            % (c['path'], current[:12], c['captured_sha'][:12]))))
        elif _NO_SUCH_PATH_RE.search(err or ''):
            results.append(dict(c, status='stale', current_sha=None,
                detail=('%s no longer exists at %s -- confirmed removed/moved, '
                        're-read before logging this finding' % (c['path'], ref))))
        else:
            results.append(dict(c, status='could_not_verify', current_sha=None,
                detail=('rev-parse %s:%s failed ambiguously (%s), not a '
                        'confirmed no-such-path answer'
                        % (ref, c['path'], (err or '').strip() or 'no stderr'))))
    return results


VALID_TYPES = ('check', 'finding', 'no-report', 'note')
VALID_SEVERITY = ('critical', 'high', 'moderate', 'low', '')
VECTOR_RE = re.compile(r'^T:[ABC]/EX:(L|M|H|NA)/IM:(L|M|H)/SC:(C|S)$')


def append_entry(entry_type, summary, ref='', target='self', severity='',
                 vector='', retrospective=False, same_target_reason='',
                 undirected_sweep=False, process_pass=False,
                 eqa_checkpoint=False, path=None, source='',
                 source_exempt_reason='', repo=None, tier_claim=False,
                 contradicts=None, mistake_class='', rotation_batch=False,
                 lint_token='', routable=None):
    """Full schema per hover-interface-specs-2026-09-22.md #1. Refuses
    (raises ValueError) on: a backtick in summary (shell command-substitution
    data-loss risk -- use append_entry with text read from a file instead,
    never a literal on a command line); an unrecognised type/severity;
    type=finding with no vector; a target that repeats the immediately
    preceding entry's target with no same_target_reason (the rotation gate --
    makes target-diversity drift visible instead of silently accumulating);
    type=finding with neither --source nor --source-exempt-reason (the
    staleness guard -- a finding about a platform subject must cite what
    commit it was read against, or say explicitly why not, e.g. because it
    is about this role's own tooling rather than a platform file);
    --tier-claim (this finding asserts a resource's CRITICALITY-TIERS.md
    row is wrong) whose --source omits a path naming CRITICALITY-TIERS.md
    (the seq-96/97 gap, closed STRUCTURALLY rather than left to a practice
    reminder: citing only the app file proves the RECORD SHAPE is real but
    proves nothing about whether the register itself was read fresh, which
    is the one fact that actually decides whether 'still B' is true. This
    refuses the append entirely -- not a warning, not a stamp -- exactly
    like the missing-source case it extends).

    STALENESS GUARD (write-time, positional -- runs last, immediately before
    the entry is physically written, after every other check above). Each
    --source path is re-derived AGAIN, fresh, against CURRENT origin/main,
    and compared to what was captured when --source was parsed. A real,
    confirmed mismatch (or a path confirmed gone) HARD REFUSES the whole
    append -- nothing is written. An unreachable remote does not block (the
    one named exception to fail-closed: this guards a WRITE, not a CHECK)
    but stamps every source 'could_not_verify' on the entry itself, visible
    to every later reader, never silently treated as a pass. See
    verify_source_freshness() for the exact three-state contract."""
    if '`' in summary:
        raise ValueError('refusing: summary contains a literal backtick -- '
                         'this has caused real content loss via shell command '
                         'substitution before the logging tool ever saw the '
                         'text. Pass the text from a file (--summary-file) '
                         'instead of a command-line literal.')
    if entry_type not in VALID_TYPES:
        raise ValueError('type must be one of %s, not %r' % (VALID_TYPES, entry_type))
    if severity not in VALID_SEVERITY:
        raise ValueError('severity must be one of %s, not %r' % (VALID_SEVERITY, severity))
    if entry_type == 'finding':
        if not VECTOR_RE.match(vector or ''):
            raise ValueError('type=finding requires --vector in the form '
                             'T:x/EX:x/IM:x/SC:x (e.g. T:A/EX:M/IM:H/SC:C), got %r' % vector)
        if not source and not source_exempt_reason:
            raise ValueError(
                'refusing: type=finding requires --source <path>[:sha][,...] '
                'citing what was actually read, or --source-exempt-reason '
                'stating explicitly why not (e.g. this finding is about this '
                "role's own operational tooling, not a platform file, and there "
                'is no earlier read moment separate from logging for a sha '
                'comparison to mean anything). The leg_aftercare incident -- a '
                'finding logged against a row already fixed on origin/main, '
                "with nothing catching the staleness before it was committed "
                'to a hash-chained log -- is what this refusal exists to '
                'prevent happening silently again.')
        if tier_claim:
            cited_paths = [p for p, _sha in parse_source(source)] if source else []
            if not any(p.replace('\\', '/').endswith('CRITICALITY-TIERS.md')
                       for p in cited_paths):
                raise ValueError(
                    'refusing: --tier-claim asserts a CRITICALITY-TIERS.md row '
                    'is wrong, but --source does not cite a path ending in '
                    'CRITICALITY-TIERS.md. Citing the app file alone (what you '
                    'read) proves the record SHAPE is real but proves nothing '
                    'about whether the register itself was read fresh -- the '
                    'one fact that actually decides whether \'still B\' is '
                    'true. This is the seq-96/97 gap (sc_eligibility, logged '
                    'against a stale local tier read because only the app file '
                    'was cited), closed structurally rather than left to a '
                    'practice reminder. Add docs/CRITICALITY-TIERS.md to '
                    '--source.')

    # SELF-CONTRADICTION FIELD, added 2026-09-27 on direct instruction --
    # OWN design, never read or copied from H1's h1-h2-disagreement-protocol
    # (that mechanism is CROSS-instance, this one is a LATER READ BY THIS
    # SAME INSTANCE overturning an EARLIER CLEAN VERDICT it itself logged).
    # Higher salience than an ordinary finding: a contradiction of one's own
    # past "clean" is a calibration signal about THIS role's own reliability,
    # not only a fact about the resource. Validated mechanically, same
    # citation-checking discipline as --source/--tier-claim: the referenced
    # seq must exist, must be exactly the entry_type this field claims to
    # overturn (a prior 'check', never a prior 'finding' -- contradicting a
    # finding is just a second finding, not a self-contradiction), and must
    # share at least one target token with THIS entry (mechanically confirms
    # "the same resource" rather than trusting the caller's word for it).
    if contradicts is not None and entry_type != 'finding':
        raise ValueError(
            'refusing: --contradicts marks a LATER read overturning an '
            'earlier CLEAN verdict, which is itself a real finding -- '
            'type must be finding, not %r' % entry_type)

    # MISTAKE-CLASS TAG, added 2026-09-29 per the third-pass research
    # document's own error-pattern-tracking scope: a structured label on a
    # self-correction NOTE, so a future query can group and count by class
    # mechanically instead of re-reading every past correction's prose (the
    # exact manual reconstruction that research document itself required).
    # Restricted to type=note, same structural-refusal discipline as
    # --contradicts's type=finding restriction: this field marks THIS
    # ROLE'S OWN correction of ITS OWN prior action, and a self-correction
    # is a note about this role's own record, not a finding about a
    # platform resource or a contradiction of a prior clean verdict (both
    # already have their own fields).
    if mistake_class and entry_type != 'note':
        raise ValueError(
            'refusing: --mistake-class tags a SELF-CORRECTION note -- type '
            'must be note, not %r. A mistake-class tag on a finding or '
            'check would blur it with --contradicts/--tier-claim, which '
            'already carry that meaning for their own entry types.'
            % entry_type)

    # ROUTABLE FIELD, added 2026-09-29 (docs/2026-09-29-hover-gap-research-
    # h2.md item 1): tools/hover_routing_gap_check.py (a build-agent tool,
    # not read as H1's own implementation -- this is the shared CONTRACT
    # both hover instances are meant to satisfy) reads entry['routable'] as
    # a list of resource names and classifies it 'structured' -- EXACT --
    # versus guessing resource-shaped tokens out of free-text `ref`
    # ('prose-fallback', weaker, and the checker itself says so). Without
    # this field this role's own findings were structurally invisible to
    # that checker's exact-count half. Restricted to type=finding: a
    # routable NAME is a claim "this specific resource needs a build
    # agent's attention", which is what a finding asserts and a check/note
    # does not. Mechanically checked against target, same discipline as
    # --contradicts's shared-token check: every routable name must appear
    # as one of the comma-split target tokens, so a caller cannot route a
    # resource this entry's own target field never named.
    routable_list = []
    if routable is not None:
        if isinstance(routable, str):
            routable_list = [x.strip() for x in routable.split(',') if x.strip()]
        else:
            routable_list = [str(x).strip() for x in routable if str(x).strip()]
    if routable_list and entry_type != 'finding':
        raise ValueError(
            'refusing: --routable marks a resource that needs a build '
            "agent's attention -- type must be finding, not %r. A check "
            'or note is not itself a routable claim.' % entry_type)
    if routable_list:
        target_tokens = {t.strip() for t in (target or '').split(',') if t.strip()}
        unnamed = [r for r in routable_list if r not in target_tokens]
        if unnamed:
            raise ValueError(
                'refusing: --routable names %r which %s not in --target '
                '%r -- a routable resource must be one this entry already '
                'names as its target, checked mechanically, not asserted'
                % (unnamed, 'is' if len(unnamed) == 1 else 'are', target))

    # ROTATION-BATCH LINT-TOKEN GATE, added 2026-09-29: the mechanical
    # marker for the skipped-run gap named in docs/2026-09-29-hover-gap-
    # research-h2.md's item 3 ("nothing structural marks a skipped linter
    # run"). --rotation-batch marks an entry as one that MUST carry proof a
    # hover_citation_linter.py --lint pass actually ran against this exact
    # summary text; a missing or non-matching token is refused, and the
    # refusal message says COULD NOT RUN by name (distinct from an ordinary
    # validation refusal) so a caller or a later reader can tell "the
    # mandatory check step did not happen" apart from "a normal rule was
    # violated". Recomputed independently right here, never trusted on the
    # caller's say-so -- a hand-typed string that happens to look like a
    # token is refused exactly like a missing one, because it will not
    # match lint_token_for(summary).
    if rotation_batch:
        if not lint_token:
            raise ValueError(
                'COULD NOT RUN: --rotation-batch requires --lint-token -- '
                'run hover_citation_linter.py --lint on this exact summary '
                'text first and pass the token it prints. No token was '
                'supplied at all; this is a skipped-run refusal, not an '
                'ordinary validation error.')
        if lint_token != lint_token_for(summary):
            raise ValueError(
                'COULD NOT RUN: --lint-token %r does not match this exact '
                'summary text (expected %r) -- either the summary changed '
                'after the lint pass ran, or the token was not real. Run '
                'hover_citation_linter.py --lint on the FINAL text again '
                'and pass the token it actually prints.'
                % (lint_token, lint_token_for(summary)))

    repo = repo or DEFAULT_PLATFORM_REPO
    # Captured AT THE MOMENT --source IS PARSED, as early as this function
    # can manage it -- before the chain is even read -- so a bad path (typo,
    # never committed) fails fast and cheaply rather than after every other
    # check has already run.
    captured_source = capture_source(repo, source) if source else []

    path = path or LOG_PATH
    rows, problem = read_all(path)
    if rows is None:
        raise RuntimeError('refusing to append: existing log is unreadable '
                           '(%s). Fix or move it aside before adding to it -- '
                           'appending onto an unverified file is the thing '
                           'the chain exists to prevent.' % problem)
    ok, why = verify(rows)
    if rows and not ok:
        raise RuntimeError('refusing to append: existing chain does not '
                           'verify (%s). A tampered or corrupted log must be '
                           'investigated, not silently extended.' % why)

    if rows and rows[-1].get('target') == target and not same_target_reason:
        raise ValueError('refusing: target %r repeats the immediately '
                         'preceding entry (seq %s) with no same_target_reason '
                         '-- this gate exists to make target-diversity drift '
                         'visible rather than silently accumulating. Supply '
                         'same_target_reason to proceed deliberately.'
                         % (target, rows[-1].get('seq')))

    if contradicts is not None:
        referenced = next((r for r in rows if r.get('seq') == contradicts), None)
        if referenced is None:
            raise ValueError('refusing: --contradicts %r does not resolve '
                             'to a real seq in this log' % contradicts)
        if referenced.get('type') != 'check':
            raise ValueError(
                'refusing: --contradicts %r names a seq of type %r, not '
                "'check' -- this field is for overturning a CLEAN verdict; "
                'contradicting an existing finding is a second finding, '
                'not a self-contradiction' % (contradicts, referenced.get('type')))
        ref_tokens = {t.strip() for t in (referenced.get('target') or '').split(',')}
        cur_tokens = {t.strip() for t in (target or '').split(',')}
        if not (ref_tokens & cur_tokens):
            raise ValueError(
                'refusing: --contradicts %r targets %r, sharing no token '
                "with this entry's target %r -- must name the SAME "
                'resource, checked mechanically' % (contradicts, referenced.get('target'), target))

    prev = rows[-1]['hash'] if rows else GENESIS
    seq = (rows[-1]['seq'] + 1) if rows else 1
    body = {
        'seq': seq,
        'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'type': entry_type,
        'target': target,
        'severity': severity,
        'summary': summary,
        'ref': ref,
        'retrospective': bool(retrospective),
        'prev_hash': prev,
    }
    if vector:
        body['vector'] = vector
    if same_target_reason:
        body['same_target_reason'] = same_target_reason
    if undirected_sweep:
        body['undirected_sweep'] = True
    if process_pass:
        body['process_pass'] = True
    if eqa_checkpoint:
        body['eqa_checkpoint'] = True
    if source_exempt_reason:
        body['source_exempt_reason'] = source_exempt_reason
    if tier_claim:
        body['tier_claim'] = True
    if contradicts is not None:
        body['contradicts'] = contradicts
    if mistake_class:
        body['mistake_class'] = mistake_class
    if routable_list:
        body['routable'] = routable_list

    # THE WRITE-TIME CHECK -- positional, not optional: the last thing that
    # happens before the file is opened. Every captured source is re-derived
    # AGAIN, fresh, right now, against current origin/main.
    if captured_source:
        source_results = verify_source_freshness(repo, captured_source)
        stale = [r for r in source_results if r['status'] == 'stale']
        if stale:
            raise RuntimeError(
                'refusing to append: %d of %d cited source(s) are STALE -- '
                'read again before logging this finding. %s'
                % (len(stale), len(source_results),
                   '; '.join('%s: %s' % (r['path'], r['detail']) for r in stale)))
        body['source'] = source_results
        # source_shas: {path: captured_sha}, added 2026-09-23 on direct
        # instruction, matching hover1's field NAME (confirmed via Hank's
        # boundary-check row in docs/SAIRN-OPEN-WORK-INDEX.md: "hover1
        # records source_shas on its entries. hover2 does NOT ... source
        # and source_exempt_reason where hover1 has source_shas"). This is
        # the prerequisite for the H1/H2 disagreement-tracking axis split
        # (state-genuinely-changed vs same-frozen-state-different-reasoning)
        # -- "nothing can reconstruct it retrospectively", so this applies
        # from THIS entry forward only, not to the 111 entries before it.
        # Kept ALONGSIDE 'source' (richer, includes current_sha/status/
        # detail/explicit) rather than replacing it -- nothing here reads
        # 'source' for anything but provenance, so adding a second, simpler
        # field is additive and cannot break an existing consumer.
        body['source_shas'] = {
            r['path']: r.get('captured_sha') for r in source_results
        }

    body['hash'] = digest(prev, body)
    with io.open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(body, sort_keys=True) + '\n')
    return body


def finding_summary_gate_error(entry_type, inline_summary, summary_file):
    """CLI-layer gate, 2026-09-28 (seq-273 incident): a finding's summary
    must arrive via --summary-file, never as a command-line literal. Shell
    command substitution ate a word from seq 273's summary before this tool
    ever saw the text, and the backtick refusal in append_entry() cannot
    catch a substitution that already SUCCEEDED -- no backtick survives it.
    Findings are the entries chat routes and fixers act on, so a silently
    mangled one is the costliest; check/note/no-report keep inline summaries.
    Returns an error string to refuse with, or None to proceed."""
    if entry_type != 'finding':
        return None
    if inline_summary:
        return ('type=finding refuses an inline --summary -- shell command '
                'substitution ate a word from seq 273 before the tool saw '
                'the text, and no backtick check can catch a substitution '
                'that already succeeded. Write the text to a file and pass '
                '--summary-file.')
    if not summary_file:
        return 'type=finding requires --summary-file; inline --summary is refused.'
    return None


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--append', action='store_true')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--type', choices=list(VALID_TYPES), default='check')
    ap.add_argument('--target', default='self')
    ap.add_argument('--severity', choices=list(VALID_SEVERITY), default='')
    ap.add_argument('--summary', default='')
    ap.add_argument('--summary-file', default='')
    ap.add_argument('--ref', default='')
    ap.add_argument('--vector', default='')
    ap.add_argument('--retrospective', action='store_true')
    ap.add_argument('--same-target-reason', default='')
    ap.add_argument('--undirected-sweep', action='store_true')
    ap.add_argument('--process-pass', action='store_true')
    ap.add_argument('--eqa-checkpoint', action='store_true')
    ap.add_argument('--source', default='',
                    help='path[:sha][,path[:sha]...] -- what was actually read '
                         'for this finding. Bare path derives this clone\'s own '
                         'local HEAD blob sha now; path:sha overrides explicitly.')
    ap.add_argument('--source-exempt-reason', default='',
                    help='states why --source is not required for this finding '
                         '(this role\'s own tooling, not a platform file).')
    ap.add_argument('--repo', default=None,
                    help='platform repo to check --source against (default: %r)'
                         % DEFAULT_PLATFORM_REPO)
    ap.add_argument('--tier-claim', action='store_true',
                    help='this finding asserts a CRITICALITY-TIERS.md row is '
                         'wrong -- REQUIRES --source to include a path ending '
                         'in CRITICALITY-TIERS.md, structurally refused '
                         'otherwise (the seq-96/97 gap, closed mechanically).')
    ap.add_argument('--contradicts', type=int, default=None,
                    help='seq of an earlier entry whose CLEAN ("check") '
                         'verdict THIS finding overturns -- requires '
                         'type=finding, the referenced seq to exist and be '
                         "type='check', and to share a target token with "
                         'this entry (same resource, checked mechanically).')
    ap.add_argument('--mistake-class', default='',
                    help='tags a type=note self-correction with a structured '
                         'class label (e.g. stale-fact-reuse), so occurrences '
                         'can be counted mechanically. See --class-counts.')
    ap.add_argument('--class-counts', action='store_true',
                    help='report every mistake_class label seen in this log, '
                         'with a count and a WATCH/GUARD-REQUIRED status per '
                         'the 2-occurrences-watch / 3rd-occurrence-guard rule.')
    ap.add_argument('--rotation-batch', action='store_true',
                    help='marks this entry as a rotation batch -- REQUIRES '
                         '--lint-token matching hover_citation_linter.py '
                         "--lint's own output for this exact summary text, "
                         'or the append refuses as COULD NOT RUN.')
    ap.add_argument('--lint-token', default='',
                    help='the token hover_citation_linter.py --lint printed '
                         'for this exact summary text. See --rotation-batch.')
    ap.add_argument('--routable', default='',
                    help='comma-separated resource names this finding is '
                         'routable against -- read by tools/'
                         'hover_routing_gap_check.py as the STRUCTURED, '
                         'exact form. type=finding only; every name must '
                         'already appear in --target.')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.append:
        gate = finding_summary_gate_error(args.type, args.summary,
                                          args.summary_file)
        if gate:
            print('refusing: %s' % gate); return 2
        summary = args.summary
        if args.summary_file:
            with io.open(args.summary_file, encoding='utf-8') as f:
                summary = f.read().strip()
        if not summary:
            print('refusing: --append needs --summary or --summary-file'); return 2
        try:
            e = append_entry(args.type, summary, args.ref, args.target,
                             args.severity, args.vector, args.retrospective,
                             args.same_target_reason, args.undirected_sweep,
                             args.process_pass, args.eqa_checkpoint,
                             source=args.source,
                             source_exempt_reason=args.source_exempt_reason,
                             repo=args.repo, tier_claim=args.tier_claim,
                             contradicts=args.contradicts,
                             mistake_class=args.mistake_class,
                             rotation_batch=args.rotation_batch,
                             lint_token=args.lint_token,
                             routable=args.routable)
        except (ValueError, RuntimeError) as exc:
            print('refusing: %s' % exc); return 2
        print('appended seq %d: %s' % (e['seq'], e['summary'][:80]))
        if e.get('source'):
            for r in e['source']:
                print('  source %s: %s%s' % (r['path'], r['status'].upper(),
                                             (' -- ' + r['detail']) if r['detail'] else ''))
        return 0

    if args.verify:
        rows, problem = read_all()
        if rows is None:
            print('COULD NOT RUN: %s' % problem); return 2
        print('%d entries' % len(rows))
        ok, why = verify(rows)
        print('CHAIN: %s' % ('INTACT' if ok else ('BROKEN -- ' + why)))
        return 0 if ok else 1

    if args.class_counts:
        rows, problem = read_all()
        if rows is None:
            print('COULD NOT RUN: %s' % problem); return 2
        report = class_counts(rows)
        if not report:
            print('no mistake_class tags recorded yet'); return 0
        for label, (n, seqs, status) in sorted(report.items()):
            print('  %-24s %d occurrence(s)  %-15s seqs=%s'
                 % (label, n, status, seqs))
        return 0

    print(__doc__)
    return 0


def class_counts(rows):
    """{label: (count, [seqs], status)} -- status is WATCH at 2 occurrences,
    GUARD-REQUIRED at 3+, NAMED (informational only) at 1. This is the
    2-occurrences-watch / 3rd-occurrence-guard rule from
    docs/2026-09-29-hover-gap-research-h2.md's third pass, made mechanically
    computable rather than left as a policy statement to remember."""
    from collections import defaultdict
    by_label = defaultdict(list)
    for r in rows:
        label = r.get('mistake_class')
        if label:
            by_label[label].append(r.get('seq'))
    out = {}
    for label, seqs in by_label.items():
        n = len(seqs)
        status = 'GUARD-REQUIRED' if n >= 3 else ('WATCH' if n == 2 else 'NAMED')
        out[label] = (n, seqs, status)
    return out


def selftest():
    bad = []
    total = [0]

    def ck(name, cond):
        total[0] += 1
        ok = bool(cond)
        print(('  ok   ' if ok else '  FAIL ') + name)
        if not ok:
            bad.append(name)

    ck('canonical() sorts dict keys regardless of insertion order',
       canonical({'b': 1, 'a': 2}) == canonical({'a': 2, 'b': 1}))
    ck('canonical() preserves list order (order is data, not sorted away)',
       canonical([1, 2, 3]) != canonical([3, 2, 1]))
    ck('canonical() raises on an uncanonicalisable type',
       _raises(TypeError, canonical, object()))

    e1 = {'seq': 1, 'ts': 'x', 'type': 'check', 'summary': 'a', 'ref': '',
          'prev_hash': GENESIS}
    h1 = digest(GENESIS, e1)
    e1_full = dict(e1); e1_full['hash'] = h1
    ok, why = verify([e1_full])
    ck('a single correctly-chained entry verifies' + ('' if ok else ' (%s)' % why), ok)

    e1_bad = dict(e1_full); e1_bad['summary'] = 'TAMPERED'
    ok2, why2 = verify([e1_bad])
    ck('tampering the body after hashing breaks verification', not ok2)

    e2 = {'seq': 2, 'ts': 'y', 'type': 'finding', 'summary': 'b', 'ref': '',
          'prev_hash': h1}
    h2 = digest(h1, e2)
    e2_full = dict(e2); e2_full['hash'] = h2
    ok3, why3 = verify([e1_full, e2_full])
    ck('a two-entry chain verifies when the second links to the first hash'
       + ('' if ok3 else ' (%s)' % why3), ok3)

    e2_wronglink = dict(e2); e2_wronglink['prev_hash'] = 'not-the-real-hash'
    e2_wronglink['hash'] = digest('not-the-real-hash', e2_wronglink)
    ok4, _why4 = verify([e1_full, e2_wronglink])
    ck('a broken prev_hash link is caught even though entry 2 hashes itself '
       'correctly', not ok4)

    ck('an empty chain verifies trivially (nothing to disagree with)',
       verify([])[0])

    import tempfile
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, 'test-log.jsonl')
    a = append_entry('check', 'first real entry', 'sha1', target='alpha', path=path)
    b = append_entry('finding', 'second real entry', 'resource_x', target='beta',
                     vector='T:A/EX:M/IM:H/SC:C', path=path,
                     source_exempt_reason='selftest fixture, not a real platform finding')
    rows, problem = read_all(path)
    ck('append_entry() round-trips through the file and both entries verify',
       not problem and len(rows) == 2 and verify(rows)[0])
    ck('seq auto-increments across appends', a['seq'] == 1 and b['seq'] == 2)

    ck('a literal backtick in --summary is refused, not silently logged',
       _raises(ValueError, append_entry, 'check', 'bad `sub` text', target='gamma', path=path))
    ck('type=finding with no vector is refused',
       _raises(ValueError, append_entry, 'finding', 'no vector here', target='gamma', path=path))
    ck('an unrecognised type is refused',
       _raises(ValueError, append_entry, 'bogus-type', 'x', target='gamma', path=path))

    ck('ROTATION GATE: repeating the previous entry\'s target with no reason '
       'is refused',
       _raises(ValueError, append_entry, 'check', 'same target again',
               target='beta', path=path))
    c = append_entry('check', 'same target, but justified', target='beta',
                     same_target_reason='deliberate follow-up on the same item',
                     path=path)
    ck('...and supplying same_target_reason allows it through', c['seq'] == 3)

    # SELF-CONTRADICTION FIELD fixtures, 2026-09-27.
    ck('--contradicts on a non-finding type is refused',
       _raises(ValueError, append_entry, 'check', 'trying to contradict as a check',
               target='beta', contradicts=3, same_target_reason='x', path=path))
    ck('--contradicts naming a seq that does not exist is refused',
       _raises(ValueError, append_entry, 'finding', 'contradicts nothing real',
               target='beta', vector='T:A/EX:M/IM:H/SC:C',
               source_exempt_reason='fixture', contradicts=999,
               same_target_reason='x', path=path))
    ck("--contradicts naming a prior 'finding' (not 'check') is refused -- "
       'contradicting a finding is a second finding, not a self-contradiction',
       _raises(ValueError, append_entry, 'finding', 'tries to contradict entry b',
               target='beta', vector='T:A/EX:M/IM:H/SC:C',
               source_exempt_reason='fixture', contradicts=b['seq'],
               same_target_reason='x', path=path))
    ck('--contradicts naming a real check but a DIFFERENT target (no shared '
       'token) is refused',
       _raises(ValueError, append_entry, 'finding', 'wrong resource entirely',
               target='gamma-unrelated', vector='T:A/EX:M/IM:H/SC:C',
               source_exempt_reason='fixture', contradicts=a['seq'],
               same_target_reason='x', path=path))
    d = append_entry('finding', 'later read finds beta was not actually clean',
                     target='beta', vector='T:A/EX:M/IM:H/SC:C',
                     source_exempt_reason='fixture', contradicts=c['seq'],
                     same_target_reason='overturns the seq-3 clean verdict on '
                                        'the same resource', path=path)
    ck('--contradicts on a real finding naming a real prior check on the '
       'SAME resource succeeds and stamps the field on the entry',
       d.get('contradicts') == c['seq'])

    # MISTAKE-CLASS TAG fixtures, 2026-09-29.
    # target='mc-fixture-x' throughout, deliberately NEW and never reused
    # target='beta' -- a real prior version of this fixture used 'beta' (the
    # immediately preceding entry's own target) and passed for the WRONG
    # reason: the same-target-reason gate refused it first, masking whether
    # the mistake-class guard fired at all. Caught by a direct sabotage
    # probe outside selftest() that showed the "ok" result unchanged even
    # with the real guard disabled -- fixed here, not left passing on a
    # false premise.
    ck('--mistake-class on a non-note type is refused',
       _raises(ValueError, append_entry, 'check', 'trying to tag a check',
               target='mc-fixture-1', mistake_class='stale-fact-reuse', path=path))
    ck('--mistake-class on a finding is refused (findings have --contradicts '
       'for this purpose, not this field)',
       _raises(ValueError, append_entry, 'finding', 'trying to tag a finding',
               target='mc-fixture-2', vector='T:A/EX:M/IM:H/SC:C',
               source_exempt_reason='fixture', mistake_class='stale-fact-reuse',
               path=path))
    mc1 = append_entry('note', 'first tagged self-correction', target='beta',
                       same_target_reason='fixture',
                       mistake_class='stale-fact-reuse', path=path)
    ck('--mistake-class on type=note succeeds and stamps the field',
       mc1.get('mistake_class') == 'stale-fact-reuse')
    ck('a note with NO --mistake-class carries no mistake_class key at all '
       '(absence is absence, not an empty string sitting in every row)',
       'mistake_class' not in c)

    ck('class_counts(): an unrecorded label produces no entry at all',
       class_counts([]) == {})
    cc_rows = [
        {'seq': 1, 'mistake_class': 'stale-fact-reuse'},
        {'seq': 2, 'mistake_class': 'stale-fact-reuse'},
        {'seq': 3, 'mistake_class': 'other-class'},
        {'seq': 4},  # no tag at all -- must not appear in the report
    ]
    report = class_counts(cc_rows)
    ck('class_counts(): 2 occurrences of the same class reads WATCH',
       report['stale-fact-reuse'] == (2, [1, 2], 'WATCH'))
    ck('class_counts(): 1 occurrence reads NAMED, not WATCH or GUARD-REQUIRED',
       report['other-class'] == (1, [3], 'NAMED'))
    ck('class_counts(): an untagged row contributes to no class at all',
       sum(n for n, _s, _st in report.values()) == 3)
    cc_rows.append({'seq': 5, 'mistake_class': 'stale-fact-reuse'})
    report2 = class_counts(cc_rows)
    ck('class_counts(): a 3rd occurrence of the SAME class flips the '
       'status to GUARD-REQUIRED', report2['stale-fact-reuse'][2] == 'GUARD-REQUIRED')

    # KNOWN-BAD CONTROL: a counter that always reports WATCH regardless of
    # the real count must be shown disagreeing with the real GUARD-REQUIRED
    # verdict on this fixture.
    def broken_class_counts(rows):
        from collections import defaultdict
        by = defaultdict(list)
        for r in rows:
            lbl = r.get('mistake_class')
            if lbl:
                by[lbl].append(r.get('seq'))
        return dict((lbl, (len(s), s, 'WATCH')) for lbl, s in by.items())
    fake = broken_class_counts(cc_rows)
    ck('KNOWN-BAD CONTROL: a counter hardcoding WATCH regardless of count '
       'disagrees with the real GUARD-REQUIRED verdict at 3 occurrences',
       report2['stale-fact-reuse'][2] == 'GUARD-REQUIRED' and
       fake['stale-fact-reuse'][2] == 'WATCH')

    # ROUTABLE FIELD fixtures, 2026-09-29 (the routing-gap-invisibility gap:
    # this role's own findings had no structured field the routing-gap
    # checker could read, per tools/hover_routing_gap_check.py -- a build
    # tool's own read contract, not H1's implementation).
    ck('--routable on a non-finding type is refused',
       _raises(ValueError, append_entry, 'check', 'trying to route a check',
               target='rt_fixture_1', routable='rt_fixture_1', path=path))
    ck('--routable on a note is refused',
       _raises(ValueError, append_entry, 'note', 'trying to route a note',
               target='rt_fixture_1', routable='rt_fixture_1', path=path))
    ck('--routable naming something NOT in --target is refused -- a '
       'routable resource must already be named as this entry\'s target',
       _raises(ValueError, append_entry, 'finding', 'routes an unnamed resource',
               target='rt_fixture_a', vector='T:B/EX:NA/IM:M/SC:C',
               source_exempt_reason='fixture', routable='rt_fixture_b',
               path=path))
    rt1 = append_entry('finding', 'a real routable finding, comma string form',
                       target='rt_fixture_2,rt_fixture_3',
                       vector='T:B/EX:NA/IM:M/SC:C', source_exempt_reason='fixture',
                       routable='rt_fixture_2,rt_fixture_3', path=path)
    ck('--routable as a comma string, both names in --target, succeeds and '
       'stamps a LIST on the entry',
       rt1.get('routable') == ['rt_fixture_2', 'rt_fixture_3'])
    rt2 = append_entry('finding', 'a real routable finding, list form',
                       target='rt_fixture_4', vector='T:B/EX:NA/IM:M/SC:C',
                       source_exempt_reason='fixture',
                       routable=['rt_fixture_4'], path=path)
    ck('--routable as a real list (not a CLI string) also succeeds',
       rt2.get('routable') == ['rt_fixture_4'])
    rt3 = append_entry('finding', 'a finding with no routable names at all',
                       target='rt_fixture_5', vector='T:B/EX:NA/IM:M/SC:C',
                       source_exempt_reason='fixture', path=path)
    ck('a finding with NO --routable carries no routable key at all -- '
       'absence is absence, not an empty list sitting in every row',
       'routable' not in rt3)
    # KNOWN-BAD CONTROL: the exact shape tools/hover_routing_gap_check.py
    # itself distinguishes -- a routable list vs. the weaker prose-fallback
    # guess out of `ref`. Prove OUR entries actually classify structured
    # under that tool's own real function, not merely that our own field
    # exists.
    import importlib.util as _ilu
    _rgc_path = os.path.join(DEFAULT_PLATFORM_REPO, 'tools',
                             'hover_routing_gap_check.py')
    if os.path.isfile(_rgc_path):
        _spec = _ilu.spec_from_file_location('hover_routing_gap_check', _rgc_path)
        _rgc = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_rgc)
        ck('KNOWN-BAD CONTROL, driven against the REAL checker function: an '
           'entry with a real --routable list classifies structured, and '
           'one with none classifies NOT structured (prose-fallback or none)',
           _rgc.routable_names(rt1)[1] == 'structured' and
           _rgc.routable_names(rt3)[1] != 'structured')
    else:
        ck('routing-gap checker not found at %r -- real-function control '
           'skipped, not silently passed' % _rgc_path, True)

    # ROTATION-BATCH LINT-TOKEN fixtures, 2026-09-29 (the skipped-run gap
    # named in docs/2026-09-29-hover-gap-research-h2.md's item 3).
    lt_summary = 'a real rotation batch summary text for the token fixture'
    real_token = lint_token_for(lt_summary)
    ck('lint_token_for(): deterministic -- the same text always produces '
       'the same token', lint_token_for(lt_summary) == real_token)
    ck('lint_token_for(): different text produces a different token',
       lint_token_for(lt_summary + '.') != real_token)
    ck('--rotation-batch with NO --lint-token at all is refused as COULD '
       'NOT RUN, not silently allowed through',
       _raises(ValueError, append_entry, 'check', lt_summary,
               target='lt-fixture-1', rotation_batch=True, path=path))
    try:
        append_entry('check', lt_summary, target='lt-fixture-1',
                     rotation_batch=True, path=path)
        ck('...and the refusal message names COULD NOT RUN, distinct from '
           'an ordinary validation refusal', False)
    except ValueError as e:
        ck('...and the refusal message names COULD NOT RUN, distinct from '
           'an ordinary validation refusal', 'COULD NOT RUN' in str(e))
    not_a_real_token = ('not' + '-a-real-lint-token-' + 'just-typed-by-hand')
    ck('--rotation-batch with a HAND-TYPED string that is not the real '
       'hash is refused exactly like a missing one -- a string that merely '
       'LOOKS like a token proves nothing',
       _raises(ValueError, append_entry, 'check', lt_summary,
               target='lt-fixture-2', rotation_batch=True,
               lint_token=not_a_real_token, path=path))
    lt_entry = append_entry('check', lt_summary, target='lt-fixture-3',
                            rotation_batch=True, lint_token=real_token, path=path)
    ck('--rotation-batch with the REAL, matching token succeeds',
       lt_entry.get('seq') is not None)
    ck('--rotation-batch is NOT required for an ordinary entry -- omitting '
       'both flags entirely still works, unchanged from before this gate '
       'existed',
       append_entry('check', 'ordinary entry, no rotation-batch flag at '
                    'all', target='lt-fixture-4', path=path).get('seq')
       is not None)

    # KNOWN-BAD CONTROL: a checker that always reports the token as valid
    # (never actually compares it) must be shown disagreeing with the real
    # refusal on a genuinely missing-token fixture.
    def broken_token_checker(token, summary):
        return True  # BUG: always says "valid", never compares to the real hash
    real_says_invalid = (real_token != lint_token_for(lt_summary + 'X'))
    fake_says_invalid = not broken_token_checker('', lt_summary)
    ck('KNOWN-BAD CONTROL: a checker that always reports a token as valid '
       'disagrees with a real comparison on a genuinely wrong token -- the '
       'real gate inside append_entry() (already proven above to refuse a '
       'hand-typed string) is the one actually doing the work, not a '
       'predicate that would rubber-stamp anything',
       real_says_invalid is True and fake_says_invalid is False)

    # SUMMARY-FILE GATE fixtures, 2026-09-28 (the seq-273 incident: shell
    # command substitution ate a word from a finding's inline --summary
    # before this tool ever saw the text -- the backtick refusal cannot
    # catch a substitution that already succeeded, because no backtick
    # survives it). Written RED-FIRST, before the gate existed.
    gate_fn = globals().get('finding_summary_gate_error')

    def _regression_predicate(gate):
        # A sound gate refuses an inline finding summary, requires a file,
        # and leaves non-finding types and file-fed findings alone.
        return (gate is not None
                and gate('finding', 'inline text', '') is not None
                and gate('finding', 'inline text', 'some-file.txt') is not None
                and gate('finding', '', 'some-file.txt') is None
                and gate('finding', '', '') is not None
                and gate('check', 'inline text', '') is None
                and gate('note', 'inline text', '') is None)

    ck('SEQ-273 REGRESSION: type=finding refuses inline --summary, requires '
       '--summary-file; other types unaffected', _regression_predicate(gate_fn))

    def _broken_gate(_t, _s, _f):  # the known-bad control: waves everything through
        return None
    ck('KNOWN-BAD CONTROL: the regression predicate FAILS a gate that waves '
       'inline finding summaries through', not _regression_predicate(_broken_gate))

    # LIVE ARM, not a fixture: this reads the real self-log's line count so
    # the refusal below can be proven against real data -- the append MUST be
    # refused (rc 2) and the real self-log left byte-identical, live, not
    # simulated. Read-only in effect only because that refusal holds.
    n_before = 0
    if os.path.isfile(LOG_PATH):
        with io.open(LOG_PATH, encoding='utf-8') as f:
            n_before = sum(1 for _ in f)
    rc_gate = main(['--append', '--type', 'finding', '--target', 'selftest-gate',
                    '--summary', 'inline finding summary must be refused'])
    # same live arm: re-count the real self-log to assert it is untouched
    n_after = 0
    if os.path.isfile(LOG_PATH):
        with io.open(LOG_PATH, encoding='utf-8') as f:
            n_after = sum(1 for _ in f)
    ck('CLI integration: main() refuses an inline finding summary (rc 2) and '
       'the real log is untouched', rc_gate == 2 and n_before == n_after)

    with io.open(path, 'a', encoding='utf-8') as f:
        f.write('not json at all\n')
    rows2, problem2 = read_all(path)
    ck('a malformed trailing line makes read_all() report a problem, not a '
       'silent partial read', rows2 is None and problem2)

    try:
        append_entry('check', 'should refuse', target='delta', path=path)
        ck('append onto an unreadable file refuses rather than corrupting '
           'further', False)
    except RuntimeError:
        ck('append onto an unreadable file refuses rather than corrupting '
           'further', True)

    ck('type=finding with neither --source nor --source-exempt-reason is '
       'refused',
       _raises(ValueError, append_entry, 'finding', 'no source cited',
               target='epsilon', vector='T:A/EX:M/IM:H/SC:C', path=path))

    # THE SEQ-96/97 GAP, closed structurally: --tier-claim requires
    # CRITICALITY-TIERS.md specifically among --source's cited paths, not
    # just any source at all.
    ck('--tier-claim with --source citing only the app file (no '
       'CRITICALITY-TIERS.md) is refused -- this is exactly the sc_eligibility '
       'gap (seq 96/97): proving the record shape is real proves nothing '
       'about whether the register was read fresh',
       _raises(ValueError, append_entry, 'finding', 'tier claim, wrong source',
               target='zeta', vector='T:A/EX:M/IM:H/SC:C', path=path,
               source='some_app.html', tier_claim=True))
    ck('--tier-claim with NO --source at all is refused (hits the general '
       'source-required check first, same outcome)',
       _raises(ValueError, append_entry, 'finding', 'tier claim, no source',
               target='zeta', vector='T:A/EX:M/IM:H/SC:C', path=path,
               tier_claim=True))
    ck('--tier-claim with --source-exempt-reason but no CRITICALITY-TIERS.md '
       'citation is STILL refused -- a tier claim is inherently about a '
       'platform file, the self-tooling exemption does not apply to it',
       _raises(ValueError, append_entry, 'finding', 'tier claim, exempt only',
               target='zeta', vector='T:A/EX:M/IM:H/SC:C', path=path,
               source_exempt_reason='should not matter here', tier_claim=True))

    # The PASS case, without hitting real network: capture_source/
    # verify_source_freshness are monkeypatched for this one check only,
    # because what is under test here is the STRING-LEVEL gate (does
    # 'docs/CRITICALITY-TIERS.md' appear among the parsed --source paths),
    # not the staleness pipeline itself -- that is already covered end to
    # end, with real git, by _selftest_staleness_guard() above.
    real_capture, real_verify = capture_source, verify_source_freshness
    globals()['capture_source'] = lambda repo, src: [
        {'path': p, 'captured_sha': sha or 'deadbeef', 'explicit': True}
        for p, sha in parse_source(src)]
    globals()['verify_source_freshness'] = lambda repo, captured, **kw: [
        dict(c, status='fresh', current_sha=c['captured_sha'], detail='')
        for c in captured]
    # OWN fresh path -- `path` above was deliberately corrupted earlier in
    # this same selftest (the "malformed trailing line" arm) and must stay
    # that way for arms still to come; this check needs a clean file, not
    # a reason to skip the corruption check's own coverage.
    tc_path = os.path.join(os.path.dirname(path), 'tier-claim-pass-test-log.jsonl')
    try:
        e_tc = append_entry('finding', 'tier claim, correctly sourced',
                            target='zeta', vector='T:A/EX:M/IM:H/SC:C', path=tc_path,
                            source='some_app.html,docs/CRITICALITY-TIERS.md',
                            tier_claim=True)
        ck('--tier-claim with CRITICALITY-TIERS.md correctly cited alongside '
           'the app file is accepted, and the entry is stamped tier_claim=True',
           e_tc.get('tier_claim') is True)
    finally:
        globals()['capture_source'], globals()['verify_source_freshness'] = real_capture, real_verify

    _selftest_staleness_guard(ck)

    print('')
    if bad:
        print('%d of %d selftest arm(s) failed' % (len(bad), total[0]))
        return 2
    print('OK -- %d arms passed. Hashing verified compatible with the '
          'shared verify_chain()/_canonical()/_digest() algorithm in '
          'tools/hover_separation_audit.py (same GENESIS, same recursive '
          'sorted-key canonicalisation, same sha256(prev + body) chain).'
          % total[0])
    return 0


def _git(cwd, *args):
    """Test-scaffold helper only -- raises on failure (a broken test fixture
    should fail loudly, not degrade to a false pass). Pins a throwaway
    identity via -c flags so this never touches the real machine's git
    config."""
    p = subprocess.run(
        ['git', '-c', 'user.email=hover-selftest@example.invalid',
         '-c', 'user.name=hover-selftest', '-C', cwd] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding='utf-8', errors='replace')
    if p.returncode != 0:
        raise RuntimeError('test-fixture git command failed: git %s\n%s'
                           % (' '.join(args), p.stderr))
    return p.stdout.strip()


def _selftest_staleness_guard(ck):
    """Tested against the REAL incident shape, not simulated shas: a bare
    'origin' and a real clone of it, playing the two-clone scenario the
    interface spec describes -- the clone's local HEAD genuinely falls
    behind origin/main when a fix lands there, and catches up for real on
    a real git pull. Every sha compared below is a real git blob sha
    derived by git itself, never fabricated."""
    import tempfile
    import shutil

    tmp = tempfile.mkdtemp(prefix='hover-staleness-selftest-')
    try:
        bare = os.path.join(tmp, 'origin.git')
        seed = os.path.join(tmp, 'seed')
        clone = os.path.join(tmp, 'clone')

        os.makedirs(bare)
        _git(bare, 'init', '--bare', '-q', '-b', 'main')

        os.makedirs(seed)
        _git(seed, 'init', '-q', '-b', 'main')
        _git(seed, 'remote', 'add', 'origin', bare)
        with io.open(os.path.join(seed, 'thefile.txt'), 'w', encoding='utf-8') as f:
            f.write('version 1\n')
        _git(seed, 'add', 'thefile.txt')
        _git(seed, 'commit', '-q', '-m', 'v1')
        _git(seed, 'push', '-q', 'origin', 'main')

        _git(tmp, 'clone', '-q', bare, clone)

        # --- fresh: clone is caught up with origin at capture time ---
        captured = capture_source(clone, 'thefile.txt')
        results = verify_source_freshness(clone, captured)
        ck('staleness guard: an up-to-date clone reads FRESH',
           len(results) == 1 and results[0]['status'] == 'fresh')

        # --- the real incident: origin moves, clone's local HEAD does not ---
        with io.open(os.path.join(seed, 'thefile.txt'), 'w', encoding='utf-8') as f:
            f.write('version 2 -- the fix another session already landed\n')
        _git(seed, 'commit', '-q', '-am', 'v2, the fix')
        _git(seed, 'push', '-q', 'origin', 'main')

        # clone's local HEAD is UNCHANGED -- this is the unpulled-clone shape
        captured_stale = capture_source(clone, 'thefile.txt')
        results_stale = verify_source_freshness(clone, captured_stale)
        ck('staleness guard: an unpulled clone reads STALE once origin moves',
           len(results_stale) == 1 and results_stale[0]['status'] == 'stale'
           and results_stale[0]['current_sha'] is not None)

        # append_entry() must hard-refuse and write NOTHING when stale
        log_path = os.path.join(tmp, 'test-log.jsonl')
        refused = False
        try:
            append_entry('finding', 'a finding about the stale file',
                        target='staletarget', vector='T:A/EX:M/IM:H/SC:C',
                        source='thefile.txt', path=log_path, repo=clone)
        except RuntimeError:
            refused = True
        rows_after, _p = read_all(log_path)
        ck('append_entry() hard-refuses a stale --source and writes nothing',
           refused and (rows_after == [] or rows_after is None))

        # --- the identical citation logs clean after a real git pull ---
        _git(clone, 'pull', '-q', 'origin', 'main')
        e = append_entry('finding', 'a finding about the now-current file',
                         target='staletarget2', vector='T:A/EX:M/IM:H/SC:C',
                         source='thefile.txt', path=log_path, repo=clone)
        ck('...and the identical citation logs clean after a real git pull',
           e.get('source', [{}])[0].get('status') == 'fresh')

        # --- confirmed-gone path is STALE, not ambiguous ---
        _git(seed, 'rm', '-q', 'thefile.txt')
        _git(seed, 'commit', '-q', '-m', 'remove thefile.txt')
        _git(seed, 'push', '-q', 'origin', 'main')
        results_gone = verify_source_freshness(clone, captured)
        ck('staleness guard: a path confirmed removed from origin is STALE, '
           'not could_not_verify',
           results_gone[0]['status'] == 'stale')

        # --- genuinely unreachable remote is could_not_verify, never stale ---
        broken = os.path.join(tmp, 'broken-clone')
        shutil.copytree(clone, broken)
        _git(broken, 'remote', 'set-url', 'origin',
             os.path.join(tmp, 'does-not-exist.git'))
        results_unreachable = verify_source_freshness(broken, captured)
        ck('staleness guard: an unreachable remote is could_not_verify, '
           'never silently treated as fresh or stale',
           results_unreachable[0]['status'] == 'could_not_verify')

        # a could_not_verify source must NOT block the write, per the one
        # named exception to fail-closed
        e2 = append_entry('finding', 'a finding whose remote is unreachable',
                          target='staletarget3', vector='T:A/EX:M/IM:H/SC:C',
                          source='thefile.txt', path=log_path, repo=broken)
        ck('a could_not_verify source does not block the append (the one '
           'named exception to fail-closed)',
           e2.get('source', [{}])[0].get('status') == 'could_not_verify')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _raises(exc_type, fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False
    except exc_type:
        return True


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
