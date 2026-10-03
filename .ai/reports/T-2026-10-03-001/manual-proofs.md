# T-2026-10-03-001 — WP1.2: manual proofs

Run on 2026-10-03, bash 5.3.9, glibc 2.43 (Ubuntu 2.43-2ubuntu2.4), Python 3.14.4 and 3.11.16.

## By-hand proofs the plan names

| Proof | Command | Result |
|---|---|---|
| pylint | `pylint --rcfile .pylintrc hooks/lib/ai_ere.py tests/test_ere_unit.py tests/test_pattern_differential.py` | 10.00/10 |
| units on 3.11 | `uv run --offline --no-project --python 3.11 bash tests/test-ere-unit.sh` (`python3` inside is 3.11.16) | `Ran 11 tests … OK` |
| differential, both locales | `bash tests/test-pattern-differential.sh` (on 3.14 and on 3.11) | 67 patterns × 339 subjects; `LC_ALL=C: 22713 identical, 0 undeclared`; `LC_ALL=C.UTF-8: 22713 identical, 0 undeclared` |
| Untouched | `git diff --quiet fea014f -- settings.common.json codex/hooks.json hooks/ai-*-defaults.json .ai/policies/path-guard.json tests/test-guard-characterization.sh tests/fixtures/guard-characterization/golden.txt tests/test-ai-{git,path,scope}-guard.sh tests/test-end-to-end.sh skills/ai-task/sensors.py` | exit 0 |

## Extra evidence (scratchpad only, nothing committed)

- **The unit expectations come from bash.** Every pattern in `test_ere_unit.py` was replayed through
  `[[ $s =~ $p ]]` under `LC_ALL=C`: 11,024 bracket-membership records (each byte 1–255 against
  `^(<bracket>)$`) and all 78 `VERDICTS` rows. Zero differences. (`\1\9` is a valid *token* stream
  and an invalid *pattern*: its rejection is the parser's, step 2, and `VERDICTS` holds it.)
- **The differential bites.** With `[[:space:]]` patched to exclude `\n`, it printed two `FAIL` lines
  (`terraform[[:space:]]+(apply|destroy)` over `terraform\napply`), with locale, pattern, subject,
  both verdicts and the seed, and exited 1. A missing locale prints one `skipped` line; without bash
  on `PATH` it prints `pattern differential: skipped, bash not on PATH` and exits 0.
- **Random fuzz.** 810,000 random pattern × subject records (patterns of 0–16 tokens over
  `ab()[]{}|*+?^$\.-,0129:=]<>` plus GNU escapes, classes, collating symbols, intervals,
  back-references, `é` and `\n`), both locales, ASCII-only under C.UTF-8. The only differences are
  the newline-anchor quirk below: 39 short and 7 long patterns, all with a `\n` in the subject.

## Finding: glibc's `^` and `$` next to a newline inside the match (decision needed before WP1.3)

**KNOWN FACT** (probe, `LC_ALL=C` and `C.UTF-8` alike). With no `REG_NEWLINE`, glibc's matcher still
treats a newline that the match itself consumes as a line boundary:

| pattern | subject | bash | ai_ere |
|---|---|---|---|
| `^a` | `x\na` | no match | no match |
| `\n^a` | `x\na` | **match** | no match |
| `.*^a` | `x\na` | **match** | no match |
| `a$` | `a\n` | no match | no match |
| `a$\n` | `a\n` | **match** | no match |
| `a$.` | `a\nb` | **match** | no match |
| `` \`a `` after `\n`, `a\'` before `\n` | | no match | no match |

So `^` also holds right after a newline the match consumed, and `$` right before a newline the match
goes on to consume. The buffer anchors `` \` `` and `\'` do not do this. INFERENCE (from
`posix/regexec.c`): the DFA picks the next state by the consumed byte, newline included, without
checking `newline_anchor`, while a context outside the match is read through
`re_string_context_at`, which does check it.

**KNOWN FACT: the hook path cannot reach it.** Every `[[ =~ ]]` in the hooks sees a subject with no
newline. `ere_match` matches a multi-line subject one line at a time
(`hooks/lib/ai-hook-common.sh:229-236`), and the two capture sites read single lines
(`hooks/ai-git-guard.sh:171-172`, `hooks/ai-path-guard.sh:352-353`).

**INFERENCE: WP1.2's corpus cannot reach it either.** Every shipped pattern has `^` only first and
`$` only last. WP1.3's mutations, construct snippets and seeded subjects (which include `\n`) will
reach it, so R5's "zero undeclared divergences" will need one of these:

- **A (recommended): declare it in D6.** The declaration is exact, not a blanket one. Write *strict*
  for ai_ere's matches, *glibc* for bash's and *loose* for the translation with `^` →
  `(?:\A|(?<=\n))` and `$` → `(?:\Z|(?=\n))`. Then strict ⊆ glibc ⊆ loose, because loosening an
  anchor only adds matches. A difference is the quirk exactly when bash matches, ai_ere does not,
  the subject has a `\n` and *loose* matches. The fuzz above classified every difference this way.
- **B: emulate it in `ai_ere`.** That needs per-anchor nullability analysis, with the pattern
  duplicated around each anchor. That breaks Python's group numbering, so captures and
  back-references would need rework. It is a sizeable change, for behaviour the hook path never
  reaches.

The plan's translation (`$` → `\Z`, `^` at the subject start only) is what this task implements.
