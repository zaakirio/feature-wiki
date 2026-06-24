#!/usr/bin/env python3
"""Mine a git repo's history into grouped feature records.

Groups commits into features by (in precedence order): ticket key, then merged branch, then
conventional-commit scope. Emits JSON consumed by the rest of the feature-wiki pipeline.

Usage:
  python3 mine_history.py --repo . --author you@co.com [--author other@co.com] \
      --since 2025-01-01 --ticket-pattern '[A-Z][A-Z0-9]+-\\d+' \
      --group-by ticket --files --out .featurewiki/features.json

  --author may be repeated; omit and pass --all to include every author.
  --files adds the union of changed paths per feature (slower; one `git show` per commit).
Stdlib only.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys

# ASCII unit/record separators keep commit fields unambiguous even with newlines in bodies.
FIELD = "\x1f"
RECORD = "\x1e"

BRANCH_RE = re.compile(r"Merged in ([^\s]+) \(pull request", re.I)
BRANCH_RE2 = re.compile(r"Merge branch '([^']+)'", re.I)
CONV_RE = re.compile(r"^(?:feat|fix|refactor|perf|chore|docs|test|build|ci)\(([^)]+)\)", re.I)
BRANCH_PREFIX_RE = re.compile(r"^(?:feature|feat|fix|hotfix|bugfix|chore|release)/", re.I)


def _run(repo, *git_args):
    return subprocess.run(["git", "-C", repo, *git_args],
                          capture_output=True, text=True).stdout


def build_pr_map(repo, ticket_re, since, max_range):
    """Map commit-hash -> (branch, ticketKey) using merge commits.

    A merge commit M with parents (P1 mainline, P2 branch-tip) introduces the commits in
    `P1..P2`; we tag each of those with the branch/ticket named in M's message. This recovers
    ticket association for commits whose own subject never mentioned the key (it lived in the
    branch name). Merges are scanned regardless of author, since the merger may differ.

    Guard: branches that merged mainline back in repeatedly produce huge `P1..P2` ranges that
    swallow unrelated work, so merges whose range exceeds `max_range` are skipped. They are
    almost always release/dev-sync merges, not a single feature PR.
    """
    fmt = FIELD.join(["%H", "%P", "%s", "%b"]) + RECORD
    args = ["log", "--merges", f"--pretty=format:{fmt}"]
    if since:
        args.append(f"--since={since}")
    out = _run(repo, *args)
    pr_map = {}
    for chunk in out.split(RECORD):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(FIELD)
        if len(parts) < 4:
            parts += [""] * (4 - len(parts))
        _h, parents, subject, body = parts[:4]
        text = subject + " " + body
        m = BRANCH_RE.search(text) or BRANCH_RE2.search(text)
        if not m:
            continue
        branch = m.group(1)
        ticket = extract_ticket(branch, ticket_re) or extract_ticket(text, ticket_re)
        par = parents.split()
        if len(par) < 2:
            continue
        p1, p2 = par[0], par[1]
        rng = _run(repo, "rev-list", "--no-merges", f"{p1}..{p2}").split()
        if len(rng) > max_range:
            continue  # release/dev-sync merge, not a single feature PR — skip
        for c in rng:
            pr_map.setdefault(c, (clean_branch(branch), ticket))  # first (newest) merge wins
    return pr_map


def git_log(repo, authors, since, all_authors):
    fmt = FIELD.join(["%H", "%ae", "%an", "%ad", "%s", "%b"]) + RECORD
    cmd = ["git", "-C", repo, "log", "--no-merges", "--date=short", f"--pretty=format:{fmt}"]
    if since:
        cmd.append(f"--since={since}")
    if not all_authors:
        for a in authors:
            cmd.append(f"--author={a}")
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    records = []
    for chunk in out.split(RECORD):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(FIELD)
        if len(parts) < 6:
            parts += [""] * (6 - len(parts))
        h, ae, an, date, subject, body = parts[:6]
        records.append({"hash": h, "authorEmail": ae, "author": an,
                        "date": date, "subject": subject, "body": body})
    return records


def slugify(text, maxlen=60):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].strip("-") or "feature"


def changed_files(repo, commit_hash):
    cmd = ["git", "-C", repo, "show", "--name-only", "--pretty=format:", commit_hash]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if l.strip()]


def extract_ticket(text, ticket_re):
    m = ticket_re.search(text or "")
    return m.group(0) if m else None


def clean_branch(name):
    return BRANCH_PREFIX_RE.sub("", name).strip()


def ticket_sort_key(ticket):
    """Sort ticket-like keys deterministically.

    Prefer the smallest numeric suffix within the same prefix, then fall back to
    lexical order. This matches the documented "lowest-numbered ticket" rule and
    keeps cross-provider namespaces stable when a feature mentions more than one key.
    """
    m = re.match(r"^([^:]+:)?([A-Z][A-Z0-9]+)-(\d+)$", ticket or "")
    if m:
        namespace = m.group(1) or ""
        prefix = m.group(2)
        number = int(m.group(3))
        return (namespace, prefix, number, ticket)
    return ("", "", sys.maxsize, ticket or "")


def assign_key(commit, ticket_re, group_by, pr_map):
    """Return (group_key, kind) for a commit per the precedence rules."""
    text = commit["subject"] + " " + commit["body"]
    # 1. ticket key in the commit's own message
    if group_by == "ticket":
        key = extract_ticket(text, ticket_re)
        if key:
            return key, "ticket"
    # 2. ticket/branch recovered from the PR (merge commit) that contains this commit
    pr = pr_map.get(commit["hash"])
    if pr:
        branch, ticket = pr
        if group_by == "ticket" and ticket:
            return ticket, "ticket"
        if group_by == "branch" and branch:
            return branch, "branch"
    # 3. conventional-commit scope
    m = CONV_RE.match(commit["subject"])
    if m:
        return m.group(1).lower(), "scope"
    return None, "unassigned"


def best_title(commits, key):
    """Pick a human title: the longest non-merge 'feat/fix' subject, else the longest subject."""
    cands = [c["subject"] for c in commits if not c["subject"].lower().startswith(("merge", "merged"))]
    cands = cands or [c["subject"] for c in commits]
    if not cands:
        return key
    feats = [s for s in cands if re.match(r"^(feat|fix)", s, re.I)]
    pool = feats or cands
    return max(pool, key=len).strip()


def source_hash(commits):
    h = hashlib.sha1()
    for c in sorted(c["hash"] for c in commits):
        h.update(c.encode())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--author", action="append", default=[])
    ap.add_argument("--all", action="store_true", help="include all authors")
    ap.add_argument("--since")
    ap.add_argument("--ticket-pattern", default=r"[A-Z][A-Z0-9]+-\d+")
    ap.add_argument("--group-by", choices=["ticket", "branch", "scope"], default="ticket")
    ap.add_argument("--max-pr-range", type=int, default=25,
                    help="skip merge commits whose branch range exceeds this many commits")
    ap.add_argument("--files", action="store_true", help="collect changed files per feature (slower)")
    ap.add_argument("--include-unassigned", action="store_true")
    ap.add_argument("--out", default=".featurewiki/features.json")
    args = ap.parse_args()

    if not args.all and not args.author:
        print("error: pass --author <email> (repeatable) or --all", file=sys.stderr)
        sys.exit(2)

    ticket_re = re.compile(args.ticket_pattern)
    pr_map = build_pr_map(args.repo, ticket_re, args.since, args.max_pr_range)
    commits = git_log(args.repo, args.author, args.since, args.all)

    groups = {}
    for c in commits:
        key, kind = assign_key(c, ticket_re, args.group_by, pr_map)
        if kind == "unassigned" and not args.include_unassigned:
            continue
        g = groups.setdefault(key or "unassigned", {"key": key, "kind": kind, "commits": []})
        g["commits"].append(c)

    features = []
    for key, g in groups.items():
        cs = g["commits"]
        # all distinct ticket keys mentioned anywhere in the group, plus the group key itself when
        # the group was formed from a ticket (recovered via the PR map but absent from commit text)
        found = {k for c in cs for k in ticket_re.findall(c["subject"] + " " + c["body"])}
        if g["kind"] == "ticket" and key and ticket_re.fullmatch(str(key)):
            found.add(str(key))
        ticket_keys = sorted(found, key=ticket_sort_key)
        primary = ticket_keys[0] if ticket_keys else None
        fw_id = primary if primary else f"slug:{slugify(str(key))}"
        title = best_title(cs, str(key))
        slug = slugify((primary + "-" + title) if primary else title)
        branches = set()
        for c in cs:
            pr = pr_map.get(c["hash"])
            if pr and pr[0]:
                branches.add(pr[0])
            for line in (c["subject"] + "\n" + c["body"]).splitlines():
                m = BRANCH_RE.search(line) or BRANCH_RE2.search(line)
                if m:
                    branches.add(clean_branch(m.group(1)))
        feat = {
            "slug": slug,
            "fwId": fw_id,
            "ticketKeys": ticket_keys,
            "epicKey": None,
            "title": title,
            "kind": g["kind"],
            "branches": sorted(branches),
            "commits": [{"hash": c["hash"], "date": c["date"],
                         "subject": c["subject"], "author": c["author"]} for c in cs],
            "firstDate": min(c["date"] for c in cs),
            "lastDate": max(c["date"] for c in cs),
            "sourceHash": source_hash(cs),
        }
        if args.files:
            paths = set()
            for c in cs:
                paths.update(changed_files(args.repo, c["hash"]))
            feat["filesTouched"] = sorted(paths)
        features.append(feat)

    features.sort(key=lambda f: f["lastDate"], reverse=True)
    payload = {"scope": ("all" if args.all else args.author), "groupBy": args.group_by,
               "featureCount": len(features), "features": features}

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(features)} features to {args.out}")
    if not features:
        print("warning: no features were produced", file=sys.stderr)
        if not args.include_unassigned:
            print("hint: rerun with --include-unassigned to keep tickets/scopes that did not match the filters",
                  file=sys.stderr)
    for feat in features[:20]:
        print(f"  {feat['fwId']:<18} {len(feat['commits']):>3} commits  {feat['title'][:70]}")


if __name__ == "__main__":
    main()
