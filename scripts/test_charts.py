"""
Test script for GitHub Actions CI
Runs a quick chart generation to verify the pipeline doesn't break.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.understat_api import fetch_player_shots, fetch_multi_player_shots
from eplshotmaps.plot import plot_shot_map
import tempfile

print("Testing fetch_player_shots...")
df = fetch_player_shots("Erling Haaland", season=2024)
assert len(df) > 0, "No shots returned"
print(f"  Got {len(df)} shots for Haaland")

print("Testing fetch_multi_player_shots...")
df_dict = fetch_multi_player_shots(["Mohamed Salah", "Alexander Isak"], season=2024)
assert len(df_dict) == 2, "Multi-player fetch failed"
print(f"  Got shots for: {list(df_dict.keys())}")

print("Testing plot_shot_map...")
with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
    tmp_path = tmp.name

try:
    plot_shot_map(df, player="Erling Haaland", out_path=tmp_path)
    assert os.path.exists(tmp_path), "Plot file not created"
    assert os.path.getsize(tmp_path) > 10000, "Plot file too small"
    print(f"  Generated plot: {tmp_path}")
    print("ALL TESTS PASSED")
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
