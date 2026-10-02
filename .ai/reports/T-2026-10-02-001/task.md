# T-2026-10-02-001 — WP1.1: oracle, harness and the OS module

Workflow `refactoring`, tier T3 (solo, direct mode): a refactoring of shared code is T3 at minimum
(`.ai/workflows/refactoring.md:13-25`); no T4 path scope reached; sensors re-score the diff to T3.
Plan: `docs/sdlc/plans/os-independent-installer-packaging-wp1-guards-in-python.md`, section WP1.1,
approved by the human in plan mode. Nothing on the hook path changes.

## What changed

1. `docs/sdlc/intent/os-independent-installer-packaging.md` — the WP1 row names the exec shims and the
   split into WP1.1–WP1.8 and no longer claims the hook command lines or the entry upgrade; the WP4a
   row gains the command-line switch and O30's de-duplicating upgrade and stale-file removal (H1).
2. `tests/fixtures/guard-port/` — byte copies (`cp -p`) of `hooks/ai-{git,path,scope}-guard.sh` and
   `hooks/lib/ai-hook-common.sh`: the frozen oracle (H4). `cmp` identical, modes kept.
3. `tests/test_guard_differential.py` + `tests/test-guard-differential.sh` + one entry in
   `tests/run-all.sh` — the whole-guard differential (spec D4 iii): the characterization tree rebuilt
   in Python plus a symlinked project, scratch HOME and hooks/, `LC_ALL=C`, the `PORTED` table (empty:
   every guard runs its frozen copy against itself), the jq-less PATH for a `.py` guard, a seeded
   10 % sample through the source-tree `.sh`, rc/stdout/stderr compared byte for byte, 30 s timeout,
   22 state variants, the D4 iii payload grammar kept inside D6. Seed `AI_DIFF_SEED` (20261003), size
   `AI_DIFF_N` (300).
4. `hooks/lib/ai_os.py` — the one OS module (O3, R4): `runtime_home`, `hook_config_dirs`,
   `logical_cwd`, `resolve_dir` (bash `cd -L` + `pwd`, both fallbacks), `find_ai_root`, `abs_path`,
   `real_path`, `run_git` (argument list, no shell, lazy `subprocess`). Not imported by anything on
   the hook path yet; not installed (`install.sh:626` copies `lib/*.sh` only).
5. `tests/test-ai-status-root.sh` — the reference call compares the skill's walk with
   `ai_os.find_ai_root` (`python3 -I -S`), comment at :9 follows. No assertion changed (R14).

## Deliberately preserved

The three guards, `hooks/lib/ai-hook-common.sh`, both defaults files, `.ai/policies/path-guard.json`,
`settings.common.json`, `codex/hooks.json`, the characterization suite and its golden file, the three
guard suites, `tests/test-end-to-end.sh` and `skills/ai-task/sensors.py`: `git diff --quiet fea014f`
exit 0 on all 16.

## Verification

- `state.py test-run --scope suite` (`bash tests/run-all.sh`): run 1 exit 0 (249 s), and after the
  remediation run 2 exit 0 (257 s); 3038 assertions measured in run 2. `--scope e2e`: exit 0,
  `end-to-end: 41 passed, 0 failed` (again inside run 2).
- By hand (`manual-proofs.md`): the 4 `cmp`s; `AI_DIFF_N=2000` → 4884 passed, 0 failed, seed
  20261003; pylint 10.00 on 3.14 and under `uvx --offline --python 3.11`; ai_os smoke 7/7 under
  `uv` 3.11 and 3.13; the differential under 3.11; P-R4 prints nothing (with `grep -H`, see
  observations); ai_os vs bash and the frozen library 308/312 (the 4: `find_ai_root("")`, the
  caller's default) plus the reviewer's MEDIUM repro 4/4.
- `review-gate`: every sensor green except the expected red bite on `tests/test-ai-status-root.sh`
  (ai_os absent at the base). The row also names the differential only because `sensors.py` lists
  every must-pass suite on a combined non-zero exit; `bite-must_pass.log` shows it 734/0 at the base.

## Review

One `ai-reviewer` on STRONG (opus), verdict pass: HIGH (grammar outside D6 in
`tool_name`/`cwd`/`hook_event_name`) and MEDIUM (`resolve_dir` missed bash's retry when the canonical
directory cannot be entered) fixed in remediation step R1 together with LOW-4 (a run that compares
nothing now fails; four more environment variables stripped). No security review (plan). Details:
`review-report.md`.

## Rollback

`git revert <commit>`. Nothing on the hook path, no installed file, no state format changes.

## Observations (not fixed here)

- `README.md:759` says "Twenty-five suites, 2,179 assertions"; the tree now has 26 suites and run 2
  measured 3038 (2179 was already behind before this task: the differential adds 734). README is
  outside this task's files.
- `sensors.py` bite: on a combined failure the detail names every must-pass suite, not the failing
  ones (Untouched file; recorded only).
- P-R4 as the plan spells it needs `grep -H` while `hooks/lib/` holds one `.py` file and no
  `hooks/ai-*-guard.py` exists; from WP1.2 on it works as written.
- Open for the spec owner: whether `""` as `cwd` is inside D6 (the shell treats `""`, null, false
  and an absent `cwd` alike, by falling back to `$PWD`). The grammar sends `""` only as `tool_name` or
  `hook_event_name` for now. D6's "jq ≥ 1.7" is not checked by the harness (jq 1.8.1 here).
- For WP1.6: the differential has no user-config variant (`$HOME/.claude/hooks/ai-git-guard.json`,
  `CLAUDE_CONFIG_DIR`, `CODEX_HOME`); only the golden covers the config lookup today. The port runs
  from the source `hooks/`, as the plan's step 3 says, not from a scratch copy as spec D4 iii says.
- `state.py quick` advised `preferred runtime: codex (plan table: refactoring -> codex)`; the task
  stayed in Claude Code.
- The uncommitted `.ai/policies/risk-tiers.json` edit is the human's own (the plan's `diff_budget.exclude`
  entries, plus raised T0–T2 per-task and T1 per-step budgets the plan did not ask for).
