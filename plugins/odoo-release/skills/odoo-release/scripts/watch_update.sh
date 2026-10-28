#!/bin/sh
# Stream the progress of an Odoo module update, to be used as a Monitor source.
# Runs ON THE SERVER (POSIX sh, no dependency), read-only. From the local machine:
#   ssh <ssh> sh -s -- <log> <modules, comma separated> [heartbeat seconds] < watch_update.sh
#
# The update must have been started by the launcher of the skill, which writes
#   <log>       the Odoo log (`--logfile`)
#   <log>.out   what the process printed on stdout / stderr (crashes before logging)
#   <log>.pid   pid of the Odoo process
#   <log>.exit  "exit=<code>" and the end time, once the process is over
#
# Every line printed is one event:
#  - a heartbeat every N seconds (default 30): module in progress, n/total, counts
#  - at once: migration scripts, ERROR / CRITICAL / Traceback lines, the end
#  - when the log has been quiet for 60 s or more (QUIET): what the process is doing
#  - `DONE: unknown (process gone)` when the process is gone and no exit file comes
LOG=$1
MODS=$2
EVERY=${3:-30}
QUIET=${QUIET:-60}   # seconds of silence after which the heartbeat says what the process does
PIDFILE="$LOG.pid"
total=$(echo "$MODS" | tr ',' '\n' | grep -c .)
pos=0
beat=0
prev_cpu=""
prev_io=""
gone_since=""
start=$(date +%s)
PROC_DESC=""

# Is the Odoo process still there? (no side effect, called every loop)
alive() {
  pid=$(cat "$PIDFILE" 2>/dev/null)
  [ -n "$pid" ] && [ -d "/proc/$pid" ]
}

# Sets PROC_DESC (and keeps prev_cpu / prev_io, so call it once per heartbeat only): it must NOT run in a subshell,
# `$(proc_state)` would throw the previous values away and every delta would be 0.
proc_state() {
  pid=$(cat "$PIDFILE" 2>/dev/null)
  if [ -z "$pid" ] || [ ! -d "/proc/$pid" ]; then
    PROC_DESC="process gone"
    return
  fi
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
  PROC_DESC="$why | cpu +${d_cpu} ticks, read +${d_io} KiB since last beat"
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
    # Odoo 18 logs "Loading module X (i/N)" and "Module X loaded in ..." at INFO for every
    # module that is installed or updated, dependents included, whatever its files.
    cur=$(grep -o 'Loading module [a-z_0-9]* ([0-9]*/[0-9]*)' "$LOG" | tail -1 | sed 's/Loading module //')
    reached=0
    finished=0
    for m in $(echo "$MODS" | tr ',' ' '); do
      grep -q "Loading module $m (" "$LOG" && reached=$((reached + 1))
      grep -q "Module $m loaded in" "$LOG" && finished=$((finished + 1))
    done
    warn=$(grep -c ' WARNING ' "$LOG")
    errs=$(grep -cE ' (ERROR|CRITICAL) |Traceback' "$LOG")
    quiet=$((now - $(stat -c %Y "$LOG")))
    elapsed=$((now - start))
    line="[$(date -u +%T) UTC] +$((elapsed / 60))m$((elapsed % 60))s | now: ${cur:-starting} | requested modules: $reached/$total reached, $finished/$total done | warnings $warn | errors $errs | log quiet ${quiet}s"
    proc_state
    if [ "$quiet" -ge "$QUIET" ] || [ "$PROC_DESC" = "process gone" ]; then line="$line | $PROC_DESC"; fi
    echo "$line"
  fi
  if [ -f "$LOG.exit" ]; then
    echo "DONE: $(tr '\n' ' ' < "$LOG.exit")"
    echo "  warnings $(grep -c ' WARNING ' "$LOG"), errors $(grep -cE ' (ERROR|CRITICAL) |Traceback' "$LOG")"
    tail -3 "$LOG" | cut -c1-200 | sed 's/^/  /'
    if ! grep -q '^exit=0' "$LOG.exit" && [ -s "$LOG.out" ]; then
      echo "  stdout/stderr of the process:"
      tail -8 "$LOG.out" | cut -c1-200 | sed 's/^/    /'
    fi
    break
  fi
  # The launcher can die (wrapper killed, server rebooted): no exit file will ever come
  if ! alive; then
    [ -z "$gone_since" ] && gone_since=$now
    if [ $((now - gone_since)) -ge 15 ]; then
      echo "DONE: unknown (process gone, no exit file after 15 s): do not assume success"
      tail -3 "$LOG" | cut -c1-200 | sed 's/^/  /'
      [ -s "$LOG.out" ] && tail -8 "$LOG.out" | cut -c1-200 | sed 's/^/    /'
      break
    fi
  else
    gone_since=""
  fi
  sleep 2
done
