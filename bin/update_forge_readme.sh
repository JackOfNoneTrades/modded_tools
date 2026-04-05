#!/usr/bin/env bash
set -euo pipefail
source "$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
cd "$PROJECT_DIR"

# Load .env from tools directory
if [ -f "$TOOLS_DIR/.env" ]; then
    set -a
    source "$TOOLS_DIR/.env"
    set +a
fi

cookies_source="${1:-${CURSEFORGE_COOKIES_FROM_BROWSER:-firefox}}"
"$PYTHON" "$TOOLS_DIR/bin/update_curseforge.py" --cookies-from-browser "$cookies_source"
