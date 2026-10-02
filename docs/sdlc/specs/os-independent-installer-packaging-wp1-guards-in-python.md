# Spec: WP1 — Shared OS module and the guards in Python (refactoring)

Intent: `docs/sdlc/intent/os-independent-installer-packaging.md` (work-package table, row 1)

<!-- Stage 2. Requirements and design derived from the intent, checked against project conventions. -->

A **refactoring** (C3). The three PreToolUse guards and `hooks/lib/ai-hook-common.sh` are ported to
Python, together with the first piece of the one shared OS module (O3). Nothing a guard decides
changes, and the proof is the unchanged golden file plus two differential runs over generated input
(OQ7). The package depends on nothing. Later packages build on it: WP2 (the installer imports
`ai_os`), WP4a (switches the registered command lines, runs the install self-test, proves the
runtime calls the guards), WP4b (Windows paths, interpreter name, UTF-8 for files) and WP3b (retires
the frozen shell copies). The tier is estimated at T3, with a security review whatever the tier.

The design comes from the `architect` agent (STRONG tier) and was checked in the session. One
mechanism was corrected after a run: the slow-pattern budget (D5). `file:line` marks a fact read
from the code; *inferred* marks a conclusion.

## Requirements

| # | Requirement | Serves |
|---|---|---|
| R1 | The Python guards reproduce every record of `tests/fixtures/guard-characterization/golden.txt` (1047 runs, 307 denies, all `rc=0`, no stderr) byte for byte: rc, stdout and stderr. They are reached through the `.sh` shims. `tests/test-guard-characterization.sh` and the golden file are untouched (`git diff --quiet` on both). | constraint "guards proven against the golden file"; C3; `docs/hook-performance.md:25-27` |
| R2 | The registered command lines in `settings.common.json:33,44,55` and `codex/hooks.json:10,21,32` stay byte-identical. Each `hooks/ai-*-guard.sh` becomes an exec shim with no logic: at most 6 lines, one `exec`, no other command. | C1 (Codex `trusted_hash` covers the whole entry, `install.sh:1008-1013`); intent Problem "nothing on screen says so"; D1 |
| R3 | No `jq` and no shell code from the Python entry point onwards. `grep -n jq hooks/ai-*-guard.py hooks/lib/*.py` is empty. The differential runs the `.py` guards with `PATH` set to a scratch `bin/` that holds only symlinks to `python3` and `git`. | O2 (in part: the shim stays bash until WP4a), Q10 |
| R4 | One OS module. In `hooks/ai-*-guard.py` and `hooks/lib/*.py`, only `hooks/lib/ai_os.py` reads `HOME`/`expanduser`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME` or `PWD`, or calls `os.getcwd`, `os.path.realpath` or `subprocess`. This is checked with grep. | O3, Q11 |
| R5 | User and project patterns stay POSIX ERE as glibc `regcomp(REG_EXTENDED)` compiles them. `tests/test_pattern_differential.py` reports zero undeclared divergences between `ai_ere` and bash `[[ =~ ]]` over the corpus of D4, under `LC_ALL=C` and `LC_ALL=C.UTF-8`. | OQ7; constraint "patterns stay POSIX ERE" |
| R6 | A pattern glibc rejects never matches in Python. This holds for single patterns, for the `\|`-joined pre-filter (`ai-hook-common.sh:259-264`) and for the anchor-stripped "loose" forms (`ai-path-guard.sh:82-89`). It is proven by the mutation corpus. | OQ7, C1 |
| R7 | `ere_match` keeps its line semantics (`ai-hook-common.sh:227-238`): one trailing `\n` is stripped, the subject is matched line by line, an empty subject never matches, and `^`/`$` anchor per line. This is proven against the frozen shell `ere_match`. | C1 |
| R8 | The scope guard's plan-glob semantics are reproduced: bash `[[ $s == $p ]]` with extglob on, plus the `$dir/*` prefix rule (`ai-scope-guard.sh:85-98`). So is its deny message's unquoted `$ALLOWED`, which is word-split and then **pathname-expanded** against the hook process's cwd (`ai-scope-guard.sh:117`). | C1 |
| R9 | Pattern lists and Bash tokens are ordered in C-locale `sort -u` order, which is Python code-point order (`ai-path-guard.sh:63-71,338-344`). The golden proves it. The difference for users whose hook locale is not C is declared (D6); it affects the message only. | constraint "no decision changes on Linux" |
| R10 | Slow patterns have a defined outcome (D5). Each pattern is either clean under the static screen `ai_ere.is_risky` or matched under `AI_GUARD_MATCH_BUDGET_MS` (default 500). The budget is a `signal.setitimer(ITIMER_REAL)` alarm in the main thread, **not a thread**. On expiry, a deny-kind list counts as matched, an allow-kind list as not matched, and the joined pre-filter as interesting. Every shipped pattern and built-in rule is either screen-clean or listed as budgeted in that guard's `RULES` table. A unit test shows `(a+)+$` over `"a"*34+"b"` returning within budget + 100 ms on Python 3.11, 3.12 and 3.13. The `CONFIRM_RE` case in `.ai/project/known-risks.md:54-61` (a 120 KB padded line, about 13 s under glibc) is measured again and recorded. | OQ7; constraints "guards must not be weakened" and fail-open (`ai-hook-common.sh:15-17`) |
| R11 | The hot path is no slower than the budget. Process count by the doc's `strace` recipe: at most 3 through the shim (the script, bash via `env`, `python3`), plus one per git call where a rule asks git today (`ai-git-guard.sh:78,89,139`). Wall clock stays within every row of the budget table and not above the measured rows of 2026-09-20. Both are measured by the recipe at `docs/hook-performance.md:151-160` and written into that file. | constraint "budgets hold on Linux" |
| R12 | Outside the equivalence domain (D6) a guard exits 0, prints nothing, and lets no exception escape. `tests/test_guard_port_unit.py` calls each guard's `main()` **in-process**, so a swallowed exception is still seen. It feeds random bytes, concatenated JSON, a 1 MiB payload, NUL bytes, lone surrogates, non-string fields and an unparsable state file. | fail-open policy |
| R13 | `install.sh` installs the new files into both roots and stops installing `hooks/lib/ai-hook-common.sh`, which is deleted from the tree. A copy already installed is **left in place**; removing stale files is O30 and belongs to WP4a. No other installer behaviour changes. The `--dry-run` output differs only in the hook file listing. | intent WP1 row ("the hook list"); C3 |
| R14 | Edits to existing tests are limited to these, and none adds, removes or changes an assertion: `tests/run-all.sh` (the new suite wrappers), the reference call in `tests/test-ai-status-root.sh:41-45`, and the installed-file lists at `tests/test-install-dry-run.sh:168` and `tests/test-codex-install.sh:70-71`. `git diff --stat tests/` shows only those four files plus new files. | `.ai/workflows/refactoring.md` ("a test that has to be modified … signals behaviour changed") — see F2 |
| R15 | Whole-guard differential: the frozen shell guards against the Python guards, at least 300 seeded generated payloads per run, compared on rc + stdout + stderr bytes. Before approval there is one logged run at `AI_DIFF_N=5000`, with its seed recorded in the task report. | OQ7 |
| R16 | The port gets a security review whatever its tier, covering at least the checklist in F7. | intent constraint |
| R17 | New Python files score 10.00 under `.pylintrc` on 3.11, 3.12 and 3.13 (CI `pylint.yml`). They use the stdlib only and nothing newer than 3.11. An unavoidable warning gets an inline disable with its reason. | `.ai/policies/testing.md:150-155`; O2 |
| R18 | No rule changes. `hooks/*-defaults.json` and `.ai/policies/path-guard.json` are untouched. The new `hooks/ai-*-guard.py` files fall under the existing `(^|/)\.claude/hooks/ai-[^/]*$` and `.codex` patterns (`hooks/ai-path-guard-defaults.json:32-35`). `hooks/lib/*.py` keeps the library's current status: protected only while a task is in flight (F6e). | C3; Out of scope "what a guard decides on Linux" |
| R19 | `docs/hook-performance.md` gains the Python-port measurement block, the process model with and without the shim, the slow-pattern rule (R10), and "ctypes libc engine" under "deliberately not done". | intent WP1 row |
| R20 | The payload is read as bytes and decoded as UTF-8 with `errors="replace"` (jq's U+FFFD). Lone-surrogate escapes become U+FFFD. Stdout is written as UTF-8 with `\n` whatever the locale. | constraint "text is UTF-8" (WP4b extends it to files) |
| R21 | References follow the code, with no behaviour change: `docs/hooks.md:37,49`, `docs/architecture.md:232,239`, `skills/ai-status/SKILL.md:35` (keeps the name `find_ai_root`, asserted at `tests/test-ai-status-root.sh:23`, and names `hooks/lib/ai_os.py`), and `.ai/project/known-risks.md:30`. `known-risks.md` also gains entries for F6a, F6c and F6e. | `.ai/AGENTS.md` "Keeping this directory true" |

## Design

### Components

| File | Status | Responsibility |
|---|---|---|
| `hooks/lib/ai_os.py` | new | **The one OS module** (O3). WP1 ships only what the guards use: the runtime homes, the hook-config search dirs, the logical cwd, `cd`-like directory resolution, `find_ai_root`, `abs_path`, `real_path`, `run_git`. WP2 and WP4b add `atomic_write`, `lock`, `is_tty` and the file-system path comparison of O6 **here and nowhere else**. |
| `hooks/lib/ai_ere.py` | new | POSIX ERE → Python `re` translator that parses as glibc does. An invalid pattern compiles to `None`, which never matches. It also holds the static ReDoS screen and the budgeted match. |
| `hooks/lib/ai_bashpat.py` | new | The bash `[[ == ]]` matcher (extglob on; `nocasematch`, `globstar` and `dotglob` off) and the pathname expansion used in the scope guard's deny message. |
| `hooks/lib/ai_hook_common.py` | new | Port of `ai-hook-common.sh`: the payload with jq stream semantics, tool normalisation, `target_paths`/`patch_paths`, `strip_prose`, `ere_match`/`matches_any`/`matches_joined`, `json_strings`, the `jq -nc`-compatible deny, and the fail-open wrapper. |
| `hooks/ai-git-guard.py`, `hooks/ai-path-guard.py`, `hooks/ai-scope-guard.py` | new | One-to-one ports. Rule order, messages and laziness are the same: `task_in_flight` is read only on demand (`ai-path-guard.sh:111-123`) and git only where the shell asks it. Each exports `RULES` (name → ERE source) for the differential. `git_subcommand` (`ai-git-guard.sh:103-105`) is dead code and is not ported. |
| `hooks/ai-*-guard.sh` | rewritten | Exec shims (R2). |
| `hooks/lib/ai-hook-common.sh` | deleted | No second shell implementation (Q11). |
| `tests/fixtures/guard-port/{ai-git-guard.sh,ai-path-guard.sh,ai-scope-guard.sh,lib/ai-hook-common.sh}` | new | Byte copies of today's files, made in the first step (`cmp` in the report). They are the differential's oracle and are retired in WP3b (F3). |
| `tests/test_pattern_differential.py`, `tests/test_guard_differential.py`, `tests/test_ere_unit.py`, `tests/test_guard_port_unit.py`, `tests/fixtures/ere/cases.tsv` | new | D4 and R10–R12. `test_*.py` falls under the `tests` path scope of `risk-tiers.json`. Each runs through a two-line bash wrapper in `run-all.sh`'s literal list until WP3a's runner exists. |

### Data flow (one tool call)

runtime → `"$HOME/.claude/hooks/ai-path-guard.sh"` (unchanged entry) → the shim runs `exec python3 -I -S <dir>/ai-path-guard.py`, which inserts `<dir>/lib` at the head of `sys.path` → `ai_hook_common.read_payload(sys.stdin.buffer)`, one parse → tool switch → `ai_os.find_ai_root(cwd)` → pattern lists through `json_strings`, unioned and C-sorted → the rules in source order, each one `ai_ere` search per line → `deny(reason)` prints one compact JSON line and exits 0, or `allow()` exits 0. Git is called through `ai_os.run_git`, with an argument list, no shell, and `subprocess` imported lazily. Every exception ends in exit 0 with no output, as `2>/dev/null` / `|| exit 0` do today.

### Decisions

**D1. The hook entries stay as they are; WP4a switches them.** WP1 keeps every registered command
line byte-identical and turns the `.sh` files into exec shims. This follows WP5's precedent of old
names kept as shims so that Codex trust survives (`docs/hook-performance.md:139-142`). Moving to
WP4a are:
- the switch to a direct `python3 … .py` command line;
- the upgrade of old entries without duplicates (O30);
- the removal of stale installed files (O30).

Reasons:
- Changing an entry changes its Codex `trusted_hash` (`install.sh:1008-1013`). Codex users would
  then be unguarded with nothing on screen until O29 exists, which is exactly the hazard the
  intent's own Problem text names.
- Every guard suite and the e2e suite (`tests/test-end-to-end.sh:30-32,112-114`) call the `.sh`
  paths and keep working unchanged, so the refactoring is proven with its suites unchanged.
- A running Claude session keeps its hook snapshot either way.

Cost: one bash process (≈3 ms), and bash stays on the hook path until WP4a. This needs the human's
confirmation (H1 / F1).

**D2. Four small modules in `hooks/lib/`**, a directory both roots already install. They have
importable underscore names; the guard scripts keep hyphenated names as `context-guard.py` does.
The import is explicit: `sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))`. With `-I` the script's
directory is not on `sys.path`, and `PYTHONPATH` and the user site are ignored. `-S` skips `site`,
which saves an estimated 4–6 ms. Bytecode caching is wanted (no `-B`), and `__pycache__` is already
git-ignored. Later code reaches `ai_os` at the same relative path in the source tree and in both
install roots. Folding in the four home-directory and seven atomic-write copies elsewhere is WP2 and
WP4b work, not WP1's.

**D3. The engine translates ERE to `re`, follows glibc's parse rules, and uses C-locale classes.**
Whether a pattern matches at all depends only on the language it describes, so glibc's
leftmost-longest rule against Python's leftmost-first cannot change a decision. They can only differ
in captures. Two built-in rules use captures: `refspec_re` (`ai-git-guard.sh:169-173`) and `ln_re`
(`ai-path-guard.sh:350-354`). Each gets a dedicated generated corpus of at least 1000 lines; if
POSIX subexpression rules diverge there, a hand-written extractor replaces the regex. Translator
rules, each one a corpus item:
- `[[:class:]]` becomes an ASCII set; `[[:space:]]` becomes `[ \t\n\v\f\r]`.
- A backslash inside brackets is literal. `[]a]`, `[^]a]` and a trailing `-` are handled.
- `[[=c=]]` and `[[.c.]]` are accepted for a single character.
- The GNU escapes `\w \W \s \S \b \B \< \> \` \'` map to ASCII equivalents and are compiled with
  `re.ASCII`.
- A back-reference `\1`–`\9` is kept.
- `a+?` and `a*?` become `(?:a+)?`. POSIX has no lazy quantifier.
- A lone `)` is literal.
- A leading `*`, `+` or `?`, `(?`, a bad interval, a bad range, an unknown class, a trailing `\`,
  and an unmatched `(` or `[` are invalid and never match.
- A `{` that does not form a valid interval: the oracle decides.

Class semantics are ASCII on every OS (H2). That is what the golden pins, and it is the only
meaning that is the same everywhere (O6).

**D4. The proof (OQ7).**
- **(i) Golden.** Unchanged, through the shims (R1).
- **(ii) Engine differential, `tests/test_pattern_differential.py`.**
  - *Oracle:* one long-lived `bash` per locale (`C`, `C.UTF-8`) reads `pattern\tsubject` records
    and answers through `[[ =~ ]]` (and `[[ == ]]` for `ai_bashpat`). The oracle is bash and not
    ctypes, because bash *is* today's engine.
  - *Patterns:*
    - every string in both defaults files, with protected branches wrapped `^…$` as at
      `ai-git-guard.sh:98`;
    - every built-in `RULES` entry;
    - the joined and loose forms of each list;
    - about 150 hand-written construct snippets covering D3;
    - five one-character mutations per pattern, drawn from its own alphabet plus `()[]{}|*+?^$\.`.
  - *Subjects:*
    - the characterization corpus's commands and paths;
    - seeded random strings (`AI_DIFF_SEED`, default `20261003`, printed in the summary) of length
      0–40, over the pattern's literals plus `/ . - _ space tab ; & | ( ) < > ' " $ = : \n` and two
      non-ASCII characters;
    - `AI_DIFF_N` per pattern (default 200), about 150 k cases in under 60 s.
  - *Multi-line subjects* go through `ai_hook_common.ere_match`, compared with the frozen
    `ere_match` sourced from the fixture copy.
  - *Declared divergences* (D6) are an explicit list inside the test. Anything else fails, naming
    the pattern, the subject, both verdicts and the seed.
  - `--record` samples 2000 cases into `tests/fixtures/ere/cases.tsv`. `tests/test_ere_unit.py`
    replays them without bash, which is what macOS and Windows later run.
- **(iii) Whole-guard differential, `tests/test_guard_differential.py`.**
  - *Tree:* it rebuilds the characterization tree (`test-guard-characterization.sh:44-89`) in
    Python, plus a symlinked project directory.
  - *Payloads* are generated from a grammar:
    - verbs × flags × paths, with `..`, symlinks, missing files and `=`-tokens;
    - quoting, `;&|()<>`, heredocs, backslash-newline and multi-line commands;
    - the file tools × their path fields, with relative and absolute paths;
    - Codex `apply_patch` headers and `shell` arrays;
    - malformed input: concatenated JSON, non-string fields, `false`/`null`, numbers;
    - state variants: the stage, duplicate step ids, an unparsable state file.
  - *Runs:* the frozen shell guards (bash + jq) against the `.py` guards (the jq-less `PATH` of
    R3, plus the shim on a 10 % sample). Both run under `LC_ALL=C` with a scratch `HOME`, from a
    scratch `hooks/` that holds the current `*-defaults.json`. The bytes are compared.
  - *Size:* `AI_DIFF_N=300` per run by default, plus the one logged 5000-payload run (R15).
  - *Where the old guards come from:* frozen copies, not `git show <sha>`, because
    `actions/checkout@v4` without `fetch-depth` is shallow (`.github/workflows/tests.yml:15`). The
    suite skips with one line when bash or jq is absent.

**D5. Slow patterns.** glibc does not backtrack catastrophically without back-references; Python
`re` does. Only the `CONFIRM_RE` case recorded at `.ai/project/known-risks.md:54-61` is slow in
glibc too.
- **Screen.** `ai_ere.is_risky` is a static screen over the translator's AST. It flags a quantified
  group that contains a quantifier, or an alternation whose branches can match the same prefix:
  `(a+)+`, `(a|a)*`, `(.*x)*`, `(a*)*`. It is conservative on purpose.
- **Budget.** A risky pattern is matched under a `signal.setitimer(ITIMER_REAL)` alarm in the main
  thread. CPython's `_sre` checks for pending signals while it matches, so the handler's exception
  interrupts it. Checked in this session on Python 3.14: `(a+)+$` over `"a"*34+"b"` was interrupted
  after 0.20 s. On 3.11–3.13 this is *inferred*; R10's unit test proves it.
- **Not a thread.** The architect's first proposal was a daemon thread with `join(timeout)`. It was
  tried and does not work: `_sre` holds the GIL, `join(0.2)` never returned, and the process ran
  until it was killed at 8 s.
- **On expiry** the outcome is the stricter one (H3):
  - deny-kind lists (`deny`, `protected`, `task`, `vendor`, `sensitive_staging_patterns`,
    `deploy_patterns`, `protected_branches`) count as matched, and the reason reads
    `(matched: <pattern>; matching exceeded <N> ms)`;
  - allow lists count as not matched;
  - the joined pre-filter counts as interesting.
- **Where `setitimer` is missing** (native Windows Python, WP4b), a risky pattern runs without a
  budget, bounded by the runtime's hook timeout as today. WP4b chooses the Windows mechanism.

**D6. Equivalence domain.** Byte identity with the shell guards is promised when all of these hold:
- stdin is empty, not JSON, or one or more RFC 8259 texts in valid UTF-8 without NUL. Several
  concatenated values reproduce jq's `[inputs]` "SLOW" path (`ai-hook-common.sh:62-65`) through a
  `raw_decode` loop; any parse error allows.
- `tool_name`, `cwd` and `hook_event_name` are absent, `null`, `false` or a string.
- `cwd` is absolute and names an existing directory.
- The hook locale is `C`, or a UTF-8 locale with ASCII-only subjects.
- jq ≥ 1.7 is the formatting reference for a non-string `command`. Arrays and objects of strings
  are reproduced by `json.dumps(v, indent=2, ensure_ascii=False)`; numbers depend on jq's version.
- git is on `PATH`.

Declared divergences:
- POSIX classes on non-ASCII text under a UTF-8 locale;
- `sort -u` order under a non-C locale, which affects the message only;
- lone surrogates (both give U+FFFD, but bash's path differs);
- a relative `cwd` (bash `cd` honours `CDPATH`);
- multi-character `[[.x.]]` and `[[=x=]]`;
- NUL bytes (bash warns on stderr, Python drops them silently);
- the budget's outcome on expiry (D5).

Outside the domain the guard exits 0 and stays silent (R12).

**D7. The hot path** (estimated in the design; measured in the task). The parts are `python3 -I -S`
start-up (≈9–10 ms), `json` + `re` (≈3), the three cached `.pyc` imports (≈2) and lazy regex
compilation (≈3–8). The joined forms are compiled only on a Bash call, and each rule regex on first
use. The estimate is ≈25–35 ms per budget row against 62–112 ms measured today, plus ≈3 ms through
the shim.

### Alternatives rejected

1. **ctypes to libc `regcomp` as the engine.** It is bit-exact on glibc, but macOS libc lacks the
   GNU escapes and Windows has no POSIX regex. O3 and O6 would need a second engine anyway, and
   `import ctypes` costs ≈3 ms per call.
2. **A pure-Python POSIX NFA (Pike VM).** It is linear and exact, but it is ≈1 k lines of new
   security-critical code, and interpreting the ≈2.5 KB joined pre-filter over a 200-character
   command costs an estimated 100–200 ms, over budget.
3. **Switching the command lines in WP1 (intent row as written).** Codex users would be silently
   unguarded until O29, and three install suites would need assertion edits (D1).
4. **Keeping `ai-hook-common.sh` for `test-ai-status-root.sh`.** That keeps a second shell
   implementation of `find_ai_root` (Q11).
5. **`git show <ref>:hooks/…` as the differential's oracle.** It fails on the shallow CI checkout.
6. **One monolithic `ai_hook_common.py`.** The engines would not be reviewable or differentially
   testable as units, and the security review would lose its focus.
7. **A thread-based regex timeout.** `_sre` holds the GIL, as shown in D5.

### Build order (input for `/sdlc-plan`; one mechanical step each)

1. Freeze the four shell files under `tests/fixtures/guard-port/`, and add a skeleton of the
   whole-guard differential that compares old against old and passes, which proves the harness.
2. Write `ai_os.py` and change the reference call in `test-ai-status-root.sh`, which proves the walk
   matches.
3. Write `ai_ere.py`, `ai_bashpat.py` and the engine differential, record `cases.tsv`, and write
   `test_ere_unit.py`; the step ends with zero undeclared divergences.
4. Write `ai_hook_common.py` and `test_guard_port_unit.py`.
5. Port `ai-scope-guard.py`, the smallest.
6. Port `ai-git-guard.py`.
7. Port `ai-path-guard.py`. Each port ends with its slice of the differential green.
8. Rewrite the three `.sh` files as shims and delete `lib/ai-hook-common.sh`. The characterization
   suite and every guard suite pass through the shims.
9. Change the `install.sh` copy lists, the two install-suite file lists and `run-all.sh`. Run
   `bash tests/run-all.sh` once, then `bash tests/test-end-to-end.sh` once.
10. Measure and write `docs/hook-performance.md`, update the references in R21, do the logged
    5000-payload run, then the security review.

## Interfaces

**Shim** (`hooks/ai-git-guard.sh`; path and scope are the same with their own names):

```bash
#!/usr/bin/env bash
# claude-agentic: shim — the guard is ai-git-guard.py beside this file. Kept so the registered
# hook entries and Codex trust hashes survive until WP4a's installer replaces them.
d="${BASH_SOURCE[0]%/*}"; [ "$d" != "${BASH_SOURCE[0]}" ] || d=.
exec python3 -I -S "$d/ai-git-guard.py" "$@"
```

**Registered command lines (unchanged):** `"\"$HOME/.claude/hooks/ai-{git,path,scope}-guard.sh\""`
in `settings.common.json`, and `"\"$HOME/.codex/hooks/ai-{git,path,scope}-guard.sh\""` in
`codex/hooks.json`.

**Guard contract (unchanged):**
- stdin: the PreToolUse payload.
- stdout: nothing (allow), or exactly one line,
  `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}\n`
  (compact, UTF-8 raw, `\u007f` escaped, as `jq -nc`).
- rc: always 0. stderr: empty.
- Environment read: `HOME`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `PWD`, `AI_UNATTENDED`, and the new
  `AI_GUARD_MATCH_BUDGET_MS` (an integer; a missing or invalid value means 500).

**`hooks/lib/ai_os.py`**
```python
def runtime_home(runtime: str) -> str                # "claude": CLAUDE_CONFIG_DIR or ~/.claude; "codex": CODEX_HOME or ~/.codex
def hook_config_dirs(hook_dir: str) -> list[str]     # [hook_dir, runtime_home("claude")+"/hooks", runtime_home("codex")+"/hooks"]  (ai-hook-common.sh:94)
def logical_cwd() -> str                              # $PWD when it names the same directory as ".", else os.getcwd()
def resolve_dir(path: str, base: str) -> str | None   # `cd "$d" && pwd`: logical normalisation; None unless a searchable directory
def find_ai_root(start: str) -> str | None            # ai-hook-common.sh:182-192, including the "/" case
def abs_path(path: str, cwd: str) -> str              # ai-hook-common.sh:196-202 — no normalisation
def real_path(path: str, cwd: str) -> str             # ai-hook-common.sh:205-213 — realpath only when the path exists
def run_git(cwd: str, *args: str) -> str | None       # ["git", "-C", cwd, *args]; stdout (UTF-8, replace) or None on error/rc != 0
```

**`hooks/lib/ai_ere.py`**
```python
class EreError(ValueError): ...                       # translate(): where glibc regcomp fails
class MatchBudgetExceeded(Exception): pattern: str
class Ere:                                            # __slots__ = ("source", "risky", "_rx")
    def search(self, line: str) -> bool               # raises MatchBudgetExceeded only when risky and the alarm fires
    def captures(self, line: str) -> tuple[str | None, ...] | None
def translate(pattern: str) -> str
def compile(pattern: str) -> Ere | None               # None == never matches; cached per process
def is_risky(pattern: str) -> bool
BUDGET_MS: int
```

**`hooks/lib/ai_bashpat.py`**
```python
def match(subject: str, pattern: str) -> bool         # bash [[ $subject == $pattern ]], extglob on
def expand_words(text: str, cwd: str) -> list[str]    # split on " \t\n", then pathname expansion per word:
                                                      # C-sorted, dotfiles excluded, an unmatched word kept literal
```

**`hooks/lib/ai_hook_common.py`**
```python
class Payload: raw: str; values: list; tool_raw: str; tool: str; cwd: str; event: str; command: str | None; command_ok: bool
def read_payload(stream) -> Payload                   # sys.exit(0) on empty/unparsable; tool map ai-hook-common.sh:75-79
def chomp_all(s: str) -> str
def jq_r(value) -> str                                # jq -r: str raw; None/False/absent -> ""; else json.dumps(indent=2, ensure_ascii=False)
def bash_command(p: Payload) -> str
def patch_paths(p: Payload) -> list[str]              # ai-hook-common.sh:116-119
def target_paths(p: Payload) -> list[str]             # ai-hook-common.sh:122-129: jq `?`, `.[]?` over object values, "\n" split
def runtime_hook_config(hook_dir: str, name: str) -> str | None
def ere_escape(s: str) -> str
def strip_prose(cmd: str) -> str                      # ai-hook-common.sh:148-169: same regexes and the same `<<` / `-m` pre-check
def ere_match(pattern: str, subject: str) -> bool
def matches_any(subject: str, patterns: list[str]) -> str | None
def matches_joined(subject: str, patterns: list[str]) -> bool   # one ERE built by "|".join — never an OR of compiled parts (F6a)
def json_strings(path: str, key: str) -> list[str]
def encode_deny(reason: str) -> str
def deny(reason: str) -> NoReturn
def allow() -> NoReturn
def main_guard(fn) -> NoReturn                        # stdout reconfigured UTF-8/"\n"; any exception -> exit 0, silent
```

**Guards:** each `hooks/ai-*-guard.py` exposes `RULES: dict[str, str]`, a `BUDGETED: frozenset[str]`
naming the rules that fail the screen (R10), and `main()`. `ai-path-guard.py` adds
`load_pattern_lists(files) -> dict[str, list[str]]` (unique, sorted by `(tag, rest)` in code-point
order). `ai-git-guard.py` keeps `LIST_KEYS` from `ai-git-guard.sh:48`.

**Tests:**
```
bash tests/test-guard-characterization.sh                          # unchanged; golden unchanged
bash tests/test-pattern-differential.sh -> python3 tests/test_pattern_differential.py  [AI_DIFF_SEED] [AI_DIFF_N=200] [--record]
bash tests/test-guard-differential.sh   -> python3 tests/test_guard_differential.py    [AI_DIFF_SEED] [AI_DIFF_N=300]
python3 tests/test_ere_unit.py ; python3 tests/test_guard_port_unit.py                 # stdlib unittest; no bash, no jq
```
Each Python suite prints `<name>: N passed, M failed` and exits 1 on any failure. Each wrapper is
`exec python3 "$(dirname "$0")/<module>.py" "$@"`.

**`install.sh` (these edits only):**
- `:626`: the glob gains `"$SRC"/hooks/lib/*.py`.
- `codex_hook_files` (`:965-973`): gains the three `.py` guards.
- `:990`: becomes a loop over `"$SRC"/hooks/lib/*.py`.
- The dry-run listing follows from these.

## Policy conformance

- **`~/.claude/CLAUDE.md` (global).** The change runs through `/ai-task` after `/sdlc-plan`. Each
  build step names its files (C4). The spec documents the defects it finds and does not fix them
  (F6). No refactoring is mixed with a feature (C3; D1 keeps the entry switch out). Verification is
  one `bash tests/run-all.sh` run plus one e2e run (step 9). The architect ran at STRONG on a named
  trigger (sdlc-spec step 3, a reversible design with several viable options), one agent, with no
  EXPERT escalation: no data model or public contract changes, because the hook contract stays the
  same.
- **`CLAUDE.md` (project, managed block).** `/ai-task` with scope refusal by `SCOPE_CHANGE_REQUIRED`;
  `verify_command` then `e2e_command`; no agent commits; decisions in files (this spec, then the
  task's `questions.md`). There is no repo-root `AGENTS.md`, so there was no second file to compare.
- **`.ai/AGENTS.md` non-negotiables 1–7.**
  - 1: production behaviour is reproduced, including its bugs (F6).
  - 5: characterization first; the golden plus two differentials prove the port.
  - 6: evidence labels are used in this spec and in the `known-risks.md` entries.
  - 7: C-principles are cited.
- **`docs/sdlc/constitution.md`.** C1 (reproduce F6a–F6d), C3 (refactoring only; R1, R14, D1), C4
  (build order, one step one file set), C5 (approval and commit are human; F11). C6–C10 are
  placeholders (F11).
- **`.ai/workflows/refactoring.md`.**
  - The required order is followed: characterization, then refactor, then identical behaviour
    proven.
  - The rule "a test that has to be modified signals behaviour change" is met for every suite that
    tests guard **decisions**. The four test edits that remain carry no assertion and are named in
    R14 and F2.
  - Plan review always.
- **`docs/hook-performance.md`.** The golden is not edited and not re-recorded. The budget table
  holds (R11), and the process count is the contract. Rejected as in "deliberately not done": a
  compiled engine, a daemon, caching a decision.
- **`.ai/policies/testing.md`.** Suites are named per step. New suites are added to `run-all.sh`'s
  literal list. CI pylint must score 10.00 on 3.11–3.13 (R17). The row at `:142` goes stale (F8).
- **`.ai/policies/security.md`.**
  - Command execution: git takes an argument list and no shell.
  - Input validation: the payload is untrusted; R12 and R20 cover it.
  - Dependencies: none added (stdlib only).
  - AI context safety: deny reasons are unchanged.
  - The security review is mandatory (R16, F7).
- **`.ai/policies/production.md`.** Compatibility order: the shim (an adapter and compatibility
  layer) wins over a breaking entry change, and the change is incremental (D1).
- **`.ai/policies/risk-tiers.json`.** The source files under `hooks/` fall in no path scope;
  `tests/**` is T1, `docs/**` T0, and `.ai/policies/**` T3 if `testing.md:142` is edited.
  `ai-risk` assigns the tier; the intent estimates T3, and the security review applies at any tier.
- **`.ai/policies/safety.md` and the path guard's task-protected list.** `.ai/policies/` cannot be
  edited by an agent in flight (F8). `.ai/project/known-risks.md` is not task-protected, so R21 can
  edit it.
- **Repo skills and agents** (`.claude/skills`, `.claude/agents`, `.codex/*`): none exist in the
  repository.
- **ADRs** (`docs/sdlc/adr/`): only `TEMPLATE.md`; none bind.
- **Plugin skills:** none match a bash/Python hook port (the Symfony UX, PHP, Remotion and
  document skills do not apply).

## Flagged concerns

**F1 — The intent contradicts itself on hook entries (decided: H1, keep the entries).** The WP1 row
assigns "the hook command lines in `settings.common.json` and `codex/hooks.json`; `install.sh` (…
the upgrade of existing entries)" to WP1. The intent's Problem text says that changing a guard's
entry leaves Codex users unguarded with nothing on screen. O29, the only remedy, is in WP4a, and
WP4a depends on WP1. The spec resolves this by D1:
- the entries stay as they are, and the shims carry the change;
- the command-line switch and O30 move to WP4a;
- the intent's WP table needs a one-line amendment.

Consequence: O2's "no shell script on the hook path" holds only after WP4a. If H1 is rejected, WP1
must not be released without WP4a (OQ24), and three install suites need assertion edits.

**F2 — "A suite stays fixed while the code under it is ported" cannot hold literally.** Deleting
`ai-hook-common.sh` (Q11: no second shell implementation) breaks:
- `tests/test-ai-status-root.sh:41`, which **sources** the shell library to compare `find_ai_root`;
- the installed-file lists at `tests/test-install-dry-run.sh:168` and
  `tests/test-codex-install.sh:70-71`.

These are edited in their invocation and file names only, with no assertion added, removed or
changed (R14). The reviewer checks that with `git diff`. Every suite that tests guard decisions
stays byte-identical.

**F3 — Frozen shell copies as the oracle.** `tests/fixtures/guard-port/` keeps the old shell logic
alive as a test fixture until WP3b. That is in tension with "no second implementation of the same
logic is kept in shell". It also keeps bash and jq as development-only dependencies until then, which
is consistent with O8's "after that". The alternative, `git show`, fails on a shallow CI checkout.
Accepted as H4.

**F4 — "No guard decision changes on Linux" is not well defined today.** The shell guards' output
already depends on things outside the code:
- the hook process's locale: POSIX class membership for non-ASCII text, `sort -u` collation for
  which pattern or token a deny names, and possibly bracket ranges on some glibc versions
  (*inferred*);
- jq's version: the pretty-printed form of a non-string `command`;
- `CDPATH` for a relative `cwd`.

The golden pins `LC_ALL=C`. The spec defines the equivalence domain (D6) and fixes C-locale
semantics on every OS (H2). On a machine running en_US.UTF-8, a deny message may then name a
different but equally matching pattern than it does today. The decision is the same; the text is not.

**F5 — The slow-pattern rule changes the outcome where today the runtime's timeout decides.** On
budget expiry a deny-kind rule now denies (H3). Today glibc either answers correctly or, for the
`CONFIRM_RE` case in `known-risks.md:54-61`, runs past the 10 s hook timeout, after which the
runtime proceeds (*inferred*, as that entry says). In that case the port is stricter. This is
declared, not hidden. The architect's thread-based budget was shown not to work in this session. The
spec uses `setitimer`, and Windows (no `SIGALRM`) is left to WP4b. Some built-in rules (*inferred*:
`CONFIRM_RE`'s `([^|;&]|[<>]&|&>)*`, whose branches overlap on `<&>`) may fail the static screen.
They run budgeted and are listed in `BUDGETED`; their regex text is not rewritten in WP1.

**F6 — Defects found and reproduced, not fixed (C1).** Each goes to `known-risks.md` or to a later
rule task:
- **a.** One invalid regex in a project's `path-guard.json` makes the `|`-joined pre-filter invalid,
  and the **whole path guard then allows everything** (`ai-hook-common.sh:259-264`,
  `ai-path-guard.sh:132`). Joining can also make two invalid patterns valid together.
- **b.** The loose patterns' string surgery can produce an invalid pattern, for example `foo\$` →
  `foo\` (`ai-path-guard.sh:85`), with the same effect on the Bash fast path.
- **c.** The scope deny message lists `$ALLOWED` unquoted, so plan globs are pathname-expanded
  against the hook's cwd (`ai-scope-guard.sh:117`).
- **d.** `skills/ai-task/sensors.py:342-351` claims the scope guard's semantics but uses
  `fnmatch.fnmatchcase`, which has no extglob and reads `[^x]` literally. It is an existing
  divergence; `ai_bashpat` makes a later fix possible but WP1 does not touch `sensors.py`.
- **e. (security)** `protected_config_patterns` cover `.claude/hooks/ai-*` and `.codex/hooks/ai-*`
  but not `hooks/lib/` (`hooks/ai-path-guard-defaults.json:32-35`). Outside a task, an agent can edit
  the library every guard executes. The exposure is the same as today's `.sh` library. The additive
  pattern `(^|/)\.(claude|codex)/hooks/lib/[^/]*$` is proposed as a separate rule change with a
  golden re-record.
- **f.** The approve rule is matched line by line, so a backslash-newline splits it
  (`known-risks.md:26-32`). This is reproduced.

**F7 — Security review checklist (R16).**
- `-I -S` flags and the explicit `sys.path` entry: no `PYTHONPATH` injection, no user site.
- The lib directory's writability (F6e).
- The UTF-8 decode with `replace`, and the handling of lone surrogates.
- `run_git`: an argument list, `-C cwd`, no shell.
- The fail-open wrapper turns any bug into a silent allow. R12's in-process tests and the
  differentials are the only defence, so their coverage is part of the review.
- The translator's accept/reject boundary: accepting more creates new denies, rejecting more
  silently drops a deny rule.
- The budget handler must not leak an alarm into the next match.
- The new `AI_GUARD_MATCH_BUDGET_MS` comes from the runtime's environment, not the agent's. An agent
  cannot set it for the hook process (*inferred* from how hooks are spawned). A very large value only
  restores today's timeout behaviour.

**F8 — Task-protected and stale policy text.** `.ai/policies/testing.md:142` maps
`hooks/ai-*-guard.sh` to the guard suites. After WP1 it should read `hooks/ai-*-guard.py`,
`hooks/lib/*.py` → the guard suites plus the two differentials. The path guard freezes
`.ai/policies/` during a task, so a human makes this edit outside the run (H5). Separately,
`testing.md:150` names `.github/workflows/test.yml`; the file is `tests.yml`. That is documented
here, not fixed.

**F9 — New Python tests come before WP3a's runner.** The wrappers in `run-all.sh` and the stdlib
`unittest` layout pre-empt WP3a's choice of runner. Both are disposable: two-line wrappers, and
`unittest` also runs under pytest.

**F10 — Latency off Linux is unknown.** The budgets were measured on Linux only (OQ8). WP1 proves
Linux. Python start-up on macOS and Windows is WP4b's question.

**F11 — Observed outside the task (documented, not fixed):**
- **(a)** `install.sh` renders both runtimes' routing into the same `$TMP/routing.md` (`:423`,
  `:932`) and installs it at `:730`. On this machine `~/.claude/claude-agentic/routing.md` holds the
  Codex "ChatGPT Plus" text while `profile.json` says Claude Max 20x. WP2's "identical installed
  result" would lock this bug in unless WP2 names it.
- **(b)** The global `~/.claude/CLAUDE.md` says "no agent commits, **pushes**, merges or deploys";
  the project block and C5 omit "pushes". The git guard enforces push rules either way.
- **(c)** Constitution C6–C10 and the project `CLAUDE.md` sections (Commands, Verification,
  Conventions, Architecture) are unfilled placeholders. Verification lives in
  `.ai/policies/testing.md`.
- **(d)** Both intents number their packages WP1…, so "WP2" is ambiguous in prose. This spec writes
  "WP2 of `adaptive-cross-runtime-sdlc`" when it means the older one.

**F12 — A missing interpreter becomes loud.** Without `python3`, the shim's `exec` fails with exit
127 and the runtime shows the error and proceeds. Today, a missing `jq` is a silent allow. Both are
outside every supported environment (`install.sh:80-81`). Loud is recommended (H7).

## Open questions

**Decided 2026-10-03 by the maintainer, via the picker during the spec review:**

- **H1:** keep the registered entries and ship exec shims in WP1. The command-line switch, the
  de-duplicating upgrade of old entries and stale-file removal (O30) move to WP4a. The intent's
  WP1 and WP4a rows are to be amended to match.
- **H2:** POSIX bracket classes are ASCII on every OS.
- **H3:** on budget expiry the outcome is the stricter one: deny-kind lists match, allow lists do
  not.
- **H4:** frozen shell guards live under `tests/fixtures/guard-port/` until WP3b.

| # | Question | Owner | Blocks |
|---|---|---|---|
| H5 | F8: who edits `.ai/policies/testing.md:142`: the human after approval, or WP3a? *Recommended: the human, one row.* | human | release of WP1 |
| H6 | `-I -S` in the shim now (and in the command line in WP4a)? *Recommended: yes*; the task keeps `-S` only if every suite passes with it. | human | the plan |
| H7 | F12: a missing interpreter is loud (exit 127) rather than silent? *Recommended: loud.* | human | — |
| OQ7 | Carried from the intent and answered here: D3 (meaning), D4 (side-by-side over generated inputs), D5 (too slow). | spec → plan review | WP1 |
| OQ3 | The interpreter's name on Windows (`python3`/`python`/`py`), and the shell used for hooks. | WP4b | WP4b |
| OQ8 | Acceptable latency on macOS and Windows. | WP4b | WP4b |
| OQ24 | Which packages make up which release. If H1 is rejected, WP1 must ship with WP4a. | human | release |
| N1 | Should the additive rule protecting `hooks/lib/` (F6e) and a fix for F6a and F6c be scheduled as their own rule-change tasks after WP1? | human | — |
