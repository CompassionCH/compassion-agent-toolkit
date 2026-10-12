#!/bin/sh
# compassion-agent-toolkit · SessionStart
#
# Context7 runs through `ctx7`, or `npx ctx7@latest` when it isn't installed.
# When neither can run, every docs lookup fails. This check says so once, when
# the session starts. Plain sh, so it runs where Node doesn't. Silent when all
# is well; otherwise exit 2 shows stderr to the user only, and the session goes
# on. The Node minimum is ctx7's `engines` field (`npm view ctx7 engines`):
# older Node crashes on load.

ctx7 --version >/dev/null 2>&1 && exit 0
v=$(node -p process.versions.node 2>/dev/null)
major=${v%%.*}
minor=${v#*.}
minor=${minor%%.*}
if ! { [ "$major" -gt 22 ] || { [ "$major" -eq 22 ] && [ "$minor" -ge 13 ]; }; } 2>/dev/null; then
  echo "find-docs: Node.js 22.13+ is not on the PATH Claude Code started with (found: ${v:-none}), so docs lookups through Context7 fail. Install or update Node.js, then restart Claude Code." >&2
  exit 2
fi
command -v npx >/dev/null 2>&1 && exit 0
echo "find-docs: npx is missing, so docs lookups through Context7 fail. Install npm (on Debian and Ubuntu it is a package of its own), then restart Claude Code." >&2
exit 2
