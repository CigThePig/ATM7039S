#!/usr/bin/env python3
"""Parse the Actions (Owl/ATM7039S) raw SD early-loader region without executing it.

Structure recovered from four Anbernic RG35XX stock releases and Koriki v1.0
(see reports/anbernic-stock-reverse-engineering.md):

* ``ActBrm`` trailers: the 12 bytes ``"ActBrm" 0xAA 0x55 <u32 checksum>`` end a
  block. The stored checksum equals (sum of little-endian u32 words from the
  block start up to, but excluding, the checksum word) + 0x1234, modulo 2**32.
  Block starts are not stored in the trailer; this tool reports every
  sector-aligned start for which the rule holds (zero padding makes several
  starts equivalent) and the latest non-zero sector at or after that start.
* ``PACK`` directory at loader offset 0x2000: u32 member count at +0x3c and
  64-byte entries from +0x40: 16-byte name, then u32 size and offset in 512-byte
  sectors, and a u32 load address.
* ``bootloader.ini`` DRAM record: field meanings come from the loader's own
  printf format ("DRAM init mode%d,type%d,%dcs,x%dbus,rcc0x%x,wrodt%d,rdodt%d,
  drv%x,%dMHz"); offsets were established by tracing the copy into the
  0xb4070820 parameter block. Values are configuration, not measurements.

The layout is a description of observed releases, not a vendor specification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

SECTOR = 512
TAG = b'ActBrm\xaa\x55'
PACK_OFFSET = 0x2000
LIMIT = 4 * 1024 * 1024
INI_DRAM_FIELDS = (  # (name, ini offset, size) ; see module docstring
    ('ddr_clock_mhz', 0x1c, 2), ('capacity_mib', 0x20, 2), ('bus_width_selector', 0x24, 1),
    ('chip_selects', 0x25, 1), ('type', 0x26, 1), ('rcc', 0x27, 1), ('rdodt', 0x28, 1),
    ('wrodt', 0x29, 1), ('drv', 0x2a, 1))


def checksum(data, start, tag_offset):
    """Actions BROM-style checksum over [start, tag_offset+8)."""
    end = tag_offset + 8
    if start < 0 or start % 4 or end % 4 or end > len(data) or start >= end:
        raise ValueError('checksum range must be word aligned and within data')
    return (sum(struct.unpack_from(f'<{(end - start) // 4}I', data, start)) + 0x1234) & 0xffffffff


def trailers(data):
    out = []
    pos = data.find(TAG)
    while pos >= 0:
        if pos % 4 or pos + 12 > len(data):
            out.append(dict(offset=pos, valid=False, error='misaligned or truncated trailer'))
        else:
            stored = struct.unpack_from('<I', data, pos + 8)[0]
            starts = [s for s in range(0, pos, SECTOR) if checksum(data, s, pos) == stored]
            entry = dict(offset=pos, stored_checksum=f'0x{stored:08x}', valid=bool(starts))
            if starts:
                # Earliest non-zero sector inside the valid window is the most specific start.
                first_data = next((s for s in range(starts[0], pos + 1, SECTOR) if any(data[s:s + SECTOR])), starts[0])
                entry.update(earliest_valid_start=starts[0], first_nonzero_sector_in_window=first_data,
                             latest_valid_start=starts[-1], block_end=pos + 12)
            out.append(entry)
        pos = data.find(TAG, pos + 1)
    return out


def pack(data, offset=PACK_OFFSET):
    if data[offset:offset + 4] != b'PACK':
        return None
    count = struct.unpack_from('<I', data, offset + 0x3c)[0]
    if count > 16:
        raise ValueError('implausible PACK member count')
    members, slot = [], offset + 0x40
    while len(members) < count and slot + 64 <= offset + SECTOR:
        e = data[slot:slot + 64]
        slot += 64
        if not any(e):
            continue
        raw = e[:16].split(b'\0')[0]
        if not raw or any(c < 0x20 or c > 0x7e for c in raw) or b'/' in raw:
            raise ValueError('invalid PACK member name')
        size, start, load = struct.unpack_from('<3I', e, 16)
        lo, hi = start * SECTOR, (start + size) * SECTOR
        m = dict(name=raw.decode(), size_sectors=size, offset_sectors=start, load_address=f'0x{load:08x}',
                 byte_range=[lo, hi], within_region=hi <= len(data))
        if m['within_region']:
            m['sha256'] = hashlib.sha256(data[lo:hi]).hexdigest()
        members.append(m)
    if len(members) != count:
        raise ValueError('PACK directory shorter than its member count')
    return dict(offset=offset, count=count, members=members)


def dram_record(data, ini_offset):
    if ini_offset + 0x40 > len(data):
        raise ValueError('bootloader.ini outside region')
    ini = data[ini_offset:ini_offset + 0x40]
    rec = dict(ini_offset=ini_offset, version=ini[:4].split(b'\0')[0].decode('ascii', 'replace'))
    for name, off, size in INI_DRAM_FIELDS:
        rec[name] = int.from_bytes(ini[off:off + size], 'little')
    rec['bus_width_bits_as_printed'] = 16 if rec['bus_width_selector'] else 32
    uart_index, uart_pad = ini[0x0e], ini[0x0f]
    rec.update(uart_index=uart_index, uart_pad=uart_pad, uart_baudrate=struct.unpack_from('<I', ini, 0x10)[0])
    return rec


def parse(data):
    if len(data) > LIMIT:
        raise ValueError('loader region exceeds 4 MiB')
    result = dict(format_version=1, tool='actions_loader.py', size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                  trailers=trailers(data), pack=pack(data))
    if result['pack']:
        ini = next((m for m in result['pack']['members'] if m['name'] == 'bootloader.ini'), None)
        if ini and ini['within_region']:
            result['dram_config'] = dram_record(data, ini['byte_range'][0])
    nz = [i for i in range(0, len(data), SECTOR) if any(data[i:i + SECTOR])]
    result['last_nonzero_sector_end'] = (nz[-1] + SECTOR) if nz else 0
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input', type=Path, help='loader region (e.g. 448 sectors from disk offset 0x200200)')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    if not a.input.is_file():
        raise SystemExit('input must be a regular file')
    a.output.write_text(json.dumps(parse(a.input.read_bytes()), indent=1) + '\n')


if __name__ == '__main__':
    main()
