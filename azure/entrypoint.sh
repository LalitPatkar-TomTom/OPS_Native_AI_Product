#!/bin/bash
# One job execution = one fire_all_now.py run.
# The analytics DB lives on the opshub-config share; it is copied into the container for the run
# (SQLite and SMB locking do not mix) and written back with SQLite's backup API at the end.
set -u
DATA="${OPS_DATA_DIR:-/data/config/native-ai}"
WORK="${OPS_OUTPUT_DIR:-/work/output}"
mkdir -p "$DATA/logs" "$DATA/backups" "$WORK"
export OPS_BACKUP_DIR="$DATA/backups"

if [ -f "$DATA/trigger_audit.db" ]; then
    cp "$DATA/trigger_audit.db" "$WORK/trigger_audit.db"
    echo "analytics DB loaded from the share"
else
    echo "no analytics DB on the share yet — starting a new one"
fi

cd /app/MultiAgent_Briefing
python /app/azure/sync_skills_mount.py || echo "skills sync failed — using the profiles in the image"
python fire_all_now.py "$@"
rc=$?

python - "$WORK/trigger_audit.db" "$DATA/trigger_audit.db" <<'EOF'
import os, sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
if os.path.exists(src):
    tmp = dst + ".tmp"
    s, d = sqlite3.connect(src), sqlite3.connect(tmp)
    s.backup(d)
    d.close(); s.close()
    os.replace(tmp, dst)
    print("analytics DB saved to the share")
EOF

[ -f "$WORK/fire_all_now.log" ] && cat "$WORK/fire_all_now.log" >> "$DATA/logs/fire_all_now.log"
echo "run finished with exit code $rc"
exit $rc
