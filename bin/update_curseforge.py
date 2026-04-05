#!/usr/bin/env python3
"""
Update CurseForge project description from transform_readme.py output.

Usage:
    python update_curseforge.py --cookies-from-browser firefox
    python update_curseforge.py --project-id 1449057 --cookies-from-browser firefox
    python update_curseforge.py -b firefox:/path/to/profile

If --project-id is not specified, reads curseForgeProjectId from gradle.properties.
"""

import argparse
import configparser
import os
import subprocess
import sys
from pathlib import Path

import browser_cookie3
import markdown
import requests


def find_firefox_cookies_file(base_path: str) -> str:
    """
    Find cookies.sqlite for Firefox-based browsers.
    
    Handles:
    - Direct path to cookies.sqlite
    - Path to profile directory (contains cookies.sqlite)
    - Path to browser data directory (contains profiles.ini)
    """
    path = Path(base_path)
    
    # If it's directly the cookies file
    if path.is_file() and path.name == "cookies.sqlite":
        return str(path)
    
    # If it's a profile directory containing cookies.sqlite
    cookies_in_dir = path / "cookies.sqlite"
    if cookies_in_dir.is_file():
        return str(cookies_in_dir)
    
    # If it's a browser data directory with profiles.ini
    profiles_ini = path / "profiles.ini"
    if profiles_ini.is_file():
        config = configparser.ConfigParser()
        config.read(profiles_ini)
        
        # Find the default profile from [Install*] section first (more reliable)
        # These paths are always relative to the base path
        default_profile_path = None
        for section in config.sections():
            if section.startswith("Install"):
                if config.has_option(section, "Default"):
                    default_profile_path = config.get(section, "Default")
                    break
        
        # Fallback to Profile sections
        is_relative = True  # Default to relative
        if not default_profile_path:
            for section in config.sections():
                if section.startswith("Profile"):
                    if config.has_option(section, "Default") and config.get(section, "Default") == "1":
                        default_profile_path = config.get(section, "Path")
                        is_relative = config.get(section, "IsRelative", "1") == "1"
                        break
            
            # If still not found, use first profile
            if not default_profile_path:
                for section in config.sections():
                    if section.startswith("Profile") and config.has_option(section, "Path"):
                        default_profile_path = config.get(section, "Path")
                        is_relative = config.get(section, "IsRelative", "1") == "1"
                        break
        
        if default_profile_path:
            # Paths from Install* sections and most Profile sections are relative
            if is_relative or not Path(default_profile_path).is_absolute():
                profile_dir = path / default_profile_path
            else:
                profile_dir = Path(default_profile_path)
            
            cookies_file = profile_dir / "cookies.sqlite"
            if cookies_file.is_file():
                return str(cookies_file)
            else:
                raise FileNotFoundError(f"cookies.sqlite not found in profile: {profile_dir}")
    
    # Check Profiles subdirectory (some browsers use this)
    profiles_dir = path / "Profiles"
    if profiles_dir.is_dir():
        # Try to find any profile with cookies
        for profile in profiles_dir.iterdir():
            if profile.is_dir():
                cookies_file = profile / "cookies.sqlite"
                if cookies_file.is_file():
                    return str(cookies_file)
    
    raise FileNotFoundError(
        f"Could not find cookies.sqlite in: {base_path}\n"
        f"Try providing the full path to the profile directory or cookies.sqlite file."
    )


def get_browser_cookies(browser_spec: str) -> dict:
    """
    Extract cookies from browser, similar to yt-dlp's --cookies-from-browser.
    
    Format: browser_name or browser_name:/path/to/profile
    Supported browsers: chrome, firefox, edge, opera, brave, chromium
    
    For Firefox-based browsers (including Waterfox, LibreWolf, etc.), the path can be:
    - Path to cookies.sqlite file
    - Path to profile directory (e.g., ~/.mozilla/firefox/xxxxx.default)
    - Path to browser data directory (e.g., ~/Library/Application Support/Waterfox)
    """
    parts = browser_spec.split(":", 1)
    browser_name = parts[0].lower()
    profile_path = parts[1] if len(parts) > 1 else None
    
    browser_funcs = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "edge": browser_cookie3.edge,
        "opera": browser_cookie3.opera,
        "brave": browser_cookie3.brave,
        "chromium": browser_cookie3.chromium,
    }
    
    if browser_name not in browser_funcs:
        raise ValueError(f"Unsupported browser: {browser_name}. Supported: {', '.join(browser_funcs.keys())}")
    
    browser_func = browser_funcs[browser_name]
    
    # Get cookie jar from browser
    if profile_path:
        # For Firefox-based browsers, resolve the cookies file path
        if browser_name == "firefox":
            resolved_path = find_firefox_cookies_file(profile_path)
            cookie_jar = browser_func(cookie_file=resolved_path)
        else:
            cookie_jar = browser_func(cookie_file=profile_path)
    else:
        cookie_jar = browser_func()
    
    # Extract only curseforge.com cookies
    cookies = {}
    for cookie in cookie_jar:
        if "curseforge.com" in cookie.domain:
            cookies[cookie.name] = cookie.value
    
    return cookies


def get_readme_markdown() -> str:
    """Run transform_readme.py and capture its stdout."""
    transform_script = Path(__file__).resolve().with_name("transform_readme.py")
    result = subprocess.run(
        [sys.executable, str(transform_script)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def get_project_id_from_gradle() -> int | None:
    """
    Extract CurseForge project ID from gradle.properties in current directory.
    
    Looks for a line like: curseForgeProjectId = 1449057
    """
    gradle_props = Path("gradle.properties")
    if not gradle_props.is_file():
        return None
    
    with open(gradle_props, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("curseForgeProjectId"):
                # Handle both "key = value" and "key=value" formats
                if "=" in line:
                    value = line.split("=", 1)[1].strip()
                    try:
                        return int(value)
                    except ValueError:
                        return None
    return None


def markdown_to_curseforge_html(md_text: str) -> str:
    """
    Convert markdown to HTML and format for CurseForge API.
    
    - Convert markdown to HTML
    - Escape double quotes
    - Replace newlines with \n (for JSON serialization)
    """
    # Convert markdown to HTML
    html = markdown.markdown(
        md_text,
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )
    
    # Add rel and target attributes to links (like CurseForge does)
    # This is a simple replacement - for complex cases, use BeautifulSoup
    html = html.replace("<a href=", '<a rel="noopener noreferrer" target="_blank" href=')
    
    return html


def update_curseforge_description(project_id: int, html_description: str, cookies: dict) -> requests.Response:
    """Send PUT request to update CurseForge project description."""
    
    session = requests.Session()
    
    # Set cookies
    for name, value in cookies.items():
        session.cookies.set(name, value, domain="authors.curseforge.com")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://authors.curseforge.com/",
        "Content-Type": "application/json",
        "Origin": "https://authors.curseforge.com",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0",
    }
    
    json_data = {
        "description": html_description,
        "descriptionType": 1,
    }
    
    url = f"https://authors.curseforge.com/_api/projects/description/{project_id}"
    
    response = session.put(url, headers=headers, json=json_data)
    
    return response


def main():
    parser = argparse.ArgumentParser(
        description="Update CurseForge project description from transform_readme.py output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --cookies-from-browser firefox
    %(prog)s --project-id 1449057 --cookies-from-browser firefox
    %(prog)s -p 1449057 -b chrome:/path/to/profile
    %(prog)s -b firefox --dry-run

If --project-id is not specified, the script will try to read it from
gradle.properties in the current directory (curseForgeProjectId = ...).
        """,
    )
    parser.add_argument(
        "-p", "--project-id",
        type=int,
        default=None,
        help="CurseForge project ID (default: read from gradle.properties)",
    )
    parser.add_argument(
        "-b", "--cookies-from-browser",
        type=str,
        required=True,
        metavar="BROWSER[:PATH]",
        help="Browser to extract cookies from (chrome, firefox, edge, opera, brave, chromium). "
             "Optionally specify profile path after colon.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the HTML that would be sent without making the request",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose output",
    )
    
    args = parser.parse_args()
    
    # Get project ID from args or gradle.properties
    project_id = args.project_id
    if project_id is None:
        project_id = get_project_id_from_gradle()
        if project_id is None:
            print("Error: No project ID specified and could not find curseForgeProjectId in gradle.properties", file=sys.stderr)
            sys.exit(1)
        if args.verbose:
            print(f"Using project ID {project_id} from gradle.properties", file=sys.stderr)
    
    # Get markdown from transform_readme.py
    if args.verbose:
        print("Running transform_readme.py...", file=sys.stderr)
    
    try:
        md_text = get_readme_markdown()
    except subprocess.CalledProcessError as e:
        print(f"Error running transform_readme.py: {e}", file=sys.stderr)
        print(f"stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: transform_readme.py not found in PATH", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"Got {len(md_text)} characters of markdown", file=sys.stderr)
    
    # Convert to HTML
    html = markdown_to_curseforge_html(md_text)
    
    if args.verbose:
        print(f"Converted to {len(html)} characters of HTML", file=sys.stderr)
    
    if args.dry_run:
        print("=== HTML Output (dry run) ===")
        print(html)
        print("=== End HTML Output ===")
        return
    
    # Get browser cookies
    if args.verbose:
        print(f"Extracting cookies from {args.cookies_from_browser}...", file=sys.stderr)
    
    try:
        cookies = get_browser_cookies(args.cookies_from_browser)
    except Exception as e:
        print(f"Error extracting cookies: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not cookies:
        print("Warning: No CurseForge cookies found in browser", file=sys.stderr)
    elif args.verbose:
        print(f"Found {len(cookies)} CurseForge cookies", file=sys.stderr)
    
    # Update CurseForge
    if args.verbose:
        print(f"Updating project {project_id}...", file=sys.stderr)
    
    response = update_curseforge_description(project_id, html, cookies)
    
    if response.ok:
        print(f"Successfully updated project {project_id}")
        if args.verbose:
            print(f"Response: {response.status_code} {response.reason}", file=sys.stderr)
    else:
        print(f"Error updating project: {response.status_code} {response.reason}", file=sys.stderr)
        print(f"Response body: {response.text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
