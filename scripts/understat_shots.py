"""
Fetch Premier League per-shot data (xG + coordinates) from Understat by scraping the
league & match pages. Robust to legacy (matchesData/shotsData) and Nuxt ('window.__NUXT__') formats,
and uses cloudscraper to reduce Cloudflare challenges.

Usage examples:
  python understat_shots.py --season 2024 --limit-matches 3 --out data/shots_last3.csv --debug
  python understat_shots.py --season 2024 --from-round 1 --to-round 10 --out data/shots_r1_10.csv
  python understat_shots.py --season 2024 --out data/shots_2024.csv
"""

import argparse
import json
import re
import time
import random
from typing import Any, Dict, List, Optional

import pandas as pd
from tqdm import tqdm

PITCH_LENGTH = 105.0
PITCH_WIDTH  = 68.0

LEAGUE_URL = "https://understat.com/league/EPL/{season}"
MATCH_URL  = "https://understat.com/match/{match_id}"

# ---------- HTTP (Cloudflare-friendly) ----------
def _get(url: str, debug_path: Optional[str] = None, max_retries: int = 7, sleep: float = 1.4) -> str:
    import cloudscraper
    scraper = cloudscraper.create_scraper(browser={
        "browser": "chrome",
        "platform": "windows",
        "mobile": False
    })
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://understat.com/",
        "Upgrade-Insecure-Requests": "1",
    }
    last_err = None
    for i in range(max_retries):
        try:
            r = scraper.get(url, headers=headers, timeout=35)
            if r.status_code == 200 and r.text:
                text = r.text
                # Heuristic check: real page typically contains these tokens
                if ("__NUXT__" in text) or ("matchesData" in text) or ("shotsData" in text) or ("understat" in text.lower()):
                    if debug_path:
                        with open(debug_path, "w", encoding="utf-8") as f:
                            f.write(text)
                    return text
        except Exception as e:
            last_err = e
        time.sleep(sleep * (1.6 ** i) + random.uniform(0, 0.8))
    if last_err:
        raise RuntimeError(f"Failed to GET {url}: {last_err}")
    raise RuntimeError(f"Failed to GET {url}: blocked or empty response")

# ---------- JSON extractors ----------
def _extract_json_parse_block(html: str, key: str) -> Optional[str]:
    # var key = JSON.parse('...'); (escaped string)
    pat = re.compile(rf"var\s+{re.escape(key)}\s*=\s*JSON\.parse\('(.+?)'\);", re.DOTALL)
    m = pat.search(html)
    if not m:
        return None
    s = m.group(1)
    try:
        s = s.encode("utf-8").decode("unicode_escape")
    except Exception:
        pass
    return s

def _extract_json_literal_block(html: str, key: str) -> Optional[str]:
    # var key = {...};  OR  var key = [...];
    pat = re.compile(rf"var\s+{re.escape(key)}\s*=\s*(\{{.*?\}}|\[.*?\]);", re.DOTALL)
    m = pat.search(html)
    return m.group(1) if m else None

def _extract_nuxt_json(html: str) -> Optional[Dict[str, Any]]:
    # window.__NUXT__ = {...};
    pat = re.compile(r"window\.__NUXT__\s*=\s*(\{.*?\});", re.DOTALL)
    m = pat.search(html)
    if not m:
        return None
    s = m.group(1)
    s = s.replace(": undefined", ": null")
    try:
        return json.loads(s)
    except Exception:
        # relax trailing commas, etc.
        s2 = re.sub(r",\s*}", "}", s)
        s2 = re.sub(r",\s*]", "]", s2)
        try:
            return json.loads(s2)
        except Exception:
            return None

def _deep_find_all(obj: Any, pred) -> List[Any]:
    found = []
    try:
        if pred(obj):
            found.append(obj)
        if isinstance(obj, dict):
            for v in obj.values():
                found.extend(_deep_find_all(v, pred))
        elif isinstance(obj, list):
            for v in obj:
                found.extend(_deep_find_all(v, pred))
    except Exception:
        pass
    return found

def _deep_find_first(obj: Any, pred) -> Optional[Any]:
    res = _deep_find_all(obj, pred)
    return res[0] if res else None

# ---------- Normalizers ----------
def _normalize_outcome(v: str) -> str:
    v = (v or "").lower().replace(" ", "_")
    return {
        "goal":"goal",
        "saved":"saved",
        "blocked":"blocked",
        "missed":"off_target",
        "shot_on_post":"off_target",
    }.get(v, v or "unknown")

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

def _normalize_shots(match_id: int, shots: Dict[str, Any]) -> List[Dict]:
    rows: List[Dict] = []
    for side in ("h", "a"):
        arr = shots.get(side, [])
        if not isinstance(arr, list):
            continue
        for s in arr:
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

# ---------- Fetchers ----------
def fetch_league_matches(season: int, debug: bool=False) -> List[Dict]:
    html = _get(LEAGUE_URL.format(season=season), debug_path=("debug_league.html" if debug else None))

    # 1) legacy matchesData / matches
    for key in ("matchesData", "matches"):
        data_str = _extract_json_parse_block(html, key) or _extract_json_literal_block(html, key)
        if data_str:
            try:
                matches = json.loads(data_str)
                norm = _normalize_matches(matches)
                if norm:
                    return norm
            except Exception:
                pass

    # 2) Nuxt fallback
    nuxt = _extract_nuxt_json(html)
    if nuxt:
        def looks_like_matches(x):
            return (
                isinstance(x, list)
                and len(x) > 0
                and isinstance(x[0], dict)
                and "id" in x[0]
                and any(k in x[0] for k in ("round","round_number","week"))
            )
        matches = _deep_find_first(nuxt, looks_like_matches)
        if matches:
            norm = _normalize_matches(matches)
            if norm:
                return norm

    raise RuntimeError("Cannot find matches JSON on league page (legacy & Nuxt both failed).")

def fetch_match_shots(match_id: int, debug: bool=False) -> List[Dict]:
    html = _get(MATCH_URL.format(match_id=match_id), debug_path=(f"debug_match_{match_id}.html" if debug else None))

    # 1) legacy shotsData
    shots_str = _extract_json_parse_block(html, "shotsData") or _extract_json_literal_block(html, "shotsData")
    if shots_str:
        try:
            shots = json.loads(shots_str)
            rows = _normalize_shots(match_id, shots)
            if rows:
                return rows
        except Exception:
            pass

    # 2) Nuxt fallback
    nuxt = _extract_nuxt_json(html)
    if nuxt:
        def looks_like_shots(x):
            if isinstance(x, dict) and "h" in x and "a" in x:
                return isinstance(x.get("h"), list) and isinstance(x.get("a"), list)
            return False
        shots_obj = _deep_find_first(nuxt, looks_like_shots)
        if shots_obj:
            rows = _normalize_shots(match_id, shots_obj)
            if rows:
                return rows

    raise RuntimeError(f"Cannot find shots JSON for match {match_id} (legacy & Nuxt both failed).")

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Scrape EPL per-shot data (Understat) → CSV (xG + coords)")
    ap.add_argument("--season", type=int, required=True, help="Season start year (e.g., 2024 for 2024/25)")
    ap.add_argument("--out", default=None, help="Output CSV (default data/shots_<season>.csv)")
    ap.add_argument("--limit-matches", type=int, default=None, help="Only fetch the most recent N matches (optional)")
    ap.add_argument("--from-round", type=int, default=None, help="Only matches with round >= this (optional)")
    ap.add_argument("--to-round", type=int, default=None, help="Only matches with round <= this (optional)")
    ap.add_argument("--debug", action="store_true", help="Save league/match HTML for troubleshooting")
    args = ap.parse_args()

    out_path = args.out or f"data/shots_{args.season}.csv"

    matches = fetch_league_matches(args.season, debug=args.debug)

    # round filters
    if args.from_round is not None:
        matches = [m for m in matches if (m["round"] or 0) >= args.from_round]
    if args.to_round is not None:
        matches = [m for m in matches if (m["round"] or 10**9) <= args.to_round]
    # sort + recent tail
    matches.sort(key=lambda m: m.get("date") or "")
    if args.limit_matches:
        matches = matches[-int(args.limit_matches):]

    if not matches:
        raise SystemExit("No matches found after filters. Check season or round range.")

    all_rows: List[Dict] = []
    for m in tqdm(matches, desc=f"EPL {args.season} fetching shots"):
        mid = int(m["id"])
        try:
            rows = fetch_match_shots(mid, debug=args.debug)
            all_rows.extend(rows)
            time.sleep(0.6 + random.uniform(0.0, 0.4))  # polite rate limit
        except Exception as e:
            print(f"[warn] match {mid} skipped: {e}")

    df = pd.DataFrame(all_rows)
    if df.empty:
        raise SystemExit("No shots parsed. Possibly blocked or site changed.")

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
