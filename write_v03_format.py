#!/usr/bin/env python3
"""Write the NvStrapsReBar EFI variable in the legacy v0.2/v0.3 layout
(2-byte header, no CRC field), for boards flashed with a DXE driver older
than v0.4 that cannot parse the format ReBarState writes today.

This is the rescue path for when the tool itself cannot save. Use ReBarState
first; reach for this only if that fails.

Every NVIDIA GPU and its upstream bridge is read from sysfs, so any number of
cards works. Existing entries are merged rather than replaced: dual-socket
boards renumber PCI buses between boots, and the entries kept for the other
layout are what let ReBAR survive that.

Previews by default. Pass --write to actually touch the variable.
"""
import argparse
import glob
import os
import struct
import subprocess
import sys
import time

VAR = ("/sys/firmware/efi/efivars/"
       "NvStrapsReBar-e3ee4a27-e2a2-4435-bba3-184ccad935a8")
GPU_STRIDE = 24          # <HHHBB (8) + <QQ (16)
BR_STRIDE = 7            # <HHBBB
NVIDIA = 0x10DE
HEADER = 4               # barSize, flags, nGPUSelector, nGPUConfig


def _hex(path):
    with open(path) as f:
        return int(f.read().strip(), 16)


def _dec(path):
    with open(path) as f:
        return int(f.read().strip())


def _devfn(text):
    """'03.0' -> (3 << 3) | 0, the packed device/function byte."""
    dev, fn = text.split(".")
    return (int(dev, 16) << 3) | int(fn)


def detect():
    """Read every NVIDIA display device and its upstream bridge from sysfs."""
    gpus, bridges = [], []
    for path in sorted(glob.glob("/sys/bus/pci/devices/*")):
        try:
            if _hex(f"{path}/class") >> 8 != 0x0300:
                continue
            if _hex(f"{path}/vendor") != NVIDIA:
                continue
            _dom, bus, devfn = os.path.basename(path).split(":")
            with open(f"{path}/resource") as fh:      # first line is BAR0
                base, top, _flags = (int(x, 16) for x in fh.readline().split())
            gpus.append((_hex(f"{path}/device"),
                         _hex(f"{path}/subsystem_vendor"),
                         _hex(f"{path}/subsystem_device"),
                         int(bus, 16), _devfn(devfn), base, top))

            # the GPU's parent in sysfs is the bridge it hangs off
            br = os.path.basename(os.path.dirname(os.path.realpath(path)))
            if br.count(":") != 2:
                print(f"warning: {os.path.basename(path)} has no parent bridge "
                      f"-- its BAR cannot be enlarged", file=sys.stderr)
                continue
            bpath = f"/sys/bus/pci/devices/{br}"
            _bdom, bbus, bdevfn = br.split(":")
            bridges.append((_hex(f"{bpath}/vendor"), _hex(f"{bpath}/device"),
                            int(bbus, 16), _devfn(bdevfn),
                            _dec(f"{bpath}/secondary_bus_number")))
        except (OSError, ValueError) as e:
            print(f"warning: skipping {path}: {e}", file=sys.stderr)
    return gpus, bridges


def parse(data):
    """(barSize, flags, nGPUSelector, [gpu...], [bridge...]) or None if the
    stored value is not in this layout."""
    try:
        bar, flags, nsel, ngpu = data[0], data[1], data[2], data[3]
        gpus = []
        for i in range(ngpu):
            at = HEADER + i * GPU_STRIDE
            gpus.append(struct.unpack_from("<HHHBB", data, at)
                        + struct.unpack_from("<QQ", data, at + 8))
        off = HEADER + ngpu * GPU_STRIDE
        nbr = data[off]
        brs = [struct.unpack_from("<HHBBB", data, off + 1 + i * BR_STRIDE)
               for i in range(nbr)]
        if off + 1 + nbr * BR_STRIDE != len(data):
            return None                      # trailing bytes: not this layout
        return bar, flags, nsel, gpus, brs
    except (IndexError, struct.error):
        return None


def build(bar, flags, nsel, gpus, brs):
    out = bytes([bar, flags, nsel, len(gpus)])
    for g in gpus:
        out += struct.pack("<HHHBBQQ", *g)
    out += bytes([len(brs)])
    for b in brs:
        out += struct.pack("<HHBBB", *b)
    return out


def merge(old, new):
    """Keep every old entry, append the ones detection found that are missing.
    Order matters to nobody here, but stability keeps diffs readable."""
    out = list(old)
    for item in new:
        if item not in out:
            out.append(item)
    return out


def show(gpus, brs):
    for i, (d, sv, sd, bus, devfn, base, top) in enumerate(gpus, 1):
        print(f"  gpu{i}: {d:04X} subsys {sv:04X}:{sd:04X} "
              f"at {bus:02X}:{devfn >> 3:02X}.{devfn & 7} "
              f"BAR0 {base:#010x}-{top:#010x}")
    for i, (v, d, bus, devfn, sec) in enumerate(brs, 1):
        print(f"  br{i} : {v:04X}:{d:04X} "
              f"at {bus:02X}:{devfn >> 3:02X}.{devfn & 7} -> bus {sec:02X}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="actually write (default is to preview only)")
    ap.add_argument("--bar-size", type=int, default=32, metavar="N",
                    help="nPciBarSize: 32 = any size the card supports "
                         "(default). 0 means straps only, which the v0.3 DXE "
                         "does NOT resize the BAR for -- it leaves you at 256MB")
    ap.add_argument("--replace", action="store_true",
                    help="drop stored entries instead of merging into them")
    args = ap.parse_args()

    if not os.path.exists(VAR):
        sys.exit(f"{VAR} not found -- is the NvStrapsReBar DXE driver flashed?")

    with open(VAR, "rb") as f:
        raw = f.read()
    attrs, data = raw[:4], raw[4:]

    stored = parse(data)
    if stored is None:
        print(f"stored value ({len(data)} bytes) is not in the v0.2/v0.3 "
              f"layout -- starting fresh")
        old_gpus, old_brs, flags, nsel = [], [], 0x0A, 0
    else:
        bar, flags, nsel, old_gpus, old_brs = stored
        print(f"stored: barSize={bar} flags={flags:#04x} "
              f"{len(old_gpus)} GPU / {len(old_brs)} bridge entries")
        if bar != args.bar_size:
            print(f"note: stored barSize {bar} -> writing {args.bar_size}")

    new_gpus, new_brs = detect()
    if not new_gpus:
        sys.exit("no NVIDIA GPU found in sysfs -- refusing to write")
    print(f"detected {len(new_gpus)} GPU / {len(new_brs)} bridge:")
    show(new_gpus, new_brs)

    if args.replace:
        gpus, brs = new_gpus, new_brs
    else:
        gpus, brs = merge(old_gpus, new_gpus), merge(old_brs, new_brs)
    out = build(args.bar_size, flags, nsel, gpus, brs)

    print(f"\nwould write {len(out)} bytes "
          f"({len(gpus)} GPU / {len(brs)} bridge entries):")
    show(gpus, brs)

    if not args.write:
        print("\npreview only -- pass --write to apply, then reboot")
        return 0

    if os.geteuid() != 0:
        sys.exit("writing the EFI variable needs root")

    backup = os.path.expanduser(f"~/NvStrapsReBar-{time.strftime('%Y%m%d-%H%M%S')}.var")
    with open(backup, "wb") as f:
        f.write(raw)
    print(f"\nbacked up current value to {backup}")

    subprocess.run(["chattr", "-i", VAR], check=True)
    with open(VAR, "wb") as f:
        f.write(attrs + out)

    with open(VAR, "rb") as f:
        back = f.read()[4:]
    if back != out:
        sys.exit("readback mismatch -- the variable was NOT written as intended")
    print("written and verified. Reboot for the DXE driver to apply it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
