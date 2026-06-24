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

## Recommended setups

Choose the smallest setup that matches where your team already plans work and reads docs.

- **Local-first / solo project.** No MCP required. Use only `git` and `python3`; feature-wiki mines the
  repo and builds `.featurewiki/site/index.html`.
- **Linear-first team.** Connect Linear for issue enrichment and Linear docs publishing. This is the
  simplest one-provider setup when planning and docs both live in Linear.
- **Atlassian team.** Connect Atlassian for Jira enrichment and Confluence publishing. This is the best
  fit when Jira is the system of record and Confluence is where onboarding docs already live.
- **Notion knowledge base.** Connect Jira, Linear, or GitHub for ticket enrichment, then connect Notion
  for publishing. Use this when tickets live elsewhere but the team reads long-form docs in Notion.
- **Open-source / GitHub-native project.** Use GitHub issues or PRs for enrichment and publish to a
  GitHub wiki or `docs/feature-wiki/` in the repo. The `gh` CLI is enough for many GitHub workflows.

## Supported provider examples

feature-wiki binds by capability, not by an exact MCP server name. These are the provider families it
knows how to use when connected:

- **Jira.** Read ticket title, description, status, issue type, parent or epic, and URL. Recommended
  when commit messages contain keys like `PROJ-123`.
- **Confluence.** Write or update durable feature pages. Recommended target for larger teams because
  feature pages can sit under an onboarding or engineering knowledge-base parent page.
- **Linear.** Read issues and, when available, write Linear documents. Recommended for small teams that
  keep product planning and engineering docs close together.
- **Notion.** Write pages under a chosen parent page or database. Recommended when Notion is the team
  wiki but ticket ownership lives in Jira, Linear, or GitHub.
- **GitHub.** Read issues and pull requests through a GitHub MCP or the `gh` CLI; publish to a GitHub
  wiki or repo docs. Recommended for open-source and code-first teams.
- **Shortcut / Asana.** Read ticket/story/task context when an MCP server is connected. Recommended as
  enrichment-only unless your team already publishes docs there.

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

Example shapes:

```bash
# Linear: issue enrichment and Linear docs when supported by the connected server
claude mcp add --transport sse linear https://mcp.linear.app/sse

# Atlassian: Jira enrichment and Confluence publishing
claude mcp add --transport sse atlassian <official-atlassian-mcp-url>

# Notion: docs publishing
claude mcp add --transport sse notion <official-notion-mcp-url>

# GitHub: issues, PRs, and wiki/repo-doc workflows
claude mcp add --transport sse github <official-github-mcp-url>
```

Use the provider's current docs for the transport and URL. Some providers have moved from SSE to HTTP
streaming; feature-wiki does not care which transport is used as long as Claude Code exposes the tools.

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

## Security recommendations

- Prefer official provider-hosted MCP servers or internally reviewed servers.
- Use OAuth where available, and grant the narrowest workspace/project access that still lets the skill
  read tickets and publish docs.
- Start with read-only ticket enrichment plus local HTML output before enabling write targets.
- Keep provider IDs such as `cloudId`, `spaceId`, parent page IDs, and database IDs in
  `.featurewiki/config.json`; do not commit tokens or personal credentials.
- Review `/mcp` before publishing so you know which authenticated accounts the write actions will use.

## If nothing is connected

The skill still runs. It mines git history, links any ticket keys it finds in commit messages, and
builds the local HTML wiki. Connect a provider later and re-run to enrich and publish.

## Before a run

Run `/mcp` and confirm the providers you expect are connected and authenticated. Then `/feature-wiki-init`
detects them and writes `.featurewiki/config.json`.
