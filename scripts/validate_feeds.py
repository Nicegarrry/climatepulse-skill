#!/usr/bin/env python3
"""Validate / discover RSS sources for climate-digest.

Used in three places:
  • onboarding — test a user-suggested feed (or site) before adding it
  • daily learning loop — health-check the active list, flag feeds that went dead
  • ad hoc — `python3 scripts/validate_feeds.py https://example.com/feed/`

Modes:
  validate_feeds.py URL [URL ...]   validate specific feeds
  validate_feeds.py --all           validate every source in the active list
  validate_feeds.py --discover URL  treat URL as a site, probe common feed paths

For each candidate it reports: status, entry count, latest entry date, feed
title — so a human (or the skill) can decide whether to add it. It NEVER edits
config; it only reports. Output is JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

try:
    import feedparser
except ImportError:
    sys.exit("feedparser missing — run: pip install -r scripts/requirements.txt")
try:
    import yaml
except ImportError:
    sys.exit("PyYAML missing — run: pip install -r scripts/requirements.txt")

CONFIG = Path(__file__).resolve().parent.parent / "config"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Common feed locations to probe when given a bare site URL.
DISCOVER_PATHS = ["feed/", "rss/", "rss.xml", "feed.xml", "atom.xml",
                  "index.xml", "feeds/posts/default", "?feed=rss2"]


def latest_date(feed):
    best = None
    for e in feed.entries:
        for key in ("published_parsed", "updated_parsed"):
            t = e.get(key)
            if t:
                d = datetime(*t[:6], tzinfo=timezone.utc)
                if best is None or d > best:
                    best = d
    return best


def check(url: str) -> dict:
    try:
        feed = feedparser.parse(url, agent=UA)
    except Exception as e:
        return {"url": url, "status": "unreachable", "error": str(e)[:200]}
    if getattr(feed, "status", None) in (401, 403, 429):
        return {"url": url, "status": "blocked", "http": feed.status,
                "hint": "bot-protection or network allowlist — see README network note"}
    if getattr(feed, "status", None) in (404, 410):
        return {"url": url, "status": "not-found", "http": feed.status,
                "hint": "dead URL — the feed moved or never existed at this path"}
    n = len(feed.entries)
    if n == 0:
        # bozo + no entries usually means "not a feed" or down
        reason = "not-a-feed" if getattr(feed, "bozo", 0) else "empty"
        return {"url": url, "status": reason,
                "bozo": str(getattr(feed, "bozo_exception", "") or "")[:120]}
    ld = latest_date(feed)
    stale = bool(ld and (datetime.now(timezone.utc) - ld).days > 30)
    return {
        "url": url,
        "status": "stale" if stale else "ok",
        "title": (feed.feed.get("title") or "").strip()[:80],
        "entries": n,
        "latest": ld.isoformat() if ld else None,
        "days_since_latest": (datetime.now(timezone.utc) - ld).days if ld else None,
    }


def discover(site: str) -> dict:
    base = site if site.endswith("/") else site + "/"
    tried = []
    for path in DISCOVER_PATHS:
        cand = urljoin(base, path)
        res = check(cand)
        tried.append({"candidate": cand, "status": res["status"]})
        if res["status"] in ("ok", "stale"):
            res["discovered_from"] = site
            res["probed"] = tried
            return res
    return {"url": site, "status": "no-feed-found", "probed": tried}


def load_active_sources():
    cfg = CONFIG / "feeds.yaml"
    if not cfg.exists():
        cfg = CONFIG / "feeds.default.yaml"
    data = yaml.safe_load(cfg.read_text()) or {}
    return [(s.get("name"), s["url"]) for s in data.get("sources", [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--all", action="store_true", help="validate the active source list")
    ap.add_argument("--discover", action="store_true", help="treat each URL as a site and probe feed paths")
    args = ap.parse_args()

    results = []
    if args.all:
        for name, url in load_active_sources():
            r = check(url)
            r["name"] = name
            results.append(r)
    else:
        if not args.urls:
            ap.error("give one or more URLs, or use --all")
        for url in args.urls:
            results.append(discover(url) if args.discover else check(url))

    ok = sum(1 for r in results if r["status"] == "ok")
    print(json.dumps({"checked": len(results), "ok": ok, "results": results}, indent=2))


if __name__ == "__main__":
    main()
