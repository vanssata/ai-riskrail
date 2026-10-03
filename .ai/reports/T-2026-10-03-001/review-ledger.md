# Review ledger — T-2026-10-03-001

<!-- Append-only. Every review agent reads this before it plans its
     own work; a CONFIRMED row is out of budget for later passes. -->

| claim | verified by | outcome | pass |
|---|---|---|---|
| tests on e1f2a9053: verify_command exit 0 in 241s, run 1, log .ai/reports/T-2026-10-03-001/tests-suite-1.log | sensors.py tests | CONFIRMED | sensor |
| lint on e1f2a9053: pylint $(git ls-files '*.py') exit 0 in 4s | sensors.py lint | CONFIRMED | sensor |
| diff on e1f2a9053: 6 files / 674 lines (T3 task budget 30 / 800) | sensors.py diff | CONFIRMED | sensor |
| rescore on e1f2a9053: T3 — scopes: source, tests | sensors.py rescore | CONFIRMED | sensor |
| traceability on e1f2a9053: 4/4 finished steps name tests that exist | sensors.py traceability | CONFIRMED | sensor |
| duplicates on e1f2a9053: 0 blocks >= 8 lines repeat | sensors.py duplicates | CONFIRMED | sensor |
| plan_sections on e1f2a9053: docs/sdlc/plans/os-independent-installer-packaging-wp1-guards-in-python.md carries every section | sensors.py plan_sections | CONFIRMED | sensor |
| bite on e1f2a9053: 2 characterization test(s) fail against the code they describe (tests/test-ere-unit.sh, tests/test-pattern-differential.sh) | sensors.py bite | DEFECT, open | sensor |
| bite red is the plan's declared expected red: both suites fail at the base with `ModuleNotFoundError: No module named 'ai_ere'` (bite-must_pass.log:4,8); the module is new in this task | session, bite-must_pass.log | CONFIRMED, expected | manager probe |
| every unit expectation in tests/test_ere_unit.py is glibc's: 11,024 bracket-membership records and the 78 VERDICTS rows replayed through `[[ $s =~ $p ]]` under LC_ALL=C, 0 differences | session, scratchpad xcheck1.py / xcheck2.py | CONFIRMED | manager probe |
| translator accept/reject and match verdicts equal bash outside one quirk: 810,000 random pattern×subject records (0–16 tokens incl. brackets, classes, collating symbols, intervals, back-refs, GNU escapes, `é`, `\n`), both locales | session, scratchpad fuzz.py | CONFIRMED | manager probe |
| glibc sets `^`/`$` next to a newline consumed inside the match even without REG_NEWLINE (`\n^a` on `x\na`, `a$.` on `a\nb` match in bash, not in ai_ere); unreachable on the hook path (ai-hook-common.sh:229-236, ai-git-guard.sh:171-172, ai-path-guard.sh:352-353 match single lines) and absent from WP1.2's corpus | session, manual-proofs.md | OPEN, decision for WP1.3 / spec owner (not a WP1.2 defect: the plan's translation is `$`→`\Z`) | manager probe |
| the differential bites: `[[:space:]]` without `\n` injected → 2 FAIL lines naming locale, pattern, subject, both verdicts and seed, exit 1 | session, scratchpad bite.py | CONFIRMED | manager probe |
| tests on 114b25c05: verify_command exit 0 in 258s, run 2, log .ai/reports/T-2026-10-03-001/tests-suite-2.log | sensors.py tests | CONFIRMED | sensor |
| lint on 114b25c05: pylint $(git ls-files '*.py') exit 0 in 4s | sensors.py lint | CONFIRMED | sensor |
| diff on 114b25c05: 6 files / 712 lines (T3 task budget 30 / 800) | sensors.py diff | CONFIRMED | sensor |
| rescore on 114b25c05: T3 — scopes: source, tests | sensors.py rescore | CONFIRMED | sensor |
| traceability on 114b25c05: 5/5 finished steps name tests that exist | sensors.py traceability | CONFIRMED | sensor |
| duplicates on 114b25c05: 0 blocks >= 8 lines repeat | sensors.py duplicates | CONFIRMED | sensor |
| plan_sections on 114b25c05: docs/sdlc/plans/os-independent-installer-packaging-wp1-guards-in-python.md carries every section | sensors.py plan_sections | CONFIRMED | sensor |
| bite on 114b25c05: 2 characterization test(s) fail against the code they describe (tests/test-ere-unit.sh, tests/test-pattern-differential.sh) | sensors.py bite | DEFECT, open | sensor |
