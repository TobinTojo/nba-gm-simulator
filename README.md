# Name Rush

A fast basketball initials trivia game. You get **30 seconds** to name an all-time player from their **initials**. Faster answers earn more points.

**Live site:** [namerushball.netlify.app](https://namerushball.netlify.app)

---

## How to Play

1. You see two initials (e.g. **MJ**)
2. Type a player name who matches those initials
3. Answer quickly: points equal seconds remaining (up to **30 pts**)
4. Correct answer: new initials, timer resets
5. Wrong answer, invalid player, or time runs out: game over

### Modes and features

- **Solo:** race the clock; miss once and the run ends
- **Play with friends:** private rooms, era filters, race rounds, rematch
- **Career stats:** games played, accuracy, average points, best score, friendly 1v1 wins (Google sign-in)
- **Leaderboard:** one row per signed-in player with their best solo score
- **Settings:** sound effects on/off and dark/light theme (dedicated page, like Stats)
- Close spellings still count; suffixes like Jr. / III are handled (Otto Porter Jr. = **OP**)
- On game over, see every valid player for each round with career years

### Rules

- **5,100+ all-time basketball players** in the pool
- Shows how many players share each set of initials
- Friend matches: up to 4 players, era filters (60s to 2020s / all-time), 9 / 12 / 15 rounds

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Player data | Bundled JSON (~5,100 players with career seasons) |
| Auth / leaderboard | Supabase (Google OAuth + Postgres) |
| Hosting | Netlify (frontend) + Render (API) |

---

## Local Development

### Prerequisites

- Python 3.12+ (3.14 works with the pinned pydantic version)
- Node.js 20+

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` to the backend on port 8001.

---

## Project Structure

```
nba-gm-simulator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings + CORS
│   │   ├── routers/game.py      # Game API routes
│   │   ├── routers/leaderboard.py
│   │   └── services/
│   │       ├── name_game_service.py  # Game logic, fuzzy match, scoring
│   │       ├── auth_service.py       # Supabase JWT verification
│   │       └── leaderboard_service.py
│   ├── sql/
│   │   ├── leaderboard.sql           # Create leaderboard table
│   │   └── leaderboard_fix_rls.sql   # Fix permissions if writes fail
│   ├── data/
│   │   └── all_time_players.json     # Player pool (required for deploy)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/GamePage.tsx        # Main app shell / modes
│   │   ├── MultiplayerRoom.tsx
│   │   ├── LeaderboardPanel.tsx
│   │   ├── components/               # Landing, Stats, Settings, nav
│   │   ├── context/SettingsContext.tsx
│   │   ├── hooks/useLeaderboardAuth.ts
│   │   └── api/client.ts
│   └── public/_redirects
└── netlify.toml
```

> **Note:** The repo folder is still named `nba-gm-simulator` from an earlier project. The active app is Name Rush only.

---

## Deployment

| Service | Host | Purpose |
|---|---|---|
| Frontend | [Netlify](https://netlify.com) | Static React build |
| Backend | [Render](https://render.com) | FastAPI web service |

### Render (backend)

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

**Environment variables:**

| Key | Required | Value |
|---|---|---|
| `CORS_ORIGINS_EXTRA` | Yes | `https://namerushball.netlify.app` (no trailing slash) |
| `SUPABASE_URL` | For leaderboard | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | For leaderboard | Secret key from Supabase Settings > API Keys (`sb_secret_...`) |
| `LEADERBOARD_DATABASE_URL` | Optional | Postgres URI from Supabase **Connect** (Session pooler) |
| `SUPABASE_JWT_SECRET` | Optional | Only for legacy Supabase projects (new projects use JWKS via `SUPABASE_URL`) |

> **Tip:** Score writes use the Supabase REST API with the service role key. The Postgres URI is optional (fallback for reads/writes).

### Netlify (frontend)

Netlify reads `netlify.toml` automatically:

| Setting | Value |
|---|---|
| Base directory | `frontend` |
| Build command | `npm run build` |
| Publish directory | `dist` |

`VITE_API_URL` is set in `netlify.toml` to point at the Render API.

**Leaderboard env vars** (Netlify > Site configuration > Environment variables):

| Key | Value |
|---|---|
| `VITE_SUPABASE_URL` | `https://<project-ref>.supabase.co` (base URL, no `/rest/v1/`) |
| `VITE_SUPABASE_ANON_KEY` | Publishable key from Supabase Settings > API Keys (`sb_publishable_...`) |

If these are omitted, the game works but the leaderboard UI is hidden.

> **Important:** Vite bakes `VITE_*` vars in at build time. After adding or changing them, use **Clear cache and deploy** on Netlify.

### Online leaderboard setup (Supabase)

#### 1. Create a Supabase project

At [supabase.com](https://supabase.com) > **New project**.

Save your **database password**. You need it for the Postgres connection string.

#### 2. Create the leaderboard table

**SQL Editor > New query**: paste and run `backend/sql/leaderboard.sql`.

If Supabase warns about RLS, choose **Run and enable RLS**, then also run `backend/sql/leaderboard_fix_rls.sql`.

#### 3. Enable Google sign-in

**Authentication > URL Configuration:**

| Field | Value |
|---|---|
| Site URL | `https://namerushball.netlify.app` |
| Redirect URLs | `https://namerushball.netlify.app` |

In [Google Cloud Console](https://console.cloud.google.com):

1. Configure the **OAuth consent screen** (External).
2. **APIs & Services > Credentials > Create OAuth client ID** (Web application).
3. Set:
   - **Authorized JavaScript origins:** `https://namerushball.netlify.app`
   - **Authorized redirect URIs:** `https://<project-ref>.supabase.co/auth/v1/callback`

Then **Authentication > Providers > Google**: enable and paste Client ID and Secret.

#### 4. Copy environment variables

| Copy this | Put it on |
|---|---|
| Project URL | Netlify `VITE_SUPABASE_URL` and Render `SUPABASE_URL` |
| Publishable key | Netlify `VITE_SUPABASE_ANON_KEY` |
| Secret key | Render `SUPABASE_SERVICE_ROLE_KEY` |
| Postgres URI (optional) | Render `LEADERBOARD_DATABASE_URL` |

#### 5. Deploy

1. **Render:** save env vars, then Manual Deploy > Deploy latest commit
2. **Netlify:** save env vars, then Clear cache and deploy

#### How it works

After a solo run, signed-in players can submit scores. Each user appears **once** on the leaderboard with their **highest score only**. Career stats and friendly wins update from play.

#### Troubleshooting

| Symptom | Fix |
|---|---|
| Leaderboard hidden on site | Add Netlify env vars and redeploy with cache cleared |
| DNS error on Google sign-in | Check `VITE_SUPABASE_URL` for typos in the project ref |
| Google sign-in blocked / only you can sign in | OAuth consent is in Testing: add test users or Publish the app |
| 401 on score submit | Add `SUPABASE_URL` on Render and redeploy |
| 500 on score submit | Add `SUPABASE_SERVICE_ROLE_KEY` on Render; run `leaderboard_fix_rls.sql` |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check + player count |
| GET | `/api/game/status` | Game config (timer, player count) |
| POST | `/api/game/start` | Start a round, get first initials |
| POST | `/api/game/guess` | Submit a guess |
| POST | `/api/game/reveal` | Get all players matching initials (game over) |
| GET | `/api/leaderboard?limit=25` | Top scores (optional Bearer token to highlight your row) |
| POST | `/api/leaderboard/submit` | Submit score (Supabase JWT; upserts one row per user) |
| GET | `/api/leaderboard/me` | Career profile for the signed-in user |
| POST | `/api/leaderboard/career` | Update career stats after a run |
| POST | `/api/multiplayer/create` | Create a private room (2 to 4 players, 9 / 12 / 15 rounds) |
| POST | `/api/multiplayer/join` | Join a room by code |
| POST | `/api/multiplayer/rounds` | Host sets round count while waiting |
| POST | `/api/multiplayer/start` | Host starts the match (needs 2+ players) |
| GET | `/api/multiplayer/room/{code}` | Poll room state |
| POST | `/api/multiplayer/guess` | Submit a race guess (first correct wins the round) |

---

## Regenerating Player Data

The all-time player list is bundled in `backend/data/all_time_players.json`. To refresh it:

```powershell
cd backend
.venv\Scripts\activate
pip install nba_api
python scripts/generate_all_time_players.py
```

This requires network access and pulls ~5,100 players with career season spans.

---

## License

MIT
