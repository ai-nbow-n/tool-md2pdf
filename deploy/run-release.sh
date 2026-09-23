#!/usr/bin/env bash
# Install root-owned as /usr/local/sbin/deploy-md2pdf. This is the only command
# the website's deployment account needs permission to invoke through sudo.
set -euo pipefail
if [ "$(id -u)" -ne 0 ] || [ "$#" -ne 1 ] || [[ ! "$1" =~ ^[0-9a-f]{40}$ ]]; then
  echo 'Usage: sudo deploy-md2pdf <40-character commit SHA>' >&2
  exit 1
fi
revision=$1
repo_dir=/opt/md2pdf
repository=https://github.com/ai-nbow-n/tool-md2pdf.git
umask 022
if [ ! -e "$repo_dir" ]; then
  git clone --depth=1 "$repository" "$repo_dir"
fi
if [ "$(realpath "$repo_dir")" != "$repo_dir" ] || [ ! -d "$repo_dir/.git" ]; then
  echo 'Expected a regular Git checkout at /opt/md2pdf.' >&2
  exit 1
fi
if [ "$(git -C "$repo_dir" remote get-url origin)" != "$repository" ]; then
  echo 'Unexpected md2pdf origin; refusing to replace it.' >&2
  exit 1
fi
if [ -n "$(git -C "$repo_dir" status --porcelain --untracked-files=all)" ]; then
  echo 'Uncommitted files in /opt/md2pdf; preserve them before deploying.' >&2
  exit 1
fi
git -C "$repo_dir" fetch --depth=1 origin "$revision"
git -C "$repo_dir" checkout --detach --no-overwrite-ignore "$revision"
bash "$repo_dir/deploy/install.sh"
echo "Deployed md2pdf commit $revision"
