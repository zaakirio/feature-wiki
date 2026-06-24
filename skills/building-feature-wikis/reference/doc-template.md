# Doc template & style guide (team-onboarding lens)

This is the default `onboarding` lens: neutral reference documentation that helps a new engineer (or
your future self returning to an old side project) understand what a feature does, how it fits the
system, and how to work on it. (The `adr` lens reframes around the decision and its alternatives —
switch via `lens` in config.)

## Hard rules
- **No markdown tables, no `|` pipe character** except inside fenced ASCII diagrams. Use lists/prose —
  they survive paste into Confluence, Linear, and Notion; tables frequently do not.
- **Line 1 is the dedup marker**, an HTML comment, exactly: `<!-- feature-wiki-id: <fw-id> -->`.
- Cite real code as `path/to/file.ext:line` relative to the repo root.
- Name actual classes, methods, tables, queues, endpoints — not vague descriptions.
- Separate evidence from inference. If a behavior is inferred from code or ticket context rather than
  directly stated, say so in the relevant sentence.
- Do not invent missing architecture. If the implementation, ticket, or tests do not reveal an answer,
  write `Unknown from available evidence` and name what would need to be checked.
- Use ASCII diagrams for data flow / sequence / component relationships.
- Don't include information that goes stale (dated "as of" notes); describe the current design.

## Required section order

1. `<!-- feature-wiki-id: <fw-id> -->` (line 1, no blank line before it)
2. `# <Feature name>`
3. **Tickets:** one line per ticket — `[KEY](url) — <summary> — <status>`. Omit if link-only/no PM.
4. `## What it does` — 3–5 sentences a new teammate can read in 30 seconds.
5. `## Why it exists` — the business/product problem (from the ticket description).
6. `## How it fits` — where it lives in the system; upstream callers and downstream consumers; the
   services/lambdas/domains involved. An ASCII component or data-flow diagram.
7. `## Data model` — tables/entities/keys/indexes, queues, caches, external stores.
8. `## Key behaviours & edge cases` — the important flows, plus concurrency, idempotency, retries,
   dedup, ordering, and failure handling that a maintainer must know.
9. `## How to work on it` — where to start reading, how to run/test it locally, the main extension
   points, and gotchas (config/flags/env). This is what makes it an onboarding doc.
10. `## Design patterns` — name the patterns used and where (Strategy, Factory, fan-out-on-read,
    outbox, event-driven, etc.).
11. `## Code map` — the key files and the responsibility of each.

Keep it proportionate to the feature: a small fix is one screen; a platform is several. Favour
precision over length.

## Lens variations
- `adr`: restructure sections 5–8 around Decision / Context / Alternatives considered / Consequences.
