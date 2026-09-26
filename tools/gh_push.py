import os, sys, json, base64, shutil, subprocess, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_token import github_token  # noqa: E402

OWNER = "SAIRN1"
REPO = "SAIRN"
BRANCH = "main"
FILE_PATH = "stonedesk.html"
EXTRA_FILES = []  # additional repo-relative paths to include in the same commit

# ── THE TOKEN LOOKUP LIVED HERE AND WAS DEAD FOR SEVEN WEEKS ─────────────────
# This function read GITHUB_TOKEN out of C:\Users\marsh\Documents\SAIRN\.env.local
# and that file has been 0 bytes since 2026-08-08, so every invocation since has
# raised `GITHUB_TOKEN not found in .env.local` -- a message that sent readers to
# the one place that could not have had it. tools/gh_verify.py carried a
# byte-identical copy of the same dead lookup, which is why fixing one would
# never have fixed the other. The decision now lives in tools/gh_token.py, once:
# env var, then the git credential manager (what actually holds a working token
# on this machine), then .env.local last so a file somebody re-populates still
# works without shadowing a live credential.
#
# `github_token()` returns (token, source_label) and raises TokenUnavailable
# NAMING EVERY SOURCE TRIED. It never prints the token, not even a prefix.
def get_token():
    token, source = github_token()
    print("token source:", source)
    return token

def api(method, path, token, body=None):
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("HTTP ERROR", e.code, e.read().decode())
        raise

def git(repo, *args):
    r = subprocess.run(['git', '-C', repo] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=120)
    return r.returncode, (r.stdout or ''), (r.stderr or '')


def deny(*lines):
    """Refuse the push. FAILS CLOSED, unlike .githooks/pre-push.

    THE DIVERGENCE FROM THE HOOK'S STANDARD IS DELIBERATE AND IS THE WHOLE
    REASON THIS PATH EXISTS. The shell hook fails OPEN on an internal error,
    and its header states why: "a gate that crashes closed gets disabled, and
    then protects nothing." That reasoning is about the path used for every
    push, hundreds of times a day. This path is the BYPASS, reached by hand,
    rarely -- so a could-not-tell here costs one retry and never tempts anyone
    to rip the gate out. PR 1.11: could-not-run is a third state and is never
    folded into passed.
    """
    sys.stderr.write('\n')
    for l in lines:
        sys.stderr.write(l + '\n')
    sys.stderr.write('\n(refused by tools/gh_push.py before any GitHub write)\n')
    sys.exit(1)


def run_the_real_gate(repo, files, branch, remote_sha):
    """Run .githooks/pre-push on this REST push, with synthesized ref lines.

    ── WHY THIS IS A CALL AND NOT A COPY OF THE CHECKS ──────────────────────
    A REST push does not run a git hook -- git is never invoked, so nothing
    fires. That was read as "the checks therefore have to be duplicated into
    this script", and duplicating them would have been the defect: fourteen
    checks in two places, going stale in one of them, which is item 94 on the
    largest gate on the platform. The hook is also where the ENUMERATION lives
    (hover scope gate, register feed gate, push gate) -- three today, and a
    fourth added to the hook would silently not apply to this path if this file
    listed them itself.

    So the hook is INVOKED. `git` does not fire it automatically; nothing stops
    this script from firing it deliberately, with exactly the stdin git would
    have supplied:

        <local ref> <local sha> <remote ref> <remote sha>

    ── THE PRE-FLIGHT IS NOT PART OF THE GATE AND IS NEW ────────────────────
    The gate reasons about COMMITS. This script sends WORKING-TREE BYTES, and
    that gap is a second hole, not a wrinkle: before this change gh_push.py
    could publish content that existed in NO local commit, on any branch, seen
    by nothing -- and the gate could not have judged it even if it had run,
    because there was no commit to judge. So the files must be committed and
    clean at HEAD first, and HEAD must descend from what the remote holds.
    Then `remote_sha..HEAD` is a real range, and every check runs on real
    objects rather than on a fabricated view of them.

    ── WHY GATING ON `remote..HEAD` IS SOUND WHEN THE REST PUSH SENDS LESS ──
    The range and the push are not the same change set, and the direction of the
    difference is what makes this safe rather than a coincidence.

    The REST commit's tree is the remote's tree with `files` overwritten by their
    working-tree bytes. Every one of those files is required above to be
    committed and CLEAN at HEAD, so those bytes ARE HEAD's bytes -- and HEAD
    descends from the remote. So what the REST push publishes is a SUBSET of what
    `remote..HEAD` changed, restricted to `files`.

    Gating on the superset therefore OVER-blocks and cannot UNDER-block: the
    gate may refuse over a file this push is not sending, and it can never pass
    a file this push IS sending without having looked at it. Over-blocking on a
    hand-run bypass costs a retry. Under-blocking is the defect being fixed.
    """
    sh = shutil.which('sh') or shutil.which('bash')
    hook = os.path.join(repo, '.githooks', 'pre-push')
    if not os.path.isfile(hook):
        deny('COULD NOT RUN THE PUSH GATE: .githooks/pre-push is not present at',
             '  ' + hook,
             'The gate did NOT run and nothing was verified. That is a third',
             'state, not a pass (PR 1.11).')
    if not sh:
        deny('COULD NOT RUN THE PUSH GATE: no `sh` or `bash` on PATH, so',
             '.githooks/pre-push cannot be executed from here.',
             'The gate did NOT run and nothing was verified -- refusing rather',
             'than pushing ungated (PR 1.11).')

    # ── EVERY FILE COMMITTED AND CLEAN, NAMED INDIVIDUALLY ──────────────────
    for path in files:
        rc, _o, _e = git(repo, 'ls-files', '--error-unmatch', '--', path)
        if rc != 0:
            deny('NOT TRACKED: ' + path,
                 'This script would have sent its working-tree bytes to origin as a',
                 'commit, and no local commit would ever have contained them. Commit',
                 'it first -- then the gate has something real to judge.')
        rc, out, _e = git(repo, 'status', '--porcelain', '--', path)
        if rc != 0 or out.strip():
            deny('UNCOMMITTED CHANGES: ' + path + '  (' + out.strip() + ')',
                 'A REST push sends the WORKING TREE. Pushing now would publish bytes',
                 'that exist in no commit here, so nothing -- not this gate, not a',
                 'reviewer, not a future bisect -- could ever see what was shipped.',
                 'Commit it, then push.')

    rc, head, _e = git(repo, 'rev-parse', 'HEAD')
    head = head.strip()
    if rc != 0 or not head:
        deny('COULD NOT RESOLVE HEAD in ' + repo + ' -- the gate cannot be given a',
             'range, so nothing can be checked.')

    # ── THE REMOTE SHA MUST BE AN ANCESTOR, AND IT MUST BE HERE TO TELL ─────
    # If this clone does not hold the remote's tip, `remote..HEAD` is not a
    # range this repo can compute and the gate would judge the wrong set. An
    # unfetched remote is could-not-tell, which refuses.
    rc, _o, _e = git(repo, 'cat-file', '-e', remote_sha + '^{commit}')
    if rc != 0:
        deny('THE REMOTE TIP ' + remote_sha[:12] + ' IS NOT IN THIS CLONE.',
             'Run `git fetch origin` first. Without it the gate would be handed a',
             'range this repo cannot compute, and a gate given the wrong range',
             'reports a pass it never performed.')
    rc, _o, _e = git(repo, 'merge-base', '--is-ancestor', remote_sha, head)
    if rc != 0:
        deny('HEAD DOES NOT DESCEND FROM THE REMOTE TIP ' + remote_sha[:12] + '.',
             'origin has commits this clone does not. The GitHub API would refuse',
             'the non-fast-forward anyway (force:false) -- refused here first, with',
             'the reason, rather than as an opaque 422. Rebase, then push.')

    refline = 'refs/heads/%s %s refs/heads/%s %s\n' % (branch, head, branch, remote_sha)
    print('gate: running .githooks/pre-push on %s..%s' % (remote_sha[:8], head[:8]))
    r = subprocess.run([sh, hook, 'origin', 'https://github.com/%s/%s.git' % (OWNER, REPO)],
                       input=refline, cwd=repo, text=True, encoding='utf-8',
                       errors='replace', timeout=1800)
    if r.returncode != 0:
        # The hook already wrote its own refusal to stderr, in the same words a
        # `git push` would have shown. Nothing is restated here: two wordings of
        # one refusal is how the override hint ended up wrong in eight places.
        sys.stderr.write('\nThe push gate REFUSED this REST push (exit %d). '
                         'Nothing was sent.\n' % r.returncode)
        sys.exit(r.returncode)
    print('gate: passed')
    return head


def main():
    commit_message = sys.argv[1]
    extra = sys.argv[2:] if len(sys.argv) > 2 else EXTRA_FILES
    token = get_token()

    files = [FILE_PATH] + list(extra)

    # ── THE GATE RUNS BEFORE ANY GITHUB WRITE, INCLUDING THE BLOBS ──────────
    # The ref GET used to sit AFTER the blob uploads. It is first now, because
    # the gate needs the remote tip to build its range and a refusal should
    # leave nothing at all behind -- an uploaded blob is only a dangling object,
    # but "nothing was sent" is a claim worth being literally true.
    rc, repo, _e = git(os.getcwd(), 'rev-parse', '--show-toplevel')
    repo = repo.strip()
    if rc != 0 or not repo:
        deny('NOT INSIDE A GIT REPOSITORY, so the push gate cannot be run and',
             'nothing can be verified about what this would publish.')

    ref = api("GET", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", token)
    latest_commit_sha = ref["object"]["sha"]
    print("latest_commit_sha:", latest_commit_sha)

    run_the_real_gate(repo, files, BRANCH, latest_commit_sha)

    tree_entries = []
    for path in files:
        with open(path, "rb") as f:
            content_bytes = f.read()
        content_b64 = base64.b64encode(content_bytes).decode()
        blob = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs", token, {
            "content": content_b64, "encoding": "base64"
        })
        print(path, "blob_sha:", blob["sha"])
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})

    commit = api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{latest_commit_sha}", token)
    base_tree_sha = commit["tree"]["sha"]

    tree = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", token, {
        "base_tree": base_tree_sha,
        "tree": tree_entries
    })
    tree_sha = tree["sha"]
    print("tree_sha:", tree_sha)

    new_commit = api("POST", f"/repos/{OWNER}/{REPO}/git/commits", token, {
        "message": commit_message,
        "tree": tree_sha,
        "parents": [latest_commit_sha]
    })
    new_commit_sha = new_commit["sha"]
    print("new_commit_sha:", new_commit_sha)

    api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", token, {
        "sha": new_commit_sha, "force": False
    })
    print("PUSHED:", new_commit_sha)

if __name__ == "__main__":
    main()
