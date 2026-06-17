# Providers: detection, adapters, deduplication contract, config

## Contents
- Provider detection procedure
- PM-read adapters (ticket enrichment)
- Docs-write adapters (publishing)
- Deduplication contract (read this carefully)
- Config schema (.featurewiki/config.json)

---

## Provider detection procedure

Tool names are NOT fixed across installations (the same server may surface as `Atlassian`,
`atlassian`, `jira`, or a `mcp__..._Atlassian__...` slug). So bind by capability at runtime:

1. List the connected MCP tools available this session (they appear in the tool namespace; search with
   keywords via the tool-search facility, e.g. "jira issue", "linear issue", "confluence page",
   "notion page", "create document").
2. Match each connected tool to a capability in the tables below by its action keywords, not its exact
   server slug. Always call the matched tool by its fully-qualified name.
3. If two providers satisfy the same capability (e.g. both Jira and Linear are connected and ticket
   keys are ambiguous), prefer the one named in `.featurewiki/config.json`; if unset, ask once and
   persist the answer.
4. If no PM-read provider is connected, run in link-only mode: parse ticket keys/URLs from commit
   messages, infer the provider from the key shape, and link them without enrichment.

Ticket-key shapes (for parsing and provider inference):
- Jira / Linear / Shortcut: `[A-Z][A-Z0-9]+-\d+` (e.g. `PROJ-128`, `ABC-42`). Ambiguous between
  providers — disambiguate by which MCP is connected or by config.
- GitHub issues/PRs: `#\d+` and `org/repo#\d+`.
- Asana: numeric task ids, usually as full URLs.

---

## PM-read adapters (ticket enrichment)

Each entry: capability -> tool action to match -> prerequisites.

- **Jira**: match a `getJiraIssue` / `get_issue` action. Prerequisite: `cloudId` (obtain once from a
  `getAccessibleAtlassianResources` action; cache in config). Fetch summary, description, status,
  issuetype, parent/epic link. Ticket URL: `https://<site>/browse/<KEY>`.
- **Linear**: match a get-issue-by-identifier action. Fetch title, description, state, parent, project.
- **GitHub**: use `gh issue view <n> --json` / `gh pr view`, or a GitHub MCP `get_issue`. Fetch title,
  body, labels, milestone (treat milestone/epic as the grouping parent).
- **Shortcut / Asana**: match get-story / get-task actions; map to {title, description, state, epic}.

For epic/parent grouping: if the ticket exposes a parent or epic, record it as the feature's
`epicKey`. Sibling tickets sharing an `epicKey` may be merged into one feature page (see grouping doc).

---

## Docs-write adapters (publishing)

Every write adapter MUST implement create-or-update keyed on the feature marker (next section). Each
entry: capability -> tool action -> where the marker lives.

- **Confluence**: match `createConfluencePage` / `updateConfluencePage`. Prerequisite: `spaceId` and a
  parent page id. Store the marker as a **content property** (`featureWikiId`) AND in the page title
  prefix, so it is findable by both property query and title search. Update by page id.
- **Linear docs**: match a create/update document action (or create/update issue if docs are
  unavailable). Store the marker in the document's first line as an HTML comment and, if supported, a
  label. Update by document id.
- **Notion**: match a create-page / update-page action under a parent database/page. Store the marker
  as a page property (`Feature Wiki ID`). Update by page id.
- **GitHub wiki / repo docs**: write `docs/feature-wiki/<slug>.md` (or push to the `.wiki` repo). The
  marker is an HTML comment on line 1: `<!-- feature-wiki-id: <ID> -->`. Update by overwriting the file
  with the matching marker. Commit, do not duplicate.
- **Local HTML**: run `scripts/build_html.py`. The marker lives in front-matter and in `content.js`.
  Idempotent by construction (regenerated each run).

---

## Deduplication contract

This is the core guarantee: the same ticket or epic must yield exactly one page per target, even when
multiple authors touched it and even across separate runs by different people.

Definitions:
- **Feature ID** (`fw-id`): the canonical stable identity. Resolution order:
  1. the feature's **epic key** if grouping at epic level (e.g. `PROJ-EPIC-220`),
  2. else the feature's **primary ticket key** (the lowest-numbered ticket in the group, deterministic),
  3. else, for ticketless features, `slug:<deterministic-slug>` derived from the merged branch or
     conventional-commit scope.
- **Marker**: the literal string `feature-wiki-id: <fw-id>`. It is embedded in every doc and stamped on
  every published page as a property/label/comment, exactly as the write adapter specifies.

Publish algorithm (run per feature, per target):
1. Compute `fw-id` and the marker (`scripts/manifest.py` prints both).
2. **Search the live target** for an existing page bearing the marker:
   - Confluence: query pages where content property `featureWikiId == fw-id` (fallback: title search
     for the `fw-id` prefix).
   - Notion/Linear: query by the marker property/label.
   - GitHub/local: look for the file whose line 1 marker matches.
   - Also check the local manifest for a recorded `pageId`.
3. Decide:
   - Match found (anywhere) -> **UPDATE** that page in place. Do not create.
   - No match, and manifest says UNCHANGED `sourceHash` -> skip (nothing to do).
   - No match, NEW or CHANGED -> **CREATE**, then stamp the marker.
4. Record `{slug, fwId, provider, pageId, url, sourceHash}` in the manifest.

Why search the live target and not just trust the manifest: the manifest only records what *this* user
published. A colleague who ran the skill (or hand-wrote the ticket page) already owns a page for that
`fw-id`. Searching the target makes the operation converge to one page regardless of who ran it.

Collision and merge notes:
- Two providers can mint identical keys (`ABC-123`). Namespace the `fw-id` with the provider when more
  than one PM provider is in play: `jira:PROJ-128`, `linear:ABC-42`.
- If a search returns multiple matches for one `fw-id` (a pre-existing duplicate), update the oldest
  and report the others to the user for manual merge rather than guessing.
- Never delete pages automatically. Report orphans (manifest entries whose ticket no longer maps to any
  current feature) for human review.

---

## Config schema (.featurewiki/config.json)

```json
{
  "scope": { "mode": "author", "authors": ["you@example.com"], "since": "2025-01-01" },
  "ticketPattern": "[A-Z][A-Z0-9]+-\\d+",
  "groupBy": "ticket",
  "pmProvider": { "name": "jira", "cloudId": "<uuid>", "site": "your-site.atlassian.net" },
  "writeTargets": [
    { "name": "local-html", "outDir": ".featurewiki/site" },
    { "name": "confluence", "spaceId": "<id>", "parentPageId": "<id>" }
  ],
  "lens": "onboarding",
  "epicGrouping": true
}
```

- `scope.mode`: `author` (default) or `all`.
- `groupBy`: `ticket` (default), `branch`, or `scope`.
- `lens`: `onboarding` (default), `adr`, or `interview` — selects the template variant.
- `writeTargets`: one or more; each must name a provider from the write-adapter list.
