"""
Lesson 14 - Program 3: Database Query Program
Command-line interface to query the MLB SQLite database.
Supports ad-hoc SQL, joins (e.g. player stats + World Series by year), and filters.
"""

import sqlite3
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "mlb_history.db"

INTRO = """
Lesson 14 - MLB History Database Query
-------------------------------------
Commands:
  list              List tables
  schema [table]    Show schema (or all tables)
  run <SQL>         Execute a SQL query
  join              Run example: player stats joined with World Series by year
  filter year <Y>   Example: filter by year (run pre-defined query)
  quit / exit       Exit
"""


def get_conn():
    if not DB_PATH.exists():
        print("Database not found. Run 2_db_import.py first.")
        sys.exit(1)
    return sqlite3.connect(str(DB_PATH))


def list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [row[0] for row in cur.fetchall()]


def show_schema(conn: sqlite3.Connection, table: str = None):
    if table:
        cur = conn.execute(f"PRAGMA table_info({table})")
        rows = cur.fetchall()
        print(f"Table: {table}")
        for r in rows:
            print(f"  {r[1]} ({r[2]})")
    else:
        for t in list_tables(conn):
            show_schema(conn, t)
            print()


def run_query(conn: sqlite3.Connection, sql: str) -> bool:
    """Execute SQL and print results. Returns False on error."""
    sql = sql.strip()
    if not sql:
        return True
    try:
        cur = conn.execute(sql)
        rows = cur.fetchall()
        names = [d[0] for d in cur.description] if cur.description else []
        if names:
            print(" | ".join(names))
            print("-" * (4 * len(names)))
        for row in rows:
            print(" | ".join(str(x) if x is not None else "" for x in row))
        print(f"({len(rows)} row(s))")
        return True
    except sqlite3.Error as e:
        print("Error:", e)
        return False


def example_join(conn: sqlite3.Connection):
    """Run a join: season hitting leaders with World Series by year."""
    tables = list_tables(conn)
    if "season_hitting_leaders" in tables and "world_series" in tables:
        sql = """
        SELECT s.year, s.player, s.team, s.hr, s.rbi, w.winner AS ws_winner, w.runner_up
        FROM season_hitting_leaders s
        LEFT JOIN world_series w ON s.year = w.year
        ORDER BY s.year DESC, CAST(s.hr AS INTEGER) DESC
        LIMIT 25
        """
        print("Example join: hitting leaders + World Series by year\n")
        run_query(conn, sql)
    else:
        print("Need tables 'season_hitting_leaders' and 'world_series'. Run 2_db_import.py.")
        for t in tables:
            print("  -", t)


def filter_by_year(conn: sqlite3.Connection, year: str):
    """Pre-defined filter by year across tables."""
    tables = list_tables(conn)
    if "season_hitting_leaders" in tables:
        cur = conn.execute(
            "SELECT * FROM season_hitting_leaders WHERE year = ? LIMIT 20",
            (year,),
        )
        rows = cur.fetchall()
        names = [d[0] for d in cur.description] if cur.description else []
        print(f"Season hitting leaders for year {year}:\n")
        if names:
            print(" | ".join(names))
            print("-" * (4 * len(names)))
        for row in rows:
            print(" | ".join(str(x) if x is not None else "" for x in row))
        print(f"({len(rows)} row(s))")
    if "world_series" in tables:
        cur = conn.execute("SELECT * FROM world_series WHERE year = ?", (year,))
        rows = cur.fetchall()
        names = [d[0] for d in cur.description] if cur.description else []
        print(f"\nWorld Series for {year}:")
        if names:
            print(" | ".join(names))
            for row in rows:
                print(" | ".join(str(x) if x is not None else "" for x in row))
        print(f"({len(rows)} row(s))")


def main():
    print(INTRO)
    conn = get_conn()
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not line:
            continue
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        rest = (parts[1] or "").strip()

        if cmd in ("quit", "exit", "q"):
            break
        if cmd == "list":
            print("Tables:", ", ".join(list_tables(conn)))
        elif cmd == "schema":
            show_schema(conn, rest or None)
        elif cmd == "run":
            if rest:
                run_query(conn, rest)
            else:
                print("Usage: run <SQL>")
        elif cmd == "join":
            example_join(conn)
        elif cmd == "filter":
            # filter year 2022
            args = rest.split()
            if len(args) >= 2 and args[0].lower() == "year":
                filter_by_year(conn, args[1])
            else:
                print("Usage: filter year <YEAR>")
        else:
            # Treat as raw SQL
            run_query(conn, line)
    conn.close()


if __name__ == "__main__":
    main()
