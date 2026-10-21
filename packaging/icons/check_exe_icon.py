"""
Check that a Windows executable carries the app icon (packaging/icons/icon.ico).

Compares the RT_ICON resources embedded by PyInstaller byte for byte with the
images in icon.ico and exits non-zero if any size is missing or different.
Used by the Windows CI job; needs pefile (a PyInstaller dependency on Windows).

Usage:
    python packaging/icons/check_exe_icon.py dist/vinyl-label-printer/vinyl-label-printer.exe
"""

import struct
import sys
from pathlib import Path

import pefile

ICO_FILE = Path(__file__).resolve().parent / "icon.ico"


def ico_images(path: Path) -> dict[int, bytes]:
    """Return the images of an .ico file, keyed by pixel width."""
    data = path.read_bytes()
    _, _, count = struct.unpack_from("<HHH", data, 0)
    images = {}
    for i in range(count):
        width, _, _, _, _, _, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        images[width or 256] = data[offset:offset + size]
    return images


def exe_icon_images(path: Path) -> list[bytes]:
    """Return the raw data of all RT_ICON resources of an executable."""
    pe = pefile.PE(str(path))
    rt_icon = pefile.RESOURCE_TYPE["RT_ICON"]
    resources = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
    images = []
    for entry in resources.entries if resources else []:
        if entry.id != rt_icon:
            continue
        for icon in entry.directory.entries:
            for lang in icon.directory.entries:
                rva, size = lang.data.struct.OffsetToData, lang.data.struct.Size
                images.append(pe.get_data(rva, size))
    return images


def main() -> int:
    exe = Path(sys.argv[1])
    expected = ico_images(ICO_FILE)
    embedded = exe_icon_images(exe)
    print(f"{exe.name}: {len(embedded)} RT_ICON resource(s)")
    missing = [size for size, data in sorted(expected.items()) if data not in embedded]
    for size in sorted(expected):
        print(f"  {size:>3} px: {'MISSING' if size in missing else 'ok'}")
    if missing:
        print(f"ERROR: exe does not carry {ICO_FILE.name} (missing sizes: {missing})")
        return 1
    print(f"OK: exe carries all {len(expected)} images of {ICO_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
