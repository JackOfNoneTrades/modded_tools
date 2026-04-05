#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

info() {
    echo -e "${GREEN}$1${NC}"
}

# Check for the tool's own .env file
if [[ ! -f "$ENV_FILE" ]]; then
    error ".env file not found at $ENV_FILE

Create it with:
  MAVEN_USER=your_username
  MAVEN_PASSWORD=your_password
  MAVEN_URL=https://your-maven-repo.com/releases"
fi

# Load .env file
info "Loading credentials from $ENV_FILE..."
set -a
source "$ENV_FILE"
set +a

# Validate required variables
if [[ -z "${MAVEN_USER:-}" ]]; then
    error "MAVEN_USER not set in .env"
fi

if [[ -z "${MAVEN_PASSWORD:-}" ]]; then
    error "MAVEN_PASSWORD not set in .env"
fi

if [[ -z "${MAVEN_URL:-}" ]]; then
    error "MAVEN_URL not set in .env"
fi
info "Maven URL: $MAVEN_URL"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    error "You have uncommitted changes. Commit or stash them first.
Run 'git status' to see what's changed."
fi

# Get available tags
echo ""
warn "Available tags:"
git tag --sort=-version:refname | head -10
echo ""

# Prompt for tag
read -rp "Enter the tag to publish (will be created if it doesn't exist): " TAG

if [[ -z "$TAG" ]]; then
    error "No tag specified"
fi

# Save current branch/commit to return to
ORIGINAL_REF=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse HEAD)

# Check if tag exists, create if not
if git rev-parse "$TAG" >/dev/null 2>&1; then
    info "Tag $TAG exists"
else
    warn "Tag $TAG does not exist, creating on current commit..."
    git tag "$TAG"
    info "Created tag $TAG"
fi

# Always checkout the tag so version is clean
info "Checking out tag $TAG..."
git checkout "$TAG" --quiet

# Publish
info "Publishing to Maven..."
./gradlew publishMavenPublicationToMainRepository -PmavenPublishUrl="$MAVEN_URL"

# Return to original branch
info "Returning to $ORIGINAL_REF..."
git checkout "$ORIGINAL_REF" --quiet

info "Done!"
