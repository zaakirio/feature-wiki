# feature-wiki

> Turn any codebase's git history into a feature wiki, enriched with your Jira / Linear / GitHub
> tickets and published to Confluence, Notion, a GitHub wiki, or a local HTML site.

![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-6c5ce7)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Python](https://img.shields.io/badge/scripts-Python%20stdlib%20only-3776ab)

A Claude Code plugin that reconstructs the features an author shipped from **git history**, enriches
them with **project-management ticket context** (Jira, Linear, GitHub, Shortcut, Asana, whatever MCP is
connected), and publishes the result to **Confluence, Linear, Notion, a GitHub wiki, or a self-contained
local HTML wiki**.

It turns the one-off job of "document what this repo does" into a repeatable pipeline you can re-run as
the code changes.

## Why / use cases

The story of why and how a feature was built already lives in your commits and tickets. It just is not
written down anywhere readable. feature-wiki assembles it into clear, onboarding-grade docs and keeps
them current as the code evolves. It helps whether you work solo or on a team:

- **Solo builders.** Collate what each of your side projects actually contains and why you built it the
  way you did, so coming back to one after months is painless.
- **Teams.** Give new starters accurate onboarding docs instead of weeks of reverse-engineering, and
  keep those docs in sync as the code changes.
- **Shared docs spaces.** When publishing to a shared Confluence, Notion, or Linear space, it first
  searches the space for an existing page for each ticket or epic and updates that page rather than
  creating a new one. Several teammates can run it against the same project and everyone lands on one
  page per feature instead of spawning copies.

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
/feature-wiki-publish confluence   # publish or update pages in a shared space
```

Or just ask in natural language ("build a wiki of the features I shipped in this repo") and the skill
self-triggers.

## How it works

```
discover repo + scope  ->  mine git history into features  ->  enrich from the PM tool
        ->  one subagent per feature reads code + writes a doc  ->  check what changed
        ->  create or update each feature on the target(s)
```

Stages are deterministic where it matters (git mining, bookkeeping, and HTML bundling are scripts) and
high-freedom where judgement helps (grouping review, code reconstruction, provider binding).

## Layout

- `skills/building-feature-wikis/SKILL.md`: the orchestrator (the 6-stage workflow and checklist).
- `skills/building-feature-wikis/reference/`: provider adapters, grouping heuristics, and the doc
  template (team-onboarding lens by default; ADR variant available).
- `skills/building-feature-wikis/scripts/`: `mine_history.py`, `manifest.py`, `build_html.py`
  (Python stdlib only, no external deps).
- `commands/`: `/feature-wiki-init`, `/feature-wiki-build`, `/feature-wiki-publish`.
- `evals/scenarios.json`: baseline test scenarios.

## Defaults

- Scope: the current user's authored commits (`git config user.email`). Widen with `--all`.
- Grouping: by ticket key (recovered from commit subjects and from merge-commit branch names).
- Lens: team onboarding.
- Output: local HTML wiki, plus any remote targets configured.

## Known limitations

- Branch-range ticket recovery is skipped for oversized merges (release or dev-sync merges that would
  over-capture), so work split across many small PRs without ticket keys in the subject can fragment
  across a ticket page and a conventional-scope page. The build stage pauses for you to merge or split
  groups before docs are written.
- Jira and Linear use identically-shaped keys. When both are connected, set the provider in config so
  keys stay namespaced (`jira:PROJ-1`, `linear:ABC-1`).
