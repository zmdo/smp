#!/bin/sh
set -eu

BIND="$(hostname -i | awk '{print $1}')"
printf '%s' "$BIND" > /tmp/dsh-bind

PROFILE="$DSH_HOME/profiles/web/package.json"
if [ -f "$PROFILE" ] && grep -q 'file:/opt/console-shell' "$PROFILE"; then
  sed -i 's#file:/opt/console-shell#file:/opt/console-plugins/shell#' "$PROFILE"
fi

install_plugin() {
  name="$1"
  dir="$2"
  if [ ! -f "$PROFILE" ] || ! grep -q "\"$name\"" "$PROFILE"; then
    dsh plugin --profile web add "file:$dir"
  fi
  installed="$DSH_HOME/profiles/web/node_modules/$name"
  if [ -d "$installed/lib" ]; then
    cp -f "$dir"/lib/*.js "$installed/lib/"
    cp -f "$dir/package.json" "$installed/package.json"
  fi
}

install_plugin @smp/console-shell /opt/console-plugins/shell
install_plugin @smp/console-dashboard /opt/console-plugins/dashboard
install_plugin @smp/console-quant /opt/console-plugins/quant
install_plugin @smp/console-accounts /opt/console-plugins/accounts
install_plugin @smp/console-servers /opt/console-plugins/servers
install_plugin @smp/console-settings /opt/console-plugins/settings

exec dsh --profile web --no-open --host "$BIND" --port 3080 \
  --public-url "${DSH_PUBLIC_URL}" \
  --trusted-host 127.0.0.1 \
  --trusted-host localhost
