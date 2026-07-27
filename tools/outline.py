"""
Structure/outline extraction for stonedesk.html, in place of a full re-read.

Verified this session: re-reading the whole 2.0MB file costs ~575,800
tokens (tiktoken cl100k_base). A ctags-based function outline of the same
file costs ~39,600 tokens -- a 93% reduction -- while still giving every
function name and its real line number in stonedesk.html.

Why not just point ctags at the .html file directly: universal-ctags'
HTML parser treats <script> as a reference-only tag and does not descend
into its contents (confirmed empirically -- 1,342 tags, all DOM ids/
headings, zero functions). So this script extracts each <script> block
first (reusing extract_scripts.ScriptExtractor, which already tracks each
block's real start line), runs ctags on the concatenated JS, and then
remaps every tag's line number back to its true line in the original
HTML file using each block's offset.

Requires `ctags` (Universal Ctags) on PATH. Get it from
https://github.com/universal-ctags/ctags-win32/releases (Windows) or your
package manager (brew install universal-ctags / apt install universal-ctags).
"""
import sys, os, subprocess, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_scripts import ScriptExtractor

FUNCTION_KINDS = {'f', 'C', 'c', 'M'}  # function, constant, class, method


def find_ctags():
    from shutil import which
    exe = which('ctags') or which('ctags.exe')
    if not exe:
        sys.exit(
            "ERROR: ctags not found on PATH.\n"
            "Install Universal Ctags: https://github.com/universal-ctags/ctags-win32/releases\n"
            "(Windows) or `brew install universal-ctags` / `apt install universal-ctags`."
        )
    return exe


def extract_blocks(html_path):
    with open(html_path, encoding='utf-8', errors='replace') as f:
        html = f.read()
    parser = ScriptExtractor()
    parser.feed(html)
    return parser.blocks  # list of (start_line, end_line, content)


def build_combined_js(blocks):
    """Concatenate all script blocks, tracking the line offset of each so
    ctags' line numbers (relative to the combined blob) can be mapped back
    to real lines in the original HTML file."""
    combined_lines = []
    # offsets[i] = (combined_start_line, html_start_line) for block i
    offsets = []
    for start_line, end_line, content in blocks:
        combined_start = len(combined_lines) + 1
        offsets.append((combined_start, start_line))
        combined_lines.extend(content.split('\n'))
        combined_lines.append('')  # blank-line separator between blocks
    return '\n'.join(combined_lines), offsets


def map_line(combined_line, offsets):
    """Map a line number in the combined JS blob back to its real line in
    the original HTML file, using the block offset table (offsets sorted
    by combined_start ascending, as built)."""
    html_line = offsets[0][1]
    for combined_start, html_start in offsets:
        if combined_line >= combined_start:
            html_line = html_start + (combined_line - combined_start)
        else:
            break
    return html_line


def run_ctags(ctags_exe, js_path):
    tags_path = js_path + '.tags'
    subprocess.run(
        [ctags_exe, '--languages=JavaScript', '-f', tags_path, '--fields=+n', js_path],
        check=True,
    )
    with open(tags_path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    os.remove(tags_path)
    return lines


def parse_tags(lines):
    entries = []
    for line in lines:
        if line.startswith('!'):
            continue
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 4:
            continue
        name = parts[0]
        kind = parts[3]
        if kind not in FUNCTION_KINDS:
            continue
        line_field = next((p for p in parts[4:] if p.startswith('line:')), None)
        if not line_field:
            continue
        combined_line = int(line_field.split(':', 1)[1])
        entries.append((name, kind, combined_line))
    return entries


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python tools/outline.py <path-to-html-file>")
    html_path = sys.argv[1]

    ctags_exe = find_ctags()
    blocks = extract_blocks(html_path)
    if not blocks:
        sys.exit(f"No <script> blocks found in {html_path}")

    combined_js, offsets = build_combined_js(blocks)

    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tf:
        tf.write(combined_js)
        js_path = tf.name

    try:
        tag_lines = run_ctags(ctags_exe, js_path)
    finally:
        os.remove(js_path)

    entries = parse_tags(tag_lines)

    results = sorted(
        {(name, map_line(combined_line, offsets)) for name, kind, combined_line in entries},
        key=lambda e: e[1],
    )

    for name, html_line in results:
        print(f"{html_line}: {name}()")

    print(f"\nTOTAL_SYMBOLS:{len(results)}", file=sys.stderr)
    print(f"SCRIPT_BLOCKS:{len(blocks)}", file=sys.stderr)


if __name__ == '__main__':
    main()
