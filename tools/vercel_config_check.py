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
import json
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

    # Every route destination should point at a file the buildCommand actually
    # produces -- a route with no matching cp is the Iron Law violation in the
    # other direction (file ships with no route is the one already documented
    # in-repo; this is route-with-no-file).
    routes = cfg.get('routes', [])
    for r in routes:
        dest = r.get('dest', '')
        if dest.startswith('/') and dest.endswith('.html'):
            fname = dest.lstrip('/')
            stem = fname[:-len('.html')]
            # buildCommand may spell this out (`cp sairnbiz.html ...`) or, since
            # the 2026-07-30 fix, name it bare inside a shell loop
            # (`for f in ... sairnbiz ...`) -- check both forms so this doesn't
            # false-positive on a style it wasn't written against, the exact
            # mistake sairn-portfolio-triage's scanners already made once.
            if fname != 'index.html' and fname not in bc and stem not in bc:
                failures.append(
                    f'route {r.get("src")} -> {dest} but buildCommand has no '
                    f'reference to {fname} or {stem} -- this route will 404 in production.'
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
