#!/bin/sh
# Diagnostic only. No passwords in args, logs or chat.
set -eu
cd /home/hub/pf1007l-reminders-stage.LEZsOd
printf '%s\n' 'Read-only CalDAV principal/home/VTODO discovery diagnostics.'
sudo -k -p 'PF1007L discovery diagnostic sudo password (hidden): ' -- python3 ./diagnose_discovery.py
