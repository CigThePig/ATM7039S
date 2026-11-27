"""Continuous A32 loader execution with bounded, synthetic ROM and peripheral services."""
from copy import deepcopy

import boot_chain as boot
import ddr_emulate as ddr
import dram_complete as dram
import predram_analysis as pre
import sd2_dram_analysis as sd2


class BoundaryError(RuntimeError):
    def __init__(self, outcome, detail):
        super().__init__(detail)
        self.outcome = outcome


class Loader(sd2.ComparisonHarness):
    """Start with block 0 alone and keep CPU, SRAM, MMIO and GPIO live through app.bin."""

    boot_word_rule = 'boot word written by executed block 0'

    def __init__(self, loader, disk, case, clock_gate, rom_failure=False, sfvd_missing=False):
        # Reset the historical harness's preloaded SRAM. The ROM read installs
        # instructions, and main's own INI read installs the configuration.
        super().__init__(loader, case, 0, initial_mmio={0xB01600A0: clock_gate})
        self.uc.mem_write(boot.SRAM_BASE, loader[:512] + bytes(boot.SRAM_SIZE - 512))
        self.uc.mem_write(dram.AFI, self.afi_before)
        self.uc.mem_write(boot.BOOT_CODE_VA, b'\xff' * 4)
        self.disk, self.case = disk, case
        self.rom_failure, self.sfvd_missing = rom_failure, sfvd_missing
        self.read_log, self.write_requests, self.stage_stops = [], [], []
        self.rom_ranges = [(boot.SRAM_BASE, boot.SRAM_BASE + 512)]
        self.failure = None
        self.app_sites = []
        self.flat_limit = None
        self.window = 'early'
        self.pmic.regs = {**pre.PMIC_DEFAULTS, **self.pmic.regs}
        self.stubs.pop(dram.FN['uart_init'])
        self.stubs.pop(dram.FN['pmu_detect'])
        self.stubs.pop(dram.FN['pmic_read'])
        self.stubs.pop(dram.FN['pmic_write'])
        self.stubs.update({
            boot.ROM_SERVICE: ('ROM selector', self._rom_read),
            0xB406AC10: ('PMIC I2C read', self._i2c_read),
            0xB406AC60: ('PMIC I2C write', self._i2c_write),
        })
        self.setreg('cpsr', 0x1D3)
        self.setreg('sp', pre.STACK_TOP)
        self.uc.mem_map(0xFFFF0000, 0x10000)
        self.stops.update({pre.MAIN: 'early-loader entry', 0xB4060120: 'block-0 idle',
                           boot.ROM_ADFU: 'ROM entry (instructions unavailable)'})

    def _i2c_read(self):
        slave, reg, buf = (self.reg(r) for r in ('r0', 'r1', 'r3'))
        reg &= 0xff
        size = self.u32(self.reg('sp'))
        if slave != 0x65 or size != 2:
            raise BoundaryError('unmodelled-dependency', 'unsupported I2C read request')
        fail = reg in self.case.pmic_errors
        value = None if fail else self.pmic.read(reg)
        self._event('pmic', 'r', reg, size, value, 'I2C register file' if not fail else 'injected I2C failure')
        if fail:
            return 1
        self.uc.mem_write(buf, value.to_bytes(2, 'big'))
        return 0

    def _i2c_write(self):
        slave, reg, buf = (self.reg(r) for r in ('r0', 'r1', 'r3'))
        size = self.u32(self.reg('sp'))
        if slave != 0x65 or size != 2:
            raise BoundaryError('unmodelled-dependency', 'unsupported I2C write request')
        value = int.from_bytes(self.uc.mem_read(buf, size), 'big')
        self.pmic.write(reg & 0xff, value)
        self._event('pmic', 'w', reg & 0xff, size, value, 'I2C register file')
        return 0

    def _map_flat(self, start, length):
        if not length or not 0 <= start < start + length <= self.flat_limit:
            raise BoundaryError('invalid-memory-layout', f'destination {start:#x}+{length:#x} outside detected RAM')
        for page in range(start & ~0xfff, start + length, 0x1000):
            if page not in self.dram_pages:
                self.uc.mem_map(page, 0x1000)
                self.dram_pages.add(page)

    def _unmapped(self, uc, access, address, size, value, user):
        if self.flat_limit is not None and address < dram.DRAM_WINDOW:
            if address + size > self.flat_limit:
                return False
            self._map_flat(address, size)
            return True
        return super()._unmapped(uc, access, address, size, value, user)

    def _check_flat_access(self, uc, address, size):
        if address + size > self.flat_limit:
            self.failure = ('invalid-memory-layout', f'post-DRAM access outside detected RAM at {address:#x}')
            uc.emu_stop()

    def _dram_read(self, uc, access, address, size, value, user):
        if self.flat_limit is None:
            super()._dram_read(uc, access, address, size, value, user)
        else:
            self._check_flat_access(uc, address, size)

    def _dram_write(self, uc, access, address, size, value, user):
        if self.flat_limit is None:
            super()._dram_write(uc, access, address, size, value, user)
        else:
            self._check_flat_access(uc, address, size)

    def _rom_read(self):
        selector, lba, count, dest = (self.reg(r) for r in ('r9', 'r0', 'r1', 'r2'))
        row = dict(selector=selector, lba=lba, sectors=count, destination=hex(dest), status='requested')
        self.read_log.append(row)
        if selector != 4:
            raise BoundaryError('unmodelled-dependency', f'unsupported ROM service {selector}')
        if self.rom_failure or not 0 < count <= 256:
            row.update(status='failed')
            self.failure = ('rom-service-failure', 'ROM sector service returned a synthetic read error')
            return 1
        size = count * 512
        if self.flat_limit is None:
            if (lba, count, dest) not in ((0x102B, 80, pre.MAIN), (0x1013, 8, pre.INI_VA)):
                raise BoundaryError('unmodelled-dependency', 'unexpected pre-DRAM ROM read')
        else:
            try:
                self._map_flat(dest, size)
            except BoundaryError as error:
                row.update(status='rejected', detail=str(error))
                raise
        try:
            raw = self.disk.sectors(lba, count)
        except (OSError, boot.Unmodelled):
            raw = b''
        if len(raw) != size:
            row.update(status='failed', bytes=len(raw))
            self.failure = ('storage-read-failure', 'short or out-of-range ROM sector read')
            return 1
        data = bytearray(raw)
        if dest == pre.INI_VA:
            for offset, patch in self.case.ini_patch.items():
                data[offset:offset + len(patch)] = patch
            if self.sfvd_missing:
                data[0x400:0x404] = b'\0' * 4
        self.uc.mem_write(dest, bytes(data))
        if dest == pre.MAIN:
            self.rom_ranges.append((dest, dest + size))
        if dest == pre.INI_VA:
            self.ini_before = self.ini_records()
        row.update(status='ok', bytes=size, source_sha256=boot.sha(raw), loaded_sha256=boot.sha(data))
        self._event('storage', 'read', dest, size, row['loaded_sha256'], f'ROM selector 4, sector {lba:#x}')
        return 0

    def _oracle(self, addr):
        if addr == 0xB0168010:
            step = 2400  # 100 us per read, including the loopback's real delay loop
            self.regs[addr] = (self.regs.get(addr, 0) + step) & 0xffffffff
            self.gpio.advance(step / 24)
            return self.regs[addr], 'synthetic timer, 2400 ticks per read'
        if 0xB0120000 <= addr < 0xB012E000 and addr & 0x1FFF == 0xC:
            return 0x400, 'synthetic UART ready'
        if 0xB0170000 <= addr < 0xB0180000 and addr & 0x3FFF == 0x20:
            return 1, 'synthetic I2C FIFO ready'
        if self.window == 'app':
            if addr == 0xB01B00E0:
                return 0x41, 'synthetic supported chip revision'
            if addr in (0xB0150000, 0xB0150004) and self.regs.get(0xB0150004) == 0x746E3531:
                return (0x41 if addr == 0xB0150000 else 0), 'synthetic CHIPID ready and zero data'
        return super()._oracle(addr)

    def _code(self, uc, address, size, user):
        if address in self.stage_stops:
            self.stage_stops.remove(address)
            self._snapshot('checkpoint', address)
            self.stopped = dict(kind='checkpoint', pc=hex(address))
            uc.emu_stop()
            return
        if address == ddr.F_DELAY and (self.window == 'early' or self.window == 'app'):
            # Bypass Harness's delay shortcut during early initialization.
            self.insns += 1
            if self.insns - self.budget_start < self.budget:
                return
        if address not in self.stops and address not in self.stubs:
            executable = any(start <= address < end for start, end in self.rom_ranges)
            if self.window == 'app':
                executable |= boot.APP_VA <= address < boot.APP_VA + 0x1f000
            if not executable:
                self.failure = ('unmodelled-dependency', f'no verified instructions at {address:#x}')
                uc.emu_stop()
                return
        if self.window == 'app' and address in (0x8190, 0x8248, 0x8258, 0x8264, 0x9430, 0x1030):
            self.app_sites.append(hex(address))
        if self.window == 'app' and address in (0x806C, 0x851C, 0x7E54, 0x7F20):
            args = [self.reg(f'r{i}') for i in range(4)]
            kind = 'configuration write-back dispatch' if address == 0x806C else 'storage writer entry'
            self.write_requests.append(dict(pc=hex(address), arguments=args, kind=kind, performed=False))
            self.failure = ('app-unsupported', 'app.bin requested the unmodelled storage write-back path')
            uc.emu_stop()
            return
        super()._code(uc, address, size, user)

    def advance(self, entry, budget=sd2.DEFAULT_LIMIT):
        self.budget, self.budget_start = budget, self.insns
        self.limit = self.insns + 3 * budget + 48
        self.stopped = None
        try:
            self.uc.emu_start(entry, 0xffffffff, count=3 * budget + 48)
        except BoundaryError as error:
            self.failure = error.outcome, str(error)
        except Exception as error:
            self.stopped = dict(kind='fault', pc=hex(self.reg('pc')), error=str(error))
        if self.stopped is None and self.failure is None:
            self.failure = ('emulator-fault', 'execution ended without a classified stop')
        self._snapshot('terminal', self.reg('pc'))

    def boundary(self):
        snapshot = deepcopy(self.boundaries[-1])
        sp = self.reg('sp')
        frame = None
        if boot.SRAM_BASE <= sp < boot.SRAM_BASE + boot.SRAM_SIZE - 128:
            frame = boot.sha(self.uc.mem_read(sp, 128))
        return dict(snapshot=snapshot, sram_sha256=boot.sha(self.uc.mem_read(boot.SRAM_BASE, boot.SRAM_SIZE)),
                    stack_window_sha256=frame, trace=self.ordered.summary(),
                    synthetic_sctlr=hex(self.uc.cpr_read(15, 0, 1, 0, 0, 0, 0)),
                    timer_word=self.regs.get(0xB0168010), gpio_time_us=self.gpio.now)
