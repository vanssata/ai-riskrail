# Review — T-2026-10-03-001 (WP1.2)

Adversarial review: `ai-reviewer` on the STRONG tier. It ran on Opus 5.5 (claude-opus-5-5). The verdict is
**passed**, with no BLOCKER and no HIGH. Each finding below was reproduced by the manager in this session.

| # | Severity | Finding | Where | Disposition |
|---|---|---|---|---|
| 1 | MEDIUM | glibc never matches a back-reference to a group that can match empty and is repeated with a minimum of at least 2; ai_ere does match it. `(a*){2}\1` on `aa`, `(){2}\1` on `""`, `(\|a){2,}\1b` on `aab`: bash 1, ai_ere 0. This is a new deny for a user pattern. The shipped defaults hold no back-references. | `hooks/lib/ai_ere.py` (emit of a dup over a group) | open decision for WP1.3, next to the newline-anchor quirk (manual-proofs.md) |
| 2 | MEDIUM | A stacked quantifier is emitted as nested quantified groups, e.g. `a***b` → `(?:(?:a*)*)*b`, which backtracks exponentially. `a**b` over 22 × `a` takes 0.15 s and doubles with each character, against about 1 ms in glibc. The differential has no timeout. | `hooks/lib/ai_ere.py` (`_emit`, dup), `tests/test_pattern_differential.py` | remediation: merge `*`/`+`/`?` under a repeat into one quantifier; the differential's timeout and budget stay WP1.3's (D5) |
| 3 | LOW | A RecursionError gives None, and that None is cached, so the caller's stack depth poisons later calls. Nesting from 198 levels up gives None, though glibc accepts it. | `hooks/lib/ai_ere.py` (`compile`) | remediation: an outcome that depends on the stack is not cached; the depth limit is noted for the spec owner |
| 4 | LOW | The DECLARED multi-character `[[.x.]]` predicate matches ordinary bracket text, e.g. `a[.bc.]`, so a real divergence could be waived. C and C.UTF-8 both reject multi-character elements, so the entry never applies. | `tests/test_pattern_differential.py` (DECLARED) | remediation: drop the entry, with a comment saying why |
| 5 | INFO | The C.UTF-8 pass has no non-ASCII case in WP1.2's corpus. | — | WP1.3 adds non-ASCII subjects |

Ledger: finding 1 reopens the fuzz row ("0 differences except one quirk"). The manager's fuzz alphabet
held `{2}` and `\1`, but never a group that can match empty followed by `{m≥2}` and then a back-reference.

Examined and clean, per the reviewer:
- about 1,000 hand cases and 200k fuzz records on the accept/reject boundary;
- `captures()` equals BASH_REMATCH for `refspec_re` and `ln_re` on 378 lines;
- the units pass under `-W error` on Python 3.11–3.14;
- COMMANDS extraction, golden labels, fixture glob, NUL framing, answer count, env, the empty-corpus failure and the failure-line contents;
- scope.

## Re-review after R1 (scoped)

`ai-reviewer` on STRONG (opus), over R1's diff against e1f2a90 (3 files, +46 −8). The verdict is **pass**, with no BLOCKER and no HIGH.

| # | Severity | Finding | Where | Disposition |
|---|---|---|---|---|
| 2 | MEDIUM | Only partly closed. `_merge` folds only an inner `*`, `+` or `?`, so an interval under a repeat stays nested and still backtracks exponentially. Over `"a"*n` with no `b`: `a?{2}+b` → `(?:a{0,2})+b` takes 16.3 s at n=38, and `a{1,3}+b` takes 32.6 s at n=34. bash answers in under 10 ms. The manager reproduced it at n=28: 0.13 s and 0.84 s. Before R1, `a?{2}+b` did not finish in 60 s. | `hooks/lib/ai_ere.py` (`_merge`, the dup loop) | human decision: widen the fold to every contiguous `x{a,b}{c,d}`, or leave the rest to D5's timeout (WP1.3) |
| 3 | — | Closed. A `RecursionError` result is not cached, and the test catches the old code. It passes under `-W error` on Python 3.11 to 3.14. | `compile` | closed |
| 4 | — | Closed. bash and ai_ere both reject `a[[.bc.]]` under C and C.UTF-8. | differential | closed |
| 6 | INFO | `(a*)*b` and `(a+)+b`, nested inside a group, are exponential as before R1. | — | D5, WP1.3 |
| 7 | INFO | spec :198 still declares multi-character `[[.x.]]`/`[[=x=]]`. This is true for other UTF-8 locales and does not conflict with R1. | `docs/sdlc/specs/…-wp1-guards-in-python.md:198` | none |

`captures()` after the merge: against `BASH_REMATCH` over 14,520 records, the old code differs on 487 and the new code on 471. R1 introduces 0 regressions and fixes 16. The remaining differences are D3's leftmost-first against leftmost-longest. Bounds cannot exceed `RE_DUP_MAX`, and the back-reference bookkeeping is unchanged.
