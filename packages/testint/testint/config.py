"""Where your tests, checkers and sources live -- one file, no conventions.

    from testint.config import load
    cfg = load('testint.config.json')
    for path in cfg.tests(): ...

WHY A CONFIG AND NOT A CONVENTION. The checks in this suite have to be pointed
at things: the tests that make assertions, the sources those assertions read,
and (for the determinism check) the checkers whose output must not move. Every
codebase names those differently. A tool that assumes `tests/` and `src/` works
on the repo it was written in and nowhere else -- which is the difference
between a tool and a product.

EVERY PATH IS A GLOB, and globs are resolved relative to `root`, which defaults
to the directory holding the config file. Nothing is relative to the current
working directory, deliberately: a checker whose answer depends on where you
happened to run it from is a checker that reports clean from the wrong folder,
and that is a real failure this suite's own lineage recorded four times.

── THE FIELDS ────────────────────────────────────────────────────────────────

  tests       files that make assertions. Checked BY this suite.
  sources     files those assertions read. Checked AGAINST.
  checkers    executables whose output must be identical run to run.
  probes      mutation controls, if they are separate from `tests`.
  allow       path to the deliberate-exceptions file, or null.

An absent field is an EMPTY LIST and the check that needs it reports COULD NOT
RUN rather than clean. A check with nothing to look at has not passed.
"""
import glob
import io
import json
import os


class ConfigError(Exception):
    pass


class Config(object):
    def __init__(self, data, root, here):
        self.root = root
        # WHERE THE CONFIG FILE ITSELF LIVES. The allow file is a COMPANION to
        # the config, not to the repo being checked -- you ship one testint
        # config per project and the exceptions belong beside it. Resolving it
        # against `root` instead made the shipped example unloadable, which the
        # tool correctly reported as COULD NOT RUN rather than as clean.
        self.here = here
        self._data = data
        self.allow_path = data.get('allow')

    def _expand(self, key):
        pats = self._data.get(key) or []
        if isinstance(pats, str):
            pats = [pats]
        out = []
        for p in pats:
            hits = glob.glob(os.path.join(self.root, p), recursive=True)
            out += [h for h in hits if os.path.isfile(h)]
        # Sorted so every consumer iterates in the same order. An unordered walk
        # is one of the three ways this suite's own determinism check finds a
        # checker that answers differently twice.
        return sorted(set(out))

    def tests(self):
        return self._expand('tests')

    def sources(self):
        return self._expand('sources')

    def checkers(self):
        return self._expand('checkers')

    def probes(self):
        return self._expand('probes') or self.tests()

    def rel(self, path):
        try:
            return os.path.relpath(path, self.root).replace(os.sep, '/')
        except ValueError:
            return path

    def allow(self):
        """The deliberate-exceptions table: {(file, literal): reason}.

        EVERY ENTRY CARRIES A REASON AND THE LOADER ENFORCES IT. An exclusion
        with a reason beside it is a decision; an exclusion without one is a
        silence, and a suite full of silences is the thing this package is sold
        against. An entry with an empty reason is a config ERROR, not a warning.
        """
        if not self.allow_path:
            return {}
        p = self.allow_path
        if not os.path.isabs(p):
            p = os.path.join(self.here, p)
        if not os.path.isfile(p):
            raise ConfigError('allow file not found: %s' % p)
        raw = json.load(io.open(p, encoding='utf-8'))
        out = {}
        for entry in raw.get('expected', []):
            f, lit, why = entry.get('file'), entry.get('literal'), entry.get('reason')
            if not f or lit is None:
                raise ConfigError('an allow entry needs "file" and "literal": %r' % entry)
            if not (why or '').strip():
                raise ConfigError(
                    'the allow entry for %s / %r has no "reason". An exclusion '
                    'without a reason is a silence -- say why, or remove it.'
                    % (f, lit))
            out[(f, lit)] = why
        return out


def load(path='testint.config.json'):
    if not os.path.isfile(path):
        raise ConfigError(
            'no config at %r. Copy testint.config.example.json and point it at '
            'your tests, sources and checkers.' % path)
    data = json.load(io.open(path, encoding='utf-8'))
    here = os.path.dirname(os.path.abspath(path)) or '.'
    # ── A RELATIVE `root` IS RELATIVE TO THE CONFIG FILE, NOT TO THE CWD ─────
    # The first version used a relative root as given, so `"root": ".."` meant
    # "the parent of wherever you happen to be standing". Running the same
    # config from two directories then resolved two different repos, and one of
    # them matched nothing -- which every check here would have reported as a
    # clean run over zero files. Caught by running it rather than by reading it,
    # which is the same lesson this suite sells.
    root = data.get('root') or here
    if not os.path.isabs(root):
        root = os.path.join(here, root)
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise ConfigError('root %r is not a directory' % root)
    return Config(data, root, here)
