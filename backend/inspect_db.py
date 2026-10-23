import sqlite3
import os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "focusflow.db")
print("db exists:", os.path.exists(path), "size:", os.path.getsize(path) if os.path.exists(path) else 0)
conn = sqlite3.connect(path)
conn.row_factory = sqlite3.Row

tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("tables:", tables)

for t in tables:
    cols = [(r["name"], r["type"], r["notnull"], r["dflt_value"]) for r in conn.execute(f"PRAGMA table_info({t})")]
    print(f"\n-- {t} --")
    for c in cols:
        print("   ", c)

try:
    users = conn.execute("SELECT id, username, email FROM users").fetchall()
    print("\nUSERS:")
    for u in users:
        print("   ", dict(u))
except Exception as e:
    print("users read error:", e)

try:
    print("\napi_tokens count:", conn.execute("SELECT COUNT(*) FROM api_tokens").fetchone()[0])
except Exception as e:
    print("api_tokens error:", e)

conn.close()
