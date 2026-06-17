# feature-wiki

> Turn any codebase's git history into a deduplicated feature wiki — enriched with your Jira / Linear /
> GitHub tickets, published to Confluence, Notion, a GitHub wiki, or a local HTML site.

![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-6c5ce7)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Python](https://img.shields.io/badge/scripts-Python%20stdlib%20only-3776ab)

A Claude Code plugin that reconstructs the features an author shipped from **git history**, enriches
them with **project-management ticket context** (Jira, Linear, GitHub, Shortcut, Asana — whatever MCP
is connected), and publishes **deduplicated** documentation to **Confluence, Linear, Notion, a GitHub
wiki, or a self-contained local HTML wiki**.

It generalises a one-off task — "build a wiki of everything I built on this project" — into a
repeatable, idempotent pipeline.

## Why

New starters spend weeks reverse-engineering what a service does. Solo builders with a dozen side
projects lose track of what each one actually contains and why it was built that way. The history of
*why* and *how* a feature was built already exists — in commits and tickets — it just is not written
down. `feature-wiki` assembles it into onboarding-grade docs, and keeps them current on re-runs without
ever creating duplicate pages — so you can document one team service or collate everything across your
own repos.

## What makes it safe to re-run

The headline guarantee is **no duplicate pages**, even when several people worked the same ticket or
epic, and even across separate runs by different people. Every feature has a stable identity (its
ticket/epic key), every published page is stamped with a marker, and the publish step **searches the
live target** for that marker before deciding to create or update. The local manifest is only a cache.
See `skills/building-feature-wikis/reference/providers.md` → Deduplication contract.

## Install

This repo is a Claude Code plugin marketplace. From GitHub:

```
/plugin marketplace add zaakirio/feature-wiki
/plugin install feature-wiki
```

Or from a local checkout:

```
/plugin marketplace add /path/to/feature-wiki
/plugin install feature-wiki
```

(Or copy `skills/building-feature-wikis` into a `.claude/skills/` directory to use the skill alone,
with no plugin install.)

## Use

```
/feature-wiki-init                 # detect MCPs, set scope, write .featurewiki/config.json
/feature-wiki-build --since 2025-11-01   # mine, enrich, write docs, render local HTML wiki
/feature-wiki-publish confluence   # publish/update pages, deduplicated
```

Or just ask in natural language ("build a wiki of the features I shipped in this repo") and the skill
self-triggers.

## How it works

```
discover repo + scope  ->  mine git history into features  ->  enrich from the PM tool
        ->  one subagent per feature reads code + writes a doc  ->  diff vs manifest + live target
        ->  create-or-update each changed feature on the target(s)
```

Stages are deterministic where it matters (git mining, dedup bookkeeping, HTML bundling are scripts)
and high-freedom where judgement helps (grouping review, code reconstruction, provider binding).

## Layout

- `skills/building-feature-wikis/SKILL.md` — the orchestrator (the 6-stage workflow + checklist).
- `skills/building-feature-wikis/reference/` — provider adapters + dedup contract, grouping heuristics,
  the doc template (team-onboarding lens by default; ADR variant available).
- `skills/building-feature-wikis/scripts/` — `mine_history.py`, `manifest.py`, `build_html.py`
  (Python stdlib only; no external deps).
- `commands/` — `/feature-wiki-init`, `/feature-wiki-build`, `/feature-wiki-publish`.
- `evals/scenarios.json` — baseline test scenarios.

## Defaults

- Scope: the current user's authored commits (`git config user.email`). Widen with `--all`.
- Grouping: by ticket key (recovered from commit subjects and from merge-commit branch names).
- Lens: team onboarding.
- Output: local HTML wiki, plus any remote targets configured.

## Known limitations

- Branch-range ticket recovery is skipped for oversized merges (release/dev-sync merges that would
  over-capture), so work split across many small PRs without ticket keys in the subject may fragment
  across a ticket page and a conventional-scope page. The build stage pauses for you to merge/split
  groups before docs are written.
- Jira and Linear mint identically-shaped keys; when both are connected, set the provider in config so
  keys are namespaced (`jira:PROJ-1`, `linear:ABC-1`).
