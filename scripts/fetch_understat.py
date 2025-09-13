"""
Fetch Premier League shot-level data (with xG & coords) from Understat by scraping
league & match pages. Robust to both legacy (matchesData/shotsData) and Nuxt ('window.__NUXT__') pages.

Usage:
  python scripts/fetch_understat.py --season 2024 --from-round 1 --to-round 10 --out data/shots_r1_10.csv
  python scripts/fetch_understat.py --season 2024 --limit-matches 10 --out data/shots_last10.csv
"""

import argparse
import json
import re
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from tqdm import tqdm

PITCH_LENGTH = 105.0
PITCH_WIDTH  = 68.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

LEAGUE_URL = "https://understat.com/league/EPL/{season}"
MATCH_URL  = "https://understat.com/match/{match_id}"

# ---------- HTTP with retry ----------
# ---------- HTTP with retry (Cloudflare-friendly) ----------
def _get(url: str, max_retries: int = 6, sleep: float = 1.5) -> str:
    import cloudscraper, random
    last_err = None
    # 伪装成常见浏览器，并携带基本 header
    scraper = cloudscraper.create_scraper(browser={
        "browser": "chrome",
        "platform": "windows",
        "mobile": False
    })
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://understat.com/",
    }
    for i in range(max_retries):
        try:
            r = scraper.get(url, headers=headers, timeout=30)
            if r.status_code == 200 and r.text and "understat" in r.text.lower():
                return r.text
        except Exception as e:
            last_err = e
        # 指数退避 + 随机抖动，避免触发限流
        import time
        time.sleep(sleep * (1.6 ** i) + random.uniform(0, 0.75))
    if last_err:
        raise RuntimeError(f"Failed to GET {url}: {last_err}")
    raise RuntimeError(f"Failed to GET {url}: blocked or empty response")

# ---------- HTML JSON extractors ----------
def _extract_json_parse_block(html: str, key: str) -> Optional[str]:
    """
    Find: var <key> = JSON.parse('...');  (escaped string)
    """
    pat = re.compile(rf"var\s+{re.escape(key)}\s*=\s*JSON\.parse\('(.+?)'\);", re.DOTALL)
    m = pat.search(html)
    if not m:
        return None
    s = m.group(1)
    # Unescape \uXXXX and escaped quotes
    s = s.encode("utf-8").decode("unicode_escape")
    return s

def _extract_json_literal_block(html: str, key: str) -> Optional[str]:
    """
    Find: var <key> = {...}; OR [...];
    """
    pat = re.compile(rf"var\s+{re.escape(key)}\s*=\s*(\{{.*?\}}|\[.*?\]);", re.DOTALL)
    m = pat.search(html)
    return m.group(1) if m else None

def _extract_nuxt_json(html: str) -> Optional[Dict[str, Any]]:
    """
    Find: window.__NUXT__ = {...};
    """
    pat = re.compile(r"window\.__NUXT__\s*=\s*(\{.*?\});", re.DOTALL)
    m = pat.search(html)
    if not m:
        return None
    s = m.group(1)
    # Some pages may contain 'undefined' or single-quoted strings; try to sanitize
    s = s.replace(": undefined", ": null")
    try:
        return json.loads(s)
    except Exception:
        # crude fixes for trailing commas etc.
        s2 = re.sub(r",\s*}", "}", s)
        s2 = re.sub(r",\s*]", "]", s2)
        try:
            return json.loads(s2)
        except Exception:
            return None

def _deep_find_first(obj: Any, pred) -> Optional[Any]:
    """
    Recursively search nested dict/list, return first value where pred(value) is True.
    """
    try:
        if pred(obj):
            return obj
        if isinstance(obj, dict):
            for v in obj.values():
                res = _deep_find_first(v, pred)
                if res is not None:
                    return res
        elif isinstance(obj, list):
            for v in obj:
                res = _deep_find_first(v, pred)
                if res is not None:
                    return res
    except Exception:
        pass
    return None

# ---------- Normalization ----------
def _normalize_outcome(v: str) -> str:
    v = (v or "").lower().replace(" ", "_")
    return {
        "goal":"goal",
        "saved":"saved",
        "blocked":"blocked",
        "missed":"off_target",
        "shot_on_post":"off_target",
    }.get(v, v or "unknown")

# ---------- Fetch league matches ----------
def fetch_league_matches(season: int) -> List[Dict]:
    """
    Return list of {id, round, date} for league season.
    Tries legacy (matchesData) then falls back to window.__NUXT__.
    """
    html = _get(LEAGUE_URL.format(season=season))

    # 1) Legacy blocks
    data_str = _extract_json_parse_block(html, "matchesData") or _extract_json_literal_block(html, "matchesData")
    if not data_str:
        data_str = _extract_json_parse_block(html, "matches") or _extract_json_literal_block(html, "matches")
    if data_str:
        try:
            matches = json.loads(data_str)
            return _normalize_matches(matches)
        except Exception:
            pass

    # 2) Nuxt fallback
    nuxt = _extract_nuxt_json(html)
    if nuxt:
        # Look for an array of dicts with at least 'id' and any round-like field
        def looks_like_matches(x):
            return (
                isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict)
                and "id" in x[0] and any(k in x[0] for k in ("round","round_number","week"))
            )
        matches = _deep_find_first(nuxt, looks_like_matches)
        if matches:
            return _normalize_matches(matches)

    raise RuntimeError("Cannot find matches JSON on league page (legacy & Nuxt both failed).")

def _normalize_matches(matches: List[Dict]) -> List[Dict]:
    out = []
    for m in matches:
        try:
            mid = int(m.get("id"))
        except Exception:
            continue
        rnd_raw = m.get("round") or m.get("round_number") or m.get("week")
        try:
            rnd = int(rnd_raw) if rnd_raw is not None else None
        except Exception:
            rnd = None
        date = m.get("datetime") or m.get("date") or ""
        out.append({"id": mid, "round": rnd, "date": date})
    return out

# ---------- Fetch match shots ----------
def fetch_match_shots(match_id: int) -> List[Dict]:
    """
    Return shot events for a given match_id.
    Tries legacy (shotsData) then Nuxt.
    """
    html = _get(MATCH_URL.format(match_id=match_id))

    # 1) Legacy block
    shots_str = _extract_json_parse_block(html, "shotsData") or _extract_json_literal_block(html, "shotsData")
    if shots_str:
        try:
            shots = json.loads(shots_str)
            return _normalize_shots(match_id, shots)
        except Exception:
            pass

    # 2) Nuxt fallback
    nuxt = _extract_nuxt_json(html)
    if nuxt:
        # We expect an object with keys 'h' and 'a', both lists
        def looks_like_shots(x):
            if isinstance(x, dict) and "h" in x and "a" in x:
                try:
                    return isinstance(x["h"], list) and isinstance(x["a"], list)
                except Exception:
                    return False
            return False
        shots = _deep_find_first(nuxt, looks_like_shots)
        if shots:
            return _normalize_shots(match_id, shots)

    raise RuntimeError(f"Cannot find shots JSON for match {match_id} (legacy & Nuxt both failed).")

def _normalize_shots(match_id: int, shots: Dict[str, Any]) -> List[Dict]:
    rows: List[Dict] = []
    for side in ("h", "a"):
        for s in shots.get(side, []):
            try:
                x_norm = float(s.get("x", 0.0))
                y_norm = float(s.get("y", 0.0))
                x_m = x_norm * PITCH_LENGTH
                y_m = (1.0 - y_norm) * PITCH_WIDTH

                rows.append({
                    "match_id": match_id,
                    "date": s.get("date") or "",
                    "player": s.get("player") or "",
                    "team": s.get("team") or "",
                    "minute": int(float(s.get("minute", 0))),
                    "x": round(x_m, 4),
                    "y": round(y_m, 4),
                    "xg": float(s.get("xG", 0.0)),
                    "outcome": _normalize_outcome(s.get("result")),
                    "is_penalty": bool(int(s.get("isPenalty", 0))) if str(s.get("isPenalty", "0")).isdigit() else False,
                    "player_id": int(s["player_id"]) if str(s.get("player_id", "")).isdigit() else None,
                    "h_a": s.get("h_a") or "",
                    "situation": s.get("situation") or "",
                    "shotType": s.get("shotType") or "",
                    "assisted_by": s.get("player_assisted") or "",
                    "lastAction": s.get("lastAction") or "",
                })
            except Exception:
                continue
    return rows

# ---------- Main pipeline ----------
def main():
    ap = argparse.ArgumentParser(description="Scrape EPL shot data from Understat into CSV (robust)")
    ap.add_argument("--season", type=int, required=True, help="赛季开始年（如 2024 表示 2024/25）")
    ap.add_argument("--out", default=None, help="输出 CSV（默认 data/shots_<season>.csv）")
    ap.add_argument("--limit-matches", type=int, default=None, help="仅抓最近 N 场（可选）")
    ap.add_argument("--from-round", type=int, default=None, help="起始轮（可选）")
    ap.add_argument("--to-round", type=int, default=None, help="结束轮（可选）")
    args = ap.parse_args()

    out_path = args.out or f"data/shots_{args.season}.csv"

    matches = fetch_league_matches(args.season)

    # 轮次过滤
    if args.from_round is not None:
        matches = [m for m in matches if (m["round"] or 0) >= args.from_round]
    if args.to_round is not None:
        matches = [m for m in matches if (m["round"] or 10**9) <= args.to_round]

    # 排序 + 最近 N 场
    matches.sort(key=lambda m: m.get("date") or "")
    if args.limit_matches:
        matches = matches[-int(args.limit_matches):]

    if not matches:
        raise SystemExit("No matches found after filters. Check season or round range.")

    all_rows: List[Dict] = []
    for m in tqdm(matches, desc=f"EPL {args.season} fetching shots"):
        mid = int(m["id"])
        try:
            rows = fetch_match_shots(mid)
            all_rows.extend(rows)
            time.sleep(0.6)  # 减速，礼貌访问
        except Exception as e:
            print(f"[warn] match {mid} skipped: {e}")

    df = pd.DataFrame(all_rows)
    if df.empty:
        raise SystemExit("No shots parsed. Site may have changed or blocked requests.")

    # 统一列顺序
    cols = [
        "match_id","date","player","team","minute",
        "x","y","xg","outcome","is_penalty",
        "player_id","h_a","situation","shotType","assisted_by","lastAction",
    ]
    df = df[[c for c in cols if c in df.columns]]

    import os
    os.makedirs("data", exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")

if __name__ == "__main__":
    main()
