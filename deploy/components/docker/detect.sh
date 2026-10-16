#!/bin/sh
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker version --format '{{.Server.Version}}'
  exit 0
fi
exit 1
