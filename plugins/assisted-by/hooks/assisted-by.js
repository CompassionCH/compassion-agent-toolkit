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
// subagent's transcript), the effort from the hook input's `effort.level`
// (a subagent's own transcript first; CLAUDE_EFFORT as a fallback).
// The trailer goes right after the first `git commit` in the command, so chained
// commands (`git add … && git commit …`) and heredoc messages keep working.
// Trailers already in the command or its message credit other agents that
// drafted part of the change, and are kept. The hook adds this agent's line
// unless that exact line is already in the command, in a `-F` message file,
// or, for `--amend --no-edit`, in the message being kept. Any failure leaves
// the command untouched: the hook never blocks a commit.

const fs = require('fs')
const path = require('path')
const { execFileSync } = require('child_process')

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

// The effort of the API request nearest above line `i`: the request that
// produced the message on that line.
function requestEffort(lines, i) {
  for (let j = i - 1; j >= 0; j--) {
    if (!lines[j].includes('"api-request"')) continue
    try {
      const req = JSON.parse(lines[j])
      const level = req.params && req.params.output_config && req.params.output_config.effort
      if (typeof level === 'string') return level
    } catch {}
  }
  return null
}

// Scans one transcript tail, newest first: the model of the assistant message
// holding this tool call (`hit`) with its request's effort, and the newest
// assistant model (`latest`).
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
    if (toolUseId && Array.isArray(msg.content) && msg.content.some((c) => c && c.id === toolUseId)) return { hit: model, latest, effort: requestEffort(lines, i) }
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

// The model that made this tool call and, for a subagent, its own effort.
// Claude Code may write the assistant message just after the hook starts, so
// look for it for up to ~1 s. Not found: the session's newest assistant model.
function caller(transcriptPath, toolUseId) {
  if (!transcriptPath) return {}
  let latest = null
  for (let attempt = 0; attempt < 10; attempt++) {
    const main = scan(transcriptPath, toolUseId)
    if (main.hit) return { model: main.hit }
    latest = main.latest || latest
    if (!toolUseId) return { model: latest }
    for (const f of subagentFiles(transcriptPath)) {
      const sub = scan(f, toolUseId)
      if (sub.hit) return { model: sub.hit, effort: sub.effort }
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100)
  }
  return { model: latest }
}

// The message text git will keep beside the command line: a `-F` file, and
// HEAD's message when `--amend --no-edit` reuses it.
function keptMessages(command, cwd) {
  const texts = []
  const file = command.match(/(?:\s-F\s*|\s--file[=\s])\s*(?:"([^"]+)"|'([^']+)'|([^\s;&|]+))/)
  const name = file && (file[1] || file[2] || file[3])
  if (name && name !== '-') {
    try { texts.push(fs.readFileSync(path.resolve(cwd || '.', name), 'utf8')) } catch {}
  }
  if (/\s--amend\b/.test(command) && /\s--no-edit\b/.test(command)) {
    try {
      texts.push(execFileSync('git', ['log', '-1', '--format=%B'], { cwd: cwd || undefined, encoding: 'utf8', timeout: 2000, stdio: ['ignore', 'pipe', 'ignore'] }))
    } catch {}
  }
  return texts
}

const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

let raw = ''
process.stdin.on('data', (c) => { raw += c })
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(raw)
    const command = input.tool_input && input.tool_input.command
    if (typeof command !== 'string' || !/\bgit\s+commit(?=\s|$|;|&|\|)/.test(command)) return

    const found = caller(input.transcript_path, input.tool_use_id)
    const model = found.model || 'unknown'
    const effort = found.effort || (input.effort && input.effort.level) || process.env.CLAUDE_EFFORT || 'unknown'
    const trailer = `Assisted-by: ${model}, ${effort}, claude-code`

    const own = new RegExp(`Assisted-by:\\s*${escape(model)}\\s*,\\s*${escape(effort)}\\s*,\\s*claude-code\\b`, 'i')
    if (own.test(command) || keptMessages(command, input.cwd).some((t) => own.test(t))) return

    const quoted = `'${trailer.replace(/'/g, `'\\''`)}'`
    const updated = command.replace(/\bgit(\s+)commit(?=\s|$|;|&|\|)/, (_, space) => `git${space}commit --trailer ${quoted}`)

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
