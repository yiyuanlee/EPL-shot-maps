import argparse
import pandas as pd
from eplshotmaps.plot import plot_shot_map, plot_efficiency_bar, plot_xg_goals_scatter

def main():
    parser = argparse.ArgumentParser(description="Generate EPL shot-efficiency charts from CSV")
    parser.add_argument("--csv", required=True, help="Path to shot-level CSV")
    parser.add_argument("--player", help="Generate shot map for a specific player")
    parser.add_argument("--min-shots", type=int, default=10, help="Minimum shots for efficiency charts")
    parser.add_argument("--outdir", default="out", help="Output directory")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    # Basic sanity
    required = {"player", "team", "minute", "x", "y", "xg", "outcome"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    import os
    os.makedirs(args.outdir, exist_ok=True)

    if args.player:
        plot_shot_map(df, player=args.player, out_path=f"{args.outdir}/shotmap_{args.player.replace(' ', '_')}.png")
    else:
        # Generate shot maps for top 3 volume shooters (example behavior)
        top3 = df.groupby("player").size().sort_values(ascending=False).head(3).index.tolist()
        for p in top3:
            plot_shot_map(df, player=p, out_path=f"{args.outdir}/shotmap_{p.replace(' ', '_')}.png")

    plot_efficiency_bar(df, min_shots=args.min_shots, out_path=f"{args.outdir}/efficiency_bar.png")
    plot_xg_goals_scatter(df, out_path=f"{args.outdir}/xg_goals_scatter.png", min_shots=args.min_shots)

if __name__ == "__main__":
    main()
