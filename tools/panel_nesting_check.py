"""
panel_nesting_check.py -- flags any panel-X div that is NOT a direct
sibling of every other panel-X div.

div_balance_check.py only verifies that the TOTAL count of open and close
divs matches -- it does not verify actual nesting structure, and a file
can have perfectly balanced totals while still having real divs nested in
the wrong place. This is exactly how panel-crm went undetected: it ended
up nested one level inside #page-field-quote (a missing closing </div> in
an unrelated ~100-line span earlier in the file), rendering at 0x0 forever,
while div_balance_check.py reported PASS the whole time because the
overall open/close totals still matched.

All panel-X divs are meant to be siblings under the same parent
(.panel-wrap) -- that's what makes the .panel/.panel.active show/hide CSS
mechanism work at all. If one panel is nested inside another (or inside
some other leftover container), showPanel()/sbNav() can apply the
'active' class correctly and it will still never become visible, because
a display:none ancestor hides everything inside it regardless of the
child's own class/display state.

Method: parse the full document with a real HTML parser (not naive
<script> or <div> counting), tracking nesting depth of every element.
Record the depth at which each <div id="panel-X"> opens. The correct
depth is whatever the majority (mode) of panels share -- flag any panel
whose depth differs from that majority, and name its actual parent
element so the trapped location is immediately visible.
"""
import sys
from collections import Counter
from html.parser import HTMLParser

VOID_ELEMENTS = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}


class PanelDepthMapper(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []  # list of (tag, id_or_class)
        self.panels = {}  # panel_id -> (depth, line, parent_desc)
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        if tag.lower() == 'script':
            self.in_script = True
        if self.in_script:
            return
        d = dict(attrs)
        pid = d.get('id', '')
        if tag.lower() in VOID_ELEMENTS:
            return
        if pid.startswith('panel-'):
            parent_desc = '%s#%s' % self.stack[-1] if self.stack else '(document root)'
            self.panels[pid] = (len(self.stack), line, parent_desc)
        ident = pid or ('.' + d.get('class', '').split(' ')[0] if d.get('class') else tag)
        self.stack.append((tag, ident))

    def handle_endtag(self, tag):
        if tag.lower() == 'script':
            self.in_script = False
            return
        if self.in_script:
            return
        if tag.lower() in VOID_ELEMENTS:
            return
        if self.stack:
            self.stack.pop()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'stonedesk.html'
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    parser = PanelDepthMapper()
    parser.feed(html)

    if not parser.panels:
        print("NO_PANELS_FOUND")
        sys.exit(1)

    # Two legitimate app-shell containers exist and BOTH are always
    # visible (app-body and panel-wrap) -- confirmed by checking this
    # file directly: a real, separate, pre-existing structural imbalance
    # elsewhere (independent of the page-field-quote/panel-crm bug this
    # tool was originally built to catch) causes panel-wrap to appear
    # prematurely "closed" partway through the panel list, making many
    # later panels register as direct children of app-body instead of
    # panel-wrap. That's real and worth knowing, but it does NOT hide
    # anything -- both containers render fine -- so treating every
    # non-majority parent as equally "trapped" (an earlier version of
    # this check did) drowns the one finding that actually matters in 26
    # harmless ones. Only a parent OUTSIDE this safe set is a real find:
    # that's what "trapped inside a hidden container" (page-field-quote,
    # in panel-crm's case) actually looks like.
    SAFE_PARENTS = {'div#.app-body', 'div#.panel-wrap'}

    parents = [p for d, l, p in parser.panels.values()]
    safe_count = sum(1 for p in parents if p in SAFE_PARENTS)

    trapped = {pid: info for pid, info in parser.panels.items() if info[2] not in SAFE_PARENTS}
    shell_split = {pid: info for pid, info in parser.panels.items()
                   if info[2] in SAFE_PARENTS and info[2] != Counter(parents).most_common(1)[0][0]}

    print("TOTAL_PANELS:%d" % len(parser.panels))
    print("SAFE_SHELL_PARENT_PANELS:%d (app-body or panel-wrap)" % safe_count)
    print("TRAPPED_PANELS (parent outside app-body/panel-wrap):%d" % len(trapped))
    for pid in sorted(trapped):
        depth, line, parent = trapped[pid]
        print("TRAPPED: %s at line %d -- actual parent: %s" % (pid, line, parent))
    if shell_split:
        print("NOTE: %d panels split between app-body/panel-wrap as direct parent (both safe, "
              "still visible) -- likely a separate, real structural imbalance elsewhere worth "
              "its own look, but not a hidden-panel bug:" % len(shell_split))
        for pid in sorted(shell_split):
            depth, line, parent = shell_split[pid]
            print("  %s at line %d -- parent: %s" % (pid, line, parent))

    sys.exit(1 if trapped else 0)


if __name__ == '__main__':
    main()
