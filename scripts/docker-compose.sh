#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

compose_files=("$REPO_ROOT/docker-compose.yml")
gpu_override="$REPO_ROOT/docker-compose.gpu.yml"

function require_nvidia_toolkit() {
  if command -v nvidia-container-cli >/dev/null 2>&1 || command -v nvidia-container-toolkit >/dev/null 2>&1; then
    return 0
  fi

  cat <<'WARN' >&2
Detected NVIDIA GPU but NVIDIA Container Toolkit is not installed.
Install it following https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
WARN
  exit 1
}

if command -v nvidia-smi >/dev/null 2>&1; then
  require_nvidia_toolkit
  if [[ -f "$gpu_override" ]]; then
    compose_files+=("$gpu_override")
  else
    echo "Warning: GPU override $gpu_override is missing, running without GPU hints." >&2
  fi
fi

user_args=()
if [[ "$#" -gt 0 ]]; then
  user_args=("$@")
else
  user_args=("up" "--build")
fi

compose_args=()
for file in "${compose_files[@]}"; do
  compose_args+=("-f" "$file")
done

docker compose "${compose_args[@]}" "${user_args[@]}"