# climatepulse

A self-contained Claude skill that builds a personalised daily climate / energy /
sustainability news digest into a local Markdown wiki — no database, no server.

- **What it does** — pulls your RSS feeds (and optional Gmail newsletters), scores
  and tags each story, and writes a dated morning briefing plus structured
  per-article notes into `wiki/`.
- **First run** — `/climatepulse` runs a one-time onboarding interview to tailor
  your sources; every run after that just produces the day's digest.
- **Install (Claude Code)** — get the folder, then drop it in. Two ways to get it:
  download the ZIP from GitHub (green **Code** button → **Download ZIP**, or a
  Releases asset) and unzip, **or** `git clone`. Put the folder at
  `.claude/skills/climatepulse/` (rename it to `climatepulse` if it unzipped as
  `climatepulse-skill`), then `pip install -r scripts/requirements.txt`. Invoke
  with `/climatepulse`.
- **Runs in Claude Code only.** It fetches live RSS, and the Claude desktop/web app
  runs skills in a sandbox with no outbound internet — so uploading this as a
  desktop-app skill installs but can't fetch. Use the local Claude Code CLI.
- **Extras** — `python3 scripts/build_dashboard.py` renders a simple static
  dashboard (Briefing / Newsroom / Archive); add Gmail newsletters as sources if
  Gmail is connected in Claude.
- **Run it daily** — schedule `claude -p "/climatepulse"` via a Claude Code
  Routine, GitHub Actions, or cron. (Needs outbound internet; if *every* feed
  returns 403 it's a network block — run locally.)

Longer guide: [`docs/GUIDE.md`](docs/GUIDE.md) · Backlog: [`docs/BACKLOG.md`](docs/BACKLOG.md)
