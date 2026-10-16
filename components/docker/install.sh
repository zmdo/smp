#!/bin/sh
# Copied to the server and executed there. Already-working Docker is left alone.
set -eu

if ! sudo -n true >/dev/null 2>&1; then
  echo "需要免密 sudo 才能安装 Docker Engine" >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker version --format '{{.Server.Version}}'
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
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
  codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
  if [ -z "$codename" ]; then
    echo "无法识别系统版本" >&2
    exit 1
  fi
  export DEBIAN_FRONTEND=noninteractive
  arch="$(dpkg --print-architecture)"
  sudo -n apt-get update
  sudo -n apt-get install -y ca-certificates curl
  sudo -n install -m 0755 -d /etc/apt/keyrings
  sudo -n curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
  sudo -n chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${ID} ${codename} stable" \
    | sudo -n tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo -n apt-get update
  sudo -n apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
fi

if command -v systemctl >/dev/null 2>&1; then
  sudo -n systemctl enable --now docker >/dev/null 2>&1 || true
fi

target="$(id -un)"
if ! id -nG "$target" | grep -qw docker; then
  sudo -n usermod -aG docker "$target"
fi

sudo -n docker version --format '{{.Server.Version}}'
