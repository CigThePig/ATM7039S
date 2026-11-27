"""Read first 4 MiB of an explicitly identified spare card; never write.
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
https://learn.microsoft.com/en-us/powershell/module/storage/get-partition
https://learn.microsoft.com/en-us/powershell/module/storage/get-disk
"""
import ctypes
import json
import os
import re
import stat
import subprocess

HEAD_SIZE = 4 * 1024 * 1024
BOOT_OFFSET = 8 * 1024 * 1024
BOOT_SIZE = 3 * 1024 * 1024 * 1024


def windows_disk_number(letter):
    if not re.fullmatch(r'[A-Za-z]:?', letter):
        raise ValueError('supply only the spare boot partition letter, e.g. E')
    letter = letter[0].upper()
    command = (
        "$ErrorActionPreference='Stop'; "
        f"$p=Get-Partition -DriveLetter '{letter}'; "
        "$d=Get-Disk -Number $p.DiskNumber; "
        "[pscustomobject]@{Number=$d.Number;Bus=[string]$d.BusType;"
        "IsBoot=$d.IsBoot;IsSystem=$d.IsSystem;Offset=$p.Offset;"
        "PartitionSize=$p.Size;DiskSize=$d.Size}|ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
            capture_output=True, check=True, timeout=30, text=True)
        info = json.loads(result.stdout)
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        raise ValueError('could not identify spare card using Windows Storage cmdlets') from e
    if not isinstance(info, dict):
        raise ValueError('drive letter did not resolve to exactly one disk')
    number = info.get('Number')
    if (type(number) is not int or number < 0 or
            info.get('IsBoot') is not False or info.get('IsSystem') is not False or
            info.get('Bus') not in ('USB', 'SD', 'MMC') or
            info.get('Offset') != BOOT_OFFSET or info.get('PartitionSize') != BOOT_SIZE or
            type(info.get('DiskSize')) is not int or info['DiskSize'] < 4303355904):
        raise ValueError('not a non-system USB/SD/MMC disk with expected Koriki boot partition')
    return number


def read_windows_card(letter):
    if os.name != 'nt':
        raise ValueError('--windows-boot-letter is only for Windows')
    return read_windows_disk(windows_disk_number(letter))


def read_windows_disk(number):
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    read = kernel.ReadFile
    read.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                     ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    read.restype = wintypes.BOOL
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    # GENERIC_READ, FILE_SHARE_READ|FILE_SHARE_WRITE, OPEN_EXISTING.
    handle = create(r'\\.\PhysicalDrive' + str(number), 0x80000000, 3, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError(f'cannot open spare card read-only (Windows error {ctypes.get_last_error()}); use an administrator terminal')
    try:
        # Align the buffer for raw devices that impose sector alignment.
        alignment = 65536
        buf = ctypes.create_string_buffer(HEAD_SIZE + alignment)
        address = (ctypes.addressof(buf) + alignment - 1) & ~(alignment - 1)
        count = wintypes.DWORD()
        if not read(handle, ctypes.c_void_p(address), HEAD_SIZE, ctypes.byref(count), None):
            raise OSError(f'raw card read failed (Windows error {ctypes.get_last_error()})')
        if count.value != HEAD_SIZE:
            raise ValueError('short raw card read')
        return ctypes.string_at(address, HEAD_SIZE)
    finally:
        close(handle)


def read_posix_card(path):
    if os.name != 'posix':
        raise ValueError('--card-device is only for Linux/macOS')
    if not re.fullmatch(r'/dev/(?:sd[a-z]+|mmcblk[0-9]+|r?disk[0-9]+)', path):
        raise ValueError('supply a whole spare-card device, not a partition')
    with open(path, 'rb', buffering=0) as f:
        mode = os.fstat(f.fileno()).st_mode
        if not (stat.S_ISBLK(mode) or stat.S_ISCHR(mode)):
            raise ValueError('not a block or character device')
        data = f.read(HEAD_SIZE)
    if len(data) != HEAD_SIZE:
        raise ValueError('short raw card read')
    return data
