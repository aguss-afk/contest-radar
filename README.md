# Contest Radar

A quiet, chronological calendar of upcoming and live competitive programming contests.

It aggregates upcoming and live contests from Codeforces (including Gym), AtCoder,
CodeChef, LeetCode, HackerRank and HackerEarth, sorts them by start time and
shows them in a single responsive list. Sites are identified by icon and name only,
with no per-site colour coding.

The design follows the spirit of the Quickshell widget rules in
`~/.config/quickshell/DESIGN-RULES.txt`: flat translucent surfaces, no borders,
no shadows, no gradients, Inter typography, pill controls, soft spacing and
motion that only communicates state changes.

## Run locally

No Node.js, npm or third-party Python packages are needed. Python 3.10+ is
enough (the project is developed against Python 3.14).

```bash
cd ~/repos/contest-radar
python3 server.py --open
```

The site opens at <http://127.0.0.1:8787>. The server:

- fetches every source in parallel on startup;
- refreshes in the background every 10 minutes;
- caches the last good result in `data/cache.json`;
- keeps the last known contests for a source that temporarily fails;
- serves the frontend from `docs/` and live data from `/api/contests`.

Useful options:

```bash
python3 server.py --port 9000
python3 server.py --host 0.0.0.0   # reachable from your phone on the LAN
python3 server.py --refresh-seconds 300
```

## GitHub Pages / static hosting

GitHub Pages cannot run the Python server, so the repo also includes a static
snapshot and a refresh workflow:

- `docs/index.html`, `docs/app.css`, `docs/app.js` — the site;
- `docs/data/contests.json` — the last generated snapshot;
- `.github/workflows/update-contests.yml` — regenerates the snapshot every
  15 minutes and commits it.

To publish it:

1. Push this repository to GitHub.
2. Open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select branch `main` and folder `/docs`, then save.

The page will use `data/contests.json` and fall back gracefully when the live
API is not present. Countdowns still tick locally; the underlying data updates
when the workflow commits a new snapshot. GitHub's scheduled workflows can be
delayed, and it may disable schedules for inactive repositories — if that
happens, run the workflow manually or use the local server.

`build.py` can also be used by any other static host:

```bash
python3 build.py
# writes docs/data/contests.json and docs/theme.css
```

## Data sources

| Source | How it is read |
|---|---|
| Codeforces | Official `contest.list` API, regular and Gym |
| AtCoder | `atcoder.jp/contests` upcoming table |
| CodeChef | Site's `api/list/contests/all` endpoint |
| LeetCode | Public `upcomingContests` GraphQL query |
| HackerRank | `rest/contests/upcoming` endpoint |
| HackerEarth | `chrome-extension/events` endpoint, hackathons excluded |

AtCoder, CodeChef, HackerRank and HackerEarth do not have stable official
public APIs. Their adapters are intentionally small and isolated, so a markup
or endpoint change only affects one source. The footer shows per-source health;
if one fails, its rows stay available from cache when possible.

Topcoder is not included because its old upcoming-events endpoint now returns
`410 Gone`. Codeforces Gym placeholders with multi-year windows are filtered out.

## Keyboard

- `/` — focus search
- `R` — refresh
- `T` — toggle light/dark theme
- `Esc` — clear search / leave the search box

Filters and theme choice are stored in `localStorage`.

## Theme

`theme.py` reads `~/.config/quickshell/Colors.qml` and writes
`docs/theme.css`. It derives the opposite light/dark palette from the same
hues, so the site stays consistent with the current Matugen wallpaper palette.
If `Colors.qml` is unavailable (for example on a CI runner), the existing
generated theme is preserved.

To refresh the theme manually after changing your wallpaper:

```bash
python3 theme.py
```

## Project layout

```text
contest-radar/
├── server.py              # local HTTP server + background refresh
├── build.py               # static snapshot builder
├── theme.py               # Matugen Colors.qml → docs/theme.css
├── cache.py               # atomic JSON cache and failed-source fallback
├── model.py               # normalized Contest model
├── sources/               # one adapter per site
├── docs/                  # publishable static site
│   ├── index.html
│   ├── app.css
│   ├── app.js
│   ├── theme.css
│   ├── fonts/InterVariable.ttf
│   └── data/contests.json
└── .github/workflows/update-contests.yml
```

## Notes

- Times are stored as UTC epochs and rendered in the browser's local timezone.
- The default bind address is `127.0.0.1`; use `--host 0.0.0.0` only on a
  trusted network.
- `data/cache.json` and Python bytecode are ignored by git.
