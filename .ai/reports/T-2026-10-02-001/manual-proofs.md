# WP1.1 — manual proofs (T-2026-10-02-001)

## Step 2: the oracle is a byte copy (cmp), with the modes kept (cp -p)

```
cmp hooks/ai-git-guard.sh                      tests/fixtures/guard-port/ai-git-guard.sh          identical  mode 775 -> 775
cmp hooks/ai-path-guard.sh                     tests/fixtures/guard-port/ai-path-guard.sh         identical  mode 775 -> 775
cmp hooks/ai-scope-guard.sh                    tests/fixtures/guard-port/ai-scope-guard.sh        identical  mode 775 -> 775
cmp hooks/lib/ai-hook-common.sh                tests/fixtures/guard-port/lib/ai-hook-common.sh    identical  mode 664 -> 664
git diff --quiet fea014f -- <the four sources>: exit 0 (the sources equal fea014f)
```

## Step 4: one run with AI_DIFF_N=2000 (old against old, PORTED empty)

```
$ AI_DIFF_N=2000 bash tests/test-guard-differential.sh
== guard differential (2000 payloads, 22 state variants, seed 20261003)
guard differential: 4884 passed, 0 failed (seed 20261003, n 2000)
exit 0, 0 FAIL lines, wall clock 17 s, 2026-10-02T22:49Z, python3 3.14.4, GNU bash, version 5.3.9(1)-release, jq-1.8.1
```

## Step 5: ai_os against bash and the frozen library (scratchpad probe, not a suite)

Five bases (a real dir, a symlink, under a symlink, a leading `//`, `/`) × 30 paths (empty, `.`/`..`, through a symlink and
back with `..`, a file, a missing prefix, `//`, `///`, `/..`, a dangling link, a loop, a dir without search
permission, `-`, `~`). Compared: `resolve_dir` with `cd "$p" && pwd`; `find_ai_root`, `abs_path`, `real_path` with the frozen
`ai-hook-common.sh`; `logical_cwd` with bash's own `pwd` under eight inherited `PWD`s; `hook_config_dirs` under four environments.

```
ai_os probe: 308 agree, 4 differ
```

The 4 that differ are all `find_ai_root("")`: the shell's `${1:-$AI_CWD}` falls back to the caller's cwd. Every guard calls it
with `"$AI_CWD"`, never empty; the docstring says the default is the caller's.

## End of task: lint, interpreters, P-R3, P-R4, Untouched, P-R14

```
$ pylint --rcfile .pylintrc hooks/lib/ai_os.py tests/test_guard_differential.py
Your code has been rated at 10.00/10 (previous run: 10.00/10, +0.00)
(pylint 4.0.8 on Python 3.14.4)
$ uvx --offline --python 3.11 pylint --rcfile .pylintrc hooks/lib/ai_os.py tests/test_guard_differential.py
Your code has been rated at 10.00/10 (previous run: 10.00/10, +0.00)
$ uv run --offline --no-project --python 3.11 python -I -S -c <smoke>
python 3.11.16 ai_os smoke: 7 of 7 ok
$ uv run --offline --no-project --python 3.13 python -I -S -c <smoke>
python 3.13.15 ai_os smoke: 7 of 7 ok
$ AI_DIFF_N=100 uv run --offline --no-project --python 3.11 python tests/test_guard_differential.py
guard differential: 248 passed, 0 failed (seed 20261003, n 100)
$ P-R4
3:Among hooks/ai-*-guard.py and hooks/lib/*.py, only this file reads HOME,
4:CLAUDE_CONFIG_DIR, CODEX_HOME or PWD, or calls os.getcwd, os.path.realpath or
5:subprocess. Each function reproduces the shell it replaces in
14:_HOMES = {"claude": ("CLAUDE_CONFIG_DIR", "/.claude"), "codex": ("CODEX_HOME", "/.codex")}
18:    """${CLAUDE_CONFIG_DIR:-$HOME/.claude} for "claude", ${CODEX_HOME:-$HOME/.codex} for "codex".
20:    An empty variable counts as unset, as `:-` has it; an unset HOME reads as
23:    var, tail = _HOMES[runtime]
24:    return os.environ.get(var) or os.environ.get("HOME", "") + tail
59:    An inherited $PWD that is absolute and names the same directory as "." is
60:    kept, canonicalised; anything else falls back to getcwd().
62:    pwd = os.environ.get("PWD", "")
65:            return _canon(pwd) or os.getcwd()
68:    return os.getcwd()
76:    directory, bash changes into it and answers with getcwd(), the physical
85:        canon = os.path.realpath(full)
125:    return os.path.realpath(full) if os.path.exists(full) else full
132:    after the payload had used up stdin. subprocess is imported here rather than
135:    import subprocess
137:        proc = subprocess.run(["git", "-C", cwd, *args], stdin=subprocess.DEVNULL,
138:                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
(P-R4 printed 20 lines)
$ P-R3 (secondary)
(P-R3 printed 0 lines)
$ imports of hooks/lib/*.py (read against the stdlib)
from __future__ import annotations
import os
    import subprocess
$ git diff --quiet fea014f -- <Untouched: R2, R18, R1, F2, sensors.py; plus the four shell sources>
exit 0: all 16 files unchanged since fea014f
$ P-R14 (tests/ against fea014f; only modifications listed)
M	tests/run-all.sh
M	tests/test-ai-status-root.sh
?? tests/fixtures/guard-port/
?? tests/test-guard-differential.sh
?? tests/test_guard_differential.py
$ P-R4 with -H (grep names the file even when given one)
(P-R4 -H printed 0 lines; without -H the 20 lines were all ai_os.py's own, unprefixed)
```

Suite: `state.py test-run --scope suite` exit 0 in 249 s (tests-suite-1.log); e2e: exit 0 in 3 s (tests-e2e-1.log).
P-R4 as the plan spells it needs `grep -H` while `hooks/lib/` holds one .py file and no `hooks/ai-*-guard.py` exists: grep then
drops the file prefix and the `grep -v '^hooks/lib/ai_os.py:'` filter cannot match. From WP1.2 on, `hooks/lib/` holds two files.

## R1 (review remediation): the MEDIUM repro, the 312-case probe again, the D6 check of the grammar

`med/x/y` mode 000, `med/x/l -> med/p/q`, `med/p/y/.ai`; columns: find_ai_root, then resolve_dir (`cd && pwd`).

```
agree  med/x/l/../y | shell: med/p/y med/p/y | ai_os: med/p/y med/p/y
agree  med/x/y | shell: NONE NONE | ai_os: NONE NONE
agree  med/x/l | shell: NONE med/x/l | ai_os: NONE med/x/l
agree  med/x/l/../q | shell: NONE med/p/q | ai_os: NONE med/p/q
ai_os probe: 308 agree, 4 differ
D6 check over 3 seeds x 2000 payloads: 6119 JSON texts, 0 with tool_name/cwd/hook_event_name or cwd outside D6
R1 suites: guard differential 734 passed, 0 failed (n 300); AI_DIFF_N=0 now exits 1 ("nothing was compared"); ai-status project root 16 passed, 0 failed; pylint 10.00
```
