"""
Lesson 14 - Program 1: Web Scraping Program
Scrapes MLB history data from Major League Baseball website using Selenium.
Saves raw data to CSV files (season hitting leaders, World Series results).
Handles: pagination, missing tags, user-agent headers.
"""

import csv
import os
import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Output directory for CSV files
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# User-Agent to mimic a real browser (avoids some blocks)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def get_driver(headless: bool = True):
    """Create Selenium WebDriver with Chrome, user-agent, and options."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def safe_text(element, default=""):
    """Get text from element or return default if missing."""
    try:
        return (element.text or "").strip() if element else default
    except Exception:
        return default


def scrape_hitting_leaders(max_pages: int = 5, output_path: Path = None):
    """
    Scrape MLB all-time hitting leaders by season from mlb.com/stats.
    Handles pagination and missing cells. Saves to CSV.
    """
    output_path = output_path or DATA_DIR / "season_hitting_leaders.csv"
    url = "https://www.mlb.com/stats/all-time-by-season"
    driver = get_driver()
    rows = []
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        # Wait for table to load (stats tables often use data-testid or table)
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, [class*='table'], [class*='Table']"))
        )
        time.sleep(2)

        for page in range(max_pages):
            # Find table rows - adapt selectors to current MLB site structure
            try:
                table = driver.find_element(By.CSS_SELECTOR, "table")
            except Exception:
                table = driver.find_element(By.XPATH, "//table")
            body = table.find_elements(By.TAG_NAME, "tbody")
            tbody = body[0] if body else table
            trs = tbody.find_elements(By.TAG_NAME, "tr") if body else table.find_elements(By.XPATH, ".//tr")

            for tr in trs:
                tds = tr.find_elements(By.TAG_NAME, "td")
                if len(tds) < 3:
                    continue
                row = []
                for td in tds:
                    row.append(safe_text(td))
                if any(row):
                    rows.append(row)

            # Pagination: look for "Next" or "Load more" button
            try:
                next_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(translate(., 'NEXT', 'next'), 'next')] | //a[contains(translate(., 'NEXT', 'next'), 'next')] | //button[contains(., 'Load')]"
                )
                if next_btn and next_btn.is_displayed():
                    next_btn.click()
                    time.sleep(1.5)
                else:
                    break
            except Exception:
                break

        # If we have no header, use a default; otherwise first row might be header
        if rows:
            # MLB table often has: #, Player, Team, Year, G, AB, R, H, 2B, 3B, HR, RBI, BB, SO, SB, CS, AVG, OBP, SLG, OPS
            headers = [
                "rank", "player", "position", "year", "team", "g", "ab", "r", "h", "2b", "3b", "hr", "rbi",
                "bb", "so", "sb", "cs", "avg", "obp", "slg", "ops"
            ]
            # Pad or trim to match column count
            ncols = len(rows[0])
            if ncols > len(headers):
                headers = headers + [f"col_{i}" for i in range(len(headers), ncols)]
            else:
                headers = headers[:ncols]

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(headers)
                w.writerows(rows)
            print(f"Saved {len(rows)} hitting leader rows to {output_path}")
        else:
            _write_sample_hitting_csv(output_path)
    finally:
        driver.quit()
    return output_path


def _write_sample_hitting_csv(output_path: Path):
    """Write sample hitting data so DB/dashboard can run if scrape returns nothing."""
    headers = ["rank", "player", "position", "year", "team", "g", "ab", "r", "h", "2b", "3b", "hr", "rbi", "bb", "so", "sb", "cs", "avg", "obp", "slg", "ops"]
    sample = [
        ["1", "Babe Ruth", "RF", "1927", "NYY", "151", "540", "158", "192", "29", "8", "60", "164", "137", "89", "7", "6", ".356", ".486", ".772", "1.258"],
        ["2", "Roger Maris", "RF", "1961", "NYY", "161", "590", "132", "159", "16", "4", "61", "141", "94", "67", "0", "0", ".269", ".372", ".620", ".992"],
        ["3", "Aaron Judge", "CF", "2022", "NYY", "157", "570", "133", "177", "28", "0", "62", "131", "111", "175", "16", "3", ".311", ".425", ".686", "1.111"],
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(sample)
    print(f"No table rows found; wrote sample data to {output_path}")


def scrape_world_series(output_path: Path = None):
    """
    Scrape World Series winners by year from MLB postseason history.
    Saves year, winner, runner_up, series_score to CSV.
    """
    output_path = output_path or DATA_DIR / "world_series.csv"
    url = "https://www.mlb.com/postseason/history/world-series"
    driver = get_driver()
    results = []
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        time.sleep(2)

        # Find year headings and "Winner defeat Runner-up X-Y" text
        page_text = driver.find_element(By.TAG_NAME, "body").text
        # Pattern: "2024" then "Dodgers defeat Yankees 4-1" or "Nationals defeat Astros 4-3"
        year_pattern = re.compile(r"^(19\d{2}|20\d{2})$", re.MULTILINE)
        block_pattern = re.compile(
            r"(?:(\d{4})\s*\n)?(.+?)\s+defeat\s+(.+?)\s+(\d)-(\d)",
            re.IGNORECASE | re.DOTALL
        )

        # Simpler: find all h3 (year) and following text
        headings = driver.find_elements(By.CSS_SELECTOR, "h2, h3")
        current_year = None
        for el in headings:
            text = safe_text(el)
            if re.match(r"^(19|20)\d{2}$", text):
                current_year = text
            elif current_year and "defeat" in text.lower():
                # e.g. "Dodgers defeat Blue Jays 4-3"
                m = re.search(r"(.+?)\s+defeat\s+(.+?)\s+(\d)-(\d)", text, re.IGNORECASE)
                if m:
                    winner, runner_up, w, l = m.group(1).strip(), m.group(2).strip(), m.group(3), m.group(4)
                    results.append({
                        "year": current_year,
                        "winner": winner,
                        "runner_up": runner_up,
                        "winner_games": w,
                        "runner_up_games": l,
                    })
                current_year = None

        # Fallback: parse full page text for "YYYY ... defeat ... X-Y"
        if not results:
            lines = page_text.split("\n")
            for i, line in enumerate(lines):
                m = re.match(r"^(\d{4})$", line.strip())
                if m and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    d = re.search(r"(.+?)\s+defeat\s+(.+?)\s+(\d)-(\d)", next_line, re.IGNORECASE)
                    if d:
                        results.append({
                            "year": m.group(1),
                            "winner": d.group(1).strip(),
                            "runner_up": d.group(2).strip(),
                            "winner_games": d.group(3),
                            "runner_up_games": d.group(4),
                        })

        if not results:
            _write_sample_world_series_csv(output_path)
        else:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["year", "winner", "runner_up", "winner_games", "runner_up_games"])
                w.writeheader()
                w.writerows(results)
            print(f"Saved {len(results)} World Series records to {output_path}")
    finally:
        driver.quit()
    return output_path


def _write_sample_world_series_csv(output_path: Path):
    """Write sample World Series data if scrape finds nothing."""
    sample = [
        {"year": "2024", "winner": "Dodgers", "runner_up": "Yankees", "winner_games": "4", "runner_up_games": "1"},
        {"year": "2023", "winner": "Rangers", "runner_up": "D-backs", "winner_games": "4", "runner_up_games": "1"},
        {"year": "2022", "winner": "Astros", "runner_up": "Phillies", "winner_games": "4", "runner_up_games": "2"},
        {"year": "2021", "winner": "Braves", "runner_up": "Astros", "winner_games": "4", "runner_up_games": "2"},
        {"year": "2019", "winner": "Nationals", "runner_up": "Astros", "winner_games": "4", "runner_up_games": "3"},
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "winner", "runner_up", "winner_games", "runner_up_games"])
        w.writeheader()
        w.writerows(sample)
    print(f"No World Series rows parsed; wrote {len(sample)} sample records to {output_path}")


def main():
    print("Lesson 14 - Web Scraper: MLB History Data")
    print("Scraping season hitting leaders (may take a minute)...")
    scrape_hitting_leaders(max_pages=3)
    print("Scraping World Series history...")
    scrape_world_series()
    print("Done. CSV files are in:", DATA_DIR)


if __name__ == "__main__":
    main()
