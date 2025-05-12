#!/usr/bin/env bash

set -euox pipefail

CHAIN="${CHAIN:-${1:?Which chain to set up for? eth | bsc | base | sol}}"
PORT="${2:-9100}"
SCRIPT_PATH="$(realpath chain_drift.py)"
INSTALL_PATH="/usr/local/bin/chain_drift.py"
SERVICE_NAME="chain_drift_${CHAIN}.service"

if command -v apt >/dev/null; then
    apt update
    apt install -y python3 python3-pip wget
elif command -v yum >/dev/null; then
    yum install -y python3 python3-pip wget
else
    echo "Unsupported OS package manager"
    exit 1
fi

pip3 install --upgrade pip
pip3 install flask requests

if [ ! -f "${SCRIPT_PATH}" ] ; then
  SCRIPT_PATH=/tmp/block_drift_exporter.py
  wget https://raw.githubusercontent.com/dit-darius/shared_scriptlets/refs/heads/main/bc/monitoring/block_drift/block_drift_exporter.py -O "${SCRIPT_PATH}"
fi
cp "${SCRIPT_PATH}" "${INSTALL_PATH}"
chmod +x "${INSTALL_PATH}"

cat <<EOF > /etc/systemd/system/${SERVICE_NAME}
[Unit]
Description=Chain drift exporter for ${CHAIN}
After=network.target
PartOf=alloy.service

[Service]
ExecStart=/usr/bin/python3 $INSTALL_PATH ${CHAIN} --serve --port ${PORT}
Restart=always
User=root
WorkingDirectory=/root

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /etc/systemd/system/alloy.service.d
cat <<EOF > /etc/systemd/system/alloy.service.d/override.conf
[Unit]
Requires=${SERVICE_NAME}
After=${SERVICE_NAME}
EOF

CONFIG_FILE="/etc/alloy/config.alloy"
SCRAPE_SNIPPET="prometheus.scrape \"chain_drift_${CHAIN}\""

if [ -f "${CONFIG_FILE}" ] && ! grep -q "${SCRAPE_SNIPPET}" "${CONFIG_FILE}"; then
    cat <<EOF >> "$CONFIG_FILE"

$SCRAPE_SNIPPET {
  targets = [
    {
      job = "chain_drift_${CHAIN}",
      __address__ = "localhost:${PORT}",
    },
  ]
  forward_to = [prometheus.remote_write.default.receiver]
}
EOF
fi

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"
systemctl restart alloy

echo "✅ Setup complete for ${CHAIN} exporter on port ${PORT}"

