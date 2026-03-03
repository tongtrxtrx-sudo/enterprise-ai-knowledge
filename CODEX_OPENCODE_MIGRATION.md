# OpenCode -> Codex Migration Report

Date: 2026-03-02 23:09:35 +08:00

## Applied
- Added project-level AGENTS.md from archibate/dotfiles-opencode
- Converted opencode `agent/*.md` into Codex skills with prefix `opencode-agent-*`
- Converted opencode `command/*.md` into Codex skills with prefix `opencode-command-*`

## Installed Skills
- opencode-agent-brainstorm
- opencode-agent-committer
- opencode-agent-executor
- opencode-agent-gitignore-writer
- opencode-agent-quick
- opencode-agent-spec-feasible
- opencode-agent-spec-implement
- opencode-agent-spec-orchestrator
- opencode-agent-spec-review
- opencode-agent-spec-test
- opencode-agent-spec-write
- opencode-agent-web-scraper
- opencode-agent-worker
- opencode-command-code-review
- opencode-command-prompt-engineering
- opencode-command-proof-read
- opencode-command-repo-analyser
- opencode-command-review-custom-command
- opencode-command-skillful
- opencode-command-write-failing-test

## Notes
- OpenCode runtime settings in `opencode.jsonc` (provider/mcp/plugins/theme/default_agent) are not directly compatible with Codex `config.toml`.
- Migrated portable parts are now available through AGENTS.md and skill wrappers.
- Restart Codex to load new project AGENTS and skill metadata.
