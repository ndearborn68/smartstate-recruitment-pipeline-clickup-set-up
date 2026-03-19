#!/bin/bash
# SmartState — Install macOS Launch Agents
# Run this once to activate the schedulers.

PLIST_DIR="$HOME/Library/LaunchAgents"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing SmartState launchd agents..."

# Copy plists to LaunchAgents
cp "$SCRIPT_DIR/com.smartstate.replies.plist" "$PLIST_DIR/"
cp "$SCRIPT_DIR/com.smartstate.performance.plist" "$PLIST_DIR/"

# Unload first if already loaded (ignore errors)
launchctl unload "$PLIST_DIR/com.smartstate.replies.plist" 2>/dev/null
launchctl unload "$PLIST_DIR/com.smartstate.performance.plist" 2>/dev/null

# Load agents
launchctl load "$PLIST_DIR/com.smartstate.replies.plist"
launchctl load "$PLIST_DIR/com.smartstate.performance.plist"

echo ""
echo "✅ Installed:"
echo "   com.smartstate.replies    — runs every 15 minutes"
echo "   com.smartstate.performance — runs Mon/Wed/Fri at 8:00 AM"
echo ""
echo "Logs:"
echo "   Replies:     tail -f /tmp/smartstate_replies.log"
echo "   Performance: tail -f /tmp/smartstate_performance.log"
echo ""
echo "To uninstall:"
echo "   launchctl unload ~/Library/LaunchAgents/com.smartstate.replies.plist"
echo "   launchctl unload ~/Library/LaunchAgents/com.smartstate.performance.plist"
