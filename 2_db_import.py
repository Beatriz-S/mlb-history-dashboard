"""
Lesson 14 - Program 2: Database Import Program
Imports each CSV in the data folder as a separate SQLite table.
Uses appropriate data types (numeric, integer, text) and reports import errors.
"""

import csv
import sqlite3
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = Path(__file__).resolve().parent / "data" / "mlb_history.db"


def infer_type(values: list[str]) -> str:
    """Infer SQLite type from a list of string values."""
    for v in values:
        if v is None or v == "":
            continue
        v = v.strip()
        if not v or v in ("--", "—"):
            continue
        try:
            int(v)
            return "INTEGER"
        except ValueError:
            pass
        try:
            float(v.replace(",", ""))
            return "REAL"
        except ValueError:
            pass
    return "TEXT"


def safe_column_name(name: str) -> str:
    """Convert CSV header to valid SQLite column name."""
    s = "".join(c if c.isalnum() or c == "_" else "_" for c in (name or "col").strip())
    return s or "col"


def import_csv_to_table(conn: sqlite3.Connection, csv_path: Path, table_name: str) -> tuple[bool, str]:
    """
    Import a single CSV file as a table. Returns (success, message).
    Infers types from first 100 rows.
    """
    if not csv_path.exists():
        return False, f"File not found: {csv_path}"

    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
    except Exception as e:
        return False, f"Read error: {e}"

    if not header:
        return False, "CSV has no header"

    cols = [safe_column_name(h) for h in header]
    # Deduplicate column names
    seen = {}
    for i, c in enumerate(cols):
        if c in seen:
            cols[i] = f"{c}_{i}"
        seen[cols[i]] = True

    # Infer types from data (sample)
    sample = rows[: min(100, len(rows))]
    col_types = []
    for j in range(len(cols)):
        col_vals = [row[j] if j < len(row) else "" for row in sample]
        col_types.append(infer_type(col_vals))

    col_defs = ", ".join(f'"{c}" {t}' for c, t in zip(cols, col_types))
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_defs})'
    try:
        conn.execute(create_sql)
    except sqlite3.Error as e:
        return False, f"CREATE TABLE error: {e}"

    placeholders = ", ".join("?" * len(cols))
    insert_sql = f'INSERT INTO "{table_name}" ({", ".join(chr(34) + c + chr(34) for c in cols)}) VALUES ({placeholders})'
    errors = 0
    for row in rows:
        # Pad or trim row to match column count
        row = list(row)[: len(cols)]
        while len(row) < len(cols):
            row.append("")
        try:
            # Coerce types for SQLite
            out = []
            for j, (val, typ) in enumerate(zip(row, col_types)):
                v = (val or "").strip()
                if typ == "INTEGER" and v:
                    try:
                        out.append(int(float(v)))
                    except ValueError:
                        out.append(v)
                elif typ == "REAL" and v:
                    try:
                        out.append(float(v.replace(",", "")))
                    except ValueError:
                        out.append(v)
                else:
                    out.append(v if v else None)
            conn.execute(insert_sql, out)
        except sqlite3.Error as e:
            errors += 1
            if errors <= 3:
                print(f"  Row insert warning: {e}", file=sys.stderr)

    try:
        conn.commit()
    except sqlite3.Error as e:
        return False, f"Commit error: {e}"

    msg = f"Imported {len(rows)} rows into '{table_name}'"
    if errors:
        msg += f" ({errors} row errors)"
    return True, msg


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = DB_PATH
    conn = sqlite3.connect(str(db_path))

    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("No CSV files found in", DATA_DIR)
        print("Run 1_web_scraper.py first to generate data.")
        conn.close()
        sys.exit(1)

    print("Lesson 14 - Database Import")
    print("Database:", db_path)
    all_ok = True
    for csv_path in sorted(csv_files):
        table_name = csv_path.stem
        # SQLite-safe table name
        table_name = "".join(c if c.isalnum() or c == "_" else "_" for c in table_name) or "table"
        ok, msg = import_csv_to_table(conn, csv_path, table_name)
        print(f"  {csv_path.name} -> {table_name}: {msg}")
        if not ok:
            all_ok = False

    conn.close()
    if not all_ok:
        sys.exit(1)
    print("Import complete.")


if __name__ == "__main__":
    main()
