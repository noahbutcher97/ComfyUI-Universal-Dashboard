#!/bin/bash
# MacOS Double-Click Launcher
# This extension (.command) is recognized by Finder as executable.

# 1. Navigate to the directory where this file is located
cd "$(dirname "$0")"

# 2. Ensure the underlying script is executable (fixes permission issues from zips)
chmod +x ./start_dashboard.sh

# 3. Run it
./start_dashboard.sh
