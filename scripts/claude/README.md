# Claude Code Scripts

Utility scripts for managing Claude Code plans and integration.

## Scripts

### import-plan

Import Claude Code plans from `~/.claude/plans/` to `docs/plans/`.

**Project-aware:** By default, only imports plans that contain "AI Universal Suite" in their content.

```bash
# Windows
import-plan.bat [latest|all|any|filename]

# macOS/Linux (Git Bash on Windows)
./import-plan.sh [latest|all|any|filename]
```

**Options:**
- `latest` (default) - Import the most recent plan **for this project**
- `all` - Import all plans for this project that haven't been imported yet
- `any` - Import the most recent plan regardless of project
- `<filename>` - Import a specific plan by name

**Example:**
```bash
# Import the most recent AI Universal Suite plan
import-plan.bat

# Import all AI Universal Suite plans
import-plan.bat all

# Import the most recent plan (any project)
import-plan.bat any

# Import a specific plan
import-plan.bat luminous-humming-moth.md
```

Plans are automatically renamed with a standard prefix and date:
- `compressed-nibbling-goose.md` → `claude-plan_01-18-26.md`

### list-plans

List available plans in Claude's directory or local project.

```bash
# Windows
list-plans.bat [claude|local|both]

# macOS/Linux
./list-plans.sh [claude|local|both]
```

**Options:**
- `claude` (default) - Show plans in `~/.claude/plans/`
- `local` - Show plans in `docs/plans/`
- `both` - Show both locations

## Auto-Import Hook

A PostToolUse hook is configured in `~/.claude/settings.json` that automatically copies plans to `docs/plans/` when you exit plan mode. The hook:

1. Triggers on `ExitPlanMode` tool use
2. Finds the most recently modified plan in `~/.claude/plans/`
3. Copies it to `./docs/plans/` with format `claude-plan_MM-DD-YY.md`

**Note:** The auto-hook imports the globally latest plan (not project-filtered). Use the manual import script if you need project-specific filtering.

## Plan Naming Convention

Imported plans follow this naming pattern:
```
claude-plan_MM-DD-YY.md
```

Where:
- `claude-plan` is the standard prefix
- `MM-DD-YY` is the file modification date

If a file with the same name already exists, a counter or timestamp is appended.

## Customizing for Other Projects

To use these scripts in another project:

1. Copy the `scripts/claude/` folder to your project
2. Edit the variables in the scripts:
   - `PROJECT_NAME` - used to filter plans by content (e.g., "AI Universal Suite")
   - `FILE_PREFIX` - the filename prefix (e.g., "claude-plan")
3. Create a `docs/plans/` directory in your project
