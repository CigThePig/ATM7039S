#!/bin/sh
# ATM7039S read-only runtime capture: hardware test V3, capture script version 3.
#
# Reads a fixed allowlist of ordinary kernel-exported files and two small text
# files on the boot partition, lists three fixed sysfs directories, and runs a
# fixed set of read-only commands. Writes only inside one new output folder.
# It never writes to /sys or /proc, never opens anything under /dev (no raw
# block devices, /dev/mem or I2C), never mounts, loads modules, changes clock,
# CPU, regulator or backlight state, and never reads PMIC-backed power_supply
# attributes or cpuinfo_cur_freq. See device/README.md before running it.
#
# Usage: sh capture.sh [OUTPUT_PARENT]
#   OUTPUT_PARENT defaults to the directory containing this script.
#   sh capture.sh --list   prints the allowlist and exits without reading it.
#
# Testing only. Both are recorded in capture-info.txt, and the parser refuses
# such captures as hardware evidence:
#   ATM_CAPTURE_ROOT=/fixture  read every path under /fixture instead of /;
#                              command items read /fixture/.cmd/<id>.
#   ATM_CAPTURE_PATH=dirs      replace the default PATH.

CAPTURE_VERSION=3
CAPTURE_FORMAT=2
ITEM_LIMIT=4194304
set -u
umask 022
PATH=/bin:/sbin:/usr/bin:/usr/sbin
if [ -n "${ATM_CAPTURE_PATH:-}" ]; then PATH=$ATM_CAPTURE_PATH; fi
export PATH
LC_ALL=C
export LC_ALL

# Allowlist: id|kind|target. Kinds:
#   file       copy the file, at most ITEM_LIMIT bytes (more: status truncated)
#   cmd        run one fixed command; no argument comes from input
#   probe      list one fixed sysfs directory: link targets plus a fixed set
#              of attribute files per entry (see probe_attrs)
#   tree       tar of the device-tree directory, after resolving it to an
#              approved kernel path; symbolic links inside are not followed
#   treeindex  find listing of the same directory, to cross-check the tar
# Ids are lower case so that FAT, which ignores case, cannot merge two items.
# Keep in sync with device/capture-versions.json; the parser rejects captures
# whose recorded allowlist differs from the registered script version.
ALLOWLIST='version|file|/proc/version
uname|cmd|uname -a
cmdline|file|/proc/cmdline
uptime|file|/proc/uptime
cpuinfo|file|/proc/cpuinfo
cpu-kernel_max|file|/sys/devices/system/cpu/kernel_max
cpu-possible|file|/sys/devices/system/cpu/possible
cpu-present|file|/sys/devices/system/cpu/present
cpu-online|file|/sys/devices/system/cpu/online
cpu-offline|file|/sys/devices/system/cpu/offline
cpufreq-available|file|/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies
cpufreq-min|file|/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq
cpufreq-max|file|/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq
cpufreq-governor|file|/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cpufreq-driver|file|/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver
cpufreq-scaling_min|file|/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq
cpufreq-scaling_max|file|/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
cpufreq-scaling_cur|file|/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
meminfo|file|/proc/meminfo
iomem|file|/proc/iomem
interrupts|file|/proc/interrupts
modules|file|/proc/modules
mounts|file|/proc/mounts
partitions|file|/proc/partitions
block-sysfs|probe|/sys/block
mmc-sysfs|probe|/sys/bus/mmc/devices
mmc-host-sysfs|probe|/sys/class/mmc_host
fb|file|/proc/fb
fb0-name|file|/sys/class/graphics/fb0/name
fb0-mode|file|/sys/class/graphics/fb0/mode
fb0-modes|file|/sys/class/graphics/fb0/modes
fb0-virtual_size|file|/sys/class/graphics/fb0/virtual_size
fb0-bits_per_pixel|file|/sys/class/graphics/fb0/bits_per_pixel
fb0-stride|file|/sys/class/graphics/fb0/stride
pvr-version|file|/proc/pvr/version
os-release|file|/etc/os-release
batocera-version|file|/usr/share/batocera/batocera.version
koriki-version|file|/usr/share/simplemenu/Koriki/version.txt
boot-uenv|file|/boot/uEnv.txt
boot-conf|file|/boot/batocera-boot.conf
kconfig|file|/proc/config.gz
fdt|file|/sys/firmware/fdt
device-tree|tree|/proc/device-tree
device-tree-index|treeindex|/proc/device-tree
dmesg|cmd|dmesg'

# Items without which the main V3 questions cannot be answered. A capture with
# any of these not "ok" is reported as partial, never as complete.
ESSENTIAL='version cmdline cpu-possible cpu-present cpu-online meminfo iomem partitions mounts block-sysfs device-tree dmesg'

if [ "${1:-}" = "--list" ]; then
    printf '%s\n' "$ALLOWLIST"
    exit 0
fi

ROOT=""
if [ -n "${ATM_CAPTURE_ROOT:-}" ]; then
    ROOT=$(cd "$ATM_CAPTURE_ROOT" 2>/dev/null && pwd -P) || { echo "cannot use fixture root" >&2; exit 1; }
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd -P) || { echo "cannot locate the script folder" >&2; exit 1; }
PARENT="${1:-$SCRIPT_DIR}"
# Absolute path: the tree items change directory before writing.
if ! mkdir -p "$PARENT" 2>/dev/null || ! PARENT=$(cd "$PARENT" 2>/dev/null && pwd -P); then
    echo "cannot use output folder $PARENT" >&2
    exit 1
fi

# FAT-safe name (no colons). The clock may be unset on this handheld, so the
# PID and a counter, not the time, guarantee a new folder; mkdir without -p
# fails if the folder already exists, so an earlier capture is never reused.
STAMP=$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null) || STAMP=unknown-time
[ -n "$STAMP" ] || STAMP=unknown-time
n=0
while :; do
    OUT="$PARENT/atm-capture-$STAMP-$$-$n"
    if [ ! -e "$OUT" ] && mkdir "$OUT" 2>/dev/null; then break; fi
    n=$((n + 1))
    if [ "$n" -gt 50 ]; then echo "cannot create a new capture folder in $PARENT" >&2; exit 1; fi
done
mkdir "$OUT/items" || { echo "cannot write to $OUT" >&2; exit 1; }

WRITE_FAIL=0
have() { command -v "$1" >/dev/null 2>&1; }

if have sha256sum; then HASH_TOOL=sha256sum; else HASH_TOOL=none; fi
hash_file() {
    if [ "$HASH_TOOL" = sha256sum ]; then
        h=$(sha256sum "$1" 2>/dev/null) && [ -n "$h" ] && { printf '%s\n' "${h%% *}"; return 0; }
    fi
    echo unavailable
}
size_file() { s=$(wc -c < "$1" 2>/dev/null | tr -d ' ') && [ -n "$s" ] && echo "$s" || echo ""; }

# head -c bounds every file read. If it is missing, files are read with cat
# and the capture records that no limit applied.
if have head && [ "$(printf abc | head -c 2 2>/dev/null)" = ab ]; then HEAD_C=yes; else HEAD_C=no; fi
LIMIT_READ=$((ITEM_LIMIT + 1))
read_bounded() {
    if [ "$HEAD_C" = yes ]; then head -c "$LIMIT_READ" "$1"; else cat "$1"; fi
}
read_small() {
    if [ "$HEAD_C" = yes ]; then head -c 256 "$1"; else head -n 4 "$1"; fi
}
if have readlink; then READLINK=yes; else READLINK=no; fi

uptime_now() { u=$(head -n 1 "$ROOT/proc/uptime" 2>/dev/null) && echo "${u%% *}" || echo unknown; }

info() { printf '%s=%s\n' "$1" "$2" >> "$OUT/capture-info.txt" || WRITE_FAIL=1; }

: > "$OUT/capture-info.txt" || { echo "cannot write to $OUT" >&2; exit 1; }
info capture_version "$CAPTURE_VERSION"
info capture_format "$CAPTURE_FORMAT"
info script_sha256 "$(hash_file "$0")"
info script_path "$0"
info started_utc "$STAMP"
info started_uptime "$(uptime_now)"
info uid "$(id -u 2>/dev/null || echo unknown)"
info fixture_root "${ROOT:-none}"
info path_override "${ATM_CAPTURE_PATH:-none}"
info item_limit "$ITEM_LIMIT"
info head_c "$HEAD_C"
info hash_tool "$HASH_TOOL"
info tar_tool "$(have tar && echo yes || echo no)"
info find_tool "$(have find && echo yes || echo no)"
info readlink_tool "$READLINK"
if have busybox; then info busybox "$(busybox 2>/dev/null | head -n 1)"; else info busybox none; fi
info output_dir "$OUT"

cat > "$OUT/PRIVATE-README.txt" <<'EOF' || WRITE_FAIL=1
This folder is a raw ATM7039S V3 capture. It can contain the board serial
number (kernel command line, boot log, device tree) and other identifiers.
Do not edit, rename or delete anything inside it. Copy the whole folder to a
computer, keep it private, and share only the parsed, redacted summary.
EOF

printf '%s\n' "$ALLOWLIST" > "$OUT/allowlist.txt" || WRITE_FAIL=1
printf 'id\tkind\ttarget\tstatus\tbytes\tsha256\tnote\n' > "$OUT/manifest.tsv" || WRITE_FAIL=1

# Classify a failed read from its error text.
classify() {
    if grep -q -i 'permission denied' "$1" 2>/dev/null; then echo denied
    elif grep -q -i -e 'not supported' -e 'invalid argument' "$1" 2>/dev/null; then echo unsupported
    else echo error
    fi
}

run_cmd() {
    # Only fixed command strings from the allowlist reach this function.
    case "$1" in
        'uname -a') uname -a ;;
        'dmesg') dmesg ;;
        *) echo "command not in allowlist: $1" >&2; return 97 ;;
    esac
}

safe_name() {
    case "$1" in
        ''|.|..|*[!A-Za-z0-9_.:@+,-]*) return 1 ;;
    esac
    return 0
}

# Attribute files read for each entry of a probed directory. Card serial
# numbers (serial, cid, csd) and manufacturing dates are deliberately absent.
probe_attrs() {
    case "$1" in
        /sys/block) echo 'removable ro size dev ext_range device/type device/name device/manfid device/oemid' ;;
        /sys/bus/mmc/devices) echo 'type name manfid oemid' ;;
        /sys/class/mmc_host) echo '' ;;
    esac
}

one_line() { tr '\t\n\r' '   '; }

probe_dir() {
    base="$ROOT$1"
    [ -d "$base" ] || return 3
    attrs=$(probe_attrs "$1")
    count=0
    for entry in "$base"/*; do
        [ -e "$entry" ] || [ -L "$entry" ] || continue
        name=${entry##*/}
        if ! safe_name "$name"; then printf 'skipped\tunsafe-name\n'; continue; fi
        count=$((count + 1))
        if [ "$count" -gt 64 ]; then printf 'skipped\tentry-limit\n'; break; fi
        printf 'entry\t%s\n' "$name"
        if [ -L "$entry" ]; then
            if [ "$READLINK" = yes ]; then
                l=$(readlink "$entry" 2>/dev/null)
                printf 'link\t%s\t%s\n' "$name" "$(printf '%s' "$l" | one_line)"
            else
                printf 'link\t%s\treadlink-unavailable\n' "$name"
            fi
        fi
        for a in $attrs; do
            f="$entry/$a"
            if [ ! -e "$f" ]; then printf 'attr\t%s\t%s\tmissing\t\n' "$name" "$a"; continue; fi
            if v=$(read_small "$f" 2>/dev/null); then
                printf 'attr\t%s\t%s\tok\t%s\n' "$name" "$a" "$(printf '%s' "$v" | one_line)"
            else
                printf 'attr\t%s\t%s\terror\t\n' "$name" "$a"
            fi
        done
    done
    return 0
}

# Resolve the device-tree directory to its physical path and accept it only
# if it is one of the two kernel exports; a link pointing anywhere else is
# rejected rather than followed.
dt_resolve() {
    src="$ROOT$1"
    [ -d "$src" ] || return 1
    phys=$(cd "$src" 2>/dev/null && pwd -P) || return 2
    case "$phys" in
        "$ROOT/proc/device-tree"|"$ROOT/sys/firmware/devicetree/base") printf '%s\n' "$phys"; return 0 ;;
    esac
    return 3
}

is_essential() {
    for e in $ESSENTIAL; do [ "$e" = "$1" ] && return 0; done
    return 1
}

C_OK=0; C_MISSING=0; C_DENIED=0; C_ERROR=0; C_TRUNC=0; C_UNSUP=0; C_REJECT=0
ESSENTIAL_BAD=""

# Here-document, not a pipeline: the loop runs in this shell, so counters and
# WRITE_FAIL survive it.
while IFS='|' read -r id kind target; do
    [ -n "$id" ] || continue
    case "$kind" in
        tree) dest="$OUT/items/$id.tar" ;;
        *) dest="$OUT/items/$id.out" ;;
    esac
    err="$OUT/items/$id.err"
    status=ok
    note=""
    case "$kind" in
        file)
            src="$ROOT$target"
            if [ ! -e "$src" ]; then
                status=missing
            elif [ ! -r "$src" ]; then
                status=denied
            elif ! read_bounded "$src" > "$dest" 2> "$err"; then
                status=$(classify "$err")
            else
                sz=$(size_file "$dest")
                if [ -n "$sz" ] && [ "$sz" -gt "$ITEM_LIMIT" ]; then status=truncated; note="limit=$ITEM_LIMIT"; fi
                [ "$HEAD_C" = yes ] || note="unbounded-read"
            fi
            ;;
        cmd)
            if [ -n "$ROOT" ]; then
                if [ -e "$ROOT/.cmd/$id" ]; then
                    cat "$ROOT/.cmd/$id" > "$dest" 2> "$err" < /dev/null || status=error
                else
                    status=missing
                fi
            elif ! have "${target%% *}"; then
                status=unsupported; note="command-not-found"
            else
                run_cmd "$target" > "$dest" 2> "$err" < /dev/null
                rc=$?
                if [ "$rc" -ne 0 ]; then status=$(classify "$err"); note="rc=$rc"; fi
            fi
            ;;
        probe)
            probe_dir "$target" > "$dest" 2> "$err" < /dev/null
            rc=$?
            if [ "$rc" -eq 3 ]; then status=missing; rm -f "$dest"
            elif [ "$rc" -ne 0 ]; then status=error; note="rc=$rc"
            fi
            ;;
        tree|treeindex)
            phys=$(dt_resolve "$target")
            rc=$?
            if [ "$rc" -eq 1 ]; then
                status=missing
            elif [ "$rc" -ne 0 ]; then
                status=rejected; note="unapproved-resolution"
            elif [ "$kind" = tree ] && ! have tar; then
                status=unsupported; note="tar-not-found"
            elif [ "$kind" = treeindex ] && ! have find; then
                status=unsupported; note="find-not-found"
            else
                note="resolved=${phys#"$ROOT"}"
                if [ "$kind" = tree ]; then
                    (cd "$phys" && tar -cf "$dest" .) 2> "$err" < /dev/null
                    rc=$?
                else
                    (cd "$phys" && { find . -type d | sed 's/^/d /'; find . -type f | sed 's/^/f /'; find . -type l | sed 's/^/l /'; }) > "$dest" 2> "$err" < /dev/null
                    rc=$?
                    [ -s "$err" ] && rc=1
                fi
                if [ "$rc" -ne 0 ]; then status=$(classify "$err"); note="$note rc=$rc"; fi
            fi
            ;;
        *)
            status=error
            echo "unknown kind $kind" > "$err"
            ;;
    esac
    [ -s "$err" ] || rm -f "$err"
    case "$status" in
        ok) C_OK=$((C_OK + 1)) ;;
        missing) C_MISSING=$((C_MISSING + 1)) ;;
        denied) C_DENIED=$((C_DENIED + 1)) ;;
        truncated) C_TRUNC=$((C_TRUNC + 1)) ;;
        unsupported) C_UNSUP=$((C_UNSUP + 1)) ;;
        rejected) C_REJECT=$((C_REJECT + 1)) ;;
        *) C_ERROR=$((C_ERROR + 1)) ;;
    esac
    if [ "$status" != ok ] && is_essential "$id"; then ESSENTIAL_BAD="$ESSENTIAL_BAD $id"; fi
    if [ -f "$dest" ]; then
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$kind" "$target" "$status" "$(size_file "$dest")" "$(hash_file "$dest")" "$note" >> "$OUT/manifest.tsv" || WRITE_FAIL=1
    else
        printf '%s\t%s\t%s\t%s\t\t\t%s\n' "$id" "$kind" "$target" "$status" "$note" >> "$OUT/manifest.tsv" || WRITE_FAIL=1
    fi
done <<EOF
$ALLOWLIST
EOF

if [ -n "$ESSENTIAL_BAD" ] || [ "$WRITE_FAIL" -ne 0 ]; then CAPTURE_STATUS=partial; else CAPTURE_STATUS=complete; fi
info finished_utc "$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || echo unknown-time)"
info finished_uptime "$(uptime_now)"
info counts "ok=$C_OK missing=$C_MISSING denied=$C_DENIED error=$C_ERROR truncated=$C_TRUNC unsupported=$C_UNSUP rejected=$C_REJECT"
info essential_not_ok "${ESSENTIAL_BAD# }"
info write_failures "$WRITE_FAIL"
info capture_status "$CAPTURE_STATUS"
info manifest_sha256 "$(hash_file "$OUT/manifest.tsv")"
sync
if [ "$WRITE_FAIL" -ne 0 ]; then
    echo "Capture INCOMPLETE: writing to $OUT failed (card full or read-only?)" >&2
    exit 2
fi
: > "$OUT/DONE" || { echo "Capture INCOMPLETE: cannot write DONE marker" >&2; exit 2; }
sync
echo "Capture $CAPTURE_STATUS: $OUT"
exit 0
