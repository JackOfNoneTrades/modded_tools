#!/usr/bin/env python3
"""
Transform a GitHub README to be compatible with Modrinth/CurseForge.

Converts local image paths to raw GitHub URLs so images display correctly
on external platforms that don't have access to the repository files.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote


def get_git_remote_url() -> Optional[str]:
    """Get the GitHub repository URL from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output to find origin (or first remote)
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # Format: "origin  git@github.com:user/repo.git (fetch)"
            # or:     "origin  https://github.com/user/repo.git (fetch)"
            parts = line.split()
            if len(parts) >= 2 and "(fetch)" in line:
                return parts[1]
        
        # If no fetch found, try any remote
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
                    
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        print("Error: git is not installed or not in PATH", file=sys.stderr)
        return None
    
    return None


def parse_github_url(remote_url: str) -> Optional[Tuple[str, str]]:
    """
    Parse a GitHub remote URL to extract owner and repo name.
    
    Handles:
    - git@github.com:owner/repo.git
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo
    """
    # SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$", remote_url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)
    
    # HTTPS format: https://github.com/owner/repo.git
    https_match = re.match(r"https?://github\.com/([^/]+)/(.+?)(?:\.git)?$", remote_url)
    if https_match:
        return https_match.group(1), https_match.group(2)
    
    return None


def get_default_branch() -> str:
    """Get the default branch name (main, master, etc.)."""
    try:
        # Try to get the current branch first
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        branch = result.stdout.strip()
        if branch and branch != "HEAD":
            return branch
    except subprocess.CalledProcessError:
        pass
    
    # Try to detect default branch from remote
    try:
        result = subprocess.run(
            ["git", "remote", "show", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.split("\n"):
            if "HEAD branch:" in line:
                return line.split(":")[-1].strip()
    except subprocess.CalledProcessError:
        pass
    
    # Fallback to common defaults
    return "main"


def is_local_path(path: str) -> bool:
    """Check if a path is a local file path (not a URL)."""
    # Skip URLs
    if path.startswith(("http://", "https://", "//", "data:")):
        return False
    # Skip anchor links
    if path.startswith("#"):
        return False
    return True


def is_image_file(path: str) -> bool:
    """Check if the path looks like an image file."""
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp"}
    return Path(path.lower()).suffix in image_extensions


def transform_readme(content: str, owner: str, repo: str, branch: str) -> str:
    """
    Transform local image paths to GitHub raw URLs.
    
    Handles:
    - Markdown images: ![alt](path)
    - Markdown images with titles: ![alt](path "title")
    - HTML img tags: <img src="path">
    """
    base_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    
    def make_raw_url(local_path: str) -> str:
        """Convert a local path to a raw GitHub URL."""
        # Remove leading ./ if present
        clean_path = local_path.lstrip("./")
        # URL encode the path (but keep slashes)
        encoded_path = "/".join(quote(part, safe="") for part in clean_path.split("/"))
        return f"{base_url}/{encoded_path}"
    
    # Pattern for Markdown images: ![alt](path) or ![alt](path "title")
    md_image_pattern = r'(!\[[^\]]*\]\()([^)\s"]+)([^)]*\))'
    
    def replace_md_image(match):
        prefix = match.group(1)  # ![alt](
        path = match.group(2)    # the path
        suffix = match.group(3)  # optional title + )
        
        if is_local_path(path) and is_image_file(path):
            return f"{prefix}{make_raw_url(path)}{suffix}"
        return match.group(0)
    
    content = re.sub(md_image_pattern, replace_md_image, content)
    
    # Pattern for HTML img tags: <img src="path"> or <img src='path'>
    html_img_pattern = r'(<img\s+[^>]*src=["\'])([^"\']+)(["\'][^>]*>)'
    
    def replace_html_img(match):
        prefix = match.group(1)
        path = match.group(2)
        suffix = match.group(3)
        
        if is_local_path(path) and is_image_file(path):
            return f"{prefix}{make_raw_url(path)}{suffix}"
        return match.group(0)
    
    content = re.sub(html_img_pattern, replace_html_img, content, flags=re.IGNORECASE)
    
    return content


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Transform a GitHub README for Modrinth/CurseForge compatibility"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="README.md",
        help="Input README file (default: README.md)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: print to stdout)"
    )
    parser.add_argument(
        "-b", "--branch",
        help="Git branch name (default: auto-detect)"
    )
    parser.add_argument(
        "--repo",
        help="Override repository in format 'owner/repo'"
    )
    
    args = parser.parse_args()
    
    # Get repository info
    if args.repo:
        if "/" not in args.repo:
            print("Error: --repo must be in format 'owner/repo'", file=sys.stderr)
            sys.exit(1)
        owner, repo = args.repo.split("/", 1)
    else:
        remote_url = get_git_remote_url()
        if not remote_url:
            print("Error: Could not determine git remote URL", file=sys.stderr)
            print("Make sure you're in a git repository with a remote configured,", file=sys.stderr)
            print("or use --repo owner/repo to specify manually.", file=sys.stderr)
            sys.exit(1)
        
        parsed = parse_github_url(remote_url)
        if not parsed:
            print(f"Error: Could not parse GitHub URL from: {remote_url}", file=sys.stderr)
            print("Use --repo owner/repo to specify manually.", file=sys.stderr)
            sys.exit(1)
        
        owner, repo = parsed
    
    # Get branch
    branch = args.branch or get_default_branch()
    
    # Read input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    content = input_path.read_text(encoding="utf-8")
    
    # Transform
    transformed = transform_readme(content, owner, repo, branch)
    
    # Output
    if args.output:
        Path(args.output).write_text(transformed, encoding="utf-8")
        print(f"Transformed README written to: {args.output}", file=sys.stderr)
    else:
        print(transformed)
    
    # Print info
    # print(f"\n# Repository: {owner}/{repo}", file=sys.stderr)
    # print(f"# Branch: {branch}", file=sys.stderr)


if __name__ == "__main__":
    main()
