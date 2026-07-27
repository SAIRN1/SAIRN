import sys, re

if __name__ == '__main__':
    path = sys.argv[1]
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

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
