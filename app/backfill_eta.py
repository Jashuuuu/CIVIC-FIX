import sqlite3
from datetime import datetime, timedelta

def backfill():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    accepted = cursor.execute("SELECT id, issue_type FROM complaints WHERE status = 'Accepted' AND estimated_completion_date IS NULL").fetchall()

    for row in accepted:
        id, issue_type = row
        eta_days = {'Garbage': 1, 'Water': 2, 'Streetlight': 3, 'Roads': 5}.get(issue_type, 4)
        estimated_date = (datetime.now() + timedelta(days=eta_days)).strftime('%Y-%m-%d')
        cursor.execute("UPDATE complaints SET estimated_completion_date = ? WHERE id = ?", (estimated_date, id))

    conn.commit()
    conn.close()
    print(f"Backfilled {len(accepted)} complaints.")

if __name__ == '__main__':
    backfill()
