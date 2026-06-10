#!/usr/bin/env python3
"""Render the wiki into a single self-contained static dashboard.

Reads wiki/digests/*.md and wiki/articles/**/*.md and emits wiki/dashboard.html
— one file, inline CSS + a little vanilla JS, no build step, no server. It is a
simpler echo of the ClimatePulse dashboard: a Briefing tab (latest digest), a
Newsroom tab (filterable article wire), and an Archive tab.

Pure stdlib + PyYAML. Open the file in a browser, or `python3 -m http.server`.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML missing — run: pip install -r scripts/requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"

# Editorial palette echoing the production dashboard (sage / forest / ink).
CSS = """
:root{--bg:#f6f5f0;--surface:#fffdf8;--border:#e3e0d6;--ink:#23271f;
--ink-sec:#5a6152;--ink-muted:#8b9082;--forest:#2f5d45;--sage:#e8efe6;--plum:#7a4b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.app{display:flex;min-height:100vh}
nav{width:170px;flex-shrink:0;border-right:1px solid var(--border);padding:22px 12px;
position:sticky;top:0;height:100vh}
nav .logo{font:600 17px/1 Georgia,serif;color:var(--forest);margin:0 8px 22px}
nav button{display:block;width:100%;text-align:left;border:0;background:none;
padding:8px 10px;margin-bottom:2px;border-radius:6px;cursor:pointer;color:var(--ink-sec);
font-size:13px}
nav button.active{background:var(--sage);color:var(--forest);font-weight:600}
main{flex:1;max-width:860px;margin:0 auto;padding:34px 28px 80px}
h1{font:600 26px/1.2 Georgia,serif;margin:0 0 4px}
.sub{color:var(--ink-muted);font-size:13px;margin-bottom:26px}
.daily-number{background:var(--forest);color:#fff;border-radius:12px;padding:20px 24px;margin:0 0 26px}
.daily-number .v{font:700 30px/1 Georgia,serif}
.daily-number .l{opacity:.85;font-size:13px;margin-top:6px}
.tab{display:none}.tab.active{display:block}
.md h2{font:600 18px/1.3 Georgia,serif;margin:28px 0 8px}
.md h3{font-size:15px;margin:20px 0 6px}
.md a{color:var(--forest)}.md p{margin:8px 0}.md ul{padding-left:20px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 20px}
.chip{font-size:11px;text-transform:lowercase;letter-spacing:.03em;padding:4px 10px;
border:1px solid var(--border);border-radius:20px;background:var(--surface);cursor:pointer;color:var(--ink-sec)}
.chip.active{background:var(--forest);color:#fff;border-color:var(--forest)}
.row{border-bottom:1px solid var(--border);padding:14px 0;display:flex;gap:14px}
.row .score{font:700 13px/1 ui-monospace,monospace;color:var(--forest);width:30px;flex-shrink:0;padding-top:2px}
.row h4{margin:0 0 4px;font:600 15px/1.35 Georgia,serif}
.row h4 a{color:var(--ink);text-decoration:none}.row h4 a:hover{color:var(--forest)}
.row .meta{font-size:12px;color:var(--ink-muted)}
.row .why{font-size:13px;color:var(--ink-sec);margin-top:4px}
.dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--plum);margin-left:6px;vertical-align:middle}
.arc a{display:block;padding:10px 0;border-bottom:1px solid var(--border);color:var(--ink);text-decoration:none}
.arc a:hover{color:var(--forest)}
"""

JS = """
function show(t){document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
document.getElementById('tab-'+t).classList.add('active');
document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.t===t));}
function filt(d){document.querySelectorAll('#tab-newsroom .chip').forEach(c=>c.classList.toggle('active',c.dataset.d===d));
document.querySelectorAll('#tab-newsroom .row').forEach(r=>{r.style.display=(d==='all'||r.dataset.d===d)?'flex':'none';});}
"""


def md_to_html(md: str) -> str:
    out, in_ul = [], False
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("### "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            continue  # page already has its own H1
        elif line.startswith(("- ", "* ")):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(line[2:])}</li>")
        elif line.strip() == "":
            if in_ul: out.append("</ul>"); in_ul = False
        else:
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<p>{inline(line)}</p>")
    if in_ul: out.append("</ul>")
    return "\n".join(out)


def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s


def parse_record(path: Path):
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None
    meta = yaml.safe_load(m.group(1)) or {}
    meta["_body"] = m.group(2).strip()
    return meta


def main():
    digests = sorted(WIKI.glob("digests/*.md"), reverse=True)
    if not digests:
        sys.exit("no digests found — run the skill first")
    latest = digests[0]
    latest_date = latest.stem

    records = [r for r in (parse_record(p) for p in WIKI.glob("articles/**/*.md")) if r]
    records.sort(key=lambda r: (r.get("significance", 0)), reverse=True)
    domains = sorted({r.get("domain", "other") for r in records})

    rows = []
    for r in records:
        urgent = '<span class="dot"></span>' if (r.get("significance", 0) or 0) >= 80 else ""
        rows.append(f"""<div class="row" data-d="{html.escape(str(r.get('domain','other')))}">
  <div class="score">{int(r.get('significance',0) or 0)}</div>
  <div><h4><a href="{html.escape(r.get('url','#'))}">{html.escape(r.get('title','(untitled)'))}</a>{urgent}</h4>
  <div class="meta">{html.escape(str(r.get('source','')))} · {html.escape(str(r.get('domain','')))} · {html.escape(str(r.get('signal_type','')))}</div>
  <div class="why">{html.escape(str(r.get('why_it_matters','')))}</div></div></div>""")

    chips = '<span class="chip active" data-d="all" onclick="filt(\'all\')">all</span>' + "".join(
        f'<span class="chip" data-d="{html.escape(d)}" onclick="filt(\'{html.escape(d)}\')">{html.escape(d)}</span>'
        for d in domains)

    archive = "".join(f'<a href="digests/{p.stem}.md">{p.stem}</a>' for p in digests)

    page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>climate-digest · {latest_date}</title><style>{CSS}</style></head><body>
<div class="app">
<nav><div class="logo">climate&nbsp;pulse</div>
<button class="active" data-t="briefing" onclick="show('briefing')">Briefing</button>
<button data-t="newsroom" onclick="show('newsroom')">Newsroom</button>
<button data-t="archive" onclick="show('archive')">Archive</button></nav>
<main>
<div id="tab-briefing" class="tab active">
<h1>Daily Briefing</h1><div class="sub">{latest_date}</div>
<div class="md">{md_to_html(latest.read_text())}</div></div>

<div id="tab-newsroom" class="tab">
<h1>Newsroom</h1><div class="sub">{len(records)} tracked stories · sorted by significance</div>
<div class="chips">{chips}</div>{''.join(rows)}</div>

<div id="tab-archive" class="tab"><h1>Archive</h1>
<div class="sub">{len(digests)} digests</div><div class="arc">{archive}</div></div>
</main></div><script>{JS}</script></body></html>"""

    out = WIKI / "dashboard.html"
    out.write_text(page)
    print(json.dumps({"dashboard": str(out), "digests": len(digests), "records": len(records)}))


if __name__ == "__main__":
    main()
