#!/usr/bin/env python3
"""Build the CrispOffice open font packs from pinned Google Fonts sources.

The build downloads fonts only into a temporary dist directory. Neither the
font binaries nor Microsoft fonts are committed to the repository; release
assets contain the rebuilt OFL/Apache faces and their licences.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
LICENSES = ROOT / "licenses"
COMMIT = "869789e84da92782c144d83d69b64cec54905b5f"
RAW = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}"

# family: (google path, license path, axes, aliases)
STATIC = {
    "Carlito": ("ofl/carlito", ("Calibri",)),
    "Tinos": ("ofl/tinos", ("Times New Roman", "Times")),
    "Cousine": ("ofl/cousine", ("Courier New", "Courier")),
    "Caladea": ("ofl/caladea", ("Cambria",)),
    "Lato": ("ofl/lato", ()),
    "PTSans": ("ofl/ptsans", ()),
    "CourierPrime": ("ofl/courierprime", ()),
}
VARIABLE = {
    "Arimo": ("ofl/arimo", "Arimo", "Arimo-Italic", {"wght": (400, 700)}, ()),
    "Inter": ("ofl/inter", "Inter", "Inter-Italic", {"wght": (400, 700), "opsz": 14}, ()),
    "DMSans": ("ofl/dmsans", "DMSans", "DMSans-Italic", {"wght": (400, 700), "opsz": 14}, ()),
    "OpenSans": ("ofl/opensans", "OpenSans", "OpenSans-Italic", {"wght": (400, 700), "wdth": 100}, ()),
    "NotoSans": ("ofl/notosans", "NotoSans", "NotoSans-Italic", {"wght": (400, 700), "wdth": 100}, ()),
    "SourceSerif4": ("ofl/sourceserif4", "SourceSerif4", "SourceSerif4-Italic", {"wght": (400, 700), "opsz": 14}, ()),
}
DISPLAY = {
    "PTSans": "PT Sans",
    "DMSans": "DM Sans",
    "OpenSans": "Open Sans",
    "NotoSans": "Noto Sans",
    "SourceSerif4": "Source Serif 4",
}

STYLES = (
    ("Regular", 400, False, ""),
    ("Bold", 700, False, "Bold"),
    ("Italic", 400, True, "Italic"),
    ("BoldItalic", 700, True, "BoldItalic"),
)

def fetch(path: str) -> bytes:
    with urllib.request.urlopen(f"{RAW}/{path}", timeout=60) as response:
        return response.read()

def set_names(font: TTFont, family: str, weight: int, italic: bool) -> None:
    if weight >= 700 and italic:
        style = "Bold Italic"
    elif weight >= 700:
        style = "Bold"
    elif italic:
        style = "Italic"
    else:
        style = "Regular"
    full = f"{family} {style}"
    ps = f"{family}-{style.replace(' ', '')}"
    names = font["name"]
    for record in list(names.names):
        if record.nameID in {1, 2, 4, 6, 16, 17}:
            names.removeNames(nameID=record.nameID)
    for platform_id, encoding_id, language_id in ((3, 1, 0x409),):
        names.setName(family, 1, platform_id, encoding_id, language_id)
        names.setName(style if style != "Regular" else "Regular", 2, platform_id, encoding_id, language_id)
        names.setName(full, 4, platform_id, encoding_id, language_id)
        names.setName(ps, 6, platform_id, encoding_id, language_id)
        names.setName(family, 16, platform_id, encoding_id, language_id)
        names.setName(style, 17, platform_id, encoding_id, language_id)
    os2 = font["OS/2"]
    os2.usWeightClass = weight
    os2.fsSelection &= ~0x41
    os2.fsSelection |= (0x20 if weight >= 700 else 0) | (0x01 if italic else 0)
    if weight < 700 and not italic:
        os2.fsSelection |= 0x40
    if "head" in font:
        font["head"].macStyle = (0x01 if weight >= 700 else 0) | (0x02 if italic else 0)
    if "post" in font:
        font["post"].italicAngle = -12.0 if italic else 0.0

def save(font: TTFont, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    font.save(destination)

def build() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    LICENSES.mkdir(exist_ok=True)
    manifest = {"version": 1, "source": f"https://github.com/google/fonts/tree/{COMMIT}", "packs": {}}
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        core_files = []
        visual_files = []
        for family, (directory, aliases) in STATIC.items():
            source_dir = temp / family
            for style, weight, italic, suffix in STYLES:
                remote = f"{directory}/{family}-{style}.ttf"
                if family == "PTSans":
                    remote = f"{directory}/PT_Sans-Web-{style}.ttf"
                data = fetch(remote)
                # Static upstream faces are redistributed byte-for-byte. Several
                # of them carry a Reserved Font Name; that licence permits
                # bundling the original, not publishing a renamed derivative.
                dest = DIST / ("core" if family in {"Carlito", "Tinos", "Cousine", "Caladea"} else "visual") / f"{family}-{style}.ttf"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                entry = {"family": family, "weight": weight, "italic": italic, "file": dest.name, "bytes": dest.stat().st_size, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "aliases": list(aliases)}
                (core_files if dest.parent.name == "core" else visual_files).append(entry)
            if family == "Tinos":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/googlefonts/tinos/3b4482a99b80ea5fc75f187b1be3120a3f5905b3/OFL.txt",
                    timeout=60,
                ) as response:
                    license_data = response.read()
            else:
                license_data = fetch(f"{directory}/OFL.txt")
            (LICENSES / f"{family}-OFL.txt").write_bytes(license_data)
        for family, (directory, base, italic_base, axes, aliases) in VARIABLE.items():
            for style, weight, italic, suffix in STYLES:
                source_name = italic_base if italic else base
                remote = f"{directory}/{source_name}%5B{','.join(f'{axis}' for axis in axes)}%5D.ttf"
                # Google stores axes alphabetically in the filename.
                axis_names = sorted(axes)
                remote = f"{directory}/{source_name}%5B{','.join(axis_names)}%5D.ttf"
                data = fetch(remote)
                src = temp / f"{family}-{style}-var.ttf"
                src.write_bytes(data)
                font = TTFont(src)
                locations = {axis: (weight if axis == "wght" else value) for axis, value in axes.items()}
                instance = instantiateVariableFont(font, locations, inplace=False)
                set_names(instance, DISPLAY.get(family, family), weight, italic)
                dest = DIST / ("core" if family == "Arimo" else "visual") / f"{family}-{style}.ttf"
                save(instance, dest)
                entry = {"family": DISPLAY.get(family, family), "weight": weight, "italic": italic, "file": dest.name, "bytes": dest.stat().st_size, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "aliases": list(aliases)}
                (core_files if dest.parent.name == "core" else visual_files).append(entry)
            (LICENSES / f"{family}-OFL.txt").write_bytes(fetch(f"{directory}/OFL.txt"))
        # Core archive includes the four metric-compatible families.
        manifest["packs"]["core"] = {"files": core_files}
        manifest["packs"]["visual"] = {"files": visual_files}
        (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        for pack in ("core", "visual"):
            archive = ROOT / f"crispoffice-{pack}-fonts-v1.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for entry in manifest["packs"][pack]["files"]:
                    bundle.write(DIST / pack / entry["file"], f"fonts/{entry['file']}")
                for license_file in sorted(LICENSES.glob("*.txt")):
                    bundle.write(license_file, f"licenses/{license_file.name}")
                bundle.write(ROOT / "manifest.json", "manifest.json")
            print(archive, archive.stat().st_size)
        print("core files", len(core_files), "visual files", len(visual_files))

if __name__ == "__main__":
    build()
