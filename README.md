# Scripts and bobs

Download a single script without cloning the repo by using:

```sh
curl -O https://raw.githubusercontent.com/<user>/<repo>/main/<path/to/script>.py
```

## Scripts

- `check_gh_repos.py` – Compare local directories to GitHub repositories (and vice versa) using the authenticated `gh` CLI to spot missing clones or remotes.
- `youtube_thumbnail_grabber.py` – Scan files for YouTube IDs, then dry‑run or download the matching thumbnails (optionally recursively) via `yt-dlp`.
