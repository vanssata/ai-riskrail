"""The one OS module of the hooks (intent O3, spec R4).

Among hooks/ai-*-guard.py and hooks/lib/*.py, only this file reads HOME,
CLAUDE_CONFIG_DIR, CODEX_HOME or PWD, or calls os.getcwd, os.path.realpath or
subprocess. Each function reproduces the shell it replaces in
hooks/lib/ai-hook-common.sh, edges included: what bash's `cd` and `pwd` make of
`..`, symlinks and a leading `//`, and what `${VAR:-default}` makes of an empty
variable. Standard library only; it runs under `python3 -I -S`.
"""
from __future__ import annotations

import os

_HOMES = {"claude": ("CLAUDE_CONFIG_DIR", "/.claude"), "codex": ("CODEX_HOME", "/.codex")}


def runtime_home(runtime: str) -> str:
    """${CLAUDE_CONFIG_DIR:-$HOME/.claude} for "claude", ${CODEX_HOME:-$HOME/.codex} for "codex".

    An empty variable counts as unset, as `:-` has it; an unset HOME reads as
    empty, as bash expands it.
    """
    var, tail = _HOMES[runtime]
    return os.environ.get(var) or os.environ.get("HOME", "") + tail


def hook_config_dirs(hook_dir: str) -> list[str]:
    """Where runtime_hook_config looks for a guard's config, in order (ai-hook-common.sh:94)."""
    dirs = (hook_dir, runtime_home("claude") + "/hooks", runtime_home("codex") + "/hooks")
    return [d for d in dirs if d]


def _canon(path: str) -> str | None:
    """bash's sh_canonpath(PATH_CHECKDOTDOT | PATH_CHECKEXISTS) of an absolute path.

    `.` and repeated slashes go, and `..` drops the component before it once
    that prefix is a directory. Exactly two leading slashes stay, as POSIX
    allows. None when a prefix the walk depends on, or the result, is not a
    directory.
    """
    lead = "//" if path[:2] == "//" and path[2:3] != "/" else "/"
    parts: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part != "..":
            parts.append(part)
        elif parts:
            if not os.path.isdir(lead + "/".join(parts)):
                return None
            parts.pop()
    result = lead + "/".join(parts)
    return result if os.path.isdir(result) else None


def logical_cwd() -> str:
    """The working directory as bash starts with it.

    An inherited $PWD that is absolute and names the same directory as "." is
    kept, canonicalised; anything else falls back to getcwd().
    """
    pwd = os.environ.get("PWD", "")
    try:
        if pwd[:1] == "/" and os.path.samefile(pwd, "."):
            return _canon(pwd) or os.getcwd()
    except OSError:
        pass
    return os.getcwd()


def resolve_dir(path: str, base: str) -> str | None:
    """`cd "$path" && pwd` run from the logical directory base, in bash's default -L mode.

    The joined path is normalised lexically, so the symlinks it passes through
    stay in it, and that directory is the answer when one may enter it. When
    the normalisation fails, or its directory cannot be entered, bash changes
    into the path as written and answers with getcwd(), the physical directory.
    None when neither can be entered; `cd ""` fails in bash too.
    """
    if not path:
        return None
    full = path if path[:1] == "/" else base + ("" if base.endswith("/") else "/") + path
    canon = _canon(full)
    if canon is not None and os.access(canon, os.X_OK):
        return canon
    if os.path.isdir(full) and os.access(full, os.X_OK):
        return os.path.realpath(full)
    return None


def find_ai_root(start: str) -> str | None:
    """The nearest directory, from start upwards, that holds a .ai/ directory (ai-hook-common.sh:182-192).

    start is resolved as `cd "$start" && pwd` from the logical working
    directory. The walk drops one component at a time, as `${d%/*}` does, and
    "/" is tried last. None when start is empty, cannot be entered, or no
    directory on the way holds .ai/. The shell's `${1:-$AI_CWD}` default is the
    caller's: every guard passes its cwd, which is never empty.
    """
    if not start:
        return None
    d = resolve_dir(start, logical_cwd())
    if d is None:
        return None
    d = d.rstrip("\n")                    # $(...) drops the trailing newlines
    while d and d != "/":
        if os.path.isdir(d + "/.ai"):
            return d
        d = d[:d.rfind("/")] or "/"
    return "/" if os.path.isdir("/.ai") else None


def abs_path(path: str, cwd: str) -> str:
    """path made absolute against cwd, without normalising (ai-hook-common.sh:196-202).

    One trailing slash of cwd goes, as `${AI_CWD%/}` drops it; symlinks and
    `..` stay as they are.
    """
    if path[:1] == "/":
        return path
    return (cwd[:-1] if cwd.endswith("/") else cwd) + "/" + path


def real_path(path: str, cwd: str) -> str:
    """abs_path, resolved through every symlink when it exists (ai-hook-common.sh:205-213)."""
    full = abs_path(path, cwd)
    return os.path.realpath(full) if os.path.exists(full) else full


def run_git(cwd: str, *args: str) -> str | None:
    """`git -C cwd args...` without a shell: its stdout, or None when git cannot run or fails.

    stdin and stderr are /dev/null: the guards' git calls ran with `2>/dev/null`,
    after the payload had used up stdin. subprocess is imported here rather than
    at the top because most guard runs never ask git anything.
    """
    import subprocess
    try:
        proc = subprocess.run(["git", "-C", cwd, *args], stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")
