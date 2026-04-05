#!/usr/bin/env bash
set -euo pipefail
source "$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
cd "$PROJECT_DIR"

if [ "$#" -gt 0 ]; then
    # Pass through custom args directly when provided.
    "$PYTHON" "$TOOLS_DIR/bin/lang_manager.py" "$@"
    exit 0
fi

default_folder="${LANGMANAGER_FOLDER:-}"
if [ -z "$default_folder" ] && [ -d "src/main/resources/assets" ]; then
    default_folder="$(find src/main/resources/assets -type d -name lang | head -n 1 || true)"
fi
default_model="${LANGMANAGER_MODEL:-en_US.lang}"
default_mode="${LANGMANAGER_MODE:-apply}"

if [ -n "$default_folder" ]; then
    read -r -p "Lang folder (default: ${default_folder}): " folder
    folder="${folder:-$default_folder}"
else
    read -r -p "Lang folder: " folder
fi

if [ -z "$folder" ]; then
    echo -e "${RED}No lang folder provided.${NC}"
    exit 1
fi

if [ ! -d "$folder" ]; then
    echo -e "${RED}Lang folder does not exist: ${folder}${NC}"
    exit 1
fi

read -r -p "Model lang file (default: ${default_model}): " model
model="${model:-$default_model}"

if [ -z "$model" ]; then
    echo -e "${RED}No model file provided.${NC}"
    exit 1
fi

mode=0
if [ "$default_mode" = "gui" ]; then
    select_option "GUI" "Apply To All (Headless)" || mode=$?
else
    select_option "Apply To All (Headless)" "GUI" || mode=$?
fi

cmd=("$PYTHON" "$TOOLS_DIR/bin/lang_manager.py" --folder "$folder" --model "$model")
if [ "$mode" -eq 0 ] && [ "$default_mode" != "gui" ]; then
    cmd+=(--apply)
elif [ "$mode" -eq 1 ] && [ "$default_mode" = "gui" ]; then
    cmd+=(--apply)
fi

"${cmd[@]}"
