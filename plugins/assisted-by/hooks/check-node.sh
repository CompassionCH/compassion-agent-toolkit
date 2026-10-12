#!/bin/sh
# compassion-agent-toolkit · SessionStart
#
# The commit hook runs on Node.js 18+. When Node can't run, it fails on every
# commit with a one-line notice, and commits silently lose their trailer. This
# check says so once, when the session starts. Plain sh, so it runs where Node
# doesn't. Silent when all is well; otherwise exit 2 shows stderr to the user
# only, and the session goes on.

v=$(node -p process.versions.node 2>/dev/null)
[ "${v%%.*}" -ge 18 ] 2>/dev/null && exit 0
echo "assisted-by: Node.js 18+ is not on the PATH Claude Code started with (found: ${v:-none}), so commits get no Assisted-by trailer. Install or update Node.js, then restart Claude Code." >&2
exit 2
