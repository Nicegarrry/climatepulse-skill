#!/usr/bin/env python3
"""Merge Gmail-sourced items into state/new_items.json.

RSS collection is deterministic (fetch_feeds.py). Email collection can't be —
the Gmail MCP tools are only callable by the skill (Claude), not a script. So
the skill reads relevant emails via its Gmail connection, writes them as a raw
JSON array, then runs THIS to normalise + dedup them into the same
new_items.json that RSS items land in. That keeps id/title_hash derivation in
one place, so email and RSS flow through identical scoring + the same seen.json.

Input: a JSON array of objects with at least:
    message_id, subject, from, date   (body recommended)
  optional: source_name, tags (list), permalink
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
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", help="path to JSON array of raw email items")
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
        mid = (e.get("message_id") or "").strip()
        subj = (e.get("subject") or "").strip()
        if not mid and not subj:
            continue
        uid = sha1("gmail:" + mid) if mid else sha1("gmail:" + subj + (e.get("date") or ""))
        th = title_hash(subj)
        if uid in seen_ids or uid in have_ids or th in seen_titles or th in have_titles:
            continue
        items.append({
            "id": uid,
            "url": e.get("permalink") or "",
            "title": subj or "(email)",
            "source": e.get("source_name") or e.get("from") or "email",
            "source_tags": e.get("tags", []),
            "published_at": to_iso(e.get("date")),
            "title_hash": th,
            "text": clean(e.get("body")),
            "origin": "email",
        })
        have_ids.add(uid)
        have_titles.add(th)
        added += 1

    items_path.write_text(json.dumps(items, indent=2))
    print(json.dumps({"email_items_added": added, "total_new_items": len(items)}))


if __name__ == "__main__":
    main()
