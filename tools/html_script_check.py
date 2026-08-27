"""
PostToolUse hook for Write|Edit, and a CLI.

WHAT THIS DOES AND DOES NOT DO -- read this before citing it as evidence.
It previews the inline <script> block count of an edited .html file and runs
duplicate_global_check.py and missing_dom_target_check.py against it.
IT DOES NOT VERIFY JAVASCRIPT SYNTAX. There is no `node --check` here and
never has been. For syntax use:
    python tools/extract_scripts.py <file>      # get the block line ranges
    node --check <extracted block>
The name is misleading and is kept only because .claude/settings.json wires it
by that name; the banner below says so on every run so nobody repeats the
mistake this comment exists because of.

── THE 2026-08-27 FIX: SILENCE IS NO LONGER A REACHABLE OUTCOME ──────────
Three orphaned processes were found alive, one for ~26 hours, all of them this
script. Root cause, in two parts, both of which made a non-run look like a
clean pass:

  1. It read its input ONLY from stdin (`json.load(sys.stdin)`) and never
     looked at sys.argv -- the word did not appear in the file. Invoked from
     a terminal as `python tools/html_script_check.py foo.html`, the argument
     was ignored and the process BLOCKED FOREVER waiting for a JSON payload
     that was never coming.
  2. The whole of main() sat inside `except Exception: pass`. When stdin did
     hit EOF instead of hanging, json.load raised, the handler swallowed it,
     and the process exited 0 with no output.

So the two possible outcomes of running it wrong were "hang forever, no
output" and "exit 0, no output" -- and exit 0 with no output is exactly what a
clean pass looks like. It was cited as passing evidence in a real session
while having checked nothing at all.

Now: argv is honoured, stdin is read with a hard timeout, every exit path
prints, and every failure path exits non-zero. Hook mode still cannot block a
tool call (PostToolUse never can) but it can no longer lie by omission.
"""
import sys, re, json, os, subprocess, threading

STDIN_TIMEOUT_SECONDS = 10
SUBCHECK_TIMEOUT_SECONDS = 20

BANNER = '--- html_script_check: block preview + duplicate-global + missing-DOM. NOT a JS syntax check. ---'


def read_stdin_with_timeout(seconds):
    """Return stdin's text, or None on timeout. Threaded because Windows
    cannot select() on a pipe, so this is the portable way to bound it."""
    box = {}

    def worker():
        try:
            box['data'] = sys.stdin.read()
        except Exception as exc:  # pragma: no cover - defensive
            box['error'] = exc

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        return None
    if 'error' in box:
        raise box['error']
    return box.get('data', '')


def resolve_file_path(argv):
    """CLI mode wins. Returns (path, mode) or exits non-zero, loudly."""
    args = [a for a in argv[1:] if not a.startswith('-')]
    if args:
        return args[0], 'cli'

    raw = read_stdin_with_timeout(STDIN_TIMEOUT_SECONDS)
    if raw is None:
        print(BANNER)
        print('ERROR: no argument given and nothing arrived on stdin within '
              '%ds. This script takes a hook payload on stdin OR a file path '
              'as argv[1].' % STDIN_TIMEOUT_SECONDS, file=sys.stderr)
        print('       Run it as: python tools/html_script_check.py <file.html>', file=sys.stderr)
        sys.exit(2)
    if not raw.strip():
        print(BANNER)
        print('ERROR: empty stdin and no file argument. Nothing was checked.', file=sys.stderr)
        sys.exit(2)
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        print(BANNER)
        print('ERROR: stdin was not valid JSON (%s). Nothing was checked.' % exc, file=sys.stderr)
        sys.exit(2)
    tool_input = payload.get('tool_input', {}) or {}
    return (tool_input.get('file_path', '') or ''), 'hook'


def main():
    file_path, mode = resolve_file_path(sys.argv)

    if not file_path:
        print(BANNER)
        print('ERROR: payload carried no file_path. Nothing was checked.', file=sys.stderr)
        sys.exit(2)

    if not file_path.lower().endswith('.html'):
        # A non-HTML edit is the overwhelmingly common hook case and is a real
        # pass, not a skip -- but say so rather than exiting mute.
        print(BANNER)
        print('not an .html file, nothing to check: %s' % file_path)
        sys.exit(0)

    try:
        with open(file_path, encoding='utf-8', errors='replace') as f:
            content = f.read()
    except OSError as exc:
        print(BANNER)
        print('ERROR: could not read %s (%s)' % (file_path, exc), file=sys.stderr)
        sys.exit(2)

    print(BANNER)
    pattern = re.compile(r'<script(?![^>]*\bsrc=)[^>]*>')
    matches = [m.group(0)[:50] for m in pattern.finditer(content)]
    print('inline <script> blocks (regex preview, not an HTML parse): %d' % len(matches))

    tools_dir = os.path.dirname(os.path.abspath(__file__))
    findings = 0
    errors = 0
    for script_name, label in (
        ('duplicate_global_check.py', 'DUPLICATE GLOBAL CHECK'),
        ('missing_dom_target_check.py', 'MISSING DOM TARGET CHECK'),
    ):
        script_path = os.path.join(tools_dir, script_name)
        try:
            result = subprocess.run(
                [sys.executable, script_path, file_path],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=SUBCHECK_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            # Previously swallowed. A sub-check that times out has checked
            # NOTHING, and reporting that as quiet success is the same bug
            # this whole file was rewritten for.
            errors += 1
            print('ERROR: %s timed out after %ds -- it checked nothing.'
                  % (label, SUBCHECK_TIMEOUT_SECONDS), file=sys.stderr)
            continue
        except Exception as exc:
            errors += 1
            print('ERROR: %s could not run (%s) -- it checked nothing.' % (label, exc), file=sys.stderr)
            continue

        if result.returncode != 0:
            findings += 1
            # Capped, not the full dump: missing_dom_target_check.py carries a
            # large pre-existing backlog that would otherwise print in full on
            # every .html edit and drown out anything NEW.
            out_lines = result.stdout.splitlines()
            print('--- %s: FOUND ISSUES (showing first 3 of %d output lines) ---' % (label, len(out_lines)))
            print('\n'.join(out_lines[:3]))
            if len(out_lines) > 3:
                print('... (%d more lines -- run `python tools/%s %s` directly for the full list)'
                      % (len(out_lines) - 3, script_name, file_path))
        else:
            print('%s: clean' % label)

    if errors:
        print('RESULT: INCOMPLETE -- %d sub-check(s) did not run.' % errors, file=sys.stderr)
        sys.exit(2)
    if findings:
        print('RESULT: FINDINGS -- %d sub-check(s) reported issues.' % findings)
        sys.exit(1 if mode == 'cli' else 0)
    print('RESULT: clean (block preview + both sub-checks). Reminder: JS SYNTAX WAS NOT CHECKED.')
    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        # Never silent. A crash used to exit 0 with no output, which is
        # indistinguishable from a pass.
        print('ERROR: html_script_check crashed (%s) -- nothing was checked.' % exc, file=sys.stderr)
        sys.exit(2)
