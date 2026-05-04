"""
EPL Shot Map — Streamlit Web Demo
Features: Autocomplete, player headshots, 24h cache
"""

import streamlit as st
import sys
import os

CURRENT_DIR = os.path.dirname(__file__)
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.join(CURRENT_DIR, "src"))
sys.path.insert(0, os.path.join(CURRENT_DIR, "data"))

st.set_page_config(
    page_title="EPL Shot Map Generator",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ EPL Shot Map Generator")
st.markdown("输入球员名字，从 Understat 自动获取射门数据并生成可视化")

# ── Situation filter (shared helper) ─────────────────────────────
def filter_situation(df, situation):
    if situation == "All":
        return df
    return df[df["situation"] == situation]


@st.cache_data(ttl=3600)
def get_all_players_cached():
    from data.understat_api import get_all_players
    return get_all_players()


def get_player_headshot_url(player_name: str) -> str:
    """Fetch Wikipedia thumbnail URL for a player."""
    import requests
    import urllib.parse

    search_url = (
        f"https://en.wikipedia.org/w/api.php?action=query&list=search"
        f"&srsearch={urllib.parse.quote(player_name + ' footballer')}&format=json&srlimit=1"
    )
    try:
        r = requests.get(search_url, timeout=5)
        data = r.json()
        results = data.get("query", {}).get("search", [])
        if not results:
            return None
        page_title = results[0]["title"]
        img_url = (
            f"https://en.wikipedia.org/w/api.php?action=query&titles="
            f"{urllib.parse.quote(page_title)}&prop=pageimages&format=json"
            f"&pithumbsize=200&format=json"
        )
        r2 = requests.get(img_url, timeout=5)
        d = r2.json()
        pages = d.get("query", {}).get("pages", {})
        for v in pages.values():
            if "thumbnail" in v:
                return v["thumbnail"]["source"]
    except Exception:
        pass
    return None


def player_headshot_col(player_name: str, width: int = 80):
    """Render a player headshot + name in a column. Falls back to emoji icon."""
    url = get_player_headshot_url(player_name)
    if url:
        st.image(url, width=width)
    else:
        st.image(f"https://ui-avatars.com/api/?name={player_name.replace(' ', '+')}&background=1a1a2e&color=fff&size=80", width=width)
    st.caption(player_name)


# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    season = st.selectbox(
        "Season",
        options=[2025, 2024, 2023, 2022, 2021, 2020],
        index=0,
        format_func=lambda x: f"{x}/{x+1}",
    )
    situation_filter = st.selectbox(
        "Shot Situation",
        options=["All", "Open Play", "Penalty", "Free Kick", "From Corner"],
        help="Filter shots by how they were created",
    )
    st.markdown("---")
    if st.button("Clear cache", use_container_width=True):
        from data.understat_api import clear_cache
        clear_cache()
        st.success("Cache cleared!")
    st.markdown("---")
    st.markdown("Data: [Understat](https://understat.com)")

# ── Mode Selector ────────────────────────────────────────
mode = st.radio("Mode", ["Single Player", "Multi-Player Comparison"], horizontal=True)

# ──────────────────────────────────────────────────────────
# SINGLE PLAYER
# ──────────────────────────────────────────────────────────
if mode == "Single Player":
    all_players = get_all_players_cached()

    st.subheader("Player Search")
    col_input, col_avatar = st.columns([2, 1])

    with col_input:
        selected = st.selectbox(
            "Type or select a player",
            options=[""] + sorted(all_players),
            format_func=lambda x: x if x else "Type to search...",
            help="Autocomplete from Understat EPL player list",
        )
        player_name = st.text_input(
            "Or type any name (partial match works)",
            value=selected,
            placeholder="e.g. Haaland, Salah, Saka",
            key="single_name",
        )

    with col_avatar:
        if player_name:
            player_headshot_col(player_name, width=70)

    col1, col2 = st.columns([1, 2])
    with col1:
        generate = st.button("Generate Shot Map", type="primary", use_container_width=True)

    if generate and player_name:
        with st.spinner(f"Fetching {player_name} data..."):
            try:
                from data.understat_api import fetch_player_shots
                df = fetch_player_shots(player_name.strip(), season=season)
                df = filter_situation(df, situation_filter)

                shots_count = len(df)
                goals_count = (df["outcome"] == "goal").sum()
                total_xg = df["xg"].sum()
                conversion = round(goals_count / shots_count * 100, 1) if shots_count > 0 else 0

                mc = st.columns(4)
                mc[0].metric("Shots", shots_count)
                mc[1].metric("Goals", goals_count)
                mc[2].metric("xG", f"{total_xg:.2f}")
                mc[3].metric("Conversion", f"{conversion}%")

                from eplshotmaps.plot import plot_shot_map, plot_efficiency_bar, plot_xg_goals_scatter
                os.makedirs("out", exist_ok=True)

                st.subheader(f"Shot Map — {player_name}")
                safe_name = player_name.replace(" ", "_")
                shotmap_path = f"out/shotmap_{safe_name}.png"
                plot_shot_map(df, player=player_name, out_path=shotmap_path)
                st.image(shotmap_path, use_container_width=True)

                st.subheader("League Conversion Rankings (shots >= 10)")
                bar_path = "out/efficiency_bar.png"
                plot_efficiency_bar(df, min_shots=10, out_path=bar_path)
                st.image(bar_path, use_container_width=True)

                st.subheader("xG vs Goals")
                scatter_path = "out/xg_goals_scatter.png"
                plot_xg_goals_scatter(df, out_path=scatter_path, min_shots=10)
                st.image(scatter_path, use_container_width=True)

                with st.expander("Raw Data"):
                    st.dataframe(df, use_container_width=True)

            except Exception as e:
                st.error(f"Error: {e}")

# ──────────────────────────────────────────────────────────
# MULTI-PLAYER COMPARISON
# ──────────────────────────────────────────────────────────
else:
    all_players = get_all_players_cached()

    st.subheader("Multi-Player Comparison (up to 6 players)")
    player_input = st.text_area(
        "Player names (comma-separated)",
        value="Erling Haaland, Mohamed Salah, Alexander Isak",
        height=70,
        key="multi_input",
    )
    selected_preset = st.selectbox(
        "Quick select (autocomplete)",
        options=[""] + sorted(all_players),
        format_func=lambda x: x if x else "Choose a player to add...",
        key="preset_select",
    )

    if selected_preset:
        current = st.session_state.get("multi_input", "")
        players_cur = [p.strip() for p in current.split(",") if p.strip()]
        if selected_preset not in players_cur and len(players_cur) < 6:
            players_cur.append(selected_preset)
            st.session_state["multi_input"] = ", ".join(players_cur)

    col1, col2 = st.columns([1, 2])
    with col1:
        generate = st.button("Generate Comparison", type="primary", use_container_width=True)

    if generate:
        player_list = [p.strip() for p in st.session_state.get("multi_input", "").split(",") if p.strip()]

        if len(player_list) < 2:
            st.warning("Need at least 2 players")
        elif len(player_list) > 6:
            st.warning("Max 6 players")
        else:
            with st.spinner(f"Fetching {len(player_list)} players..."):
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

                    # Headshots row
                    st.subheader("Players")
                    head_cols = st.columns(len(df_dict))
                    for col, (name, _) in zip(head_cols, df_dict.items()):
                        with col:
                            player_headshot_col(name, width=70)

                    # Summary table
                    rows = []
                    for name, df in df_dict.items():
                        goals = (df["outcome"] == "goal").sum()
                        shots = len(df)
                        total_xg = df["xg"].sum()
                        rows.append({
                            "Player": name,
                            "Shots": shots,
                            "Goals": goals,
                            "Conversion%": round(goals / shots * 100, 1) if shots else 0,
                            "xG": round(total_xg, 2),
                            "xG Diff": round(goals - total_xg, 2),
                        })
                    st.dataframe(rows, use_container_width=True)

                    # Figures
                    st.subheader("Shot Maps")
                    plot_comparison_shot_maps(df_dict, out_path="out/compare_shotmaps.png")
                    st.image("out/compare_shotmaps.png", use_container_width=True)

                    st.subheader("Key Metrics")
                    plot_comparison_bar(df_dict, out_path="out/compare_bar.png")
                    st.image("out/compare_bar.png", use_container_width=True)

                    st.subheader("xG vs Goals")
                    plot_comparison_scatter(df_dict, out_path="out/compare_xg_scatter.png")
                    st.image("out/compare_xg_scatter.png", use_container_width=True)

                    st.subheader("Shot Density")
                    plot_comparison_heatmap(df_dict, out_path="out/compare_heatmap.png")
                    st.image("out/compare_heatmap.png", use_container_width=True)

                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown("---")
st.markdown(
    "Built by [@yiyuanlee](https://github.com/yiyuanlee) · "
    "Data by [Understat](https://understat.com) · "
    "Powered by [Streamlit](https://streamlit.io)"
)
