# MLB History Dashboard

This repository contains four programs that retrieve baseball history data from the Major League Baseball (MLB) website and present it in an interactive dashboard. (Lesson 14 — Web Scraping and Dashboard Project.)

## Learning Objectives

- Use **Selenium** to scrape data from MLB.com
- Clean and transform raw data into structured CSV files
- Store data in **SQLite** (one table per CSV)
- Query the database via **command line** with joins and filters
- Build an **interactive dashboard** with **Streamlit** (dropdowns, sliders, 3+ visualizations)

## Project Structure

```
mlb-history-dashboard/
├── 1_web_scraper.py    # Scrape MLB stats & World Series history → CSV
├── 2_db_import.py      # Import CSVs into SQLite
├── 3_db_query.py        # CLI to run SQL and joined queries
├── 4_dashboard.py      # Streamlit dashboard
├── data/               # CSV output and mlb_history.db
├── requirements.txt
└── README.md
```

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   You need Chrome installed for Selenium (ChromeDriver is installed automatically via `webdriver-manager`).

## Running the Programs

### 1. Web Scraping

Scrapes MLB.com for:

- **Season hitting leaders** (all-time by season) → `data/season_hitting_leaders.csv`
- **World Series results** (year, winner, runner-up) → `data/world_series.csv`

Handles pagination, missing tags, and browser user-agent.

```bash
python 1_web_scraper.py
```

If the live site structure has changed, sample data is written so the rest of the pipeline still runs.

### 2. Database Import

Imports each CSV in `data/` as a separate SQLite table with inferred types (integer, real, text). Creates `data/mlb_history.db`.

```bash
python 2_db_import.py
```

### 3. Database Query (CLI)

Interactive command-line interface to query the database:

```bash
python 3_db_query.py
```

Commands:

- `list` — List tables
- `schema [table]` — Show table schema(s)
- `run <SQL>` — Execute any SQL
- `join` — Example: hitting leaders joined with World Series by year
- `filter year <YEAR>` — Filter by year
- `quit` / `exit` — Exit

### 4. Dashboard

Streamlit app with:

- **Year range slider** and **World Series winner** dropdown
- **Visualization 1:** Home runs by year (bar chart)
- **Visualization 2:** World Series winner by year (bar chart)
- **Visualization 3:** HR leaders vs. World Series winner by year (scatter)
- **Data table** filtered by year

Run locally:

```bash
streamlit run 4_dashboard.py
```

## Deployment

- **Streamlit Cloud:** Push this repo to GitHub, then connect it at [share.streamlit.io](https://share.streamlit.io). Add the repo and set the run command to `streamlit run 4_dashboard.py`. Ensure `data/mlb_history.db` and any needed CSVs are in the repo or generated in a build step.
- **Render:** Use a "Web Service" with build command `pip install -r requirements.txt` and start command `streamlit run 4_dashboard.py --server.port $PORT`.

For deployment, either commit `data/mlb_history.db` (and CSVs) to the repo or add a build step that runs `1_web_scraper.py` and `2_db_import.py` before starting the app.

## Data Sources

- [MLB Stats — All-Time by Season](https://www.mlb.com/stats/all-time-by-season)
- [MLB Postseason History — World Series](https://www.mlb.com/postseason/history/world-series)

## License

For educational use as part of the Python class.
