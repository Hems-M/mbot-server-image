#!/bin/bash
# Build the ROB550 course website (rob550-docs submodule) with the MBot server image changes.
# Only the changed pages live in this folder (overlay/); the full site is built in _build/.
# Also writes course-docs.patch, the same changes as a patch for the course-site owners.
#
# Usage: website/build-site.sh          (website/serve.sh builds and serves it)
# Output: website/_build/src (site sources) and website/_build/src/_site (HTML)
# Needs Docker (any architecture) and internet access (Ruby gems, remote theme).

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
src="$here/rob550-docs"
out="${MBOT_SITE_OUT:-$here/_build}"

log() { printf '[%s build-site] %s\n' "$(date '+%H:%M:%S')" "$*"; }

[[ -f "$src/_config.yml" ]] || { echo "website/rob550-docs is empty: run git submodule update --init" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker not found" >&2; exit 1; }

log "base: rob550-docs at $(git -C "$src" rev-parse --short HEAD)"
rm -rf "$out/src"
mkdir -p "$out"
rsync -a --exclude .git "$src/" "$out/src/"
rsync -a "$here/overlay/" "$out/src/"

log "patch for the course-site owners: website/course-docs.patch"
patch_file="$here/course-docs.patch"
{
    echo "# Changes to rob550-docs for the MBot server image, against $(git -C "$src" rev-parse --short HEAD)."
    echo "# Apply in a clone of the course-docs repository: git apply course-docs.patch"
    echo "# Not in this patch: assets/images/botlab/system-setup-oled-server.png (copy it from"
    echo "# website/overlay/)."
} > "$patch_file"
(cd "$here/overlay" && find . -type f -name '*.md' | sort) | while read -r f; do
    f="${f#./}"
    if [[ -f "$src/$f" ]]; then
        diff -u --label "a/$f" --label "b/$f" "$src/$f" "$here/overlay/$f" >> "$patch_file" || true
    else
        diff -u --label /dev/null --label "b/$f" /dev/null "$here/overlay/$f" >> "$patch_file" || true
    fi
done

log "jekyll build in a ruby:3.3 container"
docker run --rm -v "$out/src:/site" -w /site ruby:3.3 bash -c '
    set -e
    gem install --silent bundler:2.6.2 >/dev/null
    bundle install --quiet
    bundle exec jekyll build -d /site/_site 2>&1 | grep -v "^\s*$"
'
log "done: $out/src/_site/index.html"
