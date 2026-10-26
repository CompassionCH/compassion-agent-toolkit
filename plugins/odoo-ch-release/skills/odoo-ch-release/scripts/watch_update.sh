#!/bin/sh
# Stream the progress of an Odoo module update, to be used as a Monitor source.
# Runs ON THE SERVER (POSIX sh, no dependency), read-only. From the local machine:
#   ssh <ssh> sh -s -- <log> <modules, comma separated> [heartbeat seconds] < watch_update.sh
#
# The update must have been started by the launcher of the skill, which writes
#   <log>       the Odoo output
#   <log>.pid   pid of the Odoo process
#   <log>.exit  "exit=<code>" and the end time, once the process is over
#
# Every line printed is one event:
#  - a heartbeat every N seconds (default 30): module in progress, n/total, counts
#  - at once: migration scripts, ERROR / CRITICAL / Traceback lines, the end
#  - when the log has been quiet for 60 s or more: what the process is doing
LOG=$1
MODS=$2
EVERY=${3:-30}
PIDFILE="$LOG.pid"
total=$(echo "$MODS" | tr ',' '\n' | grep -c .)
pos=0
beat=0
prev_cpu=""
prev_io=""
start=$(date +%s)

proc_state() {
  pid=$(cat "$PIDFILE" 2>/dev/null)
  [ -n "$pid" ] && [ -d "/proc/$pid" ] || { echo "process gone"; return; }
  st=$(awk '{print $3}' "/proc/$pid/stat")
  cpu=$(awk '{print $14+$15}' "/proc/$pid/stat")
  io=$(awk '/^rchar/{print $2}' "/proc/$pid/io" 2>/dev/null)
  d_cpu=$((cpu - ${prev_cpu:-$cpu}))
  d_io=$(( (${io:-0} - ${prev_io:-${io:-0}}) / 1024 ))
  prev_cpu=$cpu
  prev_io=$io
  case "$st" in
    D) why="waiting on disk or network files (state D)";;
    S) why="sleeping, probably waiting for the database or a lock";;
    R) why="computing";;
    *) why="state $st";;
  esac
  echo "$why | cpu +${d_cpu} ticks, read +${d_io} KiB since last beat"
}

while :; do
  size=$(wc -c < "$LOG" 2>/dev/null || echo 0)
  if [ "$size" -gt "$pos" ]; then
    tail -c +$((pos + 1)) "$LOG" | head -c $((size - pos)) |
      grep -E 'Running upgrade|(pre|post|end)-migration|OpenUpgrade|ERROR|CRITICAL|Traceback|Modules loaded|Registry loaded' |
      cut -c1-230 | sed 's/^/  /'
    pos=$size
  fi
  now=$(date +%s)
  if [ $((now - beat)) -ge "$EVERY" ]; then
    beat=$now
    cur=$(grep -o 'loading [a-z_0-9]*/' "$LOG" | tail -1 | sed 's/loading //; s#/##')
    done_n=0
    for m in $(echo "$MODS" | tr ',' ' '); do
      grep -q "loading $m/" "$LOG" && done_n=$((done_n + 1))
    done
    warn=$(grep -c ' WARNING ' "$LOG")
    errs=$(grep -cE ' (ERROR|CRITICAL) |Traceback' "$LOG")
    quiet=$((now - $(stat -c %Y "$LOG")))
    elapsed=$((now - start))
    line="[$(date -u +%T) UTC] +$((elapsed / 60))m$((elapsed % 60))s | module: ${cur:-starting} | $done_n/$total modules reached | warnings $warn | errors $errs | log quiet ${quiet}s"
    [ "$quiet" -ge 60 ] && line="$line | $(proc_state)"
    echo "$line"
  fi
  if [ -f "$LOG.exit" ]; then
    echo "DONE: $(tr '\n' ' ' < "$LOG.exit")"
    echo "  warnings $(grep -c ' WARNING ' "$LOG"), errors $(grep -cE ' (ERROR|CRITICAL) |Traceback' "$LOG")"
    tail -3 "$LOG" | cut -c1-200 | sed 's/^/  /'
    break
  fi
  sleep 2
done
