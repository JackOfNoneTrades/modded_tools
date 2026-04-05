#!/usr/bin/env bash
# Shared functions and constants for ModdedTools scripts

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Resolve TOOLS_DIR (the ModdedTools root) from this script's location
TOOLS_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$TOOLS_DIR/venv/bin/python3"
CACHE_DIR="$TOOLS_DIR/cache"
# PROJECT_DIR defaults to cwd; override with env var if needed
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"

# Interactive arrow-key menu. Returns selected index via $?.
# Usage: select_option "opt1" "opt2" "opt3"; choice=$?
# All UI output goes to /dev/tty so the menu works inside $() command substitutions.
function select_option {
    local ESC key idx selected option_count
    ESC=$(printf "\033")

    option_count=$#
    selected=0

    # Reserve lines for the menu once, then redraw in place.
    for _ in "$@"; do
        printf "\n" >/dev/tty
    done

    trap 'printf "%b[?25h\n" "'"$ESC"'" >/dev/tty; stty echo; exit' INT
    printf "%b[?25l" "$ESC" >/dev/tty

    while true; do
        # Move up by number of options and redraw all lines.
        printf "%b[%dA" "$ESC" "$option_count" >/dev/tty

        idx=0
        for option in "$@"; do
            if [ "$idx" -eq "$selected" ]; then
                # Clear line, then print highlighted option
                printf "%b[2K  %b[7m %s %b[27m\n" "$ESC" "$ESC" "$option" "$ESC" >/dev/tty
            else
                printf "%b[2K   %s\n" "$ESC" "$option" >/dev/tty
            fi
            idx=$((idx + 1))
        done

        # Read up/down/enter from terminal
        IFS= read -rsn3 key </dev/tty 2>/dev/null || key=""

        if [[ "$key" == "$ESC[A" ]]; then
            selected=$((selected - 1))
            if [ "$selected" -lt 0 ]; then
                selected=$((option_count - 1))
            fi
        elif [[ "$key" == "$ESC[B" ]]; then
            selected=$((selected + 1))
            if [ "$selected" -ge "$option_count" ]; then
                selected=0
            fi
        else
            break
        fi
    done

    printf "%b[?25h\n" "$ESC" >/dev/tty
    return "$selected"
}

select_java_task_suffix() {
    local prompt="${RUN_JAVA_PROMPT:-1}"
    local version="${RUN_JAVA_VERSION:-}"

    if [ "$prompt" = "0" ] || [ "$prompt" = "false" ]; then
        version="${version:-25}"
    else
        echo "Select Java version:" >/dev/tty
        local java_choice=0
        select_option "Java 25 (default)" "Java 21" "Java 17" "Java 8" || java_choice=$?

        case "$java_choice" in
            0) version="25" ;;
            1) version="21" ;;
            2) version="17" ;;
            3) version="8" ;;
            *) version="25" ;;
        esac
    fi

    if [ -z "$version" ]; then
        version="25"
    fi

    case "$version" in
        25) echo "25" ;;
        21) echo "21" ;;
        17) echo "17" ;;
        8) echo "" ;;
        *)
            echo -e "${RED}Invalid Java version '${version}'. Expected 8, 17, 21, or 25.${NC}" >&2
            return 1
            ;;
    esac
}
