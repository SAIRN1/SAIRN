"""testint -- test-suite integrity checks.

The question this suite asks is not *does the code work*. It is **does the
thing that tells you the code works actually check anything?**

Three failure shapes, each of which produces a green bar over a real defect:

  * an assertion that matches a COMMENT describing the code rather than the code
  * a mutation control whose anchor no longer matches, so it mutates nothing
  * a checker that answers differently on identical input, so its clean run is
    one sample rather than a fact

See README.md.
"""
__version__ = '0.1.0'
