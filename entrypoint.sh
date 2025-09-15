#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"
MAX_PROC="${SCRAPYD_MAX_PROC:-4}"

# Use an app-writable path (avoid /etc in case of restrictions)
CONF="/app/scrapyd.conf"
mkdir -p /app

cat >"$CONF" <<EOF
[scrapyd]
# Bind to the Cloud Run port
bind_address = 0.0.0.0
http_port = ${PORT}
max_proc = ${MAX_PROC}
# Ensure Twisted runs in foreground; Scrapyd uses twistd -n under the hood
application = scrapyd.app.application

[services]
# leave empty unless you add custom services
EOF

echo "[entrypoint] Starting Scrapyd on 0.0.0.0:${PORT} (max_proc=${MAX_PROC})"
# -n ensures foreground; scrapyd command already does this, but be explicit
exec scrapyd #-c "$CONF" -n