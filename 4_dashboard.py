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


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase so 'Year'/'year' and 'HR'/'hr' both work."""
    if df is None or df.empty:
        return df
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


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
    return _normalize_columns(df)


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
        raise
    finally:
        conn.close()
    return _normalize_columns(df)


def _year_range_hint(hitting: pd.DataFrame) -> str:
    """Return a short hint like '1927–2022' for the year range in the hitting data."""
    if hitting.empty or "year" not in hitting.columns:
        return "unknown"
    y = pd.to_numeric(hitting["year"], errors="coerce").dropna()
    if len(y) == 0:
        return "unknown"
    return f"{int(y.min())}–{int(y.max())}"


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
            # Same 15 records in both panels; after cleaning, dropna() may remove invalid rows so "After" can have fewer rows
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
                st.caption("**After:** Same 15 records; numeric conversion + dropna (invalid year/hr). Fewer rows if any were removed.")
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
            yr_hint = _year_range_hint(hitting)
            st.info(f"No HR data in selected year range ({year_range[0]}–{year_range[1]}). Data contains years {yr_hint}. Try expanding the year range in the sidebar.")
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
                fig2.update_layout(xaxis=dict(tickformat="d", dtick=1))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No World Series data in selected range.")
        else:
            st.write(ws)
    else:
        st.info("No World Series table.")

    # Visualization 3: Joint view — HR leaders and WS winner (scatter or table)
    st.header("3. Hitting leaders vs. World Series winner (by year)")
    try:
        joined = load_joined(year_range)
    except Exception as e:
        st.error(f"Join failed: {e}")
        joined = pd.DataFrame()
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
                symbol="ws_winner",
                size_max=16,
            )
            fig3.update_traces(
                marker=dict(size=14, line=dict(width=2, color="white")),
                selector=dict(mode="markers"),
            )
            fig3.update_layout(
                xaxis=dict(tickformat="d", dtick=1),
                legend=dict(title="World Series winner", orientation="h", yanchor="top", y=1.12),
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.dataframe(joined.head(20))
    else:
        yr_hint = _year_range_hint(hitting)
        st.info(f"No data in selected year range ({year_range[0]}–{year_range[1]}). Hitting leaders has years {yr_hint}. Try expanding the year range in the sidebar, or run the scraper to fetch more seasons.")

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
