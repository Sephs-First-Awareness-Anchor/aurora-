#!/usr/bin/env python3
"""Build an installable native desktop shell containing Aurora's existing runtime.

Run on each target OS. No phone code, generated state, history, checkpoints,
secrets, logs, or repository metadata are bundled into installers.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build" / "aurora-desktop"
SOURCE = BUILD / "aurora_source"

# Runtime and introspection resources. All persistent state must be external.
SOURCE_DIRS = (
    "aurora_internal", "aurora_genealogy", "aurora_manifold_directory",
    "lessons", "knowledge_graph", "src", "docs",
)
EXCLUDE = {".git", ".github", ".venv", "__pycache__", "aurora_state",
           "aurora_state_test", "aurora_logs", "tests", "fixtures"}
EXTENSIONS = {".py", ".pyi", ".json", ".md", ".txt", ".csv",
              ".toml", ".yaml", ".yml", ".html", ".css", ".js",
              ".svg", ".png", ".jpg", ".jpeg", ".webp", ".bin"}


def ignored(directory, names):
    return [n for n in names if n in EXCLUDE or n.endswith((".pyc", ".pyo", ".log", ".zip", ".db", ".sqlite"))
            or (Path(directory) / n).is_file() and (Path(directory) / n).suffix.lower() not in EXTENSIONS]


def stage_runtime():
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    SOURCE.mkdir(parents=True)
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix.lower() in {".py", ".json", ".txt"}:
            shutil.copy2(path, SOURCE / path.name)
    for dirname in SOURCE_DIRS:
        path = ROOT / dirname
        if path.is_dir():
            shutil.copytree(path, SOURCE / dirname, ignore=ignored)
    # The setup module must be available to the in-app phone pairing button.
    (SOURCE / "scripts").mkdir()
    for name in ("__init__.py", "aurora_home_setup.py"):
        p = ROOT / "scripts" / name
        if p.exists():
            shutil.copy2(p, SOURCE / "scripts" / name)


def build():
    if sys.version_info[:2] != (3, 11):
        raise SystemExit("Build on Python 3.11; runtime supports Linux/Windows.")
    stage_runtime()
    source_files = [
        p.stem for p in SOURCE.glob("*.py")
        if p.stem.isidentifier() and p.stem not in {"setup", "conftest"}
    ]
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onedir", "--windowed", "--name", "AuroraDesktop",
        "--distpath", str(ROOT / "dist"), "--workpath", str(BUILD / "work"),
        "--specpath", str(BUILD), "--paths", str(SOURCE),
        "--add-data", f"{SOURCE}{os.pathsep}aurora_source",
        "--hidden-import", "PySide6.QtWebEngineWidgets",
        "--collect-submodules", "aurora_internal",
        "--collect-submodules", "aurora_genealogy",
        "--collect-submodules", "requests",
        "--collect-submodules", "pyttsx3",
    ]
    for mod in source_files:
        cmd.extend(["--hidden-import", mod])
    cmd.append(str(ROOT / "packaging" / "desktop" / "aurora_desktop.py"))
    print("Staged runtime:", SOURCE)
    print("Bundled root modules:", len(source_files))
    subprocess.run(cmd, cwd=ROOT, check=True)


if __name__ == "__main__":
    build()
