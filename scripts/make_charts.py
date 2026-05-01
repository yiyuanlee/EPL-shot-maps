"""
Generate EPL shot-efficiency charts.

Supports:
  1. Single player:   --player "Haaland" --source understat
  2. Multi player:    --players "Haaland,Salah,Isak" --source understat
  3. CSV mode:        --csv data/sample_shots.csv --player "Haaland"

Usage:
  # Single player
  python scripts/make_charts.py --player "Erling Haaland" --source understat --season 2024

  # Multi player comparison
  python scripts/make_charts.py --players "Erling Haaland,Mohamed Salah,Alexander Isak" --source understat --season 2024
"""

import argparse
import os
import sys

# 确保 src 和 data 在路径里
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "src"))

from eplshotmaps.plot import (
    plot_shot_map, plot_efficiency_bar, plot_xg_goals_scatter,
    plot_comparison_shot_maps, plot_comparison_bar,
    plot_comparison_scatter, plot_comparison_heatmap,
)


def main():
    parser = argparse.ArgumentParser(description="Generate EPL shot-efficiency charts")
    parser.add_argument("--csv", help="Path to shot-level CSV (CSV mode, single player only)")
    parser.add_argument("--player", help="Single player name")
    parser.add_argument("--players", help="Comma-separated multi-player names (comparison mode)")
    parser.add_argument("--min-shots", type=int, default=10, help="Minimum shots for efficiency charts")
    parser.add_argument("--outdir", default="out", help="Output directory")
    parser.add_argument(
        "--source", choices=["csv", "understat"], default="csv",
        help="Data source: csv or understat (auto-fetch)",
    )
    parser.add_argument(
        "--season", type=int, default=2024,
        help="Season start year (e.g. 2024 for 2024/25)",
    )
    args = parser.parse_args()

    import pandas as pd
    os.makedirs(args.outdir, exist_ok=True)

    # ── 多球员对比模式 ─────────────────────────────
    if args.players:
        player_list = [p.strip() for p in args.players.split(",")]
        print(f"[Understat] 正在批量获取 {len(player_list)} 位球员数据...")

        from data.understat_api import fetch_multi_player_shots
        df_dict = fetch_multi_player_shots(player_list, season=args.season)

        # 对比图 1：并排射门图
        compare_shotmap_path = f"{args.outdir}/compare_shotmaps.png"
        print(f"[Chart] 射门对比图 → {compare_shotmap_path}")
        plot_comparison_shot_maps(df_dict, out_path=compare_shotmap_path)

        # 对比图 2：4项指标柱状图
        compare_bar_path = f"{args.outdir}/compare_bar.png"
        print(f"[Chart] 指标对比图 → {compare_bar_path}")
        plot_comparison_bar(df_dict, out_path=compare_bar_path)

        # 对比图 3：xG vs Goals
        compare_scatter_path = f"{args.outdir}/compare_xg_scatter.png"
        print(f"[Chart] xG对比图 → {compare_scatter_path}")
        plot_comparison_scatter(df_dict, out_path=compare_scatter_path)

        # 对比图 4：热力图
        compare_heatmap_path = f"{args.outdir}/compare_heatmap.png"
        print(f"[Chart] 热力图 → {compare_heatmap_path}")
        plot_comparison_heatmap(df_dict, out_path=compare_heatmap_path)

        print(f"\nDone! {len(player_list)} players comparison charts saved to {args.outdir}/")
        return

    # ── 单球员模式 ────────────────────────────────
    if not args.player and args.source == "csv":
        raise SystemExit("Error: --player is required for CSV mode")

    if args.source == "understat":
        from data.understat_api import fetch_player_shots
        df = fetch_player_shots(args.player, season=args.season)
        print(f"[Understat] 获取到 {len(df)} 脚射门")
    else:
        if not args.csv:
            raise SystemExit("Error: --csv is required for CSV mode")
        df = pd.read_csv(args.csv)

    required = {"player", "team", "minute", "x", "y", "xg", "outcome"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    safe_name = args.player.replace(" ", "_")
    out_path = f"{args.outdir}/shotmap_{safe_name}.png"
    print(f"[Chart] 射门图 → {out_path}")
    plot_shot_map(df, player=args.player, out_path=out_path)

    bar_path = f"{args.outdir}/efficiency_bar.png"
    print(f"[Chart] 效率图 → {bar_path}")
    plot_efficiency_bar(df, min_shots=args.min_shots, out_path=bar_path)

    scatter_path = f"{args.outdir}/xg_goals_scatter.png"
    print(f"[Chart] xG散点图 → {scatter_path}")
    plot_xg_goals_scatter(df, out_path=scatter_path, min_shots=args.min_shots)

    print(f"\n✅ 完成！图片保存在 {args.outdir}/")


if __name__ == "__main__":
    main()