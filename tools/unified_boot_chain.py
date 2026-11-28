#!/usr/bin/env python3
"""Offline causal reconstruction through the ATM7039S pre-kernel entry boundary."""
import argparse
from copy import deepcopy
from dataclasses import dataclass, replace
import gc
from importlib.metadata import version
import json
import os
from pathlib import Path
import stat
import struct
import tempfile

import boot_chain as boot
import dram_complete as dram
import predram_analysis as pre
import sd2_dram_analysis as sd2
from firmware_catalogue import regular
from unified_environment import Environment, persistent_environment
from unified_loader import BoundaryError, Loader
from unified_uboot import afi_consumers, fdt_layout, legacy_image

VERSION = 1
REFERENCE = sd2.REFERENCE
OBS = pre.ROOT / 'evidence' / 'observations' / 'OBS-001.json'
STAGES = {
    'boot-rom-boundary': 'synthetic input',
    'block-0': 'executed with stubs',
    'early-loader-entry': 'continuous execution',
    'pre-dram': 'executed with stubs',
    'recovery-resume-decision': 'executed with stubs',
    'dram-and-main-dispatch': 'executed with stubs',
    'load-app-and-uboot': 'executed with stubs',
    'app-bin': 'executed with stubs',
    'uboot-entry': 'continuous execution',
    'uboot-afi-and-ram': 'transferred-state execution',
    'mmc-registration': 'executed with stubs',
    'boot-device': 'executed with stubs',
    'environment-and-storage': 'independent model',
    'boot-files': 'independent model',
    'device-tree': 'transferred-state execution',
    'linux-entry': 'executed with stubs',
}
GRAPH = {name: prev for name, prev in zip(STAGES, (None, *STAGES))}
ASSUMPTIONS = {
    'ROM': 'First sector at 0xb4060000, SP 0xb409f000, CPSR 0x1d3 and Unicorn CP15 defaults are synthetic. '
           'The boot-code word starts with an unsupported sentinel and must be set by block 0.',
    'peripherals': 'Unknown reset words use the declared synthetic seed. Timer advances 2400 ticks per read; UART and '
                   'I2C FIFO are ready. I2C transfers use a register file. DDR PHY and controller follow scenario rules.',
    'DRAM': 'The comparison harness models sparse aliasing, training outcomes and diagnostic faults. After 0xb4065440 '
            'existing mapped bytes stay live; new accesses use bounded linear RAM. Analog and cache effects are unknown.',
    'app.bin': 'A CHIPID request for 0x746e3531 completes with zero data; the synthetic revision word is 0x41. '
               'Unsupported write paths stop before storage changes.',
    'U-Boot': 'Startup, relocation, full driver initialization and full board data are unavailable. '
              'Bounded invocations take the loaded payload and raw AFI. MMC pin mux starts from the live loader word.',
    'storage': 'Only the selected SD controller has a verified backing image. Secondary card init is a supplied outcome. '
               'Unbacked persistent environment reads are modeled unavailable.',
    'handoff': 'Only the pinned in-place initrd/FDT policy and ARM legacy zImage entry are supported. The LMB models '
               'input FDT reservations and a fixed bounded helper scratch window. Runtime U-Boot relocation is unknown.',
    'strap': 'GPIOC6 is an independent U-Boot variant input, separate from the loader GPIOC10 loopback input. SN absent.',
}


@dataclass(frozen=True)
class Scenario:
    name: str
    medium: str = 'sd2'
    dram_case: str = 'reference'
    strap_high: bool = True
    alternate_card: bool = False
    fault: str | None = None
    c10_high: bool = False
    pmic_pending: bool = False


SCENARIOS = (
    Scenario('sd2-reference'),
    Scenario('sd0-reference', medium='sd0'),
    Scenario('sd2-strap-low', strap_high=False),
    Scenario('sd2-c10-high', c10_high=True),
    Scenario('sd2-both-registered', alternate_card=True),
    Scenario('sd0-both-registered', medium='sd0', alternate_card=True),
    Scenario('sd2-64m-storage-limit', dram_case='col-bank-row-c9-r13-b8-cs1'),
    Scenario('sd2-128m', dram_case='col-bank-row-c10-r13-b8-cs1'),
    Scenario('sd2-512m', dram_case='two-ranks-first-attempt'),
    Scenario('diagnostic-failure', dram_case='memory-test-dropped-write'),
    Scenario('training-failure', dram_case='persistent-training-failure'),
    Scenario('zq-failure', dram_case='zq-timeout'),
    Scenario('phy-poll', dram_case='dram-init-hang'),
    Scenario('invalid-ini', dram_case='invalid-ini-version'),
    Scenario('pmic-adfu', pmic_pending=True),
    Scenario('pmic-read-error', dram_case='pmic-read-error'),
    Scenario('gpio-adfu', dram_case='gpio-exact-echo'),
    Scenario('resume', dram_case='resume-valid'),
    Scenario('resume-power-off', dram_case='resume-training-failure'),
    Scenario('rom-failure', fault='rom-read'),
    Scenario('sfvd-absent', fault='sfvd-absent'),
    Scenario('mmc-failure', fault='mmc-init'),
    Scenario('missing-kernel', fault='missing-kernel'),
    Scenario('invalid-kernel', fault='invalid-kernel'),
    Scenario('corrupt-dtb', fault='corrupt-dtb'),
    Scenario('unsupported-env', fault='unsupported-env'),
    Scenario('invalid-afi', fault='invalid-afi'),
)
SCENARIO_BY_NAME = {scenario.name: scenario for scenario in SCENARIOS}


@dataclass(frozen=True)
class State:
    """Canonical immutable evidence envelope. No executable bytes are serialized."""
    encoded: bytes
    sha256: str

    @classmethod
    def create(cls, stage, image, scenario, parent, payload):
        data = sd2.serial(dict(version=VERSION, stage=stage, image=image, scenario=scenario,
                               parent=parent, method=STAGES[stage], payload=payload)).encode('utf-8')
        return cls(data, boot.sha(data))

    def validate(self, stage, image, scenario, parent):
        try:
            data = json.loads(self.encoded)
            if (data['version'], data['stage'], data['image'], data['scenario'], data['parent'], data['method']) != (
                    VERSION, stage, image, scenario, parent, STAGES[stage]):
                raise ValueError
            if (boot.sha(self.encoded) != self.sha256 or
                    not isinstance(data['payload'], dict) or sd2.serial(data).encode('utf-8') != self.encoded):
                raise ValueError
            return data['payload']
        except (ValueError, KeyError, TypeError) as error:
            raise BoundaryError('invalid-handoff-state', 'state integrity, predecessor or firmware/scenario identity failed'
                                ) from error


class StageGraph:
    def __init__(self, image, scenario):
        self.image, self.scenario = image, scenario
        self.states, self.rows = {}, {}
        self.terminal = None

    def step(self, stage, produce):
        if stage not in GRAPH or stage in self.rows:
            raise ValueError(f'unexpected stage: {stage}')
        if self.terminal:
            return
        prev = GRAPH[stage]
        if prev is not None and prev not in self.states:
            raise BoundaryError('invalid-handoff-state', f'{stage} requires {prev}')
        parent = self.states[prev].sha256 if prev else None
        try:
            inherited = None
            if prev is not None:
                older = GRAPH[prev]
                inherited = self.states[prev].validate(prev, self.image, self.scenario,
                                                       self.states[older].sha256 if older else None)
            payload = produce(inherited)
            state = State.create(stage, self.image, self.scenario, parent, payload)
        except BoundaryError as error:
            self.terminal = dict(stage=stage, outcome=error.outcome, detail=str(error))
            self.rows[stage] = dict(status='terminal', method=STAGES[stage], input_sha256=parent)
            return
        self.states[stage] = state
        self.rows[stage] = dict(status='completed', method=STAGES[stage], input_sha256=parent,
                                state_sha256=state.sha256, state=payload)

    def evidence(self):
        blocker = self.terminal['stage'] if self.terminal else None
        return {stage: self.rows.get(stage, dict(status='blocked', method='blocked', blocked_by=blocker,
                                                predecessor=GRAPH[stage])) for stage in STAGES}


def cold_afi(result, boot_code):
    outcome = result['outcome']
    if outcome not in ('cold-success', 'cold-success-diagnostic-failure'):
        raise BoundaryError(outcome, 'executed main did not reach cold storage loading')
    diagnostic = 'failed' if outcome == 'cold-success-diagnostic-failure' else 'passed'
    afi = result['afi']
    if (result['boot_code'] != boot_code or result['boot_code_observed'] != boot_code or
            result['caller_return'] != '0x0' or result['dram_return'] != '0x0' or
            not result['main_continuation_boundary_reached'] or result['terminal']['pc'] != hex(sd2.MAIN_LOAD) or
            result['memory_test']['status'] != diagnostic or not afi['generated'] or afi['stores'] <= 0):
        raise BoundaryError('invalid-handoff-state', 'inconsistent cold continuation facts')
    try:
        raw = boot.checked_afi(bytes.fromhex(afi['bytes']))
    except ValueError as error:
        raise BoundaryError('invalid-afi-handoff', str(error)) from error
    fields = dram.decode_afi(raw)
    if (not fields['magic_ok'] or fields['boot_mode'] != 0 or fields['boot_dev'] != (0x20 | boot_code) or
            not result['capacity_mib'] or fields['ddr_size'] != result['capacity_mib'] << 20 or
            fields != afi['decoded']):
        raise BoundaryError('invalid-afi-handoff', 'AFI and loader outcome disagree')
    return raw


def cpu_state(loader):
    data = loader.boundary()
    snapshot = data['snapshot']
    return dict(pc=snapshot['pc'], cpu=snapshot['cpu'], sctlr=data['synthetic_sctlr'], boot_word=snapshot['boot_word'],
                sram_sha256=data['sram_sha256'], stack_window_sha256=data['stack_window_sha256'],
                pmic=snapshot['pmic'], gpio_sha256=sd2.digest(snapshot['gpio']),
                gpio={key: snapshot['gpio'].get(key) for key in ('0xb01b0020', '0xb01b0048', '0xb01b0064')},
                mmio_sha256=sd2.digest(snapshot['mmio']), timer_word=data['timer_word'], gpio_time_us=data['gpio_time_us'],
                records=snapshot['records'], afi=snapshot['afi'], trace=data['trace'])


def dram_case(name):
    if name == 'col-bank-row-c9-r13-b8-cs1':
        # The historical geometry sweep reports 64 MiB for this x16 device.
        device = dram.DmmDevice(9, 13, 3, 1, dram.ORDERS['col-bank-row'])
        scenario = dram.Scenario(name, note='hypothetical 64 MiB x16 single-rank device',
                                 col_bits=9, row_bits=13, bank_log2=3, ranks=1)
        return sd2.Case(name, 'geometry', scenario, ram=dram.Ram('dmm', device=device, float_value=0))
    return next(case for case in sd2.cases() if case.name == name)


class Execution:
    loader_type = Loader

    def __init__(self, disk, loader, identity, scenario, detail):
        self.disk, self.identity, self.scenario, self.detail = disk, identity, scenario, detail
        self.graph = StageGraph(identity['actual_sha256'], sd2.digest(vars(scenario)))
        self.case = dram_case(scenario.dram_case)
        if scenario.c10_high:
            self.case.c10_rule = ('const', 1)
        if scenario.pmic_pending:
            self.case.pmic[0x35] = 2
        self.clock_gate = {'sd0': 0x10, 'sd2': 0x80}[scenario.medium]
        self.loader = self.loader_type(loader, disk, self.case, self.clock_gate, scenario.fault == 'rom-read',
                                       scenario.fault == 'sfvd-absent')
        self.dram_result = None
        self.environment = None
        self.environment_attempts = None
        self.files = None
        self.warning = None
        self.reentry = None

    def run(self):
        for name in STAGES:
            self.graph.step(name, getattr(self, name.replace('-', '_')))
        result = dict(format_version=VERSION, firmware=self.identity, scenario=vars(self.scenario),
                      dram_inputs=self.case.inputs(), assumptions=ASSUMPTIONS, stages=self.graph.evidence(),
                      terminal=self.graph.terminal or dict(stage='linux-entry', outcome='linux-entry-boundary'),
                      diagnostic_warning=self.warning, storage_reads=self.loader.read_log,
                      app_write_requests=self.loader.write_requests)
        if self.dram_result is not None:
            result['dram_result'] = self.dram_result
        if self.loader.window == 'app':
            result['app_sites'] = self.loader.app_sites
        if self.reentry is not None:
            result['rom_reentry'] = self.reentry
        if self.environment is not None:
            result['environment'] = self.environment.evidence()
        if self.environment_attempts is not None:
            result['persistent_environment'] = self.environment_attempts
        if self.detail:
            result['trace_detail'] = dict(fields=sd2.TRACE_FIELDS, events=self.loader.ordered.runs,
                                          boundaries=self.loader.boundaries, console=self.loader.prints)
        return result

    def boot_rom_boundary(self, _):
        return dict(clock_gate=hex(self.clock_gate), block0_sha256=self.identity['block0_sha256'],
                    inherited_physical_cpu_state=None, rom_code=None, sram_entry=hex(boot.SRAM_BASE))

    def _advance(self, entry, budget=sd2.DEFAULT_LIMIT):
        self.loader.advance(entry, budget)
        if self.loader.failure is not None:
            raise BoundaryError(*self.loader.failure)

    def _at(self, *entries):
        stop = self.loader.stopped or {}
        if any(stop.get('pc') == hex(entry) for entry in entries) and stop.get('kind') in ('stop', 'checkpoint'):
            return
        if self.loader.window in ('loading', 'app'):
            outcome = {'fault': 'emulator-fault', 'instruction limit': 'instruction-limit'}.get(
                stop.get('kind'), 'unmodelled-dependency')
        else:
            outcome = self.loader.verdict()
        raise BoundaryError(outcome, f'expected {", ".join(map(hex, entries))}; stopped at {stop}')

    def _inherit_loader(self, value):
        if cpu_state(self.loader) != value.get('machine'):
            raise BoundaryError('invalid-handoff-state', 'live loader state differs from the predecessor snapshot')

    def block_0(self, inherited):
        self._advance(int(inherited['sram_entry'], 16))
        self._at(pre.MAIN)
        code = self.loader.word(boot.BOOT_CODE_VA)
        if code not in (0, 2):
            raise BoundaryError('unsupported-configuration', f'block 0 selected unsupported code {code}')
        self.loader.boot_code = code
        return dict(boot_code=code, storage_reads=deepcopy(self.loader.read_log), machine=cpu_state(self.loader))

    def early_loader_entry(self, inherited):
        self._inherit_loader(inherited)
        h = self.loader
        body = bytes(h.uc.mem_read(pre.MAIN, 80 * 512))
        record = h.read_log[-1]
        if boot.sha(body) != record['source_sha256'] or record['destination'] != hex(pre.MAIN):
            raise BoundaryError('invalid-handoff-state', 'the early loader instruction span was not installed')
        return dict(boot_code=inherited['boot_code'], loader_span_sha256=boot.sha(body), machine=cpu_state(h))

    def pre_dram(self, inherited):
        self._inherit_loader(inherited)
        h = self.loader
        h.stops.pop(pre.MAIN)
        h.stage_stops.append(dram.FN['adfu_check'])
        self._advance(pre.MAIN)
        if h.reg('pc') == sd2.MAIN_RECOVERY and h.caller_return is not None:
            self.dram_result = h.result()
        self._at(dram.FN['adfu_check'])
        return dict(machine=cpu_state(h), i2c_transactions=len(h.pmic.log), ini_read=deepcopy(h.read_log[-1]))

    def recovery_resume_decision(self, inherited):
        self._inherit_loader(inherited)
        h = self.loader
        h.stage_stops.extend([pre.DRAM_COLD, pre.RESUME_ENTRY])
        self._advance(dram.FN['adfu_check'])
        if h.reg('pc') == pre.ROM_REENTRY:
            self.dram_result = h.result()
            self._trace_reentry()
            raise BoundaryError('adfu-before-dram', 'early ADFU branch entered the loader ROM re-entry routine')
        self._at(pre.DRAM_COLD, pre.RESUME_ENTRY)
        return dict(machine=cpu_state(h), decision='cold' if h.reg('pc') == pre.DRAM_COLD else 'resume',
                    entry_argument=hex(h.reg('r0')), caller_return_address=hex(h.reg('lr')),
                    loopback_word=h.loopback_word)

    def _trace_reentry(self):
        h = self.loader
        copy_requests = []

        def rom_copy():
            args = [h.reg(f'r{i}') for i in range(3)]
            if args != [0xB4060000, 0xFFFF5200, 0x2E00]:
                raise BoundaryError('unmodelled-dependency', 'unexpected ROM copy request')
            copy_requests.append(dict(destination=hex(args[0]), source=hex(args[1]), size=args[2]))
            return args[0]

        del h.stops[pre.ROM_REENTRY]
        h.stubs[0xB406AF64] = ('record unavailable ROM copy', rom_copy)
        h.stops[boot.SRAM_BASE] = 'ROM re-entry target (copy unavailable)'
        h.advance(pre.ROM_REENTRY)
        self.reentry = dict(copy_requests=copy_requests, terminal=h.stopped, failure=h.failure,
                            vbar=hex(h.uc.cpr_read(15, 0, 12, 0, 0, 0, 0)), machine=cpu_state(h))

    def dram_and_main_dispatch(self, inherited):
        self._inherit_loader(inherited)
        h = self.loader
        h.window = 'dram'
        self._advance(int(inherited['machine']['pc'], 16))
        res = self.dram_result = h.result()
        self.raw_afi = cold_afi(res, inherited['machine']['boot_word'])
        if res['outcome'] == 'cold-success-diagnostic-failure':
            self.warning = 'Firmware continued after a failed memory diagnostic'
        h.flat_limit = res['capacity_mib'] << 20
        milestones = []
        phases = set(sd2.PHASES.values()) | set(sd2.RETURN_PHASES.values()) | {'after-memory-test'}
        for row in h.boundaries:
            if row['phase'] in phases:
                milestones.append({key: row[key] for key in ('phase', 'pc', 'event_index')})
        return dict(machine=cpu_state(h), transfer_afi_sha256=boot.sha(self.raw_afi),
                    capacity_bytes=h.flat_limit, milestones=milestones, diagnostic=res['memory_test']['status'])

    def load_app_and_uboot(self, inherited):
        self._inherit_loader(inherited)
        h = self.loader
        h.stops.pop(sd2.MAIN_LOAD)
        h.window = 'loading'
        h.stops[boot.APP_VA] = 'app.bin entry'
        self._advance(sd2.MAIN_LOAD, 500_000)
        if h.reg('pc') == sd2.MAIN_RECOVERY:
            raise BoundaryError('invalid-image', 'loader rejected app.bin or U-Boot')
        self._at(boot.APP_VA)
        app = bytes(h.uc.mem_read(boot.APP_VA, 0x1f000))
        app_read = next((r for r in h.read_log if r['destination'] == hex(boot.APP_VA)), None)
        if app_read is None or app_read['loaded_sha256'] != boot.sha(app):
            raise BoundaryError('invalid-handoff-state', 'loaded app.bin does not match its recorded read')
        self.app = boot.Blob(app, boot.APP_VA, 'app.bin')
        hdr = bytes(h.uc.mem_read(boot.UBOOT_DISK, 64))
        size, load, entry = struct.unpack_from('>III', hdr, 12)
        if not (size <= 1 << 20 and load == 0x05000000 and entry == load + 64 == h.reg('r0')):
            raise BoundaryError('invalid-image', 'unsupported loaded U-Boot size/load/entry')
        image = bytes(h.uc.mem_read(load, size + 64))
        meta = legacy_image(image, 5, 1 << 20, os_id=17)
        if hdr != image[:64]:
            raise BoundaryError('invalid-image', 'loaded U-Boot header differs from the staged header')
        self.uboot_image = dict(header=meta, load=load, entry=entry, size=size, header_sha256=boot.sha(hdr),
                                payload_sha256=boot.sha(image[64:]), image_sha256=boot.sha(image))
        return dict(machine=cpu_state(h), app_sha256=boot.sha(app), uboot=self.uboot_image)

    def app_bin(self, inherited):
        self._inherit_loader(inherited)
        h = self.loader
        entry = inherited['uboot']['entry']
        h.stops.pop(boot.APP_VA)
        h.window = 'app'
        h.stops.update({entry: 'U-Boot entry', 0x1024: 'app.bin failure loop'})
        sfvd = bytes(h.uc.mem_read(pre.INI_VA + 0x400, 4))
        writes = len(h.writes)
        self._advance(boot.APP_VA, 100_000)
        if h.reg('pc') != entry:
            raise BoundaryError('app-unsupported', f'app.bin did not reach U-Boot: {h.stopped}')
        self._at(entry)
        return dict(machine=cpu_state(h), sfvd_hex=sfvd.hex(), reached_sites=h.app_sites,
                    sram_saved_target=hex(h.word(0xB4060018)), direct_callers_9430=boot.direct_callers(self.app, 0x9430),
                    pad_writes=[w for w in h.writes[writes:] if 0xB01B0000 <= int(w['address'], 16) < 0xB01B0100],
                    uboot=inherited['uboot'])

    def uboot_entry(self, inherited):
        self._inherit_loader(inherited)
        h, meta = self.loader, inherited['uboot']
        image = bytes(h.uc.mem_read(meta['load'], 64 + meta['size']))
        if boot.sha(image) != meta['image_sha256'] or int(inherited['sram_saved_target'], 16) != meta['entry']:
            raise BoundaryError('invalid-handoff-state', 'app.bin transfer target or live U-Boot image differs')
        raw = bytes(h.uc.mem_read(boot.AFI_VA, 16))
        if raw != self.raw_afi:
            raise BoundaryError('invalid-afi-handoff', 'AFI changed between the loader and U-Boot entry')
        self.ub = boot.Blob(image[64:], meta['entry'], 'u-boot')
        pinmux = h.gpio.regs.get(0xB01B0048, h.regs.get(0xB01B0048))
        if pinmux is None:
            raise BoundaryError('unmodelled-dependency', 'missing loader pin mux state for U-Boot MMC')
        return dict(machine=cpu_state(h), uboot=meta, afi_exact_hex=raw.hex(), afi_sha256=boot.sha(raw), pinmux=pinmux)

    def uboot_afi_and_ram(self, inherited):
        raw = bytes.fromhex(inherited['afi_exact_hex'])
        if self.scenario.fault == 'invalid-afi':
            raw = b'BAD\0' + raw[4:]
        if raw != self.raw_afi or boot.sha(raw) != inherited['afi_sha256']:
            raise BoundaryError('invalid-afi-handoff', 'AFI transfer bytes differ from live loader state')
        result = afi_consumers(self.ub, raw)
        if result['exact_hex'] != raw.hex() or result['fallback_used'] or result['gd_ram_size'] != self.loader.flat_limit:
            raise BoundaryError('invalid-afi-handoff', 'U-Boot RAM result differs from cold AFI')
        return dict(afi=result, pinmux=inherited['pinmux'])

    def mmc_registration(self, inherited):
        self.slot = inherited['afi']['getters']['device'] & 0xf
        if self.slot != self.loader.boot_code:
            raise BoundaryError('invalid-afi-handoff', 'consumed boot device differs from block 0')
        status = {slot: (self.scenario.fault != 'mmc-init' if slot == self.slot else self.scenario.alternate_card)
                  for slot in (0, 2)}
        exact_hex = inherited['afi']['exact_hex']
        mmc = boot.mmc_registration(self.ub, raw_afi=bytes.fromhex(exact_hex), card_status=status,
                                    pinmux=inherited['pinmux'])
        row = mmc['rows'][0]
        if row['error'] or not row['returned'] or row['return_value'] or row['afi_in_memory'] != exact_hex:
            raise BoundaryError('uboot-initialization-failure', f'MMC registration failed: {row["error"]}')
        return dict(registration=row, afisize=inherited['afi']['gd_ram_size'], afi=inherited['afi'])

    def boot_device(self, inherited):
        regs = inherited['registration']['registered']
        env, source, attempts = persistent_environment(self.ub, self.disk, regs, self.slot)
        self.environment_attempts = attempts
        afi = inherited['afi']
        raw = bytes.fromhex(afi['exact_hex'])
        row = boot.check_boot_flag_table(self.ub, boot.find_check_boot_flag(self.ub), raw_afi=raw)['rows'][0]
        if row['error'] or not row['returned'] or row['return_value'] or row['afi_in_memory'] != raw.hex():
            raise BoundaryError('uboot-initialization-failure', 'check_boot_flag failed or changed the AFI')
        self.environment = Environment(env, source, self.disk, regs, self.slot, afi['gd_ram_size'],
                                       fault=self.scenario.fault)
        for name, value in row['mutations']:
            self.environment.change(name, value, 'check_boot_flag')
        return dict(boot_flag=row, afi=afi, registration=regs, bootcmd=self.environment.values.get('bootcmd'))

    def environment_and_storage(self, inherited):
        e = self.environment
        if e.values.get('bootcmd') != inherited['bootcmd']:
            raise BoundaryError('invalid-handoff-state', 'environment does not carry the selected boot command')
        if self.scenario.fault == 'unsupported-env':
            e.change('mboot', 'unsupported_fixture', 'synthetic fixture')
        e.run()
        if e.bootm is None:
            raise BoundaryError('environment-execution-failure', 'selected script did not reach bootm')
        return dict(bootm=[item.identity() for item in e.bootm], env_sha256=sd2.digest(e.values),
                    ram_size=inherited['afi']['gd_ram_size'], afi=inherited['afi']['exact_hex'])

    def boot_files(self, inherited):
        e = self.environment
        self.files = kernel, ramdisk, fdt = e.bootm
        if [file.identity() for file in self.files] != inherited['bootm'] or sd2.digest(e.values) != inherited['env_sha256']:
            raise BoundaryError('invalid-handoff-state', 'loaded files or bootm environment changed')
        if {(file.slot, file.device, file.partition) for file in self.files} != {(self.slot, self.files[0].device, 1)}:
            raise BoundaryError('invalid-handoff-state', 'boot files do not share the selected card and partition')
        k = legacy_image(kernel.data, 2, 32 << 20)
        r = legacy_image(ramdisk.data, 3, 32 << 20)
        total, reservations = fdt_layout(fdt.data)
        if total != len(fdt.data):
            raise BoundaryError('invalid-image', 'DTB length does not match totalsize')
        ranges = self._layout(e, inherited['ram_size'], k, r, total, reservations)
        return dict(kernel=k, ramdisk=r, fdt=fdt.identity(), input_dt_reservations=reservations,
                    intervals=ranges, images=inherited['bootm'], env_sha256=inherited['env_sha256'],
                    ram_size=inherited['ram_size'], afi=inherited['afi'])

    def _layout(self, env, ram_size, k, r, total, reservations):
        kernel, ramdisk, fdt = self.files
        addr = int(k['entry'], 16)
        if int(k['load'], 16) != kernel.address + 64 or addr != kernel.address + 64:
            raise BoundaryError('invalid-memory-layout', 'unsupported kernel copy or entry placement')
        policy = boot.ramdisk_fdt_policy(self.ub, {'variables': env.values})
        if not (policy['ramdisk_in_place'] and policy['fdt_in_place'] and policy['fdt_pad'] == '0x3000'):
            raise BoundaryError('unmodelled-dependency', 'U-Boot placement requires a relocation model')
        payload = kernel.data[64:64 + k['size']]
        if len(payload) < 0x30 or struct.unpack_from('<I', payload, 0x24)[0] != 0x016F2818:
            raise BoundaryError('invalid-image', 'kernel is not a supported ARM zImage')
        uncompressed = boot.zimage_decompressed_size(payload)
        if uncompressed is None or not 0 < uncompressed <= 64 << 20:
            raise BoundaryError('unmodelled-dependency', 'zImage decompression footprint unavailable')
        rows = [
            ('zImage buffer and decompression envelope', kernel.address,
             max(kernel.address + len(kernel.data), addr + uncompressed)),
            ('ramdisk file', ramdisk.address, ramdisk.address + len(ramdisk.data)),
            ('DTB with in-place padding', fdt.address, fdt.address + total + 0x3000),
            ('U-Boot helper scratch', 0x03C00000, 0x04000000),
            ('U-Boot load before relocation', self.uboot_image['load'],
             self.uboot_image['load'] + 64 + self.uboot_image['size']),
        ]
        bootm_addresses = {file.address for file in self.files}
        for address, file in sorted(env.loads.items()):
            if address not in bootm_addresses:
                rows.append((f'active environment/script buffer for {file.filename}', address, address + len(file.data)))
        for name, lo, hi in rows:
            if not 0 <= lo < hi <= ram_size:
                raise BoundaryError('invalid-memory-layout', f'{name} lies outside declared RAM')
        input_reservations = [(f'input DT reservation {i}', start, start + size)
                              for i, (start, size) in enumerate(reservations)]
        checks = rows + input_reservations
        for i, (name, lo, hi) in enumerate(checks):
            for other, start, end in checks[i + 1:]:
                if lo < end and start < hi:
                    raise BoundaryError('invalid-memory-layout', f'{name} overlaps {other}')
        return dict(ranges=[dict(name=name, start=lo, end=hi) for name, lo, hi in checks],
                    zimage_decompressed_size=uncompressed,
                    actual_relocation_region=None, zimage_self_relocation=None)

    def device_tree(self, inherited):
        e = self.environment
        k, r, fdt = self.files
        if [file.identity() for file in self.files] != inherited['images'] or sd2.digest(e.values) != inherited['env_sha256']:
            raise BoundaryError('invalid-handoff-state', 'handoff inputs changed after boot-file validation')
        if any(file.address + len(file.data) >= 0x04000000 for file in self.files):
            raise BoundaryError('unmodelled-dependency', 'bootm file address outside the helper mapping')
        rd = (r.address + 64, r.address + 64 + inherited['ramdisk']['size'])
        reservations = [(start, size) for start, size in inherited['input_dt_reservations']
                        if start + size <= inherited['ram_size']]
        reservations.append((0x03C00000, 0x400000))
        setup = boot.owl_fdt_setup_strings(self.ub)
        helper = boot.bootargs_helper(self.ub, int(setup['function'], 16))
        kwargs = dict(raw_afi=bytes.fromhex(inherited['afi']), reservations=reservations,
                      loaded_images=((k.address, k.data), (r.address, r.data)))
        def capture_machine(emu, images, gd):
            self.jump_context = (emu, images, gd)

        h = boot.handoff_emulation(
            self.ub, setup, helper, fdt.data, None, e.values, rd, inherited['ram_size'],
            gd_flags=0x100000 if self.scenario.strap_high else 0, fdt_addr=fdt.address,
            capture_machine=capture_machine, **kwargs)
        if h['error'] or h['return_value'] != 0:
            raise BoundaryError('device-tree-handoff-failure', h['error'] or f'handoff returned {h["return_value"]}')
        if (h['dt_memory_reg'] != ['0x0', hex(inherited['ram_size'])] or h['afi_in_memory'] != inherited['afi'] or
                tuple(int(h[key], 16) for key in ('initrd_start', 'initrd_end')) != rd or
                int(h['ft_addr'], 16) != fdt.address or not h['dt_chosen'].get('bootargs') or
                h['dt_chosen'].get('linux,initrd-start') != [hex(rd[0])] or
                h['dt_chosen'].get('linux,initrd-end') != [hex(rd[1])]):
            raise BoundaryError('device-tree-handoff-failure', 'DTB output disagrees with the supplied state')
        h['environment_after'] = {key: val for key, val in h['environment_after'].items() if val != e.values.get(key)}
        h['kernel_entry_from_header'] = inherited['kernel']['entry']
        return h

    def linux_entry(self, inherited):
        jump = boot.execute_linux_jump(self.ub, *self.jump_context, int(inherited['kernel_entry_from_header'], 16))
        if (not jump or jump['error'] or jump['stopped'] != 'before first Linux instruction' or
                jump['r0'] != 0 or jump['r2'] != inherited['ft_addr'] or not jump['irq_fiq_masked'] or
                jump['thumb'] or jump['mmu'] or jump['dcache'] or jump['icache']):
            raise BoundaryError('unmodelled-dependency', f'Linux transfer did not satisfy the bounded entry contract: {jump}')
        return jump


class Release:
    def __init__(self, directory, release):
        self.directory, self.name = Path(directory), release

    def __enter__(self):
        if self.name not in sd2.RELEASES:
            raise ValueError(f'unknown release {self.name}')
        path = self.directory / f'{self.name}.img'
        regular(path)
        self.f = path.open('rb')
        try:
            if not stat.S_ISREG(os.fstat(self.f.fileno()).st_mode):
                raise ValueError('firmware must be an ordinary file')
            self.loader, _, self.identity = sd2.load_release(self.directory, self.name, stream=self.f)
            self.disk = boot.Disk(self.f)
        except BaseException:
            self.f.close()
            raise
        return self

    def __exit__(self, *_):
        self.f.close()

    def run(self, scenario, detail=False):
        result = Execution(self.disk, self.loader, self.identity, scenario, detail).run()
        gc.collect()  # release Unicorn hook cycles between independent scenarios
        return result


def compare_observation(run, captured):
    """Compare only properties visible to OBS-001 or linked to its catalogue."""
    if run['terminal']['outcome'] != 'linux-entry-boundary':
        return dict(compared=False, reason='no Linux entry boundary')
    summary = captured['summary']
    stages = run['stages']
    fdt = stages['device-tree']['state']
    boot_files = stages['boot-files']['state']
    kernel = boot_files['images'][0]
    card = next(row for row in stages['mmc-registration']['state']['registration']['registered']
                if row['device_number'] == kernel['device'])
    cmdline = fdt['dt_chosen']['bootargs']
    tokens = dict(token.split('=', 1) for token in cmdline.split() if '=' in token)
    observed_dt = summary['device_tree']
    expected_chosen = observed_dt['chosen']
    input_uenv = next((f for f in run['environment']['loads']
                       if f['requested'].lower() == 'uenv.txt' and f['status'] == 'ok'), None)
    checks = {
        'complete_cmdline': (cmdline, summary['cmdline']['raw']),
        'chosen_bootargs': (cmdline, expected_chosen['bootargs']),
        'boot_dev': (tokens.get('boot_dev'), summary['cmdline']['boot_dev']),
        'boot_card_controller': (card['controller'].removeprefix('0x'), summary['storage_model']['boot_controller']),
        'console': (tokens.get('console'), summary['cmdline']['console'][0]),
        'memory_reg': (dict(zip(('base', 'size'), (int(v, 16) for v in fdt['dt_memory_reg']))),
                       observed_dt['memory_banks'][0]),
        'kernel_addressable_bytes': (fdt['board_memory'][1], int(summary['memory_model']['quantities']['kernel_system_ram_bytes'])),
        'initrd': ([int(fdt[k], 16) for k in ('initrd_start', 'initrd_end')],
                   [expected_chosen['initrd_start'], expected_chosen['initrd_end']]),
        'card_uenv_hash': (input_uenv['sha256'] if input_uenv else None, summary['card_files']['boot_uenv']['sha256']),
        'catalogued_dtb_hash': (boot_files['fdt']['sha256'], summary['device_tree_vs_reference']['reference_sha256']),
        'catalogued_kernel_version_link': (kernel['sha256'],
                                           summary['release_link']['kernel_version_matches'][0]['component_sha256']),
    }
    return dict(compared=True, authenticated_capture=bool(captured['capture']['admissible_as_evidence']),
                checks={name: dict(reconstructed=model, observed_or_linked=obs, equals=model == obs)
                        for name, (model, obs) in checks.items()},
                all_match=all(a == b for a, b in checks.values()),
                unobserved=['Boot ROM/CPU state', 'live AFI', 'analog training and physical DRAM geometry',
                            'early UART', 'pre-kernel DTB reservation block and relocation history'])


def compact_run(run):
    """Keep stage hashes and the handoff values that locate a divergence."""
    out = {k: v for k, v in run.items() if k not in ('firmware', 'assumptions', 'trace_detail', 'dram_result')}
    # Work on an evidence copy. Full stage envelopes remain available in 'run'.
    out = deepcopy(out)
    for stage, row in out['stages'].items():
        state = row.get('state', {})
        machine = state.get('machine')
        if machine and stage != 'recovery-resume-decision':
            keys = ('pc', 'boot_word', 'sram_sha256', 'trace', 'mmio_sha256')
            if stage in ('dram-and-main-dispatch', 'uboot-entry'):
                keys += ('cpu', 'sctlr', 'records', 'afi', 'gpio_sha256', 'gpio')
            state['machine'] = {key: machine[key] for key in keys}
        if stage in ('boot-device', 'mmc-registration'):
            state.pop('afi', None)
            if stage == 'boot-device':
                state.pop('registration', None)
        if stage == 'device-tree':
            state.pop('models', None)
            state.pop('console', None)
        if stage == 'block-0':
            state.pop('storage_reads', None)
        if stage == 'load-app-and-uboot' and out['stages']['uboot-entry']['status'] == 'completed':
            state.pop('uboot', None)
    for read in out['storage_reads']:
        if read.get('source_sha256') == read.get('loaded_sha256'):
            read.pop('source_sha256', None)
    dram_result = run.get('dram_result')
    if dram_result:
        out['dram_result'] = {key: dram_result[key] for key in (
            'boot_code_observed', 'outcome', 'terminal', 'caller_return', 'dram_return', 'capacity_mib',
            'record_selection', 'record_final', 'ini_initial', 'ini_final', 'afi', 'memory_test',
            'training', 'internal_codes', 'selected_mmio_final', 'gpio_final', 'trace')}
    return out


def isolated_afi_controls(ub):
    inputs = {
        'missing': bytes(16),
        'below-minimum': boot.afi_bytes(dev=0x22, size=7 << 20),
        'at-minimum': boot.afi_bytes(dev=0x22, size=8 << 20),
        'distinctive-reserved-byte': boot.afi_bytes(magic=b'AFI\xa5', dev=0x22),
    }
    return {name: afi_consumers(ub, raw) for name, raw in inputs.items()}


def suite(directory, releases=sd2.RELEASES):
    observed = json.loads(OBS.read_bytes())
    result = dict(format_version=VERSION, tool_version=VERSION, tool='unified_boot_chain.py',
                  tool_dependencies={**pre.tool_versions(), 'sd2_dram_analysis': sd2.TOOL_VERSION,
                                     'pyfatfs': version('pyfatfs')}, assumptions=ASSUMPTIONS, stage_graph=GRAPH,
                  stage_coverage=STAGES, firmware={}, scenarios={}, obs_001={}, isolated_afi_controls={},
                  reproduction='python tools/unified_boot_chain.py evidence --firmware-dir FW OUT.json')
    for release in releases:
        with Release(directory, release) as source:
            result['firmware'][release] = source.identity
            selected = SCENARIOS if release == REFERENCE else SCENARIOS[:2]
            runs = {}
            for scenario in selected:
                run = source.run(scenario)
                runs[scenario.name] = compact_run(run)
                if release == REFERENCE:
                    result['obs_001'][scenario.name] = compare_observation(run, observed)
                if release == REFERENCE and scenario.name == 'sd2-reference':
                    meta = run['stages']['uboot-entry']['state']['uboot']
                    code = source.disk.sectors(boot.UBOOT_DISK // 512, (meta['size'] + 64 + 511) // 512)[64:64 + meta['size']]
                    if boot.sha(code) != meta['payload_sha256']:
                        raise ValueError('consumer-control payload differs from the verified normal run')
                    result['isolated_afi_controls'] = isolated_afi_controls(boot.Blob(code, meta['entry'], 'U-Boot'))
            result['scenarios'][release] = runs
    return result


def evidence_bytes(doc):
    # One scenario per line keeps repeated checkpoint summaries compact.
    root = {key: val for key, val in doc.items() if key != 'scenarios'}
    text = json.dumps(root, indent=2, ensure_ascii=True)
    groups = []
    for release, rows in doc['scenarios'].items():
        lines = [f'      {json.dumps(name)}: {sd2.serial(row)}' for name, row in rows.items()]
        groups.append(f'    {json.dumps(release)}: {{\n' + ',\n'.join(lines) + '\n    }')
    return (text[:-2] + ',\n  "scenarios": {\n' + ',\n'.join(groups) + '\n  }\n}\n').encode('ascii')


def write_json_output(path, directory, data):
    # Refuse an alias to a pinned input, including hard links, before writing.
    inputs = [Path(directory) / f'{release}.img' for release in sd2.RELEASES]
    if path.exists():
        regular(path)
    for image in inputs:
        if path.resolve() == image.resolve() or (path.exists() and image.exists() and path.samefile(image)):
            raise ValueError('output would overwrite a firmware input')
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
        temporary = Path(temp.name)
        try:
            temp.write(data)
            temp.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def coverage(run):
    for name, row in run['stages'].items():
        print(f"{name:26s} {row['status']:10s} {row['method']}")
    if run['diagnostic_warning']:
        print(run['diagnostic_warning'])
    print(f"Terminal outcome: {run['terminal']['outcome']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list', help='list pinned releases and scenarios')
    run = commands.add_parser('run', help='execute a single scenario')
    run.add_argument('--scenario', default=SCENARIOS[0].name, choices=SCENARIO_BY_NAME)
    run.add_argument('--release', default=REFERENCE, choices=sd2.RELEASES)
    run.add_argument('--medium', choices=('sd0', 'sd2'))
    run.add_argument('--strap', choices=('low', 'high'))
    run.add_argument('--detail', action='store_true', help='include ordered loader events and full checkpoints')
    run.add_argument('--coverage', action='store_true', help='print the executed and blocked stages')
    run.add_argument('--compare-obs', action='store_true')
    run.add_argument('--output', type=Path, help='write local JSON, including trace if requested')
    summary = commands.add_parser('suite', help='execute focused controls and pinned references')
    summary.add_argument('--release', choices=sd2.RELEASES)
    evidence = commands.add_parser('evidence', help='regenerate the five-release evidence')
    evidence.add_argument('output', type=Path)
    for command in (run, summary, evidence):
        command.add_argument('--firmware-dir', default=os.environ.get('ATM_FIRMWARE_DIR'), type=Path)
    args = parser.parse_args()
    if args.command == 'list':
        print(json.dumps(dict(releases=sd2.RELEASES, scenarios=[vars(s) for s in SCENARIOS]), indent=2))
        return
    if args.firmware_dir is None:
        parser.error('use --firmware-dir or ATM_FIRMWARE_DIR with the pinned expanded images')
    try:
        if args.command == 'run':
            scenario = SCENARIO_BY_NAME[args.scenario]
            if args.medium:
                scenario = replace(scenario, medium=args.medium)
            if args.strap:
                scenario = replace(scenario, strap_high=args.strap == 'high')
            with Release(args.firmware_dir, args.release) as release:
                result = release.run(scenario, args.detail)
            if args.compare_obs:
                result['obs_001'] = compare_observation(result, json.loads(OBS.read_bytes()))
            if args.output:
                write_json_output(args.output, args.firmware_dir, (json.dumps(result, indent=2) + '\n').encode('utf-8'))
            if args.coverage:
                coverage(result)
                if args.compare_obs:
                    print(json.dumps(result['obs_001'], indent=2))
            elif not args.output:
                print(json.dumps(result, indent=2))
        else:
            releases = (args.release,) if args.command == 'suite' and args.release else sd2.RELEASES
            result = suite(args.firmware_dir, releases)
            if args.command == 'evidence':
                write_json_output(args.output, args.firmware_dir, evidence_bytes(result))
            else:
                for release, rows in result['scenarios'].items():
                    print(release)
                    for name, row in rows.items():
                        print(f"  {name:26s} {row['terminal']['outcome']}")
    except (OSError, ValueError) as error:
        parser.exit(1, f'{Path(__file__).name}: {error}\n')


if __name__ == '__main__':
    main()
