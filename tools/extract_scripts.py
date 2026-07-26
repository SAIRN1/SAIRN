import sys
from html.parser import HTMLParser

class ScriptExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.in_script = False
        self.current = []
        self.blocks = []  # list of (start_line, end_line, content)
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

    # HTMLParser calls handle_data for script content since we're not using
    # CDATA mode; but script content isn't parsed as tags by html.parser
    # by default IF we rely on its built-in script handling. Actually
    # Python's html.parser DOES treat <script> content specially (CDATA-like)
    # via set_cdata_mode internally when it sees the start tag, so handle_data
    # gets the raw content. Good.

if __name__ == '__main__':
    path = sys.argv[1]
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()
    parser = ScriptExtractor()
    parser.feed(html)
    print(f"TOTAL_SCRIPT_BLOCKS:{len(parser.blocks)}")
    for i, (s, e, content) in enumerate(parser.blocks, 1):
        print(f"BLOCK {i}: lines {s}-{e}, {len(content)} chars")
