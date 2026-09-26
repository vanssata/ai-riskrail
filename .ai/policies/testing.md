# Testing policy

Tests describe behaviour. Coverage percentage is a side effect, not a goal.

## Characterization first

Before changing behaviour that is not covered by a test — which is most legacy
behaviour — write a test that passes against the code **as it is today**. That
test is the definition of what must not break. Only then change the code.

```
characterization test → refactor → verify identical behaviour → feature change
```

Never do those in one step, and never in one commit.

## What to consider, by kind of change

| Change touches | Also test |
|---|---|
| a shared service | the existing callers, not only the new one |
| money, tax, fiscal | rounding, currency, negative and zero amounts, refunds |
| a state machine | every transition that is now reachable, and the ones that must stay unreachable |
| an async consumer | retry, double delivery, out-of-order delivery, poison message |
| an external integration | timeout, 500, malformed response, partial write |
| a write path | idempotency, concurrency, transaction boundaries |
| authorization | the negative case, for every role |
| a public API or event | the old shape still works |

## Three scopes, three moments

A task runs tests three times at most, and each run has its own scope. Nothing
else runs in between.

| When | What runs | Command |
|---|---|---|
| after each implementation step, before `step-done` | **only the tests the plan named for that step** — the files it touched, their direct callers' tests | `step_test_command` |
| once, after the **last** step | the full fast suite — unit and integration, no e2e | `verify_command` |
| once, at the **end of the task**, after the full suite is green | the end-to-end suite | `e2e_command` |

- A step never runs the full suite, and **never** runs e2e. If the plan named
  no test for a step, nothing runs for it.
- A step's tests are scoped by path or filter, not by `--stop-on-failure`: the
  scoped run still goes to the end, and its failures are fixed inside that step.
- The e2e suite runs **once per task**, at the very end, never per step. Skip it
  at T0/T1, and when the change cannot reach a flow the e2e suite covers — say
  which, in one line; silence is not a verdict.
- A failure in a step's own tests is fixed in that step, before `step-done`;
  the batch rule below is for the two end-of-task runs.

## Reading a failure

**Run to the end, then fix as one batch.** The verification command runs with
no fail-fast flag and is never interrupted at the first failure. Collect every
failure, classify each one, fix all the new regressions in a single remediation
step (`state.py remediate`), and run the command once more. One failure never
sends the task back to the start: the plan, the tier and the finished steps
stand. At most two remediation rounds; a third means the human decides.

Classify before fixing. The four answers are:

- **EXISTING TEST FAILURE** — it failed before this change too. Say so, do not
  fix it inside this task.
- **NEW REGRESSION** — this change broke it. Fix the code, not the test.
- **TEST ENVIRONMENT FAILURE** — database, fixtures, network, container. Say what
  is missing.
- **UNKNOWN** — you could not tell. Say what you tried.

**Never edit a test to make it pass when production behaviour changed
unexpectedly.** A test that suddenly disagrees with the code is evidence, and
deleting evidence is the worst available option.

## Verification

Three commands, one per scope. `verify_command` proves the project is healthy;
`step_test_command` proves one step is; `e2e_command` proves the whole flow
still works. Keep each to one command — chain the pieces in a Makefile or
composer script if there are several — and make sure none of them stops at the
first failure (`--stop-on-failure`, `-x`, `--bail`, `failfast` are off).

`verify_command` must **exclude** the e2e suite: it is the fast loop run after
the last step and again after a remediation batch. `e2e_command` runs once, at
the end of the task. A bugfix still shows its new failing test first — that one
test only, through `single_test`.

```
verify_command:      bash tests/run-all.sh
step_test_command:   bash -c 'rc=0; for t in {files}; do bash "$t" || rc=1; done; exit $rc'
e2e_command:         bash tests/test-end-to-end.sh
lint_command:        pylint $(git ls-files '*.py')
typecheck_command:   none
healthy_output:      run-all.sh ends with "all suites passed" and exit 0; each suite prints
                     "<name>: N passed, 0 failed". pylint ends with "rated at 10.00/10".
                     test-end-to-end.sh ends with "end to end: N passed, 0 failed".
runtime:             run-all.sh ~4-5 min (the CI job measures 4m21s); test-end-to-end.sh
                     ~7 s; pylint ~5 s; any single suite seconds, except the install and
                     adopt suites, which scaffold scratch trees and take tens of seconds.
single_test:         bash tests/test-<name>.sh
```

`step_test_command` may contain `{files}`, which is replaced by the paths the
step names; without it the paths are appended. The placeholder is what lets
`sensors.py` run a step's own tests for the "test must bite" check, so a runner
that only takes a `--filter` gets `bite: unavailable` rather than a wrong answer.

`lint_command` and `typecheck_command` are read by the deterministic sensors,
never by a model. They decide, together with the test run, whether a T2 change
can skip its model review (`risk-tiers.json`, `sensors`). A **missing** line is
`unavailable` and keeps the review; only the literal `none`, written by a human,
says the project has no such tool. `sensors.py detect` proposes the exact line
from the config files it finds, and never runs what it detected.

If the project has no e2e suite, write `e2e_command: none` and say so — an
empty line is read as "not written down yet" and the next task will go looking
for it. Say which group, tag or directory marks the e2e tests and how
`verify_command` excludes them, so a step's scoped run and the fast suite stay
free of them.

## Project specifics

Every suite is a bash script under `tests/`, self-contained: it scaffolds what it
needs into a `mktemp -d` and removes it on exit. `tests/lib.sh` holds the
harness — `pass`, `fail`, `summary`, and the fixture runners for the hook
payloads under `tests/fixtures/`. There is no unit/integration split: the axis is
what a suite exercises, not how deep it goes.

`tests/run-all.sh` names its suites in a literal list, so **a new test file is
not run until it is added there**. It skips a suite that is missing rather than
failing, which is deliberate for a partial checkout and worth remembering when a
suite seems to have disappeared from the count.

`verify_command` includes `test-end-to-end.sh`, so the end-of-task `e2e_command`
run is a second run of the same suite. At 7 seconds that is cheaper than an
exception to the rule; keep it.

**A step names its own suites, by hand, in `allowed_files`-style paths.** There
is no mechanical map from a source file to its tests; the useful ones are:

| Touching | Run |
|---|---|
| `skills/usage-report/**` | `tests/test-usage-report.sh`, `tests/test-codex-usage-report.sh` |
| `hooks/ai-*-guard.sh` | `tests/test-ai-path-guard.sh`, `tests/test-ai-scope-guard.sh`, `tests/test-ai-git-guard.sh`, `tests/test-guard-characterization.sh` |
| `skills/ai-task/state.py` | `tests/test-ai-task-state.sh`, `tests/test-ai-status-root.sh` |
| `skills/ai-task/sensors.py` | `tests/test-ai-task-sensors.sh` |
| `skills/project-update/**` | `tests/test-project-update.sh`, `tests/test-merge-migration.sh`, `tests/test-project-adopt.sh`, `tests/test-scaffold-idempotency.sh` |
| `install.sh`, `profiles/**`, `scripts/resolve-profile.py` | `tests/test-install-dry-run.sh`, `tests/test-profiles.sh`, `tests/test-codex-install.sh`, `tests/test-dual-runtime-install.sh` |
| `hooks/fable-gate.py`, `hooks/runtime-gate.py`, `hooks/context-guard.py` | `tests/test-fable-gate.sh`, `tests/test-runtime-gate.sh`, `tests/test-context-guard.sh` |
| `agents/**`, `codex/**`, `instructions/**` | `tests/test-codex-agent-render.sh`, `tests/test-shared-prompts-model-free.sh`, `tests/test-instruction-budget.sh` |

CI runs two workflows on every push and pull request: `.github/workflows/test.yml`
(`bash tests/run-all.sh`) and `.github/workflows/pylint.yml`
(`pylint $(git ls-files '*.py')` on Python 3.11, 3.12 and 3.13, with no
`--exit-zero` and no `--fail-under` — a single warning fails it). `.pylintrc` is
the config; the house convention for an unavoidable warning is an inline
`# pylint: disable=<name>` with the reason next to it, not a change to `.pylintrc`.

Required tools: `jq`, `python3`, `git` — `run-all.sh` refuses without them. The
assertion count quoted in `README.md` under **Tests** is measured, not estimated:
`bash tests/run-all.sh | grep -oE "[0-9]+ passed" | awk "{s+=\$1} END {print s}"`.
It changes with almost every task; update it in the same commit.
