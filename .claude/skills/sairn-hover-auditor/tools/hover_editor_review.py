#!/usr/bin/env python
"""hover_editor_review.py -- the EDITOR pass: a mechanical re-derivation of a
report's own checkable claims against CURRENT source, run before the report
is pasted to Michael.

WHERE IT SITS IN THE PIPELINE, and why it is not a duplicate of what exists:
hover_second_opinion.py (the supervisor-equivalent) hands a finding's OWN
WRITTEN EVIDENCE to a different model for a fresh read -- it deliberately
does not re-open source. This tool is the structural complement (discipline
6, different method): it ignores the reasoning entirely and re-derives the
citations FROM the source -- every commit hash re-resolved with git, every
cited path re-stat'ed, every file:line re-read for its claimed anchor, every
"N hours later" recomputed from real commit timestamps. It catches the class
today's H2 report caught in finished reviews: a dangling pre-rebase hash
(e2765029's verdict cited a387e9ca three times; only 7df1e47c exists), a
cited line that drifted (98a37b09 cited report_only_checks.py:855; the entry
sits at 860), a stated "FOUR HOURS LATER" that is one hour by every
timestamp source (306e8930). It cannot catch a wrong MECHANISM claim
(05cfb0ed's "hydration bails first") -- that class needs instrumented
re-execution and this tool says so rather than implying coverage.

FAIL-CLOSED (PR 1.11): git missing or the target not a repo is exit 2 COULD
NOT RUN, never a pass. A cited file that exists but cannot be read is a
CANNOT-CHECK row, counted and printed -- a third state, never folded into
"passed". A report from which nothing checkable extracts prints
NOTHING-TO-CHECK first; that is not a pass either.

BLIND LOCK (discipline 1): every run rebuilds a throwaway git repo and
classifies the synthetic fixtures in hover_editor_review_criteria.py FIRST,
in isolation. Any fixture misclassifying is exit 2 -- nothing real was
judged. Criteria are stamped CRITERIA_VERSION.

Run:
  python hover_editor_review.py --report <file> [--repo <path>]
  python hover_editor_review.py --stdin [--repo <path>]
  python hover_editor_review.py --report <f> --default-file <path>
                                   -- resolves bare `:NNNN` citations (the
                                      register's own evidence-cell shape,
                                      CRITERIA_VERSION 3) against <path>;
                                      omit and they report CANNOT-CHECK
  python hover_editor_review.py --fixtures        # lock only
Exit: 0 all checked claims hold and none were skipped; 1 findings;
      2 could not run; 3 no findings but some claims could not be checked.
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import hover_editor_review_criteria as C

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run_git(repo, *args):
    try:
        r = subprocess.run(["git"] + list(args), cwd=repo,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None, "git executable not found"
    return (r.stdout.strip(), None) if r.returncode == 0 else (None, r.stderr.strip())


def paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def sentences(paragraph):
    # (?<=[.!?])\*{0,2}\s+ -- not just \s+. Register prose bolds sentence-
    # final punctuation ("...individually.**"), so a period is followed by
    # `**` with NO whitespace before the real gap; a bare \s+ split missed
    # that boundary entirely and merged the bolded sentence into the next
    # one, letting an EARLIER clause's backticked token (e.g. "`sf_*`" in a
    # re-audit header) leak into a LATER citation's anchor search -- found
    # 2026-09-28 testing CRITERIA_VERSION 3 against a real register row
    # (sf_ceremonial_items), where the leaked token coincidentally matched
    # elsewhere in the file and produced a false LINE-MISMATCH. Locked by F22.
    return [s for s in re.split(r"(?<=[.!?])\*{0,2}\s+", paragraph) if s.strip()]


class Review:
    def __init__(self, repo, default_file=None):
        self.repo = repo
        # default_file: resolves a bare `:NNNN` citation (CRITERIA_VERSION 3,
        # 2026-09-28) -- the register's own evidence cells cite these with
        # the file implied by which row's cell they sit in, never restated.
        # None means "no assumption offered" -> CANNOT-CHECK, never guessed.
        self.default_file = default_file
        self.rows = []          # (kind, cls, detail)  kind: OK/DRIFT/SHALLOW/CANNOT/FINDING
        self._lsfiles = None
        self._hash_cache = {}

    def row(self, kind, cls, detail):
        self.rows.append((kind, cls, detail))

    # -- git-backed lookups -----------------------------------------------
    def ls_files(self):
        if self._lsfiles is None:
            out, err = run_git(self.repo, "ls-files")
            self._lsfiles = out.splitlines() if out is not None else []
        return self._lsfiles

    def resolve_hash(self, tok):
        """-> (full_sha or None, objtype or None, err)"""
        if tok in self._hash_cache:
            return self._hash_cache[tok]
        t, terr = run_git(self.repo, "cat-file", "-t", tok)
        if t is None:
            res = (None, None, terr)
        else:
            full, _ = run_git(self.repo, "rev-parse", tok)
            res = (full or tok, t, None)
        self._hash_cache[tok] = res
        return res

    def commit_times(self, sha):
        out, _ = run_git(self.repo, "log", "-1", "--format=%cI|%aI", sha)
        if not out or "|" not in out:
            return None, None
        c, a = out.split("|", 1)
        try:
            return (datetime.fromisoformat(c), datetime.fromisoformat(a))
        except ValueError:
            return None, None

    def resolve_path(self, path):
        """-> (worktree_abspath or None, note or None). Bare filenames fall
        back to a unique basename match in git ls-files."""
        p = os.path.join(self.repo, path)
        if os.path.isfile(p):
            return p, None
        base = os.path.basename(path)
        hits = [f for f in self.ls_files() if os.path.basename(f) == base]
        if len(hits) == 1:
            return os.path.join(self.repo, hits[0]), "resolved as %s" % hits[0]
        if len(hits) > 1:
            return None, "AMBIGUOUS: %d files named %s" % (len(hits), base)
        return None, None

    # -- claim checks ------------------------------------------------------
    def check_hash(self, tok, sentence):
        full, typ, err = self.resolve_hash(tok)
        if full:
            self.row("OK", "hash", "%s resolves (%s)" % (tok, typ))
        elif err and "ambiguous" in (err or "").lower():
            self.row("OK", "hash", "%s ambiguous-but-real prefix" % tok)
        elif C.is_negated(sentence):
            self.row("OK", "hash",
                     "%s does not resolve, and the report SAYS so" % tok)
        else:
            self.row("FINDING", "hash",
                     "DANGLING-REF: %s is not an object in this repo "
                     "(a pre-rebase hash?). Sentence: %s"
                     % (tok, squeeze(sentence)))

    def check_fileline(self, path, l1, l2, sentence, implied=False):
        # implied=True: `path` was not written in the report -- it is
        # self.default_file, supplied by the caller as the file a bare
        # `:NNNN` citation is understood to mean. Every message says so
        # explicitly so a reader never mistakes an assumption for a quote.
        tag = "IMPLIED-FILE %s" % path if implied else path
        cls = "path-implied" if implied else "path"
        lcls = "line-implied" if implied else "line"
        negated = C.is_negated(sentence)
        abspath, note = self.resolve_path(path)
        if abspath is None:
            if negated:
                self.row("OK", cls,
                         "%s absent, and the report SAYS it is absent" % tag)
            elif note:  # ambiguous basename
                self.row("CANNOT", cls, "%s: %s" % (tag, note))
            else:
                self.row("FINDING", cls,
                         "MISSING-PATH: %s not in worktree or git ls-files. "
                         "Sentence: %s" % (tag, squeeze(sentence)))
            return
        if l1 is None:
            self.row("OK", cls, tag + (" (%s)" % note if note else ""))
            return
        try:
            with io.open(abspath, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError as e:
            self.row("CANNOT", lcls,
                     "%s:%s exists but could not be read (%s) -- "
                     "NOT checked, NOT a pass" % (tag, l1, e))
            return
        lo, hi = l1, (l2 or l1)
        if lo > hi:
            lo, hi = hi, lo
        if hi > len(lines):
            self.row("FINDING", lcls,
                     "LINE-OUT-OF-RANGE: %s:%d cited; file has %d lines. "
                     "Sentence: %s" % (tag, hi, len(lines), squeeze(sentence)))
            return
        own_stem = os.path.basename(path).rsplit(".", 1)[0]
        cands = {c for c in C.anchor_candidates(sentence) if c != own_stem}
        if not cands:
            self.row("SHALLOW", lcls,
                     "%s:%d line-bounds only -- no anchor extractable "
                     "from the sentence" % (tag, l1))
            return
        best = None  # (distance, cand, at_line)
        for cand in cands:
            for i, ln in enumerate(lines, 1):
                if C.anchor_in_line(cand, ln):
                    d = 0 if lo <= i <= hi else min(abs(i - lo), abs(i - hi))
                    if best is None or d < best[0]:
                        best = (d, cand, i)
        if best is None:
            # NEGATION EXEMPTION, added 2026-09-29 (H1's own log #658): a
            # report can correctly ASSERT an anchor's absence ("field X is
            # no longer written at line Y") -- `negated` (is_negated on the
            # whole sentence, computed once at the top of this function) was
            # already being consulted for the MISSING-PATH branch above but
            # never here, so a TRUE negated-absence claim read as a FALSE
            # ANCHOR-ABSENT finding. F28/F29 lock both directions: negated
            # -> OK, the identical shape with no negation wording -> still
            # FINDING.
            if negated:
                self.row("OK", lcls,
                         "%s:%d -- none of %s appear on the cited line, and "
                         "the report SAYS the field/anchor is no longer "
                         "there" % (tag, l1, sorted(cands)))
            else:
                self.row("FINDING", lcls,
                         "ANCHOR-ABSENT: none of %s appear anywhere in %s "
                         "(cited :%d). Sentence: %s"
                         % (sorted(cands), tag, l1, squeeze(sentence)))
        elif best[0] == 0:
            self.row("OK", lcls, "%s:%d anchor '%s' on the cited line"
                     % (tag, l1, best[1]))
        elif best[0] <= C.LINE_DRIFT_FINDING:
            self.row("DRIFT", lcls,
                     "%s:%d -> '%s' actually at :%d (drift %d, within %d)"
                     % (tag, l1, best[1], best[2], best[0],
                        C.LINE_DRIFT_FINDING))
        else:
            self.row("FINDING", lcls,
                     "LINE-MISMATCH: %s:%d cited for '%s' which is at :%d "
                     "(drift %d > %d). Sentence: %s"
                     % (tag, l1, best[1], best[2], best[0],
                        C.LINE_DRIFT_FINDING, squeeze(sentence)))

    def check_duration(self, stated_s, phrase, para_hashes, dur_pos):
        commits = []
        seen = set()
        for pos, tok in para_hashes:
            full, typ, _ = self.resolve_hash(tok)
            if full and typ == "commit" and full not in seen:
                seen.add(full)
                commits.append((abs(pos - dur_pos), full, tok))
        if len(commits) < 2:
            self.row("CANNOT", "duration",
                     "'%s' -- fewer than two resolvable commits in the "
                     "paragraph to measure against; NOT checked, NOT a pass"
                     % phrase)
            return
        commits.sort()
        (_, sha_a, tok_a), (_, sha_b, tok_b) = commits[0], commits[1]
        ca, aa = self.commit_times(sha_a)
        cb, ab = self.commit_times(sha_b)
        if not (ca and cb):
            self.row("CANNOT", "duration",
                     "'%s' -- could not read commit times for %s/%s"
                     % (phrase, tok_a, tok_b))
            return
        dc = abs((ca - cb).total_seconds())
        da = abs((aa - ab).total_seconds()) if (aa and ab) else dc
        tol = max(C.DURATION_TOLERANCE_MIN_SECONDS,
                  C.DURATION_TOLERANCE_FRACTION * stated_s)
        if abs(dc - stated_s) > tol and abs(da - stated_s) > tol:
            self.row("FINDING", "duration",
                     "DURATION-MISMATCH: '%s' stated between %s and %s, but "
                     "committer gap is %s and author gap is %s (tolerance %s)"
                     % (phrase, tok_a, tok_b, hms(dc), hms(da), hms(tol)))
        else:
            self.row("OK", "duration",
                     "'%s' vs %s..%s measured %s" % (phrase, tok_a, tok_b,
                                                     hms(dc)))

    # -- driver ------------------------------------------------------------
    def review_text(self, text):
        for para in paragraphs(text):
            para_hashes = []   # (pos_in_para, token)
            durations = []     # (pos_in_para, stated_seconds, phrase)
            for sent in sentences(para):
                spans = []
                for m in C.FILELINE.finditer(sent):
                    spans.append(m.span())
                    l1 = int(m.group(2)) if m.group(2) else None
                    l2 = int(m.group(3)) if m.group(3) else None
                    self.check_fileline(m.group(1), l1, l2, sent)
                for m in C.IMPLIED_LINE.finditer(sent):
                    if any(a <= m.start() < b for a, b in spans):
                        continue  # already the tail of an explicit path:line
                    spans.append(m.span())
                    l1 = int(m.group(1))
                    l2 = int(m.group(2)) if m.group(2) else None
                    if self.default_file:
                        self.check_fileline(self.default_file, l1, l2, sent,
                                            implied=True)
                    else:
                        self.row("CANNOT", "line-implied",
                                 "IMPLIED-FILE :%d cited with no file named in "
                                 "this sentence and no --default-file given -- "
                                 "NOT checked, NOT a pass. Sentence: %s"
                                 % (l1, squeeze(sent)))
                for m in C.HEX_TOKEN.finditer(sent):
                    if any(a <= m.start() < b for a, b in spans):
                        continue
                    tok = m.group(0)
                    if not C.hexish(tok):
                        continue
                    para_hashes.append((para.find(tok), tok))
                    self.check_hash(tok, sent)
                for m in C.DURATION.finditer(sent):
                    stated = C.parse_duration_seconds(m.group(1), m.group(2))
                    if stated is not None:
                        durations.append((para.find(m.group(0)),
                                          stated, m.group(0)))
            for pos, stated, phrase in durations:
                self.check_duration(stated, phrase, para_hashes, pos)

    def counts(self):
        c = {"OK": 0, "DRIFT": 0, "SHALLOW": 0, "CANNOT": 0, "FINDING": 0}
        for kind, _, _ in self.rows:
            c[kind] += 1
        c["claims"] = len(self.rows)
        return c


def squeeze(s, n=160):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 3] + "..."


def hms(seconds):
    seconds = int(round(seconds))
    return "%dh%02dm" % (seconds // 3600, (seconds % 3600) // 60)


# --- fixture lock ---------------------------------------------------------

def run_fixture_lock(verbose):
    try:
        d, sha1, sha2, sha3 = C.build_fixture_repo()
    except (RuntimeError, OSError) as e:
        print("COULD NOT RUN: fixture repo build failed (%s)." % e)
        print("Nothing real was judged.")
        return False, 0
    try:
        ok = True
        count = 0
        for name, text, exp in C.fixtures(sha1, sha2, sha3):
            count += 1
            # F26/F27 (2026-09-28): a realistic-transition fixture needs the
            # repo's WORKING TREE to genuinely be at the post-shift commit,
            # not just a claim about it -- checkout for real, run, restore
            # sha2 in a finally so a checkout failure never leaves later
            # fixtures silently running against the wrong tree state.
            checkout_sha = exp.get("checkout")
            if checkout_sha:
                run_git(d, "checkout", "-q", checkout_sha)
            try:
                r = Review(d, default_file=exp.get("default_file"))
                r.review_text(text)
                c = r.counts()
            finally:
                if checkout_sha:
                    run_git(d, "checkout", "-q", sha2)
            fails = []
            if c["FINDING"] != exp.get("findings", 0):
                fails.append("findings %d != %d" % (c["FINDING"],
                                                    exp.get("findings", 0)))
            if "drift_notes" in exp and c["DRIFT"] != exp["drift_notes"]:
                fails.append("drift %d != %d" % (c["DRIFT"],
                                                 exp["drift_notes"]))
            if "shallow" in exp and c["SHALLOW"] != exp["shallow"]:
                fails.append("shallow %d != %d" % (c["SHALLOW"], exp["shallow"]))
            if c["CANNOT"] != exp.get("cannot_check", 0):
                fails.append("cannot %d != %d" % (c["CANNOT"],
                                                  exp.get("cannot_check", 0)))
            if c["claims"] < exp.get("min_claims", 0):
                fails.append("claims %d < %d" % (c["claims"],
                                                 exp["min_claims"]))
            if "max_claims" in exp and c["claims"] > exp["max_claims"]:
                fails.append("claims %d > %d (an explicit citation must not "
                             "ALSO be double-counted as implied)"
                             % (c["claims"], exp["max_claims"]))
            if exp.get("nothing_to_check") and c["claims"] != 0:
                fails.append("expected nothing checkable, got %d claims"
                             % c["claims"])
            if fails:
                ok = False
                print("FIXTURE FAIL  %s: %s" % (name, "; ".join(fails)))
                for kind, cls, detail in r.rows:
                    print("    [%s %s] %s" % (kind, cls, detail))
            elif verbose:
                print("fixture ok    %s" % name)
        return ok, count
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--fixtures", action="store_true")
    ap.add_argument("--default-file",
                    help="resolve bare `:NNNN` citations against this path "
                         "(repo-relative) -- the register's own evidence "
                         "cells cite these with the file implied by which "
                         "row's cell they sit in, never restated. Omit to "
                         "have implied citations reported CANNOT-CHECK "
                         "rather than guessed.")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    print("hover_editor_review CRITERIA_VERSION %d" % C.CRITERIA_VERSION)
    lock_ok, lock_count = run_fixture_lock(a.verbose or a.fixtures)
    if not lock_ok:
        print("REFUSED: the fixture lock failed -- criteria v%d judged "
              "nothing real (exit 2)." % C.CRITERIA_VERSION)
        return 2
    # lock_count comes from the SAME real run that just executed, including
    # the realistic-transition fixtures (F26/F27) that only exist when a
    # real sha3 is passed -- printing a SEPARATE dummy-sha3 count() call
    # here would silently undercount them, exactly the kind of drift
    # discipline 8 warns about (two instruments that should agree, quietly
    # not asked to).
    print("fixture lock: all %d fixtures classify correctly (isolated repo)"
          % lock_count)
    if a.fixtures:
        return 0

    if not a.report and not a.stdin:
        print("COULD NOT RUN: no --report/--stdin given (exit 2).")
        return 2
    if a.stdin:
        text = sys.stdin.read()
    else:
        try:
            with io.open(a.report, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            print("COULD NOT RUN: report unreadable (%s) (exit 2)." % e)
            return 2

    head, herr = run_git(a.repo, "rev-parse", "HEAD")
    if head is None:
        print("COULD NOT RUN: %s is not a usable git repo (%s). "
              "Nothing was judged (exit 2)." % (a.repo, herr))
        return 2
    dirty, _ = run_git(a.repo, "status", "--porcelain")
    print("VERDICTS ARE AGAINST THE WORKING TREE AT %s, HEAD %s%s -- "
          "as of %s, not as of the report's writing."
          % (os.path.abspath(a.repo), head[:12],
             " (DIRTY)" if dirty else "",
             datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))

    r = Review(a.repo, default_file=a.default_file)
    r.review_text(text)
    c = r.counts()

    if c["claims"] == 0:
        print("NOTHING-TO-CHECK: 0 checkable claims extracted from %d chars "
              "of report. This is NOT a pass -- the report makes no claim "
              "this tool can re-derive." % len(text))
        return 0

    order = {"FINDING": 0, "CANNOT": 1, "DRIFT": 2, "SHALLOW": 3, "OK": 4}
    for kind, cls, detail in sorted(r.rows, key=lambda t: order[t[0]]):
        if kind == "OK" and not a.verbose:
            continue
        print("[%s %s] %s" % (kind, cls, detail))

    print("-" * 70)
    print("claims extracted %d | held %d | drift-notes %d | shallow %d | "
          "cannot-check %d | FINDINGS %d"
          % (c["claims"], c["OK"], c["DRIFT"], c["SHALLOW"], c["CANNOT"],
             c["FINDING"]))
    if c["SHALLOW"]:
        print("note: %d line citations were checked for line-bounds only "
              "(no extractable anchor) -- weaker than the rest of the "
              "denominator, said rather than hidden." % c["SHALLOW"])
    if c["FINDING"]:
        print("VERDICT: DO NOT SHIP AS-IS -- %d claim(s) contradict current "
              "source." % c["FINDING"])
        return 1
    if c["CANNOT"]:
        print("VERDICT: PARTIAL -- no contradictions, but %d claim(s) could "
              "not be checked and are NOT passes (exit 3)." % c["CANNOT"])
        return 3
    print("VERDICT: all %d checkable claims hold against current source. "
          "Mechanism claims are NOT covered by this pass (see docstring)."
          % c["claims"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
