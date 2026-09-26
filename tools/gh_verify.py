import os, sys, json, base64, hashlib, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_token import github_token  # noqa: E402

OWNER = "SAIRN1"
REPO = "SAIRN"
BRANCH = "main"
FILE_PATH = "stonedesk.html"

# THE SECOND COPY OF A DEAD LOOKUP. This read the same 0-byte
# C:\Users\marsh\Documents\SAIRN\.env.local as tools/gh_push.py did, so both
# tools broke together on 2026-08-08 and neither could be fixed without finding
# the other. One decision, one place: tools/gh_token.py. See that file's header.
def get_token():
    token, source = github_token()
    print("token source:", source)
    return token

def api(path, token):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def main():
    # NOTE: raw.githubusercontent.com is CDN-cached and can lag several
    # seconds after a ref update, producing false MISMATCH reports right
    # after a push. Always verify via the git blob API (authoritative,
    # uncached) using the ref's current tree, not the raw content CDN.
    token = get_token()
    ref = api(f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", token)
    commit_sha = ref["object"]["sha"]
    commit = api(f"/repos/{OWNER}/{REPO}/git/commits/{commit_sha}", token)
    tree = api(f"/repos/{OWNER}/{REPO}/git/trees/{commit['tree']['sha']}", token)
    entry = next((e for e in tree["tree"] if e["path"] == FILE_PATH), None)
    if not entry:
        print("FILE NOT FOUND IN REMOTE TREE"); sys.exit(1)

    blob = api(f"/repos/{OWNER}/{REPO}/git/blobs/{entry['sha']}", token)
    remote_bytes = base64.b64decode(blob["content"])
    remote_hash = hashlib.sha256(remote_bytes).hexdigest()

    with open(FILE_PATH, "rb") as f:
        local_bytes = f.read()
    local_hash = hashlib.sha256(local_bytes).hexdigest()

    print("remote_commit:", commit_sha)
    print("local_size:", len(local_bytes), "local_sha256:", local_hash)
    print("remote_size:", len(remote_bytes), "remote_sha256:", remote_hash)
    print("MATCH" if local_hash == remote_hash else "MISMATCH")

if __name__ == "__main__":
    main()
