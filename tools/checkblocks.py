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
    for i, (s, e, content) in enumerate(parser.blocks, 1):
        if not content.strip():
            continue
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
        tf.write(content)
        tf.close()
        try:
            r = subprocess.run(['node', '--check', tf.name], capture_output=True, text=True)
            if r.returncode != 0:
                fails.append((i, s, e, r.stderr.strip()))
        finally:
            os.unlink(tf.name)
    print(f"TOTAL_BLOCKS:{total}")
    print(f"FAILED_BLOCKS:{len(fails)}")
    for i, s, e, err in fails:
        print(f"--- BLOCK {i} (lines {s}-{e}) ---")
        print(err[:500])
