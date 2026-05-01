# EPL Shot Maps

A Python tool to generate **Premier League player shot-efficiency visuals** from CSV or directly from [Understat](https://understat.com).

## Features

### Single Player
- Shot map on a half-pitch (goal/saved/blocked/off_target markers)
- Shot conversion rate bar chart
- xG vs. Goals scatter plot

### Multi-Player Comparison (new!)
- **Side-by-side shot maps** for 2-6 players
- **4-metric bar comparison**: shots, goals, conversion rate, xG diff
- **xG vs. Goals scatter** with all players on one chart
- **Shot density heatmaps** per player

## Installation

```bash
git clone https://github.com/yiyuanlee/EPL-shot-maps.git
cd EPL-shot-maps
pip install -r requirements.txt
```

## Quickstart

### From Understat (no CSV needed!)

```bash
# Single player
python scripts/make_charts.py --player "Erling Haaland" --source understat

# Multi-player comparison (up to 6 players)
python scripts/make_charts.py --players "Erling Haaland,Mohamed Salah,Alexander Isak" --source understat

# Specify season (default: 2024)
python scripts/make_charts.py --players "Haaland,Salah" --source understat --season 2024
```

### From CSV

```bash
python scripts/make_charts.py --csv data/sample_shots.csv --player "Erling Haaland"
```

## Output Files

| File | Description |
|------|-------------|
| `out/shotmap_<player>.png` | Single player shot map |
| `out/compare_shotmaps.png` | Multi-player shot maps |
| `out/compare_bar.png` | 4-metric comparison bar chart |
| `out/compare_xg_scatter.png` | xG vs Goals scatter |
| `out/compare_heatmap.png` | Shot density heatmap |
| `out/efficiency_bar.png` | Top converters |
| `out/xg_goals_scatter.png` | xG vs Goals |

## Web Demo

Run a Streamlit web app locally:

```bash
streamlit run web_demo.py
```

Then open http://localhost:8501 — choose **Single Player** or **Multi-Player Comparison** mode.

Deploy to Streamlit Cloud (free): connect your GitHub repo at [share.streamlit.io](https://share.streamlit.io).

## CSV Data Schema

If using your own CSV, it must contain these columns:

| Column | Type | Description |
|--------|------|-------------|
| `player` | str | Player name |
| `team` | str | Team name |
| `minute` | int | Match minute |
| `x` | float | Shot x in meters (0–105) |
| `y` | float | Shot y in meters (0–68) |
| `xg` | float | Expected goals |
| `outcome` | str | `goal`, `saved`, `blocked`, `off_target` |

> Sample data: `data/sample_shots.csv`

## Library Usage

```python
from eplshotmaps.plot import (
    plot_shot_map, plot_efficiency_bar, plot_xg_goals_scatter,
    plot_comparison_shot_maps, plot_comparison_bar,
    plot_comparison_scatter, plot_comparison_heatmap,
)
from data.understat_api import fetch_player_shots, fetch_multi_player_shots
import pandas as pd

# Single player
df = fetch_player_shots("Erling Haaland", season=2024)
plot_shot_map(df, player="Erling Haaland", out_path="out/shotmap.png")

# Multi-player comparison
df_dict = fetch_multi_player_shots(["Haaland", "Salah", "Isak"], season=2024)
plot_comparison_shot_maps(df_dict, out_path="out/compare.png")
plot_comparison_bar(df_dict, out_path="out/compare_bar.png")
```

## API Reference

**`data.understat_api.py`:**
- `fetch_player_shots(name, season)` → DataFrame
- `fetch_multi_player_shots(names_list, season)` → Dict[name, DataFrame]
- `search_player(name)` → (player_id, player_name)

**`src/eplshotmaps/plot.py`:**
- `plot_shot_map(df, player)` — single shot map
- `plot_efficiency_bar(df, min_shots)` — conversion bar chart
- `plot_xg_goals_scatter(df, min_shots)` — xG vs Goals scatter
- `plot_comparison_shot_maps(df_dict)` — multi-player shot maps
- `plot_comparison_bar(df_dict)` — 4-metric comparison
- `plot_comparison_scatter(df_dict)` — xG vs Goals all players
- `plot_comparison_heatmap(df_dict)` — shot density heatmaps

## Tips

- Use a **minimum shots cutoff** (10–20) to reduce noise
- Exclude penalties for comparable conversion rates
- For best comparison, use players from the **same season**

## License

MIT