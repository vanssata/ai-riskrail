# Cursor fixture

Source: https://cursor.com/docs/context/rules , https://cursor.com/docs/context/mcp
Checked: 2026-09-22

Layout assumed:
- `.cursorrules` at the root (legacy, still loaded, no frontmatter) and `.cursor/rules/` are the signatures.
- `.cursor/rules/**/*.mdc`, frontmatter `description`, `globs` (one comma-separated string), `alwaysApply` (bool). Nested `.cursor/rules/` in subdirectories is supported by Cursor; `detect` is root-only, so a nested one is `unmapped` (R4) — the test plants `packages/x/.cursor/rules/a.mdc`.
- `.cursor/mcp.json` → `ignore`.

The fixture covers always (general.mdc), glob-scoped with a literal leading directory
(frontend/react.mdc → `.ai/rules/`), description-only (testing.mdc → `.ai/policies/adopted/`), and glob-only with no literal directory
(typescript.mdc, `globs: *.ts,*.tsx` → `.ai/policies/adopted/` with `paths:`). Since spec amendment
A4 (2026-09-27) the always rule goes into the root instruction files.

Corrections to spec I2: none. Noted, out of scope: Cursor now also reads `AGENTS.md` (root and
nested); a root one is the codex instruction file, nested ones are not detected.
