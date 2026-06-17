#!/usr/bin/env python3
"""Bundle feature docs into a self-contained local HTML wiki (works on file://, no server needed).

Reads <docs>/*.md, emits <out>/content.js (a window.WIKI bundle) and <out>/index.html (a viewer with
sidebar nav, live filter, and CDN-rendered markdown + syntax highlighting, with a raw-markdown
fallback when offline).

Usage:
  python3 build_html.py --docs .featurewiki/docs --out .featurewiki/site --title "My Feature Wiki"

Conventions read from each .md:
  line 1   <!-- feature-wiki-id: <id> -->   (optional marker; carried into the bundle)
  '# ...'  first H1 is the title
  group    optional '<!-- group: Name -->' sets the sidebar group (default "Features")
  tickets  first 'KEY-123' on a line starting with '**Tickets:'/'Jira:' becomes the sidebar tag
Stdlib only.
"""
import argparse
import glob
import json
import os
import re

MARKER_RE = re.compile(r"<!--\s*feature-wiki-id:\s*(.+?)\s*-->")
GROUP_RE = re.compile(r"<!--\s*group:\s*(.+?)\s*-->")
H1_RE = re.compile(r"^#\s+(.+)$", re.M)
KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-\d+")

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>__TITLE__</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<style>
:root{--bg:#0d1117;--panel:#111722;--panel2:#0a0f17;--border:#222c3a;--text:#c9d4e3;--muted:#7d8aa0;--accent:#4aa3ff;--code:#0b0f16}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--text);font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;display:flex}
#sidebar{width:312px;min-width:312px;height:100vh;overflow-y:auto;background:var(--panel2);border-right:1px solid var(--border);padding:18px 0}
#sidebar h1{font-size:15px;margin:0 18px 4px}#sidebar .sub{color:var(--muted);font-size:12px;margin:0 18px 14px}
#search{width:calc(100% - 36px);margin:0 18px 14px;padding:8px 10px;background:var(--code);border:1px solid var(--border);border-radius:7px;color:var(--text);font-size:13px}
#search:focus{outline:none;border-color:var(--accent)}
.group{color:var(--muted);text-transform:uppercase;font-size:11px;letter-spacing:.8px;margin:16px 18px 5px;font-weight:700}
a.nav{display:flex;justify-content:space-between;gap:8px;padding:7px 18px;color:var(--text);text-decoration:none;font-size:13.5px;border-left:3px solid transparent;cursor:pointer}
a.nav:hover{background:var(--panel)}a.nav.active{background:var(--panel);border-left-color:var(--accent);color:#fff}
a.nav .jira{color:var(--muted);font-size:10.5px;font-family:ui-monospace,monospace;white-space:nowrap}
#main{flex:1;height:100vh;overflow-y:auto}#content{max-width:920px;margin:0 auto;padding:46px 54px 120px}
#content h1{font-size:30px;border-bottom:1px solid var(--border);padding-bottom:14px;color:#fff}
#content h2{font-size:21px;margin-top:38px;border-bottom:1px solid var(--border);padding-bottom:7px;color:#eaf1fb}
#content h3{font-size:16.5px;margin-top:26px;color:#dce6f4}#content a{color:var(--accent);text-decoration:none}
#content a:hover{text-decoration:underline}#content code{background:var(--code);padding:2px 6px;border-radius:5px;font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#e3b341}
#content pre{background:var(--code);border:1px solid var(--border);border-radius:9px;padding:16px;overflow-x:auto}
#content pre code{background:none;padding:0;color:#c9d4e3;font-size:12.8px}#content strong{color:#fff}
#content hr{border:none;border-top:1px solid var(--border);margin:30px 0}
.offline{display:none;background:#3d2a12;border:1px solid #7a5a1f;color:#f0c674;padding:10px 14px;border-radius:8px;margin-bottom:20px;font-size:13px}
::-webkit-scrollbar{width:11px}::-webkit-scrollbar-thumb{background:#1d2632;border-radius:6px}
</style></head><body>
<nav id="sidebar"><h1>__TITLE__</h1><div class="sub">Feature wiki</div>
<input id="search" placeholder="Filter features…" autocomplete="off"/><div id="nav"></div></nav>
<div id="main"><div id="content">
<div class="offline" id="offline">Markdown renderer failed to load (offline?). Raw markdown shown below.</div>
<div id="doc"></div></div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="content.js"></script>
<script>
var DOCS=(window.WIKI&&window.WIKI.docs)||[],byId={};DOCS.forEach(function(d){byId[d.slug]=d});
function buildNav(f){f=(f||"").toLowerCase();var n=document.getElementById("nav");n.innerHTML="";var lg=null;
DOCS.forEach(function(d){var hay=(d.title+" "+d.group+" "+d.jira+" "+d.md).toLowerCase();if(f&&hay.indexOf(f)===-1)return;
if(d.group!==lg){var g=document.createElement("div");g.className="group";g.textContent=d.group;n.appendChild(g);lg=d.group}
var a=document.createElement("a");a.className="nav";a.dataset.slug=d.slug;a.href="#"+d.slug;
a.innerHTML="<span>"+d.title+"</span>"+(d.jira?"<span class='jira'>"+d.jira+"</span>":"");
a.onclick=function(e){e.preventDefault();show(d.slug)};n.appendChild(a)})}
function show(slug){var d=byId[slug]||DOCS[0];if(!d)return;location.hash=d.slug;var el=document.getElementById("doc");
if(window.marked){if(window.hljs){marked.setOptions({highlight:function(c,l){try{return l&&hljs.getLanguage(l)?hljs.highlight(c,{language:l}).value:hljs.highlightAuto(c).value}catch(e){return c}}})}
el.innerHTML=marked.parse(d.md)}else{document.getElementById("offline").style.display="block";var p=document.createElement("pre");p.textContent=d.md;el.innerHTML="";el.appendChild(p)}
document.querySelectorAll("a.nav").forEach(function(a){a.classList.toggle("active",a.dataset.slug===d.slug)});document.getElementById("main").scrollTop=0}
document.getElementById("search").addEventListener("input",function(e){buildNav(e.target.value)});
buildNav("");show((location.hash||"").replace("#","")||(DOCS[0]&&DOCS[0].slug));
</script></body></html>
"""


def parse_doc(path):
    md = open(path, encoding="utf-8").read()
    slug = os.path.splitext(os.path.basename(path))[0]
    h1 = H1_RE.search(md)
    title = h1.group(1).strip() if h1 else slug
    gm = GROUP_RE.search(md)
    group = gm.group(1).strip() if gm else "Features"
    mk = MARKER_RE.search(md)
    fw_id = mk.group(1).strip() if mk else ""
    jira = ""
    for line in md.splitlines():
        if line.startswith(("**Tickets:", "Tickets:", "**Jira:", "Jira:")):
            k = KEY_RE.search(line)
            if k:
                jira = k.group(0)
            break
    return {"slug": slug, "title": title, "group": group, "fwId": fw_id, "jira": jira, "md": md}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=".featurewiki/docs")
    ap.add_argument("--out", default=".featurewiki/site")
    ap.add_argument("--title", default="Feature Wiki")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.docs, "*.md")))
    docs = [parse_doc(p) for p in paths]
    # stable group order: first appearance, but keep "Overview" first if present
    order, seen = [], set()
    for d in docs:
        if d["group"] not in seen:
            seen.add(d["group"]); order.append(d["group"])
    if "Overview" in order:
        order.remove("Overview"); order.insert(0, "Overview")
    docs.sort(key=lambda d: (order.index(d["group"]), d["title"].lower()))

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "content.js"), "w", encoding="utf-8") as f:
        f.write("window.WIKI = " + json.dumps({"docs": docs}, ensure_ascii=False) + ";\n")
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_HTML.replace("__TITLE__", args.title))
    print(f"Built wiki: {len(docs)} docs -> {args.out}/index.html")


if __name__ == "__main__":
    main()
