#!/bin/bash
set -e

if [ -z "$ROOT_PASSWORD" ]; then
    echo "ROOT_PASSWORD is not set"
    exit 1
fi

echo "root:$ROOT_PASSWORD" | chpasswd

mkdir -p /var/run/sshd

exec /usr/sbin/sshd -D -e
