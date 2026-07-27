"""Generate backend/data/all_time_players.json from nba_api."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUT_PATH = BACKEND_DIR / "data" / "all_time_players.json"


def season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def main() -> int:
    try:
        from nba_api.stats.endpoints import commonallplayers
        from nba_api.stats.static import players
    except ImportError:
        print("Install nba_api first: pip install nba_api", file=sys.stderr)
        return 1

    career_df = commonallplayers.CommonAllPlayers(
        is_only_current_season=0,
        season="2025-26",
        timeout=60,
    ).get_data_frames()[0]
    careers = {
        int(row["PERSON_ID"]): (int(row["FROM_YEAR"]), int(row["TO_YEAR"]))
        for _, row in career_df.iterrows()
    }

    records = []
    for player in players.get_players():
        first = (player.get("first_name") or "").strip()
        last = (player.get("last_name") or "").strip()
        if not first or not last:
            continue
        nba_id = int(player["id"])
        record = {
            "nba_id": nba_id,
            "first_name": first,
            "last_name": last,
            "full_name": player.get("full_name") or f"{first} {last}",
            "is_active": bool(player.get("is_active")),
        }
        if nba_id in careers:
            from_year, to_year = careers[nba_id]
            record["from_year"] = from_year
            record["to_year"] = to_year
            record["from_season"] = season_label(from_year)
            record["to_season"] = season_label(to_year)
        records.append(record)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    active = sum(1 for row in records if row["is_active"])
    with_careers = sum(1 for row in records if "from_season" in row)
    print(f"Wrote {len(records)} players to {OUT_PATH} ({active} active, {with_careers} with careers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
