"""
⚽ EPL Shot Map — Streamlit Web Demo

Run locally:
    pip install -r requirements.txt
    streamlit run web_demo.py

Deploy to Streamlit Cloud (free):
    1. Push this repo to GitHub
    2. Go to share.streamlit.io → Connect GitHub → Deploy
    3. Set main file: web_demo.py
"""

import streamlit as st
import sys
import os

# 路径设置
CURRENT_DIR = os.path.dirname(__file__)
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.join(CURRENT_DIR, "src"))

# ── Page Config ───────────────────────────────
st.set_page_config(
    page_title="⚽ EPL Shot Map Generator",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ EPL Shot Map Generator")
st.markdown("输入球员名字，自动从 Understat 获取射门数据并生成可视化图表")

# ── Sidebar: Season Selector ─────────────────
with st.sidebar:
    st.header("设置")
    season = st.selectbox(
        "选择赛季",
        options=[2024, 2023, 2022, 2021, 2020],
        index=0,
        format_func=lambda x: f"{x}/{x+1}",
    )
    st.markdown("---")
    st.markdown("**数据来源**: [Understat](https://understat.com)")

# ── Main: Player Input & Charts ─────────────
player_name = st.text_input(
    "输入球员名字（英文）",
    value="Erling Haaland",
    placeholder="例如: Erling Haaland, Mohamed Salah, Marcus Rashford",
)

col1, col2 = st.columns([1, 2])

with col1:
    generate = st.button("🚀 生成射门图", type="primary", use_container_width=True)

with col2:
    st.write("")  # spacer

# ── Results ─────────────────────────────────
if generate and player_name:
    with st.spinner(f"正在从 Understat 获取 {player_name} 的数据..."):
        try:
            from data.understat_api import fetch_player_shots
            df = fetch_player_shots(player_name.strip(), season=season)

            shots_count = len(df)
            goals_count = (df["outcome"] == "goal").sum()
            total_xg = df["xg"].sum()

            metric_cols = st.columns(3)
            metric_cols[0].metric("射门数", shots_count)
            metric_cols[1].metric("进球数", goals_count)
            metric_cols[2].metric("总 xG", f"{total_xg:.2f}")

            st.success(f"获取到 {shots_count} 脚射门，{goals_count} 个进球！")

            # 生成图表
            from eplshotmaps.plot import plot_shot_map, plot_efficiency_bar, plot_xg_goals_scatter
            import matplotlib.pyplot as plt
            import io

            os.makedirs("out", exist_ok=True)

            # 1. 射门图
            st.subheader(f"📍 {player_name} — 射门分布图")
            safe_name = player_name.replace(" ", "_")
            shotmap_path = f"out/shotmap_{safe_name}.png"
            plot_shot_map(df, player=player_name, out_path=shotmap_path)
            st.image(shotmap_path, use_container_width=True)

            # 2. 效率图
            st.subheader("📊 联赛效率排行（射门≥10）")
            bar_path = "out/efficiency_bar.png"
            plot_efficiency_bar(df, min_shots=10, out_path=bar_path)
            st.image(bar_path, use_container_width=True)

            # 3. xG 散点图
            st.subheader("🎯 xG vs 实际进球")
            scatter_path = "out/xg_goals_scatter.png"
            plot_xg_goals_scatter(df, out_path=scatter_path, min_shots=10)
            st.image(scatter_path, use_container_width=True)

            # 4. 原始数据
            with st.expander("📋 查看原始数据"):
                st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"❌ 获取数据失败: {e}")
            st.info("💡 提示：检查球员名字拼写是否正确（使用英文名）")

# ── Footer ─────────────────────────────────
st.markdown("---")
st.markdown(
    "Built by [@yiyuanlee](https://github.com/yiyuanlee) · "
    "Data by [Understat](https://understat.com) · "
    "Powered by [Streamlit](https://streamlit.io)"
)
