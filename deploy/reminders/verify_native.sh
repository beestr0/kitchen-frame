#!/bin/sh
# Private native TTY only. No account credentials in arguments, output logs or chat.
set -eu
cd /home/hub/pf1007l-reminders-stage.LEZsOd
printf '%s\n' 'Verify existing private HTTPS; preserve all installed components and data.'
sudo -k -p 'PF1007L HTTPS verification sudo password (hidden): ' -- python3 ./verify_https.py --show-account
