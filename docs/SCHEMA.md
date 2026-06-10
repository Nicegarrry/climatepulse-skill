# Article record schema

Every kept article is one Markdown file at
`wiki/articles/<YYYY>/<YYYY-MM-DD>/<slug>.md`. The YAML frontmatter **is** the
canonical record — this is intentionally the future "datalake row", so keep it
stable. The body is a 2–4 sentence summary.

```markdown
---
schema_version: 1
id: <sha1 of canonical url>          # stable; never change derivation
url: https://example.com/article
title: Article title
source: Carbon Brief
published_at: 2026-06-10T08:00:00+00:00
ingested_at: 2026-06-10T19:05:00+00:00
domain: policy-and-regulation        # one of config/taxonomy.yaml domains
signal_type: policy-or-regulation    # one of config/taxonomy.yaml signal_types
sentiment: neutral                   # positive | neutral | negative
origin: rss                          # rss | email — where the item came from
jurisdictions: [EU]                  # [] if none
entities:
  - {name: European Commission, type: organisation}
  - {name: CBAM, type: policy}
significance: 78                     # 0–100
why_it_matters: One-sentence reason this is on the radar today.
---

Two to four sentences of summary, written for a practitioner skimming at 6am.
Link out only via the `url` field above, not inline.
```

## Invariants (so this upgrades into the shared pool cleanly)

- `id = sha1(normalised_url)` — the dedup key. Identical across all users, which
  is exactly what lets a future shared pool merge contributions without
  duplication.
- Records are **immutable** once written. Corrections become a new dated record,
  never an edit in place.
- `schema_version` bumps only when fields change; older records stay readable.
- `domain` / `signal_type` are controlled vocabularies from `config/taxonomy.yaml`.
  A pool would freeze these centrally; locally you may extend them.
- **`origin: email` records are private** — derived from the user's personal
  inbox. They live only in the local wiki and must **never** be contributed to a
  shared/public pool. A future pool sync filters to `origin: rss` only. For email
  items `url` is a Gmail permalink (or empty), and `id` derives from the Gmail
  message id, so the same newsletter is deduped across runs.

## Why frontmatter instead of a DB

Human-readable in any editor, diff-friendly in git, greppable, and a one-line
parser turns the whole `wiki/articles/` tree into rows whenever you do stand up
the central store. No migration, no ORM, no vectors — until you actually want
them.
