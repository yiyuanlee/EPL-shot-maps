"""
Understat API — Player shot data from Understat.com
with local caching (24h TTL)

Usage:
    from data.understat_api import fetch_player_shots, fetch_multi_player_shots, search_player
    df = fetch_player_shots("Erling Haaland", season=2024)
    df_dict = fetch_multi_player_shots(["Haaland", "Salah", "Isak"], season=2024)
"""

import os
import json
import hashlib
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

# ── Cache setup ───────────────────────────────────────────────
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
_CACHE_TTL_HOURS = 24


def _cache_path(player_name: str, season: int) -> str:
    key = hashlib.md5(f"{player_name}_{season}".encode()).hexdigest()[:12]
    return os.path.join(_CACHE_DIR, f"shots_{key}_{season}.json")


def _cache_valid(path: str) -> bool:
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    return (datetime.now(timezone.utc) - mtime).total_seconds() < _CACHE_TTL_HOURS * 3600


def _save_cache(df: pd.DataFrame, player_name: str, season: int) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    df.to_json(_cache_path(player_name, season), orient="records", indent=2, date_format="iso")


def _load_cache(player_name: str, season: int) -> Optional[pd.DataFrame]:
    path = _cache_path(player_name, season)
    if not _cache_valid(path):
        return None
    try:
        return pd.read_json(path)
    except Exception:
        return None


# ── Player search ───────────────────────────────────────────────

def search_player(player_name: str, league: str = "EPL", season: str = "2024") -> Optional[Tuple[str, str]]:
    """
    Search for a player by partial name. Returns (player_id, player_name).
    Uses all available seasons as fallback so partial names work even if the player
    has no shots in the requested season.
    """
    from understatapi import UnderstatClient

    with UnderstatClient() as understat:
        players = understat.league(league=league).get_player_data(season=season)
        q = player_name.lower()
        # exact match first, then partial
        exact, partial = None, None
        for p in players:
            full = p.get("player_name", "")
            if q == full.lower():
                exact = (str(p["id"]), full)
                break
            if q in full.lower():
                partial = (str(p["id"]), full)
        if exact:
            return exact
        if partial:
            return partial
    return None


def get_all_players(league: str = "EPL", season: str = "2024") -> list:
    """Return a list of all player names in a league/season. Used for autocomplete."""
    from understatapi import UnderstatClient

    with UnderstatClient() as understat:
        players = understat.league(league=league).get_player_data(season=season)
        return [p["player_name"] for p in players]


# ── Core fetch ────────────────────────────────────────────────

def _fetch_single_player_shots(player_name: str, season: int) -> pd.DataFrame:
    """
    Internal: fetch + cache a single player's shots. Returns a DataFrame.
    """
    # Try cache first
    cached = _load_cache(player_name, season)
    if cached is not None and not cached.empty:
        return cached

    from understatapi import UnderstatClient

    season_str = str(season)

    with UnderstatClient() as understat:
        players = understat.league(league="EPL").get_player_data(season=season_str)
        player_id, found_name = None, player_name

        q = player_name.lower()
        for p in players:
            if q in p.get("player_name", "").lower():
                player_id = str(p["id"])
                found_name = p["player_name"]
                break

        if player_id is None:
            raise ValueError(f"Player not found: {player_name}. Check spelling (use English name).")

        all_shots = understat.player(player=player_id).get_shot_data()

    shots = [s for s in all_shots if str(s.get("season")) == season_str]
    if not shots:
        shots = all_shots

    rows = []
    for s in shots:
        try:
            x_m = float(s.get("X", 0)) * PITCH_LENGTH
            y_m = (1.0 - float(s.get("Y", 0))) * PITCH_WIDTH
            result = (s.get("result") or "").lower()
            outcome_map = {
                "goal": "goal", "saved": "saved", "blocked": "blocked",
                "missed": "off_target", "shot on post": "off_target",
            }
            outcome = outcome_map.get(result, result or "unknown")
            rows.append({
                "player": found_name,
                "team": s.get("h_team") if s.get("h_a") == "h" else s.get("a_team"),
                "minute": int(s.get("minute", 0) or 0),
                "x": round(x_m, 4),
                "y": round(y_m, 4),
                "xg": float(s.get("xG", 0) or 0),
                "outcome": outcome,
                "is_penalty": s.get("situation") == "Penalty",
                "situation": s.get("situation", ""),
                "shotType": s.get("shotType", ""),
            })
        except Exception:
            continue

    if not rows:
        raise ValueError(f"No shots for {found_name} in {season}/{season+1} season.")

    df = pd.DataFrame(rows)
    _save_cache(df, player_name, season)
    return df


def fetch_player_shots(player_name: str, season: int = 2024) -> pd.DataFrame:
    """
    Get shot data for one player. Columns: player, team, minute, x, y, xg,
    outcome, is_penalty, situation, shotType.
    """
    return _fetch_single_player_shots(player_name, season)


def fetch_multi_player_shots(player_names: list, season: int = 2024) -> Dict[str, pd.DataFrame]:
    """
    Batch-fetch shots for multiple players. Returns {name: DataFrame}.

    Usage:
        df_dict = fetch_multi_player_shots(["Haaland", "Salah", "Isak"], season=2024)
    """
    result = {}
    for name in player_names:
        df = _fetch_single_player_shots(name, season)
        result[name] = df
        print(f"[Understat] {name}: {len(df)} shots (cached: {_load_cache(name, season) is not None})")
    return result


def clear_cache(player_name: str = None, season: int = None) -> None:
    """Clear all cache, or a specific player/season."""
    if player_name and season:
        path = _cache_path(player_name, season)
        if os.path.exists(path):
            os.remove(path)
            print(f"Cache cleared: {path}")
    else:
        if os.path.exists(_CACHE_DIR):
            for f in os.listdir(_CACHE_DIR):
                if f.startswith("shots_"):
                    os.remove(os.path.join(_CACHE_DIR, f))
            print("All cache cleared.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python understat_api.py 'Player Name' [season]")
        sys.exit(1)
    name = sys.argv[1]
    season = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
    print(f"Fetching {name} ({season}/{season+1})...")
    df = fetch_player_shots(name, season=season)
    print(f"Got {len(df)} shots")
    print(df.head())
