---
description: Publish the built feature docs to the configured remote target(s), deduplicating against existing pages
argument-hint: "[provider: confluence|linear|notion|github]"
---

Invoke the `building-feature-wikis` skill and run **stage 6 (Publish)** for the configured write
target(s), or the single provider named in `$ARGUMENTS`.

Follow the **Deduplication contract** in `reference/providers.md` strictly:

1. For each built doc in `.featurewiki/docs/`, compute its `fwId` and marker (`scripts/manifest.py`).
2. SEARCH the live target for an existing page bearing that marker (content property / label /
   front-matter comment), and also check the local manifest.
3. Match found anywhere -> UPDATE that page in place. No match and CHANGED/NEW -> CREATE and stamp the
   marker. No match and UNCHANGED -> skip.
4. If a search returns multiple existing pages for one `fwId`, update the oldest and report the rest to
   the user for manual merge — never auto-delete.
5. Record each published page with `scripts/manifest.py record`.

Report a summary: created, updated, skipped, and any duplicates flagged for manual merge.
