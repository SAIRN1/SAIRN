import sys, re

if __name__ == '__main__':
    path = sys.argv[1]
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    # Strip HTML comments before counting (fixed 2026-08-07, was CONFIRMED
    # REAL GAP, now closed). This checker previously counted <div>/</div>
    # as plain substrings anywhere in the raw file, including inside
    # <!-- --> comments -- so a bug-fix comment that DESCRIBES a past
    # widget-bleed bug in prose (e.g. "...panel-customers' own closing
    # </div>...") got counted as a real closing tag. Found live on
    # stonedesk.html: two historical fix comments (one mentioning </div>
    # 3 times, one mentioning it once) produced a phantom DIFF:-4 with
    # zero real defect behind it -- independently confirmed via a real
    # HTML-parser-based trace (same engine panel_nesting_check.py already
    # uses), which reported 0 underflow events and 0 unclosed tags on the
    # exact same file. Comment content is replaced with an equal number
    # of newlines (not simply deleted) so line numbers reported below
    # still match the real file.
    COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
    html = COMMENT_RE.sub(lambda m: '\n' * m.group(0).count('\n'), html)

    opens = len(re.findall(r'<div\b', html))
    closes = len(re.findall(r'</div>', html))
    print(f"OPEN_DIVS:{opens}")
    print(f"CLOSE_DIVS:{closes}")
    print(f"DIFF:{opens - closes}")

    # Walk the file tracking depth so an imbalance can be located, not just counted.
    depth = 0
    line = 1
    min_depth_line = None
    for m in re.finditer(r'<div\b|</div>|\n', html):
        tok = m.group(0)
        if tok == '\n':
            line += 1
            continue
        if tok.startswith('<div'):
            depth += 1
        else:
            depth -= 1
            if depth < 0 and min_depth_line is None:
                min_depth_line = line

    if opens == closes and min_depth_line is None:
        print("RESULT:PASS")
        sys.exit(0)
    else:
        print("RESULT:FAIL")
        if min_depth_line is not None:
            print(f"FIRST_UNDERFLOW_LINE:{min_depth_line} (a </div> closes before its <div> opened, going by this point)")
        sys.exit(1)
