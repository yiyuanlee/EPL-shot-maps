# EPL Shot Maps

A tiny open-source project to generate **Premier League player shot-efficiency visuals** from a tidy CSV.

## ✅ Features (MVP)
- Shot map per player on a half-pitch
- Player **shot conversion** (goals / shots) bar chart with a minimum-shots filter
- **xG vs. Goals** scatter for quick efficiency sense-checks

> BYO data: You can use any shot-level CSV with the columns listed below (sample included).

## 📦 Installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 🗂️ Data schema (CSV columns)
- `player` (str): Player name
- `team` (str): Team name
- `minute` (int): Match minute of the shot
- `x` (float): Shot x location in meters (0–105), left to right
- `y` (float): Shot y location in meters (0–68), bottom to top
- `xg` (float): Expected goals value for the shot
- `outcome` (str): One of `goal`, `saved`, `blocked`, `off_target`, etc.

> Coordinates follow a 105m x 68m pitch. If your provider uses 0–1 or different origins, rescale/flip before use.

## 🚀 Quickstart (using sample data)
Generate all charts into `out/` with the included sample data:
```bash
python scripts/make_charts.py --csv data/sample_shots.csv --min-shots 10
```

Or generate for a single player:
```bash
python scripts/make_charts.py --csv data/sample_shots.csv --player "Erling Haaland"
```

Outputs:
- `out/shotmap_<player>.png`
- `out/efficiency_bar.png` (top converters with >= min-shots)
- `out/xg_goals_scatter.png`

## 🔧 Library usage
```python
from eplshotmaps.plot import plot_shot_map, plot_efficiency_bar, plot_xg_goals_scatter
import pandas as pd

df = pd.read_csv("data/sample_shots.csv")
plot_shot_map(df, player="Mohamed Salah", out_path="out/salah_shotmap.png")
plot_efficiency_bar(df, min_shots=15, out_path="out/efficiency_bar.png")
plot_xg_goals_scatter(df, out_path="out/xg_goals_scatter.png")
```

## 🧪 CSV tips
- Aggregate only **open-play + set-piece shots**; exclude penalties if you want comparable conversion.
- Use a **minimum shots** cutoff (10–20) to reduce noise.
- For providers without xG, you can compute simple proxies (distance/angle bins), but xG is preferred.

## 🤝 Contributing
- Issues/PRs welcome! Please keep functions small and tested.
- Style: black + isort (optional).

## 📝 License
MIT
