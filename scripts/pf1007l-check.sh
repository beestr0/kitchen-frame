#!/usr/bin/env bash
# Read-only PF1007L checks for Codex CLI on macOS; never installs or changes device settings.
set -euo pipefail
command -v adb >/dev/null || { echo 'Install ADB on the Mac: brew install --cask android-platform-tools' >&2; exit 1; }
args=()
if [[ -n "${ANDROID_SERIAL:-}" ]]; then args=(-s "$ANDROID_SERIAL"); fi
# adb itself refuses to select a target if multiple devices are connected.
[[ "$(adb "${args[@]}" get-state)" == device ]] || { echo 'Authorize USB debugging on the frame, then retry.' >&2; exit 1; }
for prop in ro.product.model ro.product.board ro.build.version.release ro.build.version.sdk ro.product.cpu.abi; do
  printf '%s: ' "$prop"
  adb "${args[@]}" shell getprop "$prop"
done
adb "${args[@]}" shell wm size
adb "${args[@]}" shell wm density
adb "${args[@]}" shell date
# Android 6 may not expose webviewupdate; package version remains useful evidence.
adb "${args[@]}" shell dumpsys webviewupdate || true
adb "${args[@]}" shell dumpsys package com.google.android.webview | sed -n '/versionName=/p'
adb "${args[@]}" shell dumpsys package com.android.webview | sed -n '/versionName=/p'
printf 'Read-only checks complete. No APK, settings, firmware, or app data changed.\n'
