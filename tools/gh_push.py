import os, sys, json, base64, urllib.request, urllib.error

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

def main():
    commit_message = sys.argv[1]
    extra = sys.argv[2:] if len(sys.argv) > 2 else EXTRA_FILES
    token = get_token()

    files = [FILE_PATH] + list(extra)
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

    ref = api("GET", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", token)
    latest_commit_sha = ref["object"]["sha"]
    print("latest_commit_sha:", latest_commit_sha)

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
