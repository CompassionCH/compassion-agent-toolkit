#!/usr/bin/env node
// compassion-agent-toolkit · PreToolUse (Bash)
//
// Adds the team's AI trailer to every `git commit` Claude runs:
//
//     Assisted-by: claude-opus-5-5, high, claude-code
//
// model (the raw API id, so commits can be counted per model), effort,
// harness. The values come from what Claude Code records,
// never from the model's memory: the model from the session transcript
// (the assistant message holding this tool call, in the session's or a
// subagent's transcript; else the model SessionStart received), the effort from the hook
// input's `effort.level` (CLAUDE_EFFORT as a fallback).
// The trailer goes right after the first `git commit` in the command, so chained
// commands (`git add … && git commit …`) and heredoc messages keep working.
// A command that already carries an Assisted-by trailer is left alone, and
// any failure leaves the command untouched: the hook never blocks a commit.

const fs = require('fs')
const path = require('path')

function readTail(file, bytes = 256 * 1024) {
  const fd = fs.openSync(file, 'r')
  try {
    const size = fs.fstatSync(fd).size
    const len = Math.min(size, bytes)
    const buf = Buffer.alloc(len)
    fs.readSync(fd, buf, 0, len, size - len)
    return buf.toString('utf8').split('\n')
  } finally {
    fs.closeSync(fd)
  }
}

// Scans one transcript tail, newest first: the model of the assistant message
// holding this tool call (`hit`) and the newest assistant model (`latest`).
function scan(file, toolUseId) {
  let lines
  try { lines = readTail(file) } catch { return {} }
  let latest = null
  for (let i = lines.length - 1; i >= 0; i--) {
    if (!lines[i].includes('"assistant"')) continue
    let entry
    try { entry = JSON.parse(lines[i]) } catch { continue }
    const msg = entry && entry.type === 'assistant' && entry.message
    const model = msg && msg.model
    if (typeof model !== 'string' || model.startsWith('<')) continue // skip "<synthetic>"
    if (!latest) latest = model
    if (toolUseId && Array.isArray(msg.content) && msg.content.some((c) => c && c.id === toolUseId)) return { hit: model, latest }
  }
  return { latest }
}

// Subagents keep their own transcripts beside the session's, in
// <session>/subagents/, while hooks receive the session's transcript_path.
function subagentFiles(transcriptPath) {
  const dir = path.join(transcriptPath.replace(/\.jsonl$/, ''), 'subagents')
  try {
    return fs.readdirSync(dir).filter((f) => f.endsWith('.jsonl'))
      .map((f) => path.join(dir, f))
      .map((f) => ({ f, t: fs.statSync(f).mtimeMs }))
      .sort((x, y) => y.t - x.t).slice(0, 4).map((x) => x.f)
  } catch {
    return []
  }
}

// The model that made this tool call. Claude Code may write the assistant
// message just after the hook starts, so look for it for up to ~1 s.
// Not found: the session's newest assistant model.
function transcriptModel(transcriptPath, toolUseId) {
  if (!transcriptPath) return null
  let latest = null
  for (let attempt = 0; attempt < 10; attempt++) {
    const main = scan(transcriptPath, toolUseId)
    if (main.hit) return main.hit
    latest = main.latest || latest
    if (!toolUseId) return latest
    for (const f of subagentFiles(transcriptPath)) {
      const sub = scan(f, toolUseId)
      if (sub.hit) return sub.hit
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100)
  }
  return latest
}

// The model SessionStart received, saved by session-start.sh.
function sessionStartModel(sessionId) {
  const dir = process.env.CLAUDE_PLUGIN_DATA
  if (!dir || !sessionId) return null
  try { return fs.readFileSync(path.join(dir, 'model-' + sessionId), 'utf8').trim() || null } catch { return null }
}

let raw = ''
process.stdin.on('data', (c) => { raw += c })
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(raw)
    const command = input.tool_input && input.tool_input.command
    if (typeof command !== 'string' || !/\bgit\s+commit(?=\s|$|;|&|\|)/.test(command)) return
    if (/Assisted-by:/i.test(command)) return

    const model = transcriptModel(input.transcript_path, input.tool_use_id)
      || sessionStartModel(input.session_id) || 'unknown'
    const effort = (input.effort && input.effort.level) || process.env.CLAUDE_EFFORT || 'unknown'
    const trailer = `Assisted-by: ${model}, ${effort}, claude-code`
    const updated = command.replace(/\bgit(\s+)commit(?=\s|$|;|&|\|)/, `git$1commit --trailer "${trailer}"`)

    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        updatedInput: { ...input.tool_input, command: updated },
      },
    }))
  } catch {
    // leave the command as it was
  }
})
