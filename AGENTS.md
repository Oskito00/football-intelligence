# Codex Guidance

## Architecture Preferences

Prefer fewer, deeper modules over many shallow modules.

A good module should:

- Represent a real domain concept or workflow.
- Hide meaningful implementation complexity behind a small, testable interface.
- Be testable through that interface.
- Keep related behavior together so changes have locality.
- Avoid pass-through wrappers, tiny helper modules, and seams with only one adapter unless there is a clear reason.

When refactoring, optimize for fewer modules with stronger ownership, not more files.

## Agent skills

### Issue tracker

Issues and PRDs for this repo live in GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

This repo uses the default mattpocock/skills triage label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo with root `CONTEXT.md` and root `docs/adr/`. See `docs/agents/domain.md`.
