# Connecting your tools (MCP setup)

feature-wiki does not ship or require any MCP server. It uses whatever you have connected in Claude
Code and adapts to it. This file is the human-facing setup guide; the runtime binding rules (how Claude
matches a connected tool to a capability) live in `providers.md`.

## What to connect, and what it unlocks

Nothing is required to produce the local HTML wiki. Connect a provider only to unlock more:

- **Ticket enrichment (read).** Connect one of Jira, Linear, GitHub, Shortcut, or Asana. This pulls real
  ticket titles, descriptions, status, and epic links into each doc. Without it, docs still link the
  ticket keys parsed from your commits, just without descriptions.
- **Publishing to a shared space (write).** Connect Confluence, Notion, or Linear, or use the `gh` CLI
  for a GitHub wiki. Without any of these, output stays as the local HTML wiki.

## How to connect in Claude Code

Most of these are remote, OAuth-authenticated servers. The pattern is: add the server, then log in.

1. Add the server by URL:
   `claude mcp add --transport sse <name> <server-url>`
   (some servers use `--transport http`; use whatever the provider's docs specify)
2. Authenticate: run `/mcp` in Claude Code and log in to the server.
3. Verify: `/mcp` shows connected servers and their auth status; `claude mcp list` shows what is
   configured.

For a team, commit a project-scoped `.mcp.json` so everyone shares the same servers.

Server endpoints change over time, so copy the current URL from each provider's official MCP docs
rather than trusting a value pasted here.

## Per-provider pointers

- **Atlassian (Jira + Confluence).** One official Atlassian MCP server covers both reading Jira issues
  and writing Confluence pages, so connecting it once enables enrichment and publishing. The first run
  needs your Jira `cloudId`, which the skill reads via the server's accessible-resources call and caches
  in config.
- **Linear (issues + docs).** Official Linear MCP server, e.g.
  `claude mcp add --transport sse linear https://mcp.linear.app/sse`, then `/mcp` to log in.
- **Notion (write).** Official Notion MCP server; publish pages under a chosen parent page or database.
- **GitHub (read + wiki).** Either the official GitHub MCP server, or just the `gh` CLI (`gh auth login`),
  which needs no MCP for reading issues/PRs and pushing a wiki.
- **Shortcut / Asana (read).** Use their MCP servers if available; otherwise the skill falls back to
  link-only.

## If nothing is connected

The skill still runs. It mines git history, links any ticket keys it finds in commit messages, and
builds the local HTML wiki. Connect a provider later and re-run to enrich and publish.

## Before a run

Run `/mcp` and confirm the providers you expect are connected and authenticated. Then `/feature-wiki-init`
detects them and writes `.featurewiki/config.json`.
