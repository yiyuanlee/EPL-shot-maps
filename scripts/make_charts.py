"""
Generate EPL shot-efficiency charts.

Supports two modes:
  1. CSV mode  : --csv data/sample_shots.csv --player "Haaland"
  2. Understat mode: --player "Haaland" --source understat [--season 2024]

Usage:
  # From CSV
  python scripts/make_charts.py --csv data/shots.csv --player "Erling Haaland"

  # From Understat (auto-fetch)
  python scripts/make_charts.py --player "Erling Haaland" --source understat
  python scripts/make_charts.py --player "Erling Haaland" --source understat --season 2024
  python scripts/make_charts.py --csv data/shots.csv --min-shots 10
"""

import argparse
import os
import sys

# 确保 src 和 data 在路径里
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "src"))
from eplshotmaps.plot import plot_shot_map, plot_efficiency_bar, plot_xg_goals_scatter


def main():
    parser = argparse.ArgumentParser(description="Generate EPL shot-efficiency charts")
    parser.add_argument("--csv", help="Path to shot-level CSV (CSV mode)")
    parser.add_argument("--player", help="Player name to generate shot map for")
    parser.add_argument("--min-shots", type=int, default=10, help="Minimum shots for efficiency charts")
    parser.add_argument("--outdir", default="out", help="Output directory")
    parser.add_argument(
        "--source",
        choices=["csv", "understat"],
        default="csv",
        help="Data source: csv (default) or understat (auto-fetch)",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2024,
        help="Season start year (e.g. 2024 for 2024/25), used only with --source understat",
    )
    args = parser.parse_args()

    import pandas as pd

    # ── Understat 模式 ─────────────────────────────
    if args.source == "understat":
        if not args.player:
            raise SystemExit("Error: --player is required when using --source understat")

        print(f"[Understat] 正在获取 {args.player} ({args.season}/{args.season+1}) 的数据...")
        from data.understat_api import fetch_player_shots

        df = fetch_player_shots(args.player, season=args.season)
        print(f"[Understat] 获取到 {len(df)} 脚射门")

    # ── CSV 模式 ──────────────────────────────────
    else:
        if not args.csv:
            raise SystemExit("Error: --csv is required when using --source csv")
        df = pd.read_csv(args.csv)

    # 校验列
    required = {"player", "team", "minute", "x", "y", "xg", "outcome"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    os.makedirs(args.outdir, exist_ok=True)

    # ── 射门图 ────────────────────────────────────
    if args.player:
        safe_name = args.player.replace(" ", "_")
        out_path = f"{args.outdir}/shotmap_{safe_name}.png"
        print(f"[Chart] 射门图 → {out_path}")
        plot_shot_map(df, player=args.player, out_path=out_path)
    else:
        # 生成 top 3 射门图
        top3 = df.groupby("player").size().sort_values(ascending=False).head(3).index.tolist()
        for p in top3:
            safe_name = p.replace(" ", "_")
            out_path = f"{args.outdir}/shotmap_{safe_name}.png"
            plot_shot_map(df, player=p, out_path=out_path)
            print(f"[Chart] 射门图 ({p}) → {out_path}")

    # ── 效率柱状图 ────────────────────────────────
    bar_path = f"{args.outdir}/efficiency_bar.png"
    print(f"[Chart] 效率图 → {bar_path}")
    plot_efficiency_bar(df, min_shots=args.min_shots, out_path=bar_path)

    # ── xG 散点图 ─────────────────────────────────
    scatter_path = f"{args.outdir}/xg_goals_scatter.png"
    print(f"[Chart] xG散点图 → {scatter_path}")
    plot_xg_goals_scatter(df, out_path=scatter_path, min_shots=args.min_shots)

    print(f"\n✅ 完成！图片保存在 {args.outdir}/")


if __name__ == "__main__":
    main()
