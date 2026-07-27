# NBA GM Simulator

A local full-stack NBA General Manager simulator.

**Phase 4** adds per-career league state, AI trade inbox, contract extensions, season awards, play-in tournament, and owner job security.

## How to Run

```bash
# Backend
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Phase 4 Features

### Per-Career League State
- Win/loss records stored in `CareerTeamState` — each save slot has its own standings
- News feed filtered by `career_id`
- Loading a career restores that save's league records

### AI Trade Inbox (`/trades`)
- Incoming trade offers from AI teams
- Trade rumors in news feed
- Accept or decline offers from inbox

### Contract Extensions (`/cap-sheet`)
- View expiring contracts
- Negotiate extensions with player acceptance logic
- Player/team options processed in offseason

### Season Awards (`/awards`)
- MVP, Defensive Player of the Year, All-NBA teams
- Computed at championship / offseason
- Stored per career

### Play-In Tournament (`/playoffs`)
- Seeds 7–10 compete before Round 1
- Best-of-1 play-in games determine final 7/8 seeds

### Job Security (Team Hub)
- Meter tracks owner satisfaction (0–100%)
- Updates on wins/losses, playoff results, expectations
- Status labels: Secure, Stable, On Notice, Hot Seat, Critical

## New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/career/status` | Job security + owner expectations |
| GET | `/api/trades/inbox` | Pending AI trade offers |
| POST | `/api/trades/inbox/{id}/respond` | Accept/decline offer |
| GET | `/api/contracts/expiring` | Expiring contracts |
| POST | `/api/contracts/extend` | Extend a player contract |
| GET | `/api/awards` | Season awards for active career |

## Architecture Decisions

1. **CareerTeamState table** — Isolates W-L per save without duplicating entire rosters
2. **TradeOffer model** — Persistent inbox with JSON asset lists
3. **career_id on Transaction/Award/SeasonResult** — Scoped news and history
4. **Play-in before bracket** — Resolves seeds 7/8 before traditional Round 1
5. **Job security on CareerSave** — GM meta-progression tied to owner expectations

## Full Season Loop

```
Regular Season → Trade Deadline → Play-In → Playoffs → Awards
→ Offseason (options, extensions, FA) → Draft → Next Season
```

## What to Build Next (Phase 5)

- Full roster snapshot isolation per career
- AI-initiated extension demands
- Play-in best-of-3 format
- All-Defensive / All-Rookie teams
- GM firing / new job offers
- Historical stats hall of fame

## License

MIT
