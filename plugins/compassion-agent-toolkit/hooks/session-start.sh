#!/usr/bin/env bash
# compassion-agent-toolkit · SessionStart
#
# 1. Hands the developer's Context7 key to this session's shell commands.
#    Claude Code keeps the key in the OS keychain (plugin option
#    `context7_api_key`) and passes it to hooks only, as
#    CLAUDE_PLUGIN_OPTION_CONTEXT7_API_KEY. Writing an export to CLAUDE_ENV_FILE
#    makes it visible to the `ctx7` commands Claude runs. The key is never
#    printed. A CONTEXT7_API_KEY already set in the environment wins.
# 2. Saves the session's model (from this hook's input) for assisted-by.js,
#    the commit trailer's fallback when the transcript has none yet.
# 3. Tells Claude, in one line, when a tool the toolkit needs is missing, so it can
#    offer /compassion-agent-toolkit:setup. Silent when everything is in place.

if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -n "${CLAUDE_PLUGIN_OPTION_CONTEXT7_API_KEY:-}" ] && [ -z "${CONTEXT7_API_KEY:-}" ]; then
  printf 'export CONTEXT7_API_KEY=%q\n' "$CLAUDE_PLUGIN_OPTION_CONTEXT7_API_KEY" >> "$CLAUDE_ENV_FILE"
fi

input=$(cat)
if [ -n "${CLAUDE_PLUGIN_DATA:-}" ] && command -v node >/dev/null 2>&1; then
  printf '%s' "$input" | node -e '
    const fs = require("fs"), path = require("path")
    try {
      const i = JSON.parse(fs.readFileSync(0, "utf8"))
      if (i.model && i.session_id) {
        fs.mkdirSync(process.env.CLAUDE_PLUGIN_DATA, { recursive: true })
        fs.writeFileSync(path.join(process.env.CLAUDE_PLUGIN_DATA, "model-" + i.session_id), String(i.model))
      }
    } catch {}' 2>/dev/null
fi

missing=""
command -v node >/dev/null 2>&1 || missing="$missing, Node.js 18+"
command -v agent-browser >/dev/null 2>&1 || missing="$missing, agent-browser"
if ! command -v ctx7 >/dev/null 2>&1 && ! command -v npx >/dev/null 2>&1; then
  missing="$missing, ctx7"
fi

if [ -n "$missing" ]; then
  echo "compassion-agent-toolkit: not fully set up on this machine (missing: ${missing#, }). Before using find-docs or agent-browser, offer the user /compassion-agent-toolkit:setup."
fi
exit 0
