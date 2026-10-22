#!/bin/bash
# Build the ROB550 website with the MBot server image pages and open it on this computer.
#
# Usage: website/serve.sh [port]            build once, then serve (default port 4000)
#        website/serve.sh --rebuild [port]  build again first (after changing overlay/)
#
# Needs Docker (for the Jekyll build, first time only) and python3 (to serve the pages).

set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
site="$here/_build/src/_site"

rebuild=false
if [[ "${1:-}" == "--rebuild" ]]; then
    rebuild=true
    shift
fi
port="${1:-4000}"

if $rebuild || [[ ! -f "$site/index.html" ]]; then
    "$here/build-site.sh"
fi

echo
echo "ROB550 website with the MBot server image pages:"
echo "    http://localhost:$port/docs/botlab/mbot-system-setup-Pi5.html"
echo "Press Ctrl+C to stop."
cd "$site"
exec python3 -m http.server "$port" --bind 127.0.0.1
