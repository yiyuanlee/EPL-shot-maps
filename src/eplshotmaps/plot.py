from typing import Optional, Dict, List
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

# 配色方案（球员对比用）
PLAYER_COLORS = [
    "#E63946",  # 红
    "#457B9D",  # 蓝
    "#2A9D8F",  # 青
    "#E9C46A",  # 黄
    "#9B5DE5",  # 紫
    "#F4A261",  # 橙
    "#06D6A0",  # 绿
    "#EF476F",  # 粉
]


def _half_pitch(ax):
    """画半场球场底线向右攻"""
    ax.set_xlim(0, PITCH_LENGTH/2)
    ax.set_ylim(0, PITCH_WIDTH)
    ax.plot([0, PITCH_LENGTH/2], [0, 0])
    ax.plot([0, PITCH_LENGTH/2], [PITCH_WIDTH, PITCH_WIDTH])
    ax.plot([0, 0], [0, PITCH_WIDTH])
    ax.plot([PITCH_LENGTH/2, PITCH_LENGTH/2], [0, PITCH_WIDTH])
    box_length, box_width = 16.5, 40.32
    box_y1 = (PITCH_WIDTH - box_width)/2
    box_y2 = (PITCH_WIDTH + box_width)/2
    ax.plot([PITCH_LENGTH/2 - box_length, PITCH_LENGTH/2 - box_length], [box_y1, box_y2])
    ax.plot([PITCH_LENGTH/2 - box_length, PITCH_LENGTH/2], [box_y1, box_y1])
    ax.plot([PITCH_LENGTH/2 - box_length, PITCH_LENGTH/2], [box_y2, box_y2])
    six_len, six_w = 5.5, 18.32
    s_y1 = (PITCH_WIDTH - six_w)/2
    s_y2 = (PITCH_WIDTH + six_w)/2
    ax.plot([PITCH_LENGTH/2 - six_len, PITCH_LENGTH/2 - six_len], [s_y1, s_y2])
    ax.plot([PITCH_LENGTH/2 - six_len, PITCH_LENGTH/2], [s_y1, s_y1])
    ax.plot([PITCH_LENGTH/2 - six_len, PITCH_LENGTH/2], [s_y2, s_y2])
    pen_spot_x = PITCH_LENGTH/2 - 11.0
    pen_spot_y = PITCH_WIDTH/2
    ax.scatter([pen_spot_x], [pen_spot_y], s=10)
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')
    return ax


# ─────────────────────────────────────────────
# 单球员图（保持原接口不变）
# ─────────────────────────────────────────────

def plot_shot_map(df: pd.DataFrame, player: str, out_path: Optional[str] = None):
    """射门分布图（单个球员）"""
    pdf = df[df["player"] == player].copy()
    if pdf.empty:
        raise ValueError(f"No shots found for player: {player}")
    pdf["x_half"] = np.where(pdf["x"] > PITCH_LENGTH/2, PITCH_LENGTH - pdf["x"], pdf["x"])

    fig, ax = plt.subplots(figsize=(7, 5))
    _half_pitch(ax)
    marker_map = {"goal": "o", "saved": "s", "blocked": "x", "off_target": "^"}
    for outcome, g in pdf.groupby("outcome"):
        marker = marker_map.get(outcome, "o")
        sizes = 30 + 120 * g["xg"].clip(0, 1).values if "xg" in g.columns else 40
        ax.scatter(g["x_half"], g["y"], marker=marker, s=sizes, alpha=0.8, label=outcome)
    ax.legend(title="Outcome", loc="upper left", bbox_to_anchor=(1.02, 1.0))
    ax.set_title(f"Shot Map - {player}")
    if out_path:
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        plt.close(fig)
    else:
        plt.show()


def plot_efficiency_bar(df: pd.DataFrame, min_shots: int = 10, out_path: Optional[str] = None, top_n: int = 15):
    """效率柱状图（单球员 or 多球员 DataFrame）"""
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
    """xG vs Goals 散点图"""
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


# ─────────────────────────────────────────────
# 多球员对比图（新功能）
# ─────────────────────────────────────────────

def _agg_players(df_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """汇总多个球员的统计数据"""
    rows = []
    for player, df in df_dict.items():
        goals = (df["outcome"] == "goal").sum()
        shots = len(df)
        total_xg = df["xg"].sum()
        rows.append({
            "player": player,
            "shots": shots,
            "goals": goals,
            "total_xg": round(total_xg, 3),
            "conversion": round(goals / shots * 100, 1) if shots > 0 else 0,
            "xg_diff": round(goals - total_xg, 3),  # 实际进球 - xG
        })
    return pd.DataFrame(rows).sort_values("shots", ascending=False)


def plot_comparison_shot_maps(df_dict: Dict[str, pd.DataFrame], out_path: Optional[str] = None):
    """
    多球员射门分布并排对比图（子图排列）。
    每个球员一个子图，所有子图共享坐标轴范围便于对比。
    """
    n = len(df_dict)
    cols = min(n, 3)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
    if n == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]

    marker_map = {"goal": "o", "saved": "s", "blocked": "x", "off_target": "^"}

    for idx, (player, df) in enumerate(df_dict.items()):
        ax = axes[idx // cols][idx % cols]
        _half_pitch(ax)

        pdf = df.copy()
        pdf["x_half"] = np.where(pdf["x"] > PITCH_LENGTH/2, PITCH_LENGTH - pdf["x"], pdf["x"])
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]

        for outcome, g in pdf.groupby("outcome"):
            marker = marker_map.get(outcome, "o")
            sizes = 30 + 120 * g["xg"].clip(0, 1).values if "xg" in g.columns else 40
            ax.scatter(g["x_half"], g["y"], marker=marker, s=sizes, alpha=0.8,
                       color=color, label=outcome)

        ax.set_title(f"{player} ({len(df)} shots)", fontsize=11)
        ax.legend(title="Outcome", loc="upper left", fontsize=7)

    # 隐藏多余的空白子图
    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis("off")

    fig.suptitle("Shot Maps Comparison", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    if out_path:
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        plt.close(fig)
    else:
        plt.show()


def plot_comparison_bar(df_dict: Dict[str, pd.DataFrame], out_path: Optional[str] = None):
    """
    多球员关键指标横向对比柱状图。
    包含：射门数、进球数、转化率、xG差值（4个指标并排）。
    """
    agg = _agg_players(df_dict)
    metrics = ["shots", "goals", "conversion", "xg_diff"]
    titles = ["Total Shots", "Goals", "Conversion (%)", "xG Diff (Goals - xG)"]

    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    colors = [PLAYER_COLORS[i % len(PLAYER_COLORS)] for i in range(len(agg))]

    for ax, metric, title in zip(axes, metrics, titles):
        vals = agg[metric].values
        bars = ax.bar(range(len(agg)), vals, color=colors)
        ax.set_xticks(range(len(agg)))
        ax.set_xticklabels(agg["player"], rotation=45, ha="right", fontsize=9)
        ax.set_title(title, fontsize=11)
        for i, v in enumerate(vals):
            ax.text(i, v + max(vals)*0.01, f"{v:.1f}" if metric == "conversion" else str(int(v)), ha="center", fontsize=8)
        ax.tick_params(axis="y", labelsize=8)

    fig.suptitle("Players Comparison", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    if out_path:
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        plt.close(fig)
    else:
        plt.show()


def plot_comparison_scatter(df_dict: Dict[str, pd.DataFrame], out_path: Optional[str] = None):
    """
    多球员 xG vs Goals 散点图，所有球员同时显示在一张图上。
    """
    fig, ax = plt.subplots(figsize=(6, 5))

    for idx, (player, df) in enumerate(df_dict.items()):
        total_xg = df["xg"].sum()
        goals = (df["outcome"] == "goal").sum()
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
        ax.scatter(total_xg, goals, color=color, s=120, label=player, zorder=3)
        ax.annotate(player, (total_xg, goals), xytext=(6, 4), textcoords="offset points", fontsize=9)

    max_val = max(
        max(df["xg"].sum() for df in df_dict.values()),
        max((df["outcome"] == "goal").sum() for df in df_dict.values())
    ) + 1
    ax.plot([0, max_val], [0, max_val], linestyle="--", color="gray", alpha=0.6, label="y=x")
    ax.set_xlabel("Total xG")
    ax.set_ylabel("Goals")
    ax.set_title("xG vs Goals Comparison")
    ax.set_xlim(0, max_val + 0.5)
    ax.set_ylim(0, max_val + 0.5)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    if out_path:
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        plt.close(fig)
    else:
        plt.show()


def plot_comparison_heatmap(df_dict: Dict[str, pd.DataFrame], out_path: Optional[str] = None):
    """
    射门位置热力图：每个球员的射门密度分布。
    将射门位置分 bins，生成热力图对比。
    """
    n = len(df_dict)
    cols = min(n, 3)
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
    if n == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]

    for idx, (player, df) in enumerate(df_dict.items()):
        ax = axes[idx // cols][idx % cols]

        pdf = df.copy()
        pdf["x_half"] = np.where(pdf["x"] > PITCH_LENGTH/2, PITCH_LENGTH - pdf["x"], pdf["x"])

        # 2D 直方图热力图
        hb = ax.hist2d(pdf["x_half"], pdf["y"], bins=15, cmap="YlOrRd", alpha=0.8)
        plt.colorbar(hb[3], ax=ax, label="Shot Density")
        _half_pitch(ax)
        ax.set_title(f"{player}", fontsize=11)

    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis("off")

    fig.suptitle("Shot Density Heatmaps", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    if out_path:
        fig.savefig(out_path, bbox_inches="tight", dpi=200)
        plt.close(fig)
    else:
        plt.show()