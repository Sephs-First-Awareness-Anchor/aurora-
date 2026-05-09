#!/usr/bin/env python3
"""
aurora_internal/aurora_corpus_lifecycle.py

Handles the autonomous lifecycle of training corpora:
- Downloading new material from the internet.
- Managing storage by rotating out old corpora (max 2).
- Detecting variable file formats (JSON, JSONL, CSV, TXT).
- Providing a universal iterator for the training system.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import csv
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Iterator

_STATE_DIR = Path(__file__).resolve().parents[1] / "aurora_state"
_CORPORA_DIR = _STATE_DIR / "corpora"
_CORPORA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Downloader & Manager
# ---------------------------------------------------------------------------

def download_new_corpus(url: str, filename: Optional[str] = None) -> Optional[Path]:
    """Download a new corpus and return the path. Rotates old ones out."""
    if not filename:
        filename = f"corpus_{int(time.time())}"
        if "." in url.split("/")[-1]:
            ext = url.split("/")[-1].split(".")[-1]
            if len(ext) <= 4:
                filename += f".{ext}"
    
    target_path = _CORPORA_DIR / filename
    try:
        print(f"  [CORPUS] Downloading: {url} -> {target_path.name}")
        req = urllib.request.Request(url, headers={"User-Agent": "Aurora/1.0 (Corpus-Downloader)"})
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(target_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)
        
        # After successful download, run rotation
        rotate_corpora(keep=2)
        return target_path
    except Exception as e:
        print(f"  [CORPUS] Download failed: {e}")
        if target_path.exists():
            target_path.unlink()
        return None

def rotate_corpora(keep: int = 2):
    """Remove older corpora to keep the count within limit."""
    items = sorted(
        _CORPORA_DIR.iterdir(),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    if len(items) > keep:
        for old_item in items[keep:]:
            print(f"  [CORPUS] Pruning old corpus to prevent bloat: {old_item.name}")
            try:
                if old_item.is_dir():
                    shutil.rmtree(old_item)
                else:
                    old_item.unlink()
            except Exception:
                pass

# ---------------------------------------------------------------------------
# Format Detection & Universal Parser
# ---------------------------------------------------------------------------

def detect_corpus_format(path: Path) -> str:
    """Scan file beginning and return format key: 'openai_json', 'jsonl', 'csv', 'txt'."""
    ext = path.suffix.lower()
    
    # Peek at first 2KB
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(2048).strip()
    except Exception:
        return "unknown"

    if not head:
        return "empty"

    # Check for OpenAI JSON structure
    if head.startswith("[") or head.startswith("{"):
        try:
            data = json.loads(head if head.endswith("}") or head.endswith("]") else head + " ]")
            # If it's a list or has conversation-like keys
            if isinstance(data, list) or "conversations" in data:
                return "openai_json"
        except Exception:
            pass
        
        # Check for JSONL (multiple { } lines)
        lines = head.splitlines()
        if len(lines) > 1:
            try:
                json.loads(lines[0])
                json.loads(lines[1])
                return "jsonl"
            except Exception:
                pass

    if ext == ".csv" or ("," in head and "\n" in head):
        return "csv"

    return "txt"

def universal_corpus_iterator(path: Path) -> Iterator[Tuple[str, str]]:
    """Yields (user_input, assistant_response) pairs regardless of source format."""
    fmt = detect_corpus_format(path)
    print(f"  [CORPUS] Detected format: {fmt} for {path.name}")

    if fmt == "openai_json":
        yield from _parse_openai_json(path)
    elif fmt == "jsonl":
        yield from _parse_jsonl(path)
    elif fmt == "csv":
        yield from _parse_csv(path)
    else:
        yield from _parse_txt(path)

# --- Internal Parsers ---

def _parse_openai_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Standardize to list of conversations
        convs = []
        if isinstance(data, list): convs = data
        elif isinstance(data, dict):
            convs = data.get("conversations") or data.get("data") or []
        
        for c in convs:
            # This is specific to the complex 'mapping' structure in OpenAI exports
            # We'll try to find a simpler list of messages first
            msgs = c.get("messages")
            if msgs and isinstance(msgs, list):
                last_user = None
                for m in msgs:
                    role = m.get("role") or m.get("author", {}).get("role")
                    content = m.get("content") or ""
                    if isinstance(content, dict): content = content.get("parts", [""])[0]
                    
                    if role == "user": last_user = content
                    elif role in ("assistant", "bot") and last_user:
                        yield (last_user, content)
                        last_user = None
            else:
                # Fallback to the reconstruction logic seen in corpus_runner
                # (simplified here for brevity, would usually call the existing runner helper)
                pass
    except Exception:
        pass

def _parse_jsonl(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                # Try common formats: {"prompt": "...", "completion": "..."} or {"input": "...", "output": "..."}
                u = obj.get("prompt") or obj.get("input") or obj.get("user") or obj.get("question")
                a = obj.get("completion") or obj.get("output") or obj.get("assistant") or obj.get("answer")
                if u and a:
                    yield (str(u), str(a))
            except Exception:
                continue

def _parse_csv(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Try to guess column names
        fields = reader.fieldnames or []
        u_col = next((c for c in fields if c.lower() in ("input", "prompt", "user", "question", "text")), None)
        a_col = next((c for c in fields if c.lower() in ("output", "completion", "assistant", "answer", "response")), None)
        
        if u_col and a_col:
            for row in reader:
                yield (row[u_col], row[a_col])

def _parse_txt(path: Path):
    """Assume alternate lines of user/assistant or simple blocks."""
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
        for i in range(0, len(lines) - 1, 2):
            yield (lines[i], lines[i+1])
