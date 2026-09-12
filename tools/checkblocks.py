import sys, subprocess, tempfile, os
from html.parser import HTMLParser

class ScriptExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.in_script = False
        self.current = []
        self.blocks = []
        self.start_line = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'script':
            self.in_script = True
            self.current = []
            self.start_line = self.getpos()[0]

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self.in_script:
            self.in_script = False
            end_line = self.getpos()[0]
            self.blocks.append((self.start_line, end_line, ''.join(self.current)))

    def handle_data(self, data):
        if self.in_script:
            self.current.append(data)

if __name__ == '__main__':
    path = sys.argv[1]
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()
    parser = ScriptExtractor()
    parser.feed(html)
    total = len(parser.blocks)
    fails = []
    node_missing = False
    for i, (s, e, content) in enumerate(parser.blocks, 1):
        if not content.strip():
            continue
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
        tf.write(content)
        tf.close()
        try:
            try:
                r = subprocess.run(['node', '--check', tf.name],
                                   capture_output=True, text=True)
            except FileNotFoundError:
                node_missing = True
                break
            if r.returncode != 0:
                fails.append((i, s, e, r.stderr.strip()))
        finally:
            os.unlink(tf.name)
    print(f"TOTAL_BLOCKS:{total}")
    print(f"FAILED_BLOCKS:{len(fails)}")
    for i, s, e, err in fails:
        print(f"--- BLOCK {i} (lines {s}-{e}) ---")
        print(err[:500])

    # ── IT COULD NOT FAIL, AND IT IS GUARDIAN CHECK 0a (fixed 2026-09-12) ────
    # This printed FAILED_BLOCKS:1 and exited 0. Proven rather than read: a
    # planted `function zz({ {{{ ;` in sairnvet.html produced
    # "FAILED_BLOCKS:1" and exit 0.
    #
    # CLAUDE.md calls Check 0a non-negotiable and says it "hard blocks everything
    # else". It was reachable only by a human running it per file and READING the
    # number -- and any automatic wiring on exit code would have reported a clean
    # pass on a file that does not parse. A checker that cannot fail is the same
    # shape as the storage wrapper returning a boolean nobody read.
    #
    # ALSO TRUE, and the reason this went unnoticed: nothing on this platform
    # parsed app JavaScript on a push. tools/html_script_check.py is the
    # PostToolUse hook whose NAME suggests it does, and its own header says in
    # capitals that it does not -- "There is no `node --check` here and never has
    # been". So the syntax gate was a habit, not a mechanism.
    #
    # 0 = every block parses. 1 = at least one does not. 2 = could not tell,
    # which is NOT a pass: no `node` on PATH, or an unreadable file.
    if node_missing:
        print("COULD NOT RUN: `node` is not on PATH, so nothing was parsed. "
              "That is not a pass.")
        sys.exit(2)
    if total == 0:
        print("COULD NOT RUN: no <script> block was found at all. On an app file "
              "that means the extractor failed, not that the file is clean.")
        sys.exit(2)
    sys.exit(1 if fails else 0)
