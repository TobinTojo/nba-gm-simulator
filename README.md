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

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Player data | Bundled JSON (~5,100 players with career seasons) |
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
│   │   └── services/
│   │       └── name_game_service.py  # Game logic, fuzzy match, scoring
│   ├── data/
│   │   └── all_time_players.json     # Player pool (required for deploy)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/GamePage.tsx   # Main game UI
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

| Key | Value |
|---|---|
| `CORS_ORIGINS_EXTRA` | `https://your-site.netlify.app` (no trailing slash) |
| `LEADERBOARD_DATABASE_URL` | Supabase Postgres connection string (optional; enables leaderboard) |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret from Project Settings → API (required with leaderboard) |

### Netlify (frontend)

Netlify reads `netlify.toml` automatically:

| Setting | Value |
|---|---|
| Base directory | `frontend` |
| Build command | `npm run build` |
| Publish directory | `dist` |

`VITE_API_URL` is set in `netlify.toml` to point at the Render API.

**Additional environment variables for the online leaderboard** (set in Netlify → Site configuration → Environment variables):

| Key | Value |
|---|---|
| `VITE_SUPABASE_URL` | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon/public key |

If these are omitted, the game works normally but the leaderboard UI is hidden.

After changing env vars on either host, trigger a **fresh deploy** (clear cache on Netlify).

### Online leaderboard setup (Supabase)

1. Create a free [Supabase](https://supabase.com) project.
2. In **Authentication → Providers**, enable **GitHub** and add your OAuth app callback URL (`https://<project-ref>.supabase.co/auth/v1/callback`).
3. In **SQL Editor**, run the migration in `backend/sql/leaderboard.sql` (creates one row per user, keeps highest score only).
4. Copy from **Project Settings → API**:
   - Project URL → `VITE_SUPABASE_URL` (Netlify)
   - anon public key → `VITE_SUPABASE_ANON_KEY` (Netlify)
   - JWT Secret → `SUPABASE_JWT_SECRET` (Render)
5. Copy from **Project Settings → Database** the Postgres connection string (URI mode) → `LEADERBOARD_DATABASE_URL` (Render).
6. Redeploy Netlify and Render.

**How it works:** After game over, players sign in with GitHub. The score is submitted automatically. Each user appears once on the leaderboard with their personal best.

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
