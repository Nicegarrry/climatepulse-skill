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

# ClimatePulse editorial design language — exact tokens from the app's globals.css
# (warm paper / forest / sage-tint / plum / amber, Crimson Pro display serif +
# Source Sans 3 + JetBrains Mono, editorial 4-8px radii). Web fonts load from
# Google Fonts with serif/sans/mono fallbacks so it still renders offline.
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@500;600;700&family=Source+Sans+3:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
:root{
--bg:#FAF9F7;--surface:#FFFFFF;--paper-dark:#F5F3F0;
--border:#E8E5E0;--border-light:#F0EEEA;
--ink:#1A1A1A;--ink-sec:#5C5C5C;--ink-muted:#8C8C8C;--ink-faint:#B3B3B3;
--forest:#1E4D2B;--forest-mid:#4A7C59;--sage:#94A88A;--sage-tint:#EFF4EC;
--plum:#3D1F3D;--plum-light:#F5EEF5;--amber:#B8860B;
--sans:'Source Sans 3',ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
--serif:'Crimson Pro',Georgia,'Times New Roman',serif;
--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
.app{display:flex;min-height:100vh}
nav{width:190px;flex-shrink:0;background:var(--bg);border-right:1px solid var(--border);padding:26px 14px;position:sticky;top:0;height:100vh}
nav .logo{font:600 20px/1.1 var(--serif);color:var(--forest);letter-spacing:-.01em;margin:0 8px 28px;display:block}
nav button{display:block;width:100%;text-align:left;border:0;background:none;padding:9px 12px;margin-bottom:3px;border-radius:6px;cursor:pointer;color:var(--ink-sec);font:500 14px/1 var(--sans)}
nav button:hover{background:var(--paper-dark);color:var(--ink)}
nav button.active{background:var(--sage-tint);color:var(--forest);font-weight:600}
main{flex:1;max-width:880px;margin:0 auto;padding:40px 36px 90px}
h1{font:600 34px/1.15 var(--serif);letter-spacing:-.015em;margin:0 0 6px}
.sub{color:var(--ink-muted);font:500 12px/1 var(--mono);text-transform:uppercase;letter-spacing:.08em;margin-bottom:30px}
.daily-number{position:relative;background:var(--forest);color:#fff;border-radius:8px;padding:24px 28px;margin:0 0 32px;overflow:hidden}
.daily-number:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--amber)}
.daily-number .v{font:600 40px/1.05 var(--serif)}
.daily-number .l{opacity:.85;font-size:14px;line-height:1.5;margin-top:8px;max-width:62ch}
.tab{display:none}.tab.active{display:block}
.md .kicker{color:var(--ink-muted);font:500 12px/1.5 var(--mono);text-transform:uppercase;letter-spacing:.06em;margin:0 0 26px}
.md h2{font:600 23px/1.25 var(--serif);letter-spacing:-.01em;margin:34px 0 10px;padding-top:20px;border-top:1px solid var(--border-light)}
.md h3{font:600 17px/1.3 var(--serif);margin:24px 0 6px}
.md p{margin:10px 0;color:var(--ink-sec)}
.md strong{color:var(--ink);font-weight:600}
.md a{color:var(--forest);text-decoration:none;border-bottom:1px solid var(--sage)}
.md a:hover{background:var(--sage-tint)}
.md ul{padding-left:20px}.md li{margin:8px 0;color:var(--ink-sec)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 22px}
.chip{font:500 11px/1 var(--mono);text-transform:lowercase;letter-spacing:.02em;padding:6px 11px;border:1px solid var(--border);border-radius:6px;background:var(--surface);cursor:pointer;color:var(--ink-sec)}
.chip:hover{border-color:var(--sage)}
.chip.active{background:var(--forest);color:#fff;border-color:var(--forest)}
.row{border-bottom:1px solid var(--border-light);padding:16px 0;display:flex;gap:16px}
.row .score{font:600 13px/1 var(--mono);color:var(--forest);width:32px;flex-shrink:0;padding-top:3px}
.row h4{margin:0 0 4px;font:600 16px/1.35 var(--serif)}
.row h4 a{color:var(--ink);text-decoration:none}.row h4 a:hover{color:var(--forest)}
.row .meta{font:500 11px/1.4 var(--mono);color:var(--ink-muted);text-transform:uppercase;letter-spacing:.03em}
.row .meta a{color:var(--forest);text-decoration:none}.row .meta a:hover{text-decoration:underline}
.row .why{font-size:14px;color:var(--ink-sec);margin-top:5px}
.dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--amber);margin-left:7px;vertical-align:middle}
.arc a{display:block;padding:12px 0;border-bottom:1px solid var(--border-light);color:var(--ink);text-decoration:none;font:500 15px/1 var(--mono)}
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
        elif line.startswith("> "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f'<p class="kicker">{inline(line[2:])}</p>')
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
  <div class="meta"><a href="{html.escape(r.get('url','#'))}">{html.escape(str(r.get('source','')))}</a> · {html.escape(str(r.get('domain','')))} · {html.escape(str(r.get('signal_type','')))}</div>
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
