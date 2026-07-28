# NBA Initials — Name Rush

A fast-paced NBA trivia game. You get **30 seconds** to guess an all-time NBA player from their **initials**. Faster answers earn more points.

**Live site:** [nbanamerush.netlify.app](https://nbanamerush.netlify.app)

---

## How to Play

1. You see two initials (e.g. **MJ**)
2. Type a player name who matches those initials
3. Answer quickly — points equal seconds remaining (up to **30 pts**)
4. Correct answer → new initials, timer resets
5. Wrong answer, invalid player, or time runs out → game over

### Rules

- **5,100+ all-time NBA players** in the pool
- Shows how many players share each set of initials
- Close spellings still count (e.g. "Lebron James" → LeBron James)
- Suffixes like Jr., III are handled correctly (Otto Porter Jr. = **OP**)
- On game over, see every valid player for each round with their career span
- **Play a Friend:** private room (Google sign-in required), same 9 initials, 30s per round, first correct answer wins each round

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Player data | Bundled JSON (~5,100 players with career seasons) |
| Leaderboard | Supabase (Google OAuth + Postgres) |
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

API docs: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

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
│   │   ├── pages/GamePage.tsx   # Main game UI
│   │   ├── LeaderboardPanel.tsx
│   │   ├── hooks/useLeaderboardAuth.ts
│   │   └── api/client.ts        # API client
│   └── public/_redirects        # Netlify API proxy fallback
└── netlify.toml                 # Netlify build + deploy config
```

> **Note:** The repo folder is still named `nba-gm-simulator` from an earlier project. The active app is the initials game only.

---

## Deployment

The app is split across two free hosts:

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
| `CORS_ORIGINS_EXTRA` | Yes | `https://your-site.netlify.app` (no trailing slash) |
| `SUPABASE_URL` | For leaderboard | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | For leaderboard | Secret key from Supabase → Settings → API Keys (`sb_secret_...`) |
| `LEADERBOARD_DATABASE_URL` | Optional | Postgres URI from Supabase **Connect** button (Session pooler) |
| `SUPABASE_JWT_SECRET` | Optional | Only needed on legacy Supabase projects (new projects use JWKS via `SUPABASE_URL`) |

> **Tip:** Score writes use the Supabase REST API with the service role key. The Postgres URI is optional (used as a fallback for reads/writes).

### Netlify (frontend)

Netlify reads `netlify.toml` automatically:

| Setting | Value |
|---|---|
| Base directory | `frontend` |
| Build command | `npm run build` |
| Publish directory | `dist` |

`VITE_API_URL` is set in `netlify.toml` to point at the Render API.

**Additional environment variables for the online leaderboard** (Netlify → Site configuration → Environment variables):

| Key | Value |
|---|---|
| `VITE_SUPABASE_URL` | `https://<project-ref>.supabase.co` (base URL, no `/rest/v1/`) |
| `VITE_SUPABASE_ANON_KEY` | Publishable key from Supabase → Settings → API Keys (`sb_publishable_...`) |

If these are omitted, the game works normally but the leaderboard UI is hidden.

> **Important:** Vite bakes `VITE_*` vars in at build time. After adding or changing them, trigger **Clear cache and deploy** on Netlify.

After changing env vars on either host, trigger a **fresh deploy**.

### Online leaderboard setup (Supabase)

#### 1. Create a Supabase project

At [supabase.com](https://supabase.com) → **New project**:

| Setting | Recommendation |
|---|---|
| Connect GitHub | Skip (not needed for player sign-in) |
| Automatically expose new tables | **Uncheck** (safer) |
| Enable automatic RLS | Leave unchecked |

Save your **database password** — you need it for the Postgres connection string.

#### 2. Create the leaderboard table

**SQL Editor → New query** → paste and run `backend/sql/leaderboard.sql`.

If Supabase warns about RLS, choose **Run and enable RLS**, then also run `backend/sql/leaderboard_fix_rls.sql`.

#### 3. Enable Google sign-in

**Authentication → URL Configuration:**

| Field | Value |
|---|---|
| Site URL | `https://nbanamerush.netlify.app` |
| Redirect URLs | `https://nbanamerush.netlify.app` |

In [Google Cloud Console](https://console.cloud.google.com):

1. Create a project and configure the **OAuth consent screen** (External).
2. **APIs & Services → Credentials → Create OAuth client ID** (Web application).
3. Set:
   - **Authorized JavaScript origins:** `https://nbanamerush.netlify.app`
   - **Authorized redirect URIs:** `https://<project-ref>.supabase.co/auth/v1/callback`

Your **project ref** is the subdomain in your Supabase URL (e.g. `https://abc123.supabase.co` → ref is `abc123`).

Then **Authentication → Providers → Google** → Enable → paste Client ID and Secret.

#### 4. Copy environment variables

**Supabase → Settings → API Keys:**

| Copy this | Put it on |
|---|---|
| Project URL (`https://<ref>.supabase.co`) | Netlify → `VITE_SUPABASE_URL` and Render → `SUPABASE_URL` |
| Publishable key (`sb_publishable_...`) | Netlify → `VITE_SUPABASE_ANON_KEY` |
| Secret key (`sb_secret_...`) | Render → `SUPABASE_SERVICE_ROLE_KEY` |

**Supabase → Connect button (top bar) → Direct → Session pooler → URI** (optional):

| Copy this | Put it on |
|---|---|
| Postgres URI (replace `[YOUR-PASSWORD]`) | Render → `LEADERBOARD_DATABASE_URL` |

#### 5. Deploy

1. **Render** — save env vars → Manual Deploy → Deploy latest commit
2. **Netlify** — save env vars → Clear cache and deploy

#### How it works

After game over, players sign in with Google. The score submits automatically. Each user appears **once** on the leaderboard with their **highest score only**.

#### Troubleshooting

| Symptom | Fix |
|---|---|
| Leaderboard hidden on site | Add Netlify env vars and redeploy with cache cleared |
| DNS error on Google sign-in | Check `VITE_SUPABASE_URL` for typos in the project ref |
| Google sign-in blocked / only you can sign in | OAuth consent screen is in Testing — add test users or Publish the app |
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
| GET | `/api/leaderboard?limit=25` | Top scores (optional `Authorization: Bearer` to highlight your row) |
| POST | `/api/leaderboard/submit` | Submit score (requires Supabase JWT; upserts one row per user) |
| POST | `/api/multiplayer/create` | Create a private 1v1 room (9 shared initials, 30s rounds) |
| POST | `/api/multiplayer/join` | Join a room by code |
| GET | `/api/multiplayer/room/{code}` | Poll room state |
| POST | `/api/multiplayer/guess` | Submit a race guess (first correct wins the round) |

---

## Regenerating Player Data

The all-time player list is bundled in `backend/data/all_time_players.json`. To refresh it from the NBA API:

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
