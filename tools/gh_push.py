import sys, json, base64, subprocess, urllib.request, urllib.error

OWNER = "SAIRN1"
REPO = "SAIRN"
BRANCH = "main"
FILE_PATH = "stonedesk.html"
EXTRA_FILES = []  # additional repo-relative paths to include in the same commit

def get_token():
    winpath = r"C:\Users\marsh\AppData\Roaming\xdg.data\com.vercel.cli\auth.json"
    # not the right token source; token comes from .env.local GITHUB_TOKEN
    with open(r"C:\Users\marsh\Documents\SAIRN\.env.local", encoding="utf-8") as f:
        for line in f:
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("GITHUB_TOKEN not found in .env.local")

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
