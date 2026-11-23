#!/bin/sh
# ATM7039S read-only runtime capture.
#
# Reads a fixed allowlist of ordinary kernel-exported files and runs a fixed
# set of read-only commands, writing results only into a new output directory.
# It never writes to /sys or /proc, never opens /dev/mem or I2C, never mounts,
# loads modules, changes clocks/CPU/power state or reads PMIC-backed
# power_supply attributes. See device/README.md before running it.
#
# Usage: sh capture.sh [OUTPUT_PARENT]
#   OUTPUT_PARENT defaults to the directory containing this script.
#   sh capture.sh --list   prints the allowlist and exits without reading it.
#
# Testing only: ATM_CAPTURE_ROOT=/fixture makes every item read
# $ATM_CAPTURE_ROOT/<path> (file items) or $ATM_CAPTURE_ROOT/.cmd/<id>
# (command items) instead of the live system.

CAPTURE_VERSION=2
set -u
umask 022

# Allowlist: id|kind|target. kind: file (copied with cat), cmd (fixed command,
# no arguments taken from input), tree (tar of a read-only directory).
# Keep in sync with tools/runtime_capture.py; the parser rejects captures whose
# recorded allowlist differs from a known script version.
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
meminfo|file|/proc/meminfo
iomem|file|/proc/iomem
interrupts|file|/proc/interrupts
modules|file|/proc/modules
mounts|file|/proc/mounts
partitions|file|/proc/partitions
block-links|cmd|ls -l /sys/block
mmc-links|cmd|ls -l /sys/bus/mmc/devices
fb|file|/proc/fb
fb0-name|file|/sys/class/graphics/fb0/name
fb0-modes|file|/sys/class/graphics/fb0/modes
fb0-virtual_size|file|/sys/class/graphics/fb0/virtual_size
fb0-bits_per_pixel|file|/sys/class/graphics/fb0/bits_per_pixel
fb0-stride|file|/sys/class/graphics/fb0/stride
pvr-version|file|/proc/pvr/version
os-release|file|/etc/os-release
batocera-version|file|/usr/share/batocera/batocera.version
kconfig|file|/proc/config.gz
fdt|file|/sys/firmware/fdt
device-tree|tree|/proc/device-tree
dmesg|cmd|dmesg'

if [ "${1:-}" = "--list" ]; then
    printf '%s\n' "$ALLOWLIST"
    exit 0
fi

ROOT="${ATM_CAPTURE_ROOT:-}"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PARENT="${1:-$SCRIPT_DIR}"
# Absolute path: the tree item changes directory before writing its archive.
mkdir -p "$PARENT" && PARENT=$(cd "$PARENT" && pwd) || { echo "cannot use $PARENT" >&2; exit 1; }
# FAT-safe name: no colons. Seconds plus PID avoid collisions on repeated runs.
STAMP=$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || echo unknown-time)
OUT="$PARENT/atm-capture-$STAMP-$$"
if [ -e "$OUT" ]; then echo "refusing to reuse existing $OUT" >&2; exit 1; fi
mkdir -p "$OUT/items" || { echo "cannot create $OUT" >&2; exit 1; }

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        echo unavailable
    fi
}

size_file() { wc -c < "$1" | tr -d ' '; }

run_cmd() {
    # Only fixed command strings from the allowlist reach this function.
    case "$1" in
        'uname -a') uname -a ;;
        'ls -l /sys/block') ls -l /sys/block ;;
        'ls -l /sys/bus/mmc/devices') ls -l /sys/bus/mmc/devices ;;
        'dmesg') dmesg ;;
        *) echo "command not in allowlist: $1" >&2; return 97 ;;
    esac
}

{
    echo "capture_version=$CAPTURE_VERSION"
    echo "script_sha256=$(hash_file "$0")"
    echo "started_utc=$STAMP"
    echo "uid=$(id -u 2>/dev/null || echo unknown)"
    echo "fixture_root=${ROOT:-none}"
    echo "output_dir=$OUT"
} > "$OUT/capture-info.txt"

printf '%s\n' "$ALLOWLIST" > "$OUT/allowlist.txt"
printf 'id\tkind\ttarget\tstatus\tbytes\tsha256\n' > "$OUT/manifest.tsv"

printf '%s\n' "$ALLOWLIST" | while IFS='|' read -r id kind target; do
    [ -n "$id" ] || continue
    case "$kind" in
        tree) dest="$OUT/items/$id.tar" ;;
        *) dest="$OUT/items/$id.out" ;;
    esac
    err="$OUT/items/$id.err"
    status=ok
    case "$kind" in
        file)
            src="$ROOT$target"
            if [ ! -e "$src" ]; then
                status=missing
            elif ! cat "$src" > "$dest" 2> "$err"; then
                status=error
            fi
            ;;
        cmd)
            if [ -n "$ROOT" ]; then
                if [ -e "$ROOT/.cmd/$id" ]; then
                    cat "$ROOT/.cmd/$id" > "$dest" 2> "$err" || status=error
                else
                    status=missing
                fi
            elif ! run_cmd "$target" > "$dest" 2> "$err"; then
                status=error
            fi
            ;;
        tree)
            src="$ROOT$target"
            if [ ! -d "$src" ]; then
                status=missing
            elif ! command -v tar >/dev/null 2>&1; then
                status=unavailable
            elif ! (cd "$src/.." && tar -cf "$dest" "$(basename "$src")") 2> "$err"; then
                status=error
            fi
            ;;
        *)
            status=error
            echo "unknown kind $kind" > "$err"
            ;;
    esac
    [ -s "$err" ] || rm -f "$err"
    if [ -f "$dest" ]; then
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$kind" "$target" "$status" "$(size_file "$dest")" "$(hash_file "$dest")" >> "$OUT/manifest.tsv"
    else
        printf '%s\t%s\t%s\t%s\t\t\n' "$id" "$kind" "$target" "$status" >> "$OUT/manifest.tsv"
    fi
done

echo "finished_utc=$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || echo unknown-time)" >> "$OUT/capture-info.txt"
echo "manifest_sha256=$(hash_file "$OUT/manifest.tsv")" >> "$OUT/capture-info.txt"
: > "$OUT/DONE"
sync
echo "Capture written to $OUT"
