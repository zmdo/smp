#!/bin/sh
set -eu

BIND="$(hostname -i | awk '{print $1}')"
printf '%s' "$BIND" > /tmp/dsh-bind

if [ ! -f "$DSH_HOME/profiles/web/package.json" ] || ! grep -q '"@smp/console-shell"' "$DSH_HOME/profiles/web/package.json"; then
  dsh plugin --profile web add file:/opt/console-shell
fi

exec dsh --profile web --no-open --host "$BIND" --port 3080 \
  --public-url "${DSH_PUBLIC_URL}" \
  --trusted-host 127.0.0.1 \
  --trusted-host localhost
