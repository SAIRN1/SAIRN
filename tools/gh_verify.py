import sys, hashlib, urllib.request

OWNER = "SAIRN1"
REPO = "SAIRN"
BRANCH = "main"
FILE_PATH = "stonedesk.html"

def main():
    with open(FILE_PATH, "rb") as f:
        local_bytes = f.read()
    local_hash = hashlib.sha256(local_bytes).hexdigest()

    url = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{FILE_PATH}"
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req) as resp:
        remote_bytes = resp.read()
    remote_hash = hashlib.sha256(remote_bytes).hexdigest()

    print("local_size:", len(local_bytes), "local_sha256:", local_hash)
    print("remote_size:", len(remote_bytes), "remote_sha256:", remote_hash)
    print("MATCH" if local_hash == remote_hash else "MISMATCH")

if __name__ == "__main__":
    main()
