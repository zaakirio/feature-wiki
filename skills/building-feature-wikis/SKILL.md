---
name: building-feature-wikis
description: Use when the user wants to document, catalogue, or build a wiki of the features in a codebase (e.g. "build a wiki of what this repo does", "document this project's features", "generate onboarding docs", "collate what I've built across my projects"). Reconstructs features from git history, enriches them with project-management ticket context from whatever PM MCP is connected (Jira, Linear, GitHub, Shortcut, Asana), and publishes deduplicated docs to Confluence, Linear, Notion, a GitHub wiki, or a local HTML wiki.
---

# Building feature wikis

Turn a codebase's git history into a structured, deduplicated feature wiki. Features are
reconstructed from commits, grouped by their project-management ticket (or epic), enriched with the
ticket's real description, deep-read from the code, written up from a template, and published to a
documentation target — **without ever creating duplicate pages**, even when several people worked the
same ticket or epic.

This skill is an orchestrator. It runs a fixed pipeline, but each stage delegates: deterministic work
to the bundled scripts, provider-specific work to the adapter registry, and per-feature deep analysis
to parallel subagents.

## When to use

Trigger on intents like: "build a wiki / catalogue / docs of the features in this project", "document
everything I built", "generate onboarding docs from git history", "write up this repo for Confluence /
Linear / Notion", "collate the features across my side projects so I can keep track of them".

## Non-negotiable rules

1. **Deduplicate by ticket/epic, verified against the live target.** The stable identity of a feature
   is its canonical ticket key (or epic key), NOT a filename. Before publishing, ALWAYS search the
   target provider for an existing page carrying the feature's marker and update it in place; only
   create when none exists. The local manifest is a cache, never the sole source of truth — a teammate
   may have already published the same ticket. See `reference/providers.md` (Deduplication contract).
2. **Never use markdown tables or the `|` pipe character** except inside fenced ASCII diagrams. Use
   lists/prose (they survive copy-paste into Confluence/Linear/Notion; tables often do not).
3. **Cite real code** as `path/to/file.ext:line` relative to the repo root.
4. **Default scope is the current user's authored commits.** Resolve their git identity first; only
   widen to the whole repo when the config or the user says so.
5. **Read config before asking.** If `.featurewiki/config.json` exists, use it and skip the questions
   it already answers. Re-runs should be one command.

## Workflow

Copy this checklist and track progress:

```
Feature-wiki progress:
- [ ] 0. Init    — load or create .featurewiki/config.json (scope, providers, target, lens)
- [ ] 1. Detect  — discover connected PM-read + docs-write MCPs; bind adapters
- [ ] 2. Mine    — git history -> grouped features JSON (scripts/mine_history.py)
- [ ] 3. Enrich  — pull each ticket/epic description via the bound PM adapter
- [ ] 4. Analyze — one subagent per feature: read code, write the doc from the template
- [ ] 5. Diff    — manifest + live-target search -> NEW / CHANGED / UNCHANGED per feature
- [ ] 6. Publish — create-or-update each changed feature on the target(s); record the manifest
```

### 0. Init

If `.featurewiki/config.json` exists in the repo root, load it. Otherwise create it by resolving:
author scope (default: `git config user.email`), read provider + its ids (e.g. Jira `cloudId`,
Confluence `spaceId`), write target(s), and doc lens (default: `onboarding`). Write the file so future
runs are non-interactive. Config schema is documented in `reference/providers.md`.

### 1. Detect providers

Discover which MCPs are connected and bind them to capabilities (PM-read, docs-write). Do NOT hardcode
tool names — match the connected tools to the registry. Procedure and the full registry (Jira, Linear,
GitHub, Shortcut, Asana for read; Confluence, Linear, Notion, GitHub wiki, local HTML for write) are in
`reference/providers.md`. If no PM MCP is connected, fall back to linking ticket URLs parsed from commit
messages (no enrichment).

### 2. Mine history

Run the miner to group commits into features:

```bash
python3 scripts/mine_history.py --repo . --author "<email-or-name>" --since "<date>" --out .featurewiki/features.json
```

It groups by ticket key, then by merged branch, then by conventional-commit scope, and computes a
`sourceHash` per feature for staleness detection. Grouping heuristics and how to tune them are in
`reference/feature-grouping.md`. Review and, if needed, merge/split groups before continuing.

### 3. Enrich

For each feature with a ticket key, fetch the ticket (and its epic/parent, for grouping) through the
bound PM adapter and attach the summary, description, status, and URL to the feature record. Group
sibling tickets under their shared epic so one epic does not become many near-duplicate pages.

### 4. Analyze and write

Spawn **one subagent per feature** (parallel) — this is what makes it scale. Each subagent reads
`reference/doc-template.md` (the team-onboarding template + style rules), reads the relevant code,
reads its ticket context, and writes `.featurewiki/docs/<slug>.md`. Pass each subagent its feature
record (commits, files, ticket text) and the absolute paths. Keep the doc-template rules (no tables,
file:line cites, ASCII diagrams) explicit in every subagent prompt.

### 5. Diff against the manifest AND the live target

```bash
python3 scripts/manifest.py diff .featurewiki/features.json --manifest .featurewiki/manifest.json
```

This classifies each feature NEW / CHANGED / UNCHANGED by `sourceHash` and emits the stable marker
string for each. Then, for the chosen target, also search the live provider for an existing page with
that marker (see the Deduplication contract). The publish decision is: marker found anywhere ->
UPDATE that page; else CREATE.

### 6. Publish

For local HTML, run `scripts/build_html.py` to emit the self-contained viewer. For Confluence / Linear
/ Notion / GitHub, use the bound write adapter to create-or-update per the dedup decision, stamping the
marker as a page property/label/front-matter so the next run finds it. Record every published
`{slug, ticketKey, provider, pageId, url, sourceHash}` back into the manifest:

```bash
python3 scripts/manifest.py record <slug> --provider <p> --page-id <id> --url <url> --hash <sourceHash> --manifest .featurewiki/manifest.json
```

## References

- `reference/providers.md` — adapter registry, provider detection, the **deduplication contract**, config schema.
- `reference/feature-grouping.md` — how commits become features; tuning the heuristics.
- `reference/doc-template.md` — the team-onboarding doc template and style rules.

## Scripts

- `scripts/mine_history.py` — git log to grouped features JSON.
- `scripts/manifest.py` — diff features vs manifest; compute markers; record published pages.
- `scripts/build_html.py` — bundle docs into a self-contained `index.html` + `content.js` wiki.
