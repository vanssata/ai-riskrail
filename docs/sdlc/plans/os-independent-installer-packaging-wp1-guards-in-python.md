# Plan: WP1 — Shared OS module and the guards in Python (refactoring)

Intent: `docs/sdlc/intent/os-independent-installer-packaging.md` · Spec: `docs/sdlc/specs/os-independent-installer-packaging-wp1-guards-in-python.md`

<!-- Stage 3. Concrete, ordered steps the main session executes one at a time. -->

A refactoring (C3). Nothing a guard decides changes. The proof is the unchanged golden file plus the
two differentials (spec D4). WP1 runs as **eight `/ai-task` tasks, WP1.1 to WP1.8**. Each task leaves
the branch green, gets its own review, and ends with the human's approval and commit (C5). `file:line`
marks a fact read at `fea014f`; *est.* marks an estimate.

## Decisions this plan rests on

- **From the spec review:** H1 (the registered entries stay; WP1 ships exec shims), H2 (POSIX classes
  are ASCII), H3 (on budget expiry, the stricter outcome), H4 (frozen shell copies until WP3b).
- **Taken 2026-10-03 at plan time, by the maintainer, via the picker:**
  - **H5:** the human edits the row in `.ai/policies/testing.md:142` after WP1.8 is approved. The text
    is under *After WP1*.
  - **H6:** the shim runs `python3 -I -S`. A task keeps `-S` only if every suite passes with it;
    otherwise it falls back to `-I` and records why.
  - **H7:** a missing interpreter is loud (the shim's `exec` exits 127).
  - **N1:** F6a, F6c and F6e become separate rule-change tasks after WP1.
  - **Split:** WP1 runs as separately reviewed tasks rather than one task.
  - **Budget exclusion:** the byte copies and the recorded corpus are excluded from the diff budget,
    by the human's edit (see *Before WP1.1*).

**Why eight tasks, when seven were chosen.**
- The per-task estimates below sum to about 4,600 counted lines:
  - roughly 1,950 lines of new Python;
  - 1,450 lines of new tests;
  - 1,000 deleted lines of shell;
  - 200 lines of shims, wrappers and edits.
- Not counted:
  - about 3,000 lines of excluded data;
  - `docs/**` and `**/*.md`, which are unbudgeted (`.ai/policies/risk-tiers.json:421-423` with the
    scope at `:450-458`).
- The T3 budget is 250 lines and 10 files per step, and 800 lines and 30 files per task
  (`risk-tiers.json:368-371,394-397`). A task over its budget is re-scored one tier up at every
  `step-done` (`skills/ai-task/sensors.py:515-520`).
- The plan review added the suites the spec requires and the plan had missed, about 250 lines. With
  them, seven tasks would sit at about 800 lines each, at the limit, against estimates of ±30 %.
- Eight tasks leave each one at least 135 lines of headroom. One more approval round is cheaper than a
  re-score to T4, which brings the full pipeline. The cut changes nothing else about the decision.

## Deviations from the spec, made here

1. **`BUDGETED` becomes a mapping** from rule name to its outcome on expiry, and `ere_match` and
   `Ere.captures` take an `on_expiry` argument.
   - The spec's `frozenset` left a budgeted built-in rule, reached through a direct `ere_match`, to
     raise into `main_guard`. That is a silent allow, against H3 (plan review B-5).
   - The outcome is always the stricter one (H3). Each guard task proves it per rule with a unit case.
2. **The whole-guard differential switches a guard by an opt-in table, `PORTED`,** inside the test
   (`absent` / `"file"` / `"all"`), not by whether the `.py` file exists. That way a half-ported guard
   can be tested (plan review B-1).
3. **`install.sh` keeps its `lib/*.sh` globs** after the library is deleted. They match nothing behind
   the `[ -e "$f" ] || continue` guard (`install.sh:627`), and they keep the emergency rollback working
   (plan review B-8). The spec never asked for them to be dropped.

## Before WP1.1 (the human, outside any task)

`.ai/policies/risk-tiers.json` is always protected (`hooks/ai-path-guard-defaults.json:26-37`), so
this edit is yours. Add two entries to `diff_budget.exclude` (`risk-tiers.json:409-420`):

```json
      "tests/fixtures/guard-port/**",
      "tests/fixtures/ere/cases.tsv"
```

This is narrower than the `tests/fixtures/ere/**` named in the question, so no hand-written test data
leaves the budget. The plan review ran these two patterns through the matcher `sensors.py` uses: an
excluded file counts toward neither lines nor files, and is not scope-checked (`sensors.py:467-469`).
Check the file still parses with `python3 -c 'import json; json.load(open(".ai/policies/risk-tiers.json"))'`.

## Files that change

| Path | Change | Task |
|---|---|---|
| `docs/sdlc/intent/os-independent-installer-packaging.md` | edit: the WP1 and WP4a rows follow H1; WP1 is split into WP1.1–WP1.8 | 1.1 |
| `tests/fixtures/guard-port/{ai-git-guard.sh,ai-path-guard.sh,ai-scope-guard.sh,lib/ai-hook-common.sh}` | new: byte copies, the differential's oracle (H4) | 1.1 |
| `tests/test_guard_differential.py`, `tests/test-guard-differential.sh` | new: the whole-guard differential (D4 iii); its `PORTED` table is edited by each guard task | 1.1, 1.5–1.7 |
| `hooks/lib/ai_os.py` | new: the one OS module (O3) | 1.1 |
| `tests/test-ai-status-root.sh` | edit: the reference call `:41-45` and the comment `:9` name `ai_os.find_ai_root` (R14) | 1.1 |
| `tests/run-all.sh` | edit: the literal list (`:11-17`) gains four two-line wrappers | 1.1, 1.2, 1.4 |
| `hooks/lib/ai_ere.py` | new: the ERE translator (1.2); the slow-pattern screen and budget (1.3) | 1.2, 1.3 |
| `tests/test_ere_unit.py`, `tests/test-ere-unit.sh` | new: the translator units (1.2), the cases replay and the R10 tests (1.3) | 1.2, 1.3 |
| `tests/test_pattern_differential.py`, `tests/test-pattern-differential.sh` | new: the engine differential (D4 ii). Its generators and `--record` come in 1.3, the multi-line mode in 1.4, the `[[ == ]]` mode in 1.5, the capture corpora in 1.6 and 1.7 | 1.2–1.7 |
| `tests/fixtures/ere/cases.tsv` | new: 2,000 recorded cases (excluded from the budget) | 1.3 |
| `hooks/lib/ai_hook_common.py` | new: the port of `ai-hook-common.sh`, with the outcomes on expiry | 1.4 |
| `tests/test_guard_port_unit.py`, `tests/test-guard-port-unit.sh` | new: R12 in process; each guard task adds its `main()` cases | 1.4–1.7 |
| `hooks/lib/ai_bashpat.py` | new: bash `[[ == ]]` matching and the pathname expansion | 1.5 |
| `hooks/ai-scope-guard.py`, then `hooks/ai-scope-guard.sh` → shim | port, then cut-over | 1.5 |
| `install.sh` | edit: `:626` gains `"$SRC"/hooks/lib/*.py`; the single `install_file` at `:990` becomes a loop over `lib/*.sh` and `lib/*.py` with `[ -e ] \|\| continue` (1.5); `codex_hook_files` (`:965-973`) gains each guard's `.py` (1.5, 1.6, 1.8) | 1.5, 1.6, 1.8 |
| `hooks/ai-git-guard.py`, then `hooks/ai-git-guard.sh` → shim | port, then cut-over | 1.6 |
| `hooks/ai-path-guard.py` | new: the port, dormant until 1.8 | 1.7 |
| `hooks/ai-path-guard.sh` → shim | cut-over | 1.8 |
| `hooks/lib/ai-hook-common.sh` | deleted (Q11) | 1.8 |
| `tests/test-install-dry-run.sh:168`, `tests/test-codex-install.sh:70-71` | edit: `hooks/lib/ai-hook-common.sh` → `hooks/lib/ai_hook_common.py`; both are `[ -e ]` checks, and no assertion is added, removed or changed (R14) | 1.8 |
| `docs/hook-performance.md` | edit: a measured row per switched guard (1.5, 1.6, 1.8); the Python-port block, and `:182-190` ("where the remaining cost is"), in 1.8 (R19) | 1.5, 1.6, 1.8 |
| `docs/hooks.md:37,49`, `docs/architecture.md:232,239`, `skills/ai-status/SKILL.md:35`, `README.md:554,585` | edit: the references follow the code (R21). `docs/hooks.md` also states the interpreter dependency (see Risk 6) | 1.8 |
| `.ai/project/known-risks.md` | edit: the *Where* lines `:30,39,57` name the `.py` code (`:39`'s `:40` is in fact `:41`); new entries for F6a, F6b, F6c, F6d and F6e, with evidence labels (R21) | 1.8 |

**Untouched.** Checked with `git diff --quiet fea014f -- <files>` at every task's end. This is local
only: CI is a depth-1 clone and cannot see `fea014f` (`.github/workflows/tests.yml:15`).
- `settings.common.json` and `codex/hooks.json` (R2).
- `hooks/ai-git-guard-defaults.json`, `hooks/ai-path-guard-defaults.json` and
  `.ai/policies/path-guard.json` (R18).
- `tests/test-guard-characterization.sh` and `tests/fixtures/guard-characterization/golden.txt` (R1).
- `tests/test-ai-{git,path,scope}-guard.sh` and `tests/test-end-to-end.sh` (F2).
- `skills/ai-task/sensors.py`, whose F6d divergence is recorded, not fixed.

## Order of work

### How each task runs

1. **Before anything is armed**, the session writes the task's steps as JSON into its scratchpad. Once
   the scope guard is armed, it refuses a write outside the project root.
   - There is one object per row.
   - `step_id` is a JSON **string** (`"1"`, `"2b"`); an integer fails `state.py step`
     (`state.py:890-893`).
   - `description` holds the *Step* text plus the *By hand* proofs.
   - `allowed_files` holds *Files*.
   - `required_tests` holds *Tests*.
2. **Plan mode.** The session shows the task's table in plan mode. The human accepting it is the plan
   approval at T3 (`skills/ai-task/SKILL.md:115-130`). The session decides the tier: T3 is expected,
   because a refactoring of shared code is at least T3 (`.ai/workflows/refactoring.md:13-25`).
3. **Record and arm:**

   ```bash
   S="python3 skills/ai-task/state.py"
   $S quick --goal "WP1.<n>: <title>" --workflow refactoring --tier T3 \
            --files "<every Files entry of every step>" --note "refactoring of shared code; plan approved in plan mode"
   $S plan --ref docs/sdlc/plans/os-independent-installer-packaging-wp1-guards-in-python.md --steps <scratchpad>/wp1-<n>.json
   $S step "<id>"      # per row; then the work; then the step's own tests; then:
   $S step-done "<id>"
   ```

4. **`required_tests` holds only paths to bash suites,** such as `tests/test-guard-differential.sh`,
   because `step_test_command` runs `bash "$t"` per entry (`.ai/policies/testing.md:88`).
   - Every other proof is a *By hand* proof: `cmp`, `AI_DIFF_N=5000`, the `uv` runs on 3.11–3.13,
     `strace`, the `--dry-run` diffs, `pylint`.
   - The session runs them and records the output in `.ai/reports/<task-id>/` right after that step's
     `step-done`. Once `step-done` clears the current step, the scope guard is disarmed
     (`state.py:960-961`).
5. **The end of a task:**
   - `$S test-run --scope suite`, which runs `bash tests/run-all.sh` once;
   - `$S test-run --scope e2e`;
   - `$S review-gate`;
   - one STRONG `ai-reviewer`, plus `ai-security` where the task says so (R16);
   - the findings fixed as one batch in a `remediate` step;
   - the human's approval, and `close`.

**Expected red sensors.** Under `--workflow refactoring`, every named suite must pass at the task's
base tree, with `hooks/` reverted (`sensors.py:640-650,994-995`).
- A suite that exercises a module the task itself adds cannot pass there, so the **bite** row is red
  by construction. Each task lists its own.
- At T3 a red row never blocks anything. `review-gate` attaches the rows to the review that runs
  anyway (`state.py:1264-1274`).
- The reviewer inherits these listed rows and does not re-raise them. Any red row **not** listed is a
  finding.
- The **lint** row runs `pylint $(git ls-files '*.py')`, which never sees untracked files
  (`testing.md:89`). So every task runs `pylint --rcfile .pylintrc <its new .py files>` by hand.

**Budget handling.**
- **A step over 250 lines that spans several files** is split with `state.py step-split`.
- **A step on one file cannot be split.** `step-split` moves whole files, and the new step inherits
  the old step's `tree_before` (`state.py:1047-1057`). So the session:
  - stops at a boundary under 250 lines and runs `step-done`;
  - adds a continuation row on the same file;
  - re-registers with `state.py plan`, keeping the done steps' status and diff (SKILL.md:323-326).
- **Forced closes, at T3 only these two:** WP1.8 steps 1 and 2. Each is dominated by deleting a file
  that is byte-identical to its frozen copy (379 and 264 lines), and no step can divide a deletion.
  - First the session runs `step-done` without `--force` and confirms that the only refusal is
    `DIFF_BUDGET_EXCEEDED`. `--force` also skips the scope check (`state.py:937`).
  - Then it runs:

    ```bash
    $S step-done "<id>" --force && $S note decision "step <id> closed with --force" \
       --why "deletion of a file byte-identical to its frozen copy (cmp in WP1.1); a deletion cannot be split"
    ```
  - There is no precedent for this cause. T-2026-09-24-001 forced remediation steps, which is a
    different reason.

**Seam rule.**
- After each `step-done`, the session reads `$S get --field diff.task.lines`.
- If that number plus the estimates of the remaining steps would pass 800, the session:
  - stops at the seam the task marks;
  - runs `$S note decision "seam: steps <ids> move to WP1.<n+1>"`;
  - closes the task normally.
- The moved rows open the next task's JSON, under its own plan-mode approval.

**A T4 triage stops the work.** The session may judge a cut-over task T4: the guards authorise an
agent's actions, and "authorization" is a T4 example (`risk-tiers.json:248-258`). In that case it does
not start the task. T4 means 150 lines and 6 files per step, 400 per task, and `plan_review`
(`risk-tiers.json:276,373-375`). Every step would need re-cutting, so the work returns to
`/sdlc-plan`.

**The live guards are not the source tree.** The session's guards are the installed copies under
`~/.claude/hooks/` and `~/.codex/hooks/`. No task runs `install.sh` against the real `CLAUDE_DIR` or
`CODEX_DIR`; the suites install into scratch directories.

| Task | Content | Counted (*est.*) | Effect on the hook path | Security review |
|---|---|---|---|---|
| WP1.1 | oracle, harness, OS module | ≈560 | none | — |
| WP1.2 | ERE translator, its units, the differential's runner | ≈650 | none | yes: the translator's accept/reject boundary |
| WP1.3 | the engine differential completed; the slow-pattern screen and budget | ≈400 | none | — (reviewed in WP1.4) |
| WP1.4 | the hook library | ≈665 | none | yes: decoding, fail-open, the budget and its alarm, guarded imports |
| WP1.5 | bash-pattern engine; **scope guard ported and switched** | ≈570 | scope guard runs Python | yes: the first live shim, `-I -S` |
| WP1.6 | **git guard ported and switched** | ≈575 | git guard runs Python | — (reviewed in WP1.8) |
| WP1.7 | path guard ported, dormant | ≈520 | none | — (reviewed in WP1.8) |
| WP1.8 | **path guard switched**, shell library retired, measurement, docs | ≈660 counted, plus docs | no shell guard logic left | yes: the whole port against F7 |

**The riskiest step is WP1.7 step 2, the path guard's Bash branch.** It has:
- the joined pre-filter;
- the loose forms;
- the C-sorted token scan;
- `ln_re`;
- the most rules and the most decisions.

It cannot move earlier, because it needs every library. So it is split from its cut-over: it is
proven dormant, against the frozen shell, before WP1.8 puts it on the hook path. The scope guard
switches first (WP1.5) because it is the smallest, and its cut-over proves cheaply:
- the shim;
- the install copies;
- the installed Codex copy that `tests/test-end-to-end.sh:112-114` runs.

### WP1.1 — Oracle, harness and the OS module (no effect on the hook path)

| Id | Step | Files | Tests | *est.* |
|---|---|---|---|---|
| 1 | Amend the intent. The WP1 row drops "the hook command lines" and "the upgrade of existing entries", and names the shims and the split into WP1.1–WP1.8. The WP4a row gains the command-line switch, O30's de-duplicating upgrade and the stale-file removal (H1). | `docs/sdlc/intent/os-independent-installer-packaging.md` | — | docs |
| 2 | Freeze the four shell files with `cp`, keeping `lib/` beside the guards. **By hand:** `cmp` each copy against its source. | `tests/fixtures/guard-port/` | — | 0 (excluded) |
| 3 | The harness of `test_guard_differential.py`: <ul><li>it rebuilds the characterization tree (`tests/test-guard-characterization.sh:44-89`) in Python, plus a symlinked project;</li><li>a scratch `HOME` and a scratch `hooks/` holding the current `*-defaults.json`;</li><li>`LC_ALL=C`; it compares rc, stdout and stderr bytes;</li><li>the `PORTED` table (all absent for now) decides, per guard and payload class (`file`, `bash`), whether `hooks/ai-<g>-guard.py` runs against its frozen copy, or the frozen copy runs against itself;</li><li>a `.py` guard runs with R3's jq-less `PATH`: a scratch `bin/` holding only `python3` and `git` symlinks;</li><li>a 10 % sample also runs the source-tree `.sh` under the normal `PATH`;</li><li>without bash or jq it skips with one line.</li></ul>Add the two-line wrapper and the `run-all.sh` entry. | `tests/test_guard_differential.py`, `tests/test-guard-differential.sh`, `tests/run-all.sh` | `tests/test-guard-differential.sh` | ≈220 |
| 4 | The payload grammar of D4 iii: <ul><li>verbs × flags × paths, with `..`, symlinks, missing files and `=`-tokens;</li><li>quoting, `;&\|()<>`, heredocs, backslash-newline and multi-line commands;</li><li>the file tools × their path fields;</li><li>`apply_patch` headers and `shell` arrays;</li><li>malformed input: concatenated JSON, non-string fields, `false`/`null`;</li><li>the state variants, spelled out: each stage, duplicate step ids, an unparsable `.ai/state/current.json`.</li></ul>No numbers inside a non-string `command`, because jq's version decides their form (D6). The seed comes from `AI_DIFF_SEED` (default `20261003`) and is printed; `AI_DIFF_N` defaults to 300. **By hand:** one run with `AI_DIFF_N=2000`. | `tests/test_guard_differential.py` | `tests/test-guard-differential.sh` | ≈200 |
| 5 | `hooks/lib/ai_os.py` per the spec's interface: `runtime_home`, `hook_config_dirs`, `logical_cwd`, `resolve_dir`, `find_ai_root` (including the `/` case), `abs_path`, `real_path`, and `run_git` (an argument list, `-C cwd`, no shell, `subprocess` imported lazily). It starts with `from __future__ import annotations`. The reference call in `tests/test-ai-status-root.sh:41-45` becomes `python3 -I -S` importing `ai_os` and printing `find_ai_root($PWD)`, or an empty line, as the shell did. The comment at `:9` names `hooks/lib/ai_os.py`. Every assertion stays as it is. | `hooks/lib/ai_os.py`, `tests/test-ai-status-root.sh` | `tests/test-ai-status-root.sh` | ≈140 |

**Expected red:** bite on `tests/test-ai-status-root.sh`, because `ai_os` is absent at the base.

**Done when:**
- the old-vs-old differential and the status-root suite are green;
- `run-all.sh` and e2e are green;
- the four `cmp`s and the seed are in the report.

This order is C2's characterization first.

### WP1.2 — ERE translator and the differential's runner (no effect on the hook path)

| Id | Step | Files | Tests | *est.* |
|---|---|---|---|---|
| 1 | `ai_ere.py`, the parser: tokens and bracket expressions per D3. <ul><li>`[[:class:]]` is an ASCII set; `[[:space:]]` is `[ \t\n\v\f\r]`.</li><li>A backslash inside brackets is literal.</li><li>`[]a]`, `[^]a]` and a trailing `-` are handled.</li><li>Single-character `[[=c=]]` and `[[.c.]]` are accepted.</li><li>Bad ranges and unknown classes raise `EreError`.</li></ul>`test_ere_unit.py` starts with the parser cases. Add its wrapper and the `run-all.sh` entry. | `hooks/lib/ai_ere.py`, `tests/test_ere_unit.py`, `tests/test-ere-unit.sh`, `tests/run-all.sh` | `tests/test-ere-unit.sh` | ≈230 |
| 2 | `ai_ere.py`, `translate` and `compile`: <ul><li>the GNU escapes under `re.ASCII`;</li><li>back-references `\1`–`\9`;</li><li>`a+?` and `a*?` become `(?:a+)?`;</li><li>a lone `)` is literal;</li><li>the invalid forms compile to `None`, which never matches: a leading `*`, `+` or `?`, `(?`, a bad interval, a trailing `\`, an unmatched `(` or `[`;</li><li>the `{` cases are left to the oracle;</li><li>a cache per process;</li><li>`Ere.search` and `Ere.captures`.</li></ul>Unit cases for each, including the invalid forms (R6, unit part). | `hooks/lib/ai_ere.py`, `tests/test_ere_unit.py` | `tests/test-ere-unit.sh` | ≈200 |
| 3 | `test_pattern_differential.py`, the oracle and the runner. <ul><li>One long-lived bash per locale (`C`, `C.UTF-8`) reads `pattern\tsubject` and answers through `[[ =~ ]]`.</li><li>The declared-divergence list (D6) lives inside the test.</li><li>A failure names the pattern, the subject, both verdicts and the seed.</li><li>For now it covers the defaults files' strings over the characterization corpus.</li></ul>Add the wrapper and the `run-all.sh` entry. | `tests/test_pattern_differential.py`, `tests/test-pattern-differential.sh`, `tests/run-all.sh` | `tests/test-pattern-differential.sh` | ≈220 |

**Expected red:** bite on `tests/test-ere-unit.sh` and `tests/test-pattern-differential.sh`.

**Security review** on the translator's accept/reject boundary (F7). Accepting more creates new
denies. Rejecting more silently drops a deny rule.

### WP1.3 — The engine differential completed; the slow-pattern screen and budget

| Id | Step | Files | Tests | *est.* |
|---|---|---|---|---|
| 1 | The generators. **Patterns:** <ul><li>every string in both defaults files, with the protected branches wrapped `^…$` as at `ai-git-guard.sh:98`;</li><li>the joined and loose forms of each list (`ai-hook-common.sh:259-264`, `ai-path-guard.sh:82-89`);</li><li>about 150 hand-written construct snippets for D3;</li><li>five one-character mutations per pattern;</li><li>**every built-in `RULES` entry of each guard whose `.py` exists**, imported by the test (B-4).</li></ul>**Subjects:** the characterization corpus, plus seeded strings of length 0–40. `AI_DIFF_N` defaults to 200. **By hand:** both locales, zero undeclared divergences, under 60 s. | `tests/test_pattern_differential.py` | `tests/test-pattern-differential.sh` | ≈150 |
| 2 | `--record` samples 2,000 cases into `cases.tsv`; `test_ere_unit.py` replays them without bash. | `tests/test_pattern_differential.py`, `tests/fixtures/ere/cases.tsv`, `tests/test_ere_unit.py` | `tests/test-ere-unit.sh` | ≈60 |
| 3 | The slow-pattern screen and budget (D5): <ul><li>`ai_ere.is_risky`, a static screen over the AST;</li><li>a budgeted search and budgeted captures: `signal.setitimer(ITIMER_REAL)` in the main thread, the handler raises `MatchBudgetExceeded`, and the timer is cleared in `finally`. Without `setitimer`, there is no budget (WP4b);</li><li>`AI_GUARD_MATCH_BUDGET_MS`: a missing or invalid value means 500.</li></ul>**R10 units:** `(a+)+$` over `"a"*34+"b"` returns within budget + 100 ms; no alarm is still pending after a match. **The long-subject corpus (B-6):** every shipped pattern and its joined and loose forms over 1, 20, 60 and 200 KB subjects, with the budget active, compared with bash. Any pattern that expires where glibc does not is recorded for WP1.8's `known-risks.md` entry. **By hand:** `uv run --offline --no-project --python 3.11 bash tests/test-ere-unit.sh`, and the same for 3.12 and 3.13. | `hooks/lib/ai_ere.py`, `tests/test_ere_unit.py`, `tests/test_pattern_differential.py` | `tests/test-ere-unit.sh`, `tests/test-pattern-differential.sh` | ≈190 |

**Expected red:** bite on `tests/test-ere-unit.sh`, because `is_risky` is absent at the base.

**Done when:**
- both locales show zero undeclared divergences over the full pattern set (R5);
- every glibc-rejected pattern, joined form and loose form never matches (R6);
- the long-subject results are in the report.

**If the long-subject corpus shows a shipped pattern expiring on a subject of 20 KB or less, the
task stops and asks.** H3 would then turn today's allow into a deny on ordinary input. That needs a
decision, not a workaround.

### WP1.4 — The hook library (no effect on the hook path)

| Id | Step | Files | Tests | *est.* |
|---|---|---|---|---|
| 1 | `ai_hook_common.py`, part 1: <ul><li>`read_payload`: bytes, UTF-8 with `replace`, lone surrogates → U+FFFD (R20); a `raw_decode` loop that reproduces jq's fast `[inputs]` path (`ai-hook-common.sh:49-61`) and its SLOW fallback (`:62-65`); exit 0 on empty or unparsable input;</li><li>`Payload` and the tool map (`:75-79`);</li><li>`chomp_all`, `jq_r`, `bash_command`, `patch_paths` (`:116-119`), `target_paths` (`:122-129`);</li><li>`runtime_hook_config` through `ai_os.hook_config_dirs`;</li><li>`json_strings`.</li></ul>`test_guard_port_unit.py` starts with these cases. Add its wrapper and the `run-all.sh` entry. | `hooks/lib/ai_hook_common.py`, `tests/test_guard_port_unit.py`, `tests/test-guard-port-unit.sh`, `tests/run-all.sh` | `tests/test-guard-port-unit.sh` | ≈245 |
| 2 | Part 2: <ul><li>`ere_escape`;</li><li>`strip_prose` (`:148-169`, including the `<<` / `-m` pre-check);</li><li>`ere_match` with R7's line semantics (`:227-238`);</li><li>`matches_any`;</li><li>`matches_joined`: one ERE built by `"\|".join`, never an OR of compiled parts, so F6a is reproduced;</li><li>`encode_deny`: compact, raw UTF-8, `\u007f` escaped, as `jq -nc`;</li><li>`deny`, `allow`, and `main_guard`: stdout reconfigured to UTF-8 and `\n`, and any exception becomes exit 0 with no output.</li></ul>Unit cases for each. | `hooks/lib/ai_hook_common.py`, `tests/test_guard_port_unit.py` | `tests/test-guard-port-unit.sh` | ≈240 |
| 3 | The outcomes on expiry (H3, deviation 1): <ul><li>`matches_any`, `matches_joined`, `ere_match` and captures take `on_expiry`;</li><li>a deny-kind list counts as matched, with the reason suffix `(matched: <pattern>; matching exceeded <N> ms)`;</li><li>an allow list counts as not matched;</li><li>the joined pre-filter counts as interesting.</li></ul>**Guarded imports (B-9):** a guard's top level is only `from __future__ import annotations`, the `sys.path` insertion and an import inside `try`, so a broken or partial `lib/` still ends in exit 0 with no output. R12 in process: random bytes, concatenated JSON, 1 MiB, NUL bytes, lone surrogates, non-string fields. `encode_deny` is compared with `jq -nc` over a generated string corpus, and skipped without jq. The multi-line mode of the engine differential compares `ai_hook_common.ere_match` with the frozen `ere_match`, sourced from `tests/fixtures/guard-port/lib/ai-hook-common.sh` (R7). **By hand:** `uv run --offline --no-project --python 3.11 bash tests/test-guard-port-unit.sh`. | `hooks/lib/ai_hook_common.py`, `tests/test_guard_port_unit.py`, `tests/test_pattern_differential.py` | `tests/test-guard-port-unit.sh`, `tests/test-pattern-differential.sh` | ≈180 |

**Expected red:** bite on `tests/test-guard-port-unit.sh` and `tests/test-pattern-differential.sh`.

**Security review** of WP1.3 and WP1.4 together:
- the decode with `replace`, and lone surrogates;
- the fail-open wrapper and the guarded imports;
- the budget alarm not leaking into the next match;
- `AI_GUARD_MATCH_BUDGET_MS`, which comes from the runtime's environment;
- R12's coverage, as the only defence against silent allows.

### WP1.5 — Bash-pattern engine; scope guard ported and switched

| Id | Step | Files | Tests | *est.* |
|---|---|---|---|---|
| 1 | `ai_bashpat.match`: bash `[[ == ]]` with extglob on and `nocasematch`, `globstar` and `dotglob` off. Add the `[[ == ]]` mode of the engine differential over plan globs: the scope fixtures plus generated extglob. | `hooks/lib/ai_bashpat.py`, `tests/test_pattern_differential.py` | `tests/test-pattern-differential.sh` | ≈170 |
| 2 | `ai_bashpat.expand_words`: split on space, tab and newline, then expand each word against `cwd`: C-sorted, dotfiles excluded, an unmatched word kept literal. Compare it with bash's unquoted expansion in a scratch tree. | `hooks/lib/ai_bashpat.py`, `tests/test_pattern_differential.py` | `tests/test-pattern-differential.sh` | ≈90 |
| 3 | `hooks/ai-scope-guard.py`, a one-to-one port: <ul><li>arming at `ai-scope-guard.sh:12,30,61-71`;</li><li>matching with the `$dir/*` rule at `:77-98`;</li><li>forbidden before allowed at `:105-122`;</li><li>the deny message's `$ALLOWED` through `expand_words`, so F6c is reproduced (R8);</li><li>`RULES`, `BUDGETED` and `main()`.</li></ul>`PORTED["scope"] = "all"`. Add the R12 `main()` cases, including an unparsable `current.json` and the shim run against an empty `lib/`. | `hooks/ai-scope-guard.py`, `tests/test_guard_differential.py`, `tests/test_guard_port_unit.py` | `tests/test-guard-differential.sh`, `tests/test-guard-port-unit.sh` | ≈180 |
| 4 | **Cut-over.** <ul><li>`hooks/ai-scope-guard.sh` becomes the spec's shim: at most 6 lines, one `exec python3 -I -S`.</li><li>`install.sh`: `:626` gains `"$SRC"/hooks/lib/*.py`; `:990` becomes a loop over `"$SRC"/hooks/lib/*.sh` and `"$SRC"/hooks/lib/*.py` with `[ -e "$f" ] \|\| continue`; `codex_hook_files` gains `hooks/ai-scope-guard.py`.</li></ul> | `hooks/ai-scope-guard.sh`, `install.sh` | `tests/test-guard-characterization.sh`, `tests/test-ai-scope-guard.sh`, `tests/test-install-dry-run.sh`, `tests/test-codex-install.sh`, `tests/test-dual-runtime-install.sh` | ≈140 |
| 5 | Measure and log. **By hand:** <ul><li>the `strace` recipe (`docs/hook-performance.md:151-160`): at most 3 successful `execve` through the shim;</li><li>wall clock over 40 runs, written beside the 2026-09-20 rows (`:54-70`);</li><li>one `AI_DIFF_N=5000` differential run, with its seed (R15);</li><li>`install.sh --dry-run` into scratch directories, before against after: only the hook listing differs (R13);</li><li>H6: the suites with and without `-S`.</li></ul> | `docs/hook-performance.md` | — | docs |

**Expected red:** bite on `tests/test-pattern-differential.sh`, `tests/test-guard-differential.sh`
and `tests/test-guard-port-unit.sh`. The cut-over's suites pass at the base, and that is the
refactoring proof.

**Done when:**
- the golden is unchanged through the shim (R1);
- the scope suite and e2e are green; e2e runs the installed Codex shim (`tests/test-end-to-end.sh:112-114`);
- the measured row is within the budget table (R11).

**Security review:**
- the first live shim: `-I -S` and the explicit `sys.path` entry, so no `PYTHONPATH` and no user site;
- the fail-open path, now on the hook path;
- `ai_bashpat.expand_words` touching the file system.

### WP1.6 — Git guard ported and switched

| Id | Step | Files | Tests | *est.* |
|---|---|---|---|---|
| 1 | `hooks/ai-git-guard.py`, part 1: <ul><li>`LIST_KEYS` (`ai-git-guard.sh:48`) and the pattern lists;</li><li>the protected branches wrapped `^…$` (`:98`);</li><li>the git calls of `:78,89,139` through `ai_os.run_git`.</li></ul>`git_subcommand` (`:103-105`) is dead code and is not ported. Unit cases for these helpers. | `hooks/ai-git-guard.py`, `tests/test_guard_port_unit.py` | `tests/test-guard-port-unit.sh` | ≈130 |
| 2 | Part 2: <ul><li>the rules in source order, with `refspec_re` captures (`:169-173`);</li><li>`RULES` and `BUDGETED`, with each budgeted rule's outcome on expiry (deviation 1) and a unit case per rule;</li><li>`main()` and its R12 cases.</li></ul>`PORTED["git"] = "all"`. | `hooks/ai-git-guard.py`, `tests/test_guard_differential.py`, `tests/test_guard_port_unit.py` | `tests/test-guard-differential.sh`, `tests/test-guard-port-unit.sh` | ≈150 |
| 3 | The `refspec_re` capture corpus: at least 1,000 generated lines, in a captures mode of the engine differential. If POSIX subexpression rules diverge, a hand-written extractor replaces the regex in the guard (D3). | `tests/test_pattern_differential.py`, `hooks/ai-git-guard.py` | `tests/test-pattern-differential.sh` | ≈70 |
| 4 | **Cut-over.** `hooks/ai-git-guard.sh` becomes the shim; `codex_hook_files` gains `hooks/ai-git-guard.py`. | `hooks/ai-git-guard.sh`, `install.sh` | `tests/test-guard-characterization.sh`, `tests/test-ai-git-guard.sh`, `tests/test-codex-install.sh` | ≈225 |
| 5 | Measure and log, as in WP1.5 step 5, for the git rows. The process count is at most 3, plus one per git call where a rule asks git today (R11). | `docs/hook-performance.md` | — | docs |

**Expected red:** bite on `tests/test-guard-port-unit.sh`, `tests/test-guard-differential.sh` and
`tests/test-pattern-differential.sh`.

### WP1.7 — Path guard ported, dormant (the riskiest port)

| Id | Step | Files | Tests | *est.* |
|---|---|---|---|---|
| 1 | `hooks/ai-path-guard.py`, part 1: <ul><li>`load_pattern_lists`: unique, sorted by `(tag, rest)` in code-point order (`ai-path-guard.sh:63-71`, R9);</li><li>`task_in_flight`, read only on demand (`:111-123`);</li><li>the `find_ai_root` gate (`:41`);</li><li>the branch for the file tools.</li></ul>`PORTED["path"] = "file"`. | `hooks/ai-path-guard.py`, `tests/test_guard_differential.py` | `tests/test-guard-differential.sh` | ≈200 |
| 2 | **The riskiest step.** Part 2, the Bash branch: <ul><li>the joined pre-filter (`:132`, `ai-hook-common.sh:259-264`), so F6a is reproduced;</li><li>the loose forms (`:82-89`), so F6b is reproduced;</li><li>the C-sorted token scan (`:319-327,338-344`);</li><li>`ln_re` (`:350-354`);</li><li>`APPROVE_RE`, `HOOKRUN_RE` and `CONFIRM_RE`, with their outcomes on expiry.</li></ul>`PORTED["path"] = "all"`. **By hand:** one `AI_DIFF_N=5000` run. | `hooks/ai-path-guard.py`, `tests/test_guard_differential.py` | `tests/test-guard-differential.sh` | ≈210 |
| 3 | <ul><li>The `ln_re` capture corpus, at least 1,000 lines.</li><li>The R12 `main()` cases, including an unparsable `current.json`.</li><li>A unit case for each `BUDGETED` outcome.</li><li>The long-subject corpus over the path rules.</li></ul>**By hand:** the `CONFIRM_RE` case of `.ai/project/known-risks.md:54-61` (a 120 KB padded line), measured in the port (R10). | `tests/test_pattern_differential.py`, `tests/test_guard_port_unit.py`, `hooks/ai-path-guard.py` | `tests/test-pattern-differential.sh`, `tests/test-guard-port-unit.sh` | ≈110 |

**Expected red:** bite on `tests/test-guard-differential.sh`, `tests/test-pattern-differential.sh`
and `tests/test-guard-port-unit.sh`.

**Done when** the frozen path guard and `hooks/ai-path-guard.py` agree over the default run and one
5,000-payload run, and the source-tree `.sh` is still the full shell guard.

### WP1.8 — Path guard switched, shell library retired, measurement and docs

| Id | Step | Files | Tests | *est.* |
|---|---|---|---|---|
| 1 | **Cut-over, forced close.** `hooks/ai-path-guard.sh` becomes the shim; `codex_hook_files` gains `hooks/ai-path-guard.py`. | `hooks/ai-path-guard.sh`, `install.sh` | `tests/test-guard-characterization.sh`, `tests/test-ai-path-guard.sh`, `tests/test-codex-install.sh` | ≈385 |
| 2 | **Retire the shell library, forced close.** <ul><li>Delete `hooks/lib/ai-hook-common.sh`. `install.sh` is not touched, because its `lib/*.sh` globs now match nothing (deviation 3).</li><li>A copy already installed stays in place (R13; O30 is WP4a).</li><li>Change the file names at `tests/test-install-dry-run.sh:168` and `tests/test-codex-install.sh:70-71` (R14).</li></ul> | `hooks/lib/ai-hook-common.sh`, `tests/test-install-dry-run.sh`, `tests/test-codex-install.sh` | `tests/test-install-dry-run.sh`, `tests/test-codex-install.sh`, `tests/test-dual-runtime-install.sh` | ≈270 |
| 3 | Docs (R19, R21): <ul><li>`docs/hook-performance.md`: the Python-port block; the process model with and without the shim; the slow-pattern rule and the long-subject results; "ctypes libc engine" under *deliberately not done* (`:165-179`); `:182-190` rewritten.</li><li>`docs/hooks.md:37,49`, which also states the interpreter dependency (Risk 6).</li><li>`docs/architecture.md:232,239`.</li><li>`skills/ai-status/SKILL.md:35`, which keeps the name `find_ai_root` (`tests/test-ai-status-root.sh:23`).</li><li>`README.md:554,585`, naming `hooks/ai-path-guard.py`.</li><li>`.ai/project/known-risks.md`: the *Where* lines `:30,39,57`, and the F6a, F6b, F6c, F6d and F6e entries, plus any long-subject expiry.</li></ul> | `docs/hook-performance.md`, `docs/hooks.md`, `docs/architecture.md`, `skills/ai-status/SKILL.md`, `README.md`, `.ai/project/known-risks.md` | `tests/test-ai-status-root.sh` | docs |
| 4 | Final proof. **By hand:** <ul><li>measure all three rows (R11);</li><li>one `AI_DIFF_N=5000` run over all three guards, with its seed (R15);</li><li>every command of *Proof*.</li></ul> | `docs/hook-performance.md` | — | docs |

**Done when** every row of *Proof* is green.

**Security review** over the whole port, against the full F7 checklist. It includes:
- `run_git`, now live since WP1.6;
- the writability of `hooks/lib/` (F6e), including `hooks/lib/__pycache__/` (B-11);
- the guarded imports;
- `AI_GUARD_MATCH_BUDGET_MS`.

## Risks

**What could this break?**

1. **A silent allow.** Fail-open turns any exception into exit 0 with no output.
   - *Notice:* R12's in-process tests, the two differentials, and the golden for known cases.
   - *Mitigation:*
     - every guard's `main()` is fuzzed in process;
     - the whole-guard differential runs in every `run-all.sh`;
     - a 5,000-payload run is logged at each cut-over;
     - the guarded imports turn a broken `lib/` into the same contract.
2. **A rule silently dropped by the translator.** A pattern the translator rejects but glibc accepts
   never matches.
   - *Notice:* the engine differential flags it as an undeclared divergence, including over every
     built-in `RULES` entry (WP1.3), and WP1.2's security review checks the boundary.
3. **Allow turned to deny on long input (B-6).** Python's `re` is quadratic where glibc is linear, even
   on a plain pattern. The plan review measured `.*\.(sql|sql\.gz)$` over 50 KB without a dot at
   0.593 s, against 0.001 s in bash.
   - If the screen budgets such a pattern, H3 denies a long token that glibc allows today.
   - If it does not, the match is unbounded.
   - *Notice:* WP1.3's long-subject corpus. At 20 KB or less, the task stops and asks.
4. **A shim that loads the wrong code.** `PYTHONPATH` or the user site could inject a module.
   - *Mitigation:* `-I -S` and the explicit `sys.path` entry (H6), reviewed in WP1.5.
   - *Fallback:* `-I` alone, with the reason recorded.
5. **A planted bytecode file (B-11).** Bytecode caching (D2) creates `~/.{claude,codex}/hooks/lib/__pycache__/`,
   which no guard protects today. The N1 follow-up for F6e therefore protects the whole `lib/`
   subtree. Reviewed in WP1.8.
6. **The interpreter becomes part of the guard (B-9).**
   - Before WP1, the decisions depend on bash and jq. After WP1, they depend on the `python3` the hook
     process resolves from its `PATH`: a pyenv shim, a virtualenv, its version.
   - `install.sh:80-81` checks only that it exists; the 3.11 check is WP4b's.
   - A missing interpreter is loud (H7). A broken `lib/` is silent (the guarded imports). An
     interpreter so old that it cannot parse the guard fails loud, with rc 1 and a traceback.
   - Declared in `docs/hooks.md` (WP1.8).
7. **Latency.** The estimate is about 25–35 ms, against 62–112 ms measured today (spec D7), and it is
   measured at every cut-over. If a row is over budget, the task stops before approval and asks.
8. **Locale.** Under a UTF-8 hook locale, a deny may name a different pattern that matches equally
   well (F4, H2, D6). The decision is the same; the message can differ.
9. **Python version.** This machine runs 3.14; the floor is 3.11.
   - The unit suites run under `uv` 3.11–3.13. The plan review confirmed they work offline here.
   - CI `pylint.yml` checks 3.11–3.13, but `tests.yml` runs the suites on 3.12 only
     (`.github/workflows/tests.yml:16-20`). A matrix is WP4b's.
10. **The jq version in the oracle.** jq here is 1.8.1; the version in CI is UNKNOWN. The grammar
    keeps numbers out of a non-string `command` (D6).
11. **The timing test can flake** on a loaded CI runner. A miss on the R10 bound (budget + 100 ms) is
    classified as a test-environment failure. It is never retried silently.
12. **A mixed tree between tasks.** From WP1.5, some guards are Python and some are shell. Every such
    state is green and proven. A merge to `main` is recommended only after WP1.8 (OQ24).
13. **The installed copies.** The stale `~/.claude/hooks/lib/ai-hook-common.sh` stays where it is,
    and nothing sources it (R13; O30 is WP4a). The registered entries never change, so Codex keeps its
    trust (`install.sh:1001-1013`, D1).

**Which step is the riskiest, and can it move earlier?** WP1.7 step 2, the path guard's Bash branch.
It cannot move earlier, because it needs every library. It is split from its cut-over instead.

**The estimates are ±30 %.** The seam rule absorbs that: a seam ends a task early. A re-score is never
accepted silently.

**Policy text found inconsistent (documented, not fixed; C1):**
- `refactoring.md:20` asks for an `ai-reviewer` plan review "always", while solo T3 has the human
  approve the plan in plan mode (`skills/ai-task/SKILL.md:115-130,293`). This plan had an adversarial
  review before hand-off (*Plan review*), which covers both.
- `testing.md:81-82` says `verify_command` excludes e2e, but `:132` and `run-all.sh:13` include it.
  The extra e2e run is redundant but harmless.
- `testing.md:150` names `.github/workflows/test.yml`; the file is `tests.yml` (F8).

## Proof (tests)

Each row says where the requirement is first green. It stays green in every later task.

| Req | Proof | Task |
|---|---|---|
| R1 | `tests/test-guard-characterization.sh` green through each shim; `P-R1` below | 1.5, 1.6, 1.8 |
| R2 | `P-R2` below, for each **switched** guard's `.sh`; `git diff --quiet fea014f -- settings.common.json codex/hooks.json` | 1.5, 1.6, 1.8 |
| R3 | the whole-guard differential runs each `.py` guard with `PATH` holding only `python3` and `git`; `P-R3` as a secondary check (the library may *name* jq, as in `jq_r`, but never runs it) | 1.1 harness, 1.8 |
| R4 | `P-R4` below prints nothing | every task |
| R5 | `tests/test-pattern-differential.sh` under `C` and `C.UTF-8`, zero undeclared divergences, the built-in `RULES` included | 1.3 |
| R6 | the mutation corpus, the joined forms and the loose forms in the engine differential; the invalid-form units in `tests/test-ere-unit.sh` | 1.2, 1.3 |
| R7 | the multi-line mode against the frozen `ere_match` | 1.4 |
| R8 | the `[[ == ]]` and expansion modes; the scope slice of the whole-guard differential, over tree files that match plan globs | 1.5 |
| R9 | the golden, plus the whole-guard differential (C-sorted messages) | 1.5–1.8 |
| R10 | `tests/test-ere-unit.sh` under `uv` 3.11, 3.12 and 3.13; one outcome unit per `BUDGETED` rule; the long-subject corpus; the `CONFIRM_RE` 120 KB measurement in the report | 1.3, 1.6, 1.7 |
| R11 | the `strace` recipe and the 40-run wall clock per row, in `docs/hook-performance.md` | 1.5, 1.6, 1.8 |
| R12 | `tests/test-guard-port-unit.sh`, in process, including an unparsable `current.json` and an empty `lib/` | 1.4–1.7 |
| R13 | the install suites; the `--dry-run` diff before against after (only the hook listing); a scratch install over an old tree keeps `hooks/lib/ai-hook-common.sh` | 1.5, 1.8 |
| R14 | `P-R14` below: only `run-all.sh`, `test-ai-status-root.sh`, `test-install-dry-run.sh` and `test-codex-install.sh` are modified; the reviewer confirms that no assertion changed | 1.8 |
| R15 | `run-all.sh` runs the whole-guard differential at `AI_DIFF_N=300`; one logged `AI_DIFF_N=5000` run per cut-over and one at the end, seeds in the reports | 1.5, 1.6, 1.8 |
| R16 | the `ai-security` reports of WP1.2, WP1.4 (covering WP1.3), WP1.5 and WP1.8 (the full F7) | 1.2–1.8 |
| R17 | CI `pylint.yml` (3.11, 3.12, 3.13) at 10.00; `P-R17` below at every task's end | every task |
| R18 | `git diff --quiet fea014f -- hooks/ai-git-guard-defaults.json hooks/ai-path-guard-defaults.json .ai/policies/path-guard.json` | every task |
| R19 | the `docs/hook-performance.md` block, checked in the WP1.8 review | 1.8 |
| R20 | the decode units in `tests/test-guard-port-unit.sh`; a deny printed under `LC_ALL=C` is UTF-8 with `\n` | 1.4 |
| R21 | `P-R21` below prints nothing; `tests/test-ai-status-root.sh` | 1.8 |

The commands, outside the table, so that no `|` is escaped. They are local only, because CI is a
depth-1 clone:

```bash
# P-R1
git diff --quiet fea014f -- tests/test-guard-characterization.sh tests/fixtures/guard-characterization/golden.txt
# P-R2 (per switched guard)
for f in hooks/ai-scope-guard.sh hooks/ai-git-guard.sh hooks/ai-path-guard.sh; do   # only the ones switched so far
  [ "$(wc -l < "$f")" -le 6 ] && [ "$(grep -Evc '^\s*(#|$)' "$f")" -eq 2 ] && [ "$(grep -c '^exec ' "$f")" -eq 1 ] \
    && echo "ok $f" || echo "FAIL $f"
done
# P-R3 (secondary)
grep -nE "[\"']jq[\"']|which\(.jq|shutil\.which" hooks/ai-*-guard.py hooks/lib/*.py
# P-R4
grep -nE 'HOME|expanduser|CLAUDE_CONFIG_DIR|CODEX_HOME|PWD|getcwd|realpath|subprocess' hooks/ai-*-guard.py hooks/lib/*.py \
  | grep -v '^hooks/lib/ai_os.py:'
# P-R14
git diff --stat fea014f -- tests/ ; git diff --name-status fea014f -- tests/ | grep -v '^A'
# P-R17
pylint --rcfile .pylintrc hooks/ai-*-guard.py hooks/lib/*.py tests/test_*.py
uvx --offline --python 3.11 pylint --rcfile .pylintrc hooks/ai-*-guard.py hooks/lib/*.py tests/test_*.py
grep -hE '^(import|from) ' hooks/lib/*.py hooks/ai-*-guard.py | sort -u     # read against the stdlib
# P-R21
grep -rn 'ai-hook-common' docs/hooks.md docs/architecture.md skills/ai-status/SKILL.md .ai/project/known-risks.md README.md
```

## Rollback

- **Before merge, per task.** Revert that task's commits on `feature/installer`.
  - A dormant task (WP1.1–1.4, WP1.7) changes nothing on the hook path, so its revert only removes
    code.
  - A cut-over (WP1.5, 1.6, 1.8) reverts to the full shell guard, because the shim is the one file
    that switched.
- **After merge.** Revert the merge commit and re-run `install.sh`. The `.sh` files are overwritten
  with the full shell guards. The registered entries never changed, so neither runtime needs to
  re-register or re-trust anything. Stale `.py` files in the install roots are referenced by nothing.
- **Emergency, without git.**
  - Copy `tests/fixtures/guard-port/*.sh` over `hooks/`, and `tests/fixtures/guard-port/lib/ai-hook-common.sh`
    into `hooks/lib/`. They are byte-identical to `fea014f`, as WP1.1's `cmp` proved.
  - Re-run `install.sh`. Its `lib/*.sh` globs, kept by deviation 3, install the library into both
    roots again.
- **No migration, no data.** Nothing in `.ai/state` or `.ai/reports` changes format.

## After WP1 (the human)

1. **H5.** Edit `.ai/policies/testing.md:142` to read:

   ```
   | `hooks/ai-*-guard.sh`, `hooks/ai-*-guard.py`, `hooks/lib/*.py` | `tests/test-ai-path-guard.sh`, `tests/test-ai-scope-guard.sh`, `tests/test-ai-git-guard.sh`, `tests/test-guard-characterization.sh`, `tests/test-pattern-differential.sh`, `tests/test-guard-differential.sh`, `tests/test-ere-unit.sh`, `tests/test-guard-port-unit.sh` |
   ```

2. **N1.** Open three rule-change tasks, each with a golden re-record:
   - F6e: the additive pattern `(^|/)\.(claude|codex)/hooks/lib/`, a prefix that also covers
     `__pycache__/`;
   - F6a: one invalid project pattern disables the joined pre-filter;
   - F6c: the unquoted `$ALLOWED`.
3. **Release.** Merge after WP1.8 (OQ24). Under H1, WP1 can ship without WP4a.
4. **Next packages.**
   - WP3a's runner replaces the four two-line wrappers (F9).
   - WP4a switches the command lines and removes stale files.
   - WP3b retires `tests/fixtures/guard-port/`.
   - WP4b brings the 3.11 check, the Windows budget mechanism and the CI matrix.

## Plan review

An adversarial review ran on 2026-10-03, before hand-off, through the workflow `wp1-plan-review`. It
had three independent lenses, and each verified its findings by reading the repository and, where
possible, by executing:
- *pipeline* (STRONG): 12 findings;
- *behaviour and spec completeness* (STRONG): 15 findings;
- *citation accuracy* (BALANCED): 12 findings.

That is 39 findings: 1 BLOCKER, 22 MAJOR and 16 MINOR. All were accepted, duplicates were merged, and
they were fixed in one batch.

| Finding | Fixed in |
|---|---|
| B-1 BLOCKER: the half-ported path guard against a presence-switched harness | deviation 2 (`PORTED` table); WP1.7 steps 1–2 |
| P-1: how a task is armed in solo T3 | *How each task runs*, items 1–3 |
| P-2, B-2, F-3: `required_tests` must be suite paths | item 4; every *Tests* column |
| P-3, B-3, F-4: the unit suites had no wrapper and no `run-all.sh` entry | `tests/test-ere-unit.sh` (1.2), `tests/test-guard-port-unit.sh` (1.4); the H5 row |
| P-4: must-bite under the refactoring workflow | *Expected red sensors*; one line per task |
| P-5: a single-file step cannot be split | *Budget handling*; the git port pre-cut into two steps |
| P-6: a step's tests must exist and pass at its own `step-done` | units arrive with their code; `PORTED` |
| P-7, F-5: T4 | *A T4 triage stops the work* |
| P-8, F-11: what `--force` records; the precedent | the forced-close commands; the precedent corrected |
| P-9: seam commands | *Seam rule* |
| P-10: reports written while the scope guard is armed | item 4: recorded after `step-done` |
| P-11: the lint sensor misses untracked files | *Expected red sensors*; `P-R17` |
| P-12: string step ids | item 1 |
| B-4: built-in `RULES` missing from the engine differential | WP1.3 step 1 |
| B-5: expiry on a direct `ere_match` was a silent allow | deviation 1; WP1.4 step 3; a unit case per `BUDGETED` rule |
| B-6: long-subject quadratic matching | Risk 3; WP1.3 step 3; the stop rule |
| B-7, F-1: the R3 grep would always fail | `P-R3` |
| B-8: emergency rollback after the library is gone | deviation 3; *Rollback* |
| B-9: interpreter dependency; import failure outside `main_guard` | Risk 6; guarded imports (WP1.4 step 3); `docs/hooks.md` |
| B-10: the WP1.7 corpus step could not edit the guard | WP1.7 step 3 *Files* |
| B-11: `__pycache__` under `hooks/lib/` | Risk 5; the N1 F6e pattern; the WP1.8 security review |
| B-12: README and `hook-performance.md:182-190` | WP1.8 step 3 |
| B-13: F6b and F6d not recorded | WP1.8 step 3 |
| B-14: the unparsable state file | WP1.1 step 4; the R12 cases |
| B-15: the PATH for the shim sample; R2 before every switch | WP1.1 step 3; R2 "per switched guard" |
| F-2: escaped pipes in the table commands | the fenced *Proof* block |
| F-6 … F-10, F-12: citations and totals | `:41`, `run-all.sh:13`, `tests.yml:16-20`, `risk-tiers.json:450-458`, `ai-hook-common.sh:49-61`, the totals |

Out of the plan's scope and documented only: `testing.md:81-82` against `:132`, and `testing.md:150`.
