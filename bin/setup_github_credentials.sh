#!/usr/bin/env bash
set -euo pipefail
source "$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ENV_FILE="$TOOLS_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'EOF'
# GitHub identity used by setup_github_credentials.sh
GITHUB_USERNAME=
GITHUB_EMAIL=
GITHUB_SSH_PRIVATE_KEY=
GITHUB_SSH_PUBLIC_KEY=
EOF
    chmod 600 "$ENV_FILE" 2>/dev/null || true
    echo -e "${YELLOW}Created ${ENV_FILE}. Fill in the GitHub values and run again.${NC}"
    exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${GITHUB_USERNAME:?Missing GITHUB_USERNAME in $ENV_FILE}"
: "${GITHUB_EMAIL:?Missing GITHUB_EMAIL in $ENV_FILE}"
: "${GITHUB_SSH_PRIVATE_KEY:?Missing GITHUB_SSH_PRIVATE_KEY in $ENV_FILE}"
: "${GITHUB_SSH_PUBLIC_KEY:?Missing GITHUB_SSH_PUBLIC_KEY in $ENV_FILE}"

target_input="${1:-}"
if [ -z "$target_input" ]; then
    read -r -p "Target folder (default: ${PROJECT_DIR}): " target_input
    target_input="${target_input:-$PROJECT_DIR}"
fi

# Expand home shorthand for convenience.
if [[ "$target_input" == "~" ]]; then
    target_input="$HOME"
elif [[ "$target_input" == "~/"* ]]; then
    target_input="$HOME/${target_input#~/}"
fi

if ! target_dir="$(cd "$target_input" 2>/dev/null && pwd)"; then
    echo -e "${RED}Folder does not exist: ${target_input}${NC}"
    exit 1
fi

if ! git -C "$target_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "${RED}${target_dir} is not a Git repository.${NC}"
    exit 1
fi

if [ ! -f "$GITHUB_SSH_PRIVATE_KEY" ]; then
    echo -e "${RED}Missing SSH private key: ${GITHUB_SSH_PRIVATE_KEY}${NC}"
    exit 1
fi

if [ ! -f "$GITHUB_SSH_PUBLIC_KEY" ]; then
    echo -e "${RED}Missing SSH public key: ${GITHUB_SSH_PUBLIC_KEY}${NC}"
    exit 1
fi

ssh_command="ssh -i ${GITHUB_SSH_PRIVATE_KEY} -o IdentitiesOnly=yes"

echo -e "${CYAN}Applying GitHub credentials in ${target_dir}...${NC}"

# Set repo-local values so this folder always uses these credentials.
git -C "$target_dir" config --local user.name "$GITHUB_USERNAME"
git -C "$target_dir" config --local user.email "$GITHUB_EMAIL"
git -C "$target_dir" config --local credential.username "$GITHUB_USERNAME"
git -C "$target_dir" config --local core.sshCommand "$ssh_command"

# If origin uses https://github.com, switch it to SSH so the configured key is used.
origin_url="$(git -C "$target_dir" remote get-url origin 2>/dev/null || true)"
if [ -n "$origin_url" ]; then
    case "$origin_url" in
        https://github.com/*)
            repo_path="${origin_url#https://github.com/}"
            repo_path="${repo_path%.git}"
            git -C "$target_dir" remote set-url origin "git@github.com:${repo_path}.git"
            echo -e "${GREEN}Updated origin remote to SSH.${NC}"
            ;;
        http://github.com/*)
            repo_path="${origin_url#http://github.com/}"
            repo_path="${repo_path%.git}"
            git -C "$target_dir" remote set-url origin "git@github.com:${repo_path}.git"
            echo -e "${GREEN}Updated origin remote to SSH.${NC}"
            ;;
    esac
fi

echo -e "${GREEN}GitHub credentials configured for ${target_dir}.${NC}"
echo "user.name=$(git -C "$target_dir" config --local --get user.name)"
echo "user.email=$(git -C "$target_dir" config --local --get user.email)"
echo "credential.username=$(git -C "$target_dir" config --local --get credential.username)"
echo "core.sshCommand=$(git -C "$target_dir" config --local --get core.sshCommand)"
