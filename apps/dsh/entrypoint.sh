#!/bin/sh
set -eu

BIND="$(hostname -i | awk '{print $1}')"
printf '%s' "$BIND" > /tmp/dsh-bind

if [ ! -f "$DSH_HOME/profiles/web/package.json" ] || ! grep -q '"@smp/console-shell"' "$DSH_HOME/profiles/web/package.json"; then
  dsh plugin --profile web add file:/opt/console-shell
fi
# The profile keeps its own copy. Refresh the built files so an image update
# reaches a profile that was installed earlier.
INSTALLED="$DSH_HOME/profiles/web/node_modules/@smp/console-shell"
if [ -d "$INSTALLED/lib" ]; then
  cp -f /opt/console-shell/lib/index.js /opt/console-shell/lib/client.js "$INSTALLED/lib/"
  cp -f /opt/console-shell/package.json "$INSTALLED/package.json"
fi

exec dsh --profile web --no-open --host "$BIND" --port 3080 \
  --public-url "${DSH_PUBLIC_URL}" \
  --trusted-host 127.0.0.1 \
  --trusted-host localhost
