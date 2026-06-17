---
description: Build feature docs locally — mine git history, enrich from tickets, write docs, render the local HTML wiki
argument-hint: "[--since DATE] [--all]"
---

Invoke the `building-feature-wikis` skill and run **stages 0 through 5, plus local HTML output**:

1. Load `.featurewiki/config.json` (run init first if missing).
2. Mine history with `scripts/mine_history.py` using the configured scope; honour any `$ARGUMENTS`
   overrides (e.g. `--since`, `--all`). Show the grouped features and pause for the user to merge/split
   if the grouping looks off (see `reference/feature-grouping.md`).
3. Enrich each feature with its ticket/epic via the bound PM adapter.
4. Spawn one subagent per feature to read the code and write `.featurewiki/docs/<slug>.md` from
   `reference/doc-template.md` (team-onboarding lens by default). Each doc's line 1 must be the dedup
   marker.
5. Run `scripts/manifest.py diff` to classify NEW/CHANGED/UNCHANGED.
6. Render the local wiki with `scripts/build_html.py` into the configured `local-html` outDir.

Stop before publishing to remote providers — that is `/feature-wiki-publish`.
