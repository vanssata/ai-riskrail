# Intent: OS-independent installer and packaging for Anthropic and OpenAI

<!-- Stage 1 of the SDLC flow. Say WHAT and WHY. Leave HOW to the spec. -->

## Problem

- Installation today is `install.sh` (1104 lines of bash) and it needs `jq` and `python3`
  (`install.sh:80-81`). A Windows user cannot install the module at all, and on macOS and Linux
  `jq` is an extra prerequisite that the hooks themselves never use.
- The only distribution channel is "clone the repo and run the script". A `.codex-plugin/plugin.json`
  exists, but there is no Claude Code plugin manifest (`.claude-plugin/`) and no marketplace entry.
- The SDLC skills cannot be uploaded on their own to claude.ai, the Claude API (Skills) or OpenAI.
  People who only want `/sdlc-intent` → `/sdlc-spec` → `/sdlc-plan` have no way to get them without
  the full local install.

## Proposed outcome

1. A user on Linux, macOS or Windows (with Git Bash) runs one install command and ends up with the
   same installed result that `install.sh` produces on Linux today: same files, same managed
   `CLAUDE.md`/`AGENTS.md` block, same settings and hooks.
2. The installer requires only Python 3. `jq` is no longer a prerequisite.
3. `install.sh` keeps working with every existing flag (`--fable`, `--codex-plan`, `--dry-run`, …)
   and produces an identical result on Linux. It is now a thin wrapper over the new installer.
4. A user can install the module as a **Claude Code plugin** from the GitHub repository (a
   marketplace manifest plus a plugin manifest), and as a **Codex plugin** through the existing
   `.codex-plugin/`.
5. A release produces standalone **Agent Skill zips** (one `SKILL.md` folder per zip) that can be
   uploaded to claude.ai, the Claude API Skills endpoint and OpenAI. Only skills that are safe
   without hooks are included: `sdlc-intent`, `sdlc-spec`, `sdlc-plan`, `usage-report` and
   `ai-audit` are the candidates. `ai-task` and the other skills that depend on guards ship only
   inside the plugins.
6. CI runs the install, the `--dry-run` and the test suite on ubuntu, macos and windows, and it is
   green on all three.
7. A release job builds both plugin packages and every skill zip as downloadable artifacts. No one
   has to assemble them by hand.

## Affected users & systems

- **Users:** solo developers on Claude Code and/or Codex. This adds Windows users and people who
  only use claude.ai or the API.
- **Code:**
  - `install.sh`;
  - `scripts/` (`merge-codex-config.py`, `render-codex-agents.py`, `resolve-profile.py`);
  - `hooks/` (three of them are `.sh`: `ai-git-guard`, `ai-path-guard`, `ai-scope-guard`);
  - `skills/*`, `.codex-plugin/plugin.json`, a new `.claude-plugin/` and the marketplace manifest;
  - `README.md` install section and `VERSION`.
- **CI:** `.github/workflows/tests.yml` (to become a matrix) and a new release/packaging job. It sits
  next to `generator-generic-ossf-slsa3-publish.yml`.
- **Install roots:** `~/.claude/` and `~/.codex/` (respecting `CLAUDE_CONFIG_DIR` and `CODEX_HOME`).

## Constraints

- Production behaviour is the source of truth: on Linux the installed result must not change. That
  covers files, backups, the merged managed block, `profile.json` and the settings merge.
- Windows may require Git Bash. Native PowerShell or cmd without bash is not required.
- Python 3 is the only runtime dependency.
- The guards must not be weakened. Wherever the plugin form is installed, the hooks must still be
  registered. Anything shipped without hooks must not contain a guard-dependent skill.
- No agent commits, pushes, merges or deploys. Publishing a release stays a human action.
- This must not be mixed with a refactoring of unrelated installer behaviour.

## Out of scope

- Native Windows without bash (PowerShell or cmd only).
- A self-contained binary per OS.
- Submitting to official catalogues (Anthropic plugin directory, OpenAI listing).
- Making `ai-task` or the guards work without hooks (on claude.ai, in the API or in OpenAI).
- Changing the pipeline, the risk tiers, the routing or the guard semantics.

## Decisions taken

- **Which operating systems must the installer work on natively (no WSL/Git Bash)?** — Linux + macOS + Windows, but Windows may require Git Bash *(Q1, by vanssa via prose at 2026-10-02T18:38:06Z)*
- **What should 'packaged for Anthropic and OpenAI' produce?** — A plus standalone Agent Skills (SKILL.md zips) uploadable to claude.ai / Claude API Skills and OpenAI skills *(Q2, by vanssa via prose at 2026-10-02T18:39:14Z)*
- **Standalone skill uploads (claude.ai / API / OpenAI) run without hooks, so no guards. What is acceptable?** — Upload only the skills that are safe without guards (e.g. sdlc-intent/spec/plan, usage-report, ai-audit); ai-task and guard-dependent skills ship only in the plugins *(Q3, by vanssa via prose at 2026-10-02T18:40:04Z)*
- **What happens to the existing install.sh and its users?** — The new installer replaces install.sh; same flags and same result on Linux, install.sh kept as a thin wrapper *(Q4, by vanssa via prose at 2026-10-02T18:40:49Z)*
- **What may the installer require on the user's machine?** — Python 3 only (already needed by the hooks); jq no longer required *(Q5, by vanssa via prose at 2026-10-02T18:41:16Z)*
- **How is 'works on every OS' and 'packages are valid' proven?** — CI matrix (ubuntu, macos, windows) runs install + dry-run + test suite; a release job builds the plugin and skill zips as artifacts *(Q6, by vanssa via prose at 2026-10-02T18:41:51Z)*

## Open questions

1. **(blocking)** What exactly does each target accept today?
   - The Claude Code plugin and marketplace manifest schema.
   - claude.ai and Claude API Skills: zip layout, size and file limits, whether scripts are allowed.
   - The format for OpenAI skills or plugin uploads.
   The spec must cite current documentation for each one.
2. **(blocking)** Which skills are really "safe without guards"? Candidates: `usage-report` reads
   local transcripts and `ai-audit` writes one file. Do the `sdlc-*` skills still depend on
   `state.py`, and so on `$AI_HOME`, when there is no local install?
3. How does the Claude Code plugin form register the hooks and the managed `CLAUDE.md` block that
   `install.sh` writes today? Does the plugin replace the installer for Claude Code users, or does
   it add to it?
4. On Windows with Git Bash, do the `.sh` hooks and the `python3` invocation in the hook commands
   resolve correctly? (On Windows the executable is often `python` or `py`.)
5. What does Linux equivalence mean in practice? It needs a golden comparison of the installed
   tree before and after (`--dry-run` output plus the file tree), and the spec must define that
   check.
6. Do the skill zips get their own version, or do they follow `VERSION` (2.0.2)?
