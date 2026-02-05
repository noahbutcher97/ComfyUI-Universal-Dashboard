#!/bin/bash

# List available Claude Code plans
# Usage: list-plans.sh [claude|local|both]
#   claude - Show plans in ~/.claude/plans (default)
#   local  - Show plans in docs/plans
#   both   - Show both locations

CLAUDE_PLANS="$HOME/.claude/plans"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_PLANS="$SCRIPT_DIR/../../docs/plans"
MODE="${1:-claude}"

list_claude() {
    echo "=== Claude Code Plans ($CLAUDE_PLANS) ==="
    if [ -d "$CLAUDE_PLANS" ]; then
        for file in "$CLAUDE_PLANS"/*.md; do
            if [ -f "$file" ]; then
                echo "  $(basename "$file")"
            fi
        done
    else
        echo "  (directory not found)"
    fi
}

list_local() {
    echo "=== Local Plans ($LOCAL_PLANS) ==="
    if [ -d "$LOCAL_PLANS" ]; then
        for file in "$LOCAL_PLANS"/*.md; do
            if [ -f "$file" ]; then
                echo "  $(basename "$file")"
            fi
        done
    else
        echo "  (directory not found)"
    fi
}

case "$MODE" in
    claude)
        list_claude
        ;;
    local)
        list_local
        ;;
    both)
        list_claude
        echo ""
        list_local
        ;;
    *)
        echo "Usage: list-plans.sh [claude|local|both]"
        exit 1
        ;;
esac
