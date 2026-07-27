"""Playoff bracket generation and series simulation."""

from __future__ import annotations

import json
import random

from sqlalchemy.orm import Session

from app.models import CareerSave, SeasonResult, Team
from app.schemas import PlayoffBracket, PlayoffSeriesResult, PlayoffSimResponse
from app.services.news_service import log_news
from app.services.simulation_service import _simulate_score, _team_strength
from app.services.standings_service import get_standings


ROUNDS = ["First Round", "Conference Semifinals", "Conference Finals", "Finals"]


def _load_bracket(career: CareerSave) -> dict | None:
    if not career.save_data:
        return None
    try:
        data = json.loads(career.save_data)
        return data.get("playoff_bracket")
    except json.JSONDecodeError:
        return None


def _save_bracket(db: Session, career: CareerSave, bracket: dict) -> None:
    data = json.loads(career.save_data) if career.save_data else {}
    data["playoff_bracket"] = bracket
    career.save_data = json.dumps(data)
    db.commit()


def generate_playoff_bracket(db: Session, career: CareerSave) -> PlayoffBracket:
    standings = get_standings(db, career.season, career.id)
    east = standings.east[:10]
    west = standings.west[:10]

    if len(east) < 10 or len(west) < 10:
        raise ValueError("Not enough teams for playoffs")

    def resolve_play_in(conf_teams: list) -> list:
        """Seeds 7-10 play-in; return final top 8 team ids."""
        top6 = [t.team_id for t in conf_teams[:6]]
        s7, s8, s9, s10 = [t.team_id for t in conf_teams[6:10]]

        # 7 vs 8 — winner is 7 seed
        w78, _ = _sim_series(db, s7, s8, best_of=1)
        # 9 vs 10 — loser eliminated; winner plays loser of 7/8 for 8 seed
        w910, _ = _sim_series(db, s9, s10, best_of=1)
        loser78 = s8 if w78 == s7 else s7
        w8, _ = _sim_series(db, loser78, w910, best_of=1)

        return top6 + [w78, w8]

    east8 = resolve_play_in(east)
    west8 = resolve_play_in(west)

    def seed_matchups(team_ids: list[int]):
        return [
            (team_ids[0], team_ids[7]),
            (team_ids[1], team_ids[6]),
            (team_ids[2], team_ids[5]),
            (team_ids[3], team_ids[4]),
        ]

    bracket = {
        "play_in_east": [{"teams": [t.team_id for t in east[6:10]]}],
        "play_in_west": [{"teams": [t.team_id for t in west[6:10]]}],
        "east_r1": [{"high": h, "low": l, "winner": None, "games": []} for h, l in seed_matchups(east8)],
        "west_r1": [{"high": h, "low": l, "winner": None, "games": []} for h, l in seed_matchups(west8)],
        "east_r2": [],
        "west_r2": [],
        "east_cf": [],
        "west_cf": [],
        "finals": [],
        "champion_id": None,
    }

    _save_bracket(db, career, bracket)
    career.phase = "playoffs"
    db.commit()

    return _bracket_to_schema(db, bracket, career.season)


def _sim_series(db: Session, team_a_id: int, team_b_id: int, best_of: int = 7) -> tuple[int, list[tuple[int, int]]]:
    wins_a = 0
    wins_b = 0
    games: list[tuple[int, int]] = []
    needed = best_of // 2 + 1

    while wins_a < needed and wins_b < needed:
        home_a = (wins_a + wins_b) % 2 == 0
        if home_a:
            home_str = _team_strength(db, team_a_id)
            away_str = _team_strength(db, team_b_id)
        else:
            home_str = _team_strength(db, team_b_id)
            away_str = _team_strength(db, team_a_id)

        home_score, away_score = _simulate_score(home_str, away_str)
        if home_a:
            games.append((home_score, away_score))
            if home_score > away_score:
                wins_a += 1
            else:
                wins_b += 1
        else:
            games.append((away_score, home_score))
            if away_score > home_score:
                wins_a += 1
            else:
                wins_b += 1

    winner = team_a_id if wins_a > wins_b else team_b_id
    return winner, games


def _team_label(db: Session, team_id: int) -> str:
    t = db.query(Team).filter(Team.id == team_id).first()
    return f"{t.city} {t.name}" if t else f"Team {team_id}"


def simulate_playoff_round(db: Session, career: CareerSave) -> PlayoffSimResponse:
    bracket = _load_bracket(db, career)
    if not bracket:
        bracket_data = generate_playoff_bracket(db, career)
        bracket = _load_bracket(db, career)

    series_results: list[PlayoffSeriesResult] = []
    current_round = "First Round"

    for conf_key in ("east_r1", "west_r1", "east_r2", "west_r2", "east_cf", "west_cf"):
        series_list = bracket.get(conf_key, [])
        for series in series_list:
            if series.get("winner"):
                continue
            high, low = series["high"], series["low"]
            winner, games = _sim_series(db, high, low)
            series["winner"] = winner
            series["games"] = games
            series_results.append(
                PlayoffSeriesResult(
                    round_name=current_round,
                    team_a=_team_label(db, high),
                    team_b=_team_label(db, low),
                    winner=_team_label(db, winner),
                    score=f"{sum(1 for g in games if (g[0] > g[1] and winner == high) or (g[1] > g[0] and winner == low))}-"
                    f"{len(games) - sum(1 for g in games if (g[0] > g[1] and winner == high) or (g[1] > g[0] and winner == low))}",
                    games_played=len(games),
                )
            )
            log_news(
                db,
                career.season,
                "playoffs",
                f"PLAYOFFS: {_team_label(db, winner)} defeats "
                f"{_team_label(db, low if winner == high else high)}",
                career_id=career.id,
            )

    # Advance winners to next round
    for conf, r1_key, r2_key in [("east", "east_r1", "east_r2"), ("west", "west_r1", "west_r2")]:
        r1 = bracket.get(r1_key, [])
        winners = [s["winner"] for s in r1 if s.get("winner")]
        if len(winners) == 4 and not bracket.get(r2_key):
            bracket[r2_key] = [
                {"high": winners[0], "low": winners[3], "winner": None, "games": []},
                {"high": winners[1], "low": winners[2], "winner": None, "games": []},
            ]

    for conf_key in ("east_r2", "west_r2"):
        if all(s.get("winner") for s in bracket.get(conf_key, [])) and conf_key == "east_r2":
            winners = [s["winner"] for s in bracket["east_r2"]]
            if len(winners) == 2 and not bracket.get("east_cf"):
                bracket["east_cf"] = [{"high": winners[0], "low": winners[1], "winner": None, "games": []}]
        if all(s.get("winner") for s in bracket.get(conf_key, [])) and conf_key == "west_r2":
            winners = [s["winner"] for s in bracket["west_r2"]]
            if len(winners) == 2 and not bracket.get("west_cf"):
                bracket["west_cf"] = [{"high": winners[0], "low": winners[1], "winner": None, "games": []}]

    # Conference finals
    for cf_key in ("east_cf", "west_cf"):
        for series in bracket.get(cf_key, []):
            if series.get("winner"):
                continue
            if series.get("high") and series.get("low"):
                current_round = "Conference Finals"
                winner, games = _sim_series(db, series["high"], series["low"])
                series["winner"] = winner
                series["games"] = games

    east_champ = bracket.get("east_cf", [{}])[0].get("winner") if bracket.get("east_cf") else None
    west_champ = bracket.get("west_cf", [{}])[0].get("winner") if bracket.get("west_cf") else None

    if east_champ and west_champ and not bracket.get("finals"):
        bracket["finals"] = [{"high": east_champ, "low": west_champ, "winner": None, "games": []}]

    champion = None
    for series in bracket.get("finals", []):
        if series.get("winner"):
            champion = series["winner"]
            break
        if series.get("high") and series.get("low"):
            current_round = "Finals"
            winner, games = _sim_series(db, series["high"], series["low"])
            series["winner"] = winner
            series["games"] = games
            bracket["champion_id"] = winner
            champion = winner
            log_news(
                db,
                career.season,
                "playoffs",
                f"CHAMPION: {_team_label(db, winner)} win the {career.season} NBA Championship!",
                career_id=career.id,
            )
            from app.services.owner_service import on_playoff_result

            user_made = any(
                s.get("high") == career.team_id or s.get("low") == career.team_id
                for key in bracket
                for s in bracket.get(key, [])
                if isinstance(s, dict)
            )
            on_playoff_result(db, career, made_playoffs=user_made, won_title=winner == career.team_id)
            from app.services.awards_service import compute_season_awards

            compute_season_awards(db, career)

    _save_bracket(db, career, bracket)

    # Record season results
    if champion:
        career.phase = "offseason"
        for team in db.query(Team).all():
            from app.services.career_state_service import get_record

            wins, losses = get_record(db, career.id, team.id)
            result = db.query(SeasonResult).filter(
                SeasonResult.season == career.season,
                SeasonResult.team_id == team.id,
                SeasonResult.career_id == career.id,
            ).first()
            if not result:
                result = SeasonResult(
                    season=career.season,
                    team_id=team.id,
                    career_id=career.id,
                )
                db.add(result)
            result.wins = wins
            result.losses = losses
            result.made_playoffs = wins >= 35
        db.commit()

    return PlayoffSimResponse(
        round_name=current_round,
        series_results=series_results,
        champion_id=champion,
        champion_name=_team_label(db, champion) if champion else None,
        bracket=_bracket_to_schema(db, bracket, career.season),
    )


def _bracket_to_schema(db: Session, bracket: dict, season: str) -> PlayoffBracket:
    return PlayoffBracket(
        season=season,
        east_r1=_series_list(db, bracket.get("east_r1", [])),
        west_r1=_series_list(db, bracket.get("west_r1", [])),
        champion_id=bracket.get("champion_id"),
        champion_name=_team_label(db, bracket["champion_id"]) if bracket.get("champion_id") else None,
    )


def _series_list(db: Session, series_list: list) -> list[dict]:
    result = []
    for s in series_list:
        result.append({
            "team_a": _team_label(db, s["high"]),
            "team_b": _team_label(db, s["low"]),
            "winner": _team_label(db, s["winner"]) if s.get("winner") else None,
        })
    return result


def get_playoff_bracket(db: Session, career: CareerSave) -> PlayoffBracket:
    bracket = _load_bracket(db, career)
    if not bracket:
        return generate_playoff_bracket(db, career)
    return _bracket_to_schema(db, bracket, career.season)
