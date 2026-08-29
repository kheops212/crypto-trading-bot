#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

sudo cp "$DIR/crypto-bot.service" /etc/systemd/system/
sudo cp "$DIR/crypto-dashboard.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable crypto-bot crypto-dashboard
sudo systemctl start crypto-bot crypto-dashboard

echo ""
echo "Services installed. Checking status..."
sudo systemctl status crypto-bot --no-pager
sudo systemctl status crypto-dashboard --no-pager
