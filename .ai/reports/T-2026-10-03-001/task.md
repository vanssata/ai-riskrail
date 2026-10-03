# T-2026-10-03-001 — WP1.2: ERE translator and the differential's runner

Refactoring, T3, solo direct mode. Plan: `docs/sdlc/plans/os-independent-installer-packaging-wp1-guards-in-python.md` (WP1.2, steps 1, 1.2, 2 and 3), plus remediation R1.

## Release summary

**What changed**
- `hooks/lib/ai_ere.py` (new): a POSIX ERE parser that works the way glibc's regcomp does on UTF-8 bytes in the C locale. It translates a pattern to Python `re` over bytes (GNU escapes, back-references, intervals, the anchors without REG_NEWLINE) and has a cache per process. Invalid patterns give `None`, which never matches.
- `tests/test_ere_unit.py` and `tests/test-ere-unit.sh` (new): the parser and translator units, and 85 VERDICTS rows, each equal to bash under LC_ALL=C.
- `tests/test_pattern_differential.py` and `tests/test-pattern-differential.sh` (new): the oracle is one long-lived bash per locale (C, C.UTF-8), compared with ai_ere over both defaults files and the characterization corpus.
- `tests/run-all.sh`: one entry for each of the two new suites.
- R1 (review findings 2–4):
  - A `*`, `+` or `?` under another repeat is folded into one quantifier.
  - A `RecursionError` result is no longer cached.
  - The DECLARED multi-character `[[.x.]]` entry is dropped.

**Deliberately preserved:** no shell guard calls ai_ere yet. Production behaviour (the shell guards and `ai-hook-common.sh`) is untouched.

**Verification**
- `bash tests/run-all.sh`, run 2: exit 0 in 258 s. The units ran 12 tests OK. The differential found 22,713 identical in each locale and 0 undeclared.
- `bash tests/test-end-to-end.sh`, run 2: exit 0.
- pylint is green.
- The bite sensor is red only because `ai_ere` is new (ModuleNotFoundError at the base).

**Probes:**
- Old and merged ai_ere give the same verdict on 132,810 stacked-quantifier records.
- Fuzzing 240,000 records against bash found 0 differences besides the newline-anchor quirk.

**Review**
- Adversarial review on STRONG: passed.
- Scoped re-review after R1: passed, with no BLOCKER and no HIGH. See `review-report.md`.

**Rollback:** the change is not committed. `git checkout tests/run-all.sh` and removing the five new files undoes it; after a commit, one `git revert`.

**Open risks** (in the state and `review-report.md`):
- Finding 1: glibc's back-reference quirk. A WP1.3 decision.
- Finding 2, narrowed: an interval under a repeat still backtracks exponentially. Left to D5's timeout in WP1.3.
- Finding 3, residual: the recursion depth limit.
- Tooling: `remediate` sets no `tree_before`, so R1 closed with `--force`. Both tooling problems are recorded in `.ai/project/known-risks.md`.
