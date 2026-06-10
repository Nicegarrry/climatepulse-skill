#!/usr/bin/env python3
"""Mark the items in state/new_items.json as seen — AFTER a successful digest.

Stores {id: {t: title_hash, d: iso_date}} so dedup works by URL id AND title.
Prunes entries older than --keep-days to keep seen.json bounded.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-days", type=int, default=90)
    args = ap.parse_args()

    seen_path = STATE / "seen.json"
    items_path = STATE / "new_items.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    items = json.loads(items_path.read_text()) if items_path.exists() else []

    now = datetime.now(timezone.utc)
    today = now.isoformat()
    for it in items:
        seen[it["id"]] = {"t": it.get("title_hash"), "d": today}

    cutoff = now - timedelta(days=args.keep_days)
    pruned = {}
    for k, v in seen.items():
        try:
            d = datetime.fromisoformat(v["d"]) if isinstance(v, dict) else None
        except Exception:
            d = None
        if d is None or d >= cutoff:
            pruned[k] = v

    seen_path.write_text(json.dumps(pruned, indent=2))
    print(json.dumps({"committed": len(items), "total_seen": len(pruned)}))


if __name__ == "__main__":
    main()
