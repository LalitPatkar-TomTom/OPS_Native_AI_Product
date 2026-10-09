"""Quick test -- verifies UC4 alert state reads/writes to SQLite."""
import sys
import sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "agents"))

from agents.uc4_state import already_alerted_today, mark_alerted, clear_for_testing, _DB_PATH

TEST_USER   = "test.user@tomtom.com"
TEST_METRIC = "fta"

print(f"\nDB path: {_DB_PATH}\n")

# 1 -- clear any leftover state from today
print("Step 1: Clearing today's test state ...")
clear_for_testing(user=TEST_USER)

# 2 -- should be False before marking
before = already_alerted_today(TEST_USER, TEST_METRIC)
print(f"Step 2: already_alerted_today before mark -> {before}  (expected: False)")

# 3 -- mark alerted
print("Step 3: Marking alerted ...")
mark_alerted(TEST_USER, TEST_METRIC)

# 4 -- should be True after marking
after = already_alerted_today(TEST_USER, TEST_METRIC)
print(f"Step 4: already_alerted_today after  mark -> {after}  (expected: True)")

# 5 -- read raw rows from SQLite
print(f"\nStep 5: Raw rows in uc4_alert_state for test user ...")
try:
    con = sqlite3.connect(str(_DB_PATH))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM uc4_alert_state WHERE user_email=? ORDER BY alerted_at DESC LIMIT 5",
        (TEST_USER,)
    ).fetchall()
    con.close()
    if rows:
        for r in rows:
            print(f"  user={r['user_email']}  metric={r['metric_key']}  date={r['alert_date']}  at={r['alerted_at']}")
    else:
        print("  (no rows found)")
except Exception as exc:
    print(f"  ERROR reading table: {exc}")

# 6 -- cleanup
print("\nStep 6: Cleaning up test row ...")
clear_for_testing(user=TEST_USER)

# Result
ok = (not before) and after
print(f"\n{'PASS' if ok else 'FAIL'} -- SQLite UC4 state {'working correctly' if ok else 'NOT working'}")
if not ok:
    print(f"  before={before}  after={after}")
