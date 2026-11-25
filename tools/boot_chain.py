#!/usr/bin/env python3
"""Reconstruct the Anbernic RG35XX (ATM7039S) stock boot chain from a pinned disk image.

Nothing here touches hardware. Every result is derived from the image's own bytes
by three independent methods, and each JSON record says which one produced it:

* ``static``: Capstone A32 decoding of instructions found by a string or literal
  anchor (not by hard-coded addresses), with register constant tracking up to
  each call. Branch structure is read from the instructions, not guessed.
* ``emulated``: bounded Unicorn execution of the firmware's own code. The only
  behaviour that is *supplied* rather than executed is listed per run under
  ``models``: the Boot ROM service at SRAM 0xb4060400 (absent from the image;
  reads are served from the disk image itself), named stubs (console output,
  DRAM training outcome, PMIC/clock setup) and explicit MMIO read oracles. An
  unmodelled peripheral read stops the run with an error instead of inventing a
  value.
* ``data``: parsing of headers, environments and filesystems.

Coordinates are always labelled: ``disk`` (byte offset in the image), ``loader``
(offset inside the 448-sector raw loader at disk 0x200200), ``uboot_payload``
(offset after the 64-byte uImage header), ``va`` (the address the code uses).

Usage::

    python tools/boot_chain.py analyze IMAGE --release NAME OUT.json [--sha256 HEX]
    python tools/boot_chain.py compare A.json B.json [C.json ...] OUT.json
    python tools/boot_chain.py sfvd IMAGE   # exit 1 if app.bin would rewrite bootloader.ini
    python tools/boot_chain.py trace A.json B.json ... OUT.json [--reference stock-20231014]

The layout knowledge (loader at sector 4097, U-Boot at 0x300000) is re-checked
against the image (ActBrm trailers, PACK directory, uImage CRCs) before use.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SECTOR = 512
LOADER_DISK = 0x200200
LOADER_SECTORS = 448
UBOOT_DISK = 0x300000
SRAM_BASE = 0xB4060000
SRAM_SIZE = 0x40000
ROM_SERVICE = 0xB4060400          # called with a selector in r9; no bytes in the image
ROM_ADFU = 0xFFFF0140             # literal used on the loader's failure path
AFI_VA = 0xB4060300
BOOT_CODE_VA = 0xB4064C00          # word written by block 0, read by bootloader.bin
APP_VA = 0x1000
MMIO = (0xB0000000, 0xB0400000)
UIMAGE_MAGIC = 0x27051956
FDT_MAGIC = 0xD00DFEED
TOOL_VERSION = 1


# --------------------------------------------------------------------------- binary helpers

class Blob:
    """A byte string mapped at a base address, with literal/string lookups."""

    def __init__(self, data, base, name):
        self.data, self.base, self.name = bytes(data), base, name
        self._words = None

    def __contains__(self, va):
        return self.base <= va < self.base + len(self.data)

    def off(self, va):
        if va not in self:
            raise ValueError(f'{self.name}: 0x{va:x} outside image')
        return va - self.base

    def word(self, va):
        return struct.unpack_from('<I', self.data, self.off(va))[0]

    def cstr(self, va, limit=256):
        if va not in self:
            return None
        o = va - self.base
        e = self.data.find(b'\0', o, o + limit)
        if e < 0:
            return None
        s = self.data[o:e]
        if not s or not all(32 <= c < 127 or c in (9, 10) for c in s):
            return None
        return s.decode()

    def strings(self, text):
        """VAs of every NUL-terminated occurrence of text (text may end with \\n)."""
        b, out, i = text.encode() + b'\0', [], -1
        while True:
            i = self.data.find(b, i + 1)
            if i < 0:
                return out
            out.append(self.base + i)

    def words_equal(self, value):
        if self._words is None:
            self._words = {}
            for o in range(0, len(self.data) - 3, 4):
                self._words.setdefault(struct.unpack_from('<I', self.data, o)[0], []).append(self.base + o)
        return self._words.get(value, [])

    def literal_users(self, text):
        """(literal-pool VA, string VA) pairs for a string."""
        return [(lit, s) for s in self.strings(text) for lit in self.words_equal(s)]


def _cs():
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    md.detail = True
    md.skipdata = True
    return md


def disasm(blob, va, count):
    md = _cs()
    o = blob.off(va)
    return list(md.disasm(blob.data[o:o + 4 * count], va))[:count]


def is_push_lr(insn):
    return insn.mnemonic in ('push', 'stmdb') and 'lr' in insn.op_str


def function_start(blob, va, limit=0x1000):
    """Nearest preceding 'push {..., lr}' (A32) at or before va."""
    md = _cs()
    a = va & ~3
    while a >= max(blob.base, va - limit):
        o = a - blob.base
        for i in md.disasm(blob.data[o:o + 4], a):
            if is_push_lr(i):
                return a
        a -= 4
    raise ValueError(f'no function start before 0x{va:x}')


def users_of_literal(blob, lit_va, window=0x1000):
    """Instructions 'ldr rX, [pc, #imm]' that load the word at lit_va."""
    md = _cs()
    out = []
    start = max(blob.base, lit_va - window)
    o = start - blob.base
    for i in md.disasm(blob.data[o:lit_va - blob.base], start):
        m = re.match(r'(\w+), \[pc, #(-?0x[0-9a-f]+|-?\d+)\]$', i.op_str)
        if i.mnemonic.startswith('ldr') and m and i.address + 8 + int(m.group(2), 0) == lit_va:
            out.append(i.address)
    return out


def functions_using(blob, text):
    """Function start addresses whose code loads a pointer to the string."""
    out = set()
    for lit, _ in blob.literal_users(text):
        for use in users_of_literal(blob, lit):
            out.add(function_start(blob, use))
    return sorted(out)


REG = {'r0': 0, 'r1': 1, 'r2': 2, 'r3': 3, 'r4': 4, 'r5': 5, 'r6': 6, 'r7': 7, 'r8': 8,
       'sb': 9, 'r9': 9, 'sl': 10, 'r10': 10, 'fp': 11, 'r11': 11, 'ip': 12, 'r12': 12}


def call_log(blob, start, end, tail_calls=False):
    """Linear constant tracking over [start, end): every direct call with r0-r3.

    Values are only known when set by mov/movw/ldr-literal/add-imm in straight-line
    code since the last call or branch target; anything else is None. This is a
    static description of call sites, not an execution trace.
    """
    md = _cs()
    o = blob.off(start)
    regs = {}
    calls = []
    targets = set()
    insns = list(md.disasm(blob.data[o:blob.off(end)], start))
    for i in insns:
        if i.mnemonic in ('b', 'bl') or i.mnemonic.startswith('b') and i.op_str.startswith('#'):
            if i.op_str.startswith('#'):
                targets.add(int(i.op_str[1:], 16))
    for i in insns:
        if i.address in targets:
            regs = {}
        m, ops = i.mnemonic, i.op_str
        mm = re.match(r'(\w+), (.*)$', ops)
        dst = REG.get(mm.group(1)) if mm else None
        if (m in ('bl', 'blx') or m == 'b' and tail_calls) and ops.startswith('#'):
            t = int(ops[1:], 16)
            if m == 'b' and start <= t < end:
                continue
            calls.append(dict(site=i.address, target=t, tail=m == 'b',
                              args=[regs.get(r) for r in range(4)]))
            regs = {k: v for k, v in regs.items() if k >= 4}
            continue
        if dst is None or len(m) > 6 and not m.startswith(('movw', 'movt')):
            continue
        src = mm.group(2)
        cond = len(m) > 3 and m[3:] in ('eq', 'ne', 'lt', 'gt', 'le', 'ge', 'hi', 'ls', 'cc', 'cs') if m.startswith(('mov', 'ldr', 'add')) else False
        if cond:
            regs.pop(dst, None)
            continue
        val = None
        if m == 'mov' and src.startswith('#'):
            val = int(src[1:], 0) & 0xffffffff
        elif m == 'mov' and src in REG:
            val = regs.get(REG[src])
        elif m == 'mvn' and src.startswith('#'):
            val = ~int(src[1:], 0) & 0xffffffff
        elif m == 'movw' and src.startswith('#'):
            val = int(src[1:], 0)
        elif m == 'ldr':
            lm = re.match(r'\[pc, #(-?0x[0-9a-f]+|-?\d+)\]$', src)
            if lm:
                val = blob.word(i.address + 8 + int(lm.group(1), 0))
        elif m == 'add':
            am = re.match(r'(\w+), #(-?0x[0-9a-f]+|-?\d+)$', src)
            if am and REG.get(am.group(1)) in regs and regs[REG[am.group(1)]] is not None:
                val = (regs[REG[am.group(1)]] + int(am.group(2), 0)) & 0xffffffff
        if val is None:
            regs.pop(dst, None)
        else:
            regs[dst] = val
    return calls


def function_end(blob, start, limit=0x2000):
    """End of a function: the first literal-pool word any of its pc-relative loads uses."""
    md = _cs()
    o = blob.off(start)
    end = start + limit
    for i in md.disasm(blob.data[o:o + limit], start):
        if i.address >= end:
            break
        m = re.search(r'\[pc, #(-?0x[0-9a-f]+|-?\d+)\]', i.op_str)
        if m:
            end = min(end, i.address + 8 + int(m.group(1), 0))
    return end


def describe(blob, value):
    s = blob.cstr(value) if value is not None else None
    return s if s is not None else (None if value is None else f'0x{value:x}')


def sha(b):
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------- emulation harness

class Unmodelled(RuntimeError):
    pass


class Emulator:
    """Bounded Unicorn A32 CPU with explicit call stubs and MMIO oracles.

    stubs: {va: (name, fn(emu) -> int|None)}; the stub's return goes to r0 and
    execution resumes at lr. stops: {va: name}; execution ends there.
    mmio: fn(address, size) -> int for reads in MMIO; None means unmodelled.
    """

    def __init__(self, regions, stubs=None, stops=None, mmio=None, limit=2_000_000):
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, \
            UC_HOOK_MEM_UNMAPPED
        from unicorn.arm_const import UC_ARM_REG_PC
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for base, size, data in regions:
            self.uc.mem_map(base, size)
            if data:
                self.uc.mem_write(base, bytes(data))
        self.uc.mem_map(MMIO[0], MMIO[1] - MMIO[0])
        self.uc.mem_map(0xFFFF0000, 0x10000)  # return/ROM-stop page: never executed (stops fire first)
        self.stubs, self.stops = stubs or {}, stops or {}
        self.mmio_oracle = mmio or (lambda a, s: None)
        self.limit, self.count = limit, 0
        self.stopped, self.error = None, None
        self.mmio_log, self.events = [], []
        self.uc.hook_add(UC_HOOK_CODE, self._code)
        self.uc.hook_add(UC_HOOK_MEM_READ, self._mread, begin=MMIO[0], end=MMIO[1] - 1)
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self._mwrite, begin=MMIO[0], end=MMIO[1] - 1)
        self.uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        self._pc = UC_ARM_REG_PC

    def reg(self, n, value=None):
        from unicorn import arm_const as a
        r = [a.UC_ARM_REG_R0, a.UC_ARM_REG_R1, a.UC_ARM_REG_R2, a.UC_ARM_REG_R3, a.UC_ARM_REG_R4,
             a.UC_ARM_REG_R5, a.UC_ARM_REG_R6, a.UC_ARM_REG_R7, a.UC_ARM_REG_R8, a.UC_ARM_REG_R9,
             a.UC_ARM_REG_R10, a.UC_ARM_REG_R11, a.UC_ARM_REG_R12, a.UC_ARM_REG_SP, a.UC_ARM_REG_LR,
             a.UC_ARM_REG_PC, a.UC_ARM_REG_CPSR][n]
        if value is None:
            return self.uc.reg_read(r)
        self.uc.reg_write(r, value & 0xffffffff)

    def read(self, va, n):
        return bytes(self.uc.mem_read(va, n))

    def u32(self, va):
        return struct.unpack('<I', self.read(va, 4))[0]

    def cstr(self, va, limit=512):
        out = bytearray()
        while len(out) < limit:
            c = self.read(va + len(out), 1)[0]
            if not c:
                return out.decode('latin1')
            out.append(c)
        return out.decode('latin1')

    def _code(self, uc, address, size, _):
        self.count += 1
        if self.count > self.limit:
            self.error = f'instruction limit {self.limit} reached at 0x{address:x}'
            uc.emu_stop()
            return
        if address in self.stops:
            self.stopped = dict(at=address, name=self.stops[address], regs=[self.reg(i) for i in range(16)])
            uc.emu_stop()
            return
        if address in self.stubs:
            name, fn = self.stubs[address]
            try:
                ret = fn(self)
            except Unmodelled as e:
                self.error = str(e)
                uc.emu_stop()
                return
            if ret is not None:
                self.reg(0, ret)
            self.reg(15, self.reg(14) & ~1)

    def _mread(self, uc, access, address, size, value, _):
        v = self.mmio_oracle(address, size)
        if v is None:
            self.error = f'unmodelled MMIO read 0x{address:08x} at pc 0x{self.reg(15):x}'
            uc.emu_stop()
            return
        uc.mem_write(address, struct.pack('<I', v & 0xffffffff)[:size])
        self.mmio_log.append(dict(op='read', address=f'0x{address:08x}', value=f'0x{v:x}'))

    def _mwrite(self, uc, access, address, size, value, _):
        self.mmio_log.append(dict(op='write', address=f'0x{address:08x}', value=f'0x{value & 0xffffffff:x}'))

    def _unmapped(self, uc, access, address, size, value, _):
        self.error = f'unmapped access 0x{address:08x} at pc 0x{self.reg(15):x}'
        return False

    def call(self, entry, args=(), sp=None, lr=0xFFFFFFF0, extra_regs=None):
        for i, v in enumerate(args):
            self.reg(i, v)
        for i, v in (extra_regs or {}).items():
            self.reg(i, v)
        if sp is not None:
            self.reg(13, sp)
        self.reg(14, lr)
        self.stops.setdefault(lr, 'return')
        self.reg(16, 0x1d3)  # SVC mode, IRQ/FIQ masked, ARM state
        try:
            self.uc.emu_start(entry, 0xFFFFFFFF)
        except Exception as e:  # unicorn raises after an unmapped access
            if not self.error:
                self.error = f'{type(e).__name__}: {e}'
        return self.stopped


# --------------------------------------------------------------------------- image access

def read_regions(image_path):
    """Return the raw loader, the U-Boot uImage and a disk reader; validates CRCs."""
    f = open(image_path, 'rb')
    f.seek(LOADER_DISK)
    loader = f.read(LOADER_SECTORS * SECTOR)
    f.seek(UBOOT_DISK)
    hdr = f.read(64)
    magic, hcrc, ts, size, load, ep, dcrc = struct.unpack('>7I', hdr[:28])
    if magic != UIMAGE_MAGIC:
        raise ValueError('no legacy uImage at disk 0x300000')
    payload = f.read(size)
    check = bytearray(hdr)
    check[4:8] = b'\0\0\0\0'
    uboot = dict(header_crc_ok=zlib.crc32(bytes(check)) == hcrc, data_crc_ok=zlib.crc32(payload) == dcrc,
                 size=size, load=load, entry=ep, timestamp=ts, name=hdr[32:64].rstrip(b'\0').decode('latin1'),
                 uimage_sha256=sha(hdr + payload), payload_sha256=sha(payload))
    return f, loader, hdr, payload, uboot


class Disk:
    """Read-only sector access to the image file (the storage model for ROM reads)."""

    def __init__(self, f):
        self.f = f
        f.seek(0, 2)
        self.size = f.tell()
        self.reads = []

    def sectors(self, lba, count):
        if lba < 0 or count < 0 or (lba + count) * SECTOR > self.size:
            raise Unmodelled(f'storage read beyond image: lba {lba} count {count}')
        self.f.seek(lba * SECTOR)
        return self.f.read(count * SECTOR)


# --------------------------------------------------------------------------- stage 0: loader block 0

def block0_dispatch(loader):
    """Emulate the loader's first 512 bytes for each boot-clock / SRAM-signature hypothesis.

    Block 0 reads 0xb01600a0 (CMU_DEVCLKEN0 in the related S500 clock tree) and a
    word at 0xb4060408 (all-zero on disk). Both are parameters here. Calls into the
    ROM service and into SRAM code that is absent from the image are recorded and
    return 0; the run stops when control leaves block 0 for good.
    """
    out = []
    sig_word = struct.unpack_from('<I', loader, 0x408)[0]
    lit = [struct.unpack_from('<I', loader, o)[0] for o in range(0x164, 0x190, 4)]
    signature = next((w for w in lit if (w & 0x0f000000) == 0x0b000000 and w >> 28 == 0xe), None)
    for clk_name, clk in (('bit7', 0x80), ('bit4', 0x10), ('neither', 0x0)):
        for sig in ((False, True) if clk == 0 else (False,)):
            sram = bytearray(SRAM_SIZE)
            sram[0:0x200] = loader[0:0x200]
            if sig and signature is not None:
                struct.pack_into('<I', sram, 0x408, signature)
            calls = []

            def absent(name):
                def fn(emu, name=name):
                    calls.append(dict(target=name, r0=f'0x{emu.reg(0):x}', r1=f'0x{emu.reg(1):x}',
                                      r2=f'0x{emu.reg(2):x}', r9=emu.reg(9)))
                    return 0
                return fn
            emu = Emulator([(SRAM_BASE, SRAM_SIZE, sram)], mmio=lambda a, s: clk if a == 0xB01600A0 else None)
            # Any branch into the zero hole (0x400..0x1e00) or to the ROM service is absent code.
            for d in disasm(Blob(loader[:0x200], SRAM_BASE, 'block0'), SRAM_BASE, 0x64):
                if d.mnemonic == 'bl' and d.op_str.startswith('#'):
                    t = int(d.op_str[1:], 16)
                    if not SRAM_BASE <= t < SRAM_BASE + 0x200:
                        emu.stubs[t] = (f'0x{t:x}', absent(f'0x{t:x}'))
            emu.stubs[ROM_SERVICE] = ('rom_service', absent('rom_service@0xb4060400'))
            emu.stops.update({0xB4065400: 'bootloader.bin entry 0xb4065400', 0xB40612B0: 'relocated reader 0xb40612b0',
                              0xB4060120: 'idle loop 0xb4060120', ROM_ADFU: 'ROM 0xffff0140'})
            stop = emu.call(SRAM_BASE, sp=SRAM_BASE + 0x3F000)
            code = struct.unpack('<I', emu.read(BOOT_CODE_VA, 4))[0]
            out.append(dict(cmu_devclken0=f'0x{clk:x}', cmu_bit=clk_name,
                            sram_0x408=('signature 0x%08x present' % signature) if sig else f'disk value 0x{sig_word:x}',
                            boot_code_written=code, calls=calls, stopped=stop['name'] if stop else None,
                            error=emu.error, instructions=emu.count))
    return dict(method='emulated', signature_literal=None if signature is None else f'0x{signature:08x}',
                disk_word_at_loader_0x408=f'0x{sig_word:08x}', runs=out,
                models=['MMIO 0xb01600a0 := hypothesis value (no other MMIO read occurs)',
                        'SRAM word 0xb4060408 := disk value or the literal block 0 compares it with',
                        'calls to 0xb4060400 and to SRAM code absent from the image return 0 and are logged'])


def block0_relocated_reader(loader):
    """Static facts about loader 0x200..0x400, the copy executed at 0xb4061200 on one path."""
    b = Blob(loader[0x200:0x400], 0xB4061200, 'reader')
    facts = []
    for i in disasm(b, 0xB4061200, 0x80):
        if i.mnemonic == 'bl' and i.op_str.startswith('#'):
            facts.append(dict(site=f'0x{i.address:x}', target=i.op_str[1:]))
    return dict(method='static', link_address='0xb4061200', disk_range='loader 0x200..0x400',
                direct_calls=facts,
                note='At 0xb4061200 the call to 0xb4060140 lands on the block-0 word-sum routine; the caller then '
                     'compares sum+0x1234 with the stored trailer word (ActBrm rule).')


# --------------------------------------------------------------------------- stage 1/2: bootloader.bin + app.bin

LOADER_STUBS = {
    0xB4066854: 'console printf',
    0xB40667A8: 'console putc',
    0xB4066784: 'UART init from parameter block',
    0xB4069440: 'early PMIC/clock setup (MMIO)',
    0xB4069254: 'PMIC status read (I2C)',
    0xB406A608: 'board init helper (MMIO)',
    0xB40699E8: 'PMIC register writes (I2C)',
    0xB40690B8: 'DRAM init mode 0 (see ddr_emulate.py; outcome supplied)',
    0xB406631C: 'DRAM memory test (PR #6; not executed)',
    0xB4065FC0: 'clock/PMIC setup (MMIO)',
    0xB4065F70: 'clock/PMIC setup (MMIO)',
    0xB4065E48: 'storage clock setup (MMIO; prints emmc/spi clk)',
}


def loader_main(loader, disk, ram_mib=256):
    """Emulate bootloader.bin from 0xb4065400 to the jump into app.bin.

    The SRAM holds what block 0 and the ROM placed there on the SD path (loader
    bytes 0x0..0x33c00 from the image; block 0's ROM read covers 0x5400.. and the
    ini is reloaded by bootloader.bin itself). Reads through the ROM service
    (r9=4: r0=sector, r1=count, r2=destination) are served from the disk image.
    """
    sram = bytearray(SRAM_SIZE)
    sram[0:0x33C00] = loader[0:0x33C00]
    # Areas the on-disk image leaves zero (0x400..0x1e00 hole) stay zero: the ROM
    # service itself is modelled at its entry point, nothing else of the hole runs.
    printed, services = [], []

    def printf(emu):
        fmt = emu.cstr(emu.reg(0))
        args = [emu.reg(1), emu.reg(2), emu.reg(3)]
        printed.append(_cfmt(fmt, args, emu))
        return 0

    def service(emu):
        sel = emu.reg(9)
        rec = dict(r9=sel, r0=emu.reg(0), r1=emu.reg(1), r2=emu.reg(2))
        if sel == 4:
            lba, count, dest = emu.reg(0), emu.reg(1), emu.reg(2)
            data = disk.sectors(lba, count)
            emu.uc.mem_write(dest, data)
            rec.update(kind='read', disk_offset=f'0x{lba * SECTOR:x}', bytes=len(data), dest=f'0x{dest:x}',
                       sha256=sha(data))
            services.append(rec)
            return 0
        services.append(rec)
        raise Unmodelled(f'ROM service selector r9={sel} not modelled')

    def dram(emu):
        # Supplied outcome: the parameter block capacity field holds the MEM-006 hypothesis.
        blk = emu.reg(0)
        emu.uc.mem_write(blk + 2, struct.pack('<H', ram_mib))
        return 0

    stubs = {}
    for va, name in LOADER_STUBS.items():
        stubs[va] = (name, printf if va == 0xB4066854 else (dram if va == 0xB40690B8 else (lambda emu: 0)))
    stubs[ROM_SERVICE] = ('Boot ROM service (r9 selector)', service)
    regions = [(SRAM_BASE, SRAM_SIZE, sram), (0, 0x08000000, None)]
    emu = Emulator(regions, stubs=stubs, stops={APP_VA: 'app.bin entry 0x1000', ROM_ADFU: 'ROM 0xffff0140 (ADFU)'},
                   mmio=lambda a, s: None)
    emu.uc.mem_write(BOOT_CODE_VA, struct.pack('<I', 0))  # SD0 code written by block 0 (see block0 runs)
    stop = emu.call(0xB4065400, sp=SRAM_BASE + 0x3F000)
    afi = emu.read(AFI_VA, 16)
    result = dict(method='emulated', entry='0xb4065400', boot_code=0, stopped=stop['name'] if stop else None,
                  error=emu.error, instructions=emu.count,
                  r0_at_app_entry=None if not stop else f"0x{stop['regs'][0]:x}",
                  console=printed, storage_reads=services, afi=decode_afi(afi), afi_raw=afi.hex(),
                  models=['ROM service r9=4 := copy sectors from the disk image (successful read)',
                          f'DRAM init outcome := success, capacity {ram_mib} MiB (MEM-006 hypothesis)'] +
                         [f'stub 0x{k:x}: {v}' for k, v in sorted(LOADER_STUBS.items()) if k != 0xB40690B8],
                  mmio_accesses=len(emu.mmio_log))
    if stop and stop['name'].startswith('app.bin'):
        result['app_bin_in_ram_sha256'] = sha(emu.read(APP_VA, 0x1F000))
        hdr = emu.read(0x300000, 64)
        result['uboot_header_buffer'] = dict(va='0x300000', sha256=sha(hdr))
        result['uboot_in_ram_first_word'] = f'0x{emu.u32(0x05000000):08x}'
    return result


def _cfmt(fmt, args, emu):
    out, ai = '', 0

    def nxt():
        nonlocal ai
        v = args[ai] if ai < len(args) else 0
        ai += 1
        return v
    for m in re.finditer(r'%([-0#]*)(\d*)(l*)([dxusc%])|[^%]+|%', fmt):
        if m.group(0) == '%' or m.group(4) is None:
            out += m.group(0)
            continue
        c = m.group(4)
        if c == '%':
            out += '%'
        elif c == 's':
            out += emu.cstr(nxt())
        elif c == 'c':
            out += chr(nxt() & 0xff)
        else:
            v = nxt()
            if c == 'd':
                v = v - (1 << 32) if v & 0x80000000 else v
                out += str(v)
            elif c == 'u':
                out += str(v)
            else:
                w = m.group(2)
                out += format(v, ('0' + w if m.group(1) == '0' and w else '') + 'x')
    return out


def decode_afi(b):
    magic, mode, dev, uart, pad, baud, size = struct.unpack('<4sBBBBII', b)
    return dict(magic=magic.rstrip(b'\0').decode('latin1'), boot_mode=mode, boot_dev=f'0x{dev:02x}',
                uart_index=uart, uart_pad=pad, uart_baudrate=baud, ddr_size=f'0x{size:x}')


def boot_code_map(loader):
    """Emulate 0xb4066588 (boot code -> AFI boot_dev) for every code 0..7."""
    sram = bytearray(SRAM_SIZE)
    sram[0:0x33C00] = loader[0:0x33C00]
    rows = []
    for code in range(8):
        emu = Emulator([(SRAM_BASE, SRAM_SIZE, sram)], stops={0xB4066500: 'AFI writer 0xb4066500'})
        emu.uc.mem_write(BOOT_CODE_VA, struct.pack('<I', code))
        stop = emu.call(0xB4066588, sp=SRAM_BASE + 0x3F000)
        rows.append(dict(code=code, boot_mode=stop['regs'][0] if stop else None,
                         boot_dev=f"0x{stop['regs'][1]:02x}" if stop else None, error=emu.error))
    return dict(method='emulated', function='0xb4066588', tail_call='0xb4066500', rows=rows)


def app_entry(app):
    """Static facts for app.bin (loaded at 0x1000)."""
    b = Blob(app, APP_VA, 'app.bin')
    first = disasm(b, APP_VA, 13)
    store = next((b.word(i.address + 8 + int(re.search(r'#(0x[0-9a-f]+)', i.op_str).group(1), 16))
                  for i in first[:1] if i.mnemonic == 'ldr'), None)
    msr = any(i.mnemonic == 'msr' for i in first)
    cpsr = next((int(i.op_str.split('#')[1], 0) for i in first if i.mnemonic == 'orr' and '#' in i.op_str), None)
    main = next((int(i.op_str[1:], 16) for i in first if i.mnemonic == 'bl'), None)
    final = next((i for i in first if i.mnemonic == 'blx'), None)
    # main: the SFVD constant and the write-back call
    sfvd = b.words_equal(0x44564653)
    calls = call_log(b, main, main + 0xDC) if main else []
    return dict(method='static', entry='0x1000', saves_r0_to=None if store is None else f'0x{store:x}',
                sets_cpsr_mode=None if cpsr is None else f'0x{cpsr:x}', switches_mode=msr,
                main=None if main is None else f'0x{main:x}',
                jumps_to_saved_r0=bool(final and final.op_str in ('r1', 'r0')),
                sfvd_literals=[f'0x{x:x}' for x in sfvd],
                main_calls=[dict(site=f"0x{c['site']:x}", target=f"0x{c['target']:x}",
                                 args=[describe(b, a) for a in c['args']]) for c in calls])


def app_writeback(app):
    """Recover app.bin's write-back of bootloader.ini (static; tail-call arguments)."""
    b = Blob(app, APP_VA, 'app.bin')
    writer = functions_using(b, 'mmc write failed\n')
    out = dict(method='static', mmc_block_write=[f'0x{w:x}' for w in writer])
    lits = [lit for lit, _ in b.literal_users('SFVD')]
    if not lits or not writer:
        return out
    fn = function_start(b, users_of_literal(b, lits[0])[0])
    calls = call_log(b, fn, function_end(b, fn), tail_calls=True)
    for c in calls:
        if c['target'] in writer:
            out.update(function=f'0x{fn:x}', site=f"0x{c['site']:x}", tail_call=c['tail'],
                       start_lba=c['args'][1], sectors=c['args'][2],
                       source=None if c['args'][3] is None else f"0x{c['args'][3]:x}",
                       disk_offset=None if c['args'][1] is None else f"0x{c['args'][1] * SECTOR:x}",
                       loader_offset=None if c['args'][1] is None else f"0x{c['args'][1] * SECTOR - LOADER_DISK:x}")
    others = [dict(site=f"0x{c['site']:x}", target=f"0x{c['target']:x}") for c in calls if c['tail']]
    out['tail_calls'] = others
    return out


# --------------------------------------------------------------------------- U-Boot

def default_env(ub):
    # The default environment is a run of NUL-separated "name=value" strings that
    # starts with bootcmd (CONFIG_BOOTCOMMAND); accept the first such run of >= 8.
    i = -1
    while True:
        i = ub.data.find(b'bootcmd=', i + 1)
        if i < 0:
            raise ValueError('no default environment found')
        run, j = 0, i
        while ub.data[j] != 0 and run < 8:
            e = ub.data.find(b'\0', j)
            if b'=' not in ub.data[j:e]:
                break
            run, j = run + 1, e + 1
        if run >= 8:
            break
    env, order = {}, []
    while ub.data[i] != 0:
        e = ub.data.find(b'\0', i)
        k, _, v = ub.data[i:e].decode('latin1').partition('=')
        env[k] = v
        order.append(k)
        i = e + 1
    return dict(method='data', payload_offset=f'0x{ub.data.find(b"bootcmd=") :x}', variables=env)


def find_check_boot_flag(ub):
    fns = functions_using(ub, 'bootmode = %d\n')
    if len(fns) != 1:
        raise ValueError(f'check_boot_flag anchor ambiguous: {fns}')
    return fns[0]


def init_sequence_r(ub, cbf):
    refs = ub.words_equal(cbf)
    if len(refs) != 1:
        raise ValueError('init_sequence_r anchor ambiguous')
    text_end = ub.base + len(ub.data)
    lo = hi = refs[0]
    while ub.word(lo - 4) and ub.base <= ub.word(lo - 4) < text_end and ub.word(lo - 4) % 4 == 0:
        lo -= 4
    while hi + 4 < text_end and ub.base <= ub.word(hi + 4) < text_end and ub.word(hi + 4) % 4 == 0:
        hi += 4
    labels = [('begin to check power!\n', 'power_init_board'), ('NAND:  ', 'initr_nand'), ('MMC:   ', 'initr_mmc'),
              ('load-environment', 'initr_env'), ('bootmode = %d\n', 'check_boot_flag'),
              ('boot_logo.bmp.gz', 'splash_image_init'), ('stdin', 'console_init_r'), ('Net:   ', 'initr_net'),
              ('ethaddr', 'initr_ethaddr'), ('nulldev', 'stdio_add_devices')]
    named = {}
    for text, name in labels:
        for f in functions_using(ub, text):
            named.setdefault(f, name)
    entries = []
    for k, va in enumerate(range(lo, hi + 4, 4)):
        f = ub.word(va)
        entries.append(dict(index=k, table_va=f'0x{va:x}', function=f'0x{f:x}', label=named.get(f)))
    idx = next(e['index'] for e in entries if e['label'] == 'check_boot_flag')
    env = next((e['index'] for e in entries if e['label'] == 'initr_env'), None)
    return dict(method='static', table=f'0x{lo:x}..0x{hi + 4:x}', entries=entries,
                check_boot_flag_after_initr_env=env is not None and env < idx,
                note='Labels come from string references inside each entry; unlabelled entries are not named.')


def _uboot_emu(ub, extra=()):
    regions = [(0x05000000, (len(ub.data) + 0x40 + 0xFFFFF) & ~0xFFFFF, b'\0' * 0x40 + ub.data),
               (SRAM_BASE, SRAM_SIZE, None), (0x0, 0x04000000, None)] + list(extra)
    return regions


def afi_bytes(mode=0, dev=0x20, uart=3, pad=0, baud=115200, size=256 << 20, magic=b'AFI\0'):
    return struct.pack('<4sBBBBII', magic, mode, dev, uart, pad, baud, size)


def check_boot_flag_table(ub, cbf):
    """Emulate check_boot_flag with the real AFI getters for each (boot_mode, boot_dev)."""
    calls = call_log(ub, cbf, function_end(ub, cbf))
    setenv = {c['target'] for c in calls if describe(ub, c['args'][0]) == 'bootcmd'}
    printf = {c['target'] for c in calls if (describe(ub, c['args'][0]) or '').startswith('bootmode')}
    if len(setenv) != 1 or len(printf) != 1:
        raise ValueError('cannot identify setenv/printf in check_boot_flag')
    setenv, printf = setenv.pop(), printf.pop()
    getters = sorted({c['target'] for c in calls} - {setenv, printf})
    rows = []
    cases = [(None, None)] + [(m, d) for m in (0, 1) for d in (0x00, 0x01, 0x20, 0x21, 0x22, 0x30, 0x31, 0x40)]
    for mode, dev in cases:
        sets, out = [], []
        emu = Emulator(_uboot_emu(ub), stubs={
            setenv: ('setenv', lambda e: sets.append((e.cstr(e.reg(0)), e.cstr(e.reg(1)))) or 0),
            printf: ('printf', lambda e: out.append(_cfmt(e.cstr(e.reg(0)), [e.reg(1), e.reg(2), e.reg(3)], e)) or 0)})
        if mode is not None:
            emu.uc.mem_write(AFI_VA, afi_bytes(mode, dev))
        emu.call(cbf, sp=0x03F00000)
        rows.append(dict(afi='absent' if mode is None else 'present', boot_mode=mode,
                         boot_dev=None if dev is None else f'0x{dev:02x}',
                         setenv=dict(sets), printed=out, error=emu.error))
    return dict(method='emulated', function=f'0x{cbf:x}', setenv=f'0x{setenv:x}', printf=f'0x{printf:x}',
                afi_getters=[f'0x{g:x}' for g in getters], rows=rows,
                models=['setenv/printf replaced by recorders; AFI getters and memcmp execute from the image',
                        'AFI at 0xb4060300 := hypothesis (or zero for "absent")'])


def afi_getter_defaults(ub, getters):
    """Run each getter with no AFI magic: the values U-Boot falls back to."""
    out = []
    for g in getters:
        res = {}
        for label, blob in (('absent', b'\0' * 16), ('present', afi_bytes(0, 0x20, 3, 0, 115200, 256 << 20))):
            emu = Emulator(_uboot_emu(ub))
            emu.uc.mem_write(AFI_VA, blob)
            emu.call(int(g, 16), sp=0x03F00000)
            res[label] = None if emu.error else emu.reg(0)
        out.append(dict(getter=g, value_without_magic=res['absent'], value_with_sd_afi=res['present']))
    return dict(method='emulated', rows=out)


def env_storage(ub, disk):
    fns = functions_using(ub, '*** Error - No Valid Environment Area found\n')
    rel = fns[0] if fns else None
    offsets, dev = None, None
    md = _cs()
    # offset helper: 'cmp r1,#0; moveq r0,#A; movne r0,#B'
    for o in range(0, len(ub.data) - 12, 4):
        ins = list(md.disasm(ub.data[o:o + 12], ub.base + o))
        if len(ins) == 3 and ins[0].mnemonic == 'cmp' and ins[1].mnemonic == 'moveq' and ins[2].mnemonic == 'movne' \
                and ins[1].op_str.startswith('r0, #') and ins[2].op_str.startswith('r0, #'):
            a, b = int(ins[1].op_str.split('#')[1], 0), int(ins[2].op_str.split('#')[1], 0)
            if 0x1000 <= a < 0x100000 and 0x1000 <= b < 0x100000:
                offsets = (a, b, ub.base + o)
                break
    if rel:
        first = call_log(ub, rel, rel + 0x20)
        if first:
            dev = first[0]['args'][0]
    size = None
    if rel:
        for i in disasm(ub, rel, 0xA0):
            m = re.search(r'\[pc, #(0x[0-9a-f]+)\]', i.op_str)
            if i.mnemonic == 'ldr' and m:
                w = ub.word(i.address + 8 + int(m.group(1), 16))
                if 0x1000 <= w + 5 <= 0x100000 and (w + 5) & 0xfff == 0:
                    size = w + 5
                    break
    copies = []
    if offsets and size:
        for off in offsets[:2]:
            raw = disk.sectors(off // SECTOR, size // SECTOR)
            crc = struct.unpack('<I', raw[:4])[0]
            copies.append(dict(disk_offset=f'0x{off:x}', crc_valid=zlib.crc32(raw[5:]) == crc,
                               all_zero=not any(raw)))
    return dict(method='static+data', env_relocate_spec=None if rel is None else f'0x{rel:x}',
                mmc_device=dev, offsets=None if not offsets else [f'0x{offsets[0]:x}', f'0x{offsets[1]:x}'],
                offset_helper=None if not offsets else f'0x{offsets[2]:x}', size=None if size is None else f'0x{size:x}',
                redundant=True, image_copies=copies,
                note='Offsets are bytes on the MMC device the env driver opens; for an SD-only board that device '
                     'is the second registered controller (see embedded_fdt), not the microSD card.')


def boot_jump(ub):
    fns = functions_using(ub, '\nStarting kernel ...%s\n\n')
    if len(fns) != 1:
        raise ValueError('boot_jump_linux anchor ambiguous')
    fn = fns[0]
    ins = disasm(ub, fn, 0x30)
    text = [(i.address, i.mnemonic, i.op_str) for i in ins]
    ep = next((re.match(r'(\w+), \[r0, #(0x[0-9a-f]+)\]', o) for a, m, o in text if m == 'ldr' and '[r0, #' in o), None)
    ftaddr = [o for a, m, o in text if m.startswith('ldr') and re.search(r'\[r5, #0xa[04]\]', o)]
    blx = [o for a, m, o in text if m == 'blx']
    cleanup = None
    first_blx = next((a for a, m, o in text if m == 'blx'), None)
    for a, m, o in text:
        if m == 'bl' and o.startswith('#') and first_blx and a < first_blx:
            cleanup = int(o[1:], 16)  # last direct call before the jump: cleanup_before_linux
    machid = bool(ub.literal_users('machid'))
    return dict(method='static', function=f'0x{fn:x}',
                kernel_entry_field=None if not ep else f'images+{ep.group(2)} (ep)',
                r2_source=ftaddr, call=blx, machid_env_override=machid,
                cleanup_before_linux=None if cleanup is None else f'0x{cleanup:x}',
                registers_at_entry=dict(r0='0', r1='gd->bd->bi_arch_number or env machid',
                                        r2='images->ft_addr when images->ft_len != 0, else bd->bi_boot_params'))


def cleanup_state(ub, fn):
    """Classify cleanup_before_linux callees by their CP15/CPSR operations."""
    calls = [int(i.op_str[1:], 16) for i in disasm(ub, fn, 9) if i.mnemonic == 'bl']
    found = []
    for c in calls:
        ins = disasm(ub, c, 12)
        ops = [f'{i.mnemonic} {i.op_str}' for i in ins]
        kind = 'no-op' if ops and ops[0] == 'bx lr' else 'other'
        joined = ' ; '.join(ops)
        if 'msr cpsr_c' in joined and '#0xc0' in joined:
            kind = 'mask IRQ+FIQ (CPSR |= 0xc0)'
        elif 'c1, c0, #0' in joined and 'bic' in joined:
            m = re.search(r'bic \w+, \w+, #(0x[0-9a-f]+|\d+)', joined)
            mask = int(m.group(1), 0) if m else 0
            kind = {0x1000: 'SCTLR.I cleared (icache off)', 5: 'SCTLR.C and SCTLR.M cleared (dcache+MMU off) after flush'}.get(mask, f'SCTLR bic 0x{mask:x}')
        elif 'c7, c5, #0' in joined:
            kind = 'invalidate icache + branch predictor, DSB/ISB'
        elif ops and ops[0].startswith('push') and any('bl ' in x for x in ops[:4]):
            kind = 'cache maintenance wrapper'
        found.append(dict(function=f'0x{c:x}', effect=kind))
    return dict(method='static', function=f'0x{fn:x}', callees=found)


def owl_fdt_setup_strings(ub):
    fns = functions_using(ub, 'owl_boot_fdt_setup %s\n')
    fn = fns[0]
    end = function_end(ub, fn)
    log = call_log(ub, fn, end)
    seq = []
    for c in log:
        a = [describe(ub, x) for x in c['args']]
        if any(isinstance(x, str) and not x.startswith('0x') for x in a) or c['args'][1] in (1, 2, 3):
            seq.append(dict(site=f"0x{c['site']:x}", target=f"0x{c['target']:x}", args=a))
    return dict(method='static', function=f'0x{fn:x}', end=f'0x{end:x}', calls=seq,
                note='Arguments shown as null are stack buffers filled by the preceding strcpy/sprintf call; '
                     'r1 of the bootargs helper is its mode (1 prepend, 2 append).')


def bootargs_helper(ub, fn_setup):
    """Emulate boot_append_remove_args for modes 1..3 to fix its semantics."""
    log = call_log(ub, fn_setup, function_end(ub, fn_setup))
    cand = {}
    for c in log:
        if c['args'][1] in (1, 2):
            cand[c['target']] = cand.get(c['target'], 0) + 1
    helper = max(cand, key=cand.get)
    inner = call_log(ub, helper, helper + 0x130)
    getenv = next(c['target'] for c in inner if describe(ub, c['args'][0]) == 'bootargs')
    setenv = [c['target'] for c in inner if describe(ub, c['args'][0]) == 'bootargs' and c['target'] != getenv]
    rows = []
    for mode in (1, 2, 3):
        store = {'bootargs': 'A B C'}
        scratch = 0x03E00000

        def ge(e):
            s = store.get(e.cstr(e.reg(0)))
            if s is None:
                return 0
            e.uc.mem_write(scratch, s.encode() + b'\0')
            return scratch

        def se(e):
            store[e.cstr(e.reg(0))] = e.cstr(e.reg(1))
            return 0
        stubs = {getenv: ('getenv', ge)}
        for s in setenv:
            stubs[s] = ('setenv', se)
        emu = Emulator(_uboot_emu(ub), stubs=stubs)
        emu.uc.mem_write(0x03D00000, b'B\0')
        emu.call(helper, (0x03D00000, mode), sp=0x03F00000)
        rows.append(dict(mode=mode, before='A B C', argument='B', after=store['bootargs'], error=emu.error,
                         note=None if mode != 3 else 'mode 3 never initialises its stack buffer from bootargs before '
                         'searching it; with the zeroed emulator stack the result is empty. Real output depends on '
                         'stale stack contents. owl_boot_fdt_setup does not use mode 3.'))
    return dict(method='emulated', function=f'0x{helper:x}', getenv=f'0x{getenv:x}',
                setenv=[f'0x{s:x}' for s in setenv], rows=rows)


def fdt_setup_emulation(ub, setup, helper, fdt, afi, env, gd_flags=0, sn=None, fdt_addr=0x03800000):
    """Execute the vendor owl_boot_fdt_setup on the shipped DTB; return /chosen/bootargs.

    Replaced: getenv/setenv (a Python dict holding the environment after uEnv.txt
    import), printf, and read_mi_item("SN") (returns -1, or the supplied SN).
    Everything else, including libfdt, runs from the U-Boot image.
    """
    fn = int(setup['function'], 16)
    log = call_log(ub, fn, int(setup['end'], 16))
    getenv, setenv = int(helper['getenv'], 16), int(helper['setenv'][0], 16)
    printf = next(c['target'] for c in log if describe(ub, c['args'][0]) == 'owl_boot_fdt_setup %s\n')
    mi = next(c['target'] for c in log if describe(ub, c['args'][0]) == 'SN')
    store = dict(env)
    heap = [0x03C00000]
    printed = []

    def put(text):
        a = heap[0]
        heap[0] += (len(text) + 16) & ~7
        emu.uc.mem_write(a, text.encode('latin1') + b'\0')
        return a

    def ge(e):
        v = store.get(e.cstr(e.reg(0)))
        return 0 if v is None else put(v)

    def se(e):
        k = e.cstr(e.reg(0))
        if e.reg(1):
            store[k] = e.cstr(e.reg(1))
        else:
            store.pop(k, None)
        return 0

    def pf(e):
        printed.append(_cfmt(e.cstr(e.reg(0)), [e.reg(1), e.reg(2), e.reg(3)], e))
        return 0

    def mi_item(e):
        if sn is None:
            return 0xFFFFFFFF
        e.uc.mem_write(e.reg(1), sn.encode() + b'\0')
        return len(sn)
    gd = 0x03E80000
    emu = Emulator(_uboot_emu(ub), stubs={getenv: ('getenv', ge), setenv: ('setenv', se), printf: ('printf', pf),
                                         mi: ('read_mi_item', mi_item)})
    padded = bytearray(fdt) + bytes(0x3000)
    struct.pack_into('>I', padded, 4, len(padded))  # boot_relocate_fdt in-place growth (fdt_high = ~0)
    emu.uc.mem_write(fdt_addr, bytes(padded))
    emu.uc.mem_write(AFI_VA, afi_bytes(afi['boot_mode'], int(afi['boot_dev'], 16), afi['uart_index'],
                                       afi['uart_pad'], afi['uart_baudrate'], int(afi['ddr_size'], 16)))
    emu.uc.mem_write(gd + 4, struct.pack('<I', gd_flags))
    emu.call(fn, (fdt_addr,), sp=0x03F00000, extra_regs={9: gd})
    total = struct.unpack('>I', emu.read(fdt_addr + 4, 4))[0]
    blob = emu.read(fdt_addr, min(total, len(padded)))
    chosen = next((props for path, props in _fdt_nodes(blob) if path == '/chosen'), {})
    return dict(method='emulated', function=f'0x{fn:x}', gd_flags=f'0x{gd_flags:x}', sn=sn,
                env_bootargs_after=store.get('bootargs'), dt_chosen_bootargs=chosen.get('bootargs'),
                console=printed, error=emu.error, instructions=emu.count,
                models=['getenv/setenv := dict (default env + uEnv.txt import)', 'printf recorded',
                        'read_mi_item("SN") := ' + ('-1 (not modelled)' if sn is None else 'supplied SN'),
                        'kernel.dtb copied to fdt_addr_r with +0x3000 pad (fdt_high = 0xffffffff)'])


def direct_callers(blob, target):
    out = []
    for o in range(0, len(blob.data) - 3, 4):
        w = struct.unpack_from('<I', blob.data, o)[0]
        if (w >> 28) != 0xF and (w & 0x0E000000) == 0x0A000000:
            off = ((w & 0xFFFFFF) ^ 0x800000) - 0x800000
            if blob.base + o + 8 + 4 * off == target:
                out.append(blob.base + o)
    return out


def handoff_emulation(ub, setup, helper, fdt, afi, env, rd, ram_size, gd_flags=0, sn=None,
                      fdt_addr=0x03800000):
    """Execute image_setup_linux (ramdisk/FDT placement, image_setup_libfdt, owl_boot_fdt_setup).

    The bootm_headers_t fields image_setup_linux reads are filled as boot_get_ramdisk
    and boot_get_fdt leave them for the shipped legacy ramdisk and raw DTB. The LMB
    holds one memory bank [0, ram_size) and no reservations (the in-place policy
    makes the result independent of U-Boot's own reservation). Replaced: getenv,
    setenv, printf/puts, read_mi_item. Everything else runs from the image.
    """
    owl = int(setup['function'], 16)
    callers = direct_callers(ub, owl)
    isl = function_start(ub, callers[0])
    log = call_log(ub, owl, int(setup['end'], 16))
    getenv, setenv = int(helper['getenv'], 16), int(helper['setenv'][0], 16)
    printf = next(c['target'] for c in log if describe(ub, c['args'][0]) == 'owl_boot_fdt_setup %s\n')
    mi = next(c['target'] for c in log if describe(ub, c['args'][0]) == 'SN')
    puts = set()
    for text in ('OK\n', '   Loading Ramdisk to %08lx, end %08lx ... '):
        for lit, _ in ub.literal_users(text):
            for use in users_of_literal(ub, lit):
                for c in call_log(ub, use, use + 8):
                    puts.add(c['target'])
    store = dict(env)
    heap = [0x03C00000]
    printed = []

    def put(text):
        a = heap[0]
        heap[0] += (len(text) + 16) & ~7
        emu.uc.mem_write(a, text.encode('latin1') + b'\0')
        return a

    def ge(e):
        v = store.get(e.cstr(e.reg(0)))
        return 0 if v is None else put(v)

    def se(e):
        k = e.cstr(e.reg(0))
        if e.reg(1):
            store[k] = e.cstr(e.reg(1))
        else:
            store.pop(k, None)
        return 0

    def pf(e):
        printed.append(_cfmt(e.cstr(e.reg(0)), [e.reg(1), e.reg(2), e.reg(3)], e))
        return 0

    def mi_item(e):
        if sn is None:
            return 0xFFFFFFFF
        e.uc.mem_write(e.reg(1), sn.encode() + b'\0')
        return len(sn)
    stubs = {getenv: ('getenv', ge), setenv: ('setenv', se), printf: ('printf', pf), mi: ('read_mi_item', mi_item)}
    for t in puts:
        stubs.setdefault(t, ('puts/printf', pf))
    emu = Emulator(_uboot_emu(ub), stubs=stubs)
    gd, bd, images = 0x03E80000, 0x03E81000, 0x03E82000
    emu.uc.mem_write(gd, struct.pack('<II', bd, gd_flags))
    emu.uc.mem_write(bd + 0x48, struct.pack('<II', 0, ram_size))
    emu.uc.mem_write(fdt_addr, bytes(fdt))
    hdr = bytearray(0x200)
    struct.pack_into('<IIII', hdr, 0x98, rd[0], rd[1], fdt_addr, len(fdt))
    lmb = struct.pack('<II', 1, ram_size) + struct.pack('<II', 0, ram_size) + bytes(64) + struct.pack('<II', 1, 0) + bytes(72)
    hdr[0xC4:0xC4 + len(lmb)] = lmb
    emu.uc.mem_write(images, bytes(hdr))
    emu.uc.mem_write(AFI_VA, afi_bytes(afi['boot_mode'], int(afi['boot_dev'], 16), afi['uart_index'],
                                       afi['uart_pad'], afi['uart_baudrate'], int(afi['ddr_size'], 16)))
    emu.call(isl, (images,), sp=0x03F00000, extra_regs={9: gd})
    ret = emu.reg(0)
    vals = struct.unpack('<IIIIII', emu.read(images + 0x98, 24))
    ft = vals[2]
    total = struct.unpack('>I', emu.read(ft + 4, 4))[0]
    blob = emu.read(ft, min(total, 0x40000))
    nodes = dict(_fdt_nodes(blob))
    chosen, memory = nodes.get('/chosen', {}), nodes.get('/memory', {})
    rsv = []
    off_rsv = struct.unpack('>I', blob[16:20])[0]
    while True:
        a, n = struct.unpack_from('>QQ', blob, off_rsv)
        if not (a or n):
            break
        rsv.append([f'0x{a:x}', f'0x{n:x}'])
        off_rsv += 16
    return dict(method='emulated', image_setup_linux=f'0x{isl:x}', return_value=ret, error=emu.error,
                instructions=emu.count, gd_flags=f'0x{gd_flags:x}',
                initrd_start=f'0x{vals[4]:x}', initrd_end=f'0x{vals[5]:x}', ft_addr=f'0x{ft:x}',
                fdt_totalsize_after=total, fdt_sha256_after=sha(blob),
                dt_memory_reg=memory.get('reg'), dt_chosen=chosen, dt_memreserve=rsv, console=printed,
                models=['bootm_headers_t: rd_start/rd_end = ramdisk payload, ft_addr/ft_len = raw DTB at fdt_addr_r',
                        f'LMB: one bank [0, 0x{ram_size:x}), no reservations', 'gd->bd->bi_dram[0] = {0, ram_size}',
                        'getenv/setenv := dict (default env + uEnv.txt import)', 'printf/puts recorded',
                        'read_mi_item("SN") := ' + ('-1 (not modelled)' if sn is None else 'supplied SN')])


def autoboot(ub, env):
    """bootdelay and the abort key the autoboot loop compares against."""
    fns = functions_using(ub, 'bootdelaykey')
    keys = []
    if fns:
        fn = fns[0]
        for va in range(function_end(ub, fn), function_end(ub, fn) + 0x40, 4):
            t = describe(ub, ub.word(va))
            if t and not t.startswith('0x'):
                keys.append(t)
    known = {'bootdelaykey', 'bootdelaykey2', 'bootstopkey', 'bootstopkey2'}
    default = [k for k in keys if k not in known and '%' not in k]
    return dict(method='static+data', function=None if not fns else f'0x{fns[0]:x}',
                bootdelay=env['variables'].get('bootdelay'), env_key_names=[k for k in keys if k in known],
                default_abort_key=default[0] if default else None,
                note='With bootdelay=0 the key loop still polls the console once before running bootcmd.')


def bd_arch_number_writers(ub):
    """Stores to gd->bd + 0x40 (bi_arch_number, kernel r1) reachable as 'ldr rX,[sb]; ...; str rY,[rX,#0x40]'."""
    md = _cs()
    ins = list(md.disasm(ub.data, ub.base))
    hits = []
    for k, i in enumerate(ins):
        m = re.match(r'(\w+), \[sb\]$', i.op_str)
        if i.mnemonic == 'ldr' and m:
            r = m.group(1)
            for j in ins[k + 1:k + 10]:
                if j.mnemonic.startswith('str') and re.search(r'\[' + r + r', #0x40\]', j.op_str):
                    hits.append(f'0x{j.address:x}')
                if j.op_str.startswith(r + ','):
                    break
    return dict(method='static', pattern='ldr rX,[sb] ... str rY,[rX,#0x40] within 9 instructions', writers=hits,
                conclusion='no writer found: bd is zeroed by reserve_board, so r1 = 0 unless env machid is set'
                if not hits else 'writers found; r1 depends on them')


def variant_strap(ub):
    fns = functions_using(ub, '-----s500 \n')
    if not fns:
        return dict(method='static', present=False)
    fn = fns[0]
    entry, callers = fn, []
    for t in range(fn - 0x10, fn + 4, 4):   # the probe starts two instructions before its push
        cs = direct_callers(ub, t)
        if cs:
            entry, callers = t, cs
    gpio = None
    for i in disasm(ub, entry, 0x20):
        m = re.match(r'r0, #(0x[0-9a-f]+|\d+)$', i.op_str)
        if i.mnemonic == 'mov' and m:
            gpio = int(m.group(1), 0)
            break
    callers_info = []
    for c in callers:
        cf = function_start(ub, c)
        log = call_log(ub, cf, function_end(ub, cf))
        callers_info.append(dict(site=f'0x{c:x}', function=f'0x{cf:x}',
                                 strings=[describe(ub, x['args'][0]) for x in log if describe(ub, x['args'][0]) and
                                          not describe(ub, x['args'][0]).startswith('0x')],
                                 calls=[f"0x{x['target']:x}" for x in log]))
    users = functions_using(ub, 'allenS500=1')
    return dict(method='static', present=True, function=f'0x{entry:x}', callers=callers_info, gpio=gpio,
                bank=None if gpio is None else 'ABCDE'[gpio // 32], bit=None if gpio is None else gpio % 32,
                allenS500_appended_in=[f'0x{u:x}' for u in users])


def embedded_fdt(ub):
    d = ub.data
    best = None
    i = -1
    while True:
        i = d.find(struct.pack('>I', FDT_MAGIC), i + 1)
        if i < 0:
            break
        total = struct.unpack_from('>I', d, i + 4)[0]
        ver = struct.unpack_from('>I', d, i + 20)[0]
        if ver == 17 and i + total <= len(d):
            best = (i, total)
    if not best:
        return dict(method='data', present=False)
    i, total = best
    nodes = _fdt_nodes(d[i:i + total])
    mmc = [dict(path=p, status=props.get('status'), reg=props.get('reg')) for p, props in nodes if '/mmc@' in p]
    return dict(method='data', payload_offset=f'0x{i:x}', size=total, sha256=sha(d[i:i + total]),
                model=next((props.get('model') for p, props in nodes if p == '/'), None), mmc=mmc,
                registration_order=[m['path'] for m in mmc if m['status'] in (None, 'okay')])


def _fdt_nodes(b):
    """Minimal FDT walker: [(path, {name: str|hex})] for string-ish/short props."""
    magic, total, off_struct, off_strings = struct.unpack_from('>4I', b, 0)
    if magic != FDT_MAGIC:
        raise ValueError('not an FDT')
    p, stack, out = off_struct, [], []
    props = None
    while True:
        tok = struct.unpack_from('>I', b, p)[0]
        p += 4
        if tok == 1:
            e = b.index(b'\0', p)
            name = b[p:e].decode('latin1')
            p = (e + 4) & ~3
            stack.append(name)
            props = {}
            out.append(('/' + '/'.join(x for x in stack if x), props))
        elif tok == 3:
            ln, no = struct.unpack_from('>II', b, p)
            p += 8
            val = b[p:p + ln]
            p = (p + ln + 3) & ~3
            e = b.index(b'\0', off_strings + no)
            pname = b[off_strings + no:e].decode('latin1')
            if val.endswith(b'\0') and all(32 <= c < 127 for c in val[:-1]) and len(val) > 1:
                props[pname] = val[:-1].decode()
            elif ln % 4 == 0 and ln <= 32:
                props[pname] = [f'0x{x:x}' for x in struct.unpack(f'>{ln // 4}I', val)]
            else:
                props[pname] = f'<{ln} bytes>'
        elif tok == 2:
            stack.pop()
        elif tok == 4:
            continue
        elif tok == 9:
            return out
        else:
            raise ValueError('bad FDT token')


def ramdisk_fdt_policy(ub, env):
    ih = env['variables'].get('initrd_high')
    fh = env['variables'].get('fdt_high')
    pad = None
    for fn in functions_using(ub, 'fdt_high'):
        for i in disasm(ub, fn, 0x60):
            m = re.match(r'\w+, \w+, #(0x[0-9a-f]+)$', i.op_str)
            if i.mnemonic == 'add' and m and int(m.group(1), 16) in (0x1000, 0x2000, 0x3000, 0x4000):
                pad = int(m.group(1), 16)
                break
    return dict(method='static+data', initrd_high=ih, fdt_high=fh,
                ramdisk_in_place=ih is not None and int(ih, 16) == 0xFFFFFFFF,
                fdt_in_place=fh is not None and int(fh, 16) == 0xFFFFFFFF,
                fdt_pad=None if pad is None else f'0x{pad:x}')


def dram_init(ub):
    fns = functions_using(ub, 'mem-size=%ldMB\n')
    fn = fns[0]
    vals = []
    for i in disasm(ub, fn, 12):
        if i.mnemonic in ('cmp', 'mov', 'movlo', 'movhs', 'movcc', 'movcs') and '#' in i.op_str:
            vals.append(f'{i.mnemonic} {i.op_str}')
    return dict(method='static', function=f'0x{fn:x}', immediates=vals,
                rule='ram_size = AFI ddr_size if >= 8 MiB else 0x1f000000 (496 MiB)')


def _fh_summary(ub):
    h = function_hashes(ub)
    flat = sorted(k for k, v in h.items() for _ in v)
    return dict(method='static', chunks=len(flat), digest=sha('\n'.join(flat).encode()),
                note='push-delimited chunks; branch immediates, in-image pointers and pc-relative load offsets masked')


def function_hashes(ub):
    """Split the text at 'push {...,lr}' and hash each chunk with branch/literal normalisation."""
    starts = []
    for o in range(0, len(ub.data) - 3, 4):
        w = struct.unpack_from('<I', ub.data, o)[0]
        if (w & 0xFFFF4000) == 0xE92D4000:  # push {..., lr}
            starts.append(o)
    out = {}
    lo, hi = ub.base, ub.base + len(ub.data)
    for a, b in zip(starts, starts[1:] + [len(ub.data)]):
        if b - a > 0x4000:
            b = a + 0x4000
        h = hashlib.sha256()
        for o in range(a, b, 4):
            w = struct.unpack_from('<I', ub.data, o)[0]
            if (w >> 28) != 0xF and (w & 0x0E000000) == 0x0A000000:
                w &= 0xFF000000
            elif lo <= w < hi:
                w = 0xDEADBEEF
            elif (w & 0x0F7F0000) == 0x051F0000:  # ldr rX, [pc, #imm]
                w &= 0xFFFFF000
            h.update(struct.pack('<I', w))
        out.setdefault(h.hexdigest()[:16], []).append(ub.base + a)
    return out


# --------------------------------------------------------------------------- boot files and handoff

def gpt_partition1(f):
    f.seek(512)
    h = f.read(92)
    if h[:8] != b'EFI PART':
        f.seek(446)
        e = f.read(16)
        return dict(scheme='mbr', start_lba=struct.unpack_from('<I', e, 8)[0], sectors=struct.unpack_from('<I', e, 12)[0])
    entries_lba, n, esz = struct.unpack_from('<QII', h, 72)
    f.seek(entries_lba * SECTOR)
    e = f.read(esz)
    first, last = struct.unpack_from('<QQ', e, 32)
    name = e[56:128].decode('utf-16le').rstrip('\0')
    return dict(scheme='gpt', start_lba=first, sectors=last - first + 1, name=name)


def fat_files(f, part, names):
    """Read named files from partition 1 (case-insensitive, like U-Boot's FAT lookup)."""
    from image_inventory import Window
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    out = {}
    with PyFatBytesIOFS(Window(f, part['start_lba'] * SECTOR, part['sectors'] * SECTOR)) as fs:
        listing = {n.lower(): n for n in fs.listdir('/')}
        for want in names:
            real = listing.get(want.lower())
            if real is None:
                out[want] = None
                continue
            with fs.openbin('/' + real) as s:
                out[want] = (real, s.read(64 * 1024 * 1024))
    return out


def uimage_info(b):
    magic, hcrc, ts, size, load, ep, dcrc, os_, arch, typ, comp = struct.unpack('>7I4B', b[:32])
    chk = bytearray(b[:64])
    chk[4:8] = b'\0\0\0\0'
    return dict(magic_ok=magic == UIMAGE_MAGIC, header_crc_ok=zlib.crc32(bytes(chk)) == hcrc,
                data_crc_ok=zlib.crc32(b[64:64 + size]) == dcrc, size=size, load=f'0x{load:x}', entry=f'0x{ep:x}',
                os=os_, arch=arch, type=typ, compression=comp, name=b[32:64].rstrip(b'\0').decode('latin1'))


def parse_uenv(text):
    """'env import -t' semantics: name=value lines; later lines override earlier ones."""
    out = {}
    for line in text.replace('\r', '').split('\n'):
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, _, v = line.partition('=')
        out[k] = v
    return out


def zimage_decompressed_size(payload):
    """Bounded gunzip of the first gzip stream in a zImage; returns its length."""
    i = payload.find(b'\x1f\x8b\x08')
    if i < 0:
        return None
    d = zlib.decompressobj(31)
    total = 0
    data = payload[i:]
    for k in range(0, len(data), 1 << 20):
        total += len(d.decompress(data[k:k + (1 << 20)], 64 << 20))
        if d.eof or total > 64 << 20:
            break
    return total


def memory_map(env_vars, files, uboot):
    """Placement of every image at bootm, from env addresses and image headers."""
    kaddr = int(env_vars['kernel_addr_r'], 16)
    raddr = int(env_vars['ramdisk_addr_r'], 16)
    faddr = int(env_vars['fdt_addr_r'], 16)
    k = files['uImage']
    r = files['ramdisk.img']
    fdt = files['kernel.dtb']
    rows = []
    kload = int(k['header']['load'], 16)
    rows.append(dict(item='kernel uImage header+payload', start=kaddr, end=kaddr + 64 + k['header']['size']))
    rows.append(dict(item='kernel zImage (payload)', start=kaddr + 64, end=kaddr + 64 + k['header']['size'],
                     xip=kaddr + 64 == kload))
    if k.get('decompressed_size'):
        rows.append(dict(item='decompressed kernel Image (written by the zImage decompressor)', start=kload,
                         end=kload + k['decompressed_size']))
    rows.append(dict(item='ramdisk payload (initrd, in place)', start=raddr + 64, end=raddr + 64 + r['header']['size']))
    rows.append(dict(item='device tree (in place, +0x3000 pad)', start=faddr, end=faddr + fdt['size'] + 0x3000))
    rows.append(dict(item='U-Boot as loaded (before relocation)', start=uboot['load'],
                     end=uboot['load'] + 64 + uboot['size']))
    rows.append(dict(item='U-Boot scriptaddr (uEnv.txt / boot.scr buffer)', start=int(env_vars.get('scriptaddr', '0'), 16),
                     end=int(env_vars.get('scriptaddr', '0'), 16) + 0x1000))
    overlaps = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if 'zImage' in a['item'] and 'header' in b['item'] or 'header' in a['item'] and 'zImage' in b['item']:
                continue
            if a['start'] < b['end'] and b['start'] < a['end']:
                expected = 'zImage' in a['item'] and 'decompressed' in b['item']
                overlaps.append(dict(a=a['item'], b=b['item'], expected=expected,
                                     why='the zImage decompressor relocates itself above its output before '
                                         'decompressing (arch/arm/boot/compressed/head.S)' if expected else None))
    for row in rows:
        row['start'], row['end'] = f"0x{row['start']:x}", f"0x{row['end']:x}"
    return dict(method='data', rows=rows, overlaps=overlaps,
                note='Addresses are U-Boot/Linux physical addresses (SDRAM base 0, MMU off at handoff). '
                     'The decompressed Image row is where the zImage writes its output, after U-Boot has exited.')


def bootargs_model(uenv_bootargs, afi, gd_flags=0, sn=None, s500_strap=False, have_strap=True):
    """Bootargs produced by the traced vendor owl_boot_fdt_setup for a non-PRODUCE boot.

    Order and modes come from the static call sequence and the emulated helper
    semantics (mode 1 prepends, mode 2 appends; no de-duplication). PRODUCE and
    recovery branches are listed by boot_chain.owl_fdt_setup_strings.
    """
    # Byte-exact: the helper formats "%s %s" with getenv("bootargs") or "" (no trimming).
    args = uenv_bootargs or ''

    def tail(x):
        nonlocal args
        args = args + ' ' + x

    def head(x):
        nonlocal args
        args = x + ' ' + args
    if gd_flags & 0x10000:
        for x in ('earlyprintk', 'clk_ignore_unused', 'selinux=0'):
            tail(x)
    tail('androidboot.dvfslevel=0x705x')
    if gd_flags & 0x40000:
        tail('androidboot.mode=charger')
    if have_strap and s500_strap:   # gd->flags bit 20, set by the GPIOC6 probe (230309 onward)
        tail('allenS500=1')
    head(f"console=ttyS{afi['uart_index']}")
    dev = int(afi['boot_dev'], 16)
    tail('androidboot.bootdev=sd' if dev > 1 else 'androidboot.bootdev=nand')
    name = {0x00: 'nand', 0x01: 'slcnand', 0x20: 'sd0', 0x21: 'sd1', 0x22: 'sd2', 0x30: 'sd02nand',
            0x31: 'sd02sd2', 0x40: 'nor'}.get(dev)
    if name:
        tail(f'boot_dev={name}')
    if sn is not None:
        tail(f'androidboot.serialno={sn}')
    return args


# --------------------------------------------------------------------------- top level

def dram_scenario_capacity(loader, scenario):
    """Capacity reported to U-Boot when the stock loader's own DRAM code runs under a named, synthetic
    hardware scenario (tools/dram_complete.py), instead of a supplied --ram-mib value."""
    import dram_complete
    mib, h = dram_complete.derived_capacity(loader, scenario)
    if mib is None:
        raise SystemExit(f'DRAM scenario {scenario!r}: loader does not reach U-Boot ({h["after_caller"]}, '
                         f'DRAM return {h["dram_return"]})')
    return mib, dict(scenario=scenario, dram_return=h['dram_return'], afi_ddr_size=hex(h['afi']['ddr_size']),
                     uboot_ram_size=hex(h['uboot']['gd_ram_size']), console=[x for x in h['prints'] if 'Cap' in x or 'ddr_test' in x or x.startswith('==')],
                     assumption='synthetic PUBL/uPCTL/PMIC responses and a DRAM aliasing hypothesis; not a hardware observation')


def analyze(image_path, release, expected_sha=None, ram_mib=256, dram_scenario=None):
    p = Path(image_path)
    if expected_sha:
        h = hashlib.sha256()
        with p.open('rb') as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b''):
                h.update(chunk)
        if h.hexdigest() != expected_sha:
            raise SystemExit('image SHA-256 mismatch')
    f, loader, uhdr, payload, uboot = read_regions(p)
    disk = Disk(f)
    app = loader[0x19000:0x38000]
    ub = Blob(payload, uboot['entry'], 'u-boot')
    derived = None
    if dram_scenario:
        ram_mib, derived = dram_scenario_capacity(loader, dram_scenario)
    res = dict(format_version=1, tool='boot_chain.py', tool_version=TOOL_VERSION, release=release,
               image_sha256=expected_sha,
               components=dict(loader=dict(disk_offset=f'0x{LOADER_DISK:x}', size=len(loader), sha256=sha(loader),
                                           bootloader_bin_code_sha256=sha(loader[0x4C00:0x33C00]),
                                           app_bin_sha256=sha(app), block0_sha256=sha(loader[:0x200]),
                                           ini_0x0_0x1000_sha256=sha(loader[0x2400:0x3400]),
                                           ini_0x1000_0x1400_sha256=sha(loader[0x3400:0x3800]),
                                           ini_0x1400_0x2800_sha256=sha(loader[0x3800:0x4C00])),
                               uboot=dict(disk_offset=f'0x{UBOOT_DISK:x}', **{k: (f'0x{v:x}' if k in ('load', 'entry') else v)
                                                                                 for k, v in uboot.items()})))
    res['loader'] = dict(block0=block0_dispatch(loader), relocated_reader=block0_relocated_reader(loader),
                         main=loader_main(loader, disk, ram_mib), boot_code_map=boot_code_map(loader),
                         app_entry=app_entry(app), app_writeback=app_writeback(app),
                         ini_sfvd=dict(method='data', offset='loader 0x2800 (ini+0x400, SRAM 0xb4062800)',
                                       magic=loader[0x2800:0x2804].decode('latin1'),
                                       value=f"0x{struct.unpack_from('<I', loader, 0x2804)[0]:08x}"))
    if derived:
        res['loader']['main']['dram_outcome'] = derived
        res['loader']['main']['models'][1] = (f'DRAM init outcome := derived by executing the loader DRAM code under '
                                             f'scenario {dram_scenario!r}: {ram_mib} MiB (synthetic responses)')
    env = default_env(ub)
    cbf = find_check_boot_flag(ub)
    cbt = check_boot_flag_table(ub, cbf)
    bj = boot_jump(ub)
    setup = owl_fdt_setup_strings(ub)
    res['uboot'] = dict(default_env=env, init_sequence_r=init_sequence_r(ub, cbf), check_boot_flag=cbt,
                        afi_getters=afi_getter_defaults(ub, cbt['afi_getters']), env_storage=env_storage(ub, disk),
                        embedded_fdt=embedded_fdt(ub), dram_init=dram_init(ub), ramdisk_fdt=ramdisk_fdt_policy(ub, env),
                        boot_jump=bj, cleanup=cleanup_state(ub, int(bj['cleanup_before_linux'], 16)),
                        owl_boot_fdt_setup=setup, bootargs_helper=bootargs_helper(ub, int(setup['function'], 16)),
                        variant_strap=variant_strap(ub), autoboot=autoboot(ub, env),
                        bi_arch_number=bd_arch_number_writers(ub), normalised_functions=_fh_summary(ub))
    part = gpt_partition1(f)
    files = {}
    try:
        raw = fat_files(f, part, ['uImage', 'ramdisk.img', 'kernel.dtb', 'uEnv.txt', 'boot.scr'])
    except ImportError:
        raw = {}
    for n, v in raw.items():
        if v is None:
            files[n] = None
            continue
        real, data = v
        rec = dict(fat_name=real, size=len(data), sha256=sha(data))
        if n in ('uImage', 'ramdisk.img'):
            rec['header'] = uimage_info(data)
            if n == 'uImage':
                rec['decompressed_size'] = zimage_decompressed_size(data[64:])
        elif n == 'kernel.dtb':
            rec['fdt_magic_ok'] = struct.unpack('>I', data[:4])[0] == FDT_MAGIC
        elif n == 'uEnv.txt':
            rec['variables'] = parse_uenv(data.decode('latin1'))
        files[n] = rec
    res['boot_files'] = dict(method='data', partition1=part, files=files)
    vars_ = dict(env['variables'])
    if files.get('uEnv.txt'):
        vars_.update(files['uEnv.txt']['variables'])
    if all(files.get(n) for n in ('uImage', 'ramdisk.img', 'kernel.dtb')):
        res['memory_map'] = memory_map(vars_, files, uboot)
    afi = res['loader']['main']['afi']
    strap = res['uboot']['variant_strap']['present']
    if files.get('kernel.dtb'):
        dtb = raw['kernel.dtb'][1]
        runs = []
        for flags in ((0, 0x100000) if strap else (0,)):
            runs.append(fdt_setup_emulation(ub, res['uboot']['owl_boot_fdt_setup'], res['uboot']['bootargs_helper'],
                                            dtb, afi, vars_, gd_flags=flags))
        res['handoff_bootargs'] = runs
        if res.get('memory_map'):
            rd_start = int(vars_['ramdisk_addr_r'], 16) + 64
            rd = (rd_start, rd_start + files['ramdisk.img']['header']['size'])
            ram = int(afi['ddr_size'], 16)
            ram = ram if ram >= 8 << 20 else 0x1F000000
            res['handoff'] = [handoff_emulation(ub, res['uboot']['owl_boot_fdt_setup'], res['uboot']['bootargs_helper'],
                                                dtb, afi, vars_, rd, ram, gd_flags=fl)
                              for fl in ((0, 0x100000) if strap else (0,))]
    res['bootargs'] = dict(method='model (static order + emulated helper)', inputs=dict(
        uenv_bootargs=vars_.get('bootargs'), afi=afi),
        gpio_low=bootargs_model(vars_.get('bootargs'), afi, have_strap=strap),
        gpio_high=bootargs_model(vars_.get('bootargs'), afi, s500_strap=True, have_strap=strap) if strap else None,
        unknown_terms=['androidboot.serialno=<SN> is appended only if read_mi_item("SN") succeeds (not modelled)'])
    return res


def compare(paths):
    docs = [json.loads(Path(p).read_text()) for p in paths]
    rows = {}
    keys = [('bootloader.bin code', ('components', 'loader', 'bootloader_bin_code_sha256')),
            ('app.bin', ('components', 'loader', 'app_bin_sha256')),
            ('block0', ('components', 'loader', 'block0_sha256')),
            ('ini 0x0-0x1000', ('components', 'loader', 'ini_0x0_0x1000_sha256')),
            ('ini 0x1000-0x1400', ('components', 'loader', 'ini_0x1000_0x1400_sha256')),
            ('ini 0x1400-0x2800', ('components', 'loader', 'ini_0x1400_0x2800_sha256')),
            ('u-boot payload', ('components', 'uboot', 'payload_sha256')),
            ('kernel uImage', ('boot_files', 'files', 'uImage', 'sha256')),
            ('ramdisk', ('boot_files', 'files', 'ramdisk.img', 'sha256')),
            ('kernel.dtb', ('boot_files', 'files', 'kernel.dtb', 'sha256')),
            ('uEnv.txt', ('boot_files', 'files', 'uEnv.txt', 'sha256'))]
    for label, path in keys:
        vals = []
        for d in docs:
            v = d
            for part in path:
                v = v.get(part) if isinstance(v, dict) else None
            vals.append(v)
        rows[label] = dict(values={d['release']: (v[:16] if isinstance(v, str) else v) for d, v in zip(docs, vals)},
                           identical=len(set(vals)) == 1)
    behav = {}
    for d in docs:
        u = d['uboot']
        behav[d['release']] = dict(
            check_boot_flag=[(r['boot_mode'], r['boot_dev'], r['setenv'].get('bootcmd')) for r in u['check_boot_flag']['rows']],
            env=u['default_env']['variables'], strap=u['variant_strap'], afi=d['loader']['main']['afi'],
            reads=[(r.get('disk_offset'), r.get('dest')) for r in d['loader']['main']['storage_reads']][:3],
            uboot_normalised_digest=u.get('normalised_functions', {}).get('digest'),
            uboot_read_bytes=sum(r.get('bytes', 0) for r in d['loader']['main']['storage_reads'][2:]),
            bootargs=d['bootargs'])
    first = docs[0]['release']
    diffs = {}
    for rel, b in behav.items():
        diffs[rel] = {k: (v == behav[first][k]) for k, v in b.items()}
    return dict(format_version=1, tool='boot_chain.py compare', releases=[d['release'] for d in docs],
                components=rows, behaviour_equal_to_first=diffs)


def _same(docs, getter):
    vals = [json.dumps(getter(d), sort_keys=True) for d in docs]
    return len(set(vals)) == 1


def build_trace(docs, reference):
    """Machine-readable boot-stage trace (the committed evidence) from per-release analyses."""
    ref = next(d for d in docs if d['release'] == reference)
    L, U = ref['loader'], ref['uboot']
    comp = ref['components']
    m = L['main']
    reads = m['storage_reads']
    ub_reads = reads[3:]
    ub_bytes = sum(r['bytes'] for r in ub_reads)
    files = ref['boot_files']['files']
    env = U['default_env']['variables']
    h0 = ref['handoff'][0]
    sd0 = next(r for r in L['block0']['runs'] if r['cmu_bit'] == 'bit4')
    bl_sha = comp['loader']['bootloader_bin_code_sha256']
    ub_sha = comp['uboot']['uimage_sha256']

    def rel_all(getter):
        return dict(identical_in=[d['release'] for d in docs if json.dumps(getter(d), sort_keys=True) ==
                                  json.dumps(getter(ref), sort_keys=True)])
    stages = [
        dict(id='S0', stage='Boot ROM', component='internal Boot ROM (not in any image)', component_sha256=None,
             function=dict(va=None, note='ROM code is not available; its SRAM service entry 0xb4060400 is'),
             caller=None, callees=['S1'],
             inputs=[dict(source='SD card (controller selected by the ROM)', disk_offset='0x200200', lba=4097,
                          length=512, note='block 0 (ActBrm trailer at loader 0x1f4) is the only loader block whose '
                                           'code runs before bootloader.bin; how many sectors the ROM reads is not '
                                           'established')],
             outputs=[dict(dest_va='0xb4060000', length=512, coordinate='SRAM')],
             validation=['ActBrm word-sum + 0x1234 rule holds for block 0 (actions_loader.py); whether the ROM '
                         'checks it is not observed'],
             transition=dict(to='0xb4060000', how='ROM jump (not observed)'),
             method=['inferred'], confidence='inferred',
             evidence=['loader.block0', 'components.loader.ini_0x1000_0x1400_sha256 (SRAM fragment, see BOOT-019)'],
             findings=['BOOT-012', 'BOOT-019']),
        dict(id='S1', stage='Loader block 0', component='raw loader 0x0..0x200', component_sha256=comp['loader']['block0_sha256'],
             function=dict(va='0xb4060000', loader_offset='0x0', disk_offset='0x200200'),
             caller='S0', callees=['ROM service 0xb4060400 (r9=4)', 'S2'],
             inputs=[dict(source='MMIO 0xb01600a0 (CMU_DEVCLKEN0 in the S500 tree), bits 7 and 4',
                          note='the value the ROM leaves; bit 7 -> code 2, bit 4 -> code 0, neither -> SRAM-signature '
                               'test (codes 4/5)'),
                     dict(source='ROM service read r0=0x%x r1=0x%x' % (int(sd0['calls'][0]['r0'], 16), int(sd0['calls'][0]['r1'], 16)),
                          disk_offset=f"0x{int(sd0['calls'][0]['r0'], 16) * SECTOR:x}", lba=int(sd0['calls'][0]['r0'], 16),
                          length=int(sd0['calls'][0]['r1'], 16) * SECTOR, loader_offset='0x5400')],
             outputs=[dict(dest_va=sd0['calls'][0]['r2'], length=int(sd0['calls'][0]['r1'], 16) * SECTOR,
                           coordinate='SRAM (bootloader.bin code)'),
                      dict(dest_va='0xb4064c00', length=4, value='boot code (0 on the SD0 path)')],
             validation=['none in block 0 on the SD paths'],
             transition=dict(to='0xb4065400', how='blx r0 after the ROM read', registers='none passed'),
             method=['emulated', 'static'], confidence='strongly-supported',
             evidence=['loader.block0.runs'], findings=['BOOT-012'], **rel_all(lambda d: d['loader']['block0'])),
        dict(id='S2', stage='bootloader.bin (SRAM)', component='bootloader.bin code (loader 0x4c00..0x33c00)',
             component_sha256=bl_sha, function=dict(va='0xb4065400', loader_offset='0x5400'),
             caller='S1', callees=['0xb4065d04 load_ini', '0xb40665d0 DRAM + AFI', '0xb4065d8c load_app',
                                   '0xb4065bf0 load_uboot', 'S3'],
             inputs=[dict(source='SD via ROM service r9=4', disk_offset=r['disk_offset'], lba=r['r0'],
                          length=r['bytes'], dest_va=r['dest']) for r in reads[:3]] +
                    [dict(source='SD via ROM service r9=4 (U-Boot, %d chunks of <=128 KiB)' % len(ub_reads),
                          disk_offset=ub_reads[0]['disk_offset'], lba=ub_reads[0]['r0'], length=ub_bytes,
                          dest_va=ub_reads[0]['dest'])],
             outputs=[dict(dest_va='0xb4062400', length=0x1000, what='bootloader.ini 0x0..0x1000 (reloaded)'),
                      dict(dest_va='0xb4060300', length=16, what='AFI record', value=m['afi']),
                      dict(dest_va='0x1000', length=0x1F000, what='app.bin'),
                      dict(dest_va='0x5000000', length=ub_bytes, what='U-Boot uImage (header at 0x5000000)')],
             validation=['app.bin: ActBrm checksum over 0x1f000 bytes at 0x1000 (0xb40654c8, executed: "OK")',
                         'U-Boot: big-endian size/load/entry read from the header; no magic or CRC check in any '
                         'loader stage (no uImage magic, CRC polynomial or table constant in bootloader.bin/app.bin)'],
             transforms=['sector count = (ih_size + 0x1ff) >> 9, plus 1 header sector'],
             transition=dict(to='0x1000', how='blx 0x1000', registers=f"r0 = U-Boot entry ({m['r0_at_app_entry']})"),
             failure='0xb40693e0 prints "load fail to adfu" then blx 0xffff0140 (Boot ROM)',
             method=['emulated', 'static'], confidence='strongly-supported',
             evidence=['loader.main', 'loader.boot_code_map'], findings=['BOOT-013'],
             **rel_all(lambda d: [(r['disk_offset'], r['dest']) for r in d['loader']['main']['storage_reads'][:3]])),
        dict(id='S3', stage='app.bin (DRAM)', component='app.bin (loader 0x19000..0x38000)',
             component_sha256=comp['loader']['app_bin_sha256'], function=dict(va='0x1000', loader_offset='0x19000'),
             caller='S2', callees=[L['app_entry']['main'] + ' main', '0xbc3c chip/eFuse DVFS check',
                                   L['app_writeback'].get('function', '?') + ' SFVD write-back'],
             inputs=[dict(source='SRAM 0xb4062800 (ini+0x400) "SFVD" record', value=L['ini_sfvd']),
                     dict(source='MMIO 0xb01b00e0 and 0xb0150000/4 (read by 0xbc3c)')],
             outputs=[dict(dest='SD (only when SFVD is absent)', disk_offset=L['app_writeback'].get('disk_offset'),
                           lba=L['app_writeback'].get('start_lba'), length=(L['app_writeback'].get('sectors') or 0) * SECTOR,
                           source_va=L['app_writeback'].get('source'), what='SRAM bootloader.ini image (20 sectors)')],
             validation=['0xbc3c returns -1 -> "Error: 0xca00d001, please reburn system" and the jump is skipped'],
             transition=dict(to=m['r0_at_app_entry'], how='blx [0xb4060018] (saved r0)',
                             registers='CPSR 0xd3 (SVC, IRQ/FIQ masked) set at entry'),
             method=['static'], confidence='strongly-supported', evidence=['loader.app_entry', 'loader.app_writeback'],
             findings=['BOOT-014']),
        dict(id='S4', stage='U-Boot 2015.04 init', component='U-Boot uImage at disk 0x300000', component_sha256=ub_sha,
             function=dict(va=comp['uboot']['entry'], uboot_payload_offset='0x0'),
             caller='S3', callees=['dram_init ' + U['dram_init']['function'], 'init_sequence_r ' + U['init_sequence_r']['table'],
                                   'check_boot_flag ' + U['check_boot_flag']['function']],
             inputs=[dict(source='AFI 0xb4060300', value=m['afi']),
                     dict(source='env: MMC device %s at byte offsets %s, size %s' % (
                         U['env_storage']['mmc_device'], '/'.join(U['env_storage']['offsets']), U['env_storage']['size']),
                          note='no CRC-valid copy in any image; device 1 is the SD2 controller')],
             outputs=[dict(what='gd->ram_size', value='AFI ddr_size (%s) if >= 8 MiB else 0x1f000000' % m['afi']['ddr_size']),
                      dict(what='bootcmd', value=next(r for r in U['check_boot_flag']['rows']
                                                      if r['boot_dev'] == m['afi']['boot_dev'] and r['boot_mode'] == 0)['setenv'])],
             validation=['AFI magic "AFI" compared by every getter; absent magic -> boot_mode 1 (PRODUCE) -> ramboot'],
             transition=dict(to='main_loop', how='autoboot with bootdelay=%s, abort key "%s"' % (
                 U['autoboot']['bootdelay'], U['autoboot']['default_abort_key'])),
             method=['emulated', 'static', 'data'], confidence='verified',
             evidence=['uboot.init_sequence_r', 'uboot.check_boot_flag', 'uboot.afi_getters', 'uboot.env_storage'],
             findings=['BOOT-015', 'BOOT-018'], **rel_all(lambda d: [(r['boot_mode'], r['boot_dev'], r['setenv'])
                                                                     for r in d['uboot']['check_boot_flag']['rows']])),
        dict(id='S5', stage='U-Boot mmcboot', component='U-Boot default environment', component_sha256=ub_sha,
             function=dict(va=None, note='hush scripts in the default environment'),
             caller='S4', callees=['fatload x4', 'env import -t', 'bootm'],
             inputs=[dict(source='mmc %s (SD0, first enabled mmc node %s), partition %s' % (
                 env['mmcdev'], U['embedded_fdt']['registration_order'][0], env['bootpart']),
                          partition=ref['boot_files']['partition1'],
                          files={n: (None if v is None else dict(fat_name=v['fat_name'], size=v['size'], sha256=v['sha256']))
                                 for n, v in files.items()})],
             outputs=[dict(dest_va=env['scriptaddr'], what='uEnv.txt (imported: %s)' % ', '.join(
                 sorted(files['uEnv.txt']['variables'])) if files.get('uEnv.txt') else 'uEnv.txt absent'),
                      dict(dest_va=env['kernel_addr_r'], what='uImage', length=files['uImage']['size']),
                      dict(dest_va=env['ramdisk_addr_r'], what='ramdisk.img', length=files['ramdisk.img']['size']),
                      dict(dest_va=env['fdt_addr_r'], what='kernel.dtb', length=files['kernel.dtb']['size'])],
             validation=['FAT name lookup is case-insensitive (fs/fat downcases both names) so uEnv.txt matches uenv.txt'],
             transition=dict(to='bootm', how='run mboot: bootm ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}'),
             method=['data', 'static'], confidence='strongly-supported', evidence=['uboot.default_env', 'boot_files'],
             findings=['BOOT-016'], **rel_all(lambda d: d['uboot']['default_env']['variables'])),
        dict(id='S6', stage='bootm and FDT fixups', component='U-Boot', component_sha256=ub_sha,
             function=dict(va=h0['image_setup_linux']), caller='S5',
             callees=['image_setup_libfdt', 'owl_boot_fdt_setup ' + U['owl_boot_fdt_setup']['function']],
             inputs=[dict(what='kernel', header=files['uImage']['header']),
                     dict(what='ramdisk', header=files['ramdisk.img']['header'])],
             outputs=[dict(what='kernel', start=ref['memory_map']['rows'][1]['start'], note='XIP: payload already at ih_load'),
                      dict(what='initrd', start=h0['initrd_start'], end=h0['initrd_end'], note='in place (initrd_high=~0)'),
                      dict(what='dtb', start=h0['ft_addr'], totalsize=h0['fdt_totalsize_after'], note='in place (fdt_high=~0)'),
                      dict(what='/memory reg', value=h0['dt_memory_reg']),
                      dict(what='/chosen', value=h0['dt_chosen']),
                      dict(what='/memreserve/', value=h0['dt_memreserve'])],
             validation=['legacy uImage header and data CRC for kernel and ramdisk (verify unset -> on); all pass for the '
                         'shipped files', 'fdt_check_header on the raw DTB'],
             transforms=['bootargs rewritten by owl_boot_fdt_setup (see bootargs)'],
             transition=dict(to='boot_jump_linux ' + U['boot_jump']['function'], how='do_bootm_linux'),
             method=['emulated', 'data'], confidence='strongly-supported', evidence=['handoff', 'memory_map', 'bootargs'],
             findings=['BOOT-017']),
        dict(id='S7', stage='Linux entry', component='U-Boot', component_sha256=ub_sha,
             function=dict(va=U['boot_jump']['function']), caller='S6', callees=['cleanup_before_linux ' + U['cleanup']['function']],
             inputs=[], outputs=[],
             transition=dict(to=files['uImage']['header']['entry'], how='blx (images->ep)',
                             registers=dict(r0='0', r1='0 (bi_arch_number never written; env machid unset)',
                                            r2=h0['ft_addr'] + ' (DTB)'),
                             cpu_state=[c['effect'] for c in U['cleanup']['callees'] if c['effect'] != 'no-op'] +
                                       ['outer-cache (PL310) hooks are empty stubs: L2 state is whatever U-Boot left']),
             method=['static'], confidence='strongly-supported', evidence=['uboot.boot_jump', 'uboot.cleanup',
                                                                           'uboot.bi_arch_number'],
             findings=['BOOT-017']),
    ]
    return stages


def compact(d):
    """Drop bulky per-run detail that the trace does not need (deterministic)."""
    d = json.loads(json.dumps(d))
    d['uboot']['owl_boot_fdt_setup']['calls'] = [c for c in d['uboot']['owl_boot_fdt_setup']['calls']
                                                 if any(isinstance(a, str) and not a.startswith('0x') for a in c['args'])
                                                 or c['args'][1] in ('0x1', '0x2')]
    for r in d['uboot']['check_boot_flag']['rows']:
        r.pop('error', None) if r.get('error') is None else None
    return d


def evidence_document(paths, reference):
    docs = [json.loads(Path(p).read_text()) for p in paths]
    stock = [d for d in docs if d['release'].startswith('stock-')]
    cmp = compare([p for p, d in zip(paths, docs) if d['release'].startswith('stock-')])
    others = {}
    for d in docs:
        if d['release'].startswith('stock-'):
            continue
        twin = next((x for x in stock if x['components']['loader']['sha256'] == d['components']['loader']['sha256']), None)
        others[d['release']] = dict(
            loader_identical_to=None if twin is None else twin['release'],
            uboot_identical_to=next((x['release'] for x in stock if x['components']['uboot']['uimage_sha256'] ==
                                     d['components']['uboot']['uimage_sha256']), None),
            partition_scheme=d['boot_files']['partition1']['scheme'],
            uenv_variables=(d['boot_files']['files'].get('uEnv.txt') or {}).get('variables'),
            dt_chosen_bootargs=[h['dt_chosen'].get('bootargs') for h in d.get('handoff', [])])
    return dict(format_version=1, tool='boot_chain.py', tool_version=TOOL_VERSION, reference_release=reference,
                coordinate_spaces=dict(
                    disk='byte offset in the SD image', loader='offset in the 448-sector raw loader (disk 0x200200)',
                    uboot_payload='offset after the 64-byte uImage header (disk 0x300040, VA 0x05000040)',
                    va='address used by the code: SRAM 0xb406xxxx, DRAM physical from 0 (MMU off throughout)'),
                stages=build_trace(stock, reference), comparison=cmp, other_firmware=others,
                releases={d['release']: compact(d) for d in docs})


SFVD_DISK = LOADER_DISK + 0x2800   # bootloader.ini + 0x400 (SRAM 0xb4062800)
INI_DISK = LOADER_DISK + 0x2400
INI_WRITEBACK_SECTORS = 20


def sfvd_status(image_path):
    """Whether app.bin's write-back condition (BOOT-014) is armed for an image.

    app.bin compares only the 32-bit magic at bootloader.ini+0x400 with "SFVD";
    if it differs, it rewrites 20 sectors from disk 0x202600 on every boot.
    """
    with open(image_path, 'rb') as f:
        f.seek(SFVD_DISK)
        rec = f.read(8)
        f.seek(INI_DISK)
        ini = f.read(INI_WRITEBACK_SECTORS * SECTOR)
    if len(rec) < 8 or len(ini) < INI_WRITEBACK_SECTORS * SECTOR:
        raise ValueError('image too short for the stock loader layout')
    present = rec[:4] == b'SFVD'
    return dict(marker_disk_offset=f'0x{SFVD_DISK:x}', magic=rec[:4].hex(), present=present,
                value=f"0x{struct.unpack('<I', rec[4:])[0]:08x}",
                writeback_region=f'0x{INI_DISK:x}..0x{INI_DISK + INI_WRITEBACK_SECTORS * SECTOR:x}',
                writeback_region_sha256=sha(ini),
                consequence='no loader write-back expected' if present else
                'app.bin would rewrite the 20-sector bootloader.ini region on boot (BOOT-014)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('analyze')
    a.add_argument('image', type=Path)
    a.add_argument('output', type=Path)
    a.add_argument('--release', required=True)
    a.add_argument('--sha256')
    a.add_argument('--ram-mib', type=int, default=256, help='DRAM outcome supplied to the loader emulation')
    a.add_argument('--dram-scenario', help='derive the DRAM outcome instead by running the loader DRAM code under a '
                                           'named dram_complete.py scenario (e.g. reference); overrides --ram-mib')
    t = sub.add_parser('trace', help='build the committed boot-stage evidence document')
    t.add_argument('inputs', nargs='+', type=Path)
    t.add_argument('output', type=Path)
    t.add_argument('--reference', default='stock-20231014')
    v = sub.add_parser('sfvd', help='check the SFVD marker that suppresses app.bin\'s ini write-back')
    v.add_argument('image', type=Path)
    c = sub.add_parser('compare')
    c.add_argument('inputs', nargs='+', type=Path)
    c.add_argument('output', type=Path)
    args = ap.parse_args()
    if args.cmd == 'sfvd':
        r = sfvd_status(args.image)
        print(json.dumps(r, indent=1))
        raise SystemExit(0 if r['present'] else 1)
    if args.cmd == 'trace':
        args.output.write_text(json.dumps(evidence_document(args.inputs, args.reference), indent=1) + '\n')
        return
    if args.cmd == 'analyze':
        r = analyze(args.image, args.release, args.sha256, args.ram_mib, args.dram_scenario)
        args.output.write_text(json.dumps(r, indent=1) + '\n')
    else:
        r = compare(args.inputs)
        args.output.write_text(json.dumps(r, indent=1) + '\n')


if __name__ == '__main__':
    main()
