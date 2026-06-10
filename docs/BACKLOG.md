# Backlog

Deferred ideas, roughly in priority order.

## v2

- **Newsletter link-splitting.** Today each newsletter email becomes one item.
  For link-heavy digests (Carbon Brief, Heatmap, Canary Media) extract the
  individually notable stories as separate items, deduping against RSS so a
  linked article that also arrived via RSS isn't double-counted. Lives in the
  Step 2b email path (`SKILL.md`) + a small parser feeding `add_email_items.py`.

## Later

- **Feed auto-discovery in onboarding** — given a site URL, `validate_feeds.py
  --discover` already probes common paths; surface that more proactively when a
  user names a site rather than a feed.
- **Scheduled feed health check** — GitHub Actions running
  `validate_feeds.py --all` weekly, opening an issue when a feed goes dark.
- **Shared append-only pool (option A)** — `submit_record` / `get_unenriched`
  against a central store; `origin: rss` only (email stays private).
- **Federated compute (option B)** — coordinator + consensus/audit so pooled
  contributions from many users are trustworthy.

## Polish

- **Ordered lists in the dashboard.** `build_dashboard.py`'s `md_to_html()`
  renders `- ` / `* ` bullets but not `1.` numbered lists, so a numbered list in
  a digest would render as plain lines. Digests use bullets today, so this is
  cosmetic; add `<ol>` handling when a digest needs it.
