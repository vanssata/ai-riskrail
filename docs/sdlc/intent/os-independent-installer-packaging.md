# Intent: OS-independent interactive installer, packaging for Anthropic and OpenAI, clearer human interaction, and conflict-free multi-machine work

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
- The installer barely interacts with the user. The only prompts are free-text `read -p` lines for
  the Claude and Codex plan (`install.sh:241-246`, `install.sh:862-865`). The user cannot choose
  from a list, and nothing asks which runtime to install.
- Inside a session, the questions the pipeline asks the human are printed as plain text with
  "Reply `1B`" instructions (`state.py ask`). They are not shown as a native selectable picker like
  the one Claude Code uses for model selection. Only `skills/ai-audit/SKILL.md` uses `AskUserQuestion`.
- Commands that the **human** must run in a terminal are mixed into prose. They are not visually
  separated from what the agent runs: approval, commit, `! <login>`, the next slash command.
- `/sdlc-intent` is rarely reached for. Vague or large requests go straight into `/ai-task`, and
  the intent brainstorm is text-heavy.
- Working on one project from several computers, or as several people, produces git conflicts in
  the files the pipeline writes:
  - **Colliding task ids.** A task id is `T-<date>-<NNN>`, where `NNN` counts the existing
    `.ai/reports/` folders on this machine only (`skills/ai-task/state.py:453-454`). Two machines
    on the same day both create `T-2026-10-02-001`, so their reports, journals and questions
    collide when merged.
  - **Shared writable files.** Some committed files are rewritten by every machine, for example
    `.ai/reports/sensors.json`. Two machines editing them in parallel produce a merge conflict.
  - **Mixed tracking.** Most of `.ai/` is committed. Only `.ai/state/*.json`, `handoff.md` and
    `.ai/local/` are ignored. There is no supported way to keep a project's pipeline data local to
    one machine, either for a new project or for an existing one.

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

**Interactive installer**

8. Run on a terminal without flags, the installer asks each choice as a numbered list of options,
   with the detected or recommended option preselected so that Enter accepts it. The choices are:
   - the target runtime;
   - the Claude plan;
   - Fable;
   - the Codex plan;
   - whether to confirm before writing.
   Every choice made interactively can also be given as a flag. Without a terminal (CI, a pipe) the
   installer never prompts, and it behaves as it does today.
9. Only one runtime is needed. A user who has only Claude Code, or only Codex, completes the
   install, and only the runtime they chose is installed. The missing runtime is reported as
   skipped, not as an error. A machine with neither runtime gets one clear message that says how
   to proceed. It does not fail half-way.

**Human interaction inside Claude Code and Codex**

10. When a skill asks the human a multiple-choice question (`/sdlc-intent`, `/ai-task`'s
    `questions.md`, plan approval, `/project-init`), Claude Code shows it in the native selectable
    picker, the same UI as model selection. The answer is still recorded through `state.py`, so the
    files stay the source of truth. Codex uses its equivalent picker when it has one. Otherwise it
    falls back to the current text form.
11. Every command the human must run in their own terminal, rather than one the agent runs, is
    shown in one consistent, unmistakable format: a labelled, copy-pasteable block. A reader can
    tell at a glance what to execute, where to execute it, and that the agent will not run it.
12. `/sdlc-intent` is used more often, in two ways:
    - **The agent proposes it.** When `/ai-task` (or a plain request) is vague or large, the agent
      proposes `/sdlc-intent` first instead of planning straight away.
    - **It is lighter to use.** The brainstorm takes fewer turns and uses the native pickers, so
      that choosing it costs the human little.

**Conflict-free work from several machines and people**

13. **Shared by default, and conflict-free by construction.** Two or more machines or people can
    work on the same project at the same time, each running its own tasks, and push and pull
    through git. Merging their branches never produces a conflict in a file the pipeline writes:
    - task ids are unique across machines and people;
    - no committed file is a shared mutable file that two tasks rewrite;
    - aggregate data is either derived when it is read, or written per task or per machine.

    "Never" means a test that runs two simulated machines in parallel and merges their output, and
    it proves zero conflicts.
14. **Optional local-only mode.** A project can opt into a "local" mode in which the pipeline's
    project folders are git-ignored and stay on the machine:
    - the folders are `.ai/state`, `.ai/reports` and any other generated data that the spec
      identifies;
    - the mode can be chosen when a project is initialised (`/ai-init`, `/project-init`);
    - an existing project can be switched to it. The data already on disk is kept, and the human
      is shown exactly which tracked files git will stop tracking;
    - switching back to shared is possible too.

    The mode in force is visible in `/ai-status`.
15. Existing projects keep working after the upgrade. Task ids, reports and journals created before
    the change are still read correctly, and they are never renamed silently.

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
- **Interaction:**
  - `skills/ai-task/state.py` (`ask`, `answer`, `questions`);
  - the skill bodies that ask questions or hand commands to the human (`sdlc-*`, `ai-task`,
    `project-init`, `project-update`, `ai-init`);
  - the managed instruction block in `CLAUDE.md` and `AGENTS.md`.
- **Multi-machine work:**
  - task id allocation and every file `state.py` writes under `.ai/state` and `.ai/reports`
    (including `sensors.json` and the journals);
  - `hooks/project-scaffold.sh` and its `gitignore.snippet`;
  - `/ai-init`, `/project-init`, `/project-update` and `/ai-status`;
  - every user project that already has an `.ai/` directory.
- **Users (multi-machine):** one developer on several computers, and small teams sharing one repo.

## Constraints

- Production behaviour is the source of truth: on Linux the installed result must not change. That
  covers files, backups, the merged managed block, `profile.json` and the settings merge.
- Windows may require Git Bash. Native PowerShell or cmd without bash is not required.
- Python 3 is the only runtime dependency.
- The guards must not be weakened. Wherever the plugin form is installed, the hooks must still be
  registered. Anything shipped without hooks must not contain a guard-dependent skill.
- No agent commits, pushes, merges or deploys. Publishing a release stays a human action.
- This must not be mixed with a refactoring of unrelated installer behaviour.
- A non-interactive install (flags, CI, no TTY) must stay fully scriptable and must never block on
  a prompt.
- Native pickers are presentation only. Questions and answers are still written by `state.py` to
  `questions.md` and `<slug>.questions.md`, so a compaction, a `/clear` or a change of runtime loses
  nothing.
- Proposing `/sdlc-intent` must not become a gate on small or clear changes. A T0 or T1 fix stays a
  direct edit.
- The default for both new and existing projects is shared mode, so that today's committed
  `.ai/` knowledge (policies, project knowledge base, reports) keeps travelling with the repo.
- No agent runs `git rm --cached`, commits or pushes on its own. Switching a project to local mode
  prepares the change, and the human carries it out.
- Existing task ids and report folders stay valid, and none are renamed.

## Out of scope

- Native Windows without bash (PowerShell or cmd only).
- A self-contained binary per OS.
- Submitting to official catalogues (Anthropic plugin directory, OpenAI listing).
- Making `ai-task` or the guards work without hooks (on claude.ai, in the API or in OpenAI).
- Changing the pipeline, the risk tiers, the routing or the guard semantics.
- A full-screen TUI installer (curses, arrow-key menus). Numbered options are enough.
- Making `/sdlc-intent` mandatory before `/ai-task`.
- Real-time coordination or locking between machines (a server, a lock service). Conflict-freedom
  comes from the file layout, not from a coordinator.
- Two people working on the **same** task at the same time.
- Resolving conflicts in application code. Only pipeline-written files are covered.

## Decisions taken

- **Which operating systems must the installer work on natively (no WSL/Git Bash)?** — Linux + macOS + Windows, but Windows may require Git Bash *(Q1, by vanssa via prose at 2026-10-02T18:38:06Z)*
- **What should 'packaged for Anthropic and OpenAI' produce?** — A plus standalone Agent Skills (SKILL.md zips) uploadable to claude.ai / Claude API Skills and OpenAI skills *(Q2, by vanssa via prose at 2026-10-02T18:39:14Z)*
- **Standalone skill uploads (claude.ai / API / OpenAI) run without hooks, so no guards. What is acceptable?** — Upload only the skills that are safe without guards (e.g. sdlc-intent/spec/plan, usage-report, ai-audit); ai-task and guard-dependent skills ship only in the plugins *(Q3, by vanssa via prose at 2026-10-02T18:40:04Z)*
- **What happens to the existing install.sh and its users?** — The new installer replaces install.sh; same flags and same result on Linux, install.sh kept as a thin wrapper *(Q4, by vanssa via prose at 2026-10-02T18:40:49Z)*
- **What may the installer require on the user's machine?** — Python 3 only (already needed by the hooks); jq no longer required *(Q5, by vanssa via prose at 2026-10-02T18:41:16Z)*
- **How is 'works on every OS' and 'packages are valid' proven?** — CI matrix (ubuntu, macos, windows) runs install + dry-run + test suite; a release job builds the plugin and skill zips as artifacts *(Q6, by vanssa via prose at 2026-10-02T18:41:51Z)*
- **Point 5 ('sdlc-intent to be used more often'): what should change?** — Both A and B *(Q7, by vanssa via prose at 2026-10-02T18:50:45Z)*
- **Multi-machine/multi-person: what is the goal for task data (.ai/reports, .ai/state, docs/sdlc)?** — Shared via git but conflict-free by construction (unique task ids per machine/person, no shared mutable files) *(Q8, by vanssa via prose at 2026-10-02T18:59:43Z)*
- **Your request also asks for an option to make the project folders git-ignored/local, for new and existing projects. With 8A as the default, is that option still wanted?** — Yes — shared (8A) is the default; a 'local' opt-in git-ignores the folders, for new projects and by converting existing ones *(Q9, by vanssa via prose at 2026-10-02T19:00:25Z)*

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
7. **(blocking)** What native question UI exists in each runtime?
   - Claude Code: `AskUserQuestion` allows 1–4 questions and 2–4 options each. `state.py ask`
     allows up to six options, so how are the two reconciled?
   - Codex: is there an equivalent? If not, the text fallback stays.
8. What makes a request "vague or large" enough for the agent to propose `/sdlc-intent`? Is it the
   risk tier, the number of files, missing acceptance criteria, or something else? This must not
   add a model call to every small task.
9. This intent now covers four separate concerns:
   - OS-independence and packaging (outcomes 1–7);
   - the interactive installer (8–9);
   - in-session interaction (10–12);
   - multi-machine work (13–15).

   Should the spec stage split it into separate specs or plans so that each change stays
   reviewable on its own? Multi-machine work touches `state.py` and every existing user project,
   so it is the strongest candidate to stand alone.
10. **(blocking)** Which files does the pipeline write, and which of them are shared mutable files
    today? The spec needs a full inventory before choosing a layout. Known so far:
    `.ai/reports/sensors.json` and the per-day task-id counter. Others are unknown.
11. **(blocking)** What makes a task id unique across machines and people? It could be a machine or
    user suffix, a random component, or something else. It must stay short and sortable by date,
    and it must not break the existing `T-YYYY-MM-DD-NNN` ids.
12. In local mode, is `docs/sdlc/**` also local, or only `.ai/state` and `.ai/reports`? And are the
    policies and the project knowledge base (`.ai/policies`, `.ai/project`) always shared?
13. Switching an existing project to local mode: which already-committed files leave the index, and
    how does a teammate who pulls that change keep their own copy?
