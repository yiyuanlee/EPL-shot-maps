"""
Understat API - 球员名字 → DataFrame

用户只需提供球员名字，自动搜索 ID、获取射门数据、返回标准 DataFrame。

Usage:
    from data.understat_api import fetch_player_shots
    df = fetch_player_shots("Erling Haaland", season=2024)
"""

import re
import time
import random
from typing import List, Optional

import requests
import pandas as pd

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

# ─────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────

def _get(url: str, max_retries: int = 5, sleep: float = 1.0) -> str:
    """用 cloudscraper 抓页面，绕过 Cloudflare"""
    try:
        import cloudscraper
    except ImportError:
        raise ImportError("请先安装 cloudscraper: pip install cloudscraper")

    scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html",
        "Referer": "https://understat.com/",
    }
    last_err = None
    for i in range(max_retries):
        try:
            r = scraper.get(url, headers=headers, timeout=30)
            if r.status_code == 200 and r.text:
                return r.text
        except Exception as e:
            last_err = e
        time.sleep(sleep * (1.5 ** i) + random.uniform(0, 0.5))
    raise RuntimeError(f"GET {url} failed: {last_err}")


def _search_player(name: str) -> Optional[dict]:
    """
    在 Understat 搜索球员，返回第一个匹配的 {id, name, team}
    """
    search_url = f"https://understat.com/player/{name.replace(' ', '%20')}"
    try:
        html = _get(search_url)
    except Exception:
        return None

    # 从 HTML 中提取 player_id 和基本信息
    # Understat 页面有 <a href="/player/{id}">{name}</a>
    patterns = [
        rf'href="/player/(\d+)".*?>{re.escape(name)}<',
        rf'player.*?(\d{{6,}})',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            player_id = m.group(1)
            return {"id": int(player_id), "name": name}
    return None


def _fetch_player_data(player_id: int, season: int = 2024) -> dict:
    """
    获取球员在指定赛季的射门数据 (Understat API 风格)
    """
    url = f"https://understat.com/player/{player_id}"
    html = _get(url)

    # 方法1：找 var datesData = JSON.parse('...');
    json_data = None
    for key in ["datesData", "shotsData"]:
        pat = re.compile(rf"var\s+{key}\s*=\s*JSON\.parse\('(.+?)'\);", re.DOTALL)
        m = pat.search(html)
        if m:
            raw = m.group(1).encode("utf-8").decode("unicode_escape")
            try:
                json_data = __import__("json").loads(raw)
                break
            except Exception:
                pass

    # 方法2：直接从页面提取 NUXT 数据
    if json_data is None:
        nuxt_pat = re.compile(r"window\.__NUXT__\s*=\s*(\{.*?\});", re.DOTALL)
        m = nuxt_pat.search(html)
        if m:
            try:
                nuxt = __import__("json").loads(m.group(1).replace(": undefined", ": null"))
                # 在 nuxt 里找 shots 数组
                def find_shots(obj):
                    if isinstance(obj, dict):
                        if "shotsData" in obj or "datesData" in obj:
                            return obj.get("shotsData") or obj.get("datesData")
                        for v in obj.values():
                            r = find_shots(v)
                            if r is not None:
                                return r
                    elif isinstance(obj, list):
                        for item in obj:
                            r = find_shots(item)
                            if r is not None:
                                return r
                    return None
                json_data = find_shots(nuxt)
            except Exception:
                pass

    if json_data is None:
        raise RuntimeError(f"无法解析球员 {player_id} 的射门数据，页面结构可能已变")

    return json_data


def _normalize_outcome(v: str) -> str:
    v = (v or "").lower().replace(" ", "_")
    return {
        "goal": "goal",
        "saved": "saved",
        "blocked": "blocked",
        "missed": "off_target",
        "shot_on_post": "off_target",
    }.get(v, v or "unknown")


# ─────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────

def fetch_player_shots(player_name: str, season: int = 2024) -> pd.DataFrame:
    """
    输入球员名字，返回该球员在指定赛季的射门 DataFrame。

    列：player, team, minute, x, y, xg, outcome, is_penalty, situation, shotType

    Usage:
        df = fetch_player_shots("Erling Haaland", season=2024)
        print(df.head())
    """
    player_info = _search_player(player_name)
    if player_info is None:
        raise ValueError(f"未找到球员: {player_name}，请检查拼写")

    player_id = player_info["id"]
    raw_data = _fetch_player_data(player_id, season)

    # 标准化处理
    rows = []
    # Understat 可能是 list of dict 或 dict with keys
    shots_list = []
    if isinstance(raw_data, list):
        shots_list = raw_data
    elif isinstance(raw_data, dict):
        # 取所有赛季数据中匹配 season 的
        for year_str, season_data in raw_data.items():
            if str(season) in year_str or str(season - 1) in year_str:
                if isinstance(season_data, list):
                    shots_list.extend(season_data)
                elif isinstance(season_data, dict) and "shots" in season_data:
                    shots_list.extend(season_data["shots"])

    for s in shots_list:
        try:
            x_norm = float(s.get("X", s.get("x", 0)))
            y_norm = float(s.get("Y", s.get("y", 0)))
            x_m = x_norm * PITCH_LENGTH
            y_m = (1.0 - y_norm) * PITCH_WIDTH  # Understat Y 从下往上

            rows.append({
                "player": s.get("player", player_name),
                "team": s.get("team", ""),
                "minute": int(float(s.get("minute", 0))),
                "x": round(x_m, 4),
                "y": round(y_m, 4),
                "xg": float(s.get("xG", s.get("xG_sum", 0))),
                "outcome": _normalize_outcome(s.get("result", "")),
                "is_penalty": bool(int(s.get("isPenalty", 0))) if str(s.get("isPenalty", "0")).isdigit() else False,
                "situation": s.get("situation", ""),
                "shotType": s.get("shotType", ""),
            })
        except Exception:
            continue

    if not rows:
        raise ValueError(f"球员 {player_name} 在 {season} 赛季没有射门数据")

    df = pd.DataFrame(rows)
    return df


def fetch_player_seasons(player_name: str) -> List[dict]:
    """
    返回球员所有有数据的赛季列表。
    """
    player_info = _search_player(player_name)
    if player_info is None:
        raise ValueError(f"未找到球员: {player_name}")

    url = f"https://understat.com/player/{player_info['id']}"
    html = _get(url)

    # 提取所有赛季
    pat = re.compile(r'href="/player/(\d+)#(\d{4})"', re.IGNORECASE)
    matches = pat.findall(html)
    seasons = sorted(set(int(y) for _, y in matches), reverse=True)
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
