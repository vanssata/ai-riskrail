#!/usr/bin/env python3
"""Whole-guard differential (spec D4 iii) for the three PreToolUse guards.

The oracle is the frozen shell copy of each guard in tests/fixtures/guard-port/.
Every generated payload runs through it and through a candidate, and the exit
code, stdout and stderr must be byte-identical. The candidate is the Python port
where PORTED says so, and the frozen copy itself where it does not. A seeded
10 % of the payloads also run the source-tree hooks/ai-<g>-guard.sh, which is
how a shim is compared with what it replaced.

    python3 tests/test_guard_differential.py    # AI_DIFF_N=300 AI_DIFF_SEED=20261003

Both sides run under LC_ALL=C with a scratch HOME, from a scratch hooks/ that
holds the frozen copies and the current *-defaults.json, with the project as
the working directory. A Python guard runs with a PATH that holds only python3
and git (R3), so a jq it still called would fail here.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
ORACLE = os.path.join(HERE, "fixtures", "guard-port")
GUARDS = ("git", "path", "scope")
# The payload classes each guard is run on; malformed input goes to all three.
CLASSES = {"git": ("bash", "malformed"), "path": ("bash", "file", "malformed"),
           "scope": ("file", "malformed")}
# What the Python port answers for, per guard: "file" (that class only) or
# "all". An absent guard runs its frozen copy against itself. Each guard task
# of WP1 edits this table.
PORTED: dict[str, str] = {}
TIMEOUT = 30
SAMPLE = 0.10

# The characterization tree, tests/test-guard-characterization.sh:44-89.
TRACKED = ("src/Payment/Gateway.php", "src/Payment/LegacyGateway.php", "src/Service.php", "README.md")
UNTRACKED = {".env": "SECRET=1\n", ".env.example": "SECRET=\n", ".claude/settings.json": "{}\n",
             ".codex/hooks/ai-git-guard.json": "{}\n", **{p: "x\n" for p in (
                 "var/dump-2026-09-01.sql", "var/log/production-app.log",
                 "migrations/Version20260101.sql", "secrets/db.txt", "secrets/README.md",
                 "backups/dump_1.sql", ".ssh/id_rsa", "docs/private.key.txt",
                 ".claude/agents/ai-reviewer.md", ".claude/skills/x/SKILL.md", ".codex/config.toml",
                 ".codex/agents/ai-reviewer.md", ".ai/workflows/t3.md", ".cursorrules",
                 "vendor/acme/pkg/AGENTS.md", "vendor/acme/pkg/.cursorrules", "vendor/acme/pkg/src.php",
                 "node_modules/foo/CLAUDE.md", "node_modules/foo/index.js")}}
PATH_POLICY = {"deny_patterns": ["(^|/)docs/private\\.[^/]*$"],
               "allow_patterns": ["(^|/)secrets/db\\.txt$"]}
BASE_STATE = {"task_id": "T-2026-09-09-001", "current_stage": "implementation",
              "approved_plan": {"current_step_id": "1", "steps": [
                  {"step_id": "1",
                   "allowed_files": ["src/Payment/*.php", "tests/Payment/*.php", "docs/"],
                   "forbidden_files": ["src/Payment/LegacyGateway.php"],
                   "forbidden_reason": "legacy gateway behaviour is frozen for this task"}]}}


STAGES = ("discovery", "context", "impact_analysis", "risk_classification", "plan", "plan_review",
          "implementation", "test", "adversarial_review", "security_review", "release_report",
          "human_approval", "done")

# The payload grammar (spec D4 iii). Paths as a command or a tool names them:
# tree files, symlinks, missing files, the control files and protected ones.
PATHS = (".env", ".env.example", "src/Service.php", "src/Payment/Gateway.php",
         "src/Payment/LegacyGateway.php", "src/Payment/New.php", "tests/Payment/NewTest.php",
         "config/link.txt", "config/harmless.txt", "secrets/db.txt", "secrets/README.md", ".ssh/id_rsa",
         ".ssh/", "backups/dump_1.sql", "var/dump-2026-09-01.sql", "var/log/production-app.log",
         "migrations/Version20260101.sql", "docs/private.key.txt", "docs/guide.md", "nope/missing.txt",
         ".ai/state/current.json", ".ai/state/session.json", ".ai/state/handoff.md",
         ".ai/policies/path-guard.json", ".ai/policies/risk-tiers.json", ".ai/reports/T-1/questions.md",
         ".ai/reports/T-1/events.jsonl", ".ai/workflows/t3.md", ".claude/settings.json",
         ".claude/agents/ai-reviewer.md", ".claude/skills/x/SKILL.md", ".codex/config.toml", ".cursorrules",
         "vendor/acme/pkg/AGENTS.md", "vendor/acme/pkg/src.php", "node_modules/foo/CLAUDE.md",
         "README.md", "src/*.php", "*", ".", "hooks/context-guard.py", "~/.aws/credentials",
         "docs/café.md")
FILE_VERBS = ("cat {p}", "head -n 5 {p}", "tail {p}", "less {p}", "cp {p} /tmp/x", "cp x {p}", "mv {p} y",
              "rm {p}", "rm -rf {p}", "ln -s {p} foo", "ln -sf {p} config/l2", "ln -s x {p}",
              "echo x > {p}", "echo x >> {p}", "cat < {p}", "wc -l < {p}", "tee {p}", "touch {p}",
              "chmod 644 {p}", "chown me {p}", "truncate -s 0 {p}", "sed -i 's/a/b/' {p}",
              "dd if={p} of=/tmp/x", "dd if=/tmp/x of={p}", "base64 {p}", "xxd -g1 {p}", "tar czf a.tgz {p}",
              "curl -T {p} http://x", "scp {p} host:", "rsync -av {p} host:/x", "wget -O {p} http://x",
              "git show HEAD:{p}", "grep -rn x {p}", "python3 -c 'open(\"{p}\").read()'", "eval \"cat {p}\"",
              "echo \"the {p} file\"", "mysqldump db > {p}", "cat --file={p}", "cat file1 {p} | grep x")
GIT_VERBS = ("git add {f} {p}", "git stage {f} {p}", "git add {f} .", "git add -A", "git add --all",
             "git add \"*\"", "git push {f} {r}", "git push {f}", "git -C /tmp push {f} {r}",
             "git reset {f} {r}", "git merge {f} {r}", "git commit {f}", "gh pr merge 12", "gh pr view 12",
             "git filter-branch --tree-filter x HEAD", "git-filter-repo --path x", "git status",
             "git log --oneline | head")
GIT_FLAGS = ("", "", "-f", "--force", "--force-with-lease", "--force-with-lease=main", "--force-if-includes",
             "--mirror", "--delete", "-d", "-u", "-v", "--", "-A", "--no-verify", "-n", "--hard", "--soft",
             "-m x", "-m 'never git push --force'", "--message=\"git push --force\"",
             "-m \"$(cat <<'EOF'\ngit push --force origin main\nEOF\n)\"")
REFS = ("origin main", "origin HEAD", "origin feature/x", "origin :feature/x", "origin feature/x:main",
        "origin refs/heads/main", "origin release/1.0", "origin hotfix/urgent", "main", "HEAD~1", "feature/x")
OTHER = ("terraform apply", "terraform destroy", "terraform plan", "helm upgrade app ./chart -n production",
         "helm install x chart --set env=staging", "kubectl --context=prod get pods", "kubectl get pods",
         "kubectl delete namespace x", "argocd app sync prod-app", "cap production deploy", "dep deploy prod",
         "fly deploy", "vercel --prod", "make deploy", "ls -la", "echo hi", "node -e \"console.log(1)\"",
         "python3 /p/skills/ai-task/state.py --root . approve --by me",
         "python3 /p/skills/ai-task/state.py --root=. approve --by me", "$STATE approve --by me",
         "python3 /p/skills/ai-task/state.py --root . get --field approved_plan",
         "$STATE note decision \"approve it later\"", "python3 hooks/context-guard.py",
         "env X=1 bash .claude/hooks/context-guard.py", "grep -n foo hooks/context-guard.py",
         "python3 skills/project-update/update.py --apply --confirm-delete me",
         "python3 -m update --co=me --ap", "$UPD --confirm-del me 2>&1 --apply", "python3 update.py --apply")
SEPARATORS = ("; ", ";", " && ", " || ", " | ", " & ", "\n", " ;\n  ", "\n\n")
SHAPES = ("{c}", "{c}", "{c}", "{c}", "({c})", "(cd src && {c})", "echo $({c})", "x=1 {c}",
          "{c} 2>&1 >/dev/null", "bash -lc '{c}'", "cat <<EOF > notes.txt\n{c}\nEOF",
          "cat <<-\"END\" | sh\n\t{c}\n\tEND", "git commit -m \"$(cat <<'EOF'\n{c}\nEOF\n)\"",
          "{c}\n", "\n{c}", "  {c}  ")
BASH_TOOLS = ("Bash", "Bash", "Bash", "shell", "exec_command", "local_shell")
FILE_TOOLS = (("Read", "file_path"), ("Edit", "file_path"), ("Write", "file_path"), ("Write", "path"),
              ("MultiEdit", "file_path"), ("NotebookEdit", "notebook_path"), ("Glob", "pattern"),
              ("Glob", "path"), ("apply_patch", "command"))
JUNK = (b"", b" ", b"\n", b"not json at all", b"{", b'{"tool_name":', b"tru", b"[1,2]", b"{}", b"null",
        b"false", b'"Bash"', b"{}{}")
# D6: tool_name, cwd and hook_event_name are absent, null, false or a string, and a
# given cwd is absolute. Other values are R12's (in process), not this differential's.
ODD = (None, False, "")
# A non-string command holds strings only: jq's version decides how a number prints (D6).
ODD_INPUT = (None, False, [], 5, "cat .env", {}, {"command": None}, {"command": False},
             {"command": ["git", "push", "--force"]}, {"command": {"cmd": "cat .env"}})
ODD_PATHS = (5, None, False, ["x"], [5, {"file_path": 3}], {"file_path": ".env"})


def variants() -> dict[str, tuple[str | None, str]]:
    """Each state variant: the text of .ai/state/current.json (None: no file) and the branch."""
    def state(stage: str = "implementation", **plan: object) -> str:
        doc = json.loads(json.dumps(BASE_STATE))
        doc["current_stage"] = stage
        doc["approved_plan"].update(plan)
        return json.dumps(doc, indent=2)

    def twins(first: list[str]) -> list[dict]:
        return [{"step_id": "1", "allowed_files": first, "forbidden_files": [], "forbidden_reason": "first reason"},
                {"step_id": "1", "allowed_files": ["tests/Payment/*.php"],
                 "forbidden_files": ["src/Payment/LegacyGateway.php"], "forbidden_reason": "second reason"}]

    step = BASE_STATE["approved_plan"]["steps"][0]
    table = {"implementation": (state(), "main"), "implementation on feature/x": (state(), "feature/x")}
    table.update({f"stage {stage}": (state(stage), "main") for stage in STAGES if stage != "implementation"})
    table.update({"no step": (state(current_step_id=""), "main"),
                  "null step": (state(current_step_id=None), "main"),
                  "unknown step": (state(current_step_id="9"), "main"),
                  "empty lists": (state(steps=[dict(step, allowed_files=[], forbidden_files=[])]), "main"),
                  "duplicate step ids": (state(steps=twins(["src/Payment/*.php"])), "main"),
                  "duplicate step ids, first unrestricted": (state(steps=twins([])), "main"),
                  "unparsable state file": ("not json\n", "main"), "no state file": (None, "main")})
    return table


class Tree:
    """The project tree, the scratch HOME and hooks/, and the guards' environments."""

    def __init__(self, tmp: str):
        self.tmp = tmp
        self.root = os.path.join(tmp, "project")
        self.bare = os.path.join(tmp, "bare")
        self.linked = os.path.join(tmp, "linked")
        self.home = os.path.join(tmp, "home")
        self.hooks = os.path.join(tmp, "hooks")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        for name in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "AI_UNATTENDED", "AI_GUARD_MATCH_BUDGET_MS",
                     "CDPATH", "BASH_ENV", "POSIXLY_CORRECT", "SHELLOPTS", "BASHOPTS"):
            self.env.pop(name, None)
        self.env.update(HOME=self.home, LC_ALL="C", PWD=self.root)
        bindir = os.path.join(tmp, "bin")
        self.python = os.path.join(bindir, "python3")
        self.py_env = dict(self.env, PATH=bindir)

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", self.root, *args], env=self.env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def build(self) -> None:
        os.makedirs(os.path.join(self.home, ".claude", "hooks"))
        os.makedirs(os.path.join(self.hooks, "lib"))
        for guard in GUARDS:
            shutil.copy2(os.path.join(ORACLE, f"ai-{guard}-guard.sh"), self.hooks)
        shutil.copy2(os.path.join(ORACLE, "lib", "ai-hook-common.sh"), os.path.join(self.hooks, "lib"))
        for name in os.listdir(os.path.join(PLUGIN_ROOT, "hooks")):
            if name.endswith("-defaults.json"):
                shutil.copy2(os.path.join(PLUGIN_ROOT, "hooks", name), self.hooks)
        os.makedirs(os.path.dirname(self.python))
        os.symlink(sys.executable, self.python)
        os.symlink(shutil.which("git") or "git", os.path.join(os.path.dirname(self.python), "git"))
        for rel in ("tests/Payment", "config", ".ai/state"):
            os.makedirs(os.path.join(self.root, rel))
        for rel in TRACKED:
            self.write(rel, "x\n")
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "test")
        self.git("add", "src", "README.md")
        self.git("commit", "-qm", "init")
        for rel, text in UNTRACKED.items():
            self.write(rel, text)
        os.symlink("../.env", os.path.join(self.root, "config", "link.txt"))
        os.symlink("../src/Service.php", os.path.join(self.root, "config", "harmless.txt"))
        self.write(".ai/policies/path-guard.json", json.dumps(PATH_POLICY) + "\n")
        os.makedirs(self.bare)
        with open(os.path.join(self.bare, ".env"), "w", encoding="utf-8") as handle:
            handle.write("SECRET=1\n")
        os.symlink("project", self.linked)

    def set_variant(self, state: str | None, branch: str) -> None:
        path = os.path.join(self.root, ".ai", "state", "current.json")
        if state is None:
            if os.path.exists(path):
                os.remove(path)
        else:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(state)
        self.git("checkout", "-q", "-B", branch)


def envelope(tool: object, cwd: object, tool_input: object) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": cwd, "tool_input": tool_input}


def encode(rng: random.Random, obj: object) -> bytes:
    """One JSON text: compact as jq -c writes it or spaced, raw or ASCII-escaped."""
    seps = rng.choice(((",", ":"), (", ", ": ")))
    return json.dumps(obj, separators=seps, ensure_ascii=rng.random() < 0.3).encode()


def pick_cwd(rng: random.Random, tree: Tree) -> str:
    """An absolute, existing directory (D6), spelled the ways a runtime might."""
    return rng.choice((tree.root, tree.root, tree.root, tree.root + "/", tree.root + "/src", tree.bare,
                       tree.linked, tree.linked + "/src", tree.root + "/src/..", tree.tmp + "//project"))


def pick_path(rng: random.Random, tree: Tree) -> str:
    """A path, relative or absolute, through .. or the symlinked project."""
    prefix = rng.choice(("", "", "", "./", "../project/", "src/../", tree.root + "/", tree.linked + "/"))
    return prefix + rng.choice(PATHS + (tree.home + "/.claude/hooks/ai-path-guard.sh",
                                        tree.home + "/.claude/agents/ai-reviewer.md"))


def word(rng: random.Random, text: str) -> str:
    """text as a shell word: bare, single- or double-quoted, or with a leading backslash."""
    form = rng.randrange(6)
    return (f"'{text}'", f'"{text}"', "\\" + text)[form] if form < 3 else text


def simple(rng: random.Random, tree: Tree) -> str:
    """One simple command: a git verb with flags and refs, a file verb, or another rule's target."""
    kind = rng.randrange(10)
    if kind < 4:
        flags = " ".join(rng.choice(GIT_FLAGS) for _ in range(rng.randrange(1, 3)))
        return (rng.choice(GIT_VERBS).replace("{f}", flags).replace("{r}", rng.choice(REFS))
                .replace("{p}", word(rng, pick_path(rng, tree))))
    if kind < 8:
        return rng.choice(FILE_VERBS).replace("{p}", word(rng, pick_path(rng, tree)))
    return rng.choice(OTHER)


def command(rng: random.Random, tree: Tree) -> str:
    """Simple commands joined by ; & | && || or newlines, in a subshell, a heredoc or a message."""
    cmd = simple(rng, tree)
    for _ in range(rng.choice((0, 0, 0, 1, 1, 2))):
        cmd += rng.choice(SEPARATORS) + simple(rng, tree)
    cmd = rng.choice(SHAPES).replace("{c}", cmd)
    if " " in cmd and rng.random() < 0.15:
        cmd = cmd.replace(" ", " \\\n", 1)          # a backslash-newline
    return cmd


def bash_payload(rng: random.Random, tree: Tree) -> dict:
    cmd = command(rng, tree)
    tool = rng.choice(BASH_TOOLS)
    value: object = cmd
    if rng.random() < (0.6 if tool == "shell" else 0.1):   # Codex's shell takes an argv
        value = rng.choice((["bash", "-lc", cmd], [cmd], cmd.split(" ")))
    return envelope(tool, pick_cwd(rng, tree), {"command": value})


def file_payload(rng: random.Random, tree: Tree) -> dict:
    tool, field = rng.choice(FILE_TOOLS)
    if tool == "apply_patch":
        lines = ["*** Begin Patch"]
        for _ in range(rng.randrange(1, 4)):
            head = rng.choice(("Add", "Update", "Update", "Delete"))
            lines.append(f"*** {head} File: {pick_path(rng, tree)}")
            if head == "Update" and rng.random() < 0.4:
                lines.append(f"*** Move to: {pick_path(rng, tree)}")
            lines += [] if head == "Delete" else ["+x"]
        return envelope(tool, pick_cwd(rng, tree), {"command": "\n".join(lines + ["*** End Patch"])})
    tool_input: dict = {field: pick_path(rng, tree)}
    if tool == "MultiEdit":
        tool_input["edits"] = [{"file_path": pick_path(rng, tree), "old_string": "a", "new_string": "b"}
                               for _ in range(rng.randrange(3))]
    return envelope(tool, pick_cwd(rng, tree), tool_input)


def malformed(rng: random.Random, tree: Tree) -> bytes:
    """Input outside the normal shape: junk, concatenated JSON, fields of the wrong type."""
    obj = rng.choice((bash_payload, file_payload))(rng, tree)
    kind = rng.randrange(6)
    if kind == 0:
        return rng.choice(JUNK)
    if kind == 1:          # several JSON texts: jq's [inputs] path
        tail = rng.choice((obj, {}, [], "x", None))
        return encode(rng, obj) + rng.choice((b"", b" ", b"\n")) + encode(rng, tail)
    if kind == 2:
        return encode(rng, obj) + rng.choice((b" trailing", b"}", b"\n{"))
    if kind == 3:
        field = rng.choice(("tool_name", "cwd", "hook_event_name"))
        obj[field] = rng.choice(ODD[:2] if field == "cwd" else ODD)
    elif kind == 4:
        obj["tool_input"] = rng.choice(ODD_INPUT)
    else:
        obj["tool_input"] = {rng.choice(("file_path", "notebook_path", "path", "edits")): rng.choice(ODD_PATHS)}
    return encode(rng, obj)


def payloads(rng: random.Random, n: int, tree: Tree) -> dict[str, list[tuple[str, bytes, bool]]]:
    """n payloads, grouped by state variant: (class, stdin bytes, in the 10 % sample)."""
    names = list(variants())
    groups: dict[str, list[tuple[str, bytes, bool]]] = {name: [] for name in names}
    for _ in range(n):
        cls = rng.choices(("bash", "file", "malformed"), (45, 35, 20))[0]
        if cls == "malformed":
            data = malformed(rng, tree)
        else:
            obj = bash_payload(rng, tree) if cls == "bash" else file_payload(rng, tree)
            if rng.random() < 0.05:
                del obj["cwd"]
            data = encode(rng, obj)
        variant = names[0] if rng.random() < 0.4 else rng.choice(names)
        groups[variant].append((cls, data, rng.random() < SAMPLE))
    return groups


def run(argv: list[str], stdin: bytes, env: dict[str, str], cwd: str) -> tuple[object, bytes, bytes]:
    """The exit code, stdout and stderr of one guard run; a timeout is its own exit code."""
    try:
        proc = subprocess.run(argv, input=stdin, capture_output=True, env=env, cwd=cwd,
                              timeout=TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return ("timeout", b"", b"")
    return (proc.returncode, proc.stdout, proc.stderr)


def compare(tree: Tree, guard: str, cls: str, data: bytes, sampled: bool) -> list[tuple]:
    """Every comparison for one payload and one guard: (label, frozen triple, other triple)."""
    frozen = [os.path.join(tree.hooks, f"ai-{guard}-guard.sh")]
    want = run(frozen, data, tree.env, tree.root)
    if PORTED.get(guard) in (cls, "all"):
        port = os.path.join(PLUGIN_ROOT, "hooks", f"ai-{guard}-guard.py")
        pairs = [("python port", want, run([tree.python, "-I", "-S", port], data, tree.py_env, tree.root))]
    else:
        pairs = [("frozen copy", want, run(frozen, data, tree.env, tree.root))]
    if sampled:
        source = [os.path.join(PLUGIN_ROOT, "hooks", f"ai-{guard}-guard.sh")]
        pairs.append(("source-tree .sh", want, run(source, data, tree.env, tree.root)))
    return pairs


def show(triple: tuple) -> str:
    rc, out, err = triple
    return f"rc={rc} stdout={out[:240]!r} stderr={err[:240]!r}"


def main() -> int:
    missing = [tool for tool in ("bash", "jq", "git") if not shutil.which(tool)]
    if missing:
        print(f"guard differential: skipped, {' and '.join(missing)} not on PATH")
        return 0
    seed = int(os.environ.get("AI_DIFF_SEED") or 20261003)
    n = int(os.environ.get("AI_DIFF_N") or 300)
    rng = random.Random(seed)
    passed = failed = 0
    with tempfile.TemporaryDirectory() as raw:
        tree = Tree(os.path.realpath(raw))
        tree.build()
        table = variants()
        groups = payloads(rng, n, tree)
        print(f"== guard differential ({n} payloads, {len(table)} state variants, seed {seed})")
        with concurrent.futures.ThreadPoolExecutor(min(16, os.cpu_count() or 4)) as pool:
            for variant, items in groups.items():
                tree.set_variant(*table[variant])
                jobs = [(guard, data, pool.submit(compare, tree, guard, cls, data, sampled))
                        for cls, data, sampled in items for guard in GUARDS if cls in CLASSES[guard]]
                for guard, data, job in jobs:
                    for label, want, got in job.result():
                        if want == got and "timeout" not in (want[0], got[0]):
                            passed += 1
                            continue
                        failed += 1
                        cut = f"{data[:300]!r}{' ...' if len(data) > 300 else ''}"
                        print(f"  FAIL  {guard} guard, {label}, state '{variant}', seed {seed}")
                        print(f"        payload {cut}")
                        print(f"        frozen copy:  {show(want)}")
                        print(f"        {label + ':':<13} {show(got)}")
    if not passed + failed:
        failed = 1
        print("  FAIL  nothing was compared: a differential that runs no payload proves nothing")
    print(f"guard differential: {passed} passed, {failed} failed (seed {seed}, n {n})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
