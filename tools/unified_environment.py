"""Offline model for the commands in the pinned U-Boot environment."""
from dataclasses import dataclass
import re
import shlex
import struct
import zlib

import boot_chain as boot
from unified_loader import BoundaryError


@dataclass(frozen=True)
class FatLoad:
    slot: int
    device: int
    partition: int
    filename: str
    address: int
    data: bytes

    def identity(self):
        return dict(slot=self.slot, device=self.device, partition=self.partition, filename=self.filename,
                    address=hex(self.address), size=len(self.data), sha256=boot.sha(self.data))


def persistent_environment(ub, disk, registrations, backing_slot):
    layout = boot.env_storage(ub)
    env = boot.default_env(ub)['variables']
    source = 'compiled defaults'
    device = next((row for row in registrations if row['device_number'] == layout['mmc_device']), None)
    attempts = []
    if device is None or device['mmc_init'] != 'ok' or device['slot'] != backing_slot:
        return env, source, dict(layout=layout, device=device, attempts=attempts,
                                 status='no readable persistent environment medium')
    size = int(layout['size'], 16)
    for address in layout['offsets']:
        raw = disk.sectors(int(address, 16) // boot.SECTOR, size // boot.SECTOR)
        valid = len(raw) == size and zlib.crc32(raw[5:]) == struct.unpack_from('<I', raw)[0]
        attempts.append(dict(offset=address, size=len(raw), sha256=boot.sha(raw), crc_valid=valid,
                             flags=raw[4] if len(raw) >= 5 else None))
    if any(row['crc_valid'] for row in attempts):
        raise BoundaryError('unmodelled-dependency', 'valid persistent environment needs redundancy selection model')
    return env, source, dict(layout=layout, device=device, attempts=attempts, status='both copies invalid')


def parse_script(script):
    """Parse simple commands and the exact if/then/fi form used in shipped scripts."""
    try:
        lexer = shlex.shlex(script.replace(r'\"', '"'), posix=True, punctuation_chars=';')
        lexer.whitespace_split = True
        lexer.commenters = ''
        statements = [[]]
        for token in lexer:
            if token and all(c == ';' for c in token):
                statements.extend([] for _ in token)
            else:
                statements[-1].append(token)
    except ValueError as error:
        raise BoundaryError('environment-execution-failure', str(error)) from error

    def parse(index, stops):
        nodes = []
        while index < len(statements):
            tokens = statements[index]
            index += 1
            if not tokens:
                continue
            op, *args = tokens
            if op in stops:
                return nodes, index, args
            if op == 'if':
                if not args or index >= len(statements) or statements[index][:1] != ['then']:
                    raise BoundaryError('environment-execution-failure', 'expected if condition; then')
                statements[index] = statements[index][1:]
                body, index, trailing = parse(index, {'fi'})
                if trailing:
                    raise BoundaryError('environment-execution-failure', 'tokens after fi')
                nodes.append((args, body))
            elif op in ('then', 'else', 'fi'):
                raise BoundaryError('environment-execution-failure', f'unexpected {op}')
            else:
                nodes.append((tokens, None))
        if stops:
            raise BoundaryError('environment-execution-failure', 'unterminated conditional')
        return nodes, index, []

    return parse(0, set())[0]


class Environment:
    def __init__(self, values, source, disk, registrations, backing_slot, ram_size, *, fault=None):
        self.values = dict(values)
        self.origins = dict.fromkeys(values, source)
        self.disk = disk
        self.registrations = {row['device_number']: row for row in registrations}
        self.backing_slot, self.ram_size, self.fault = backing_slot, ram_size, fault
        self.loads, self.load_log, self.transitions, self.commands = {}, [], [], []
        self.partition = None
        self.bootm = None
        self.missing_required = False

    def change(self, name, value, source):
        self.transitions.append(dict(name=name, before=self.values.get(name), after=value, source=source))
        if value is None:
            self.values.pop(name, None)
            self.origins.pop(name, None)
        else:
            self.values[name] = value
            self.origins[name] = source

    def run(self, name='bootcmd', stack=()):
        if len(stack) >= 12 or name in stack:
            raise BoundaryError('environment-execution-failure', 'nested run cycle or depth limit')
        script = self.values.get(name)
        if script is None:
            raise BoundaryError('environment-execution-failure', f'missing script variable {name}')
        return self._nodes(parse_script(script), (*stack, name))

    def _nodes(self, nodes, stack):
        result = True
        for tokens, body in nodes:
            if self.bootm is not None:
                raise BoundaryError('environment-execution-failure', 'commands after bootm')
            result = self._command(tokens, stack)
            if body is not None:
                result = self._nodes(body, stack) if result else True
        return result

    def _command(self, tokens, stack):
        if len(self.commands) >= 128:
            raise BoundaryError('environment-execution-failure', 'environment command budget exceeded')
        expanded = [re.sub(r'\$\{([a-zA-Z_][a-zA-Z_0-9]*)\}', lambda m: self.values.get(m.group(1), ''), t)
                    for t in tokens]
        op, *args = expanded
        source = 'run ' + '/'.join(stack)
        self.commands.append(dict(source=source, arguments=expanded))
        if op == 'run' and len(args) == 1:
            return self.run(args[0], stack)
        if op == 'echo':
            return True
        if op == 'test' and len(args) == 2 and args[0] == '-n':
            return bool(args[1])
        if op == 'setenv' and args and re.fullmatch(r'[\w.-]+', args[0]):
            self.change(args[0], ' '.join(args[1:]) if len(args) > 1 else None, source)
            return True
        if op == 'fatload' and len(args) == 4:
            loaded = self._fatload(*args)
            if loaded is None:
                if stack[-1] in ('loadkernel', 'loadramdisk', 'loadfdt'):
                    self.missing_required = True
                return False
            self.change('filesize', f'{len(loaded.data):x}', source)
            self.change('fileaddr', f'{loaded.address:x}', source)
            return True
        if op == 'env' and len(args) == 4 and args[:2] == ['import', '-t']:
            address, size = self._hex(args[2]), self._hex(args[3])
            loaded = self.loads.get(address)
            if not loaded or size != len(loaded.data):
                raise BoundaryError('environment-execution-failure', 'env import has no exact loaded source')
            for key, value in boot.parse_uenv(loaded.data.decode('latin1')).items():
                self.change(key, value, loaded.filename)
            return True
        if op == 'bootm' and len(args) == 3:
            if self.missing_required:
                raise BoundaryError('boot-file-loading-failure', 'required FAT read failed before bootm')
            addresses = tuple(self._hex(a) for a in args)
            if len(set(addresses)) != 3 or any(a not in self.loads for a in addresses):
                raise BoundaryError('boot-file-loading-failure', 'bootm requests missing or duplicate image buffers')
            self.bootm = tuple(self.loads[a] for a in addresses)
            return True
        raise BoundaryError('environment-execution-failure', f'unsupported command or arguments: {op}')

    @staticmethod
    def _hex(value):
        if not re.fullmatch(r'(?:0x)?[0-9a-fA-F]+', value):
            raise BoundaryError('environment-execution-failure', f'invalid hexadecimal argument: {value}')
        return int(value, 16)

    def _fatload(self, devtype, devpart, addr, name):
        match = re.fullmatch(r'(\d+):(\d+)', devpart)
        if devtype != 'mmc' or not match or not re.fullmatch(r'[\w.-]+', name):
            raise BoundaryError('environment-execution-failure', 'unsupported FAT load selector')
        number, partition = map(int, match.groups())
        controller = self.registrations.get(number)
        if controller is None or controller['mmc_init'] != 'ok':
            raise BoundaryError('mmc-initialization-failure', f'mmc {number} did not initialize')
        if partition != 1 or controller['slot'] != self.backing_slot:
            raise BoundaryError('unmodelled-dependency', f'no pinned image for mmc {devpart} on this controller')
        if self.partition is None:
            self.partition = boot.gpt_partition1(self.disk.f)
            p = self.partition
            if not 0 < p['start_lba'] < p['start_lba'] + p['sectors'] <= self.disk.size // boot.SECTOR:
                raise BoundaryError('boot-file-loading-failure', 'partition 1 is outside the image')
        addr = self._hex(addr)
        record = dict(device=number, slot=controller['slot'], partition=partition, requested=name, address=hex(addr))
        self.load_log.append(record)
        try:
            found = boot.fat_files(self.disk.f, self.partition, [name])[name]
        except (OSError, ValueError, struct.error) as error:
            raise BoundaryError('boot-file-loading-failure', f'failed FAT read for {name}') from error
        if found is None or (self.fault == 'missing-kernel' and name.lower() == 'uimage'):
            record['status'] = 'missing'
            return None
        real, data = found
        record['source_sha256'] = boot.sha(data)
        if self.fault == 'invalid-kernel' and name.lower() == 'uimage':
            data = bytes(4) + data[4:]
        if self.fault == 'corrupt-dtb' and name.lower() == 'kernel.dtb':
            data = data[:36] + b'\xff' * 4 + data[40:]
        if not 0 < len(data) < 64 << 20 or not 0 <= addr < addr + len(data) <= self.ram_size:
            raise BoundaryError('invalid-memory-layout', f'FAT destination outside RAM for {name}')
        # Buffers at the same address can be replaced. Any partial overwrite
        # invalidates the old complete-file view.
        for old_addr, old in list(self.loads.items()):
            if old_addr < addr + len(data) and addr < old_addr + len(old.data):
                del self.loads[old_addr]
        loaded = FatLoad(controller['slot'], number, partition, real, addr, data)
        self.loads[addr] = loaded
        record.update(loaded.identity(), status='ok')
        return loaded

    def evidence(self):
        origin_names = ('bootcmd', 'devif', 'devtype', 'devpart', 'bootargs', 'os_type', 'machid', 'fdt_high',
                        'initrd_high', 'kernel_addr_r', 'ramdisk_addr_r', 'fdt_addr_r')
        return dict(transitions=self.transitions, commands=self.commands, loads=self.load_log,
                    selected={k: dict(value=self.values[k], source=self.origins[k]) for k in origin_names
                              if k in self.values}, partition=self.partition)
