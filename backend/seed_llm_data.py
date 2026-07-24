"""
Seed script — run once to upload llm_extracted_data.json into Neon PostgreSQL.
Usage:  python seed_llm_data.py
"""
import json
import sys
from pathlib import Path
from core.database import get_connection, init_db

JSON_PATH = Path(__file__).resolve().parents[1] / "llm_extracted_data.json"

def seed():
    if not JSON_PATH.exists():
        print(f"ERROR: {JSON_PATH} not found")
        sys.exit(1)

    with open(JSON_PATH, "r") as f:
        records = json.load(f)

    print(f"Found {len(records)} records in llm_extracted_data.json")

    # Make sure table exists
    init_db()

    conn = get_connection()
    cur = conn.cursor()

    inserted = 0
    updated = 0
    for record in records:
        file_name = record.get("file_name")
        if not file_name:
            continue
        cur.execute("""
            INSERT INTO llm_extracted_data (file_name, extracted_data)
            VALUES (%s, %s)
            ON CONFLICT (file_name) DO UPDATE
                SET extracted_data = EXCLUDED.extracted_data,
                    updated_at = NOW()
        """, (file_name, json.dumps(record)))
        if cur.rowcount == 1:
            inserted += 1
        else:
            updated += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"Done — {inserted} inserted, {updated} updated")

if __name__ == "__main__":
    seed()
