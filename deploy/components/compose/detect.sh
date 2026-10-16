#!/bin/sh
if docker compose version >/dev/null 2>&1; then
  docker compose version --short
  exit 0
fi
exit 1
