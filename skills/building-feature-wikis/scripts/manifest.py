#!/usr/bin/env python3
"""Dedup + incremental-publish bookkeeping for the feature wiki.

The manifest records what was published where, keyed by provider + feature id (fwId), so re-runs
update pages instead of duplicating them. It is a CACHE — the publish step must still search the live
target by marker (see reference/providers.md), because a teammate may already own a page for an fwId.

Subcommands:
  diff     <features.json> [--manifest m] [--json]   classify NEW/CHANGED/UNCHANGED, print markers
  marker   <fw-id>                                   print the canonical marker string
  record   <slug> --fwid F --provider P --page-id ID --url U --hash H [--manifest m]
  rehash   <features.json>                            recompute sourceHash from commits in place

Stdlib only.
"""
import argparse
import hashlib
import json
import os
import sys


def load(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"entries": {}}


def save(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def marker(fw_id):
    return f"feature-wiki-id: {fw_id}"


def source_hash(commits):
    h = hashlib.sha1()
    for c in sorted(c["hash"] for c in commits):
        h.update(c.encode())
    return h.hexdigest()


def entry_key(provider, fw_id):
    return f"{provider}:{fw_id}"


def cmd_diff(args):
    feats = json.load(open(args.features, encoding="utf-8"))["features"]
    man = load(args.manifest)
    results = []
    for f in feats:
        # UNCHANGED only if EVERY configured provider has a matching, current hash.
        # With no provider filter, compare against any recorded hash for this fwId.
        recorded = [v for k, v in man["entries"].items() if v.get("fwId") == f["fwId"]]
        if not recorded:
            status = "NEW"
        elif all(r.get("sourceHash") == f["sourceHash"] for r in recorded):
            status = "UNCHANGED"
        else:
            status = "CHANGED"
        results.append({"slug": f["slug"], "fwId": f["fwId"], "status": status,
                        "marker": marker(f["fwId"]),
                        "pages": [{"provider": r["provider"], "pageId": r.get("pageId"),
                                   "url": r.get("url")} for r in recorded]})
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            line = f"  {r['status']:<10} {r['fwId']:<18} <!-- {r['marker']} -->"
            if r["pages"]:
                line += "  existing: " + ", ".join(p["provider"] for p in r["pages"])
            print(line)
        counts = {}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print("summary:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


def cmd_marker(args):
    print(marker(args.fwid))


def cmd_record(args):
    man = load(args.manifest)
    key = entry_key(args.provider, args.fwid)
    man["entries"][key] = {"slug": args.slug, "fwId": args.fwid, "provider": args.provider,
                           "pageId": args.page_id, "url": args.url, "sourceHash": args.hash}
    if args.updated:
        man["entries"][key]["updated"] = args.updated
    save(args.manifest, man)
    print(f"recorded {key} -> {args.url or args.page_id}")


def cmd_rehash(args):
    data = json.load(open(args.features, encoding="utf-8"))
    for f in data["features"]:
        f["sourceHash"] = source_hash(f["commits"])
    with open(args.features, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"rehashed {len(data['features'])} features in {args.features}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("diff"); d.add_argument("features")
    d.add_argument("--manifest", default=".featurewiki/manifest.json")
    d.add_argument("--json", action="store_true"); d.set_defaults(func=cmd_diff)

    m = sub.add_parser("marker"); m.add_argument("fwid"); m.set_defaults(func=cmd_marker)

    r = sub.add_parser("record"); r.add_argument("slug")
    r.add_argument("--fwid", required=True); r.add_argument("--provider", required=True)
    r.add_argument("--page-id", dest="page_id"); r.add_argument("--url")
    r.add_argument("--hash", required=True); r.add_argument("--updated")
    r.add_argument("--manifest", default=".featurewiki/manifest.json"); r.set_defaults(func=cmd_record)

    rh = sub.add_parser("rehash"); rh.add_argument("features"); rh.set_defaults(func=cmd_rehash)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
