#!/bin/sh
set -eu
apt() {
  sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
    -o Acquire::https::Timeout=30 -o DPkg::Lock::Timeout=60 "$@"
}
apt update
apt install -y fpc
