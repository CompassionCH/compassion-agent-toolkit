#!/bin/sh
# compassion-agent-toolkit · SessionStart
#
# The agent-browser CLI installs with npm and needs Node.js 18+ for it. When the
# CLI can't run and can't be installed, every browser check fails. This check
# says so once, when the session starts; a CLI not installed yet is fine, the
# skill offers the install. Plain sh, so it runs where Node doesn't. Silent
# when all is well; otherwise exit 2 shows stderr to the user only, and the
# session goes on.

agent-browser --version >/dev/null 2>&1 && exit 0
v=$(node -p process.versions.node 2>/dev/null)
if ! [ "${v%%.*}" -ge 18 ] 2>/dev/null; then
  echo "agent-browser: Node.js 18+ is not on the PATH Claude Code started with (found: ${v:-none}), so the agent-browser CLI can't be installed or run. Install or update Node.js, then restart Claude Code." >&2
  exit 2
fi
command -v npm >/dev/null 2>&1 && exit 0
echo "agent-browser: npm is missing, so the agent-browser CLI can't be installed. Install npm (on Debian and Ubuntu it is a package of its own), then restart Claude Code." >&2
exit 2
