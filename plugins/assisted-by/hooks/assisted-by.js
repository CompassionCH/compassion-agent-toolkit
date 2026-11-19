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
// The trailer goes right after the first `git commit` that starts a command
// (`git add … && git commit …`, heredoc messages); a `git commit` inside quoted
// text is left alone. Trailers already in the command or its message credit
// other agents that drafted part of the change, and are kept. The hook adds
// this agent's line unless that exact line is already in the command, in the
// trailers of a `-F` message file, or in the message an amend or `-C` keeps. With git's default trailer settings, that gives one line per
// agent. Any failure leaves the command untouched: the hook never blocks a commit.

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

// The effort of the API request nearest above line `i`, the request that
// produced the message on that line; null when that request names none.
function requestEffort(lines, i) {
  for (let j = i - 1; j >= 0; j--) {
    if (!lines[j].includes('"api-request"')) continue
    try {
      const req = JSON.parse(lines[j])
      if (!req || req.type !== 'api-request') continue
      const level = req.params && req.params.output_config && req.params.output_config.effort
      return typeof level === 'string' ? level : null
    } catch {}
  }
  return null
}

// A subagent's settings sit beside its transcript.
function metaEffort(file) {
  try {
    const level = JSON.parse(fs.readFileSync(file.replace(/\.jsonl$/, '.meta.json'), 'utf8')).effort
    return typeof level === 'string' ? level : null
  } catch {
    return null
  }
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
      if (sub.hit) return { model: sub.hit, effort: sub.effort || metaEffort(f) || 'unknown' }
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100)
  }
  return { model: latest }
}

// The message text git will keep beside the command line: a regular `-F`
// file; the message of the revision `-C`/`-c` reuses; HEAD's message for an
// amend that gives no new one (Claude Code runs git with GIT_EDITOR=true, so a
// plain `--amend` keeps it too). Only read when the commit runs in the hook's
// own folder, and never a pipe or a device, which git must read itself.
function keptMessages(command, commitAt, cwd) {
  const texts = []
  if (!cwd || /(^|[;&|(\s])(cd|pushd)\s/.test(command.slice(0, commitAt))) return texts
  const args = command.slice(commitAt).split(/&&|\|\||;|\n/)[0]
  const file = args.match(/(?:\s-F\s*|\s--file[=\s])\s*(?:"([^"]+)"|'([^']+)'|([^\s;&|]+))/)
  const name = file && (file[1] || file[2] || file[3])
  if (name && name !== '-') {
    try {
      const full = path.resolve(cwd, name)
      const stat = fs.statSync(full)
      if (stat.isFile() && stat.size <= 1024 * 1024) texts.push(fs.readFileSync(full, 'utf8'))
    } catch {}
  }
  const reuse = args.match(/(?:\s-[cC]\s*|\s--re(?:use|edit)-message[=\s]\s*)([^\s;&|'"]+)/)
  const newMessage = /\s(-m|--message|-F|--file)\b/.test(args)
  const rev = reuse ? reuse[1] : (/\s--amend\b/.test(args) && !newMessage ? 'HEAD' : null)
  if (rev) {
    try {
      texts.push(execFileSync('git', ['log', '-1', '--format=%B', rev, '--'], { cwd, encoding: 'utf8', timeout: 2000, stdio: ['ignore', 'pipe', 'ignore'] }))
    } catch {}
  }
  return texts
}

// The first `git commit` at the start of a command: the start of the input,
// after a separator, `then`, `do` or variable assignments, or opening the
// command a shell runs (`sh -c '…'`, `rebase --exec '…'`, `foreach '…'`).
// Never inside other quoted text.
const COMMIT = /(^|[;&|(\n]\s*|\b(?:then|do|else)\s+|(?:\b(?:ba|z)?sh\s+-c|\s--exec[=\s]|\s-x|\bforeach(?:\s+--recursive)?)\s*['"]\s*)((?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*)git(\s+)commit(?=\s|$|;|&|\||['"])/

const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

let raw = ''
process.stdin.on('data', (c) => { raw += c })
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(raw)
    const command = input.tool_input && input.tool_input.command
    if (typeof command !== 'string') return
    const at = command.match(COMMIT)
    if (!at) return

    // No value may carry a quote, a backslash or a line break into the command.
    const clean = (v) => String(v).replace(/['"\\\n\r]/g, '')
    const found = caller(input.transcript_path, input.tool_use_id)
    const model = clean(found.model || 'unknown')
    const effort = clean(found.effort || (input.effort && input.effort.level) || process.env.CLAUDE_EFFORT || 'unknown')
    const trailer = `Assisted-by: ${model}, ${effort}, claude-code`

    const value = `${escape(model)}\\s*,\\s*${escape(effort)}\\s*,\\s*claude-code`
    const inCommand = new RegExp(`Assisted-by:\\s*${value}(?=\\s*(?:$|["'\\n]))`, 'im')
    const inMessage = new RegExp(`^Assisted-by:\\s*${value}\\s*$`, 'im')
    if (inCommand.test(command) || keptMessages(command, at.index, input.cwd).some((t) => inMessage.test(t))) return

    // Backslash-escaped, not quoted: it stays one literal word in a plain
    // command and inside the quotes of `sh -c '…'` or `sh -c "…"`.
    const quoted = trailer.replace(/[^A-Za-z0-9._-]/g, (c) => '\\' + c)
    const updated = command.replace(COMMIT, (_, before, vars, space) => `${before}${vars}git${space}commit --trailer ${quoted}`)

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
