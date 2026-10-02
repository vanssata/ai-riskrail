# Review report — T-2026-10-02-001 (WP1.1)

Reviewer: `ai-reviewer`, STRONG tier (model requested: opus, `state.py profile --tier STRONG`), one pass
over `git diff` and the untracked new files. No security review for this task (plan, WP1.1 row).
Verdict as returned: **pass** — "nothing blocks WP1.1 itself; the HIGH is a latent false red to fix in
the remediate step before WP1.5 sets `PORTED["scope"]="all"`."

## Findings and what was done

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | HIGH | `ODD` (`tests/test_guard_differential.py`) put `True`, numbers, arrays and objects into `tool_name`, `cwd`, `hook_event_name` — outside spec D6, which allows only absent, null, false or a string there. The frozen guards still deny some of these (path/scope with `hook_event_name: 7`; git with a non-string `cwd`), while R12 has a port exit 0 silently outside D6: a correct port would go red. Reviewer measured 39 out-of-domain runs at n=300 (2 frozen denies), 153 at n=2000 (10). | Fixed in R1: those fields now take only `None`, `False` or `""` (`""` not for `cwd`, which D6 wants absolute). Numbers stay where D6 allows them: `tool_input` and the file path fields. |
| 2 | MEDIUM | `resolve_dir` returned None when the canonical directory exists but cannot be entered; bash's `cd -L` then retries the path as written and answers with `getcwd()`. Repro: `x/y` mode 000, `x/l -> p/q`, `p/y/.ai`; start `x/l/../y` → shell `p/y`, ai_os None (a fail-open divergence, inside D6). | Fixed in R1: the fallback covers both "canonicalisation failed" and "canonical directory not enterable"; docstring corrected. Repro re-run, see manual-proofs.md. |
| 3 | LOW | The port runs from the source `hooks/`, not the scratch one (spec D4 iii says scratch); a stray untracked `hooks/ai-git-guard.json` would reach only the port and the sample. No differential coverage of user configs (HOME's `.claude/hooks`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME`). | Not changed: the plan's step 3 names `python3 -I -S hooks/ai-<g>-guard.py`, and the WP1.5+ shim runs from the source tree too. Carried as an open point for WP1.6 (git guard: a user-config variant). |
| 4 | LOW | `AI_DIFF_N=0` passes with nothing compared; `POSIXLY_CORRECT`, `SHELLOPTS`, `BASHOPTS`, `AI_GUARD_MATCH_BUDGET_MS` leak from the developer's shell; jq ≥ 1.7 (D6) is not checked. | Fixed in R1: zero comparisons fail the suite; the four variables are stripped. The jq version check is left to the spec owner (jq 1.8.1 here). |
| 5 | INFO | `real_path` does not strip trailing newlines as `p=$(abs_path …)` does; unreachable, the guards split targets on newlines. | Recorded only. |
| 6 | INFO | `run-all.sh` skips a missing suite silently: the commit must include the four untracked paths. | In the hand-over. |
| 7 | INFO | `test-ai-status-root.sh` now compares the skill with ai_os while the live guards keep the shell walk until WP1.5/1.8. | As planned; the differential covers the shell side. |
