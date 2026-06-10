# climate-digest — guide

A single-user replica of the ClimatePulse daily pipeline, packaged as one Claude
skill: fetch climate/energy/sustainability news → tag & score → synthesise a
morning briefing → store it as a local Markdown wiki. **No database, no vectors.**

Per-article records (`SCHEMA.md`) are deliberately the same shape a future
shared/crowdsourced pool would store, so v1 upgrades without a rewrite.

## Install

```bash
pip install -r scripts/requirements.txt
```

`trafilatura` is optional — without it the fetch falls back to RSS summaries.

## First run — onboarding (interactive, once)

In Claude Code: `/climate-digest`. With no `state/profile.md` present, the skill
runs `onboarding.md`: a short interview that tailors your sources into
`config/feeds.yaml` and writes your profile. This is the only step needing a
human.

## Daily run

`/climate-digest` collects new items, scores them against your profile, writes
the briefing to `wiki/digests/<date>.md` and records to `wiki/articles/...`,
updates `wiki/index.md`, and appends a learning reflection.

> **`--fulltext` is slow.** `fetch_feeds.py --fulltext` fetches and extracts each
> article's body (via trafilatura) and runs ~10–15× slower than the headline-only
> fetch (e.g. ~75s vs ~6s for the default list). It's worth it for an interactive
> run where summary quality matters; for headless/cloud/CI runs, omit `--fulltext`
> — RSS summaries are an acceptable fallback and avoid timeouts.

## Static dashboard (on demand)

```bash
python3 scripts/build_dashboard.py   # → wiki/dashboard.html
```

A simpler echo of the ClimatePulse dashboard (Briefing / Newsroom / Archive,
domain filters) as one self-contained HTML file. Open it, or
`python3 -m http.server` the folder.

## Sources & validation

- **Starter list:** `config/feeds.default.yaml` — ~14 curated, keyless RSS feeds
  across policy/science, energy verticals, transport, and US/EU/AU/Asia, with a
  `core` subset onboarding always keeps so the digest is never empty.
- **Your list:** onboarding writes `config/feeds.yaml`, which takes precedence.
- **Adding a source** (onboarding, a note in `state/feedback.md`, or a skill
  proposal) always passes through the validator first:

  ```bash
  python3 scripts/validate_feeds.py <feed-url>        # test a feed
  python3 scripts/validate_feeds.py --discover <site> # find a site's feed
  python3 scripts/validate_feeds.py --all             # health-check the active list
  ```

  Only `ok`/`stale` feeds get written; `blocked`/`unreachable`/`no-feed-found`
  are reported, not added.

## Email newsletters (optional)

If you have **Gmail connected in Claude**, onboarding can add `type: email`
sources. Their `query` is a Gmail search (`from:(daily@carbonbrief.org)
newer_than:2d` or `label:Newsletters/Climate newer_than:2d`); the skill reads
matching mail via the Gmail tools and `scripts/add_email_items.py` folds them
into the same scoring path as RSS.

Two guarantees: email is treated as **untrusted, read-only data** (the skill
never acts on instructions in an email and never sends/edits mail), and
email-derived items are **private** — local only, never contributed to any
future shared pool. Headless runs without a Gmail connection skip email sources.

## Network note

Feeds need outbound HTTPS to publishers. Two things commonly make *every* feed
return HTTP 403 (`status: blocked`):

1. **Publisher bot-protection** — mitigated by the realistic User-Agent the
   scripts send; some CDNs still block datacenter IPs.
2. **A run-environment network allowlist** — e.g. a sandbox that only permits a
   few hosts.

A **local run** (residential IP) is most permissive. For a **cloud Routine/CI**,
widen the network policy to allow the news domains, or run locally. Sanity-check
with one `validate_feeds.py <known-good-url>` before suspecting the source list.

## Scheduling (pick one)

- **Claude Code Routine (web)** — attach a daily schedule trigger; runs
  unattended on Anthropic infra, survives reboots. Easiest.
- **GitHub Actions** — a `schedule:` workflow running `claude -p "/climate-digest"`,
  committing the wiki. Free managed cron.
- **System cron / launchd** — `claude -p "/climate-digest"` each morning.

`/loop` is *not* suitable — it only runs while a session stays open.

## Self-learning

Four plain files in `state/`:

- `profile.md` — who the digest serves (set at onboarding, evolves with feedback)
- `feedback.md` — drop quick notes here anytime; consumed and cleared each run
- `source_stats.json` — per-source yield history, updated every run
- `learning.md` — append-only reflection journal, read back each run

Conservative tuning is automatic; structural changes (adding/removing sources)
are proposed and confirmed in an interactive run.

## Roadmap

1. **Now** — per-user skill → local Markdown wiki + on-demand dashboard.
2. **Next** — point the same records at a shared, public, **append-only** pool:
   each user contributes their RSS slice, everyone reads free. Schema and dedup
   keys are already pool-ready; email items stay private.
3. **Later** — coordinator + consensus for trustless federated compute.
