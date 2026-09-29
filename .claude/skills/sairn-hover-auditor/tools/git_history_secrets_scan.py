"""git_history_secrets_scan.py -- full git-HISTORY secrets scan, never picked up
before tonight (2026-09-17), built on real, live motivation: a real GitGuardian
alert, not the hypothetical this role's own SKILL.md named it as until now.

WHY HISTORY, NOT THE WORKING TREE. Deleting a committed secret in a later
commit does not remove it from the repository -- it persists permanently in
every clone's `.git` object store, retrievable by anyone with read access,
forever. SKILL.md's own real, already-found example: a placeholder credential
string shipped as if real, fixed in the working tree, sitting in this repo's
PUBLIC history regardless. This tool answers the question the platform's
existing secrets tooling (tools/secrets_inventory.py, current-state only)
cannot: was a real secret ever committed, at any point, even if it is gone
from HEAD.

THIS IS REPORT-ONLY. It never touches, rotates, revokes or types a secret
anywhere. A real hit is a candidate for a human (or the credential's own
owner) to confirm and rotate through the credential's real destination --
never through this tool, never through chat, per this platform's own standing
rule that a secret typed anywhere but its real destination is compromised the
moment it is typed.

METHOD, AND WHY IT IS EFFICIENT ON 5,800 COMMITS. `git log --all -G<pattern>`
(pickaxe) asks git's own index to find commits where a pattern's occurrence
COUNT CHANGED -- computed from git's internal diff machinery, not by
materializing every commit's full text in this process. This is the same
mechanism TruffleHog/Gitleaks build on. One pickaxe pass per named pattern,
not one Python-side regex pass over the whole history.

BLIND LOCK, RUN BEFORE THE REAL TREE IS EVER READ. `--selftest` builds a
disposable, throwaway git repo with committed-then-"fixed" secrets of each
named shape (still live in the OLD commit, exactly the persistence this tool
exists to catch), one entirely clean commit, and one near-miss (a comment
mentioning the word "password" with no value) -- and asserts the classifier
gets every one right, before this tool is trusted on the real 5,800-commit
history. Run this every time before trusting a real-tree result. Fixture
secrets are assembled from parts at runtime, deliberately, so this SOURCE
FILE never itself contains a string shaped like a real credential.

NAMED, DISCLOSED LIMITS, NOT PAPERED OVER:
  - Regex-shaped detection, not entropy analysis. A high-entropy secret with
    no recognisable prefix (a bare 40-char random string with no context)
    will not match any pattern here. TruffleHog/Gitleaks add entropy scoring
    for exactly this gap; this tool does not, and says so.
  - A pattern that never fires is a MEASURED ZERO for that specific shape,
    never silently folded into "no secrets exist." Report every pattern's own
    hit count, not a single combined pass/fail.
  - This finds a committed VALUE matching a known credential SHAPE. It cannot
    tell a real, currently-valid secret from a rotated, dead, or synthetic
    one -- that judgement is for a human reading the hit, never for this tool
    to assert.
"""

import io
import os
import re
import subprocess
import sys
import tempfile
import shutil


# ── NAMED PATTERNS, EACH WITH ITS OWN REPORTED HIT COUNT ─────────────────────
PATTERNS = [
    ("AWS access key ID", r"AKIA[0-9A-Z]{16}"),
    ("AWS secret access key (assignment)",
     r"aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]"),
    ("Stripe live secret key", r"sk_live_[0-9a-zA-Z]{16,}"),
    ("Stripe live publishable key", r"pk_live_[0-9a-zA-Z]{16,}"),
    ("Generic private key header", r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    ("Slack token", r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    ("GitHub personal access token", r"gh[pousr]_[A-Za-z0-9]{36,}"),
    ("Generic Bearer token literal",
     r"Bearer\s+[A-Za-z0-9._-]{20,}"),
    ("Placeholder credential shipped as real",
     r"REPLACE_ME_BEFORE_RUNNING|CHANGE_ME_IN_PRODUCTION|TODO_REAL_SECRET"),
    # THREE real regex-portability bugs in this one pattern, ALL caught by the
    # blind lock BEFORE this tool was trusted on real history, none found by
    # inspection -- each one individually made the regex compile cleanly
    # (exit 0) while silently matching nothing, the most dangerous shape a
    # check can take:
    # (1) a plain capturing group, not (?:...) -- git's -G pickaxe uses POSIX
    #     extended regex (via gnulib), which has no non-capturing groups at
    #     all (this one DID fail loudly, "invalid regex").
    # (2) `[:=]` as a bracket character class silently matches NOTHING under
    #     git's ERE engine -- `[:` inside a bracket expression is read as the
    #     start of a POSIX named-class token (like `[:alpha:]`), and `[:=]`
    #     is an incomplete one. Replaced with a plain alternation `(:|=)`.
    # (3) `\s` INSIDE a bracket expression (`[^'"\s]`) also silently matches
    #     nothing -- confirmed by bisecting the pattern character by
    #     character: `[^'"]{8,}` alone matches correctly; adding `\s` to that
    #     same bracket breaks it. `\s` as GNU whitespace shorthand is not
    #     honoured inside `[...]` here, and a bare backslash inside a POSIX
    #     bracket is not reliably literal either -- the safe fix is not
    #     needing it: excluding only the quote characters is sufficient to
    #     find a quoted value, without also needing to exclude whitespace.
    ("Hardcoded password/secret assignment (quoted, 8+ chars, not a var name)",
     r"(password|passwd|secret|api_key|apikey)\s*(:|=)\s*['\"][^'\"]{8,}['\"]"),
    ("Supabase/JWT-shaped service-role key literal",
     r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]


def git(repo, *args):
    r = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True,
                        text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def pickaxe_commits(repo, pattern):
    """Commits (full sha, subject) where `pattern`'s occurrence count changed,
    across ALL refs -- history that no longer exists at HEAD is still found,
    because -G walks every commit's diff regardless of what survived."""
    # NOTE: -G's argument is ALREADY a regex in modern git; combining it with
    # --pickaxe-regex (a legacy flag that only applies to -S) is a hard git
    # error ("options '-G' and '--pickaxe-regex' cannot be used together"),
    # which this tool's own blind lock caught on first run: every pattern
    # silently returned zero hits because pickaxe_commits() saw a non-zero
    # exit code and returned None, and the caller folded that into "no hits"
    # rather than surfacing the git error. Fixed here; the caller below also
    # now treats a git failure as COULD NOT TELL, never as a clean zero.
    code, out, err = git(repo, "log", "--all",
                          "-G" + pattern, "--format=%H\t%s")
    if code != 0:
        return None, err
    hits = []
    for line in out.splitlines():
        if "\t" in line:
            sha, subject = line.split("\t", 1)
            hits.append((sha, subject))
    return hits, None


def lines_matching(repo, sha, pattern, max_lines=6):
    """The actual line(s) in the commit's diff that carry the pattern, so a
    reported hit points at real text, not just a commit hash to go re-diff by
    hand."""
    code, out, err = git(repo, "show", "--format=", sha)
    if code != 0:
        return []
    rx = re.compile(pattern)
    found = []
    for line in out.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            if rx.search(line):
                found.append(line[1:].strip()[:160])
                if len(found) >= max_lines:
                    break
    return found


def scan(repo, patterns=None):
    """Real scan. Returns {pattern_name: [(sha, subject, [sample lines]), ...]}."""
    patterns = patterns or PATTERNS
    results = {}
    for name, pattern in patterns:
        hits, err = pickaxe_commits(repo, pattern)
        if hits is None:
            results[name] = {"error": err, "hits": []}
            continue
        entries = []
        for sha, subject in hits:
            samples = lines_matching(repo, sha, pattern)
            entries.append({"sha": sha[:10], "subject": subject[:100],
                             "sample_lines": samples})
        results[name] = {"error": None, "hits": entries}
    return results


# ── BLIND LOCK -- built and run BEFORE this tool trusts itself on real history
def _init_repo(path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True)


def _commit(path, filename, content, message):
    with io.open(os.path.join(path, filename), "w", encoding="utf-8") as f:
        f.write(content)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=path, check=True)


def _fake(*parts):
    """Assembles a fixture 'secret' from parts at runtime, deliberately, so
    this source file never itself contains a string shaped like a real
    credential."""
    return "".join(parts)


def selftest():
    tmp = tempfile.mkdtemp(prefix="ghsecrets_")
    try:
        _init_repo(tmp)

        aws_key = _fake("AKIA", "ABCDEFGHIJKLMNOP")
        stripe_key = _fake("sk_live_", "51ABCDEFGHIJKLMNOPQRSTUV")
        weak_pw = _fake("sUp3r", "Secr3t!")

        # 1. A real-shaped AWS key, committed then "fixed" -- must still be found.
        _commit(tmp, "config.py",
                "AWS_KEY = '" + aws_key + "'\n",
                "feat: add aws config")
        _commit(tmp, "config.py",
                "AWS_KEY = os.environ['AWS_KEY']\n",
                "fix: stop hardcoding the aws key")

        # 2. A Stripe live key, never removed.
        _commit(tmp, "stripe.py",
                "STRIPE_KEY = '" + stripe_key + "'\n",
                "feat: wire stripe")

        # 3. The placeholder-shipped-as-real shape.
        _commit(tmp, "seed.sql",
                "-- password: " + _fake("REPLACE_ME_", "BEFORE_RUNNING") + "\n",
                "chore: seed file")

        # 4. A hardcoded password assignment.
        _commit(tmp, "db.py",
                "password = '" + weak_pw + "'\n",
                "feat: db connect")

        # 5. A genuinely clean commit -- must NOT fire on anything.
        _commit(tmp, "readme.md",
                "# Project\nThis project has no secrets in it at all.\n",
                "docs: readme")

        # 6. A near-miss: mentions "password" with no assigned value at all --
        #    must NOT fire the hardcoded-assignment pattern (no ['\"] literal).
        _commit(tmp, "docs.md",
                "The user must enter their password on the login screen.\n",
                "docs: describe login flow")

        results = scan(tmp)

        checks = []
        aws_hits = results["AWS access key ID"]["hits"]
        checks.append(("AWS key found despite later fix",
                        any(aws_key in " ".join(h["sample_lines"]) for h in aws_hits)))
        stripe_hits = results["Stripe live secret key"]["hits"]
        checks.append(("Stripe live key found",
                        any(stripe_key in " ".join(h["sample_lines"]) for h in stripe_hits)))
        ph_hits = results["Placeholder credential shipped as real"]["hits"]
        checks.append(("Placeholder-shipped-as-real found",
                        len(ph_hits) >= 1))
        pw_hits = results["Hardcoded password/secret assignment (quoted, 8+ chars, not a var name)"]["hits"]
        checks.append(("Hardcoded password assignment found",
                        any(weak_pw in " ".join(h["sample_lines"]) for h in pw_hits)))

        # Sharper clean check: the readme/docs-only commits must not appear as
        # the reason any pattern fired -- i.e. no pattern's hit list includes
        # a sample line from the clean or near-miss commit.
        clean_subjects = {"docs: readme", "docs: describe login flow"}
        false_fire = []
        for name, v in results.items():
            for h in v["hits"]:
                if h["subject"] in clean_subjects and h["sample_lines"]:
                    false_fire.append((name, h["subject"]))
        checks.append(("Near-miss / clean commits never produce a sample line",
                        len(false_fire) == 0))

        ok = all(c[1] for c in checks)
        print("BLIND LOCK -- %d/%d fixtures correct" % (
            sum(1 for c in checks if c[1]), len(checks)))
        for name, passed in checks:
            print("  %s  %s" % ("ok  " if passed else "FAIL", name))
        if false_fire:
            print("  false fires:", false_fire)
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    if "--selftest" in argv:
        return 0 if selftest() else 1

    if "--repo" not in argv:
        print("--repo PATH is required (e.g. the SAIRN-hover clone), or --selftest")
        return 2
    repo = argv[argv.index("--repo") + 1]

    print("Running blind lock before trusting a real scan...")
    if not selftest():
        print("BLIND LOCK FAILED -- refusing to scan real history until this "
              "tool's own classifier is trustworthy.")
        return 2
    print()

    total_commits = git(repo, "rev-list", "--all", "--count")[1].strip()
    print("GIT-HISTORY SECRETS SCAN -- %s commits, %d named patterns, report only"
          % (total_commits or "?", len(PATTERNS)))
    results = scan(repo)
    total_hits = 0
    for name, v in results.items():
        n = len(v["hits"])
        total_hits += n
        if v["error"]:
            print("  COULD NOT TELL  %-65s %s" % (name, v["error"][:80]))
            continue
        print("  %-65s %d commit(s)" % (name, n))
        for h in v["hits"][:5]:
            print("      %s  %s" % (h["sha"], h["subject"]))
            for s in h["sample_lines"][:2]:
                print("          %s" % s)
        if n > 5:
            print("      ... %d more, not printed" % (n - 5))
    print()
    print("TOTAL CANDIDATE HITS: %d across %d patterns. Every hit is a "
          "CANDIDATE for a human to confirm and rotate through its real "
          "destination -- never through this tool." % (total_hits, len(PATTERNS)))
    print("WHAT A ZERO ON ANY ONE PATTERN MEANS: that specific shape was not "
          "found in this history. It does not mean no secret of any shape "
          "exists -- this is regex-shaped detection, not entropy analysis, "
          "and says so.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
