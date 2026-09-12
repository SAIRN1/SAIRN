"""Language profiles: what a comment, a string and a regex look like.

WHY THIS FILE EXISTS, AND WHY IT IS DATA RATHER THAN CODE. Every check in this
suite has to answer one question first -- *is this text CODE, or is it prose
about code?* -- and it has to answer it the same way in every language. The
alternative is one scanner per language, which is how the codebase this package
came from ended up with SEVEN comment strippers, three of which were destroying
most of their input while reporting clean:

    sairnvet.html (362 function declarations)
      careful implementation      94.6% survives    0 declarations lost
      naive regex implementation  11.1% survives  350 declarations lost

A scanner reading 11% of a file and reporting CLEAN is not a weak check, it is a
false one, and its clean result is evidence for the wrong conclusion.

So: ONE scanner (`comments.py`), driven by the table below. Adding a language is
a dictionary entry, not a new code path -- which is the only way a suite that
claims to work on "your codebase" can be honest about what it actually supports.

── FIELDS ────────────────────────────────────────────────────────────────────

  line            prefixes that start a comment running to end-of-line
  block           (open, close) pairs; the FIRST close wins, no nesting unless
                  `block_nests` says otherwise
  block_nests     True where the language really nests block comments. Rust and
                  Swift do; C does not. Getting this wrong silently eats code.
  strings         (open, close, spans_lines) triples. `open` may be multi-char
                  for triple-quoted forms; put LONGER openers first or `'''`
                  will be read as an empty `'' ` followed by a quote.
  escape          the escape character inside a string, or '' where there is
                  none (SQL doubles its quote instead -- handled below)
  doubled_quote   True where `''` inside a string means a literal quote (SQL).
  raw_prefixes    letters that may precede a quote to change escaping (Python's
                  r/b/f, C#'s @). Consumed so `r"\"` is read correctly.
  regex_literal   True only where a bare /.../ is a value (JavaScript). This is
                  the single most dangerous feature to get wrong: a `/` that
                  begins a regex containing `*/` will otherwise terminate a
                  block comment that never started.

── WHAT THIS IS NOT ──────────────────────────────────────────────────────────

It is not a parser and does not pretend to be. It knows enough to tell prose
from code, which is all any check here needs. Where a language has a
construct this table cannot express -- Perl's quote-like operators, heredocs in
several languages, JSX -- say so in `caveats` rather than approximate it, and
the suite reports that caveat in its output instead of a clean number.
"""

PROFILES = {
    'javascript': {
        'extensions': ['.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx'],
        'line': ['//'],
        'block': [('/*', '*/'), ('<!--', '-->')],
        'block_nests': False,
        'strings': [('"', '"', False), ("'", "'", False), ('`', '`', True)],
        'escape': '\\',
        'doubled_quote': False,
        'raw_prefixes': '',
        'regex_literal': True,
        'caveats': ['JSX text is treated as code, so a comment-looking string '
                    'inside markup is preserved rather than stripped.'],
    },
    'python': {
        'extensions': ['.py', '.pyi'],
        'line': ['#'],
        'block': [],
        'block_nests': False,
        # Triple quotes FIRST -- otherwise ''' reads as an empty '' then a quote.
        'strings': [('"""', '"""', True), ("'''", "'''", True),
                    ('"', '"', False), ("'", "'", False)],
        'escape': '\\',
        'doubled_quote': False,
        'raw_prefixes': 'rbfuRBFU',
        'regex_literal': False,
        'caveats': ['A module or function docstring is a STRING, not a comment, '
                    'and is preserved. Checks that want it gone must say so.'],
    },
    'c_family': {
        'extensions': ['.c', '.h', '.cpp', '.hpp', '.cc', '.java', '.cs',
                       '.go', '.swift', '.kt', '.scala', '.php'],
        'line': ['//', '#'],          # '#' for PHP; harmless elsewhere in practice
        'block': [('/*', '*/')],
        'block_nests': False,
        'strings': [('"', '"', False), ("'", "'", False), ('`', '`', True)],
        'escape': '\\',
        'doubled_quote': False,
        'raw_prefixes': '@',          # C#'s verbatim strings
        'regex_literal': False,
        'caveats': ['`#` is treated as a line comment for PHP\'s sake. In C or '
                    'Java a `#` only appears in preprocessor lines, which are '
                    'not code this suite reads -- but say so if that matters.',
                    'Heredocs (PHP <<<, Go raw strings spanning lines) are not '
                    'modelled beyond the backtick form.'],
    },
    'rust': {
        'extensions': ['.rs'],
        'line': ['//'],
        'block': [('/*', '*/')],
        'block_nests': True,          # Rust really nests; C does not
        'strings': [('"', '"', True)],
        'escape': '\\',
        'doubled_quote': False,
        'raw_prefixes': 'rb',
        'regex_literal': False,
        'caveats': ['r#"..."# raw strings with hash delimiters are not modelled; '
                    'a `"` inside one will be read as a string boundary.'],
    },
    'ruby': {
        'extensions': ['.rb'],
        'line': ['#'],
        'block': [('=begin', '=end')],
        'block_nests': False,
        'strings': [('"', '"', False), ("'", "'", False)],
        'escape': '\\',
        'doubled_quote': False,
        'raw_prefixes': '',
        'regex_literal': True,        # Ruby has /.../ too
        'caveats': ['%w[] and %q{} literal forms are not modelled.'],
    },
    'sql': {
        'extensions': ['.sql'],
        'line': ['--'],
        'block': [('/*', '*/')],
        'block_nests': True,          # standard SQL nests block comments
        'strings': [("'", "'", True), ('"', '"', True)],
        'escape': '',                 # no backslash escape by default
        'doubled_quote': True,        # '' means a literal quote
        'raw_prefixes': '',
        'regex_literal': False,
        'caveats': ['Dollar-quoted bodies ($$ ... $$) are treated as CODE, which '
                    'is what a checker reading a DO block wants.'],
    },
    'html': {
        'extensions': ['.html', '.htm', '.vue', '.svelte'],
        'line': [],
        'block': [('<!--', '-->')],
        'block_nests': False,
        'strings': [('"', '"', False), ("'", "'", False)],
        'escape': '\\',
        'doubled_quote': False,
        'raw_prefixes': '',
        'regex_literal': False,
        'caveats': ['An HTML file containing <script> blocks is usually better '
                    'read with the `javascript` profile, which also strips '
                    '<!-- --> -- see comments.profile_for().'],
    },
    'shell': {
        'extensions': ['.sh', '.bash', '.zsh'],
        'line': ['#'],
        'block': [],
        'block_nests': False,
        'strings': [('"', '"', True), ("'", "'", True)],
        'escape': '\\',
        'doubled_quote': False,
        'raw_prefixes': '',
        'regex_literal': False,
        'caveats': ['Heredocs are not modelled. A `#` inside a heredoc body will '
                    'be read as a comment.'],
    },
}

# A file's extension decides its profile. Anything unlisted is UNSUPPORTED and
# must be reported as such rather than guessed at -- guessing is how a scanner
# ends up reading 11% of a file and calling it clean.
BY_EXTENSION = {}
for _name, _p in PROFILES.items():
    for _ext in _p['extensions']:
        BY_EXTENSION.setdefault(_ext, _name)


def profile_name_for(path):
    """The profile name for a path, or None when the language is unsupported."""
    import os
    ext = os.path.splitext(path)[1].lower()
    # An .html file with inline <script> wants the javascript profile: it strips
    # <!-- --> as well, so nothing is lost, and it additionally understands the
    # `/*` inside `accept="image/*"` that eats 80% of a file otherwise.
    if ext in ('.html', '.htm'):
        return 'javascript'
    return BY_EXTENSION.get(ext)


def supported_extensions():
    return sorted(BY_EXTENSION)
