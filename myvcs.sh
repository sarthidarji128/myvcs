#!/usr/bin/env bash
#
# myvcs - a tiny local version control system
# Built by Sarthi
#
# This script is the Controller: it wraps myvcs.py (the Engine) into
# a friendly command-line interface.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$SCRIPT_DIR/myvcs.py"

show_about() {
cat <<'EOF'
==================================================
  myvcs - a minimal local version control system
==================================================
  Built by  : Sarthi.
  
  A lightweight, fully local VCS engine written in
  Python and wrapped in a Bash CLI. No servers, no
  network calls - everything lives in a hidden
  .myvcs/ folder inside your project.
==================================================
EOF
}

show_help() {
cat <<EOF
Usage: myvcs <command> [args]

myvcs can track MULTIPLE folders ("projects"), each remembered by a
short name. myvcs.py/.sh can live anywhere - they don't have to sit
inside any of the folders they track.

Project management:
  setup <name> [path]    Register a project (prompts for path if omitted).
                         Also switches to it and initializes it.
  use <name>              Switch the current active project
  list                    List all configured projects (* = current)
  remove <name>           Forget a project (files on disk are untouched)
  where                   Show which project is currently active

Repo commands (act on the current project, or pass -p <name> to
target a different one without switching):
  init                        Initialize the repo (usually automatic)
  commit "message" [-p name]  Snapshot changed files
  log             [-p name]   Show commit history
  status          [-p name]   Show what's changed since the last commit
  diff <file>     [-p name]   Show a diff vs the last commit
  revert <id>     [-p name]   Restore a project to a given commit

Other:
  about                   Show info about this tool and its author
  help                    Show this help message

First-time use: just run any command and myvcs will ask you to name
and locate your first project if none is configured yet.

Examples:
  myvcs setup blog ~/projects/blog
  myvcs setup api  ~/projects/api-server
  myvcs use blog
  myvcs commit "fix typo"
  myvcs commit "bump version" -p api
  myvcs list
EOF
}

if [ ! -f "$PY" ]; then
    echo "Error: myvcs.py not found next to myvcs.sh at $SCRIPT_DIR"
    exit 1
fi

if [ "$#" -eq 0 ]; then
    show_help
    exit 0
fi

cmd="$1"
shift || true

case "$cmd" in
    about)
        show_about
        ;;
    help|-h|--help)
        show_help
        ;;
    setup|use|list|remove|where|init|commit|log|status|diff|revert)
        python3 "$PY" "$cmd" "$@"
        ;;
    *)
        echo "Unknown command: $cmd"
        show_help
        exit 1
        ;;
esac
