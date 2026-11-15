#!/bin/bash
set -euo pipefail
OLD="$HOME/Downloads/JobRadar_v1.0"
PLIST="$HOME/Library/LaunchAgents/com.alihan.jobradar.hourly.plist"
printf 'DELETE old JobRadar v1 including its database and output?\nExact paths:\n%s\n%s\n' "$OLD" "$PLIST"
read -r -p 'Type DELETE V1 to proceed: ' C
if [ "$C" != 'DELETE V1' ];then echo 'Cancelled. Nothing removed.';exit 1;fi
if [ -f "$PLIST" ];then launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true;rm -- "$PLIST";fi
if [ -L "$OLD" ];then echo 'Refusing symlink';exit 2;fi
if [ -d "$OLD" ];then rm -rf -- "$OLD";echo 'v1 folder removed';fi
if [ -f "$HOME/Downloads/JobRadar_v1.0_macOS.zip" ];then read -r -p 'Also remove old ZIP? Type YES: ' Z;if [ "$Z" = 'YES' ];then rm -- "$HOME/Downloads/JobRadar_v1.0_macOS.zip";fi;fi
echo 'v2 files are untouched.'
