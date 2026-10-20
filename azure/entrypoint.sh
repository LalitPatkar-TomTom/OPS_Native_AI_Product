#!/bin/bash
# One job execution = one fire_all_now.py run.
# The analytics DB lives on the opshub-config share; it is copied into the container for the run
# (SQLite and SMB locking do not mix) and written back with SQLite's backup API at the end.
set -u
DATA="${OPS_DATA_DIR:-/data/config/native-ai}"
WORK="${OPS_OUTPUT_DIR:-/work/output}"
mkdir -p "$DATA/logs" "$DATA/backups" "$WORK"
START_DOW=$(date +%u)    # 1 = Monday (TZ is Asia/Kolkata in the image)
START_HOUR=$(date +%H)
export OPS_BACKUP_DIR="$DATA/backups"

if [ -f "$DATA/trigger_audit.db" ]; then
    cp "$DATA/trigger_audit.db" "$WORK/trigger_audit.db"
    echo "analytics DB loaded from the share"
elif [ -f "$DATA/MIGRATED_FROM_LAPTOP.json" ]; then
    # after the switch-over the share DB is the only history; never send without it
    echo "STOP: the analytics DB is missing from the share although it was migrated — no emails sent"
    exit 1
else
    echo "no analytics DB on the share yet — starting a new one"
fi

cd /app/MultiAgent_Briefing
python /app/azure/sync_skills_mount.py || echo "skills sync failed — using the profiles in the image"
python fire_all_now.py "$@"
rc=$?

db_saved=0
python - "$WORK/trigger_audit.db" "$DATA/trigger_audit.db" <<'EOF' && db_saved=1
import os, sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
if not os.path.exists(src):
    sys.exit(1)
tmp = dst + ".tmp"
s, d = sqlite3.connect(src), sqlite3.connect(tmp)
s.backup(d)
d.close(); s.close()
os.replace(tmp, dst)
print("analytics DB saved to the share")
EOF
[ "$db_saved" = 1 ] || echo "WARNING: analytics DB NOT saved to the share"

# keep what the run produced (briefings, UC3 reports, snapshots) next to the history, as the laptop did
mkdir -p "$DATA/output"
find "$WORK" -maxdepth 1 -type f ! -name 'trigger_audit.db*' ! -name 'fire_all_now.log' -exec cp -p {} "$DATA/output/" \;

[ -f "$WORK/fire_all_now.log" ] && cat "$WORK/fire_all_now.log" >> "$DATA/logs/fire_all_now.log"
python /app/azure/run_report.py "$WORK/fire_all_now.log" "$rc" "$db_saved"

# weekly analytics (Word) for the four report readers: Mondays, after the 09:00 run, from the saved DB
if { [ "$START_DOW" = 1 ] && [ "$START_HOUR" = 09 ]; } && [ "$db_saved" = 1 ]; then
    python /app/azure/weekly_analytics.py
fi
echo "run finished with exit code $rc"
exit $rc
