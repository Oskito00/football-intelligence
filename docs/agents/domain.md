# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- `CONTEXT.md` at the repo root.
- `docs/adr/` at the repo root.
- `docs/adr/0002-replace-react-chat-frontend-with-read-only-svelte-dashboard.md`
  before changing dashboard or API contracts.

If any of these files don't exist, proceed silently. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

## File structure

This is a single-context repo:

```text
/
├── CONTEXT.md
├── docs/adr/
└── football_intelligence/
```

## Use the glossary's vocabulary

When output names a domain concept, use the term as defined in `CONTEXT.md`. Do not drift to synonyms the glossary explicitly avoids.

If the concept needed is not in the glossary yet, either reconsider the language or note it for `/grill-with-docs`.

## Read-Only Dashboard Boundary

ADR-0002 pins the read-only Svelte dashboard boundary. The dashboard consumes
deterministic data endpoints for **Football Data Status**, the **Prediction
Board**, **Market Value Signals**, and **Feature Snapshots**; it is not the
**Analyst Agent** chat flow for **Natural-Language Football Questions**.

Do not add dashboard controls that trigger **Prediction Refresh**, odds refresh,
feature rebuilds, deletion, or **Model Training**. Those workflows stay in the
operational command layer unless a later ADR explicitly changes the boundary.

## Flag ADR conflicts

If output contradicts an existing ADR, surface it explicitly rather than silently overriding.
