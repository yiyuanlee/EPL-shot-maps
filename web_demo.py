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

CURRENT_DIR = os.path.dirname(__file__)
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.join(CURRENT_DIR, "src"))
sys.path.insert(0, os.path.join(CURRENT_DIR, "data"))

st.set_page_config(
    page_title="⚽ EPL Shot Map Generator",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ EPL Shot Map Generator")
st.markdown("输入球员名字，从 Understat 自动获取射门数据并生成可视化")

# ── Sidebar ─────────────────────────────────
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

# ── Mode Selector ───────────────────────────
mode = st.radio("选择模式", ["单球员", "多球员对比"], horizontal=True, label_visibility="visible")

# ── Single Player Mode ──────────────────────
if mode == "单球员":
    player_name = st.text_input(
        "输入球员名字（英文）",
        value="Erling Haaland",
        placeholder="例如: Erling Haaland, Mohamed Salah",
        key="single_player",
    )
    col1, col2 = st.columns([1, 2])
    with col1:
        generate = st.button("🚀 生成射门图", type="primary", use_container_width=True)

    if generate and player_name:
        with st.spinner(f"正在获取 {player_name} 的数据..."):
            try:
                from data.understat_api import fetch_player_shots
                df = fetch_player_shots(player_name.strip(), season=season)

                shots_count = len(df)
                goals_count = (df["outcome"] == "goal").sum()
                total_xg = df["xg"].sum()

                mc = st.columns(3)
                mc[0].metric("射门数", shots_count)
                mc[1].metric("进球数", goals_count)
                mc[2].metric("总 xG", f"{total_xg:.2f}")

                from eplshotmaps.plot import plot_shot_map, plot_efficiency_bar, plot_xg_goals_scatter
                os.makedirs("out", exist_ok=True)

                st.subheader(f"📍 {player_name} - 射门分布图")
                safe_name = player_name.replace(" ", "_")
                shotmap_path = f"out/shotmap_{safe_name}.png"
                plot_shot_map(df, player=player_name, out_path=shotmap_path)
                st.image(shotmap_path, use_container_width=True)

                st.subheader("📊 联赛效率排行（射门>=10）")
                bar_path = "out/efficiency_bar.png"
                plot_efficiency_bar(df, min_shots=10, out_path=bar_path)
                st.image(bar_path, use_container_width=True)

                st.subheader("🎯 xG vs 实际进球")
                scatter_path = "out/xg_goals_scatter.png"
                plot_xg_goals_scatter(df, out_path=scatter_path, min_shots=10)
                st.image(scatter_path, use_container_width=True)

                with st.expander("📋 查看原始数据"):
                    st.dataframe(df, use_container_width=True)

            except Exception as e:
                st.error(f"❌ 获取数据失败: {e}")
                st.info("检查球员名字拼写是否正确（使用英文名）")

# ── Multi Player Comparison Mode ───────────
else:
    st.text_area(
        "输入多个球员名字（用英文逗号分隔）",
        value="Erling Haaland, Mohamed Salah, Alexander Isak",
        height=60,
        key="multi_players",
    )
    col1, col2 = st.columns([1, 2])
    with col1:
        generate = st.button("🚀 生成对比图", type="primary", use_container_width=True)

    if generate:
        player_input = st.session_state.get("multi_players", "")
        player_list = [p.strip() for p in player_input.split(",") if p.strip()]

        if len(player_list) < 2:
            st.warning("请输入至少2位球员进行对比")
        elif len(player_list) > 6:
            st.warning("最多支持6位球员同时对比")
        else:
            with st.spinner(f"正在获取 {len(player_list)} 位球员数据..."):
                try:
                    from data.understat_api import fetch_multi_player_shots
                    df_dict = fetch_multi_player_shots(player_list, season=season)

                    from eplshotmaps.plot import (
                        plot_comparison_shot_maps,
                        plot_comparison_bar,
                        plot_comparison_scatter,
                        plot_comparison_heatmap,
                    )
                    os.makedirs("out", exist_ok=True)

                    # 汇总数据
                    rows = []
                    for name, df in df_dict.items():
                        goals = (df["outcome"] == "goal").sum()
                        shots = len(df)
                        total_xg = df["xg"].sum()
                        rows.append({
                            "球员": name,
                            "射门": shots,
                            "进球": goals,
                            "转化率%": round(goals/shots*100, 1) if shots > 0 else 0,
                            "总xG": round(total_xg, 2),
                            "xG差值": round(goals - total_xg, 2),
                        })
                    summary_df = rows
                    st.subheader("📊 数据汇总")
                    st.dataframe(summary_df, use_container_width=True)

                    # 图1：并排射门图
                    st.subheader("📍 射门分布对比")
                    compare_shotmap_path = "out/compare_shotmaps.png"
                    plot_comparison_shot_maps(df_dict, out_path=compare_shotmap_path)
                    st.image(compare_shotmap_path, use_container_width=True)

                    # 图2：4项指标柱状图
                    st.subheader("📊 关键指标对比")
                    compare_bar_path = "out/compare_bar.png"
                    plot_comparison_bar(df_dict, out_path=compare_bar_path)
                    st.image(compare_bar_path, use_container_width=True)

                    # 图3：xG vs Goals
                    st.subheader("🎯 xG vs 实际进球")
                    compare_scatter_path = "out/compare_xg_scatter.png"
                    plot_comparison_scatter(df_dict, out_path=compare_scatter_path)
                    st.image(compare_scatter_path, use_container_width=True)

                    # 图4：热力图
                    st.subheader("🗺️ 射门密度热力图")
                    compare_heatmap_path = "out/compare_heatmap.png"
                    plot_comparison_heatmap(df_dict, out_path=compare_heatmap_path)
                    st.image(compare_heatmap_path, use_container_width=True)

                except Exception as e:
                    st.error(f"❌ 获取数据失败: {e}")

# ── Footer ─────────────────────────────────
st.markdown("---")
st.markdown(
    "Built by [@yiyuanlee](https://github.com/yiyuanlee) · "
    "Data by [Understat](https://understat.com) · "
    "Powered by [Streamlit](https://streamlit.io)"
)