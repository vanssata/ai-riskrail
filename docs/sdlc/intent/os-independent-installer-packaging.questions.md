# Questions — os-independent-installer-packaging
<!-- Written by state.py. Answer with `state.py answer Q1=B`, or fill the [Answer]: lines and run
     `state.py questions --sync`. Do not edit the questions themselves. -->

## Q1. Which operating systems must the installer work on natively (no WSL/Git Bash)?
asked: 2026-10-02T18:37:10Z · stage: intent
A. Linux + macOS + Windows (native PowerShell/cmd) (recommended)
B. Linux + macOS only; Windows via WSL is acceptable
C. Linux + macOS + Windows, but Windows may require Git Bash
X. Other — answer as `X: <text>`
[Answer]: C — by vanssa via prose at 2026-10-02T18:38:06Z

## Q2. What should 'packaged for Anthropic and OpenAI' produce?
asked: 2026-10-02T18:38:07Z · stage: intent
A. Claude Code plugin (.claude-plugin + marketplace.json) and Codex plugin (.codex-plugin), installable from the GitHub repo
B. A plus standalone Agent Skills (SKILL.md zips) uploadable to claude.ai / Claude API Skills and OpenAI skills (recommended)
C. Only standalone Agent Skills zips, no plugin manifests
D. Publish to official marketplaces/registries (Anthropic plugin directory, OpenAI listing)
X. Other — answer as `X: <text>`
[Answer]: B — by vanssa via prose at 2026-10-02T18:39:14Z

## Q3. Standalone skill uploads (claude.ai / API / OpenAI) run without hooks, so no guards. What is acceptable?
asked: 2026-10-02T18:39:14Z · stage: intent
A. Upload only the skills that are safe without guards (e.g. sdlc-intent/spec/plan, usage-report, ai-audit); ai-task and guard-dependent skills ship only in the plugins (recommended)
B. Upload all skills; each degraded skill states clearly that guards are absent
C. Upload all skills unchanged
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via prose at 2026-10-02T18:40:04Z

## Q4. What happens to the existing install.sh and its users?
asked: 2026-10-02T18:40:04Z · stage: intent
A. The new installer replaces install.sh; same flags and same result on Linux, install.sh kept as a thin wrapper (recommended)
B. install.sh stays as-is; the new installer is an additional entry point
C. install.sh is removed; plugin install becomes the only path
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via prose at 2026-10-02T18:40:49Z

## Q5. What may the installer require on the user's machine?
asked: 2026-10-02T18:40:49Z · stage: intent
A. Python 3 only (already needed by the hooks); jq no longer required (recommended)
B. Python 3 + jq (as today), plus Git Bash on Windows
C. Nothing — a self-contained binary per OS
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via prose at 2026-10-02T18:41:16Z

## Q6. How is 'works on every OS' and 'packages are valid' proven?
asked: 2026-10-02T18:41:16Z · stage: intent
A. CI matrix (ubuntu, macos, windows) runs install + dry-run + test suite; a release job builds the plugin and skill zips as artifacts (recommended)
B. CI matrix only; packages built manually by the maintainer
C. Manual testing on each OS before release
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via prose at 2026-10-02T18:41:51Z

## Q7. Point 5 ('sdlc-intent to be used more often'): what should change?
asked: 2026-10-02T18:48:58Z · stage: intent
A. The agent proactively suggests /sdlc-intent when a request is vague or large (e.g. /ai-task on an unclear request routes to an intent first)
B. Make the intent interaction lighter (fewer questions, native pickers) so people choose to use it more
C. Both A and B (recommended)
D. Opposite — reduce how often sdlc-intent is needed
X. Other — answer as `X: <text>`
[Answer]: C — by vanssa via prose at 2026-10-02T18:50:45Z

## Q8. Multi-machine/multi-person: what is the goal for task data (.ai/reports, .ai/state, docs/sdlc)?
asked: 2026-10-02T18:58:54Z · stage: intent
A. Shared via git but conflict-free by construction (unique task ids per machine/person, no shared mutable files)
B. Local only (git-ignored); nothing is shared between machines
C. Both, as a per-project mode chosen at init and switchable later: 'shared' (A) or 'local' (B) (recommended)
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via prose at 2026-10-02T18:59:43Z

## Q9. Your request also asks for an option to make the project folders git-ignored/local, for new and existing projects. With 8A as the default, is that option still wanted?
asked: 2026-10-02T18:59:43Z · stage: intent
A. Yes — shared (8A) is the default; a 'local' opt-in git-ignores the folders, for new projects and by converting existing ones (recommended)
B. No — shared (8A) only; drop the local-only option
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via prose at 2026-10-02T19:00:25Z

## Q10. The three guards read their payload with jq and allow everything when jq is missing. How is 'jq no longer required' (Q5) met?
asked: 2026-10-02T19:29:03Z · stage: intent
context: hooks/lib/ai-hook-common.sh:47 exits 0 (allow) without jq, and the guards fail open by design (:15); Q5 assumed the hooks never use jq. The golden file tests/fixtures/guard-characterization/golden.txt (2461 lines) pins today's exact behaviour.
A. Port the three guards to Python as a behaviour-preserving refactoring, proven by the existing golden file; jq leaves the runtime entirely and the skill bodies stop calling it (recommended)
B. Keep the bash+jq guards; jq stays a runtime prerequisite on every OS and the installer keeps checking for it (this revises Q5)
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T19:37:52Z

## Q11. What must be true on Windows when this is done?
asked: 2026-10-02T19:29:03Z · stage: intent
context: Q1 was about the installer. The runtime is POSIX-bound today (guard paths, state.py locks and TTY check, sensors.py shell=True). Per the Codex docs, Codex on native Windows runs commands and hooks through PowerShell; Claude Code uses Git Bash when it is installed. Both facts are to be re-verified in the spec.
A. Claude Code on Windows with Git Bash runs the whole pipeline and every guard is proven to deny there; Codex on Windows is supported through WSL only, native Codex under PowerShell is out of scope (recommended)
B. Both runtimes native on Windows with full guard parity, including command rules for PowerShell
C. The installer only; the pipeline and the guards on Windows are a later intent, and the installer says so when it runs on Windows
X. Other — answer as `X: <text>`
[Answer]: X: It must work both under Git Bash and under WSL. Everything that depends on the operating system is rewritten in Python, optimised and without repetition. (original: "Трябва да може да работи и на GitBash и на WSL. Всичко което е зависимо от операционната система трябва да се пренапише на python, като се оптимизира и се ибягва повторението.") — by vanssa via picker at 2026-10-02T19:37:52Z

## Q12. Q11 moves everything OS-dependent to Python. Does that include the 26 bash test suites?
asked: 2026-10-02T19:38:35Z · stage: intent
context: tests/run-all.sh needs jq; the suites use GNU-only sed -i, stat -c, sha256sum, declare -A. They are also the proof that each port changes no behaviour, so they must stay fixed while the code under them moves.
A. No — production code only (installer, guards, scaffolds, launcher). The suites stay bash as the regression net, are made portable, and jq becomes a development-only dependency (recommended)
B. Yes — the suites are ported to Python too, in their own work package after the code ports, each suite proven equivalent before its bash original is deleted
C. Only the OS-sensitive helpers move into one shared Python test helper; the suites themselves stay bash
X. Other — answer as `X: <text>`
[Answer]: B — by vanssa via picker at 2026-10-02T19:48:20Z

## Q13. What does 'install as a plugin' give the user, on Claude Code and on Codex?
asked: 2026-10-02T19:38:35Z · stage: intent
context: Per the docs (to re-verify in the spec): a Claude Code plugin cannot write user settings, cannot add a CLAUDE.md, cannot render agents per plan; its skills are always /plugin-name:skill; a hook registered both in settings.json and by a plugin runs twice. A Codex plugin bundles skills and hooks, not agents.
A. One installed form: the plugin delivers the package and one setup command that runs the same installer, so skills keep their short names (/ai-task), hooks are registered once, and there is no second form to keep in sync (recommended)
B. A self-contained plugin: guards and skills run from the plugin itself (skills become /claude-agentic:ai-task), plus a one-time configure step for settings, per-plan agents and the profile; the installer form and the plugin form exclude each other
C. No plugin in this intent: the installer and the skill zips only; plugins get their own intent once the installer is done
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T19:48:20Z

## Q14. Which standalone skill zips are built, and for which surfaces?
asked: 2026-10-02T19:38:35Z · stage: intent
context: claude.ai and the Claude and OpenAI APIs run a skill in a container with no access to the user's files. usage-report reads local transcripts and ai-audit audits a local repository. sdlc-intent needs state.py and the docs/sdlc templates today. Skill descriptions are 291–372 characters; claude.ai allows 200.
A. sdlc-intent, sdlc-spec and sdlc-plan for every surface, self-contained (templates bundled, questions in prose, no state.py); usage-report and ai-audit only as zips for local runtimes (a Claude Code or Codex skills directory) (recommended)
B. Only sdlc-intent, sdlc-spec and sdlc-plan, self-contained, for every surface; usage-report and ai-audit ship only inside the installer and the plugin
C. All five on every surface, as Q3 listed them
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T19:48:20Z

## Q15. The intent lists 'plan approval' among the picker questions, but a gate is never recorded by the agent. What happens to gates?
asked: 2026-10-02T19:48:55Z · stage: intent
context: state.py refuses a gate through ask (:1778) and through answer (:1890); decision 8 of adaptive-cross-runtime-sdlc says the agent can never approve. Today a gate is granted by state.py approve in a terminal, or by the [Answer]: line behind a human turn that the context-guard hook recorded.
A. Gates never go through a picker: T3 plan approval stays plan mode; T4+ plan gates and the final approval stay state.py approve in the human's terminal or the [Answer]: line. The picker is for ordinary questions only (recommended)
B. A gate may be answered in a picker, but only when a hook (not the agent) records the human's selection and state.py verifies it against the gate text; where no such hook exists (Codex, headless) the terminal and file routes remain
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T19:55:49Z

## Q16. One developer, several computers: can a task that is in flight be continued on another machine?
asked: 2026-10-02T19:48:55Z · stage: intent
context: .ai/state/current.json and handoff.md are git-ignored, while the task's questions.md and events.jsonl are committed, so today a task cannot follow its owner. 'Two people on the same task at the same time' stays out of scope either way.
A. Yes, explicitly: one command parks the task so its state travels with a commit, another resumes it on the other machine; never implicit, and one machine owns the task at a time (recommended)
B. No — out of scope: a task is finished or abandoned on the machine that started it, and the intent says so
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T19:55:49Z

## Q17. What is local mode for?
asked: 2026-10-02T19:48:55Z · stage: intent
context: Q9 chose a local opt-in but not its purpose. A tracked file cannot be local to one clone, so mode A is project-wide; mode B would use the clone's own exclude file and cannot hide a change to a file the repository already tracks.
A. Keeping the pipeline's records out of git: .ai/state and .ai/reports are ignored for the whole project; policies, the knowledge base and docs/sdlc stay shared (recommended)
B. Leaving no trace in a repository I do not own: the whole pipeline footprint (.ai/, docs/sdlc, the managed blocks) stays out of git through the clone's own exclude file, with nothing committed
C. Both, as two levels of the same switch
X. Other — answer as `X: <text>`
[Answer]: C — by vanssa via picker at 2026-10-02T19:55:49Z

## Q18. The intent now covers several concerns. How is the work split?
asked: 2026-10-02T19:48:55Z · stage: intent
context: docs/sdlc/README.md says one intent file per idea; adaptive-cross-runtime-sdlc kept one intent with a Work packages table (package, files, tier, depends on, status) and one spec and plan per package. .github/workflows/** and **/migrations/** are T5 by path scope.
A. One intent with a Work packages table; each package gets its own spec, plan and task, in dependency order (recommended)
B. Separate intents (runtime and installer, packaging, interaction, several machines), each with its own questions file
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T19:55:49Z

## Q19. The module must also install through a package manager, with one command and without cloning the repository. Which registry?
asked: 2026-10-02T20:18:23Z · stage: intent
context: Added by the maintainer on 2026-10-02: installable through npm install or a similar installer, Python is fine too. Either way the package manager is one more channel for the same package and the same installer (Q13: one installed form). The names claude-agentic and claude-agentic-sdlc are unregistered on npm and on PyPI today. The run time needs Python 3.11 in any case (Q5, Q11).
A. PyPI: pipx run, uvx or pip fetches the package and runs the installer; nothing but Python is needed and no code outside Python is added (recommended)
B. npm: npx <name> install; Node.js is needed at install time only, and a small launcher finds Python and runs the same installer
C. Both registries, published from the one version source
X. Other — answer as `X: <text>`
[Answer]: C — by vanssa via picker at 2026-10-02T20:21:05Z

## Q20. An installed copy never learns that a newer version exists. How does it tell its user?
asked: 2026-10-02T20:46:56Z · stage: intent
context: Added by the maintainer on 2026-10-02: every installed client should be notified of a new version. Nothing can be pushed, because there is no list of installs: a copy can only look the latest version up itself. The module makes no network call today, so this would be its first. profile.json already records the installed version (install.sh:182-186), and /ai-status only compares a project with the installed module.
A. On by default: at most once a day, at session start, the copy looks up the latest version and shows the human one line with the exact update command for the channel it came from; /ai-status shows the same on demand; one setting turns the lookup off; the copy never updates itself (recommended)
B. Opt-in: the same notice, but the lookup at session start runs only after the user enables it (the installer asks); /ai-status still checks on demand
C. On demand only: nothing at session start; /ai-status and the installer compare with the latest version when the user runs them
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T20:49:05Z

## Q21. A second review found seven gaps in what the intent promises. Which of them enter the intent?
asked: 2026-10-02T20:54:30Z · stage: intent
context: G1 the install-time self-test proves the guard program, not that the runtime calls it: Codex skips a changed hook until it is trusted again, and an interpreter path can vanish. G2 a failed install must leave the previous one working. G3 an existing install must upgrade in place across the renamed guards. G4 UTF-8 for hook payloads, output and files: under a Windows code page a Cyrillic prompt can crash a hook. G5 a named manual check per release for what CI cannot prove on a live runtime. G6 a security review and a differential test for the guard port. G7 no update check in a headless or unattended run.
A. All seven (recommended)
B. Only the four that protect the guards: G1, G2, G3 and G6
C. None; the intent stays as it is
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T20:56:46Z

## Q22. Three refactorings come before anything a user can see, and the port of the 25 suites sits on the path of packages 4 and 9. Is package 3 re-cut?
asked: 2026-10-02T20:54:30Z · stage: intent
context: Q12 put the test port in its own package after the code ports. As drawn, package 4 (every supported environment) and package 9 (records) wait for all 25 suites.
A. Yes: package 3 becomes a small runner that runs bash and Python suites side by side, followed by the port itself; packages 4, 8 and 9 write their new tests in Python from the start and wait only for the runner (recommended)
B. No: the order stays as it is
X. Other — answer as `X: <text>`
[Answer]: A — by vanssa via picker at 2026-10-02T20:56:46Z
