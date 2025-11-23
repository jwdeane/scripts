# Repository Guidelines

## Project Structure & Module Organization
Scripts live at the repo root. Python utilities stay self-contained with the uv shebang (`#!/usr/bin/env -S uv run --quiet -s`) and keep their `.py` suffix; shell utilities are executable files without an extension. `README.md` documents available tools; `AGENTS.md` captures contributor expectations. No auxiliary modules or fixtures directories—build utilities directly into each script.

## Build & Development Commands
- `./script_name.py ...` – Run any script directly; uv resolves dependencies on demand.
- `ruff check --fix` – Lint and auto-fix Python files after every edit.
- `shfmt -w <scripts>` and `shellcheck <scripts>` – Format and lint shell scripts before submitting changes.

## Coding Style & Naming Conventions
- Stick to modern Python (3.11+) features when helpful; scripts already rely on pathlib and type hints.
- Use descriptive snake_case for functions/variables and UPPER_SNAKE for constants (e.g., `THUMBNAIL_EXTENSIONS`).
- Keep imports grouped as `stdlib`, then third-party, then local. Maintain ASCII unless a script already uses emoji in output.
- Always run `ruff check --fix` post-edit to enforce formatting, import sorting, and lint rules.

## Validation Guidelines
- Manually exercise scripts after changes (e.g., `./check_gh_repos.py -i`, `./youtube_thumbnail_grabber.py -x`). Capture CLI output snippets for verification.
- Prefer flag-driven dry runs (like `-i` or `--execute`) to confirm behavior before touching live data.

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `feat: add inverse mode`, `fix: handle yt-dlp webp output`, `docs: update AGENTS`). Keep summaries under 72 chars and optional body paragraphs for context.
- Each PR should describe the problem, the solution, and validation (commands executed). Link issues when applicable and include screenshots for UX changes (CLI output snippets suffice).

## Additional Tips
- Network-dependent scripts (GitHub API, yt-dlp) should degrade gracefully with helpful errors; guard against missing binaries.
- Prefer pathlib over os.path for new code. Keep CLI help text accurate—mirror real invocation (`./script.py -h`) rather than `python3 script.py`.
