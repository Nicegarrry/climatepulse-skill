#!/usr/bin/env python3
"""Deterministic RSS collection + dedup for the climate-digest skill.

Reads the source list (config/feeds.yaml, falling back to feeds.default.yaml),
fetches each feed, drops anything already in state/seen.json or older than the
age cutoff, and writes the surviving NEW items to state/new_items.json for the
skill (Claude) to enrich.

It deliberately does NOT mark items seen — commit_seen.py does that, only after
the digest is written, so a failed run never silently drops a day's news.

Pure stdlib + feedparser (+ optional trafilatura for full text). No DB, no vectors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import feedparser
except ImportError:
    sys.exit("feedparser missing — run: pip install -r scripts/requirements.txt")
try:
    import yaml
except ImportError:
    sys.exit("PyYAML missing — run: pip install -r scripts/requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
CONFIG = ROOT / "config"

# Many publishers 403 the default feedparser UA (bot protection). Present a
# realistic browser UA. NB: some CDNs still block datacenter IPs regardless —
# see the network-allowlist note in README/SKILL if feeds 403 from a cloud run.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def norm_url(url: str) -> str:
    url = (url or "").strip()
    url = re.sub(r"#.*$", "", url)
    url = re.sub(r"[?&](utm_[^=]+|fbclid|gclid|mc_cid|mc_eid)=[^&]*", "", url)
    url = re.sub(r"[?&]+$", "", url)
    return url.rstrip("/").lower()


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def title_hash(title: str) -> str:
    return sha1(re.sub(r"\s+", " ", (title or "").strip().lower()))


def load_sources():
    cfg = CONFIG / "feeds.yaml"
    if not cfg.exists():
        cfg = CONFIG / "feeds.default.yaml"
    data = yaml.safe_load(cfg.read_text()) or {}
    return data.get("sources", []), data.get("defaults", {})


def parse_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def best_text(entry, fulltext: bool) -> str:
    summary = re.sub(r"<[^>]+>", " ", entry.get("summary", "") or "")
    summary = re.sub(r"\s+", " ", summary).strip()
    if not fulltext:
        return summary
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(entry.get("link"))
        text = trafilatura.extract(downloaded) if downloaded else None
        if text and len(text.split()) >= 100:
            return text.strip()
    except Exception:
        pass
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fulltext", action="store_true",
                    help="best-effort full-text via trafilatura (falls back to summary)")
    ap.add_argument("--max-age-days", type=int, default=None)
    args = ap.parse_args()

    sources, defaults = load_sources()
    max_age = args.max_age_days if args.max_age_days is not None else int(defaults.get("max_article_age_days", 7))
    per_feed_limit = int(defaults.get("per_feed_limit", 40))
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age)

    STATE.mkdir(exist_ok=True)
    seen_path = STATE / "seen.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    seen_ids = set(seen.keys())
    seen_titles = {v.get("t") for v in seen.values() if isinstance(v, dict)}

    new_items, run_titles, stats = [], set(), {}
    email_sources = 0
    for src in sources:
        if src.get("type", "rss") != "rss":
            email_sources += 1   # handled by the skill via Gmail MCP, not here
            continue
        name = src.get("name", src.get("url"))
        try:
            feed = feedparser.parse(src["url"], agent=UA)
        except Exception as e:  # never let one bad feed kill the run
            stats[name] = {"error": str(e)}
            continue
        kept = 0
        for entry in feed.entries[:per_feed_limit]:
            url = norm_url(entry.get("link", ""))
            if not url:
                continue
            uid, th = sha1(url), title_hash(entry.get("title", ""))
            if uid in seen_ids or th in seen_titles or th in run_titles:
                continue
            dt = parse_date(entry)
            if dt and dt < cutoff:
                continue
            run_titles.add(th)
            new_items.append({
                "id": uid,
                "url": entry.get("link", ""),
                "title": (entry.get("title") or "").strip(),
                "source": name,
                "source_tags": src.get("tags", []),
                "published_at": dt.isoformat() if dt else None,
                "title_hash": th,
                "text": best_text(entry, args.fulltext),
                "origin": "rss",
            })
            kept += 1
        stats[name] = {"entries": len(feed.entries), "new": kept}

    (STATE / "new_items.json").write_text(json.dumps(new_items, indent=2))
    print(json.dumps({"new_items": len(new_items), "rss_sources": len(sources) - email_sources,
                      "email_sources": email_sources, "per_source": stats}, indent=2))


if __name__ == "__main__":
    main()
