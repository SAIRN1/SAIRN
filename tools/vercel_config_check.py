#!/usr/bin/env python3
"""
vercel_config_check.py -- guards against vercel.json shipping a config
Vercel's platform will silently refuse at deploy time.

Built 2026-07-30 after a real incident: adding one more `cp app.html
dist/app.html` to buildCommand pushed it from 296 chars over Vercel's
undocumented-until-you-hit-it 256-char schema limit. The deploy failed
with state ERROR, but Vercel kept serving the last successful production
build instead of erroring loudly -- so every "live-verified" check for
several commits afterward was silently checking stale content. This
script exists so that failure mode gets caught locally, before push,
instead of discovered by chance days later.

Usage: python tools/vercel_config_check.py [path/to/vercel.json]
Exits non-zero if any check fails.
"""
import fnmatch
import json
import os
import re
import sys

BUILD_COMMAND_LIMIT = 256  # Vercel's documented schema ceiling

def check(path):
    with open(path, encoding='utf-8') as f:
        cfg = json.load(f)

    failures = []

    bc = cfg.get('buildCommand', '')
    bc_len = len(bc)
    print(f'buildCommand length: {bc_len} (limit {BUILD_COMMAND_LIMIT})')
    if bc_len > BUILD_COMMAND_LIMIT:
        failures.append(
            f'buildCommand is {bc_len} chars, over the {BUILD_COMMAND_LIMIT}-char '
            f'limit by {bc_len - BUILD_COMMAND_LIMIT}. Vercel will reject this at '
            f'deploy time and silently keep serving the last successful build.'
        )

    # Every route destination should point at a file that actually reaches the
    # output directory -- a route with no file behind it is the Iron Law
    # violation in the other direction (file ships with no route is the one
    # already documented in-repo; this is route-with-no-file).
    #
    # REWRITTEN 2026-08-23. The previous version looked for each route's
    # literal filename (or bare stem) inside buildCommand. That was correct for
    # the enumerated style it was written against (`cp sairnbiz.html dist/`),
    # but buildCommand is now `mkdir -p dist && cp *.html dist/ && ...` -- a
    # glob -- so every single route failed the substring test. A Guardian pass
    # measured it: 12 routes reported as "will 404 in production", including
    # /sairnlaw, which was serving correctly at that exact moment and whose
    # bytes matched the repo copy. A push gate that is wrong 12 times per run
    # is a gate people learn to click past, which is precisely the incident
    # this script was built to prevent. This is the second time this tool has
    # false-positived on a buildCommand style it was not written against; the
    # fix this time is to stop pattern-matching the command text and instead
    # resolve what the copy sources really cover, against the real files.
    repo_root = os.path.dirname(os.path.abspath(path)) or '.'
    on_disk = {n for n in os.listdir(repo_root) if os.path.isfile(os.path.join(repo_root, n))}

    # Collect every source token handed to a `cp` in buildCommand. The last
    # token of each cp is the destination, so it is dropped.
    cp_sources = []
    for segment in re.split(r'&&|\|\||;', bc):
        toks = segment.strip().split()
        if toks and toks[0] == 'cp':
            args = [t for t in toks[1:] if not t.startswith('-')]
            if len(args) >= 2:
                cp_sources.extend(args[:-1])

    def copied_by_build(fname):
        """True when some cp source covers fname -- literally or via a glob."""
        for src in cp_sources:
            base = os.path.basename(src)
            if base == fname:
                return True
            if any(ch in base for ch in '*?[') and fnmatch.fnmatch(fname, base):
                return True
        return False

    routes = cfg.get('routes', [])
    for r in routes:
        dest = r.get('dest', '')
        if not (dest.startswith('/') and dest.endswith('.html')):
            continue
        fname = dest.lstrip('/')
        if fname == 'index.html':
            continue
        # The real failure is a route whose source file does not exist. Check
        # that first -- it is true regardless of how buildCommand is written.
        if fname not in on_disk:
            failures.append(
                f'route {r.get("src")} -> {dest} but {fname} does not exist in '
                f'{repo_root} -- this route will 404 in production.'
            )
        elif not copied_by_build(fname):
            failures.append(
                f'route {r.get("src")} -> {dest}: {fname} exists but no cp in '
                f'buildCommand copies it (literally or by glob) -- it will not '
                f'reach {cfg.get("outputDirectory", "the output directory")}.'
            )

    if failures:
        print(f'\nFAIL: {len(failures)} issue(s)')
        for f in failures:
            print(f'  - {f}')
        return False

    print('PASS: vercel.json config within known limits')
    return True


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'vercel.json'
    ok = check(path)
    sys.exit(0 if ok else 1)
