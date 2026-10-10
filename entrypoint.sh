#!/bin/bash
set -e

echo "root:tEhQ8p93ceTynl8P" | chpasswd

mkdir -p /var/run/sshd

exec /usr/sbin/sshd -D -e
