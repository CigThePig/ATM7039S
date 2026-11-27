"""Find the spare Koriki test card by disk identity and partition layout, never by drive letter.

Read-only. Collectors list disks with the operating system's own inventory (Windows Storage
cmdlets, Linux lsblk); identify() then applies fixed rules taken from the pinned image's
partition table (evidence/firmware/koriki-v1.0.json):

* the disk is not the boot or system disk and sits on a USB/SD/MMC bus (or is removable);
* partition 1 starts at 8 MiB, is 3 GiB, and its volume is labelled BATOCERA;
* partition 2 is the 512 MiB swap partition (Windows cannot read it: that is expected);
* partition 3 starts where the image puts it: still 512 MiB before the first boot, or grown
  to the end of the card and formatted as FAT with the label SHARE after it;
* the BATOCERA and SHARE volumes therefore always belong to the same physical disk.

More than one matching disk, or none, is reported and nothing is chosen. A volume Windows
cannot read is recorded on its own partition and never stops discovery of the others.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

BOOT_OFFSET = 8 * 1024 * 1024
BOOT_SIZE = 3 * 1024 ** 3
SWAP_OFFSET = 3229614080
SWAP_SIZE = 536870912
SHARE_OFFSET = 3766484992
SHARE_SIZE_PRISTINE = 536870912
IMAGE_SIZE = 4303355904
REMOVABLE_BUSES = {'USB', 'SD', 'MMC'}

PS_INVENTORY = r"""
$ErrorActionPreference = 'Stop'
$out = @()
foreach ($d in @(Get-Disk)) {
  $parts = @()
  foreach ($p in @(Get-Partition -DiskNumber $d.Number -ErrorAction SilentlyContinue)) {
    $v = $null
    try { $v = Get-Volume -Partition $p -ErrorAction Stop } catch { }
    $parts += [pscustomobject]@{
      Number = $p.PartitionNumber; Offset = $p.Offset; Size = $p.Size; MbrType = $p.MbrType
      DriveLetter = [string]$p.DriveLetter; Label = if ($v) { $v.FileSystemLabel } else { $null }
      FileSystem = if ($v) { $v.FileSystem } else { $null }; Health = if ($v) { [string]$v.HealthStatus } else { $null }
    }
  }
  $out += [pscustomobject]@{
    Number = $d.Number; Model = $d.FriendlyName; BusType = [string]$d.BusType; Size = $d.Size
    IsBoot = $d.IsBoot; IsSystem = $d.IsSystem; IsOffline = $d.IsOffline; PartitionStyle = [string]$d.PartitionStyle
    Signature = $d.Signature; Partitions = $parts
  }
}
ConvertTo-Json -InputObject $out -Depth 6 -Compress
"""


class DiscoveryError(RuntimeError):
    pass


def _probe_mount(path):
    """Can this mounted volume be listed? Returns (readable, error)."""
    try:
        os.listdir(path)
        return True, None
    except OSError as e:
        return False, f'{type(e).__name__}: {e.strerror or e}'


def normalize_windows(raw, probe=_probe_mount):
    """PowerShell inventory JSON -> list of disks in the lab's common shape."""
    if isinstance(raw, dict):
        raw = [raw]
    disks = []
    for d in raw or []:
        parts = d.get('Partitions') or []
        if isinstance(parts, dict):
            parts = [parts]
        out_parts = []
        for p in parts:
            letter = (p.get('DriveLetter') or '').strip().rstrip(':\x00')
            mount = f'{letter}:\\' if letter and letter.isalpha() else None
            readable, err = probe(mount) if mount else (None, None)
            out_parts.append(dict(number=p.get('Number'), offset=p.get('Offset'), size=p.get('Size'),
                                  type=p.get('MbrType'), label=p.get('Label') or None, fs=p.get('FileSystem') or None,
                                  mount=mount, readable=readable, error=err))
        disks.append(dict(id=f"windows-disk-{d.get('Number')}", number=d.get('Number'), model=d.get('Model') or '',
                          bus=(d.get('BusType') or '').upper(), size=d.get('Size'), removable=None,
                          is_boot=bool(d.get('IsBoot')), is_system=bool(d.get('IsSystem')),
                          offline=bool(d.get('IsOffline')), style=(d.get('PartitionStyle') or '').upper(),
                          signature=d.get('Signature'), partitions=out_parts))
    return disks


def normalize_lsblk(raw, probe=_probe_mount):
    """lsblk -J -b output -> list of disks."""
    disks = []
    for d in raw.get('blockdevices', []):
        if d.get('type') != 'disk':
            continue
        parts = []
        for c in d.get('children') or []:
            if c.get('type') != 'part':
                continue
            mps = [m for m in (c.get('mountpoints') or [c.get('mountpoint')]) if m]
            mount = mps[0] if mps else None
            readable, err = probe(mount) if mount else (None, None)
            parts.append(dict(number=int(c['partn']) if c.get('partn') else None, offset=int(c['start']) * 512 if c.get('start') is not None else None,
                              size=int(c['size']), type=c.get('parttype'), label=c.get('label'), fs=c.get('fstype'),
                              mount=mount, readable=readable, error=err))
        disks.append(dict(id=d.get('path') or '/dev/' + d['name'], number=None, path=d.get('path') or '/dev/' + d['name'],
                          model=(d.get('model') or '').strip(), bus=(d.get('tran') or '').upper(), size=int(d['size']),
                          removable=bool(d.get('rm')) or bool(d.get('hotplug')), is_boot=False,
                          is_system=any(p['mount'] in ('/', '/boot', '/boot/efi', '/usr', '/home') for p in parts),
                          offline=False, style=(d.get('pttype') or '').upper(), signature=None, partitions=parts))
    return disks


def collect(runner=subprocess.run):
    """Inventory of this computer's disks. Never needs administrator rights."""
    if os.name == 'nt':
        r = runner(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', PS_INVENTORY],
                   capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')
        if r.returncode:
            raise DiscoveryError('Windows did not list its disks: ' + (r.stderr or '').strip()[:300])
        return normalize_windows(json.loads(r.stdout or '[]'))
    r = runner(['lsblk', '-J', '-b', '-o', 'NAME,PATH,TYPE,SIZE,START,PARTN,TRAN,RM,HOTPLUG,MODEL,LABEL,FSTYPE,MOUNTPOINTS,PTTYPE,PARTTYPE'],
               capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise DiscoveryError('lsblk failed: ' + (r.stderr or '').strip()[:300])
    return normalize_lsblk(json.loads(r.stdout))


def _part(disk, n):
    return next((p for p in disk['partitions'] if p['number'] == n), None)


def classify(disk):
    """(kind, reasons, facts) for one disk. kind is 'card' or 'not-card'."""
    reasons, facts = [], {}
    if disk['is_boot'] or disk['is_system']:
        return 'not-card', ['this is the computer\'s own system disk'], facts
    if disk.get('offline'):
        reasons.append('Windows has this disk offline')
    removable = disk['bus'] in REMOVABLE_BUSES or disk.get('removable')
    if not removable:
        reasons.append(f"not on a USB/SD card reader bus (bus {disk['bus'] or 'unknown'})")
    if not disk.get('size') or disk['size'] < IMAGE_SIZE:
        reasons.append('smaller than the Koriki image')
    if disk.get('style') not in ('MBR', 'DOS', ''):
        reasons.append(f"partition table is {disk.get('style')}, the Koriki image uses MBR")
    p1, p2, p3 = _part(disk, 1), _part(disk, 2), _part(disk, 3)
    if not p1 or p1['offset'] != BOOT_OFFSET or p1['size'] != BOOT_SIZE:
        reasons.append('partition 1 is not the 3 GiB boot partition at 8 MiB')
    elif (p1['label'] or '').upper() != 'BATOCERA':
        if p1['label'] is None:
            facts['boot_label_unknown'] = True
        else:
            reasons.append(f"partition 1 is labelled {p1['label']!r}, not BATOCERA")
    if not p2 or p2['offset'] != SWAP_OFFSET or p2['size'] != SWAP_SIZE:
        reasons.append('partition 2 is not the 512 MiB swap partition')
    if not p3 or p3['offset'] != SHARE_OFFSET:
        reasons.append('partition 3 does not start where the Koriki image puts it')
    else:
        if p3['size'] == SHARE_SIZE_PRISTINE and (p3['label'] or '').upper() != 'SHARE':
            facts['stage'] = 'not-yet-booted'
        elif (p3['label'] or '').upper() == 'SHARE' and (p3['fs'] or 'FAT32').upper().startswith(('FAT', 'VFAT', 'EXFAT')):
            facts['stage'] = 'booted'
        elif p3['label'] is None and p3['size'] > SHARE_SIZE_PRISTINE:
            facts['stage'] = 'booted?'
        else:
            reasons.append('partition 3 is neither the unbooted 512 MiB partition nor a SHARE volume')
    if reasons:
        return 'not-card', reasons, facts
    facts['boot'] = p1
    facts['share'] = p3
    facts['swap'] = p2
    return 'card', [], facts


def identify(disks):
    """Exactly one Koriki test card, or a clear explanation. Never guesses."""
    cards, others = [], []
    for d in disks:
        kind, reasons, facts = classify(d)
        (cards if kind == 'card' else others).append(dict(disk=d, reasons=reasons, facts=facts))
    volumes = [dict(disk=d['id'], partition=p['number'], mount=p['mount'], label=p['label'], readable=p['readable'], error=p['error'])
               for d in disks for p in d['partitions'] if p['mount']]
    if len(cards) == 1:
        c = cards[0]
        boot, share = c['facts']['boot'], c['facts']['share']
        problems = []
        if not boot['mount']:
            problems.append('the BATOCERA partition has no drive letter')
        elif boot['readable'] is False:
            problems.append(f"the BATOCERA partition cannot be read ({boot['error']})")
        if c['facts'].get('stage', '').startswith('booted') and not share['mount']:
            problems.append('the SHARE partition has no drive letter')
        return dict(status='found' if not problems else 'found-needs-attention', card=c['disk'], stage=c['facts'].get('stage'),
                    boot_mount=boot['mount'], share_mount=share['mount'], problems=problems, others=others, volumes=volumes)
    if not cards:
        return dict(status='none', card=None, others=others, volumes=volumes,
                    problems=['no Koriki test card found: insert the spare card (only that card) and try again'])
    return dict(status='ambiguous', card=None, candidates=[c['disk'] for c in cards], others=others, volumes=volumes,
                problems=[f'{len(cards)} disks look like Koriki cards; remove every card except the spare test card'])


def fingerprint(disk, salt):
    """A stable, non-reversible identity for 'is this still the same card?' checks.

    Combines the disk size, the partition geometry and (after the first boot) the SHARE
    partition size, with a per-session salt so the stored value reveals nothing.
    """
    p3 = _part(disk, 3) or {}
    parts = [disk.get('size'), disk.get('model', '').strip()] + \
            [(p['number'], p['offset'], p['size']) for p in sorted(disk['partitions'], key=lambda p: p['number'] or 0)] + \
            [p3.get('size')]
    return hashlib.sha256((salt + json.dumps(parts, sort_keys=True, default=str)).encode()).hexdigest()


def public_view(result):
    """What may appear in logs and diagnostic bundles: no serials, signatures or labels beyond the expected ones."""
    def disk_view(d):
        return dict(id=d['id'], model=d.get('model'), bus=d.get('bus'), size=d.get('size'), is_system=d.get('is_system') or d.get('is_boot'),
                    partitions=[dict(number=p['number'], offset=p['offset'], size=p['size'], fs=p['fs'],
                                     label=p['label'] if (p['label'] or '').upper() in ('BATOCERA', 'SHARE') else ('<other>' if p['label'] else None),
                                     has_letter=bool(p['mount']), readable=p['readable']) for p in d['partitions']])
    out = dict(status=result['status'], stage=result.get('stage'), problems=result.get('problems', []))
    if result.get('card'):
        out['card'] = disk_view(result['card'])
    out['rejected'] = [dict(disk=disk_view(o['disk']), reasons=o['reasons']) for o in result.get('others', [])]
    return out


def locate_boot_file(result, *names):
    """Path to a file on the card's boot volume, re-resolved at the moment of use."""
    if result.get('status') not in ('found', 'found-needs-attention') or not result.get('boot_mount'):
        raise DiscoveryError('the test card is not available right now')
    return Path(result['boot_mount']).joinpath(*names)
