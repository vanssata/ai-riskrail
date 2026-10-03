#!/usr/bin/env python3
"""Engine differential (spec D4 ii): hooks/lib/ai_ere.py against bash's [[ =~ ]].

The oracle is one bash per locale, C and C.UTF-8, fed every case at once. It
reads NUL-delimited pattern and subject records, since the subjects hold tabs
and newlines and a bash string cannot hold a NUL, and answers each with the
exit code of `[[ $s =~ $p ]]`: 0 match, 1 no match, 2 invalid pattern. ai_ere
answers the same from compile() and search(), None being invalid. A difference
that the declared list (D6) does not explain fails the run.

For now the corpus is every string of both *-defaults.json files, _comment
excepted, over the characterization corpus: the COMMANDS array of
tests/test-guard-characterization.sh as bash reads it, the file-tool paths of
the golden's labels and every string of the fixture payloads. WP1.3 adds the
generated patterns and subjects, drawn from AI_DIFF_SEED.

    python3 tests/test_pattern_differential.py    # AI_DIFF_SEED=20261003
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks", "lib"))
import ai_ere

LOCALES = ("C", "C.UTF-8")
VERDICT = {0: "match", 1: "no match", 2: "invalid"}
ORACLE = ('while IFS= read -r -d "" p && IFS= read -r -d "" s; do'
          ' { [[ $s =~ $p ]]; } 2>/dev/null; printf "%d\\n" "$?"; done')
SHOWN = 40
# D6, the engine's part of it. ai_ere matches UTF-8 bytes, which is glibc in
# the C locale; under a UTF-8 locale glibc counts characters, so D6's "POSIX
# classes on non-ASCII text" widens to any non-ASCII pattern or subject there.
# A multi-character [[.x.]] or [[=x=]] is not declared: C and C.UTF-8 reject it
# as ai_ere does, and a test on the pattern's text also matches a plain
# bracket such as a[.bc.], so it would waive a real divergence.
DECLARED = (
    ("non-ASCII pattern or subject under a UTF-8 locale",
     lambda locale, pattern, subject: locale != "C" and not (pattern + subject).isascii()),
)


def encode(text: str) -> bytes:
    """The bytes ai_ere matches: UTF-8, surrogateescape, else surrogatepass."""
    try:
        return text.encode("utf-8", "surrogateescape")
    except UnicodeEncodeError:
        return text.encode("utf-8", "surrogatepass")


def strings(value: object) -> list[str]:
    """Every string in a JSON value, depth first, _comment members excepted."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = [v for k, v in value.items() if k != "_comment"]
    return [s for item in value for s in strings(item)] if isinstance(value, list) else []


def patterns() -> list[str]:
    found: list[str] = []
    for name in ("ai-git-guard-defaults.json", "ai-path-guard-defaults.json"):
        with open(os.path.join(PLUGIN_ROOT, "hooks", name), encoding="utf-8") as f:
            found += strings(json.load(f))
    return list(dict.fromkeys(found))


def subjects() -> list[str]:
    """The characterization corpus."""
    with open(os.path.join(HERE, "test-guard-characterization.sh"), encoding="utf-8") as f:
        lines = f.read().splitlines()
    start = lines.index("COMMANDS=(")
    script = "\n".join(lines[start:lines.index(")", start) + 1]) + '\nprintf "%s\\0" "${COMMANDS[@]}"'
    raw = subprocess.run(["bash", "-c", script], capture_output=True, check=True).stdout
    found = [c.decode("utf-8", "surrogateescape") for c in raw.split(b"\0")[:-1]]
    with open(os.path.join(HERE, "fixtures", "guard-characterization", "golden.txt"), encoding="utf-8") as f:
        found += [m.group(1) for m in re.finditer(r"^### \S+ \| \w+ \w+=(.+)$", f.read(), re.M)]
    for fixture in sorted(glob.glob(os.path.join(HERE, "fixtures", "*", "*.json"))):
        if os.path.basename(os.path.dirname(fixture)) in ("git-guard", "path-guard", "scope-guard", "codex-hooks"):
            with open(fixture, encoding="utf-8") as f:
                found += strings(json.load(f).get("payload"))
    return list(dict.fromkeys(found))


def bash_env(locale: str) -> dict[str, str]:
    return {"PATH": os.environ.get("PATH", ""), "LC_ALL": locale}


def available(locale: str) -> bool:
    """C always is; a UTF-8 locale is when bash under it reads U+00E9 as one character."""
    return locale == "C" or subprocess.run(
        ["bash", "-c", '[[ $1 =~ ^.$ ]]', "_", "é"], env=bash_env(locale), capture_output=True,
        check=False).returncode == 0


def bash_verdicts(locale: str, cases: list[tuple[str, str]]) -> list[int]:
    data = b"".join(encode(p) + b"\0" + encode(s) + b"\0" for p, s in cases)
    out = subprocess.run(["bash", "-c", ORACLE], input=data, env=bash_env(locale), capture_output=True,
                         check=False).stdout.split()
    if len(out) != len(cases):
        raise RuntimeError(f"the oracle answered {len(out)} of {len(cases)} cases under LC_ALL={locale}")
    return [int(rc) for rc in out]


def ere_verdict(pattern: str, subject: str) -> int:
    ere = ai_ere.compile(pattern)
    return 2 if ere is None else 0 if ere.search(subject) else 1


def main() -> int:
    if not shutil.which("bash"):
        print("pattern differential: skipped, bash not on PATH")
        return 0
    seed = int(os.environ.get("AI_DIFF_SEED") or 20261003)
    pats, subs = patterns(), subjects()
    cases = [(p, s) for p in pats for s in subs if "\0" not in p + s]
    mine = [ere_verdict(p, s) for p, s in cases]
    print(f"== pattern differential ({len(pats)} patterns x {len(subs)} subjects, seed {seed})")
    failed = 0
    for locale in LOCALES:
        if not available(locale):
            print(f"  LC_ALL={locale}: skipped, the locale is not installed")
            continue
        passed, declared, shown = 0, dict.fromkeys((name for name, _ in DECLARED), 0), 0
        for (pattern, subject), want, got in zip(cases, bash_verdicts(locale, cases), mine):
            reason = None if want == got else next(
                (name for name, test in DECLARED if test(locale, pattern, subject)), "")
            if reason is None:
                passed += 1
            elif reason:
                declared[reason] += 1
            else:
                failed += 1
                shown += 1
                if shown <= SHOWN:
                    print(f"  FAIL  LC_ALL={locale} pattern {pattern!r} subject {subject!r}: "
                          f"bash {VERDICT[want]}, ai_ere {VERDICT[got]} (seed {seed})")
        extra = "".join(f", {n} declared ({name})" for name, n in declared.items() if n)
        print(f"  LC_ALL={locale}: {passed} identical{extra}, {shown} undeclared")
    if not cases:
        failed = 1
        print("  FAIL  nothing was compared: a differential that runs no case proves nothing")
    print(f"pattern differential: {'FAILED' if failed else 'passed'}, {failed} undeclared (seed {seed})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
