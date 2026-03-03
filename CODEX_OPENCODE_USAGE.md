# OpenCode Imports Usage in Codex

This project imported non-skill prompts from `archibate/dotfiles-opencode` into Codex skill wrappers.

## 1. Project Conventions

Project-level conventions were imported into:
- `AGENTS.md`

These rules are applied as project instructions when Codex works in `d:/project`.

## 2. Imported Agent Wrappers

OpenCode `agent/*.md` files were mapped to Codex skills:

- `@brainstorm` -> `opencode-agent-brainstorm`
- `@executor` -> `opencode-agent-executor`
- `@worker` -> `opencode-agent-worker`
- `@committer` -> `opencode-agent-committer`
- `@quick` -> `opencode-agent-quick`
- `@web-scraper` -> `opencode-agent-web-scraper`
- `@gitignore-writer` -> `opencode-agent-gitignore-writer`
- `@spec-feasible` -> `opencode-agent-spec-feasible`
- `@spec-implement` -> `opencode-agent-spec-implement`
- `@spec-orchestrator` -> `opencode-agent-spec-orchestrator`
- `@spec-review` -> `opencode-agent-spec-review`
- `@spec-test` -> `opencode-agent-spec-test`
- `@spec-write` -> `opencode-agent-spec-write`

## 3. Imported Command Wrappers

OpenCode `command/*.md` files were mapped to Codex skills:

- `code-review` -> `opencode-command-code-review`
- `prompt-engineering` -> `opencode-command-prompt-engineering`
- `proof-read` -> `opencode-command-proof-read`
- `repo-analyser` -> `opencode-command-repo-analyser`
- `review-custom-command` -> `opencode-command-review-custom-command`
- `skillful` -> `opencode-command-skillful`
- `write-failing-test` -> `opencode-command-write-failing-test`

## 4. Invocation Pattern

Ask Codex directly with the target skill name in your prompt, for example:

- `Use skill opencode-agent-brainstorm to break this request into tasks.json.`
- `Use skill opencode-command-code-review for src/auth/*.py with focus on correctness.`

## 5. Compatibility Notes

- OpenCode runtime settings in `opencode.jsonc` (providers, MCP servers, plugins, themes) are not directly portable to Codex `config.toml`.
- The workflow logic is portable and has been preserved through AGENTS + skill wrappers.
- Restart Codex after migration so newly added skills are discovered.
