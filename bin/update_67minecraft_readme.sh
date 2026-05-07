#!/usr/bin/env bash
set -euo pipefail
source "$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
cd "$PROJECT_DIR"

"$PYTHON" "$TOOLS_DIR/bin/update_67minecraft.py" "$@"
