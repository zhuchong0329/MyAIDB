---
name: default
description: MyAIDB project default zero-memory context.
---

# Default Context

## Status

- zero-memory has been deployed for this workspace.
- Codex skills were copied into `.codex/skills`.
- Workspace memory data directories were initialized under `.zero-memory/`.
- Installation was completed manually because `bash` is not available in the current PowerShell environment.
- Verification passed: `AGENTS.md`, `.codex/skills`, `.zero-memory/`, and `.zero-memory/tmp/current-context.txt` are present.
- The local zero-memory source checkout under `extra/zero-agent-memory` is intentionally ignored by Git so public history does not expose private source metadata.

## Git Initialization

- Workspace root was initialized as a Git repository on branch `main`.
- zero-memory is not tracked as a submodule in the public repository; copied Codex skills are tracked directly under `.codex/skills`.
- Remote `origin` was set to `git@github.com:zhuchong0329/MyAIDB.git`.
- Public history was sanitized to avoid exposing private source repository metadata before pushing.
- Git author and committer metadata were changed to `zhuchong0329 <zhuchong0329@users.noreply.github.com>` for public-safe commits.
- Push is still pending because GitHub SSH returned `Permission denied (publickey)`.
- Alternative push path: HTTPS remote can be used instead of SSH, but GitHub requires a Personal Access Token or Git Credential Manager/browser login rather than account password.

## Project Anchors

- `PRINCIPLES.md` records the MyAIDB original principles.
- `DEVELOPMENT_PLAN.md` records the first-stage development plan.
