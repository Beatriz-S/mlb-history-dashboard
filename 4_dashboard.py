"""
Lesson 14 - Program 4: Interactive Dashboard
Streamlit dashboard with 3+ visualizations, dropdowns, and sliders.
Displays MLB history data from the SQLite database.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "mlb_history.db"


@st.cache_data
def load_table(table_name: str) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


@st.cache_data
def load_joined(years: tuple = (1900, 2030)) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        sql = """
        SELECT s.year, s.player, s.team, s.hr, s.rbi, s.h, s.avg,
               w.winner AS ws_winner, w.runner_up
        FROM season_hitting_leaders s
        LEFT JOIN world_series w ON s.year = w.year
        WHERE CAST(s.year AS INTEGER) BETWEEN ? AND ?
        """
        df = pd.read_sql_query(sql, conn, params=(years[0], years[1]))
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


def main():
    st.set_page_config(page_title="MLB History Dashboard", layout="wide")
    st.title("MLB History Dashboard")
    st.caption("Lesson 14 — Web Scraping and Dashboard Project. Data from MLB.com.")

    if not DB_PATH.exists():
        st.warning("Database not found. Run `2_db_import.py` after `1_web_scraper.py`.")
        st.stop()

    hitting = load_table("season_hitting_leaders")
    world_series = load_table("world_series")

    if hitting.empty and world_series.empty:
        st.warning("No data in database. Run the scraper and import first.")
        st.stop()

    # Sidebar filters
    st.sidebar.header("Filters")
    year_min = 1900
    year_max = 2030
    if not hitting.empty and "year" in hitting.columns:
        try:
            y = pd.to_numeric(hitting["year"], errors="coerce").dropna()
            if len(y) > 0:
                year_min = int(y.min())
                year_max = int(y.max())
        except Exception:
            pass
    year_range = st.sidebar.slider(
        "Year range",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
    )
    event_filter = "All"
    if not world_series.empty and "winner" in world_series.columns:
        winners = ["All"] + sorted(world_series["winner"].dropna().unique().tolist())
        event_filter = st.sidebar.selectbox("World Series winner", winners)

    # Before/after data cleaning (rubric: show cleaning stages)
    with st.expander("Data cleaning: before & after"):
        st.markdown("Raw data from the database may have mixed types (e.g. year and HR as text) or missing values. We clean by converting to numeric and dropping invalid rows.")
        if not hitting.empty and "year" in hitting.columns and "hr" in hitting.columns:
            show_cols = [c for c in ["year", "player", "hr", "rbi"] if c in hitting.columns]
            # Use the same 15 rows for both panels so we show how the same records transform
            sample_before = hitting.head(15)[show_cols].copy()
            sample_after = sample_before.copy()
            sample_after["year"] = pd.to_numeric(sample_after["year"], errors="coerce")
            sample_after["hr"] = pd.to_numeric(sample_after["hr"], errors="coerce")
            sample_after = sample_after.dropna(subset=["year", "hr"])
            col_before, col_after = st.columns(2)
            with col_before:
                st.caption("**Before:** Raw types (year, hr as stored in DB)")
                st.dataframe(sample_before, use_container_width=True)
            with col_after:
                st.caption("**After:** Same rows — numeric year/hr, invalid rows removed")
                st.dataframe(sample_after, use_container_width=True)
        else:
            st.info("Hitting table missing required columns for this demo.")

    # Visualization 1: HR by year (bar or line)
    st.header("1. Home runs by year (top leaders)")
    if not hitting.empty and "year" in hitting.columns and "hr" in hitting.columns:
        df_hr = hitting.copy()
        df_hr["year"] = pd.to_numeric(df_hr["year"], errors="coerce")
        df_hr["hr"] = pd.to_numeric(df_hr["hr"], errors="coerce")
        df_hr = df_hr.dropna(subset=["year", "hr"])
        df_hr = df_hr[
            (df_hr["year"] >= year_range[0]) & (df_hr["year"] <= year_range[1])
        ]
        if not df_hr.empty:
            agg = df_hr.groupby("year")["hr"].max().reset_index()
            agg["year"] = agg["year"].astype(int)
            fig1 = px.bar(
                agg,
                x="year",
                y="hr",
                title="Max single-season HR in leaderboard by year",
                labels={"hr": "Home runs", "year": "Year"},
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No HR data in selected year range.")
    else:
        st.info("Hitting table missing 'year' or 'hr' columns.")

    # Visualization 2: World Series winners (dropdown + bar)
    st.header("2. World Series results by year")
    if not world_series.empty:
        ws = world_series.copy()
        if "year" in ws.columns:
            ws["year"] = pd.to_numeric(ws["year"], errors="coerce")
            ws = ws.dropna(subset=["year"])
            ws = ws[(ws["year"] >= year_range[0]) & (ws["year"] <= year_range[1])]
            if event_filter != "All":
                ws = ws[ws["winner"] == event_filter]
            if not ws.empty:
                ws = ws.copy()
                ws["year"] = ws["year"].astype(int)
                ws["count"] = 1
                fig2 = px.bar(
                    ws,
                    x="year",
                    y="count",
                    color="winner",
                    title="World Series winner by year",
                    labels={"winner": "Winner", "year": "Year"},
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No World Series data in selected range.")
        else:
            st.write(ws)
    else:
        st.info("No World Series table.")

    # Visualization 3: Joint view — HR leaders and WS winner (scatter or table)
    st.header("3. Hitting leaders vs. World Series winner (by year)")
    joined = load_joined(year_range)
    if not joined.empty:
        joined["hr"] = pd.to_numeric(joined["hr"], errors="coerce")
        joined["year"] = pd.to_numeric(joined["year"], errors="coerce")
        joined = joined.dropna(subset=["year", "hr"])
        if not joined.empty:
            joined = joined.copy()
            joined["year"] = joined["year"].astype(int)
            fig3 = px.scatter(
                joined,
                x="year",
                y="hr",
                color="ws_winner",
                hover_data=["player", "team", "rbi", "ws_winner", "runner_up"],
                title="Top HR by year with World Series winner",
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.dataframe(joined.head(20))
    else:
        st.info("Join data empty. Check table names: season_hitting_leaders, world_series.")

    # Extra: dynamic table based on filters
    st.header("Data table (filtered)")
    if not hitting.empty:
        h = hitting.copy()
        if "year" in h.columns:
            h["year"] = pd.to_numeric(h["year"], errors="coerce")
            h = h[(h["year"] >= year_range[0]) & (h["year"] <= year_range[1])]
        st.dataframe(h.head(50), use_container_width=True)


if __name__ == "__main__":
    main()
