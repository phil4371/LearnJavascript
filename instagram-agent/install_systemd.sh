#!/usr/bin/env bash
# Installiert alle systemd-Timer für alle 10 Instagram-Accounts.
# Ausführen als root: sudo bash install_systemd.sh
set -e

AGENT_DIR="/home/pi/instagram-agent"
SYSTEMD_DIR="/etc/systemd/system"

# Service-Templates kopieren
for svc in ig-feed ig-story ig-reel ig-engagement ig-planner; do
  cp "$AGENT_DIR/systemd/${svc}@.service" "$SYSTEMD_DIR/"
done

# Log-Verzeichnis
mkdir -p "$AGENT_DIR/logs"
chown pi:pi "$AGENT_DIR/logs"

# Accounts und ihre gestaffelten Zeiten
# Feed: 17:00–19:30 (alle 15 Min.), Story: 10:00–12:00, Reel: Di+Fr gestaffelt
# Engagement: gleichzeitig alle (kleine Last)

declare -A FEED_TIMES=(
  [etf_finanzen]="17:00"
  [ki_tools]="17:15"
  [fitness_abnehmen]="17:30"
  [immobilien_basics]="17:45"
  [side_hustle]="18:00"
  [krypto_basics]="18:15"
  [meal_prep]="18:30"
  [mindfulness]="18:45"
  [reise_budget]="19:00"
  [produktivitaet]="19:15"
)

declare -A STORY_TIMES=(
  [etf_finanzen]="10:00"
  [ki_tools]="10:12"
  [fitness_abnehmen]="10:24"
  [immobilien_basics]="10:36"
  [side_hustle]="10:48"
  [krypto_basics]="11:00"
  [meal_prep]="11:12"
  [mindfulness]="11:24"
  [reise_budget]="11:36"
  [produktivitaet]="11:48"
)

# Reel-Zeiten: Di (offset 0–9 Min.) und Fr (offset 0–9 Min.)
declare -A REEL_OFFSET=(
  [etf_finanzen]="0"
  [ki_tools]="1"
  [fitness_abnehmen]="2"
  [immobilien_basics]="3"
  [side_hustle]="4"
  [krypto_basics]="5"
  [meal_prep]="6"
  [mindfulness]="7"
  [reise_budget]="8"
  [produktivitaet]="9"
)

write_timer() {
  local unit="$1"
  local account="$2"
  local calendar="$3"
  cat > "$SYSTEMD_DIR/${unit}@${account}.timer" <<EOF
[Unit]
Description=${unit} Timer — ${account}

[Timer]
OnCalendar=${calendar}
Persistent=true
Unit=${unit}@${account}.service

[Install]
WantedBy=timers.target
EOF
}

for account in etf_finanzen ki_tools fitness_abnehmen immobilien_basics side_hustle \
               krypto_basics meal_prep mindfulness reise_budget produktivitaet; do

  # Feed: täglich
  write_timer "ig-feed" "$account" "*-*-* ${FEED_TIMES[$account]}:00"

  # Story: täglich
  write_timer "ig-story" "$account" "*-*-* ${STORY_TIMES[$account]}:00"

  # Reel: Di 16:0X und Fr 16:0X
  offset="${REEL_OFFSET[$account]}"
  write_timer "ig-reel" "$account" "Tue,Fri *-*-* 16:0${offset}:00"

  # Engagement: 09:00 und 20:00 täglich
  cat > "$SYSTEMD_DIR/ig-engagement@${account}.timer" <<EOF
[Unit]
Description=ig-engagement Timer — ${account}

[Timer]
OnCalendar=*-*-* 09:00:00
OnCalendar=*-*-* 20:00:00
Persistent=true
Unit=ig-engagement@${account}.service

[Install]
WantedBy=timers.target
EOF

  # Planer: Sonntag 08:00
  write_timer "ig-planner" "$account" "Sun *-*-* 08:00:00"

  # Alle Timer aktivieren
  for svc in ig-feed ig-story ig-reel ig-engagement ig-planner; do
    systemctl enable "${svc}@${account}.timer"
    systemctl start  "${svc}@${account}.timer"
  done

  echo "✓ $account — alle Timer aktiv"
done

systemctl daemon-reload
echo ""
echo "Alle Timer installiert. Status-Übersicht:"
systemctl list-timers | grep "ig-"
