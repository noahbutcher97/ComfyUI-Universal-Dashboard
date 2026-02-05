#!/bin/bash

# Import Claude Code plans to docs/plans/
# Usage: import-plan.sh [latest|all|any|filename]
#   latest  - Import most recent plan for THIS PROJECT (default)
#   all     - Import all plans for this project
#   any     - Import most recent plan regardless of project
#   <name>  - Import specific plan by filename
#
# Project detection: Searches plan content for "AI Universal Suite"
# Output format: claude-plan_MM-DD-YY.md

CLAUDE_PLANS="$HOME/.claude/plans"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$SCRIPT_DIR/../../docs/plans"
PROJECT_NAME="AI Universal Suite"
FILE_PREFIX="claude-plan"
MODE="${1:-latest}"

# Ensure target directory exists
mkdir -p "$TARGET_DIR"

# Check if source directory exists
if [ ! -d "$CLAUDE_PLANS" ]; then
    echo "Error: Claude plans directory not found at $CLAUDE_PLANS"
    exit 1
fi

process_file() {
    local srcfile="$1"
    local srcname=$(basename "$srcfile")

    # Get file modification date (MM-DD-YY format)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local filedate=$(stat -f %Sm -t %m-%d-%y "$srcfile" 2>/dev/null)
    else
        local filedate=$(date -r "$srcfile" +%m-%d-%y 2>/dev/null)
    fi

    # Format: PROJECTNAME_DATE.md
    local destname="${FILE_PREFIX}_${filedate}.md"
    local destpath="$TARGET_DIR/$destname"

    # Check if destination already exists - add counter if so
    local counter=0
    while [ -f "$destpath" ]; do
        ((counter++))
        destname="${FILE_PREFIX}_${filedate}_${counter}.md"
        destpath="$TARGET_DIR/$destname"
    done

    cp "$srcfile" "$destpath"
    echo "Imported: $srcname -> $destname"
}

import_latest_project() {
    echo "Searching for most recent \"$PROJECT_NAME\" plan..."
    local latest=""

    # Find plans containing project name, sorted by modification time (newest first)
    for file in $(ls -t "$CLAUDE_PLANS"/*.md 2>/dev/null); do
        if grep -qi "$PROJECT_NAME" "$file" 2>/dev/null; then
            latest="$file"
            echo "Found: $(basename "$file")"
            break
        fi
    done

    if [ -z "$latest" ]; then
        echo "No plans found for \"$PROJECT_NAME\""
        echo ""
        echo "Available plans:"
        ls -1 "$CLAUDE_PLANS"/*.md 2>/dev/null | xargs -n1 basename
        echo ""
        echo "Use \"./import-plan.sh any\" to import any plan regardless of project"
        exit 1
    fi

    process_file "$latest"
}

import_latest_any() {
    echo "Importing most recent Claude plan (any project)..."
    local latest=$(ls -t "$CLAUDE_PLANS"/*.md 2>/dev/null | head -1)

    if [ -z "$latest" ]; then
        echo "No plans found in $CLAUDE_PLANS"
        exit 1
    fi

    process_file "$latest"
}

import_all_project() {
    echo "Importing all \"$PROJECT_NAME\" plans..."
    local count=0

    for file in $(ls -t "$CLAUDE_PLANS"/*.md 2>/dev/null); do
        if grep -qi "$PROJECT_NAME" "$file" 2>/dev/null; then
            process_file "$file"
            ((count++))
        fi
    done

    echo "Imported $count plan(s) for \"$PROJECT_NAME\""
}

import_specific() {
    local filename="$1"
    local filepath="$CLAUDE_PLANS/$filename"

    # Try with .md extension if not found
    if [ ! -f "$filepath" ]; then
        filepath="$CLAUDE_PLANS/${filename}.md"
    fi

    if [ ! -f "$filepath" ]; then
        echo "Error: Plan not found: $filename"
        echo ""
        echo "Available plans:"
        ls -1 "$CLAUDE_PLANS"/*.md 2>/dev/null | xargs -n1 basename
        exit 1
    fi

    process_file "$filepath"
}

case "$MODE" in
    latest)
        import_latest_project
        ;;
    all)
        import_all_project
        ;;
    any)
        import_latest_any
        ;;
    *)
        import_specific "$MODE"
        ;;
esac
