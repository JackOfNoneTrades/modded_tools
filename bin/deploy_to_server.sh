#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

ENV_FILE="$TOOLS_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}ERROR: .env file not found at $ENV_FILE${NC}" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${DEPLOY_KEY:?DEPLOY_KEY not set in .env}"
: "${DEPLOY_PATH:?DEPLOY_PATH not set in .env}"

GRADLE_PROPS="$PROJECT_DIR/gradle.properties"
if [[ ! -f "$GRADLE_PROPS" ]]; then
    echo -e "${RED}ERROR: gradle.properties not found in $PROJECT_DIR${NC}" >&2
    exit 1
fi

MOD_ID="$(grep -E '^modId[[:space:]]*=' "$GRADLE_PROPS" | head -1 | sed -E 's/^modId[[:space:]]*=[[:space:]]*//' | tr -d '\r')"

if [[ -z "$MOD_ID" ]]; then
    echo -e "${RED}ERROR: could not determine modId from gradle.properties${NC}" >&2
    exit 1
fi

VERSION="${VERSION:-testerino}"
ARTIFACT="build/libs/${MOD_ID}-${VERSION}.jar"

if [[ ! -f "$PROJECT_DIR/$ARTIFACT" ]]; then
    echo -e "${RED}ERROR: artifact not found: $PROJECT_DIR/$ARTIFACT${NC}" >&2
    echo -e "${YELLOW}Build the mod first (with VERSION=$VERSION).${NC}" >&2
    exit 1
fi

# Expand ~ in DEPLOY_KEY
KEY="${DEPLOY_KEY/#\~/$HOME}"

echo -e "${GREEN}Deploying $ARTIFACT to $DEPLOY_PATH${NC}"
scp -i "$KEY" "$PROJECT_DIR/$ARTIFACT" "$DEPLOY_PATH"
echo -e "${GREEN}Done!${NC}"
