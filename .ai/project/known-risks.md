# Known risks

<!-- Findings that are real but out of scope for the task that found them. This
     is where "do not fix it, write it down" lands. A human turns entries here
     into their own tasks. -->

<!--
## <short title>

- **Found**: date, by which task
- **Where**: `file:line`
- **What could go wrong**:
- **How likely / how bad**:
- **Suggested fix**: one sentence, not a plan
- **Status**: open / ticketed / accepted / fixed
-->

## `state.py approve` accepts a pty as a human

- **Found**: 2026-09-27, by T-2026-09-27-003 (WP6 F3)
- **Where**: `skills/ai-task/state.py:876-879` (`human_present()`)
- **What could go wrong**: an agent that gets past the path guard's approve regex and opens a pty (`script -qec …`) passes the terminal check and grants its own T3+ approval. `--confirm-delete` now also refuses under an agent-session marker (`adopt.human_gate()`); approve does not.
- **How likely / how bad**: needs a deliberate bypass of the hook; the approval is journalled with `via`. Bad when it happens: the one gate the pipeline may not close itself.
- **Suggested fix**: give `state.py` the same marker check as `adopt.human_gate()`.
- **Status**: open

## The approve rule is read line by line, so a backslash-newline splits it

- **Found**: 2026-09-27, by the plan review of T-2026-09-27-003
- **Where**: `hooks/ai-path-guard.sh` (`APPROVE_RE`, `HOOKRUN_RE`), `hooks/lib/ai-hook-common.sh:227-237` (`ere_match` per line)
- **What could go wrong**: `python3 …/state.py \` newline `approve --by x` is one command to the shell and two lines to the rule, so the hook allows it; `state.py`'s own tty check is then the only line.
- **How likely / how bad**: deliberate obfuscation; same class as the documented regex limit.
- **Suggested fix**: join backslash-newlines before matching, as the `--confirm-delete` rule does.
- **Status**: open

## The `--confirm-delete` hook rule needs `.ai/` in the session's cwd

- **Found**: 2026-09-27, security and adversarial review of T-2026-09-27-003
- **Where**: `hooks/ai-path-guard.sh:40` (`find_ai_root "$AI_CWD" || allow` runs before every rule)
- **What could go wrong**: a session opened in a parent directory runs `update.py /abs/project --apply --confirm-delete X`; only `adopt.human_gate()` refuses it, and an agent adding `AI_UNATTENDED=1` inline passes with `via: unattended`.
- **How likely / how bad**: needs the agent to type `AI_UNATTENDED=1` itself (the refusal no longer suggests it under a marker); irreversible deletion, originals kept under `.ai/reports/`.
- **Suggested fix**: evaluate the `--confirm-delete` rule before the `.ai/` opt-in, since it needs no project policy.
- **Status**: open

## `adopt.json` / `migration.json` carry the deletion audit but are agent-writable

- **Found**: 2026-09-27, security review of T-2026-09-27-003
- **Where**: `hooks/ai-path-guard-defaults.json` (protects only `questions.md` and `events.jsonl` under `.ai/reports/`); records written at `skills/project-update/adopt.py` (`cleanup_run`) and `update.py` (`deletions`)
- **What could go wrong**: `cleanup.via` / `deletions[].via` can be rewritten with the Write tool after the fact.
- **How likely / how bad**: deliberate tampering; the audit trail loses its weight.
- **Suggested fix**: add `.ai/reports/[^/]+/(adopt|migration)\.json$` to the protected patterns, or also journal the deletion into a protected file.
- **Status**: open

## The `--confirm-delete` hook regex is quadratic on very long lines

- **Found**: 2026-09-27, security review of T-2026-09-27-003
- **Where**: `hooks/ai-path-guard.sh` (`CONFIRM_RE`)
- **What could go wrong**: a ~120 KB padded line takes ~13 s, past the 10 s hook timeout; if the runtime treats a timeout as non-blocking the command runs (inferred, not observed). `adopt.py`'s marker check still refuses.
- **How likely / how bad**: deliberate padding only.
- **Suggested fix**: deny or skip the ERE for a line over a fixed length that contains both `update` and `--co`.
- **Status**: open

## A remediation step is measured from the task's base tree

- **Found**: 2026-10-03, by T-2026-10-03-001 (R1)
- **Where**: `skills/ai-task/state.py:1077` (`cmd_remediate` never sets `tree_before`), `:928` (`step-done` falls back to `diff.base_tree`)
- **What could go wrong**: KNOWN FACT: `step-done R1` measured the whole task (712 lines > 250) for a remediation that changed 54 lines, so the diff gate refuses every remediation in a task over the step budget and `--force` becomes the routine way out.
- **How likely / how bad**: every remediation after a task of more than 250 lines; it teaches the gate to be overridden.
- **Suggested fix**: stamp `tree_before` with `sensors.snapshot_tree` in `cmd_remediate`, as `cmd_step` does at `:899-900`.
- **Status**: open

## glibc's matcher, the differential's oracle, can spin on a stacked repeat before a back-reference

- **Found**: 2026-10-03, by T-2026-10-03-001 (R1 probe)
- **Where**: `tests/test_pattern_differential.py` (one long-lived bash per locale, no per-record timeout)
- **What could go wrong**: KNOWN FACT: `[[ $s =~ $p ]]` ran past 2 s (one record past 400 s) on 116 of 132,840 probe records, all a stacked quantifier over a group followed by `\1`, e.g. `(a)**+\1`; Python hangs likewise on `(a*){2,}{2,}+$`. A random corpus in WP1.3 that draws such a pattern stalls the run with no failure line.
- **How likely / how bad**: needs a user pattern of that shape; the run hangs instead of failing.
- **Suggested fix**: a per-record time limit on both engines, reported as its own verdict (D5, WP1.3).
- **Status**: open
