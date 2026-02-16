#!/bin/bash
# =============================================================================
# Trading Dashboard - Lightsail Setup Script
# =============================================================================
# Run this on a fresh Ubuntu 22.04/24.04 Lightsail instance:
#   chmod +x deploy/setup.sh && sudo deploy/setup.sh
# =============================================================================

set -e  # Exit on any error

APP_DIR="/home/ubuntu/trading"
DEPLOY_DIR="$APP_DIR/deploy"

echo "============================================================"
echo "  Trading Dashboard - Server Setup"
echo "============================================================"

# --- 1. System packages ---
echo ""
echo "[1/7] Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx git > /dev/null

# --- 2. Create directories ---
echo "[2/7] Setting up directories..."
mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/data"
chown -R ubuntu:ubuntu "$APP_DIR"

# --- 3. Python virtual environment ---
echo "[3/7] Creating Python virtual environment..."
sudo -u ubuntu python3 -m venv "$APP_DIR/venv"

echo "[4/7] Installing Python dependencies..."
sudo -u ubuntu "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
sudo -u ubuntu "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# --- 4. Production config ---
echo "[5/7] Setting up production config..."
if [ ! -f "$APP_DIR/config.yaml" ] || grep -q '127.0.0.1' "$APP_DIR/config.yaml" 2>/dev/null; then
    cp "$DEPLOY_DIR/config.production.yaml" "$APP_DIR/config.yaml"
    echo "  Copied production config (host=0.0.0.0, desktop_notifications=false)"
fi

# --- 5. Nginx ---
echo "[6/7] Configuring Nginx..."
cp "$DEPLOY_DIR/nginx.conf" /etc/nginx/sites-available/trading
ln -sf /etc/nginx/sites-available/trading /etc/nginx/sites-enabled/trading
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# --- 6. Systemd services ---
echo "[7/7] Installing systemd services..."
cp "$DEPLOY_DIR/trading-api.service" /etc/systemd/system/
cp "$DEPLOY_DIR/trading-fetcher.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable trading-api trading-fetcher
systemctl start trading-api
echo "  API server started"

# Only start fetcher if token.json exists
if [ -f "$APP_DIR/token.json" ]; then
    systemctl start trading-fetcher
    echo "  Fetcher started"
else
    echo "  [!] Fetcher NOT started — run 'python initial_auth.py' first to create token.json"
    echo "      Then: sudo systemctl start trading-fetcher"
fi

echo ""
echo "============================================================"
echo "  SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "  Dashboard:  http://$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo '<your-ip>')"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status trading-api"
echo "    sudo systemctl status trading-fetcher"
echo "    sudo journalctl -u trading-api -f"
echo "    sudo journalctl -u trading-fetcher -f"
echo "    tail -f $APP_DIR/logs/api.log"
echo "    tail -f $APP_DIR/logs/fetcher.log"
echo ""
echo "  To re-authenticate Schwab:"
echo "    cd $APP_DIR && source venv/bin/activate"
echo "    python initial_auth.py"
echo "    sudo systemctl restart trading-fetcher"
echo ""
