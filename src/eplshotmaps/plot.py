from typing import Optional, Dict, List
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import rcParams

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

# 配色方案
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

# 射门结果样式
OUTCOME_STYLE = {
    "goal":       {"marker": "o", "color": "#2ECC71", "size_base": 80,  "label": "Goal"},
    "saved":      {"marker": "s", "color": "#E74C3C", "size_base": 55,  "label": "Saved"},
    "blocked":    {"marker": "X", "color": "#F39C12", "size_base": 50,  "label": "Blocked"},
    "off_target": {"marker": "^", "color": "#95A5A6", "size_base": 45,  "label": "Off Target"},
}

# 预设高质量样式
plt.style.use("default")
rcParams["font.family"] = "DejaVu Sans"
rcParams["font.size"] = 11
rcParams["axes.titlesize"] = 14
rcParams["axes.labelsize"] = 11
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
rcParams["axes.grid"] = False
rcParams["figure.dpi"] = 150
rcParams["savefig.dpi"] = 300
rcParams["savefig.bbox"] = "tight"
rcParams["savefig.pad_inches"] = 0.05
rcParams["axes.titleweight"] = "bold"
rcParams["axes.labelweight"] = "normal"


def _half_pitch(ax, grid_alpha=0.3, line_width=1.2):
    """画高质量半场球场"""
    ax.set_xlim(0, PITCH_LENGTH/2)
    ax.set_ylim(0, PITCH_WIDTH)
    # 边界
    for (x0, x1), (y0, y1) in [[(0, PITCH_LENGTH/2), (0, 0)],
                                ((0, PITCH_LENGTH/2), (PITCH_WIDTH, PITCH_WIDTH))]:
        ax.plot([x0, x1], [y0, y1], color="white", lw=line_width*1.5, zorder=1)
    ax.plot([0, 0], [0, PITCH_WIDTH], color="white", lw=line_width*1.5, zorder=1)
    ax.plot([PITCH_LENGTH/2, PITCH_LENGTH/2], [0, PITCH_WIDTH], color="white", lw=line_width*1.5, zorder=1)
    # 禁区
    box_l, box_w = 16.5, 40.32
    by1, by2 = (PITCH_WIDTH - box_w)/2, (PITCH_WIDTH + box_w)/2
    ax.plot([PITCH_LENGTH/2 - box_l, PITCH_LENGTH/2 - box_l], [by1, by2],
            color="white", lw=line_width, alpha=grid_alpha*1.5, zorder=1)
    for y in [by1, by2]:
        ax.plot([PITCH_LENGTH/2 - box_l, PITCH_LENGTH/2], [y, y],
                color="white", lw=line_width, alpha=grid_alpha*1.5, zorder=1)
    # 小禁区
    six_l, six_w = 5.5, 18.32
    sy1, sy2 = (PITCH_WIDTH - six_w)/2, (PITCH_WIDTH + six_w)/2
    ax.plot([PITCH_LENGTH/2 - six_l, PITCH_LENGTH/2 - six_l], [sy1, sy2],
            color="white", lw=line_width, alpha=grid_alpha*1.2, zorder=1)
    for y in [sy1, sy2]:
        ax.plot([PITCH_LENGTH/2 - six_l, PITCH_LENGTH/2], [y, y],
                color="white", lw=line_width, alpha=grid_alpha*1.2, zorder=1)
    # 发球点
    pen_x = PITCH_LENGTH/2 - 11.0
    ax.scatter([pen_x], [PITCH_WIDTH/2], s=15, color="white", alpha=grid_alpha, zorder=1)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_facecolor("#1a1a2e")  # 深蓝黑背景


def _shot_marker(df, col="xg"):
    """计算射门点大小和边框：进球 > xG高 > 普通"""
    sizes = []
    for _, row in df.iterrows():
        base = OUTCOME_STYLE.get(row["outcome"], {}).get("size_base", 50)
        xg_boost = (row[col] if col in df.columns else 0) * 120
        size = base + xg_boost
        sizes.append(size)
    return np.array(sizes)


# ─────────────────────────────────────────────
# 单球员图
# ─────────────────────────────────────────────

def plot_shot_map(df: pd.DataFrame, player: str, out_path: Optional[str] = None,
                  dpi: int = 300, bg_color: str = "#1a1a2e"):
    """高质量射门分布图"""
    pdf = df[df["player"] == player].copy()
    if pdf.empty:
        raise ValueError(f"No shots found for player: {player}")

    pdf["x_half"] = np.where(pdf["x"] > PITCH_LENGTH/2, PITCH_LENGTH - pdf["x"], pdf["x"])

    fig, ax = plt.subplots(figsize=(8, 5.5), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    _half_pitch(ax, grid_alpha=0.25)

    for outcome in ["goal", "saved", "blocked", "off_target"]:
        g = pdf[pdf["outcome"] == outcome]
        if g.empty:
            continue
        style = OUTCOME_STYLE.get(outcome, {})
        sizes = _shot_marker(g)
        scatter = ax.scatter(
            g["x_half"], g["y"],
            marker=style["marker"],
            s=sizes,
            color=style["color"],
            edgecolors="white",
            linewidths=0.8,
            alpha=0.9,
            label=style["label"],
            zorder=5,
        )
        # 进球队列加外发光
        if outcome == "goal":
            scatter.set_path_effects([
                pe.Stroke(linewidth=2, foreground="#ffffff33"),
                pe.Normal(),
            ])

    # 统计信息
    shots = len(pdf)
    goals = (pdf["outcome"] == "goal").sum()
    total_xg = pdf["xg"].sum()
    stats_text = f"Shots: {shots}  |  Goals: {goals}  |  xG: {total_xg:.2f}"
    fig.text(0.5, 0.01, stats_text, ha="center", fontsize=9,
             color="white", alpha=0.6, style="italic")

    ax.legend(title="Outcome", loc="upper left", bbox_to_anchor=(1.02, 1.0),
              fontsize=9, facecolor=bg_color, edgecolor="white", labelcolor="white",
              title_fontsize=9)
    ax.set_title(f"Shot Map - {player}", color="white", pad=12, fontsize=15, fontweight="bold")

    if out_path:
        fig.savefig(out_path, dpi=dpi, facecolor=bg_color, pad_inches=0.1)
        plt.close(fig)
    else:
        plt.show()


def plot_efficiency_bar(df: pd.DataFrame, min_shots: int = 10, out_path: Optional[str] = None,
                        top_n: int = 15, dpi: int = 300):
    """高质量效率柱状图"""
    agg = (
        df.assign(is_goal=lambda d: d["outcome"].eq("goal").astype(int))
          .groupby("player")
          .agg(shots=("player", "size"), goals=("is_goal", "sum"))
          .reset_index()
    )
    agg = agg[agg["shots"] >= min_shots].copy()
    if agg.empty:
        raise ValueError("No players meet the minimum shots threshold.")
    agg["conversion"] = agg["goals"] / agg["shots"] * 100
    agg = agg.sort_values("conversion", ascending=False).head(top_n)

    bg = "#ffffff"
    fig, ax = plt.subplots(figsize=(9, 6), facecolor=bg)
    ax.set_facecolor(bg)

    bars = ax.barh(agg["player"], agg["conversion"], color="#457B9D", edgecolor="white",
                   linewidth=0.8, height=0.65)
    # 数值标签
    for bar, v in zip(bars, agg["conversion"]):
        ax.text(v + 0.3, bar.get_y() + bar.get_height()/2,
                f"{v:.1f}%", va="center", fontsize=9, color="#333")

    ax.invert_yaxis()
    ax.set_xlabel("Conversion Rate (%)", fontsize=11)
    ax.set_xlim(0, agg["conversion"].max() * 1.15)
    ax.set_title(f"Top Converters (min shots = {min_shots})", fontsize=14, fontweight="bold", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.2, linewidth=0.5)
    ax.tick_params(labelsize=9)

    if out_path:
        fig.savefig(out_path, dpi=dpi, facecolor=bg)
        plt.close(fig)
    else:
        plt.show()


def plot_xg_goals_scatter(df: pd.DataFrame, out_path: Optional[str] = None,
                           min_shots: int = 10, dpi: int = 300):
    """高质量 xG vs Goals 散点图"""
    d = df.copy()
    d["is_goal"] = d["outcome"].eq("goal").astype(int)
    agg = d.groupby("player").agg(
        total_xg=("xg", "sum"), goals=("is_goal", "sum"), shots=("player", "size")
    ).reset_index()
    agg = agg[agg["shots"] >= min_shots].copy()
    if agg.empty:
        raise ValueError("No players meet the minimum shots threshold.")

    bg = "#ffffff"
    fig, ax = plt.subplots(figsize=(7, 6), facecolor=bg)
    ax.set_facecolor(bg)

    ax.scatter(agg["total_xg"], agg["goals"], s=90, color="#457B9D", edgecolors="white",
              linewidth=0.8, alpha=0.85, zorder=3)

    max_val = max(agg["total_xg"].max(), agg["goals"].max()) + 1
    ax.plot([0, max_val], [0, max_val], linestyle="--", color="#E74C3C", alpha=0.6,
            linewidth=1.5, label="y = x (perfect)", zorder=2)

    for _, r in agg.sort_values("goals", ascending=False).head(8).iterrows():
        ax.annotate(r["player"], (r["total_xg"], r["goals"]),
                    xytext=(6, 5), textcoords="offset points", fontsize=8, color="#333")

    ax.set_xlabel("Total xG", fontsize=11)
    ax.set_ylabel("Goals", fontsize=11)
    ax.set_title("xG vs Goals (min shots = {})".format(min_shots), fontsize=14, fontweight="bold", pad=10)
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.2, linewidth=0.5)
    ax.tick_params(labelsize=9)

    if out_path:
        fig.savefig(out_path, dpi=dpi, facecolor=bg)
        plt.close(fig)
    else:
        plt.show()


# ─────────────────────────────────────────────
# 多球员对比图
# ─────────────────────────────────────────────

def _agg_players(df_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
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
            "xg_diff": round(goals - total_xg, 3),
        })
    return pd.DataFrame(rows).sort_values("shots", ascending=False)


def plot_comparison_shot_maps(df_dict: Dict[str, pd.DataFrame],
                               out_path: Optional[str] = None, dpi: int = 300,
                               bg_color: str = "#1a1a2e"):
    """多球员高质量射门分布并排图"""
    n = len(df_dict)
    cols = min(n, 3)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(5.5 * cols, 4.5 * rows), facecolor=bg_color)
    if n == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]

    for idx, (player, df) in enumerate(df_dict.items()):
        ax = axes[idx // cols][idx % cols]
        ax.set_facecolor(bg_color)
        _half_pitch(ax, grid_alpha=0.2)

        pdf = df.copy()
        pdf["x_half"] = np.where(pdf["x"] > PITCH_LENGTH/2, PITCH_LENGTH - pdf["x"], pdf["x"])
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]

        for outcome in ["goal", "saved", "blocked", "off_target"]:
            g = pdf[pdf["outcome"] == outcome]
            if g.empty:
                continue
            style = OUTCOME_STYLE.get(outcome, {})
            sizes = _shot_marker(g)
            sc = ax.scatter(g["x_half"], g["y"], marker=style["marker"], s=sizes,
                            color=style["color"], edgecolors="white", linewidths=0.7,
                            alpha=0.9, label=style["label"], zorder=5)
            if outcome == "goal":
                sc.set_path_effects([pe.Stroke(linewidth=2, foreground="#ffffff44"), pe.Normal()])

        goals = (df["outcome"] == "goal").sum()
        ax.set_title(f"{player}\n{len(df)} shots | {goals} goals", color="white",
                     fontsize=11, fontweight="bold")
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=7,
                  facecolor=bg_color, edgecolor="white", labelcolor="white")

    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis("off")

    fig.suptitle("Shot Maps Comparison", color="white", fontsize=16, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    if out_path:
        fig.savefig(out_path, dpi=dpi, facecolor=bg_color, pad_inches=0.08)
        plt.close(fig)
    else:
        plt.show()


def plot_comparison_bar(df_dict: Dict[str, pd.DataFrame], out_path: Optional[str] = None, dpi: int = 300):
    """多球员4项指标柱状对比图（高清）"""
    agg = _agg_players(df_dict)
    metrics = ["shots", "goals", "conversion", "xg_diff"]
    titles = ["Total Shots", "Goals", "Conversion (%)", "xG Diff (Goals - xG)"]

    bg = "#ffffff"
    fig, axes = plt.subplots(1, 4, figsize=(16, 5.5), facecolor=bg)
    colors = [PLAYER_COLORS[i % len(PLAYER_COLORS)] for i in range(len(agg))]

    for ax, metric, title in zip(axes, metrics, titles):
        vals = agg[metric].values
        bars = ax.bar(range(len(agg)), vals, color=colors, edgecolor="white", linewidth=0.8)
        ax.set_xticks(range(len(agg)))
        ax.set_xticklabels(agg["player"], rotation=45, ha="right", fontsize=9)
        ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
        for i, v in enumerate(vals):
            label = f"{v:.1f}%" if metric == "conversion" else (f"{v:.2f}" if metric == "xg_diff" else str(int(v)))
            ax.text(i, v + max(vals) * 0.02, label, ha="center", fontsize=8, color="#333")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", alpha=0.2, linewidth=0.5)
        ax.tick_params(labelsize=8)

    fig.suptitle("Players Comparison", fontsize=15, fontweight="bold", y=1.01)
    fig.tight_layout()

    if out_path:
        fig.savefig(out_path, dpi=dpi, facecolor=bg)
        plt.close(fig)
    else:
        plt.show()


def plot_comparison_scatter(df_dict: Dict[str, pd.DataFrame], out_path: Optional[str] = None, dpi: int = 300):
    """多球员 xG vs Goals 散点图（高清）"""
    fig, ax = plt.subplots(figsize=(7, 6), facecolor="#ffffff")
    ax.set_facecolor("#ffffff")

    for idx, (player, df) in enumerate(df_dict.items()):
        total_xg = df["xg"].sum()
        goals = (df["outcome"] == "goal").sum()
        color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
        ax.scatter(total_xg, goals, color=color, s=130, edgecolors="white",
                   linewidth=1.0, label=player, zorder=3)
        ax.annotate(player, (total_xg, goals), xytext=(7, 5),
                    textcoords="offset points", fontsize=9, color="#222")

    max_val = max(
        max(df["xg"].sum() for df in df_dict.values()),
        max((df["outcome"] == "goal").sum() for df in df_dict.values())
    ) + 1
    ax.plot([0, max_val], [0, max_val], linestyle="--", color="#E74C3C",
            alpha=0.6, linewidth=1.5, label="y=x")
    ax.set_xlabel("Total xG", fontsize=11)
    ax.set_ylabel("Goals", fontsize=11)
    ax.set_title("xG vs Goals Comparison", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlim(0, max_val + 0.5)
    ax.set_ylim(0, max_val + 0.5)
    ax.legend(fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.2, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)

    if out_path:
        fig.savefig(out_path, dpi=dpi, facecolor="#ffffff")
        plt.close(fig)
    else:
        plt.show()


def plot_comparison_heatmap(df_dict: Dict[str, pd.DataFrame], out_path: Optional[str] = None, dpi: int = 300):
    """多球员射门密度热力图（高清）"""
    n = len(df_dict)
    cols = min(n, 3)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(5.5 * cols, 4.5 * rows), facecolor="#1a1a2e")

    if n == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]

    for idx, (player, df) in enumerate(df_dict.items()):
        ax = axes[idx // cols][idx % cols]
        ax.set_facecolor("#1a1a2e")

        pdf = df.copy()
        pdf["x_half"] = np.where(pdf["x"] > PITCH_LENGTH/2, PITCH_LENGTH - pdf["x"], pdf["x"])

        hb = ax.hist2d(pdf["x_half"], pdf["y"], bins=14, cmap="YlOrRd", alpha=0.85, vmin=0)
        plt.colorbar(hb[3], ax=ax, label="Shot Density", shrink=0.8)
        _half_pitch(ax, grid_alpha=0.15)

        goals = (df["outcome"] == "goal").sum()
        ax.set_title(f"{player} | {len(df)} shots | {goals} goals", fontsize=11,
                     color="white", fontweight="bold")

    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis("off")

    fig.suptitle("Shot Density Heatmaps", color="white", fontsize=15, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    if out_path:
        fig.savefig(out_path, dpi=dpi, facecolor="#1a1a2e", pad_inches=0.08)
        plt.close(fig)
    else:
        plt.show()