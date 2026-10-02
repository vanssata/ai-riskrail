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
