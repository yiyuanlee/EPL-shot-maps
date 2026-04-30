"""
Understat API — 使用 understatAPI 库获取球员射门数据

Usage:
    from data.understat_api import fetch_player_shots, search_player
    df = fetch_player_shots("Erling Haaland", season=2024)
"""

from typing import Optional, Tuple

import pandas as pd

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0


def search_player(player_name: str, league: str = "EPL", season: str = "2024") -> Optional[Tuple[str, str]]:
    """
    搜索球员，返回 (player_id, player_name)。
    需要 league 和 season 来定位球员列表。
    """
    from understatapi import UnderstatClient

    with UnderstatClient() as understat:
        players = understat.league(league=league).get_player_data(season=season)
        q = player_name.lower()
        for p in players:
            if q in p.get("player_name", "").lower():
                return str(p["id"]), p["player_name"]
    return None


def fetch_player_shots(player_name: str, season: int = 2024) -> pd.DataFrame:
    """
    输入球员名字（英文），自动搜索 + 获取射门数据，返回标准 DataFrame。

    列：player, team, minute, x, y, xg, outcome, is_penalty, situation, shotType

    Usage:
        df = fetch_player_shots("Erling Haaland", season=2024)
    """
    from understatapi import UnderstatClient

    season_str = str(season)

    with UnderstatClient() as understat:
        # 1. 在 league 球员列表中搜索
        players = understat.league(league="EPL").get_player_data(season=season_str)
        player_id = None
        found_name = player_name

        q = player_name.lower()
        for p in players:
            if q in p.get("player_name", "").lower():
                player_id = str(p["id"])
                found_name = p["player_name"]
                break

        if player_id is None:
            raise ValueError(f"未找到球员: {player_name}，请检查拼写（使用英文名）")

        # 2. 获取射门数据（所有赛季）
        all_shots = understat.player(player=player_id).get_shot_data()

    # 3. 过滤指定赛季
    shots = [s for s in all_shots if str(s.get("season")) == season_str]
    if not shots:
        shots = all_shots  # 向前兼容

    # 4. 标准化为 DataFrame
    rows = []
    for s in shots:
        try:
            x_norm = float(s.get("X", 0))
            y_norm = float(s.get("Y", 0))
            x_m = x_norm * PITCH_LENGTH
            y_m = (1.0 - y_norm) * PITCH_WIDTH

            result = (s.get("result") or "").lower()
            outcome_map = {
                "goal": "goal",
                "saved": "saved",
                "blocked": "blocked",
                "missed": "off_target",
                "shot on post": "off_target",
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
                "is_penalty": False,
                "situation": s.get("situation", ""),
                "shotType": s.get("shotType", ""),
            })
        except Exception:
            continue

    if not rows:
        raise ValueError(f"球员 {found_name} 在 {season} 赛季没有射门数据")

    return pd.DataFrame(rows)


def fetch_player_seasons(player_name: str, league: str = "EPL") -> list:
    """返回球员所有可用赛季列表。"""
    from understatapi import UnderstatClient

    with UnderstatClient() as understat:
        players = understat.league(league=league).get_player_data(season="2024")
        q = player_name.lower()
        player_id = None
        for p in players:
            if q in p.get("player_name", "").lower():
                player_id = str(p["id"])
                break

        if player_id is None:
            raise ValueError(f"未找到球员: {player_name}")

        all_data = understat.player(player=player_id).get_shot_data()
        seasons = sorted(set(str(s.get("season", "")) for s in all_data if s.get("season")), reverse=True)
        return [{"season": s} for s in seasons]


# ─────────────────────────────────────────────
# 快捷测试
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python understat_api.py 'Player Name' [season]")
        sys.exit(1)

    name = sys.argv[1]
    season = int(sys.argv[2]) if len(sys.argv) > 2 else 2024

    print(f"正在获取 {name} ({season}/{season+1}) 的数据...")
    df = fetch_player_shots(name, season=season)
    print(f"共 {len(df)} 脚射门")
    print(df.head())
