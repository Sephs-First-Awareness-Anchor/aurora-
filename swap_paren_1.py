# Authors: Sunni (Sir) Morningstar & Cael Devo
import os
import re
from pathlib import Path

# Matches: foo(1).py  (NO space before parentheses)
PATTERN = re.compile(r"^(?P<stem>.+)\(1\)\.py$")

def main():
    here = Path(".").resolve()
    pairs = []

    for p in here.iterdir():
        if not p.is_file():
            continue

        m = PATTERN.match(p.name)
        if not m:
            continue

        base = here / f"{m.group('stem')}.py"
        if base.exists() and base.is_file():
            pairs.append((base, p))

    if not pairs:
        print("No pairs found like 'foo.py' and 'foo(1).py'.")
        return

    for old_path, new_path in pairs:
        tmp = old_path.with_name(old_path.stem + ".__swap_tmp__.py")

        if tmp.exists():
            raise RuntimeError(f"Temp file already exists: {tmp}")

        # Swap safely
        os.replace(old_path, tmp)
        os.replace(new_path, old_path)
        os.replace(tmp, new_path)

        print(f"Swapped: {old_path.name}  >=<  {new_path.name}")

    print(f"\nDone. Swapped {len(pairs)} file pairs.")

if __name__ == "__main__":
    main()
