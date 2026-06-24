# Feature grouping: how commits become features

`scripts/mine_history.py` turns a filtered commit list into feature records. This file explains the
heuristics so you can sanity-check and hand-correct the output before writing docs.

## Grouping precedence

Each commit is assigned to exactly one feature using the first rule that matches:

1. **Ticket key** (default, `groupBy: ticket`). Extract the first match of `ticketPattern`
   (default `[A-Z][A-Z0-9]+-\d+`) from the commit subject AND from the branch name recorded in any
   `Merged in <branch> (pull request #N)` line. All commits sharing a key form one feature.
2. **Merged branch.** Commits with no ticket key but reachable from a named feature branch are grouped
   by that branch (the merge-commit message names it).
3. **Conventional-commit scope.** `feat(scope): ...` / `fix(scope): ...` groups leftover commits by
   `scope`.
4. **Unassigned.** Anything left (chores, merges, one-off fixes) is collected into an `unassigned`
   bucket and excluded from the wiki unless the user asks otherwise.

## Epic roll-up

When `epicGrouping` is true and the PM adapter exposes a parent/epic for a ticket, sibling features
sharing an `epicKey` can be merged into one page. Prefer epic-level pages when several small tickets are
clearly one shippable feature (e.g. a migration done across 5 tickets). Keep them separate when each
ticket is independently meaningful. This is a judgement call — present the proposed grouping to the
user when it materially changes the page count.

## Feature record shape (emitted JSON)

Each feature is an object with:
- `slug` — kebab-case, derived from the title guess; stable across runs.
- `fwId` — canonical id for dedup (epic key, else primary ticket key, else `slug:<slug>`).
- `ticketKeys` — all keys in the group, sorted deterministically; `[0]` is the primary.
- `epicKey` — parent/epic key if known (filled during enrichment).
- `title` — best-effort title from the ticket summary or the most descriptive commit subject.
- `commits` — `[{hash, date, subject, author}]`.
- `filesTouched` — optional, union of paths from the commits (use for the code map and to scope reading).
- `firstDate` / `lastDate` — span of the work.
- `branches` — feature branches seen.
- `sourceHash` — sha1 of the sorted commit hashes; changes only when the feature gains/loses commits.

Primary ticket selection is numeric when possible, so `PROJ-2` sorts ahead of `PROJ-12`. When a group
mentions multiple providers and the keys are namespaced, the namespace is included in the sort.

## Hand-correction

The miner is deliberately conservative. Before the analyze stage, review `features.json` and:
- merge two slugs that are really one feature (combine `commits`, recompute `sourceHash`),
- split a grab-bag ticket into separate features,
- drop noise (revert chains, pure dependency bumps).

Recompute `sourceHash` after any edit with `python3 scripts/manifest.py rehash .featurewiki/features.json`.
