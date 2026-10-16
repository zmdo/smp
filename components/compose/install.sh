#!/bin/sh
# Copied to the server and executed there. An existing compose plugin is left alone.
set -eu

if docker compose version >/dev/null 2>&1; then
  docker compose version --short
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "需要先安装 Docker Engine" >&2
  exit 1
fi

if ! sudo -n true >/dev/null 2>&1; then
  echo "需要免密 sudo 才能安装 Docker Compose 插件" >&2
  exit 1
fi

if [ ! -r /etc/os-release ]; then
  echo "无法识别操作系统" >&2
  exit 1
fi
. /etc/os-release
case "${ID}" in
  ubuntu|debian) ;;
  *)
    echo "当前只支持 Ubuntu 和 Debian，这台机器是 ${ID:-unknown}" >&2
    exit 1
    ;;
esac

export DEBIAN_FRONTEND=noninteractive
sudo -n apt-get update
if ! sudo -n apt-get install -y docker-compose-plugin; then
  sudo -n apt-get install -y docker-compose-v2
fi
docker compose version --short
