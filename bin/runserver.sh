#!/usr/bin/env bash
set -euo pipefail
source "$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
cd "$PROJECT_DIR"

echo -e "${CYAN}Run Server${NC}"

enable_debug=false
mode="${RUNSERVER_PRESET_MODE:-}"

if [ -z "$mode" ]; then
    echo "Select mode:"
    mode=0
    select_option "Normal" "Debug" || mode=$?
fi

case "$mode" in
    0)
        ;;
    1)
        enable_debug=true
        ;;
    *)
        echo -e "${RED}Invalid RUNSERVER_PRESET_MODE: ${mode}. Expected 0-1.${NC}"
        exit 1
        ;;
esac

java_suffix="$(select_java_task_suffix)" || exit 1
RUN_TASK="runServer${java_suffix}"

if [ -z "$java_suffix" ]; then
    echo -e "${GREEN}Using Gradle task ${RUN_TASK} (Java 8)${NC}"
else
    echo -e "${GREEN}Using Gradle task ${RUN_TASK} (Java ${java_suffix})${NC}"
fi

GRADLE_ARGS=()

# Ensure online-mode=false for offline
PROPS_FILE="$PROJECT_DIR/run/server/server.properties"
if [ -f "$PROPS_FILE" ]; then
    if grep -q "^online-mode=true" "$PROPS_FILE"; then
        sed -i '' 's/^online-mode=true/online-mode=false/' "$PROPS_FILE"
        echo -e "${YELLOW}Set online-mode=false in server.properties${NC}"
    fi
fi

if $enable_debug; then
    DEFAULT_DEBUG_PORT="${SERVER_DEBUG_PORT:-5006}"
    DEBUG_SUSPEND="${SERVER_DEBUG_SUSPEND:-n}"
    DEBUG_PROMPT="${SERVER_DEBUG_PROMPT:-1}"

    if [ "$DEBUG_PROMPT" = "0" ] || [ "$DEBUG_PROMPT" = "false" ]; then
        DEBUG_PORT="$DEFAULT_DEBUG_PORT"
    else
        read -p "Debug port (default: ${DEFAULT_DEBUG_PORT}): " DEBUG_PORT
        DEBUG_PORT=${DEBUG_PORT:-$DEFAULT_DEBUG_PORT}
    fi

    GRADLE_ARGS+=(--mcJvmArgs="-agentlib:jdwp=transport=dt_socket,server=y,suspend=${DEBUG_SUSPEND},address=*:${DEBUG_PORT}")
    echo -e "${YELLOW}Server debug enabled on port ${DEBUG_PORT} (suspend=${DEBUG_SUSPEND})${NC}"
fi

echo -e "${CYAN}Launching server...${NC}"
./gradlew "$RUN_TASK" ${GRADLE_ARGS[@]+"${GRADLE_ARGS[@]}"}
