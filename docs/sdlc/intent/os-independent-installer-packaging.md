# Intent: OS-independent interactive installer, packaging for Anthropic and OpenAI, clearer human interaction, and conflict-free multi-machine work

<!-- Stage 1 of the SDLC flow. Say WHAT and WHY. Leave HOW to the spec. -->

## Problem

**Installing and running on more than Linux**

- Installation today is `install.sh` (1104 lines of bash) and it needs `jq` and `python3`
  (`install.sh:80-81`). A Windows user cannot install the module at all.
- `jq` is a hidden run-time dependency as well. The three guards read their payload with it and
  **allow everything** when it is missing (`hooks/lib/ai-hook-common.sh:47`; failing open is the
  stated policy, `:15`). A machine without `jq` is unguarded and nobody is told.
- The run time is tied to POSIX, not only the installer:
  - the guards treat only a path that starts with `/` as absolute (`ai-hook-common.sh:196-199`)
    and compare paths case-sensitively;
  - `state.py` has no lock where `fcntl` is missing (`:68-71`, `:1582`), and `approve` needs a
    terminal on stdin (`:2490`);
  - `sensors.py:607` runs the project's commands through the platform shell;
  - the repository has no `.gitattributes`, so a checkout that converts line endings breaks the
    shell scripts;
  - the Python hooks read their payload in the platform's default text encoding
    (`hooks/context-guard.py:598`) and `state.py` prints characters outside ASCII, so under a
    Windows code page that is not UTF-8 a Cyrillic prompt or an arrow can stop them (inferred
    from the code, not yet run on Windows).
- Nothing notices a guard that is not running. Codex skips a hook whose entry has changed until
  the human approves it again, "and nothing on screen says so" (`README.md`, Known risks), and no
  command checks that a guard has answered. Every package below that touches a guard's entry
  would leave Codex users unguarded in exactly that way.
- The code needs Python 3.11 (`scripts/merge-codex-config.py:31` imports `tomllib`), but the
  installer only checks that `python3` exists (`install.sh:81`).
- Logic that depends on the operating system is repeated. Seven shell scripts outside `tests/`
  carry it (`install.sh`, the three guards, `hooks/lib/ai-hook-common.sh`,
  `hooks/project-scaffold.sh`, `skills/ai-init/scaffold-ai.sh`), and so does the bash launcher
  `bin/claude-1m`. In Python, the runtime's home directory is worked out in four files and the
  atomic write in seven.
- The 25 test suites are bash, need `jq` (`tests/run-all.sh:6`) and use GNU-only `sed -i`,
  `stat -c` and `sha256sum`. CI runs them on ubuntu only (`.github/workflows/tests.yml`).

**Distribution**

- The only distribution channel is "clone the repo and run the script". A
  `.codex-plugin/plugin.json` exists, but it declares only `skills`, so a user who installs it
  gets `ai-task` without its guards. There is no Claude Code plugin manifest (`.claude-plugin/`)
  and no marketplace entry. No package manager can install the module either: the repository has
  neither a `pyproject.toml` nor a `package.json`.
- The SDLC skills cannot be uploaded on their own to claude.ai, the Claude API (Skills) or OpenAI.
  People who only want `/sdlc-intent` → `/sdlc-spec` → `/sdlc-plan` have no way to get them without
  the full local install. `sdlc-intent` cannot run alone today: it calls `state.py` from the
  install root (`skills/sdlc-intent/SKILL.md:19-28`).
- The version is written in several places and nothing keeps them equal:
  `.codex-plugin/plugin.json:3` (the one `install.sh:182` reads) and three places in `README.md`.
  The provenance workflow still signs the template's `artifact1` and `artifact2`
  (`.github/workflows/generator-generic-ossf-slsa3-publish.yml:33-37`).
- An installed copy never learns that a newer version exists. `profile.json` records the
  installed version (`install.sh:182-186`), but nothing compares it with the latest release, and
  `/ai-status` only compares a project with the installed module. The module makes no network
  call today.

**Interaction**

- The installer barely interacts with the user. The only prompts are free-text `read -p` lines for
  the Claude and Codex plan (`install.sh:241-246`, `install.sh:862-865`). The user cannot choose
  from a list. The runtime is taken from `--target` or detected (`install.sh:65-66`, `:83-118`),
  never asked.
- Inside a session, the questions the pipeline asks the human are printed as plain text with
  "Reply `1B`" instructions (`state.py ask`). The native picker was specified in WP2 of
  `adaptive-cross-runtime-sdlc` (spec `:58-66`) and `state.py answer --via picker` exists, but no
  skill body renders through it: `skills/ai-task/SKILL.md:547-551` shows the markdown rendering
  only. Only `skills/ai-audit/SKILL.md` uses `AskUserQuestion`.
- Commands that the **human** must run in a terminal are mixed into prose. They are not visually
  separated from what the agent runs: approval, commit, `! <login>`, the next slash command.
- `/sdlc-intent` is rarely reached for. Vague or large requests go straight into `/ai-task`, and
  the intent brainstorm is text-heavy. This is the maintainer's observation; nothing measures it
  yet.

**Several machines**

- Working on one project from several computers, or as several people, produces git conflicts in
  the files the pipeline writes:
  - **Colliding task ids.** A task id is `T-<date>-<NNN>`, where `NNN` counts the existing
    `.ai/reports/` folders in this working tree only (`skills/ai-task/state.py:448-454`). Two
    machines — or two branches or worktrees on one machine — both create `T-2026-10-02-001` on
    the same day, so their reports, journals and questions collide when merged. `adopt-<date>`
    report folders collide the same way.
  - **Shared writable files.** A sensor run without a task writes `.ai/reports/sensors.json`
    (`sensors.py:1139` joins an empty task id), a committed file that every machine rewrites.
    Which other committed files are shared and mutable has not been inventoried.
  - **Different versions.** `state.py` never reads `.ai/VERSION`; only `/project-update` refuses
    a newer schema (`update.py:864-866`). A machine with an older install keeps writing the old
    layout into a project another machine has migrated.
  - **A task cannot follow its owner.** `current.json` and `handoff.md` are ignored while the
    task's `questions.md` and `events.jsonl` are committed, so a task started on one computer
    cannot be continued on another.
  - **Mixed tracking.** Most of `.ai/` is committed. Only `.ai/state/*.json`, `handoff.md` and
    `.ai/local/` are ignored. There is no supported way to keep the pipeline's records out of
    git, and no way to use the pipeline in a repository the user does not own without leaving
    files in it.

## Proposed outcome

**Run-time contract and OS independence**

1. A user on Linux, macOS, Windows with Git Bash, or WSL runs one install command and ends up with
   the same installed result that `install.sh` produces on Linux today from the same sources: the
   same files, the same managed `CLAUDE.md`/`AGENTS.md` block, the same settings and hooks. Only
   machine-specific paths differ.
2. At run time the module needs Python 3.11 or newer and git, and nothing else: no `jq`, and no
   shell script on the hook path or behind a skill. The installer checks the Python version, not
   only its presence, and says what to do when it is too old.
3. Everything that depends on the operating system is Python and exists once. The installer, the
   three guards, the two scaffolds and the launcher are Python. Home directories, runtime
   detection, atomic writes, locking and terminal detection live in one shared module that all of
   them use.
4. `install.sh` keeps working with every existing flag (`--target`, `--plan`, `--fable`,
   `--codex-plan`, `--dry-run`) and produces an identical result on Linux. It is now a thin
   wrapper over the new installer.
5. The pipeline works on every supported environment, not only the install: a task runs from
   start to close, each guard denies a payload it must deny and allows one it must allow, a hook
   command starts whichever shell the runtime uses to run it, and the human can grant an approval
   from their own terminal.
6. Guard rules mean the same everywhere. A path is compared the way the file system compares it:
   separators, drive letters, letter case. On Linux no decision changes.
7. An install proves that its guards answer. The installer ends by feeding every guard it
   registered one payload that must be denied, through the exact command line it registered. A
   guard that does not answer makes the install fail, and a failed install leaves the previous
   install in place and working. `/ai-status` runs the same check on demand. This proves the
   guard program. It cannot prove that the runtime calls it; outcome 29 does that.
8. The test suite is Python as well. New tests are written in Python from the start, and one
   runner runs them beside the bash suites. The existing suites are ported in their own work
   package after the code they test, and each suite is proven equivalent before its bash original
   is deleted. After that `jq` is not needed for development either.
9. CI runs the install, the `--dry-run`, the guard self-test and the test suite on ubuntu, macos
   and windows, and it is green on all three. WSL is covered by the ubuntu job. Until the port of
   the suites is finished, the macos and windows jobs run the suites that are already Python and
   the ubuntu job runs both kinds.

**Packaging**

10. A user can get the module through any of three channels:
    - a clone of the repository and `install.sh`;
    - the plugin manager of Claude Code (a marketplace manifest plus a plugin manifest in the
      GitHub repository) and of Codex;
    - a package manager, with one command and without cloning anything: PyPI (`pipx run`, `uvx`
      or `pip`) and npm (`npx`).

    Every channel delivers the same package and runs the same installer. There is **one installed
    form**: skills keep their short names (`/ai-task`), hooks are registered once, and the plugin
    itself exposes no guard-dependent skill.
11. The package finds its own files relative to itself. No skill and no hook searches `~/.claude`
    and then `~/.codex` for a copy of the module, so two installed runtimes never pick each
    other's copy.
12. The installer installs into the directory the runtime reads. It honours `CLAUDE_CONFIG_DIR`
    and `CODEX_HOME`, and the hook commands it registers point there. Without those variables the
    result is unchanged. This is new behaviour: today the installer reads only `CLAUDE_DIR` and
    `CODEX_DIR` (`install.sh:57-58`).
13. The installer can remove what it installed (`--uninstall`), so removing the plugin does not
    leave an active copy behind with no way to take it out.
14. A release produces standalone **Agent Skill zips** (one `SKILL.md` folder per zip):
    - `sdlc-intent`, `sdlc-spec` and `sdlc-plan` for every surface: claude.ai, the Claude API,
      the OpenAI API and a local skills directory. They are self-contained: the templates are
      bundled, questions are asked in prose, nothing calls `state.py`, and the frontmatter fits
      each surface's limits.
    - `usage-report` and `ai-audit` only for a local runtime (a Claude Code or Codex skills
      directory), because they read the user's files.
    - `ai-task` and every other guard-dependent skill ship only through the installer.
15. The version has one source. Every manifest (plugin, PyPI, npm), the README and every zip
    carry the same number, a test fails when they drift, and the release job refuses a tag that
    does not match.
16. A release job builds the plugin packages, the PyPI and npm packages and every skill zip as
    downloadable artifacts, with provenance for those files. No one has to assemble them by hand.
    A package reaches a registry only when a human publishes the release.

**Interactive installer**

17. Run on a terminal without flags, the installer asks each choice as a numbered list of options,
    with the detected or recommended option preselected so that Enter accepts it. The choices are:
    - the target runtime;
    - the Claude plan;
    - Fable;
    - the Codex plan;
    - whether to look for new versions;
    - whether to confirm before writing.
    Every choice made interactively can also be given as a flag. Without a terminal (CI, a pipe)
    the installer never prompts, and it behaves as it does today. What counts as a terminal is
    decided the same way on every supported environment.
18. Only one runtime is needed. This is today's behaviour and it is kept (`install.sh:83-118`): a
    user who has only Claude Code, or only Codex, completes the install, the missing runtime is
    reported as skipped, and a machine with neither gets one clear message that says how to
    proceed. The new part is that the runtime is offered as a choice.

**Human interaction inside Claude Code and Codex**

19. When a skill asks the human an ordinary multiple-choice question (`/sdlc-intent`, `/ai-task`'s
    `questions.md`, `/project-init`), Claude Code shows it in the native selectable picker, the
    same UI as model selection. This finishes what WP2 of `adaptive-cross-runtime-sdlc` specified.
    There is one rule:
    - the picker, in an interactive main session, for a question with up to four options;
    - numbered prose everywhere else: a subagent, a headless run, `AI_UNATTENDED`, more than four
      options, Codex unless it turns out to have a usable picker, and the standalone skill zips.
    Where `state.py` is installed the answer is recorded through it (`answer --via picker`), so
    the files stay the source of truth.
20. A gate is never a picker. T3 plan approval stays plan mode. T4+ plan gates, the final approval
    and lowering a tier stay `state.py approve` in the human's terminal, or the `[Answer]:` line.
21. Every command the human must run in their own terminal, rather than one the agent runs, is
    shown in one consistent, unmistakable format: a labelled, copy-pasteable block. A reader can
    tell at a glance what to execute, where to execute it, and that the agent will not run it.
    The format is defined in one place, and a test fails when a command only a human may run (an
    approval, a commit, a push, `git rm --cached`, a login) appears in a skill body outside that
    block.
22. `/sdlc-intent` is used more often, in two ways:
    - **The agent proposes it.** When a request is vague or large, `/ai-task` proposes
      `/sdlc-intent` first instead of planning straight away. The rule lives in the `/ai-task`
      body, not in the always-loaded block, which already sends a plain request to `/ai-task`.
    - **It is lighter to use.** The brainstorm asks up to four related questions per turn through
      the picker, each with two to four options, so that choosing it costs the human little.
    Whether it worked is read from files already on disk, against today's value as the baseline.

**Conflict-free work from several machines and people**

23. **Shared by default, and conflict-free by construction, for records.** The files the pipeline
    writes are of two kinds:
    - **records**, written by a command for one task: everything under `.ai/reports/<task-id>/`
      and `.ai/state/`;
    - **curated documents**, which people review: the knowledge base in `.ai/project/`, the
      policies, `CLAUDE.md`, the constitution. They merge like code and are not part of this
      guarantee.

    Two or more machines or people can work on the same project at the same time, each running
    its own tasks, and push and pull through git. Merging their branches never produces a
    conflict in a record:
    - task ids and `adopt` report ids are unique across machines, people, branches and worktrees,
      with no coordination;
    - no record is a shared mutable file, and nothing is written at the top of `.ai/reports/`;
    - aggregate data is derived when it is read, or written per task.

    "Never" means a test: two simulated machines with different line-ending settings each run
    whole tasks, a sensor run without a task and `/project-update` at the same version; their
    output is merged, and the test proves zero conflicts.
24. A machine whose install is older than the project's schema refuses to start a task and says
    to update. It never writes the old layout into a migrated project.
25. A task in flight can move to another machine, explicitly. One command parks it so that its
    state travels with a commit; another resumes it on the other machine. Nothing moves
    implicitly, and one machine owns the task at a time.
26. **Optional local mode, in two levels.**
    - **Records local** (for the whole project): the records are git-ignored and stay on each
      machine; curated documents stay shared. It can be chosen when a project is initialised
      (`/ai-init`, `/project-init`), and an existing project can be switched to it and back. The
      human is shown exactly which tracked files git will stop tracking, and a clone that pulls
      the switch can restore its own copies with one command.
    - **No trace** (for one clone): for a repository the user does not own. The whole footprint
      (`.ai/`, `docs/sdlc/`, the runtime folders) stays out of git through the clone's own exclude
      file. Nothing is committed, not even an ignore rule, and no file the repository already
      tracks is modified.

    The level in force is visible in `/ai-status`.
27. Existing projects keep working after the upgrade. Task ids, reports and journals created
    before the change are still read correctly, and they are never renamed silently.

**Staying up to date**

28. An installed copy learns about a new version and tells its user. The lookup is on by default.
    At most once a day, at session start, the copy looks up the latest released version. When the
    installed one is older, it shows the human one line: both version numbers and the exact
    command that updates a copy from the channel it came from. `/ai-status` shows the same on
    demand. One setting, which the installer also offers, turns the lookup off. The copy never
    updates itself.

    This reaches every install that starts a session while it is online and has not turned the
    lookup off. Nothing is pushed, because there is no list of installs.

**Proof beyond the install**

29. The pipeline notices a guard that the runtime is not calling. A task does not enter the
    implementation stage unless the guards have answered through the runtime in this session.
    When they have not (Codex has not trusted a changed hook, the interpreter has moved, hooks are
    switched off), the human is told what to do, instead of nothing on screen saying so.
30. An existing install upgrades in place. Re-running any channel's command replaces the hook
    entries that point at the old shell guards without duplicating them, removes the files that
    are no longer installed, and keeps the files the user owns.
31. What CI cannot prove is named and checked by hand. CI drives `state.py` and the guards
    directly; whether a live runtime on Windows and on macOS starts the hooks is a manual check
    for each release, and the release report records it.

## Affected users & systems

- **Users:** solo developers on Claude Code and/or Codex. This adds Windows users (Git Bash or
  WSL), people who install through pip or npm, people who only use claude.ai or the APIs, one
  developer on several computers, small teams sharing one repo, and people working in a
  repository they do not own.
- **Code to be ported to Python:**
  - `install.sh` (it stays as a wrapper);
  - `hooks/ai-git-guard.sh`, `hooks/ai-path-guard.sh`, `hooks/ai-scope-guard.sh` and
    `hooks/lib/ai-hook-common.sh`;
  - `hooks/project-scaffold.sh` and `skills/ai-init/scaffold-ai.sh`;
  - `bin/claude-1m`;
  - the 25 suites under `tests/`, with `lib.sh` and `run-all.sh`.
- **Python that changes:**
  - `scripts/` (`merge-codex-config.py`, `render-codex-agents.py`, `resolve-profile.py`);
  - the Python hooks (`cap-large-read.py`, `context-guard.py`, `runtime-gate.py` and its two
    shims);
  - `skills/ai-task/state.py` and `sensors.py`;
  - `skills/project-update/update.py`, `adopt.py` and `migrations/`;
  - `skills/usage-report/usage-report.py`.
- **Registration and manifests:** `settings.common.json`, `settings.gate.json`,
  `codex/hooks.json`; `.codex-plugin/plugin.json`; a new `.claude-plugin/` with the marketplace
  manifest; a Codex marketplace manifest; a new `pyproject.toml`; a new `package.json` with its
  launcher, the only code outside Python; a new `.gitattributes`.
- **Skill bodies:** `skills/*/SKILL.md`: the `jq` calls, the search for the install root, question
  rendering, and the commands handed to the human.
- **Documentation:** `README.md` (install section, version, known risks),
  `docs/getting-started.md`, `docs/faq.md`, `docs/hooks.md`, `docs/hook-performance.md`,
  `CONTRIBUTING.md`, `.ai/policies/testing.md`.
- **CI:** `.github/workflows/tests.yml` (to become a matrix), `pylint.yml`, a new release job, and
  `generator-generic-ossf-slsa3-publish.yml`.
- **Install roots:** `~/.claude/` and `~/.codex/`, or the directories named by
  `CLAUDE_CONFIG_DIR` and `CODEX_HOME`; `~/.local/bin/claude-1m`. The installer also reads
  `~/.claude.json` and `~/.codex/auth.json` to detect the plan.
- **Interaction:**
  - `skills/ai-task/state.py` (`ask`, `answer`, `questions`);
  - the skill bodies that ask questions or hand commands to the human (`sdlc-*`, `ai-task`,
    `project-init`, `project-update`, `ai-init`);
  - the managed instruction block in `CLAUDE.md` and `AGENTS.md`, and its source
    `instructions/stub.md`.
- **Multi-machine work:**
  - task id allocation and every record `state.py` and `sensors.py` write under `.ai/state` and
    `.ai/reports`; the `adopt` report folders;
  - both `gitignore.snippet` files (`skills/ai-init/templates/`, `skills/project-init/templates/`)
    and the `.gitignore` handling in `update.py` (`:785-798`), which only appends today;
  - `/ai-init`, `/project-init`, `/project-update` and `/ai-status`;
  - every user project that already has an `.ai/` directory.
- **Proof of the guards:** the guards and `skills/ai-task/state.py` (the proof that the runtime
  calls them); the installer (the self-test, the all-or-nothing install, the upgrade of existing
  hook entries); `.ai/policies/release.md` and `.ai/templates/release-report.md` (the manual
  check).
- **Update notice:** the session-start hook (`hooks/context-guard.py`); `/ai-status`; the
  installer, which records the channel a copy came from and the setting; `profile.json`; and the
  place where the module's first network call is documented (`README.md`, `SECURITY.md`).
- **Earlier work this builds on:** `docs/ai-sdlc-adoption-plan.md` (one package root, a
  deterministic check of the install, no double hooks), and WP2 and WP8 of
  `adaptive-cross-runtime-sdlc` (question rendering; the guards' hot path).

## Constraints

- Production behaviour is the source of truth. On Linux the installer writes the same result from
  the same sources: files, backups, the merged managed block, `profile.json`, the settings merge,
  the `--dry-run` output and the exit codes.
- Supported environments are Linux, macOS, Windows with Git Bash, and WSL. Native PowerShell or
  cmd without bash is not required.
- At run time the module depends on Python 3.11 or newer and git, and on nothing else. Node.js
  is needed only to fetch the package through npm, never at run time.
- Code that depends on the operating system is written once, in Python (Q11). No second
  implementation of the same logic is kept in shell. The npm launcher is the one exception: it
  only finds a Python interpreter and hands over to the installer.
- A port to Python is a refactoring: it changes no behaviour and is proven before anything else
  changes (C3). The guards are proven against the golden file, the installer against a golden
  install, each test suite against its bash original. A port is never mixed with a feature. A
  suite stays fixed while the code under it is ported, and the code stays fixed while its suite
  is ported.
- Refactoring is limited to what Q11 names. Unrelated installer behaviour is not redesigned.
- The guards must not be weakened. They fail open by design, so an install that cannot prove its
  guards answer is a failed install, not a warning. Anything shipped without hooks must not
  contain a guard-dependent skill, and that includes the plugin before its setup command has run.
- An install is all or nothing. When it fails, the previous install is still in place and
  working.
- The guard port gets a security review whatever its tier, because it rewrites the code that
  enforces the rules.
- No guard decision changes on Linux. Patterns in users' and projects' files stay POSIX extended
  regular expressions and match what they match today.
- The guards' hot path must not get slower: the budgets in `docs/hook-performance.md` hold on
  Linux.
- No agent commits, pushes, merges or deploys. Publishing a release, and publishing a package to
  a registry, stay human actions.
- A gate is never asked in a picker and never recorded by the agent (Q15, and decision 8 of
  `adaptive-cross-runtime-sdlc`).
- A non-interactive install (flags, CI, no TTY) must stay fully scriptable and must never block on
  a prompt.
- Native pickers are presentation only. Wherever `state.py` is installed, questions and answers
  are still written by it to `questions.md` and `<slug>.questions.md`, so a compaction, a `/clear`
  or a change of runtime loses nothing. A standalone skill zip has no `state.py` and writes its
  decisions into the intent file itself.
- The always-loaded instruction blocks stay within their byte budgets: 2048 B for a project block
  and 2560 B for the global one (`tests/test-instruction-budget.sh`).
- Proposing `/sdlc-intent` must not become a gate on small or clear changes, and it must not add a
  model call. A T0 or T1 fix stays a direct edit.
- The default for both new and existing projects is shared mode, so that today's committed
  `.ai/` knowledge (policies, project knowledge base, reports) keeps travelling with the repo.
- No agent runs `git rm --cached`, commits or pushes on its own. Switching a project to local mode
  prepares the change, and the human carries it out.
- Switching to local mode never loses data on any clone.
- In the "no trace" level the pipeline never modifies a file the repository already tracks.
- Text is UTF-8 everywhere: the payload a hook reads, what a command prints, and every file.
  Records are also written with LF line endings and `/`-separated relative paths, so a team on
  mixed systems gets no diff from the platform alone.
- Existing task ids and report folders stay valid, and none are renamed.
- The update check never delays or fails a session. It has its own short time limit, runs at most
  once a day per machine, and is silent when there is no network. It never runs in a headless or
  `AI_UNATTENDED` session.
- The update check sends nothing about the user or the project. Only a version number is read
  from the answer. Nothing that arrives from the network is executed, and the update command
  shown is built from the install's own record.
- The module never updates itself. Updating is a human action, shown in the human-command format.
- The update notice is for the human. It does not add to the always-loaded instructions.

## Out of scope

- Native Windows without bash (PowerShell or cmd only).
- A self-contained binary per OS.
- Submitting to official catalogues (Anthropic plugin directory, OpenAI listing).
- Package managers other than PyPI and npm (Homebrew, apt, winget, Chocolatey).
- A self-contained plugin whose guards and skills run from the plugin itself (Q13).
- Making `ai-task` or the guards work without hooks (on claude.ai, in the API or in OpenAI).
- `usage-report` and `ai-audit` on claude.ai or in the APIs (Q14): they need the user's files.
- Changing the pipeline, the risk tiers or the routing, or what a guard decides on Linux.
- A full-screen TUI installer (curses, arrow-key menus). Numbered options are enough.
- Making `/sdlc-intent` mandatory before `/ai-task`.
- Gates in a picker (Q15).
- Real-time coordination or locking between machines (a server, a lock service). Conflict-freedom
  comes from the file layout, not from a coordinator.
- Two people, or two machines, working on the **same** task at the same time.
- Conflict-freedom for curated documents (the knowledge base, the policies, `CLAUDE.md`, the
  constitution). They are reviewed text and merge like code.
- Resolving conflicts in application code. Only the pipeline's records are covered.
- Removing records from git history when a project switches to local mode.
- Usage reports across machines: transcripts stay on the machine that ran the session.
- Pushing a notice to installed copies (a server, telemetry, a list of installs).
- Automatic updates.

## Work packages

Each package runs `/sdlc-spec` → `/sdlc-plan` → `/ai-task` on its own; specs are named
`docs/sdlc/specs/os-independent-installer-packaging-wp<N>-<slug>.md`.

| WP | Package | Main files | Tier | Depends on | Status |
|---|---|---|---|---|---|
| 1 | Shared OS module and the guards in Python (refactoring) | the new shared module; `hooks/ai-git-guard.sh`, `hooks/ai-path-guard.sh`, `hooks/ai-scope-guard.sh`, `hooks/lib/ai-hook-common.sh`; the hook command lines in `settings.common.json` and `codex/hooks.json`; `install.sh` (the hook list and the upgrade of existing entries); `docs/hook-performance.md` | T3 (estimate), with a security review whatever the tier | — | open |
| 2 | Installer, scaffolds and launcher in Python (refactoring) | the new installer; `install.sh` as a wrapper; `scripts/*.py`; `hooks/project-scaffold.sh`; `skills/ai-init/scaffold-ai.sh`; `bin/claude-1m` | T3 (estimate) | 1 | open |
| 3a | Test runner for both kinds | a Python test runner that `tests/run-all.sh` and the verify command call beside the bash suites; `.ai/policies/testing.md`; `CONTRIBUTING.md` | T3 (path scope: `.ai/policies/**`) | — | open |
| 3b | Port of the 25 suites to Python (refactoring) | `tests/*.sh`, `tests/lib.sh`, `tests/run-all.sh`; the tool list in `.ai/policies/testing.md` | T3 (path scope: `.ai/policies/**`) | 1, 2, 3a | open |
| 4a | Guards proven at install and at run time | the guard self-test in the installer and in `/ai-status`; the all-or-nothing install; the proof that the runtime calls the guards (the guards, `skills/ai-task/state.py`); the manual check in `.ai/policies/release.md` and `.ai/templates/release-report.md` | T3 (path scope: `.ai/policies/**`), with a security review | 1, 2, 3a | open |
| 4b | Works on every supported environment | the Python 3.11 check; `.gitattributes`; UTF-8 for payloads, output and files; path rules in the guards; `skills/ai-task/state.py`, `sensors.py` and the Python hooks (locks, identity, terminal check, the shell for project commands); `CLAUDE_CONFIG_DIR` and `CODEX_HOME`; `--uninstall`; `.github/workflows/tests.yml` as a matrix | T5 (path scope: `.github/workflows/**`) | 1, 2, 3a, 4a | open |
| 5 | Interactive installer | the installer's prompts and flags; the install section of `README.md` | T2 (estimate) | 2, 4b | open |
| 6 | One package, three channels | package-relative lookup in `skills/*/SKILL.md` and the hooks; the single version source and its drift test; `.claude-plugin/plugin.json` and the marketplace manifest; the Codex plugin and marketplace manifest; the setup skill; `pyproject.toml`; `package.json` and its launcher | T3 (path scope: `pyproject.toml`, `package.json`) | 2 | open |
| 7 | Standalone skill zips and the release job | the zip builder; self-contained `sdlc-intent`, `sdlc-spec` and `sdlc-plan`; a new release workflow that also builds the PyPI and npm packages; `generator-generic-ossf-slsa3-publish.yml` | T5 (path scope: `.github/workflows/**`) | 6 | open |
| 8 | In-session interaction | `skills/*/SKILL.md` (picker rendering, the human-command block, the rule that proposes `/sdlc-intent`, the lighter brainstorm); `instructions/stub.md` and the block templates; the test for the human-command block | T3 (estimate) | 3a | open |
| 9 | Records without conflicts | `skills/ai-task/state.py` (ids, the version check); `sensors.py` (nothing at the top of `.ai/reports/`); `skills/project-update/adopt.py` (report ids); a schema migration; the two-machine test | T5 (path scope: `**/migrations/**`) | 3a | open |
| 10 | Park and resume | `skills/ai-task/state.py`; `/ai-status`; `skills/ai-task/SKILL.md` | T3 (estimate) | 9 | open |
| 11 | Local mode, two levels | `skills/project-update/update.py` (`.gitignore` handling); both `gitignore.snippet` files; the scaffolds; `/ai-init`, `/project-init`, `/project-update`, `/ai-status`; the restore command | T3, or T5 if it ships a migration | 9 | open |
| 12 | Update notice | `hooks/context-guard.py` (session start); the shared module (the version lookup and its once-a-day record); `/ai-status`; the installer (the channel record, the setting and its prompt); `README.md` and `SECURITY.md` | T3 (estimate); it is the module's first network call, so it gets a security review | 6, 7 | open |

Packages 1, 2 and 3b are refactorings (C3): each one ends with the same behaviour and the proof
of it. Package 3a only adds the runner, so that every later package writes its new tests in
Python at once. Features start at package 4a. A tier marked "path scope" follows
`.ai/policies/risk-tiers.json`; the others are estimates, and `ai-risk` assigns the real tier
when the task starts. A spec may split a package further.

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
- **The three guards read their payload with jq and allow everything when jq is missing. How is 'jq no longer required' (Q5) met?** — Port the three guards to Python as a behaviour-preserving refactoring, proven by the existing golden file; jq leaves the runtime entirely and the skill bodies stop calling it *(Q10, by vanssa via picker at 2026-10-02T19:37:52Z)*
- **What must be true on Windows when this is done?** — It must work both under Git Bash and under WSL. Everything that depends on the operating system is rewritten in Python, optimised and without repetition. (original: "Трябва да може да работи и на GitBash и на WSL. Всичко което е зависимо от операционната система трябва да се пренапише на python, като се оптимизира и се ибягва повторението.") *(Q11, by vanssa via picker at 2026-10-02T19:37:52Z)*
- **Q11 moves everything OS-dependent to Python. Does that include the 26 bash test suites?** — Yes — the suites are ported to Python too, in their own work package after the code ports, each suite proven equivalent before its bash original is deleted *(Q12, by vanssa via picker at 2026-10-02T19:48:20Z)*
- **What does 'install as a plugin' give the user, on Claude Code and on Codex?** — One installed form: the plugin delivers the package and one setup command that runs the same installer, so skills keep their short names (/ai-task), hooks are registered once, and there is no second form to keep in sync *(Q13, by vanssa via picker at 2026-10-02T19:48:20Z)*
- **Which standalone skill zips are built, and for which surfaces?** — sdlc-intent, sdlc-spec and sdlc-plan for every surface, self-contained (templates bundled, questions in prose, no state.py); usage-report and ai-audit only as zips for local runtimes (a Claude Code or Codex skills directory) *(Q14, by vanssa via picker at 2026-10-02T19:48:20Z)*
- **The intent lists 'plan approval' among the picker questions, but a gate is never recorded by the agent. What happens to gates?** — Gates never go through a picker: T3 plan approval stays plan mode; T4+ plan gates and the final approval stay state.py approve in the human's terminal or the [Answer]: line. The picker is for ordinary questions only *(Q15, by vanssa via picker at 2026-10-02T19:55:49Z)*
- **One developer, several computers: can a task that is in flight be continued on another machine?** — Yes, explicitly: one command parks the task so its state travels with a commit, another resumes it on the other machine; never implicit, and one machine owns the task at a time *(Q16, by vanssa via picker at 2026-10-02T19:55:49Z)*
- **What is local mode for?** — Both, as two levels of the same switch *(Q17, by vanssa via picker at 2026-10-02T19:55:49Z)*
- **The intent now covers several concerns. How is the work split?** — One intent with a Work packages table; each package gets its own spec, plan and task, in dependency order *(Q18, by vanssa via picker at 2026-10-02T19:55:49Z)*
- **The module must also install through a package manager, with one command and without cloning the repository. Which registry?** — Both registries, published from the one version source *(Q19, by vanssa via picker at 2026-10-02T20:21:05Z)*
- **An installed copy never learns that a newer version exists. How does it tell its user?** — On by default: at most once a day, at session start, the copy looks up the latest version and shows the human one line with the exact update command for the channel it came from; /ai-status shows the same on demand; one setting turns the lookup off; the copy never updates itself *(Q20, by vanssa via picker at 2026-10-02T20:49:05Z)*
- **A second review found seven gaps in what the intent promises. Which of them enter the intent?** — All seven *(Q21, by vanssa via picker at 2026-10-02T20:56:46Z)*
- **Three refactorings come before anything a user can see, and the port of the 25 suites sits on the path of packages 4 and 9. Is package 3 re-cut?** — Yes: package 3 becomes a small runner that runs bash and Python suites side by side, followed by the port itself; packages 4, 8 and 9 write their new tests in Python from the start and wait only for the runner *(Q22, by vanssa via picker at 2026-10-02T20:56:46Z)*

Three notes on the wording above:

- Q5 assumed that the hooks do not use `jq`. They do; Q10 replaces that premise.
- Q12 says 26 test suites. `tests/run-all.sh` runs 25.
- Q22 names packages 3 and 4 as they were numbered before the re-cut. They are 3a and 3b, and 4a
  and 4b, in the table above.

## Open questions

1. **(blocking for WP6 and WP7)** What exactly does each target accept today? The spec must cite
   current documentation for every line. A documentation search on 2026-10-02 reported the
   following, and none of it has been verified yet:
   - Claude Code plugin: `.claude-plugin/plugin.json` plus `.claude-plugin/marketplace.json`; a
     plugin's `settings.json` honours only `agent` and `subagentStatusLine`; a `CLAUDE.md` at the
     plugin root is not loaded; plugin skills are always `/plugin-name:skill`; a hook present in
     the user's settings and in a plugin runs twice; the plugin's path changes on every update.
   - claude.ai skill upload: a zip with the skill folder at its root; `name` up to 64 characters
     and without "claude" or "anthropic"; `description` up to 200 characters (ours are 291–372);
     no access to local files.
   - Claude API and OpenAI API: `POST /v1/skills`; the skill runs in a hosted container.
   - Codex: `plugin.json` at the plugin root, with `.codex-plugin/plugin.json` kept for
     compatibility; a plugin bundles skills and hooks, and agents are not documented; the
     marketplace file is `.agents/plugins/marketplace.json`; a new hook must be trusted before it
     runs; user skills are loaded from `$HOME/.agents/skills`, while the installer writes to
     `~/.codex/skills` today.

   Still unknown: the size and file limits of claude.ai and the Claude API; whether extra
   frontmatter keys (`argument-hint`) are accepted; whether `claude-agentic` is an acceptable
   plugin name.
2. **(blocking for WP6)** How does the plugin carry the whole package while exposing only the
   setup skill? A `skills/` directory at the plugin root is discovered as plugin skills, which
   would expose `ai-task` without guards. And how does the setup command find the package when
   the plugin's path changes on every update? With the package in a registry (Q19) the plugin may
   not need to carry it at all: its setup command could be the package-manager command.
3. **(blocking for WP4b)** On Windows under Git Bash, which shell does each runtime use to run hook
   commands and the agent's own commands? Is the interpreter `python3`, `python` or `py`? Does
   Claude Code have a PowerShell tool that a `Bash` matcher does not see? If Codex runs commands
   through PowerShell even when it is started from Git Bash, are the guards' command rules
   (written for POSIX shells) enough, or is that a documented limit?
4. **(blocking for WP4b)** `state.py approve` accepts a terminal on stdin as proof of a human. Does
   that hold in Git Bash's default terminal, where a native Windows Python often sees a pipe? If
   it does not, what proves a human there without opening a route the agent can use? The same
   test decides whether the installer prompts (WP5).
5. **(blocking for WP2)** What does Linux equivalence mean in practice? It needs a golden
   comparison of the installed tree, of the `--dry-run` output and of the exit codes, before and
   after, and the spec must define that check.
6. **(blocking for WP3b)** What proves a Python test suite equivalent to its bash original before
   the original is deleted?
7. **(blocking for WP1)** How do patterns keep their meaning? User and project files hold POSIX
   extended regular expressions (`[[:space:]]` appears 29 times in the shipped pattern files).
   The spec must show that they match the same inputs after the port. The golden file proves
   only the recorded cases, so the spec must also define a run of the old and the new guards
   side by side over generated inputs, and say what a guard does when a pattern takes too long
   to match.
8. What hook latency is acceptable on macOS and Windows? `docs/hook-performance.md` sets budgets
   that were measured on Linux only.
9. What makes a request "vague or large" enough for the agent to propose `/sdlc-intent`? Is it the
   risk tier, the number of files, missing acceptance criteria, or something else? This must not
   add a model call to every small task.
10. How is "used more often" counted from files already on disk, and what is today's value?
11. Is `request_user_input` in Codex usable as a picker? It was reported as unavailable in the
    default mode. Is `AskUserQuestion` available in a headless run and in a subagent? The rule in
    outcome 19 falls back to prose either way.
12. **(blocking for WP9)** Which files does the pipeline write, and which kind is each: record or
    curated document? The spec needs the full inventory of what `state.py`, `sensors.py`,
    `update.py`, `adopt.py` and the hooks write. Known shared mutable record so far:
    `.ai/reports/sensors.json`.
13. **(blocking for WP9)** What does the unique id look like? It has a random component, because a
    machine or user name does not separate two branches on one machine. It must stay short, keep
    the `T-YYYY-MM-DD-` prefix so that ids sort by date, and leave existing ids valid.
14. **(blocking for WP10)** What marks which machine owns a parked task, and what happens when two
    machines resume the same one? It must be detected and refused, not merged.
15. **(blocking for WP11)** Switching an existing project to "records local": which tracked files
    leave the index, and how does a clone that pulls the switch restore its own copies with one
    command?
16. **(blocking for WP11)** "No trace": where is the level recorded when nothing may be committed,
    and where do the project's instructions live when the repository already tracks `CLAUDE.md`
    or `AGENTS.md`?
17. `--uninstall`: what exactly is removed, and what happens to the `.bak` backups and to files
    the user owns (`ai-git-guard.json`)?
18. Do records name the person (the git identity) as well as the OS login, so that journals
    merged from several people stay attributable? `state.py` takes the name from `USER` today
    (`:2638`), which Git Bash does not always set.
19. **(blocking for WP6)** Under which name is the package published? `claude-agentic` and
    `claude-agentic-sdlc` were both unregistered on npm and on PyPI on 2026-10-02. The name should
    be the same in both registries, and the doubt in question 1 about "claude" in a name applies
    here too.
20. **(blocking for WP6)** `pipx run`, `uvx` and `npx` run the installer from a temporary
    environment. Which interpreter do the registered hook commands use, so that they keep working
    after that environment is gone? And what does the npm launcher say when it finds no
    Python 3.11?
21. **(blocking for WP7)** How does a package reach each registry? Either the release workflow
    publishes when a human publishes the release, or the human uploads by hand. In both cases no
    long-lived token is kept in the repository.
22. **(blocking for WP12)** Which source says what the latest version is: the GitHub release,
    PyPI or npm? They can disagree for a short time during a release. How does Codex show one
    line to the human at session start? And what does the notice say for a copy that came from a
    clone?
23. **(blocking for WP4a)** How does a guard leave proof that the runtime called it without
    breaking the hot-path budget, and what exactly does `state.py` require before a task enters
    implementation? What does the human see on Codex while a changed hook is not yet trusted?
24. Which packages make up which release, and is the first of them a major version? The guards'
    file names, the task id and the project schema all change.
