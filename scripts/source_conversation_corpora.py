#!/usr/bin/env python3
"""
Download and convert public conversation corpora for Aurora.

Outputs JSONL files with {"prompt": ..., "completion": ..., "source": ...},
which aurora_internal.aurora_corpus_lifecycle.universal_corpus_iterator can read.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import shutil
import tarfile
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
CORPORA_DIR = ROOT / "aurora_state" / "corpora"
RAW_DIR = CORPORA_DIR / "raw"

SOURCES = {
    "dailydialog": {
        "url": "http://yanran.li/files/ijcnlp_dailydialog.zip",
        "license_note": "Research dataset; see upstream DailyDialog page/paper.",
    },
    "empatheticdialogues": {
        "url": "https://dl.fbaipublicfiles.com/parlai/empatheticdialogues/empatheticdialogues.tar.gz",
        "license_note": "Facebook/ParlAI EmpatheticDialogues release; see upstream repository.",
    },
    "taskmaster1_self": {
        "url": "https://raw.githubusercontent.com/google-research-datasets/Taskmaster/master/TM-1-2019/self-dialogs.json",
        "license_note": "Google Research Taskmaster repository.",
    },
    "taskmaster1_woz": {
        "url": "https://raw.githubusercontent.com/google-research-datasets/Taskmaster/master/TM-1-2019/woz-dialogs.json",
        "license_note": "Google Research Taskmaster repository.",
    },
    "personachat": {
        "url": "https://huggingface.co/datasets/bavard/personachat_truecased/resolve/main/personachat_truecased_full_train.json",
        "license_note": "PersonaChat truecased mirror; see Hugging Face dataset card/upstream references.",
    },
}


def clean_text(value: object) -> str:
    text = str(value or "")
    text = text.replace("\\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def useful_pair(prompt: str, completion: str) -> bool:
    prompt = clean_text(prompt)
    completion = clean_text(completion)
    if len(prompt) < 2 or len(completion) < 2:
        return False
    if prompt == completion:
        return False
    return True


def download(name: str, url: str, force: bool = False) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(url.split("?", 1)[0]).suffix
    if url.endswith(".tar.gz"):
        suffix = ".tar.gz"
    target = RAW_DIR / f"{name}{suffix or '.data'}"
    if target.exists() and target.stat().st_size > 0 and not force:
        return target

    print(f"[download] {name}: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Aurora corpus sourcing"})
    with urllib.request.urlopen(req, timeout=120) as response:
        with target.open("wb") as out:
            shutil.copyfileobj(response, out)
    return target


def write_jsonl(path: Path, rows: Iterable[dict], limit: int) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            prompt = clean_text(row.get("prompt"))
            completion = clean_text(row.get("completion"))
            if not useful_pair(prompt, completion):
                continue
            row = dict(row)
            row["prompt"] = prompt
            row["completion"] = completion
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            if limit and count >= limit:
                break
    return count


def read_jsonl_pairs(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            prompt = clean_text(obj.get("prompt"))
            completion = clean_text(obj.get("completion"))
            if useful_pair(prompt, completion):
                yield {
                    "user": prompt,
                    "assistant": completion,
                    "source": obj.get("source", path.stem),
                }


def iter_adjacent_pairs(utterances: list[str], source: str, meta: dict | None = None) -> Iterator[dict]:
    meta = meta or {}
    last = ""
    for utterance in utterances:
        utterance = clean_text(utterance)
        if last and useful_pair(last, utterance):
            yield {"prompt": last, "completion": utterance, "source": source, **meta}
        last = utterance


def parse_dailydialog(path: Path) -> Iterator[dict]:
    with zipfile.ZipFile(path) as outer:
        for member in outer.namelist():
            if not member.endswith(".zip"):
                continue
            split = Path(member).stem
            with outer.open(member) as inner_file:
                inner_bytes = inner_file.read()
            with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
                dialog_files = [n for n in inner.namelist() if "dialogues_" in n and n.endswith(".txt")]
                for dialog_name in dialog_files:
                    with inner.open(dialog_name) as f:
                        for line_no, raw in enumerate(f.read().decode("utf-8", errors="ignore").splitlines()):
                            turns = [clean_text(t) for t in raw.split("__eou__") if clean_text(t)]
                            yield from iter_adjacent_pairs(
                                turns,
                                "dailydialog",
                                {"split": split, "dialogue_line": line_no},
                            )


def parse_empatheticdialogues(path: Path) -> Iterator[dict]:
    conversations: dict[str, list[tuple[int, str]]] = defaultdict(list)
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.name.endswith(".csv"):
                continue
            split = Path(member.name).stem
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            text = extracted.read().decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            conversations.clear()
            for row in reader:
                conv_id = str(row.get("conv_id") or "")
                idx = int(row.get("utterance_idx") or 0)
                utterance = clean_text(row.get("utterance"))
                if conv_id and utterance:
                    conversations[conv_id].append((idx, utterance))
            for conv_id, items in conversations.items():
                turns = [u for _, u in sorted(items)]
                yield from iter_adjacent_pairs(
                    turns,
                    "empatheticdialogues",
                    {"split": split, "conversation_id": conv_id},
                )


def parse_taskmaster(path: Path, source: str) -> Iterator[dict]:
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    for dialog in data:
        conv_id = str(dialog.get("conversation_id") or dialog.get("instruction_id") or "")
        turns = []
        for utt in dialog.get("utterances", []) or []:
            text = clean_text(utt.get("text"))
            speaker = str(utt.get("speaker") or "")
            if text and not speaker.lower().startswith("api"):
                turns.append(text)
        yield from iter_adjacent_pairs(turns, source, {"conversation_id": conv_id})


def _personachat_turns_from_obj(obj: object) -> Iterator[list[str]]:
    if isinstance(obj, list):
        for item in obj:
            yield from _personachat_turns_from_obj(item)
    elif isinstance(obj, dict):
        if "utterances" in obj and isinstance(obj["utterances"], list):
            for utterance in obj["utterances"]:
                history = utterance.get("history") if isinstance(utterance, dict) else None
                if isinstance(history, list) and len(history) >= 2:
                    yield [clean_text(x) for x in history if clean_text(x)]
        for value in obj.values():
            if isinstance(value, (list, dict)):
                yield from _personachat_turns_from_obj(value)


def parse_personachat(path: Path) -> Iterator[dict]:
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    for idx, turns in enumerate(_personachat_turns_from_obj(data)):
        yield from iter_adjacent_pairs(turns, "personachat", {"conversation_id": str(idx)})


def build(args: argparse.Namespace) -> dict:
    CORPORA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_by": "scripts/source_conversation_corpora.py",
        "limit_per_source": args.limit,
        "sources": SOURCES,
        "outputs": {},
    }

    output_files: list[Path] = []

    try:
        daily = download("dailydialog", SOURCES["dailydialog"]["url"], args.force)
        out = CORPORA_DIR / "dailydialog_pairs.jsonl"
        count = write_jsonl(out, parse_dailydialog(daily), args.limit)
        manifest["outputs"]["dailydialog"] = {"file": out.name, "pairs": count}
        output_files.append(out)
        print(f"[convert] dailydialog: {count} pairs")
    except Exception as exc:
        manifest["outputs"]["dailydialog"] = {"file": "", "pairs": 0, "error": str(exc)}
        print(f"[skip] dailydialog: {exc}")

    empathetic = download("empatheticdialogues", SOURCES["empatheticdialogues"]["url"], args.force)
    out = CORPORA_DIR / "empatheticdialogues_pairs.jsonl"
    count = write_jsonl(out, parse_empatheticdialogues(empathetic), args.limit)
    manifest["outputs"]["empatheticdialogues"] = {"file": out.name, "pairs": count}
    output_files.append(out)
    print(f"[convert] empatheticdialogues: {count} pairs")

    tm_self = download("taskmaster1_self", SOURCES["taskmaster1_self"]["url"], args.force)
    out = CORPORA_DIR / "taskmaster1_self_pairs.jsonl"
    count = write_jsonl(out, parse_taskmaster(tm_self, "taskmaster1_self"), args.limit)
    manifest["outputs"]["taskmaster1_self"] = {"file": out.name, "pairs": count}
    output_files.append(out)
    print(f"[convert] taskmaster1_self: {count} pairs")

    tm_woz = download("taskmaster1_woz", SOURCES["taskmaster1_woz"]["url"], args.force)
    out = CORPORA_DIR / "taskmaster1_woz_pairs.jsonl"
    count = write_jsonl(out, parse_taskmaster(tm_woz, "taskmaster1_woz"), args.limit)
    manifest["outputs"]["taskmaster1_woz"] = {"file": out.name, "pairs": count}
    output_files.append(out)
    print(f"[convert] taskmaster1_woz: {count} pairs")

    persona = download("personachat", SOURCES["personachat"]["url"], args.force)
    out = CORPORA_DIR / "personachat_pairs.jsonl"
    count = write_jsonl(out, parse_personachat(persona), args.limit)
    manifest["outputs"]["personachat"] = {"file": out.name, "pairs": count}
    output_files.append(out)
    print(f"[convert] personachat: {count} pairs")

    combined: list[dict] = []
    per_source_seen: dict[str, int] = defaultdict(int)
    per_source_limit = args.combined_per_source
    for output_file in output_files:
        for pair in read_jsonl_pairs(output_file):
            source = str(pair.get("source") or output_file.stem)
            if per_source_limit and per_source_seen[source] >= per_source_limit:
                continue
            combined.append(pair)
            per_source_seen[source] += 1

    combined_path = ROOT / "conversations.json"
    combined_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest["combined"] = {
        "file": str(combined_path.relative_to(ROOT)),
        "pairs": len(combined),
        "per_source": dict(per_source_seen),
    }
    print(f"[combine] conversations.json: {len(combined)} pairs")

    manifest_path = CORPORA_DIR / "conversation_corpora_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000, help="Max pairs per source. 0 means no limit.")
    parser.add_argument("--combined-per-source", type=int, default=2500, help="Max pairs per source in root conversations.json. 0 means no limit.")
    parser.add_argument("--force", action="store_true", help="Redownload raw source files.")
    args = parser.parse_args()
    manifest = build(args)
    total = sum(v["pairs"] for v in manifest["outputs"].values())
    print(f"[done] total pairs: {total}")
    print(f"[done] manifest: {CORPORA_DIR / 'conversation_corpora_manifest.json'}")


if __name__ == "__main__":
    main()
