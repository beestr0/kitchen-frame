#!/bin/sh
# Run on Mint in a native SSH TTY. No transcript, logging or password piping.
set -eu
cd /home/hub/pf1007l-reminders-stage.LEZsOd
printf '%s\n' 'PF1007L: connected using persistent SSH; requesting Linux sudo below.'
sudo -k -p 'PF1007L Mint sudo password (hidden): ' -- python3 ./resume_demo.py
