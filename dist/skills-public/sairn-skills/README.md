# SAIRN Skills

A small, free Claude Code plugin marketplace from
[SAIRN Technologies LLC](https://sairn.com). One skill so far.

```
/plugin marketplace add <owner>/<repo>
/plugin install postgres-grant-sweep@sairn-skills
```

## postgres-grant-sweep

Changing what a database role is *allowed* to do, across many tables at once,
has an unusual risk shape: the change is invisible until something that used to
work stops working, and the verification is very easy to write in a way that
passes without proving anything. **The default outcome of a careless sweep is a
green check over a broken database.**

This skill is the procedure that prevents that — catalog-driven discovery
instead of hand-built table lists, revoke-then-grant that preserves exactly what
each table held, a baseline in a real table rather than a temp one, and a
verification that checks for privileges *lost* as well as the target removed.
Plus a six-item hardening checklist, counting discipline for audits that
generate numbers, and an explicit list of what a sweep does not cover.

### How far this has been proven

Extracted from **three real sweeps against one production Postgres database on
Supabase**, run by **one operator**, over roughly three weeks in 2026. Every
rule in it closed a failure that actually happened. None has been validated on
another database, another provider, or by anyone else.

That is stated in the skill itself as well as here, because "battle-tested" is
true and much narrower than it usually sounds. The reasoning generalises; the
specifics may not.

### It does not execute anything

`REVOKE` requires the object owner, which a pooled application role does not
have. A sweep is always a hand-off to a human with owner-level SQL access, and
the mutating section ships commented out. Nothing here asks an agent to change
your database.

## Licence

MIT. See [LICENSE](LICENSE).

## Contributing

Corrections from a database that is not the one this came from are the most
useful thing anyone could send. Open an issue with what your database did
differently.
