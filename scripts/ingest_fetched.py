#!/usr/bin/env python3
"""Normalise agent-fetched RSS items into state/new_items.json — NO network.

For the Claude web / desktop-app environment: the bundled fetch_feeds.py can't
reach publishers there (the code sandbox blocks outbound network), but the
AGENT's own web-fetch / web-search tools can. So in that environment the agent
fetches each feed itself, assembles the items as a raw JSON array, and runs THIS
to normalise + dedup them into the same state/new_items.json that fetch_feeds.py
produces. That keeps id/title_hash derivation, dedup, and scoring identical
across environments — the rest of the run (Steps 3-7) is then the same everywhere.

This is the RSS twin of add_email_items.py (id from the canonical URL, origin
"rss"). It makes no network calls, so it runs fine inside the sandbox.

Input: a JSON array of objects with at least:
    url, title   (optional: source, source_tags [list], published_at, text)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state"


def norm_url(url: str) -> str:
    # Must match fetch_feeds.py so the same article dedups across environments.
    url = (url or "").strip()
    url = re.sub(r"#.*$", "", url)
    url = re.sub(r"[?&](utm_[^=]+|fbclid|gclid|mc_cid|mc_eid)=[^&]*", "", url)
    url = re.sub(r"[?&]+$", "", url)
    return url.rstrip("/").lower()


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def title_hash(t: str) -> str:
    return sha1(re.sub(r"\s+", " ", (t or "").strip().lower()))


def to_iso(d: str | None):
    if not d:
        return None
    try:
        return datetime.fromisoformat(d).astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:
        return parsedate_to_datetime(d).astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def clean(text: str | None, limit: int = 8000) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", help="path to JSON array of agent-fetched RSS items")
    args = ap.parse_args()

    raw = json.loads(Path(args.raw).read_text())
    STATE.mkdir(exist_ok=True)
    seen_path = STATE / "seen.json"
    items_path = STATE / "new_items.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    seen_ids = set(seen.keys())
    seen_titles = {v.get("t") for v in seen.values() if isinstance(v, dict)}
    items = json.loads(items_path.read_text()) if items_path.exists() else []
    have_ids = {it["id"] for it in items}
    have_titles = {it.get("title_hash") for it in items}

    added = 0
    for e in raw:
        url = norm_url(e.get("url", ""))
        if not url:
            continue
        uid, th = sha1(url), title_hash(e.get("title", ""))
        if uid in seen_ids or uid in have_ids or th in seen_titles or th in have_titles:
            continue
        items.append({
            "id": uid,
            "url": e.get("url", ""),
            "title": (e.get("title") or "").strip(),
            "source": e.get("source") or "rss",
            "source_tags": e.get("source_tags", []),
            "published_at": to_iso(e.get("published_at")),
            "title_hash": th,
            "text": clean(e.get("text")),
            "origin": "rss",
        })
        have_ids.add(uid)
        have_titles.add(th)
        added += 1

    items_path.write_text(json.dumps(items, indent=2))
    print(json.dumps({"rss_items_added": added, "total_new_items": len(items)}))


if __name__ == "__main__":
    main()
