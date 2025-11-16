#!/usr/bin/env -S uv run --quiet -s
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Check if GitHub repositories exist for subdirectories in a given path.
Checks if repositories exist under the GitHub user 'jwdeane'.
Uses GitHub CLI (gh) for authenticated API calls to avoid rate limits.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def check_gh_installed() -> bool:
    """
    Check if GitHub CLI (gh) is installed and authenticated.

    Returns:
        True if gh is installed and authenticated, False otherwise
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_github_repo_exists(username: str, repo_name: str) -> bool:
    """
    Check if a GitHub repository exists for the given username and repo name.
    Uses GitHub CLI for authenticated API calls.

    Args:
        username: GitHub username
        repo_name: Repository name

    Returns:
        True if repository exists, False otherwise
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"/repos/{username}/{repo_name}"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return True
        else:
            if "Not Found" in result.stderr or "404" in result.stderr:
                return False
            else:
                print(f"⚠️  Unexpected error for {repo_name}: {result.stderr.strip()}")
                return False

    except subprocess.TimeoutExpired:
        print(f"✗ Timeout checking {repo_name}")
        return False
    except Exception as e:
        print(f"✗ Error checking {repo_name}: {str(e)}")
        return False


def get_authenticated_username() -> Optional[str]:
    """Return the login of the authenticated GitHub CLI user, if available."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            login = result.stdout.strip()
            return login or None
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None
    return None


def parse_paginated_json(output: str) -> List[Dict]:
    """
    Parse gh api --paginate output which concatenates JSON arrays.
    Attempts regular JSON parsing first, then splits into lines.
    """
    output = output.strip()
    if not output:
        return []

    try:
        parsed = json.loads(output)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        pass

    repos: List[Dict] = []
    normalized = output.replace("][", "]\n[")
    for chunk in normalized.splitlines():
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            data = json.loads(chunk)
        except json.JSONDecodeError as exc:
            raise exc
        if isinstance(data, list):
            repos.extend(data)
        else:
            repos.append(data)

    return repos


def get_subdirectories(path: Path) -> List[Path]:
    """
    Get all immediate subdirectories in the given path.

    Args:
        path: Path to check for subdirectories

    Returns:
        List of subdirectory paths
    """
    if not path.exists():
        return []

    return [p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")]


def get_user_repos(username: str) -> List[Dict]:
    """
    Get all repositories for a GitHub user.
    Uses the authenticated endpoint to fetch all repos.

    Args:
        username: GitHub username

    Returns:
        List of repository information dictionaries
    """
    try:
        authenticated = get_authenticated_username()
        endpoints = []

        if authenticated and authenticated.lower() == username.lower():
            endpoints.append("/user/repos")

        endpoints.append(f"/users/{username}/repos")

        errors = []

        for endpoint in endpoints:
            result = subprocess.run(
                ["gh", "api", endpoint, "--paginate"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                try:
                    return parse_paginated_json(result.stdout)
                except json.JSONDecodeError as exc:
                    print(f"✗ Error parsing repo data: {exc}")
                    return []

            errors.append(result.stderr.strip())

        print(
            "✗ Error fetching repos: "
            + " | ".join(msg for msg in errors if msg).strip()
        )
        return []

    except subprocess.TimeoutExpired:
        print("✗ Timeout fetching repos")
        return []
    except json.JSONDecodeError as e:
        print(f"✗ Error parsing repo data: {e}")
        return []
    except Exception as e:
        print(f"✗ Error fetching repos: {str(e)}")
        return []


def check_all_repos(
    directory: Path, username: str = "jwdeane", verbose: bool = False
) -> Dict[str, Dict]:
    """
    Check all subdirectories for corresponding GitHub repositories.

    Args:
        directory: Base directory to check
        username: GitHub username to check against
        verbose: Print detailed information

    Returns:
        Dictionary with repo names as keys and results as values
    """
    subdirs = get_subdirectories(directory)

    if not subdirs:
        print(f"No subdirectories found in {directory}")
        return {}

    results = {}
    total = len(subdirs)

    print(f"Checking {total} subdirectories against GitHub user '{username}'...\n")

    for idx, subdir in enumerate(sorted(subdirs), 1):
        repo_name = subdir.name
        exists = check_github_repo_exists(username, repo_name)

        results[repo_name] = {
            "exists": exists,
            "path": str(subdir),
            "url": f"https://github.com/{username}/{repo_name}" if exists else None,
        }

        if verbose or exists:
            status = "✓" if exists else "✗"
            url_part = f" → {results[repo_name]['url']}" if exists else ""
            print(f"{status} {repo_name}{url_part}")

    return results


def check_missing_local(
    directory: Path, username: str = "jwdeane", verbose: bool = False
) -> Dict[str, Dict]:
    """
    Check which GitHub repositories are NOT checked out locally.

    Args:
        directory: Base directory to check
        username: GitHub username to check against
        verbose: Print detailed information

    Returns:
        Dictionary with repo names as keys and results as values
    """
    print(f"Fetching all repositories for GitHub user '{username}'...")
    all_repos = get_user_repos(username)

    if not all_repos:
        print("No repositories found or error fetching repos")
        return {}

    local_dirs = {p.name for p in get_subdirectories(directory)}

    results = {}
    total = len(all_repos)
    missing_count = 0

    print(f"Checking {total} GitHub repositories against local directory...\n")

    for repo in sorted(all_repos, key=lambda r: r["name"]):
        repo_name = repo["name"]
        exists_locally = repo_name in local_dirs

        if not exists_locally:
            missing_count += 1

        results[repo_name] = {
            "exists_locally": exists_locally,
            "url": repo["html_url"],
            "clone_url": repo["clone_url"],
            "description": repo.get("description", ""),
        }

        if verbose or not exists_locally:
            status = "✓" if exists_locally else "✗"
            desc = (
                f" - {results[repo_name]['description']}"
                if results[repo_name]["description"]
                else ""
            )
            print(f"{status} {repo_name}{desc}")

    return results


def print_summary(results: Dict[str, Dict], username: str, inverse: bool = False):
    """Print summary of results."""
    total = len(results)

    if inverse:
        # Inverse mode: checking what's on GitHub but not local
        local_count = sum(1 for r in results.values() if r.get("exists_locally", False))
        missing_count = total - local_count

        print(f"\n{'=' * 60}")
        print(
            f"Total repos: {total} | Local: {local_count} | Not cloned: {missing_count}"
        )
        print("=" * 60)

        if missing_count > 0:
            print("\nRepositories on GitHub not cloned locally:")
            for repo_name, data in sorted(results.items()):
                if not data.get("exists_locally", False):
                    desc = (
                        f" - {data.get('description', '')}"
                        if data.get("description")
                        else ""
                    )
                    print(f"  ✗ {repo_name}{desc}")

        if local_count > 0:
            print("\nAlready cloned locally:")
            for repo_name, data in sorted(results.items()):
                if data.get("exists_locally", False):
                    print(f"  ✓ {repo_name}")
    else:
        # Normal mode: checking what's local but not on GitHub
        exists_count = sum(1 for r in results.values() if r["exists"])
        missing_count = total - exists_count

        print(f"\n{'=' * 60}")
        print(f"Total: {total} | Found: {exists_count} | Missing: {missing_count}")
        print("=" * 60)

        if missing_count > 0:
            print(f"\nMissing repositories on GitHub ({username}):")
            for repo_name, data in sorted(results.items()):
                if not data["exists"]:
                    print(f"  ✗ {repo_name}")

        if exists_count > 0:
            print("\nExisting repositories:")
            for repo_name, data in sorted(results.items()):
                if data["exists"]:
                    print(f"  ✓ {repo_name} → {data['url']}")


def main():
    parser = argparse.ArgumentParser(
        description="Check if GitHub repositories exist for subdirectories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./check_for_repo.py                    # Check current directory
  ./check_for_repo.py /path/to/projects  # Check specific directory
  ./check_for_repo.py -v                 # Verbose mode (show all results)
  ./check_for_repo.py -u username        # Check different GitHub user
  ./check_for_repo.py -i                 # Inverse: show GitHub repos not cloned locally

Note: Requires GitHub CLI (gh) to be installed and authenticated.
      Install: https://cli.github.com/
      Authenticate: gh auth login
        """,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to check (default: current directory)",
    )
    parser.add_argument(
        "-u",
        "--username",
        default=None,
        help="GitHub username to check (default: authenticated gh user)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show all results, not just existing repos",
    )
    parser.add_argument(
        "-i",
        "--inverse",
        action="store_true",
        help="Inverse mode: show GitHub repos not cloned locally",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show summary")

    args = parser.parse_args()

    # Check if gh is installed and authenticated
    if not check_gh_installed():
        print("Error: GitHub CLI (gh) is not installed or not authenticated.")
        print("\nTo install gh:")
        print("  macOS:   brew install gh")
        print(
            "  Linux:   See https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
        )
        print("  Windows: winget install --id GitHub.cli")
        print("\nTo authenticate:")
        print("  gh auth login")
        sys.exit(1)

    username = args.username or get_authenticated_username()
    if not username:
        print(
            "Error: Could not determine GitHub username. "
            "Provide one with -u/--username."
        )
        sys.exit(1)

    directory = Path(args.directory).resolve()

    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    if not directory.is_dir():
        print(f"Error: Not a directory: {directory}")
        sys.exit(1)

    if not args.quiet:
        print(f"Directory: {directory} | User: {username}")

    if args.inverse:
        # Inverse mode: check what's on GitHub but not local
        results = check_missing_local(
            directory, username=username, verbose=args.verbose and not args.quiet
        )

        if not args.quiet:
            print_summary(results, username, inverse=True)

        # Exit with status code based on results
        # 0 if all repos are cloned, 1 if any are missing locally
        missing = sum(1 for r in results.values() if not r.get("exists_locally", False))
        sys.exit(0 if missing == 0 else 1)
    else:
        # Normal mode: check what's local but not on GitHub
        results = check_all_repos(
            directory, username=username, verbose=args.verbose and not args.quiet
        )

        if not args.quiet:
            print_summary(results, username, inverse=False)

        # Exit with status code based on results
        # 0 if all repos exist, 1 if any are missing
        missing = sum(1 for r in results.values() if not r["exists"])
        sys.exit(0 if missing == 0 else 1)


if __name__ == "__main__":
    main()
