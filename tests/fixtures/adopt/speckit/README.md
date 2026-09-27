# Spec Kit fixture

Source: https://github.com/github/spec-kit (README, docs/upgrade.md, docs/reference/integrations), spec-driven.md
Checked: 2026-09-22; extended 2026-09-27 from two real projects (see below)

Layout assumed:
- `.specify/` is the signature. `.specify/memory/constitution.md`, `.specify/templates/`, `.specify/scripts/{bash,powershell,python}/`.
- `specs/<NNN-name>/` with `spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`.
- Agent integration, current releases: skills — `.claude/skills/speckit-<cmd>/SKILL.md`, `.github/skills/speckit-<cmd>/`, `.github/agents/*.agent.md`, `.cursor/skills/…`, `.agents/skills/…` (Codex); Gemini keeps `.gemini/commands/*.toml`.
- Older releases: flat command files `speckit.<cmd>.md` under `.claude/commands/`, `.github/prompts/` (`.prompt.md`), `.codex/prompts/`, `.cursor/commands/`.

The fixture carries one of each generation: `.claude/skills/speckit-plan/SKILL.md`,
`.claude/commands/speckit.specify.md`, `.gemini/commands/speckit.plan.toml`,
`.github/prompts/speckit.tasks.prompt.md`.

Corrections to spec I2:
- Added the skills layout to `roots` and a drop row `*/**/speckit-*/**`; the old row `*/**/speckit*` cannot match a file inside a `speckit-<cmd>/` directory.
- Removed `memory/constitution.md` (root) from `roots` and its row: current Spec Kit keeps the constitution under `.specify/memory/`; a root `memory/` is not a Spec Kit convention and could be application code that cleanup would delete.
- `contracts/` is real but not mapped: it is `unmapped` until the human decides (spec I6 example). The test plants it.

Extended 2026-09-27 from the manual check on github.com/galax-io/gatling-picatinny (`0228bb4`) and
github.com/pulumi/pulumi-hyperv (`60eaaa4`), shape only:
- `plan.md` and `tasks.md` carry the template's own path lines (`**Input**: Feature specification
  from `specs/<dir>/spec.md``, `Design documents from `specs/<dir>/``) — spec amendment A3.
- the constitution opens with the `/speckit.constitution` Sync Impact Report comment naming
  `.specify/templates/*` — A3.
- current `.specify/` machinery: `extensions.yml`, `init-options.json`, `integrations/*.manifest.json`,
  `presets/`, `workflows/`, and `specs/<dir>/checklists/requirements.md` — A1.
