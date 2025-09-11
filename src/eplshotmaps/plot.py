from typing import Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

def _half_pitch(ax):
    # Draw a simple half-pitch (left to right attack)
    ax.set_xlim(0, PITCH_LENGTH/2)
    ax.set_ylim(0, PITCH_WIDTH)
    # Boundaries
    ax.plot([0, PITCH_LENGTH/2], [0, 0])
    ax.plot([0, PITCH_LENGTH/2], [PITCH_WIDTH, PITCH_WIDTH])
    ax.plot([0, 0], [0, PITCH_WIDTH])
    ax.plot([PITCH_LENGTH/2, PITCH_LENGTH/2], [0, PITCH_WIDTH])
    # Box
    box_length = 16.5
    box_width = 40.32
    box_y1 = (PITCH_WIDTH - box_width)/2
    box_y2 = (PITCH_WIDTH + box_width)/2
    ax.plot([PITCH_LENGTH/2 - box_length, PITCH_LENGTH/2 - box_length], [box_y1, box_y2])
    ax.plot([PITCH_LENGTH/2 - box_length, PITCH_LENGTH/2], [box_y1, box_y1])
    ax.plot([PITCH_LENGTH/2 - box_length, PITCH_LENGTH/2], [box_y2, box_y2])
    # 6-yard box
    six_box_len = 5.5
    six_box_w = 18.32
    s_y1 = (PITCH_WIDTH - six_box_w)/2
    s_y2 = (PITCH_WIDTH + six_box_w)/2
    ax.plot([PITCH_LENGTH/2 - six_box_len, PITCH_LENGTH/2 - six_box_len], [s_y1, s_y2])
    ax.plot([PITCH_LENGTH/2 - six_box_len, PITCH_LENGTH/2], [s_y1, s_y1])
    ax.plot([PITCH_LENGTH/2 - six_box_len, PITCH_LENGTH/2], [s_y2, s_y2])
    # Penalty spot & arc (approximate arc)
    pen_spot_x = PITCH_LENGTH/2 - 11.0
    pen_spot_y = PITCH_WIDTH/2
    ax.scatter([pen_spot_x], [pen_spot_y], s=10)
    # Center line not needed for half
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')
    return ax

def plot_shot_map(df: pd.DataFrame, player: str, out_path: Optional[str] = None):
    """Plot a shot map for a given player on a half-pitch.
    Expects columns: x, y, outcome (goal/saved/blocked/off_target), xg (optional).
    Coordinates should be meters (0–105, 0–68), attacking right.
    """
    pdf = df[df["player"] == player].copy()
    if pdf.empty:
        raise ValueError(f"No shots found for player: {player}")
    # Restrict to attacking towards right half
    # If any x > 52.5, mirror to left half for consistent visualization
    pdf["x_half"] = np.where(pdf["x"] > PITCH_LENGTH/2, PITCH_LENGTH - pdf["x"], pdf["x"])
    pdf["y_half"] = pdf["y"]  # assuming symmetrical width origin already centered

    fig, ax = plt.subplots(figsize=(7, 5))
    _half_pitch(ax)

    # Marker mapping
    marker_map = {
        "goal": "o",
        "saved": "s",
        "blocked": "x",
        "off_target": "^"
    }
    for outcome, g in pdf.groupby("outcome"):
        marker = marker_map.get(outcome, "o")
        sizes = 40
        # Optionally scale by xG if present
        if "xg" in g.columns:
            sizes = 30 + 120 * g["xg"].clip(0, 1).values
        ax.scatter(g["x_half"], g["y_half"], marker=marker, s=sizes, alpha=0.8, label=outcome)

    ax.legend(title="Outcome", loc="upper left", bbox_to_anchor=(1.02, 1.0))
    ax.set_title(f"Shot Map — {player}")
    if out_path:
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        plt.close(fig)
    else:
        plt.show()

def plot_efficiency_bar(df: pd.DataFrame, min_shots: int = 10, out_path: Optional[str] = None, top_n: int = 15):
    """Bar chart of conversion rate by player (goals/shots), filtered by min_shots."""
    agg = (
        df.assign(is_goal=lambda d: d["outcome"].eq("goal").astype(int))
          .groupby("player")
          .agg(shots=("player", "size"), goals=("is_goal", "sum"))
          .reset_index()
    )
    agg = agg[agg["shots"] >= min_shots].copy()
    if agg.empty:
        raise ValueError("No players meet the minimum shots threshold.")
    agg["conversion"] = agg["goals"] / agg["shots"]
    agg = agg.sort_values("conversion", ascending=False).head(top_n)

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(agg["player"], agg["conversion"] * 100.0)
    ax.invert_yaxis()
    ax.set_xlabel("Conversion Rate (%)")
    ax.set_title(f"Top Converters (min shots = {min_shots})")
    for i, v in enumerate(agg["conversion"] * 100.0):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center")
    if out_path:
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        plt.close(fig)
    else:
        plt.show()

def plot_xg_goals_scatter(df: pd.DataFrame, out_path: Optional[str] = None, min_shots: int = 10):
    """Scatter of total xG vs. Goals per player, with a y=x line for calibration."""
    d = df.copy()
    d["is_goal"] = d["outcome"].eq("goal").astype(int)
    agg = d.groupby("player").agg(total_xg=("xg", "sum"), goals=("is_goal", "sum"), shots=("player", "size")).reset_index()
    agg = agg[agg["shots"] >= min_shots].copy()
    if agg.empty:
        raise ValueError("No players meet the minimum shots threshold.")
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(agg["total_xg"], agg["goals"])
    max_val = max(agg["total_xg"].max(), agg["goals"].max()) + 1
    ax.plot([0, max_val], [0, max_val])
    ax.set_xlabel("Total xG")
    ax.set_ylabel("Goals")
    ax.set_title("xG vs Goals (players with sufficient shots)")
    # Label a few standout points
    try:
        top = agg.sort_values("goals", ascending=False).head(8)
        for _, r in top.iterrows():
            ax.annotate(r["player"], (r["total_xg"], r["goals"]), xytext=(5,5), textcoords="offset points")
    except Exception:
        pass
    if out_path:
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        plt.close(fig)
    else:
        plt.show()
