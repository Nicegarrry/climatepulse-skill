# climatepulse — onboarding (first run only)

Goal: in one short interactive pass, learn who this digest serves and produce a
tailored `config/feeds.yaml`, then write `state/profile.md`. Run this only when
`state/profile.md` is absent.

## 1. Interview

Use the `AskUserQuestion` tool. Ask these, batching where natural. Offer the
listed options but always allow free text.

1. **Role / lens** — how should stories be weighted?
   e.g. Investor/analyst · Policy/regulatory · Engineer/technical ·
   Operator/industry · Researcher/academic · Generalist.
2. **Sectors of interest** (multi-select) — pull from `config/taxonomy.yaml`
   domains (solar, wind, grid/storage, EVs/transport, policy/regulation,
   carbon markets, hydrogen, finance/ESG, industry/heavy, nature/land, etc.).
3. **Jurisdictions** — geographies to prioritise (e.g. Australia, EU, US,
   India, global). Used to boost matching stories.
4. **Languages** — English only, or include non-English sources? (Affects which
   default feeds are kept and prompts the user to add local sources.)
5. **Digest length** — Tight (5–8 stories) · Standard (~12) · Comprehensive (15).
6. **Extra sources** — any must-have feeds/sites? (Capture URLs; this is where
   the user's niche/local sources enter — the long tail that makes the digest
   theirs.)
7. **Email newsletters** — "Do you get climate/energy newsletters by email? If
   you have Gmail connected in Claude, I can pull relevant ones in as a source."
   If yes, capture either specific senders (e.g. `daily@carbonbrief.org`) or a
   Gmail label they file newsletters under (e.g. `Newsletters/Climate`).

## 2. Build `config/feeds.yaml`

Start from `config/feeds.default.yaml`. Then:

- **Always keep every `core: true` source**, regardless of sector filters — they
  guarantee the digest is never empty for a narrow profile.
- Of the non-core sources, **keep those whose `tags` overlap** the chosen
  sectors/jurisdictions; drop clearly irrelevant ones to cut noise. Match
  loosely: taxonomy domains are hyphenated compounds (`grid-and-storage`,
  `ev-and-transport`) while feed `tags` are flat partials (`grid`, `storage`,
  `ev`). Treat any shared word as an overlap, and when unsure keep the source —
  scoring demotes off-topic items anyway. Better a slightly long list than an
  empty digest.
- Preserve the `defaults:` block (`max_article_age_days`, `per_feed_limit`).

### Adding the user's suggested sources (validate before adding)

For each source the user named, run the validator **before** writing it in:

```
# a real feed URL:
python3 scripts/validate_feeds.py <url>
# a website (let it discover the feed path):
python3 scripts/validate_feeds.py --discover <site-url>
```

Then act on the reported `status`:

| status | action |
|---|---|
| `ok` | add it — record the resolved `url`, infer `tags` from the user's interest, set `tier: 2` |
| `stale` (no items in 30+ days) | add but flag in `state/learning.md` as low-activity; confirm with the user |
| `not-found` (HTTP 404/410) | the URL is wrong or moved — run `--discover` on the site root, or ask the user for the correct feed URL |
| `not-a-feed` | the URL loads but isn't a feed — run `--discover` on the site root, or ask for the direct feed URL |
| `empty` | parses as a feed but has zero items — likely defunct; confirm with the user before adding |
| `no-feed-found` (from `--discover`) | tell the user no feed was found at that site; ask for the direct feed URL |
| `blocked` / `unreachable` | do **not** silently add. If others validated fine, it's likely this site blocks the run environment (see network note); tell the user and offer to add it unvalidated for a local run |

Only validated sources get appended. Write the result to `config/feeds.yaml`
(this takes precedence over the default).

### Email sources (if the user opted in)

For each newsletter sender/label, add a `type: email` source. Its `query` is a
Gmail search string, not a URL:

```yaml
- name: Carbon Brief Daily (email)
  type: email
  query: "from:(daily@carbonbrief.org) newer_than:2d"
  tags: [policy, science, global]
  tier: 1
# or by label:
- name: Climate newsletters
  type: email
  query: "label:Newsletters/Climate newer_than:2d"
  tags: [policy, energy]
  tier: 2
```

**Validate by test-searching**, not with `validate_feeds.py` (that's RSS only):
if Gmail is connected, run each `query` once and report how many messages it
matched in the last few days. 0 matches → tell the user the sender/label may be
wrong and confirm before keeping it. If Gmail is **not** connected this session,
still write the source but note it's unverified and only active when Gmail is
available (e.g. an interactive/local run, not necessarily a headless Routine).

## 3. Write `state/profile.md`

Capture the answers as durable memory, e.g.:

```markdown
# Profile

- **Role / lens:** <role>
- **Sectors:** <list>
- **Jurisdictions:** <list>
- **Languages:** <list>
- **Digest length:** <tight | standard | comprehensive>
- **Significance floor:** 55 (use 50 for a comprehensive digest, 55 for standard, 60 for tight)

## Notes
<anything the user said that should shape weighting>
```

## 4. Seed the learning + feedback files

- Create `state/learning.md` with a header and one entry noting the initial
  source/profile setup.
- Create `state/feedback.md` with just `# Feedback` (the drop-box the user can
  append notes to between runs).
- Create `state/source_stats.json` as `{}`.

## 4b. Health-check the final list

Run `python3 scripts/validate_feeds.py --all` against the assembled
`config/feeds.yaml`. Summarise by counting `status` across `results[*]` (e.g.
"12 ok, 1 blocked"). If **any** come back `blocked`, name them — that usually
points at the run environment's network allowlist rather than a dead feed
(DeSmog, for example, is Cloudflare-protected and 403s from many cloud IPs while
working fine locally). The user may need to run locally or widen the allowlist
(see the README network note). (`--all` only checks RSS sources; `type: email`
sources are validated separately by test-search.)

## 5. Hand off

Tell the user setup is done, show the final source count, and explain they can:
- run the digest now (continue to Step 1 of SKILL.md),
- note that a few **core** sources stay in the list regardless of the sector
  filters so the digest is never empty on a narrow profile — those aren't noise;
  leave them unless you truly never want that outlet,
- drop quick notes into `state/feedback.md` anytime to steer future runs,
- schedule a daily run (system cron + `claude -p "/climatepulse"`, a GitHub
  Actions schedule, or a Claude Code **Routine** on the web).
