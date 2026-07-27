"""Generate bundled salary snapshot from ESPN + current NBA rosters."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.contract_data_service import (
    BUNDLED_SALARIES_PATH,
    build_bundled_salary_file,
    fetch_espn_contract_lookup,
    ContractLookup,
    _load_bundled_salaries,
)
from app.services.seed_service import fetch_roster_data


def main() -> None:
    players, roster_source = fetch_roster_data()
    by_name = fetch_espn_contract_lookup()
    lookup = ContractLookup(by_name=by_name, by_nba_id={}, source="espn.com")
    salaries = build_bundled_salary_file(players, lookup)

    BUNDLED_SALARIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    BUNDLED_SALARIES_PATH.write_text(json.dumps(salaries, indent=2), encoding="utf-8")

    matched = sum(1 for p in players if str(p["nba_id"]) in salaries)
    print(f"Wrote {len(salaries)} salaries to {BUNDLED_SALARIES_PATH}")
    print(f"Roster source: {roster_source} ({len(players)} players, {matched} matched)")


if __name__ == "__main__":
    main()
