# CrispOffice open font pack

Optional, openly licensed fonts for CrispOffice Writer, Spreadsheet and
Presentation. CrispOffice prefers exact fonts installed by Microsoft Office.
This pack provides OFL/Apache-licensed metric-compatible or visual fallbacks
when those fonts are not installed.

## Packs

- **Core** — Carlito (Calibri), Tinos (Times New Roman), Cousine (Courier New),
  Caladea (Cambria) and Arimo (Arial/Helvetica). Metric-compatible where noted.
- **Visual** — Lato (Calibri Light), Inter and DM Sans (Aptos visual), Open Sans,
  PT Sans (Tahoma visual), Noto Sans and Source Serif 4, plus Courier Prime.

Fonts are built from Google Fonts commit
`869789e84da92782c144d83d69b64cec54905b5f`. The build instantiates static
Regular/Bold/Italic/Bold Italic faces and writes a manifest with SHA-256 for
every file.

## Licensing

Every family in this repository is licensed under the SIL Open Font License
1.1. The licence text for each family is in `licenses/`. The pack may be
bundled or redistributed with CrispOffice, including commercially, provided
the copyright and licence notices are retained and the fonts are not sold on
their own. The font files are unmodified except for generating static instances
from the variable sources and setting standard style names.

This repository does **not** contain Microsoft fonts. Calibri, Aptos, Arial,
Tahoma and Microsoft Sans Serif remain runtime-only from a licensed Microsoft
Office installation.

## Release assets

The app downloads the immutable `fonts-v1` release assets over HTTPS and
verifies each SHA-256 before installing into the app-support directory.

## Rebuilding

```sh
python3 -m pip install fonttools
python3 tool/build_pack.py
```

The build writes `dist/`, `manifest.json` and the two review archives. These
generated files are not committed.
