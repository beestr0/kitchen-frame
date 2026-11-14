#!/bin/sh
set -eu
cd /home/hub/pf1007l-reminders-stage.LEZsOd
sudo -k -p 'PF1007L demo integration sudo password (hidden): ' -- /opt/pf1007l-reminders-demo/venv/bin/python ./pilot_session.py
