#!/usr/bin/env python3
"""ADFU decision routine 0xb4069254 and its GPIO C11->C10 loopback test (PR #9, second part).

Offline only. Builds on predram_analysis.py (same Code/Trace harness) and gpio_model.py (the synthetic GPIO
window). Four independent strands, each labelled in the evidence:

``decoded``     instruction anchors and region hashes read from the pinned images;
``executed``    the firmware's own instructions in Unicorn, at the routine boundary (r0 = ini word +0x14,
                boot-code word, PMIC register file, GpioModel) and along main / the PR #6 DRAM caller;
``reference``   ``reference_model``, a separate Python statement of the algorithm written from the
                instructions; it never calls the emulator or the GpioModel, but it does share the GPIO
                read-semantics and sample-window *assumptions*, so agreement checks the interpretation of the
                code, not physical behaviour;
``source``      pinned vendor pinctrl/DTS/header lines and the shipped DTBs (board-level mapping).

Usage::

    python tools/adfu_analysis.py evidence OUT.json --sources SRC_DIR --image koriki-v1.0=IMG [--image ...]
    python tools/adfu_analysis.py run IMG --boot-code 2 --arg 1 --pmic 0 --input follow
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import predram_analysis as P                     # noqa: E402
from gpio_model import GpioModel, C, C10, C11, PULLCTL, lfsr_bits   # noqa: E402

TOOL_VERSION = 1
ADFU = 0xB4069254
REENTRY = 0xB40691A4
PATTERN = 0x55AA55AA
PULL1 = PULLCTL[1]
OUTEN, INEN, DAT = C['outen'], C['inen'], C['dat']
SITE_DRIVE, SITE_SAMPLE, SITE_COMPARE = 0xB406935C, 0xB406936C, 0xB40693A8
ROM_ENTRY = 0xB4060000
LIMIT = 1_500_000

# Regions whose bytes the analysis depends on (VA ranges, end exclusive). Literal pools are included.
REGIONS = {
    'adfu_check incl. literal pool': (0xB4069254, 0xB40693E0),
    'rom_reentry_adfu incl. literal pool': (0xB40691A4, 0xB4069254),
    'adfu_fail_print': (0xB40693E0, 0xB40693F8),
    'delay_us/delay_ms incl. pool': (0xB40693F8, 0xB4069440),
    'timer_init/reset/start/count/base': (0xB4069440, 0xB4069524),
    'accessors 0xb4069194/0xb406919c': (0xB4069194, 0xB40691A4),
    'pmic t2 read/write + I2C t1 select': (0xB40695AC, 0xB40697FC),
    'get_boot_code incl. pool': (0xB40664F0, 0xB4066500),
    'dram_caller call site (ini word +0x14 -> r0)': (0xB4066658, 0xB4066688),
    'memcpy': (0xB406AF64, 0xB406AF84),
    'PMIC register table 0xb406b9d0': (0xB406B9D0, 0xB406B9D8),
    'strings pmu_status / Prepare to entry ADFU mode': (0xB406B295, 0xB406B2C4),
}

# (address, expected instruction text, interpretation). Verified per release by decode.
ANCHORS = [
    (0xB4069254, 'ldr r3, [pc, #0x164]', 'r3 = 0xb406b9d0 (PMIC register table)'),
    (0xB4069258, 'push {r4, r5, r6, r7, r8, lr}', 'callee-saved r4-r8 and lr pushed'),
    (0xB406925C, 'ldrh r6, [r3, #4]', 'r6 = halfword 0xb406b9d4 = 0x35 (status register number)'),
    (0xB4069260, 'mov r7, r0', 'r7 = argument (caller passes the ini word at +0x14)'),
    (0xB4069268, 'bl #0xb40697f4', 'pmic_read_t2(0x35) -> 0xb4069610: value, or -1 on I2C error (no retry)'),
    (0xB406926C, 'lsl r0, r0, #0x10', 'r5 = r0 & 0xffff (so -1 becomes 0xffff)'),
    (0xB4069270, 'lsr r5, r0, #0x10', ''),
    (0xB406927C, 'bl #0xb4066854', 'printf("pmu_status = 0x%x\\n", r5) - always printed'),
    (0xB4069280, 'ands r4, r5, #2', 'r4 = status & 2; only bit 1 is examined'),
    (0xB4069284, 'beq #0xb4069298', 'bit 1 clear -> guards'),
    (0xB4069288, 'bic r1, r5, #3', 'write-back value = status & ~3 (bits 0 and 1 cleared, 15:2 kept)'),
    (0xB4069290, 'bl #0xb40697f8', 'pmic_write_t2(0x35, value); return value ignored'),
    (0xB4069294, 'b #0xb40693b0', 'to the ADFU print and tail call; no GPIO access on this path'),
    (0xB4069298, 'cmp r7, #0', 'argument == 0 -> return (full 32-bit compare)'),
    (0xB406929C, 'popeq {r4, r5, r6, r7, r8, pc}', ''),
    (0xB40692A0, 'bl #0xb40664f0', 'get_boot_code() = word 0xb4064c00'),
    (0xB40692A4, 'cmp r0, #0', 'boot code == 0 -> return; any non-zero code runs the test'),
    (0xB40692A8, 'popeq {r4, r5, r6, r7, r8, pc}', ''),
    (0xB40692B8, 'ldr r6, [pc, #0x10c]', 'r6 = 0x55aa55aa (shift register for the drive bits)'),
    (0xB40692BC, 'mov r5, r4', 'r5 = r4 = 0: received word; r4 = 0 is also the loop counter (from the ands)'),
    (0xB40692C0, 'bic r0, r0, #0x20000', 'PAD_PULLCTL1 &= ~bit 17 (read-modify-write, never restored)'),
    (0xB40692D0, 'mov r8, r0', 'r8 = saved GPIO_CINEN'),
    (0xB40692DC, 'mov r7, r0', 'r7 = saved GPIO_COUTEN (argument no longer needed)'),
    (0xB40692EC, 'bic r0, r0, #0x400', 'COUTEN &= ~bit 10'),
    (0xB4069300, 'orr r0, r0, #0x400', 'CINEN |= bit 10'),
    (0xB4069314, 'bic r0, r0, #0x800', 'CINEN &= ~bit 11'),
    (0xB4069328, 'orr r0, r0, #0x800', 'COUTEN |= bit 11'),
    (0xB406933C, 'bic r0, r0, #0x800', 'loop: CDAT &= ~bit 11 (first write of the iteration)'),
    (0xB406934C, 'and r2, r6, #1', 'r2 = next drive bit (LSB of r6)'),
    (0xB4069354, 'lsr r6, r6, #1', 'r6 >>= 1'),
    (0xB4069358, 'orr r0, r0, r2, lsl #11', 'CDAT = (fresh read) | bit << 11 (second write; no clear)'),
    (0xB4069360, 'mov r0, #1', ''),
    (0xB4069364, 'bl #0xb4069434', 'delay_ms(1) = delay_us(1000): after the drive, before the sample'),
    (0xB4069370, 'tst r0, #0x400', 'sample CDAT bit 10'),
    (0xB406937C, 'orr r5, r5, r1, lsl r4', 'received |= sample << i (LSB first, same order as driven)'),
    (0xB4069380, 'add r4, r4, #1', ''),
    (0xB4069384, 'cmp r4, #0x20', '32 iterations; no exit inside the loop'),
    (0xB4069388, 'bne #0xb4069330', ''),
    (0xB4069390, 'ldr r1, [pc, #0x38]', 'CINEN := saved value (exact restore)'),
    (0xB406939C, 'ldr r1, [pc, #0x30]', 'COUTEN := saved value (exact restore)'),
    (0xB40693A4, 'ldr ip, [pc, #0x20]', 'ip = 0x55aa55aa (fresh literal; r6 is exhausted)'),
    (0xB40693A8, 'cmp r5, ip', 'exact 32-bit equality'),
    (0xB40693AC, 'popne {r4, r5, r6, r7, r8, pc}', 'mismatch -> normal return (r0 is not a status; caller ignores it)'),
    (0xB40693B4, 'bl #0xb4066854', 'printf("Prepare to entry ADFU mode\\n")'),
    (0xB40693B8, 'pop {r4, r5, r6, r7, r8, lr}', 'restores the caller\'s lr, then tail-calls'),
    (0xB40693BC, 'b #0xb40691a4', 'rom_reentry_adfu (never returns in practice)'),
]

PSEUDOCODE = '''\
adfu_check(arg):                                   ; 0xb4069254, arg = ini word +0x14 (1 in every release)
  reg  = halfword[0xb406b9d4]                      ; 0x35
  s    = pmic_read(reg) & 0xffff                   ; I2C error -> -1 -> 0xffff
  printf("pmu_status = 0x%x\\n", s)
  if s & 2:                                         ; only bit 1
      pmic_write(reg, s & ~3)                       ; result ignored
      goto enter                                    ; GPIO untouched
  if arg == 0: return
  if word[0xb4064c00] == 0: return                  ; boot code 0 (SD0) returns here
  PULLCTL1 = PULLCTL1 & ~(1 << 17)                  ; not restored
  in_saved  = CINEN ; out_saved = COUTEN
  COUTEN &= ~(1<<10) ; CINEN |= 1<<10               ; C10 input
  CINEN  &= ~(1<<11) ; COUTEN |= 1<<11              ; C11 output
  shift = 0x55aa55aa ; rx = 0
  for i in 0..31:                                   ; no early exit
      CDAT = CDAT & ~(1<<11)                        ; write 1
      CDAT = CDAT | ((shift & 1) << 11)             ; write 2 (fresh read, no clear)
      shift >>= 1
      delay_ms(1)
      rx |= ((CDAT >> 10) & 1) << i
  CINEN = in_saved ; COUTEN = out_saved
  if rx != 0x55aa55aa: return
enter:
  printf("Prepare to entry ADFU mode\\n")
  tail-call rom_reentry_adfu()                      ; 0xb40691a4
'''


def sha(b):
    return hashlib.sha256(bytes(b)).hexdigest()


# --------------------------------------------------------------------------- provenance and anchors

def region_hashes(code):
    return {k: dict(range=f'0x{a:08x}..0x{b:08x}', sha256=sha(code.bytes(a, b))) for k, (a, b) in REGIONS.items()}


def verify_anchors(code):
    rows = []
    for va, text, meaning in ANCHORS:
        i = code.insn(va)
        got = f'{i.mnemonic} {i.op_str}' if i else None
        rows.append(dict(at=f'0x{va:08x}', insn=got, matches=got == text, meaning=meaning))
    return rows


def literal(code, va):
    return code.word(va)


def decoded_constants(code):
    """Constants the reference model uses, read from the image (not typed in)."""
    pool = lambda at: code.word(at + 8 + code.insn(at).operands[-1].mem.disp)
    return dict(status_register=struct.unpack_from('<H', code.bytes(0xB406B9D4, 0xB406B9D6))[0],
                pattern=pool(0xB40692B8), compare=pool(0xB40693A4), pull_register=pool(0xB40692AC),
                outen=pool(0xB40692D4), inen=pool(0xB40692C8), dat=pool(0xB4069330),
                loop_count=int(code.insn(0xB4069384).op_str.split('#')[1], 0),
                pull_clear=int(code.insn(0xB40692C0).op_str.split('#')[1], 0),
                status_mask=int(code.insn(0xB4069280).op_str.split('#')[1], 0),
                status_clear=int(code.insn(0xB4069288).op_str.split('#')[1], 0),
                delay_ms=int(code.insn(0xB4069360).op_str.split('#')[1], 0))


# --------------------------------------------------------------------------- independent reference model

def _level(rule, window, c11_now, sent):
    """Pad level seen on C10 in sample window `window`, from the scenario's physical description."""
    kind = rule[0]
    if kind == 'const':
        return rule[1] & 1
    if kind == 'follow':
        return c11_now
    if kind == 'invert':
        return 1 - c11_now
    if kind == 'script':
        return rule[1][window] & 1 if 0 <= window < len(rule[1]) else rule[2]
    if kind == 'follow_except':
        return rule[2][window] & 1 if window in rule[2] else c11_now
    if kind == 'prbs':
        return lfsr_bits(rule[1])[window] if 0 <= window < 32 else 0
    if kind == 'delay':                          # one bit period (and a half) late: previous drive bit
        return sent[window - 1] if window >= 1 else rule[3]
    raise ValueError(kind)


def reference_model(k, boot_code, arg, pmic_status, initial, c10_rule, read_semantics='mixed', pmic_fail=False,
                    undriven=0, idle_level=0, other_inputs=None):
    """Statement of 0xb4069254 written from the instructions. k: decoded_constants()."""
    out = dict(gpio_test=False, pmic_writes=[], gpio_writes=[], delays_ms=0, received=None, sent=[],
               samples=[], decision=None)
    s = 0xFFFF if pmic_fail else pmic_status & 0xFFFF
    out['printed'] = [f'pmu_status = 0x{s:x}']
    regs = {a: initial.get(a, 0) & 0xFFFFFFFF for a in (k['outen'], k['inen'], k['dat'], k['pull_register'])}
    other_inputs = other_inputs or {}
    if s & k['status_mask']:
        out['pmic_writes'].append(dict(reg=k['status_register'], value=s & ~k['status_clear'] & 0xFFFF))
        out['decision'] = 'adfu (PMIC status bit 1)'
    elif arg == 0:
        out['decision'] = 'return (argument 0)'
    elif boot_code == 0:
        out['decision'] = 'return (boot code 0)'
    else:
        out['gpio_test'] = True
        window = -1

        def rd(a):
            if a != k['dat'] or read_semantics == 'latch':
                return regs[a]
            v, oe, ie = 0, regs[k['outen']], regs[k['inen']]
            for bit in range(32):
                m = 1 << bit
                if oe & m:
                    v |= regs[a] & m
                elif ie & m:
                    if bit == 10:
                        lv = _level(c10_rule, window, regs[a] >> 11 & 1 if oe & (1 << 11) else 0, out['sent'])
                    else:
                        lv = other_inputs.get(bit, idle_level)
                    v |= lv << bit
                else:
                    v |= (undriven & 1) << bit
            return v

        def wr(a, v):
            regs[a] = v & 0xFFFFFFFF
            out['gpio_writes'].append((a, regs[a]))

        wr(k['pull_register'], rd(k['pull_register']) & ~k['pull_clear'])
        in_saved, out_saved = rd(k['inen']), rd(k['outen'])
        wr(k['outen'], rd(k['outen']) & ~0x400)
        wr(k['inen'], rd(k['inen']) | 0x400)
        wr(k['inen'], rd(k['inen']) & ~0x800)
        wr(k['outen'], rd(k['outen']) | 0x800)
        shift, rx = k['pattern'], 0
        for i in range(k['loop_count']):
            wr(k['dat'], rd(k['dat']) & ~0x800)
            bit = shift & 1
            shift >>= 1
            wr(k['dat'], rd(k['dat']) | bit << 11)
            out['sent'].append(bit)
            out['delays_ms'] += k['delay_ms']
            window += 1                                 # the delay opens the next sample window
            smp = rd(k['dat']) >> 10 & 1
            out['samples'].append(smp)
            rx |= smp << i
        wr(k['inen'], in_saved)
        wr(k['outen'], out_saved)
        out['received'] = rx
        out['decision'] = 'adfu (loopback matched)' if rx == k['compare'] else 'return (loopback mismatch)'
    out['final'] = {f'0x{a:08x}': f'0x{v:08x}' for a, v in sorted(regs.items())}
    if out['decision'].startswith('adfu'):
        out['printed'].append('Prepare to entry ADFU mode')
    return out


# --------------------------------------------------------------------------- firmware execution

def routine_trace(doc, boot_code, arg, pmic_status, gpio, pmic_fail=False, timer_step=24, limit=LIMIT):
    """Execute 0xb4069254(arg) with explicit state: boot code word, PMIC reg 0x35, GpioModel; the I2C bus is
    pre-selected (globals as pmu_init leaves them: bus 1 at 0xb4070864 and the cache 0xb406ba10)."""
    t = P.Trace(doc['loader'], None, doc['code'], doc['funcs'], boot_code, pmic={0x35: pmic_status}, gpio=gpio,
                timer_step=timer_step, i2c_fail_regs=(0x35,) if pmic_fail else (), limit=limit)
    t.emu.uc.mem_write(0xB4070864, b'\x01')
    t.emu.uc.mem_write(0xB406BA10, struct.pack('<I', 1))
    seen = {}
    orig = t.emu.on_code

    def hook(pc):
        orig(pc)
        if pc == SITE_COMPARE:
            seen['r5'], seen['ip'] = t.emu.reg(5), t.emu.reg(12)
    t.emu.on_code = hook
    res = t.run_function(ADFU, (arg,))
    return t, res, seen


def classify(res, t):
    if res['error']:
        if res['error'].startswith('instruction limit'):
            pc = int(res['error'].rsplit('0x', 1)[1], 16)
            fn = next((P.NAMES[f] for f, _ in reversed(t.stack) if f in P.NAMES), None)
            return 'instruction budget exhausted (emulator bound, not a firmware timeout)', fn
        return 'emulator error: ' + res['error'], None
    if res['stopped'] == 'return':
        return 'normal return', None
    if res['stopped'] and res['stopped'].startswith('ROM re-entry'):
        return 'ADFU boundary (0xb40691a4 reached)', None
    return 'stopped: ' + str(res['stopped']), None


def summarise(t, res, seen, gpio, initial):
    gw = [e for e in t.events if e['op'] == 'write' and gpio.covers(e['address'])]
    drives = [e for e in gw if e['pc'] == SITE_DRIVE]
    samples = [e for e in t.events if e['op'] == 'read' and e['pc'] == SITE_SAMPLE]
    outcome, where = classify(res, t)
    unexpected_mmio = sorted({P.h32(e['address']) for e in t.events if e['op'] in ('read', 'write')
                              and not gpio.covers(e['address']) and e['address'] != 0xB0168010})
    final = gpio.state()
    init = {gpio.window[a]: f'0x{initial.get(a, 0) & 0xFFFFFFFF:08x}' for a in sorted(gpio.window)}
    changed = {r: dict(initial=init[r], final=final[r], changed_bits=f'0x{int(init[r], 16) ^ int(final[r], 16):08x}')
               for r in final if init[r] != final[r]}
    return dict(outcome=outcome, stopped_in=where, instructions=res['instructions'],
                driven_bits=[e['value'] >> 11 & 1 for e in drives],
                sampled_bits=[e['value'] >> 10 & 1 for e in samples],
                received_word=P.h32(seen['r5']) if 'r5' in seen else None,
                compared_with=P.h32(seen['ip']) if 'ip' in seen else None,
                delay_calls=len(t.delays), delay_us_requested=sum(d['us'] for d in t.delays),
                pmic=[dict(op=o, reg=f'0x{r:02x}', value=f'0x{v:04x}') for o, r, v in t.pmic.log],
                gpio_writes=[(P.h32(e['address']), P.h32(e['value'])) for e in gw],
                gpio_write_count=len(gw), initial=init, final=final, changed=changed,
                unexpected_gpio_accesses=gpio.unexpected, other_mmio=unexpected_mmio,
                printed=t.printed, model_clock_us=gpio.now)


def compare(ref, fw, gpio_window):
    """Field-by-field agreement of the reference model with the firmware run."""
    checks = {}
    fw_adfu = fw['outcome'].startswith('ADFU')
    checks['decision'] = ref['decision'].startswith('adfu') == fw_adfu
    checks['gpio_test_ran'] = ref['gpio_test'] == (fw['gpio_write_count'] > 0)
    checks['pmic_writes'] = [dict(reg=f"0x{w['reg']:02x}", value=f"0x{w['value']:04x}") for w in ref['pmic_writes']] \
        == [dict(reg=x['reg'], value=x['value']) for x in fw['pmic'] if x['op'] == 'w']
    checks['delays'] = ref['delays_ms'] * 1000 == fw['delay_us_requested']
    checks['driven_bits'] = ref['sent'] == fw['driven_bits']
    checks['sampled_bits'] = ref['samples'] == fw['sampled_bits']
    checks['received_word'] = (ref['received'] is None and fw['received_word'] is None) or \
        P.h32(ref['received']) == fw['received_word']
    checks['gpio_write_sequence'] = [(P.h32(a), P.h32(v)) for a, v in ref['gpio_writes']] == \
        [tuple(x) for x in fw['gpio_writes']]
    names = {f'0x{a:08x}': n for a, n in gpio_window.items()}
    checks['final_registers'] = all(fw['final'][names[a]] == v for a, v in ref['final'].items())
    checks['printed'] = ref['printed'] == fw['printed']
    return dict(agree=all(checks.values()), checks=checks)


ZERO = {}
ONES = {OUTEN: 0xFFFFFFFF, INEN: 0xFFFFFFFF, DAT: 0xFFFFFFFF, PULL1: 0xFFFFFFFF}
MIXED = {OUTEN: 0x0000F0F0, INEN: 0x00FF0F00, DAT: 0x12345678, PULL1: 0x00030000}
UNRELATED = {OUTEN: 0x80000001, INEN: 0x00010000, DAT: 0x80000001, PULL1: 0x00020000}


def pattern_bits(p=PATTERN):
    return [(p >> i) & 1 for i in range(32)]


def _late_match(n):
    return ('script', [1 - b if i < n else b for i, b in enumerate(pattern_bits())], 0)


# name, boot_code, arg, pmic, rule, initial, extras
SCENARIOS = [
    ('pmic-0x0000', 2, 1, 0x0000, ('const', 0), ZERO, {}),
    ('pmic-0x0001-bit0-only', 2, 1, 0x0001, ('const', 0), ZERO, {}),
    ('pmic-0x0002-bit1', 2, 1, 0x0002, ('follow', C11), ZERO, {}),
    ('pmic-0x0003-bits01', 2, 1, 0x0003, ('follow', C11), ZERO, {}),
    ('pmic-0xff06-bit1-plus-high', 2, 1, 0xFF06, ('follow', C11), ONES, {}),
    ('pmic-0x8005-unrelated-no-bit1', 2, 1, 0x8005, ('const', 0), ZERO, {}),
    ('pmic-read-failure', 2, 1, 0x0000, ('const', 0), ZERO, dict(pmic_fail=True)),
    ('pmic-bit1-code0', 0, 1, 0x0002, ('follow', C11), ZERO, {}),
    ('pmic-bit1-arg0', 2, 0, 0x0002, ('follow', C11), ZERO, {}),
    ('guard-code0-loopback', 0, 1, 0, ('follow', C11), ZERO, {}),
    ('guard-arg0-loopback', 2, 0, 0, ('follow', C11), ZERO, {}),
    ('guard-arg-0x80000000', 2, 0x80000000, 0, ('follow', C11), ZERO, {}),
    ('guard-code1', 1, 1, 0, ('follow', C11), ZERO, {}),
    ('guard-code4', 4, 1, 0, ('follow', C11), ZERO, {}),
    ('guard-code5', 5, 1, 0, ('follow', C11), ZERO, {}),
    ('guard-code-0x80000000', 0x80000000, 1, 0, ('follow', C11), ZERO, {}),
    ('input-loopback', 2, 1, 0, ('follow', C11), ZERO, {}),
    ('input-low', 2, 1, 0, ('const', 0), ZERO, {}),
    ('input-high', 2, 1, 0, ('const', 1), ZERO, {}),
    ('input-inverted', 2, 1, 0, ('invert', C11), ZERO, {}),
    ('input-one-wrong-bit-13', 2, 1, 0, ('follow_except', C11, {13: 1 - pattern_bits()[13]}), ZERO, {}),
    ('input-wrong-first-bit', 2, 1, 0, ('follow_except', C11, {0: 1 - pattern_bits()[0]}), ZERO, {}),
    ('input-wrong-last-bit', 2, 1, 0, ('follow_except', C11, {31: 1 - pattern_bits()[31]}), ZERO, {}),
    ('input-wrong-bits-3-9-22', 2, 1, 0, ('follow_except', C11, {i: 1 - pattern_bits()[i] for i in (3, 9, 22)}),
     ZERO, {}),
    ('input-prbs-0x1234', 2, 1, 0, ('prbs', 0x1234), ZERO, {}),
    ('input-one-bit-delayed', 2, 1, 0, ('delay', C11, 1500, 0), ZERO, {}),
    ('input-interrupted-after-16', 2, 1, 0, ('follow_except', C11, {i: 0 for i in range(16, 32)}), ZERO, {}),
    ('input-matches-from-bit-8', 2, 1, 0, _late_match(8), ZERO, {}),
    ('semantics-latch-loopback', 2, 1, 0, ('follow', C11), ZERO, dict(read_semantics='latch')),
    ('semantics-latch-latch-preset', 2, 1, 0, ('follow', C11), {DAT: 0x400}, dict(read_semantics='latch')),
    ('init-ones-loopback', 2, 1, 0, ('follow', C11), ONES, {}),
    ('init-ones-low', 2, 1, 0, ('const', 0), ONES, {}),
    ('init-mixed-loopback', 2, 1, 0, ('follow', C11), MIXED, {}),
    ('init-mixed-low', 2, 1, 0, ('const', 0), MIXED, {}),
    ('init-unrelated-bits-low', 2, 1, 0, ('const', 0), UNRELATED, {}),
    ('init-unrelated-bits-undriven-high', 2, 1, 0, ('const', 0), UNRELATED, dict(undriven=1, idle_level=1)),
    ('init-pull-bit17-set', 2, 1, 0, ('const', 0), {PULL1: 0x00020000}, {}),
    ('init-pull-bit17-clear', 2, 1, 0, ('const', 0), {PULL1: 0xFFFDFFFF}, {}),
    ('init-c11-latch-set', 2, 1, 0, ('const', 0), {DAT: 0x800}, {}),
    ('init-c11-latch-clear', 2, 1, 0, ('const', 0), {DAT: 0xFFFFF7FF}, {}),
    ('init-c10-was-output', 2, 1, 0, ('follow', C11), {OUTEN: 0x400, DAT: 0x400}, {}),
]


def run_scenario(doc, k, name, bc, arg, pmic, rule, initial, extras):
    sem = extras.get('read_semantics', 'mixed')
    gpio = GpioModel(initial=dict(initial), inputs={C10: rule}, read_semantics=sem,
                     undriven=extras.get('undriven', 0), idle_level=extras.get('idle_level', 0), label=name)
    t, res, seen = routine_trace(doc, bc, arg, pmic, gpio, pmic_fail=extras.get('pmic_fail', False))
    fw = summarise(t, res, seen, gpio, initial)
    ref = reference_model(k, bc, arg, pmic, initial, rule, read_semantics=sem, pmic_fail=extras.get('pmic_fail', False),
                          undriven=extras.get('undriven', 0), idle_level=extras.get('idle_level', 0))
    cmp_ = compare(ref, fw, gpio.window)
    fw_compact = {k2: v for k2, v in fw.items() if k2 != 'gpio_writes'}
    fw_compact['gpio_writes_sha256'] = sha(json.dumps(fw['gpio_writes']).encode())
    return dict(name=name, inputs=dict(boot_code=P.h32(bc), arg=P.h32(arg), pmic_status=f'0x{pmic:04x}',
                                       pmic_read_fails=extras.get('pmic_fail', False), gpio_model=gpio.describe()),
                firmware=fw_compact, reference=dict(decision=ref['decision'], gpio_test=ref['gpio_test'],
                                                    received=None if ref['received'] is None else P.h32(ref['received']),
                                                    delays_ms=ref['delays_ms'], final=ref['final'],
                                                    pmic_writes=[dict(reg=f"0x{w['reg']:02x}", value=f"0x{w['value']:04x}")
                                                                 for w in ref['pmic_writes']]),
                comparison=cmp_)


def stalled_timer(doc):
    gpio = GpioModel(inputs={C10: ('const', 0)}, label='timer-stalled')
    t, res, seen = routine_trace(doc, 2, 1, 0, gpio, timer_step=0, limit=200_000)
    outcome, where = classify(res, t)
    return dict(name='timer-stalled (T0 count never advances)', outcome=outcome, stopped_in=where,
                instruction_limit=200_000, delay_calls_entered=len(t.delays), gpio_writes=len(
                    [e for e in t.events if e['op'] == 'write' and gpio.covers(e['address'])]),
                note='delay_us 0xb40693f8 polls with no iteration bound; the firmware implements no timeout. The '
                     'run ends only because the emulator stops at its instruction budget.')


def full_path(doc, label, boot_code, rule):
    """main from 0xb4065400 with the GpioModel: where does execution end, and what GPIO state reaches the
    DRAM boundary?"""
    gpio = GpioModel(inputs={C10: rule}, label=label, strict=False)
    t = P.Trace(doc['loader'], P.Disk(doc['path']), doc['code'], doc['funcs'], boot_code, gpio=gpio)
    res = t.run()
    gw = [e for e in t.events if e['op'] in ('read', 'write') and gpio.covers(e['address'])]
    fns = sorted({P.NAMES.get(e['function'], P.h32(e['function'])) for e in gw})
    return dict(name=label, boot_code=boot_code, stopped=res['stopped'], error=res['error'],
                reached_dram_init=bool(res['stopped'] and res['stopped'].startswith('DRAM init entry')),
                gpio_accesses=len(gw), gpio_access_functions=fns, final_gpio=gpio.state(),
                passthrough_addresses=sorted({x['address'] for x in gpio.passthrough}), unexpected=gpio.unexpected,
                delays_us=sum(d['us'] for d in t.delays))


def dram_stage(doc):
    """PR #6 DRAM caller with the GpioModel (reference scenario only): code 0, code 2 with C10 low and code 2
    with ideal loopback."""
    import dram_complete as D
    out = {}
    runs = {}
    for label, bc, rule in (('code0', 0, ('const', 0)), ('code2-low', 2, ('const', 0)),
                            ('code2-loopback', 2, ('follow', C11))):
        gpio = GpioModel(inputs={C10: rule}, label=label, strict=False)
        o, h = D.run_caller(doc['loader'], D.Pmic(), D.TRAINING_SCENARIOS[0], boot_code=bc, gpio=gpio)
        w = [(x['address'], x['value']) for x in h.writes]
        test_regs = {P.h32(a) for a in (OUTEN, INEN, DAT, PULL1)}
        last_test = max((i for i, (a, _) in enumerate(w) if a in test_regs), default=-1)
        window = [(i, a, v) for i, (a, v) in enumerate(w) if gpio.covers(int(a, 16))]
        runs[label] = (w, gpio)
        out[label] = dict(stopped=o['caller']['stopped']['name'] if o['caller']['stopped'] else None,
                          return_value=o['caller']['return_value'], afi_boot_dev=o['caller']['afi']['boot_dev']
                          if o['caller']['afi']['magic_ok'] else None,
                          reached_dram_routine='dram' in o['functions'], mmio_writes=len(w),
                          gpio_block_writes=len(window),
                          gpio_block_writes_outside_test=[dict(index=i, address=a, value=v) for i, a, v in window
                                                          if a not in test_regs],
                          writes_after_test_to_test_registers=[dict(index=i, address=a, value=v) for i, a, v in window
                                                               if i > last_test and a in test_regs],
                          final_gpio=gpio.state(), passthrough_addresses=sorted({x['address'] for x in gpio.passthrough}),
                          unexpected=gpio.unexpected, model_clock_us=gpio.now)
    strip = lambda w, g: [x for x in w if not g.covers(int(x[0], 16))]
    out['code0_vs_code2_low_non_gpio_writes_identical'] = strip(*runs['code0']) == strip(*runs['code2-low'])
    out['note'] = ('dram_complete.run_caller(..., boot_code=b, gpio=GpioModel(...)); scenario "reference"; every '
                   'PUBL/uPCTL/PMIC response synthetic. Other DRAM scenarios not re-run (out of scope).')
    return out


def reentry_boundary(doc):
    """Execute 0xb40691a4 up to the jump into SRAM 0xb4060000 (then ROM code). ROM bytes are not available:
    the memcpy from 0xffff5200 is recorded, not performed, and execution stops at the jump target."""
    t = P.Trace(doc['loader'], None, doc['code'], doc['funcs'], 2, rom_copy_stub=True)
    t.emu.stops = {ROM_ENTRY: 'jump to 0xb4060000 (SRAM now holds the ROM copy; not emulated)',
                   P.DRAM_COLD: 'DRAM init (must not be reached)', P.ADFU_EXIT: 'ADFU exit'}
    res = t.run_function(REENTRY)
    ev = []
    for e in t.events:
        if e['op'] in ('read', 'write') and e['address'] != 0xB0168010:
            ev.append(f"{e['op']} {P.h32(e['address'])} = {P.h32(e['value'])}")
        elif e['op'] == 'rom-copy-requested':
            ev.append(f"ROM copy requested: {e['length']:#x} bytes {e['source']} -> {e['dest']} (not performed)")
    return dict(stopped=res['stopped'], error=res['error'], sp_at_jump=res['regs_at_stop'][4] if res['regs_at_stop']
                else None, events=ev, delays=[d['us'] for d in t.delays], rom_copies=t.rom_copies,
                reached_dram_init=res['stopped'] == 'DRAM init (must not be reached)',
                sequence=[
                    '0xb40691ac timer_init(0) again', '0xb40691bc memcpy(0xb4060000, ROM 0xffff5200, 0x2e00): '
                    'overwrites block 0, the AFI 0xb4060300 and SRAM up to 0xb4062e00 (part of the ini copy)',
                    '0xb40691c4 delay_ms(5)', '0xb40691d0 CMU 0xb0160000 := 0x30a', '0xb40691dc CMU 0xb0160004 := 0x114',
                    '0xb40691e4 delay_ms(5)', '0xb40691f8 0xb0160004 |= 0x1000', '0xb406920c 0xb016001c &= ~0xf0000',
                    '0xb4069214 delay_us(5)', '0xb406921c VBAR := 0xffff0000', '0xb4069224 SP := 0xb4070800',
                    '0xb406922c blx 0xb4060000 (r3 = 0xb4070800 - 0x10800)'],
                note='If the ROM code ever returned, 0xb4069230 would pop {r3, pc} from the new stack at 0xb4070800 '
                     '(loader globals), not the caller\'s frame, so a return is not a defined path. DRAM init is '
                     'not reached from here.')


# --------------------------------------------------------------------------- downstream dependencies

WATCH = {0xB01B0064: 'PAD_PULLCTL1', 0xB01B0020: 'GPIO_CDAT', 0xB01B0018: 'GPIO_COUTEN', 0xB01B001C: 'GPIO_CINEN',
         0xB01B0048: 'MFP_CTL2'}


def downstream_static(doc):
    code = doc['code']
    out = {}
    for label, roots in (('reachable from main (pre- and post-DRAM)', (P.MAIN,)),
                         ('DRAM routine subtree from 0xb40690b8', (P.DRAM_COLD,))):
        funcs = P.call_graph(code, roots=roots, stop_at=())
        rows = P.static_accesses(code, funcs)
        hits = [dict(site=r['instruction'], function=r['function_name'] or r['function'], access=r['access'],
                     register=WATCH[int(r['address'], 16)])
                for r in rows if r['address'] and int(r['address'], 16) in WATCH and r['function'] != P.h32(ADFU)]
        out[label] = dict(functions=sum(1 for f in funcs if funcs[f]), watched_accesses_outside_adfu_check=hits,
                          unresolved_accesses=sum(1 for r in rows if r['region'] == 'unresolved'))
    return out


def later_stage_literals(doc):
    import boot_chain as bc
    f, loader, hdr, payload, ub = bc.read_regions(doc['path'])
    res = {}
    for name, blob, base in (('app.bin (loader 0x19000.., runs at 0x1000)', loader[0x19000:0x38000], 0x1000),
                             ('U-Boot payload (0x05000000)', payload, 0x05000000)):
        hits = {}
        for o in range(0, len(blob) - 3, 4):
            w = struct.unpack_from('<I', blob, o)[0]
            if w in WATCH:
                hits.setdefault(WATCH[w], []).append(P.h32(base + o))
        res[name] = {k: dict(count=len(v), first=v[:4]) for k, v in sorted(hits.items())}
    res['app.bin 0x9430'] = ('decoded: PAD_PULLCTL1 = (v & ~0x3f000) | 0x3e000 (sets bits 13-17, clears 12: by the '
                             'vendor table the pull bits of SD0 CMD, D3..D0 set and SD0_CLK cleared); no direct caller '
                             'found, so whether it runs on the shipped (SFVD present) path is not established')
    res['note'] = 'Literal words are data, not proof of use; only app.bin 0x9430 was decoded.'
    return res


# --------------------------------------------------------------------------- board-level sources

SOURCE_CHECKS = [
    ('vendor-kernel', 'arch/arm/mach-owl/pinctrl_data-atm7059.c', [
        (r'#define P_SD0_D0\s+_GPIOC\(10\)', 'GPIOC10 is the P_SD0_D0 pad'),
        (r'#define P_SD0_D1\s+_GPIOC\(11\)', 'GPIOC11 is the P_SD0_D1 pad'),
        (r'#define _GPIOC\(offset\)\s+\(64 \+ \(offset\)\)', 'GPIO numbering: C = 64 + n'),
        (r'PAD_PULL_CONF\(P_SD0_D0, 1, 17, 1, 0x1, 0\)', 'PAD_PULLCTL1 bit 17 = P_SD0_D0 pull, width 1, pull-up value '
                                                        '1, no pull-down value'),
        (r'PAD_PULL_CONF\(P_SD0_D1, 1, 16, 1, 0x1, 0\)', 'PAD_PULLCTL1 bit 16 = P_SD0_D1 pull (not touched by the test)'),
        (r'owl_mfp2_19_17_pads\[\] = \{\s*P_SD0_D0', 'MFP_CTL2[19:17] selects the P_SD0_D0 function'),
        (r'owl_mfp2_19_17_funcs\[\] = \{\s*OWL_MUX_SD0,\s*OWL_MUX_NOR,\s*OWL_MUX_RESERVED,\s*OWL_MUX_JTAG,'
         r'\s*OWL_MUX_UART2,\s*OWL_MUX_UART5', 'values 0 SD0, 1 NOR, 2 reserved, 3 JTAG, 4 UART2, 5 UART5'),
        (r'owl_mfp2_16_14_pads\[\] = \{\s*P_SD0_D1', 'MFP_CTL2[16:14] selects the P_SD0_D1 function'),
        (r'owl_mfp2_16_14_funcs\[\] = \{\s*OWL_MUX_SD0,\s*OWL_MUX_NOR,\s*OWL_MUX_RESERVED,\s*OWL_MUX_RESERVED,'
         r'\s*OWL_MUX_UART2', 'values 0 SD0, 1 NOR, 4 UART2'),
        (r'owl_mfp2_13_11_pads\[\] = \{\s*P_SD0_D2,\s*P_SD0_D3', 'MFP_CTL2[13:11] selects SD0_D2/D3'),
        (r'owl_mfp2_8_7_pads\[\] = \{\s*P_SD0_CMD', 'MFP_CTL2[8:7] selects SD0_CMD'),
        (r'owl_mfp2_6_5_pads\[\] = \{\s*P_SD0_CLK', 'MFP_CTL2[6:5] selects SD0_CLK'),
    ]),
    ('vendor-kernel', 'arch/arm/mach-owl/include/mach/regs_map-atm7039.h', [
        (r'#define GPIO_COUTEN\s+\(GPIO_MFP_PWM_BASE\+0x0018\)', 'GPIO_COUTEN = 0xb01b0018'),
        (r'#define GPIO_CINEN\s+\(GPIO_MFP_PWM_BASE\+0x001C\)', 'GPIO_CINEN = 0xb01b001c'),
        (r'#define GPIO_CDAT\s+\(GPIO_MFP_PWM_BASE\+0x0020\)', 'GPIO_CDAT = 0xb01b0020'),
        (r'#define MFP_CTL2\s+\(GPIO_MFP_PWM_BASE\+0x0048\)', 'MFP_CTL2 = 0xb01b0048'),
        (r'#define PAD_PULLCTL1\s+\(GPIO_MFP_PWM_BASE\+0x0064\)', 'PAD_PULLCTL1 = 0xb01b0064'),
    ]),
    ('vendor-kernel', 'arch/arm/boot/dts/rg35xx_atm7039.dts', [
        (r'mmc0_state_default: mmc0_default', 'SD0 default pin state'),
        (r'actions,groups = "mfp2_19_17", "mfp2_16_14", "mfp2_13_11", "mfp2_8_7", "mfp2_6_5";\s*'
         r'actions,function = "sd0";', 'SD0 data/cmd/clk groups muxed to sd0'),
        (r'actions,pins = "P_SD0_D0", "P_SD0_D1", "P_SD0_D2", "P_SD0_D3", "P_SD0_CMD";\s*actions,pull = <2>;',
         'SD0 D0-D3/CMD pull <2>'),
        (r'mmc_share_uart_state: mmc_share_uart', 'alternative SD0 state sharing UART'),
        (r'actions,groups = "mfp2_19_17","mfp2_16_14";\s*actions,function = "uart5";',
         'D0/D1 groups as UART5 (serial5_default and mmc_share_uart)'),
    ]),
]


def source_evidence(src_dir):
    """Re-derive line numbers of the board-level facts from the pinned files (hash-checked)."""
    files = {(x['source'], x['path']): x for x in json.loads((ROOT / 'evidence/files.json').read_text())}
    from build_dataset import REPOS
    out = []
    for source, path, checks in SOURCE_CHECKS:
        meta = files[(source, path)]
        p = Path(src_dir) / REPOS[source][0] / path
        if not p.exists():
            p = Path(src_dir) / source / path
        text = p.read_bytes()
        if sha(text) != meta['sha256']:
            raise ValueError(f'{path}: hash differs from evidence/files.json')
        t = text.decode('utf-8', 'replace')
        for rx, meaning in checks:
            m = re.search(rx, t)
            if not m:
                out.append(dict(source=source, path=path, sha256=meta['sha256'], found=False, meaning=meaning))
                continue
            l1 = t.count('\n', 0, m.start()) + 1
            l2 = t.count('\n', 0, m.end()) + 1
            out.append(dict(source=source, path=path, sha256=meta['sha256'], line_start=l1, line_end=l2, found=True,
                            meaning=meaning))
    return out


def dtb_survey(path):
    """Shipped kernel.dtb: every property that names the SD0_D0/D1 pads or groups, and any GPIO specifier that
    points at pin 74 or 75."""
    import boot_chain as bc
    f = open(path, 'rb')
    part = bc.gpt_partition1(f)
    name, d = bc.fat_files(f, part, ['kernel.dtb'])['kernel.dtb']
    magic, total, off_struct, off_strings = struct.unpack_from('>4I', d, 0)
    p, stack, strs, gpios = off_struct, [], [], []
    while True:
        tok = struct.unpack_from('>I', d, p)[0]
        p += 4
        if tok == 1:
            e = d.index(b'\0', p)
            stack.append(d[p:e].decode('latin1'))
            p = (e + 4) & ~3
        elif tok == 3:
            ln, no = struct.unpack_from('>II', d, p)
            p += 8
            val = d[p:p + ln]
            p = (p + ln + 3) & ~3
            e = d.index(b'\0', off_strings + no)
            prop = d[off_strings + no:e].decode('latin1')
            node = '/' + '/'.join(x for x in stack if x)
            items = [s.decode('latin1', 'replace') for s in val.split(b'\0') if s]
            if any(k in ' '.join(items) for k in ('mfp2_19_17', 'mfp2_16_14', 'P_SD0_D0', 'P_SD0_D1')) or \
                    'jtag' in ' '.join(items).lower():
                strs.append(dict(node=node, property=prop, value=items))
            if 'gpio' in prop and ln % 4 == 0 and ln >= 8:
                cells = struct.unpack(f'>{ln // 4}I', val)
                if any(cells[i + 1] in (74, 75) for i in range(0, len(cells) - 1, 3)):
                    gpios.append(dict(node=node, property=prop, cells=[hex(c) for c in cells]))
        elif tok == 2:
            stack.pop()
        elif tok == 9:
            break
    pinstate = {}
    for x in strs:
        pinstate.setdefault(x['node'].rsplit('/', 1)[0], []).append(x)
    return dict(file=name, sha256=sha(d), size=len(d), references=strs, gpio_74_75_specifiers=gpios)


def board_mfp_decode(code):
    """What board_mfp_init (ini+0x0d = 1) writes into the SD0 mux fields, using the vendor function lists."""
    reg, clr, st = code.word(0xB406B4D4), code.word(0xB406B4D8), code.word(0xB406B4DC)   # table entry 1
    if reg != 0xB01B0048:
        raise ValueError('board_mfp_init entry 1 does not target MFP_CTL2')
    fields = [('19:17', 'P_SD0_D0 (C10)', ['SD0', 'NOR', 'RESERVED', 'JTAG', 'UART2', 'UART5']),
              ('16:14', 'P_SD0_D1 (C11)', ['SD0', 'NOR', 'RESERVED', 'RESERVED', 'UART2']),
              ('13:11', 'P_SD0_D2, P_SD0_D3', ['SD0', 'NOR', 'RESERVED', 'JTAG', 'UART2', 'UART1']),
              ('8:7', 'P_SD0_CMD', ['SD0', 'NOR', 'RESERVED', 'JTAG']),
              ('6:5', 'P_SD0_CLK', ['SD0', 'RESERVED', 'JTAG'])]
    rows = []
    for rng, pads, funcs in fields:
        hi, lo = (int(x) for x in rng.split(':'))
        mask = ((1 << (hi - lo + 1)) - 1) << lo
        if clr & mask == mask:
            v = (st & mask) >> lo
            rows.append(dict(bits=rng, pads=pads, value=v, vendor_function=funcs[v] if v < len(funcs) else None))
        else:
            rows.append(dict(bits=rng, pads=pads, value=None, vendor_function='not written (Boot ROM / reset value)'))
    return dict(register='0xb01b0048', clear=P.h32(clr), set=P.h32(st), fields=rows,
                order='board_mfp_init runs before adfu_check, so these values are in place during the loopback test',
                note='Field-to-function mapping from the vendor ATM7059 pinctrl data used by the RG35XX vendor kernel; '
                     'not verified on silicon.')


# --------------------------------------------------------------------------- evidence

FINDINGS = ['BOOT-025', 'BOOT-026', 'BOOT-027', 'GPIO-003', 'GPIO-004']


def analyse(path, release, verify=True):
    loader, ident = P.load_image(path, verify=verify)
    code = P.Code(loader)
    return dict(path=path, release=release, identity=ident, loader=loader, code=code, funcs=P.call_graph(code))


def evidence(docs, reference, src_dir):
    ref = docs[reference]
    k = decoded_constants(ref['code'])
    regions = {r: region_hashes(d['code']) for r, d in docs.items()}
    anchors = {r: verify_anchors(d['code']) for r, d in docs.items()}
    scen = [run_scenario(ref, k, *s) for s in SCENARIOS]
    # one sanity scenario per other release (regions are identical; the full matrix is not repeated)
    spot = {}
    for r, d in docs.items():
        if r == reference:
            continue
        kk = decoded_constants(d['code'])
        a = run_scenario(d, kk, *SCENARIOS[[s[0] for s in SCENARIOS].index('input-loopback')])
        b = run_scenario(d, kk, *SCENARIOS[[s[0] for s in SCENARIOS].index('input-low')])
        spot[r] = dict(loopback=a['firmware']['outcome'], low=b['firmware']['outcome'],
                       agree=a['comparison']['agree'] and b['comparison']['agree'])
    first = next(iter(regions.values()))
    doc = dict(
        format_version=1, tool=f'adfu_analysis.py v{TOOL_VERSION}', reference_release=reference, findings=FINDINGS,
        tool_versions=P.tool_versions(), releases={r: d['identity'] for r, d in docs.items()},
        regions=dict(reference=regions[reference], identical_across_releases={
            name: len({regions[r][name]['sha256'] for r in regions}) == 1 for name in first}),
        anchors=dict(rows=anchors[reference], all_match_in_every_release=all(a['matches'] for v in anchors.values()
                                                                             for a in v)),
        decoded_constants={k2: (P.h32(v) if k2 in ('pattern', 'compare', 'pull_register', 'outen', 'inen', 'dat')
                                else v) for k2, v in k.items()},
        pseudocode=PSEUDOCODE,
        control_flow=control_flow(),
        pmic_rules=PMIC_RULES,
        gpio_registers=gpio_registers(),
        board=dict(sources=source_evidence(src_dir), dtbs={r: dtb_survey(d['path']) for r, d in docs.items()},
                   board_mfp_init_sd0_fields=board_mfp_decode(ref['code']), interpretation=BOARD_INTERPRETATION),
        model=dict(module='tools/gpio_model.py', assumptions=GpioModel.assumptions(),
                   harness_rules={'timer': P.SYNTHETIC_RULES['timer'], 'pmic': P.SYNTHETIC_RULES['pmic'],
                                  'pre-state': 'I2C bus 1 pre-selected (0xb4070864 = 1, 0xb406ba10 = 1) as pmu_init '
                                               'leaves it', 'printf': 'stubbed, text captured'}),
        scenarios=scen,
        scenario_summary=dict(total=len(scen), agree=sum(s['comparison']['agree'] for s in scen),
                              adfu=[s['name'] for s in scen if s['firmware']['outcome'].startswith('ADFU')],
                              errors=[s['name'] for s in scen if s['firmware']['outcome'].startswith('emulator')]),
        other_releases_spot_check=spot,
        stalled_timer=stalled_timer(ref),
        full_path=[full_path(ref, 'main code2 C10 low', 2, ('const', 0)),
                   full_path(ref, 'main code2 ideal loopback', 2, ('follow', C11)),
                   full_path(ref, 'main code0 ideal loopback', 0, ('follow', C11))],
        dram_stage=dram_stage(ref),
        reentry=reentry_boundary(ref),
        persistent_state=PERSISTENT,
        downstream=dict(static=downstream_static(ref), later_stage_literals=later_stage_literals(ref),
                        linux_dt='All five shipped DTBs give mmc@b0230000 (SD0, TF2) a default pin state that muxes '
                                 'mfp2_19_17/16_14/13_11/8_7/6_5 to sd0 and sets pull <2> on P_SD0_D0..D3/CMD, so when '
                                 'the SD0 host binds, Linux reprograms the pads the test changed (value semantics of '
                                 '<2> in the vendor driver not pinned).',
                        classification=DOWNSTREAM_CLASSES),
        unknowns=UNKNOWNS)
    return doc


def control_flow():
    return dict(mermaid='''flowchart TD
  E["0xb4069254 entry, r7 = arg"] --> R["0xb4069268 pmic_read(0x35) & 0xffff<br/>printf pmu_status"]
  R -->|"bit 1 set (0xb4069280)"| W["0xb4069288 pmic_write(0x35, s & ~3)"] --> A
  R -->|"bit 1 clear"| G1{"0xb4069298 arg == 0?"}
  G1 -->|yes| RET["pop pc: return"]
  G1 -->|no| G2{"0xb40692a0 boot code == 0?"}
  G2 -->|yes| RET
  G2 -->|no| S["0xb40692c0 PULLCTL1 &= ~bit17; save CINEN/COUTEN;<br/>C10 in, C11 out"]
  S --> L["loop i = 0..31 (0xb4069330..0xb4069388):<br/>CDAT &= ~b11; CDAT |= bit_i<<11; delay_ms(1); rx |= C10<<i"]
  L --> X["0xb4069390 restore CINEN, COUTEN"] --> C{"0xb40693a8 rx == 0x55aa55aa?"}
  C -->|no| RET
  C -->|yes| A["0xb40693b0 printf ADFU; tail-call 0xb40691a4"]''',
                exits=['return (PMIC bit 1 clear and arg 0)', 'return (boot code 0)', 'return (loopback mismatch)',
                       'tail call 0xb40691a4 (PMIC bit 1 or loopback match)'],
                calls=['0xb40697f4 pmic_read_t2', '0xb4066854 printf', '0xb40697f8 pmic_write_t2', '0xb40664f0 '
                       'get_boot_code', '0xb406919c read32', '0xb4069194 write32', '0xb4069434 delay_ms (32x)',
                       '0xb40691a4 (tail)'],
                register_allocation=dict(r4='status & 2, then loop counter i (0 on the test path)', r5='status, then '
                                         'received word', r6='status register number, then drive shift register',
                                         r7='argument, then saved COUTEN', r8='saved CINEN', ip='compare literal'),
                dependencies=['timer 0 running (delay_ms -> delay_us polls 0xb0168010, set up by timer_init)',
                              'PMIC/I2C bus selected by pmu_init (pmic_read re-selects bus [0xb4070864])',
                              'boot-code word 0xb4064c00 (block 0)', 'UART for printf (uart_init)'])


PMIC_RULES = dict(
    always_read='Register 0x35 is read and printed on every call, before the argument and boot-code guards.',
    examined_bits='bit 1 only (ands r4, r5, #2).',
    write_back='status & ~3 written back (bits 0 and 1 cleared, bits 15:2 kept) through pmic_write; its return '
               'value is ignored; then ADFU. The GPIO registers are not touched on this path.',
    precedence='PMIC bit 1 > argument == 0 > boot code == 0 > loopback result.',
    read_failure='pmic_read returns -1 on an I2C error with no retry (0xb4069610); & 0xffff gives 0xffff, bit 1 is '
                 'set, so a failed read of reg 0x35 enters ADFU and writes back 0xfffc.',
    i2c_bound='The I2C transfer (0xb406a994) polls at most 501 x delay_ms(1) before failing (not exercised here: the '
              'transaction layer is a register file).',
    register_meaning='Not established. The loader prints it as "pmu_status" and treats bit 1 as an ADFU request. '
                     'No pinned ATC2603C source or document was available offline to name reg 0x35; no '
                     'write-one-to-clear or other semantics are assumed. The register file only stores the write.')


def gpio_registers():
    return [
        dict(address='0xb01b0018', name='GPIO_COUTEN', bank='C', bits='10 cleared, 11 set during the test; restored',
             width=32, naming='vendor header regs_map-atm7039.h (pinned)', semantics='output enable per bit (name; '
             'behaviour not verified)', confidence='inferred'),
        dict(address='0xb01b001c', name='GPIO_CINEN', bank='C', bits='10 set, 11 cleared during the test; restored',
             width=32, naming='vendor header', semantics='input enable per bit (name)', confidence='inferred'),
        dict(address='0xb01b0020', name='GPIO_CDAT', bank='C', bits='11 driven (two writes per iteration), 10 sampled',
             width=32, naming='vendor header',
             semantics='Whether a read returns the output latch, the pad level or a mix is NOT established; the model '
                       'offers "mixed" and "latch". Every write is a read-modify-write of the whole word, so under '
                       '"mixed" the latch bits of other input pins (and C10) are rewritten with their sampled levels.',
             confidence='unknown read semantics'),
        dict(address='0xb01b0064', name='PAD_PULLCTL1', bank='pads', bits='17 cleared, never restored', width=32,
             naming='vendor header', semantics='Vendor ATM7059 pinctrl data: bit 17 is the P_SD0_D0 (= GPIOC10) pull '
             'field, value 1 = pull-up, no pull-down; so clearing it most likely removes the pull-up from the sampled '
             'input. Electrical effect not verified.', confidence='inferred (pinned vendor source)'),
    ]


BOARD_INTERPRETATION = [
    dict(claim='GPIO C10/C11 are the SD0 DAT0/DAT1 pads (P_SD0_D0/P_SD0_D1).', basis='pinned vendor pinctrl data',
         confidence='strongly-supported for the pad identity; ball and connector wiring not seen'),
    dict(claim='SD0 is the TF2 slot on the original RG35XX.', basis='PR #8 (BOOT-023, STOR-003; DT sd_card on '
         'b0230000)', confidence='inferred'),
    dict(claim='The loopback therefore tests DAT1 -> DAT0 of the TF2 card slot while the unit boots from SD2.',
         basis='the two facts above', confidence='inferred'),
    dict(claim='No shipped DTB uses pins 74/75 as plain GPIOs (buttons, card detect, power); they appear only as '
         'SD0 data (mmc0_default) and as the optional UART5 pair (serial5_default, mmc_share_uart).',
         basis='all five shipped kernel.dtb files', confidence='verified for the DTBs'),
    dict(claim='board_mfp_init (ini+0x0d = 1) muxes SD0_D0, D2, D3, CMD and CLK to the vendor JTAG function before the '
         'test; D1 is left as the Boot ROM/reset left it.', basis='firmware table 0xb406b4c8 + vendor function lists',
         confidence='inferred (mux numbering from vendor source)'),
    dict(claim='Purpose: a factory/service fixture in the TF2 slot that connects DAT1 to DAT0 (and drives no pull) '
         'would make an SD2-booting unit enter ADFU. This fits the evidence but is a hypothesis; no Actions '
         'document, fixture description or board schematic was available.', basis='inference',
         confidence='speculative'),
    dict(claim='Contradictory or alternative readings: the vendor DTS comment lists the same pads for UART2/UART5 '
         'debug use; a UART adapter in TF2 is another plausible intended partner. Whether GPIO enables override the '
         'JTAG mux on this pad is unknown.', basis='vendor DTS, mux table', confidence='unknown'),
]

PERSISTENT = dict(
    method='firmware execution (scenarios init-*) cross-checked with the reference model',
    registers=[
        dict(register='GPIO_COUTEN 0xb01b0018', temporary='bit 10 cleared, bit 11 set', restore='write of the value '
             'read at 0xb40692d8, before any change', final='= initial, every bit, every initial value tested',
             conditional=False),
        dict(register='GPIO_CINEN 0xb01b001c', temporary='bit 10 set, bit 11 cleared', restore='write of the value '
             'read at 0xb40692cc', final='= initial', conditional=False),
        dict(register='PAD_PULLCTL1 0xb01b0064', temporary='-', restore='none', final='initial & ~(1 << 17); other '
             'bits as read back', conditional='changes only if bit 17 was set'),
        dict(register='GPIO_CDAT 0xb01b0020', temporary='64 writes: per iteration bit 11 cleared, then set to the pattern '
             'bit; every write is a whole-word read-modify-write', restore='none',
             final='bit 11 = last pattern bit = 0. Under "latch" read semantics every other bit is unchanged. Under '
             '"mixed" read semantics the latch bit of every non-output pin is rewritten with the level read: bit 10 '
             '= the C10 level at the second read of the last iteration (just after bit 11 was cleared), other input '
             'pins = their input level, pins with neither enable = the undriven value (scenarios init-mixed-*, '
             'init-unrelated-bits-undriven-high)', conditional='bit 11 changes only if it was 1; the rest depends on '
             'the unknown read semantics and on the initial direction registers'),
    ],
    pmic='Normal return writes no PMIC register; the PMIC path writes 0x35 := status & ~3 and does not return.',
    mux='The test does not write any MFP register.')

DOWNSTREAM_CLASSES = dict(
    demonstrated=['None in the loader: after adfu_check returns, no executed access (main path to 0xb40690b8, and the '
                  'PR #6 DRAM caller through DRAM init, reference scenario) reads or writes the GPIO/pad window.'],
    no_dependency_found=['Constant-address scan of all code reachable from main and of the DRAM routine subtree: no '
                         'access to PAD_PULLCTL1, GPIO_C* or MFP_CTL2 outside adfu_check/board_mfp_init (unresolved '
                         'computed accesses counted, not resolved).'],
    possible=['app.bin 0x9430 rewrites SD0 pulls including bit 17 (caller not found).',
              'U-Boot initialises SD0 as mmc 0 on the code-2 path (BOOT-023) and carries MFP_CTL2 literals; whether it '
              'rewrites PULLCTL1 is not traced.',
              'Linux mmc0_default pin state reprograms SD0 mux and pulls.',
              'A floating, un-pulled DAT0 on an empty TF2 slot until reconfigured (electrical, unknown).'],
    unknown=['Physical effect of the changed pull and latch on the TF2 slot or a card in it.',
             'Whether the pads were in GPIO, JTAG or SD0 function electrically during the test.'])

UNKNOWNS = [
    'GPIO_CDAT read semantics (latch vs pad level) on ATM7039S.',
    'Whether GPIO output/input enables take effect while MFP_CTL2 selects JTAG (D0) or the ROM-left function (D1).',
    'Electrical meaning of PAD_PULLCTL1 bit 17 on silicon (vendor data says pull-up enable).',
    'PCB wiring of the TF2 slot DAT0/DAT1 (only DT/pinctrl naming was seen; no schematic).',
    'Meaning of PMIC register 0x35 and its bit 1 on the fitted PMIC.',
    'Real duration of the 32 delays (timer clock not measured; I2C/printf and MMIO latency add to it).',
    'What the ROM code at 0xffff5200 (copied to SRAM) does - unavailable.',
]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('evidence')
    e.add_argument('output', type=Path)
    e.add_argument('--image', action='append', required=True)
    e.add_argument('--sources', required=True, help='directory holding the pinned sources (tools/fetch_sources.py)')
    e.add_argument('--reference', default='koriki-v1.0')
    r = sub.add_parser('run')
    r.add_argument('image')
    r.add_argument('--boot-code', type=lambda x: int(x, 0), default=2)
    r.add_argument('--arg', type=lambda x: int(x, 0), default=1)
    r.add_argument('--pmic', type=lambda x: int(x, 0), default=0)
    r.add_argument('--input', default='const0', help='const0|const1|follow|invert|delay|prbs:SEED')
    a = p.parse_args()
    if a.cmd == 'evidence':
        docs = {}
        for spec in a.image:
            rel, path = spec.split('=', 1)
            docs[rel] = analyse(path, rel)
        out = evidence(docs, a.reference, a.sources)
        a.output.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
        print(f'wrote {a.output}')
    else:
        doc = analyse(a.image, 'cli', verify=False)
        rules = {'const0': ('const', 0), 'const1': ('const', 1), 'follow': ('follow', C11),
                 'invert': ('invert', C11), 'delay': ('delay', C11, 1500, 0)}
        rule = ('prbs', int(a.input.split(':')[1], 0)) if a.input.startswith('prbs:') else rules[a.input]
        s = run_scenario(doc, decoded_constants(doc['code']), 'cli', a.boot_code, a.arg, a.pmic, rule, {}, {})
        print(json.dumps(s, indent=1))


if __name__ == '__main__':
    main()
