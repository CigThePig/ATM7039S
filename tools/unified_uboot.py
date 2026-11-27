"""Bounded U-Boot consumers and boot-file validation for the unified path."""
import struct

import boot_chain as boot
from unified_loader import BoundaryError

GD = 0x03E80000
SP = 0x03F00000
# These are anchored to the pinned A32 binaries. The offsets below must remain
# the actual byte/word loads of the corresponding AFI getters.
GETTERS = {
    'mode': (0x050041D4, 'ldreq', None),
    'device': (0x05004208, 'ldrbeq', 0x305),
    'uart': (0x0500423C, 'ldrbeq', 0x306),
    'pad': (0x05004270, 'ldrbeq', 0x307),
    'baud': (0x050042A4, 'ldreq', 0x308),
    'size': (0x050042DC, 'ldreq', 0x30C),
}


def afi_consumers(ub, raw):
    raw = boot.checked_afi(raw)
    fn = int(boot.dram_init(ub)['function'], 16)
    calls = boot.call_log(ub, fn, fn + 0x30)
    printf = [c['target'] for c in calls if boot.describe(ub, c['args'][0]) == 'mem-size=%ldMB\n']
    if len(printf) != 1 or calls[0]['target'] != GETTERS['size'][0]:
        raise BoundaryError('uboot-initialization-failure', 'DRAM initialization anchors differ')
    afi_getters = {}
    machine = boot.Emulator(boot._uboot_emu(ub), stubs={printf[0]: ('printf', lambda e: 0)})
    machine.uc.mem_write(boot.AFI_VA, raw)

    def execute(entry):
        if not machine.call(entry, sp=SP, extra_regs={9: GD}) or machine.error:
            raise BoundaryError('uboot-initialization-failure', machine.error or f'no return from {entry:#x}')
        return machine.reg(0)

    for name, (entry, load, offset) in GETTERS.items():
        if offset is not None and not any(ins.mnemonic == load and f'#{offset:#x}]' in ins.op_str
                                         for ins in boot.disasm(ub, entry, 10)):
            raise BoundaryError('uboot-initialization-failure', f'AFI getter anchor differs: {name}')
        afi_getters[name] = execute(entry)
    if execute(fn) != 0:
        raise BoundaryError('uboot-initialization-failure', 'dram_init returned failure')
    memory = machine.u32(GD + 0x34)
    return dict(address=hex(boot.AFI_VA), exact_hex=machine.read(boot.AFI_VA, 16).hex(),
                sha256=boot.sha(machine.read(boot.AFI_VA, 16)), reserved_byte_3=raw[3], getters=afi_getters,
                dram_init=hex(fn), gd_ram_size=memory, gd_ram_size_offset='0x34',
                fallback_used=memory != afi_getters['size'])


def legacy_image(data, image_type, max_size, *, os_id=5):
    if len(data) < 64:
        raise BoundaryError('invalid-image', 'truncated legacy image header')
    header = boot.uimage_info(data)
    if (not all(header[k] for k in ('magic_ok', 'header_crc_ok', 'data_crc_ok')) or
            not 0 < header['size'] <= max_size or len(data) < header['size'] + 64):
        raise BoundaryError('invalid-image', 'legacy image magic, CRC or size check failed')
    if (header['os'], header['arch'], header['type'], header['compression']) != (os_id, 2, image_type, 0):
        raise BoundaryError('invalid-image', 'unsupported legacy image OS, architecture, type or compression')
    return header


def fdt_layout(data):
    """Validate the header sections and return the original reservation tuples."""
    if len(data) < 40:
        raise BoundaryError('invalid-image', 'truncated device-tree header')
    magic, total, tree, strings, reserve, version, compatible, _, strings_len, tree_len = struct.unpack_from(
        '>10I', data)
    if not (magic == boot.FDT_MAGIC and 40 <= total <= len(data) and version == 17 and compatible <= 17 and
            40 <= reserve < tree <= tree + tree_len <= strings <= strings + strings_len <= total and
            reserve % 8 == 0 and tree % 4 == 0):
        raise BoundaryError('invalid-image', 'unsupported or invalid device-tree header and sections')
    reservations = []
    while reserve + 16 <= tree:
        start, length = struct.unpack_from('>QQ', data, reserve)
        if not (start or length):
            break
        if not length:
            raise BoundaryError('invalid-image', 'empty device-tree reservation')
        reservations.append((start, length))
        reserve += 16
    else:
        raise BoundaryError('invalid-image', 'unterminated device-tree reservations')
    # Validate token framing within the header's declared sections before
    # executing libfdt. String and property lengths cannot bleed into padding.
    offset, depth, root_seen = tree, 0, False
    while offset + 4 <= tree + tree_len:
        token = struct.unpack_from('>I', data, offset)[0]
        offset += 4
        if token == 1:
            end = data.find(b'\0', offset, tree + tree_len)
            if end < 0 or depth == 0 and (root_seen or end != offset):
                break
            root_seen, depth = True, depth + 1
            offset = (end + 4) & ~3
        elif token == 2:
            if not depth:
                break
            depth -= 1
        elif token == 3:
            if not depth or offset + 8 > tree + tree_len:
                break
            length, name = struct.unpack_from('>II', data, offset)
            if name >= strings_len or data.find(b'\0', strings + name, strings + strings_len) < 0:
                break
            offset += 8 + ((length + 3) & ~3)
        elif token == 9 and not depth and root_seen and offset == tree + tree_len:
            return total, reservations
        elif token != 4:
            break
    raise BoundaryError('invalid-image', 'malformed device-tree structure')
