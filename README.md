# climate-digest

A self-contained Claude skill that builds a personalised daily climate / energy /
sustainability news digest into a local Markdown wiki — no database, no server.

- **What it does** — pulls your RSS feeds (and optional Gmail newsletters), scores
  and tags each story, and writes a dated morning briefing plus structured
  per-article notes into `wiki/`.
- **First run** — `/climate-digest` runs a one-time onboarding interview to tailor
  your sources; every run after that just produces the day's digest.
- **Install** — copy this repo into your Claude project as
  `.claude/skills/climate-digest/` (clone, submodule, or symlink), then
  `pip install -r scripts/requirements.txt`. Invoke with `/climate-digest` in
  Claude Code.
- **Extras** — `python3 scripts/build_dashboard.py` renders a simple static
  dashboard (Briefing / Newsroom / Archive); add Gmail newsletters as sources if
  Gmail is connected in Claude.
- **Run it daily** — schedule `claude -p "/climate-digest"` via a Claude Code
  Routine, GitHub Actions, or cron. (Needs outbound internet; if *every* feed
  returns 403 it's a network block — run locally.)

Longer guide: [`docs/GUIDE.md`](docs/GUIDE.md) · Backlog: [`docs/BACKLOG.md`](docs/BACKLOG.md)
