---
description: Set up feature-wiki for this repo — detect PM/docs MCPs, resolve author scope, write .featurewiki/config.json
argument-hint: "[author email | 'all']"
---

Invoke the `building-feature-wikis` skill and run **only stage 0 (Init) and stage 1 (Detect)**:

1. Resolve the author scope. If `$ARGUMENTS` is given, use it; else default to `git config user.email`.
2. Detect which project-management (read) and documentation (write) MCPs are connected, following
   `reference/providers.md`. Report what was found and which capability each maps to.
3. Capture provider prerequisites (e.g. Jira `cloudId`, Confluence `spaceId`/parent) — ask only for
   what cannot be auto-discovered.
4. Write `.featurewiki/config.json`. Confirm the resulting config back to the user.

Do not mine or publish yet — this command only prepares config.
