# Review ledger — T-2026-10-02-001

<!-- Append-only. Every review agent reads this before it plans its
     own work; a CONFIRMED row is out of budget for later passes. -->

| claim | verified by | outcome | pass |
|---|---|---|---|
| tests on 9882978a2: verify_command exit 0 in 249s, run 1, log .ai/reports/T-2026-10-02-001/tests-suite-1.log | sensors.py tests | CONFIRMED | sensor |
| lint on 9882978a2: pylint $(git ls-files '*.py') exit 0 in 4s | sensors.py lint | CONFIRMED | sensor |
| diff on 9882978a2: 5 files / 563 lines (T3 task budget 30 / 800) | sensors.py diff | CONFIRMED | sensor |
| rescore on 9882978a2: T3 — scopes: docs, source, tests | sensors.py rescore | CONFIRMED | sensor |
| traceability on 9882978a2: 5/5 finished steps name tests that exist | sensors.py traceability | CONFIRMED | sensor |
| duplicates on 9882978a2: 0 blocks >= 8 lines repeat | sensors.py duplicates | CONFIRMED | sensor |
| plan_sections on 9882978a2: docs/sdlc/plans/os-independent-installer-packaging-wp1-guards-in-python.md carries every section | sensors.py plan_sections | CONFIRMED | sensor |
| bite on 9882978a2: 2 characterization test(s) fail against the code they describe (tests/test-guard-differential.sh, tests/test-ai-status-root.sh) | sensors.py bite | DEFECT, open | sensor |
| bite red names tests/test-guard-differential.sh only because sensors.py runs every must_pass suite in one command and lists all names on a non-zero exit; bite-must_pass.log:2 shows `guard differential: 749 passed, 0 failed` at the base tree, :29 shows `ai-status project root: 12 passed, 4 failed` (ai_os absent at base, the plan's expected red) | session, bite-must_pass.log | CONFIRMED expected red (status-root only); the message's aggregation is a sensors.py observation, not fixed (Untouched) | manager probe |
| the harness bites: PORTED['scope']='file' with no hooks/ai-scope-guard.py turns 2 of 22 comparisons red (rc=2, python's "can't open file" on stderr), exit 1 | session, AI_DIFF_N=8 in-process run | CONFIRMED | manager probe |
| the grammar reaches decisions: at n=300 the frozen guards deny git 34, path 68, scope 30 times, ~37 distinct deny openings, every run rc=0 with empty stderr | session, scratchpad count | CONFIRMED | manager probe |
| ai_os agrees with bash: resolve_dir vs `cd && pwd`, find_ai_root/abs_path/real_path vs the frozen library, logical_cwd vs bash's own pwd, hook_config_dirs: 308 of 312; the 4 are find_ai_root("") where the shell defaults to $AI_CWD (docstring says the caller passes its cwd) | session, scratchpad probe_os.py; manual-proofs.md | CONFIRMED | manager probe |
| AI_DIFF_N=2000 old-vs-old: 4884 passed, 0 failed, seed 20261003, 17 s | session; manual-proofs.md | CONFIRMED | manager probe |
| P-R4 needs grep -H while hooks/lib holds one .py file (no prefix, so the filter cannot match); with -H it prints nothing | session; manual-proofs.md | CONFIRMED (plan command observation) | manager probe |
| tests on 31310db08: verify_command exit 0 in 257s, run 2, log .ai/reports/T-2026-10-02-001/tests-suite-2.log | sensors.py tests | CONFIRMED | sensor |
| lint on 31310db08: pylint $(git ls-files '*.py') exit 0 in 4s | sensors.py lint | CONFIRMED | sensor |
| diff on 31310db08: 5 files / 572 lines (T3 task budget 30 / 800) | sensors.py diff | CONFIRMED | sensor |
| rescore on 31310db08: T3 — scopes: docs, source, tests | sensors.py rescore | CONFIRMED | sensor |
| traceability on 31310db08: 6/6 finished steps name tests that exist | sensors.py traceability | CONFIRMED | sensor |
| duplicates on 31310db08: 0 blocks >= 8 lines repeat | sensors.py duplicates | CONFIRMED | sensor |
| plan_sections on 31310db08: docs/sdlc/plans/os-independent-installer-packaging-wp1-guards-in-python.md carries every section | sensors.py plan_sections | CONFIRMED | sensor |
| bite on 31310db08: 2 characterization test(s) fail against the code they describe (tests/test-guard-differential.sh, tests/test-ai-status-root.sh) | sensors.py bite | DEFECT, open | sensor |
| STRONG review (ai-reviewer, opus): verdict pass; 1 HIGH (grammar outside D6), 1 MEDIUM (resolve_dir fallback), 2 LOW, 3 INFO — review-report.md | ai-reviewer | HIGH, MEDIUM, LOW-4 fixed in R1; LOW-3 carried to WP1.6; INFO recorded | review 1 |
| R1 on the final tree: suite run 2 exit 0 (257 s), e2e 41/0 inside it; bite-must_pass.log again shows the differential 734/0 at base and status-root 12/4 (expected); MEDIUM repro agrees 4/4; D6 check 0 of 6119 texts outside | session; manual-proofs.md | CONFIRMED | manager probe |
