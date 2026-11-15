#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
export UV_CACHE_DIR="$project_dir/.uv-cache"
export UV_PYTHON_DOWNLOADS=never
exec uv run --locked ramtaskman "$@"
