#!/usr/bin/env -S uv run --quiet -s
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

THUMBNAIL_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

def extract_video_id(filename):
    """Extract video ID from filename containing [xxx] pattern."""
    match = re.search(r'\[([^\]]+)\]', filename)
    return match.group(1) if match else None

def find_existing_thumbnail(directory: Path, base_name: str) -> Optional[Path]:
    """Return an existing thumbnail path for the given base name, if any."""
    directory = Path(directory)
    for ext in THUMBNAIL_EXTENSIONS:
        candidate = directory / f"{base_name}{ext}"
        if candidate.exists():
            return candidate
    return None


def find_downloaded_thumbnail(temp_output: Path) -> Optional[Path]:
    """Locate the thumbnail file produced by yt-dlp for the temp prefix."""
    for ext in THUMBNAIL_EXTENSIONS:
        candidate = temp_output.with_suffix(ext)
        if candidate.exists():
            return candidate

    for candidate in temp_output.parent.glob(f"{temp_output.name}.*"):
        if candidate.suffix.lower() == ".part":
            continue
        return candidate
    return None


def download_thumbnail(video_id, output_filename, directory, dry_run=True):
    """Download highest resolution thumbnail using yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    directory_path = Path(directory)
    existing_thumbnail = find_existing_thumbnail(directory_path, output_filename)

    # Skip if thumbnail already exists
    if existing_thumbnail:
        print(f"Thumbnail already exists: {existing_thumbnail} (skipping)")
        return True

    if dry_run:
        print(f"[DRY RUN] Would download: {url}")
        print(f"[DRY RUN] Would save as: {directory_path / (output_filename + '.jpg')}")
        return True

    # Create temporary filename for yt-dlp output
    temp_output = directory_path / f"temp_{video_id}"

    try:
        # Download thumbnail only
        cmd = [
            "yt-dlp",
            "--write-thumbnail",
            "--skip-download",
            "--convert-thumbnails",
            "jpg",
            "-o",
            str(temp_output),
            url,
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Find the downloaded thumbnail file
        downloaded_thumbnail = find_downloaded_thumbnail(temp_output)
        if downloaded_thumbnail:
            final_thumbnail = (
                directory_path / f"{output_filename}{downloaded_thumbnail.suffix.lower()}"
            )
            downloaded_thumbnail.rename(final_thumbnail)
            print(f"✓ Downloaded thumbnail for {output_filename}")
            return True

        print(f"✗ Thumbnail file not found for {video_id}")
        return False

    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to download thumbnail for {video_id}: {e.stderr}")
        return False
    except Exception as e:
        print(f"✗ Error processing {video_id}: {str(e)}")
        return False

def process_directory(directory, dry_run=True, recursive=False):
    files_processed = 0
    files_successful = 0
    directory = Path(directory)

    if recursive:
        file_iter = (p for p in directory.rglob("*") if p.is_file())
    else:
        file_iter = (p for p in directory.iterdir() if p.is_file())

    # Precompute the list of files to process alongside their video IDs
    files_with_video_id = []
    for path in file_iter:
        video_id = extract_video_id(path.name)
        if video_id:
            files_with_video_id.append((path, video_id))

    total_to_process = len(files_with_video_id)

    for idx, (file_path, video_id) in enumerate(files_with_video_id):
        filename = file_path.name

        if video_id:
            print(f"Processing: {file_path}")
            print(f"Video ID: {video_id}")

            # Remove extension but keep the full filename including [video_id]
            base_name = os.path.splitext(filename)[0]

            if download_thumbnail(video_id, base_name, file_path.parent, dry_run):
                files_successful += 1

            files_processed += 1
            if not dry_run:
                remaining = total_to_process - (idx + 1)
                print(f"{remaining} of {total_to_process} remaining")
                print("-" * 50)

    return files_processed, files_successful

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Download YouTube thumbnails for files with video IDs in filename",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./youtube_thumbnail_grabber.py                    # Dry run in current directory
  ./youtube_thumbnail_grabber.py -x                 # Execute in current directory
  ./youtube_thumbnail_grabber.py /path/to/files     # Dry run in specified directory
  ./youtube_thumbnail_grabber.py -x /path/to/files  # Execute in specified directory
  ./youtube_thumbnail_grabber.py -R                 # Recursively process subdirectories (dry run)
  ./youtube_thumbnail_grabber.py -x -R              # Recursively process subdirectories (execute)
        """
    )
    parser.add_argument('-x', '--execute', action='store_true',
                       help='Execute downloads (default is dry run)')
    parser.add_argument('-R', '--recursive', action='store_true',
                       help='Recursively process directories')
    parser.add_argument('directory', nargs='?', default='.',
                       help='Directory to process (default: current directory)')

    args = parser.parse_args()

    directory = Path(args.directory).resolve()
    dry_run = not args.execute
    recursive = args.recursive

    if not directory.exists():
        print(f"Directory not found: {directory}")
        sys.exit(1)

    print(f"Processing files in: {directory}")
    if recursive:
        print("🔁 RECURSIVE MODE - Processing subdirectories")
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be downloaded")
        print("   Use -x or --execute to actually download thumbnails")
    else:
        print("🚀 EXECUTE MODE - Downloading thumbnails")
    print("-" * 60)

    # Check if yt-dlp is available (only in execute mode)
    if not dry_run:
        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: yt-dlp not found. Please install it first:")
            print("pip install yt-dlp")
            sys.exit(1)

    files_processed, files_successful = process_directory(directory, dry_run=dry_run, recursive=recursive)

    print("\nSummary:")
    print(f"Files processed: {files_processed}")
    if dry_run:
        print(f"Would download: {files_successful} thumbnails")
        print("\n💡 Run with -x to actually download the thumbnails")
    else:
        print(f"Thumbnails downloaded: {files_successful}")
        print(f"Failed: {files_processed - files_successful}")

if __name__ == "__main__":
    main()
