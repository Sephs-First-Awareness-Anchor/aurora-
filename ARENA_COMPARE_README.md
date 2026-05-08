# CrystalZip Arena Compare

This script compares:

- CrystalZip
- ZIP Deflate
- 7-Zip LZMA2 max settings, if installed

## Termux setup

Install 7-Zip:

```bash
pkg update
pkg install 7zip
```

Check:

```bash
7z
```

## Run benchmark

Put `arena_compare.py` in the same folder as `crystalzip.py`, then run:

```bash
python arena_compare.py /path/to/test-folder
```

Example for Android shared downloads:

```bash
python arena_compare.py ~/storage/downloads/MyFolder -o arena_out
```

## Output

The script creates:

- `arena_report.json`
- `arena_report.txt`
- `.cz`, `.zip`, and `.7z` test archives

Send `arena_report.txt` or `arena_report.json` back to Ceph for analysis.
