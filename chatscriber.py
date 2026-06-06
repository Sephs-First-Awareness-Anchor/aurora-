#!/usr/bin/env python3
# chatscriber.py
#
# Chats Criteria (single-file, Termux-friendly, stdlib-only)
# ---------------------------------------------------------
# What this version adds:
# - ingest-code: ingest a local codebase (e.g. Aurora) into the SAME continuity DB
# - Keeps existing share-link ingest behavior intact
# - Default DB path set to /storage/emulated/0/Aurora/chats_criteria.json (Termux-friendly)
#
# Usage:
#   # 1) Ingest a ChatGPT share link (existing)
#   python chatscriber.py ingest "https://chatgpt.com/share/<id>" --db /storage/emulated/0/Aurora/chats_criteria.json
#
#   # 2) Ingest a codebase (NEW)
#   python chatscriber.py ingest-code /storage/emulated/0/Aurora --name aurora --db /storage/emulated/0/Aurora/chats_criteria.json
#
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple, Iterable

APP_NAME = "chats_criteria"
SCHEMA_VERSION = 4  # bumped for full transcript capture
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) chatscriber/4.0"

# Termux-friendly default; override with --db if you want.
DEFAULT_DB_PATH = "/storage/emulated/0/Aurora/chats_criteria.json"


# ----------------------------
# Utilities
# ----------------------------

def _now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def _sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()

def _safe_int(x: Any) -> int:
    try:
        return int(x)
    except Exception:
        return 0

def _read_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json(path: str, obj: Dict[str, Any], pretty: bool = False) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        else:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    os.replace(tmp, path)

def _http_get(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html,*/*",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ----------------------------
# Share link ingestion (ChatGPT)
# ----------------------------

_SHARE_RE = re.compile(r"(?:https?://)?chatgpt\.com/share/([0-9a-fA-F-]{16,})")
_SHARE_RE2 = re.compile(r"(?:https?://)?chat\.openai\.com/share/([0-9a-fA-F-]{16,})")

def extract_share_id(s: str) -> Optional[str]:
    s = (s or "").strip()
    m = _SHARE_RE.search(s)
    if m:
        return m.group(1)
    m = _SHARE_RE2.search(s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[0-9a-fA-F-]{16,}", s):
        return s
    return None

def fetch_shared_conversation_json(share_id: str) -> Dict[str, Any]:
    url = f"https://chatgpt.com/backend-api/share/{share_id}"
    try:
        raw = _http_get(url)
        text = raw.decode("utf-8", errors="replace").lstrip()
        if text.startswith("<"):
            raise RuntimeError("Got HTML instead of JSON. Share link may not be public.")
        return json.loads(text)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP error fetching share JSON ({e.code}): {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching share JSON: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError("Got non-JSON response from share endpoint.") from e


# ----------------------------
# Conversation linearization
# ----------------------------

class Msg:
    __slots__ = ("role", "text", "create_time", "message_id")
    def __init__(self, role: str, text: str, create_time: Optional[float], message_id: Optional[str]) -> None:
        self.role = role
        self.text = text
        self.create_time = create_time
        self.message_id = message_id

def _message_text_from_content(content: Dict[str, Any]) -> str:
    if not content:
        return ""
    ctype = content.get("content_type")
    if ctype == "text":
        parts = content.get("parts") or []
        if isinstance(parts, list):
            return "\n".join([p for p in parts if isinstance(p, str)]).strip()
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        return "\n".join([str(p) for p in parts]).strip()
    return ""

def linearize_mapping(mapping: Dict[str, Any]) -> List[Msg]:
    if not mapping:
        return []

    roots: List[str] = []
    for node_id, node in mapping.items():
        parent = node.get("parent")
        if parent is None or parent not in mapping:
            roots.append(node_id)

    if "bbb23_placeholder_parent" in mapping:
        roots = ["bbb23_placeholder_parent"]

    visited = set()
    out: List[Msg] = []

    def node_sort_key(nid: str) -> Tuple[float, str]:
        node = mapping.get(nid, {})
        msg = node.get("message") or {}
        ct = msg.get("create_time")
        ct_f = float(ct) if isinstance(ct, (int, float)) else float("inf")
        mid = msg.get("id") or nid
        return (ct_f, str(mid))

    def dfs(nid: str) -> None:
        if nid in visited:
            return
        visited.add(nid)

        node = mapping.get(nid, {})
        msg = node.get("message")
        if isinstance(msg, dict):
            author = msg.get("author") or {}
            role = str(author.get("role") or "unknown")
            content = msg.get("content") or {}
            text = _message_text_from_content(content)
            ct = msg.get("create_time")
            ct_f = float(ct) if isinstance(ct, (int, float)) else None
            if text and text.strip():
                out.append(Msg(role=role, text=text.strip(), create_time=ct_f, message_id=msg.get("id")))

        children = node.get("children") or []
        if not isinstance(children, list):
            children = []
        children = sorted(children, key=node_sort_key)
        for c in children:
            dfs(c)

    for r in sorted(roots, key=node_sort_key):
        dfs(r)

    if len(visited) != len(mapping):
        leftovers = sorted([k for k in mapping.keys() if k not in visited], key=node_sort_key)
        for nid in leftovers:
            dfs(nid)

    out.sort(key=lambda m: (m.create_time if m.create_time is not None else float("inf"), m.message_id or ""))
    return out


# ----------------------------
# Tokenization + summarization helpers
# ----------------------------

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_STOP = set("""
the and for that with this you your are was were have has but not from they their will would can could
just like what its it's into about because when then than there here also really im i'm dont don't did does doing done
get got one two three yes no okay right sure true
a an to of in on at as is be by if or we i me my our us
""".split())

def _tokenize(text: str) -> List[str]:
    toks = []
    for t in _WORD_RE.findall(text or ""):
        tl = t.lower()
        if tl in _STOP:
            continue
        if len(tl) <= 2:
            continue
        toks.append(tl)
    return toks

def _bag(tokens: List[str]) -> Dict[str, int]:
    d: Dict[str, int] = {}
    for t in tokens:
        d[t] = d.get(t, 0) + 1
    return d

def _top_terms_from_bag(bag: Dict[str, int], n: int = 12) -> List[Tuple[str, int]]:
    return sorted(bag.items(), key=lambda kv: (-kv[1], kv[0]))[:n]

def _first_line(text: str, limit: int = 200) -> str:
    s = (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""
    if len(s) > limit:
        s = s[:limit - 3] + "..."
    return s

def _extract_salient_sentences(text: str, max_sent: int = 4) -> List[str]:
    sents = [s.strip() for s in _SENT_SPLIT_RE.split(text or "") if s.strip()]
    if not sents:
        return []
    toks_all = _tokenize(text)
    freq = _bag(toks_all)
    if not freq:
        return sents[:max_sent]

    def sent_score(s: str) -> float:
        toks = _tokenize(s)
        if not toks:
            return 0.0
        score = 0.0
        for t in set(toks):
            score += 1.0 / (1.0 + freq.get(t, 0))
        L = len(s)
        if 60 <= L <= 240:
            score += 0.5
        return score

    ranked = sorted(sents, key=sent_score, reverse=True)
    return ranked[:max_sent]


# ----------------------------
# Snapshot (chat)
# ----------------------------

def summarize_conversation(messages: List[Msg], title: str, include_messages: bool = True) -> Dict[str, Any]:
    user_msgs = [m for m in messages if m.role == "user"]
    assistant_msgs = [m for m in messages if m.role == "assistant"]

    freq: Dict[str, int] = {}
    for m in messages:
        for t in _tokenize(m.text):
            freq[t] = freq.get(t, 0) + 1
    top_terms = dict(_top_terms_from_bag(freq, n=30))

    def score_msg(m: Msg) -> int:
        s = len(m.text)
        s += 6 * len(re.findall(r"\b[A-Z][a-z]{2,}\b", m.text))
        s += 3 * len(re.findall(r"\b\d{2,}\b", m.text))
        return s

    candidates = sorted(messages, key=score_msg, reverse=True)[:12]
    highlights = []
    seen = set()
    for m in candidates:
        line = _first_line(m.text, 220)
        if not line:
            continue
        h = _sha1(m.role + "|" + line)
        if h in seen:
            continue
        seen.add(h)
        highlights.append({"role": m.role, "line": line})

    # Full transcript fingerprint (stable even if titles change)
    text_all = "\n".join([f"{m.role}: {m.text}" for m in messages])
    fp = _sha1(text_all[:500000])

    snap: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "chat_share",
        "title": title,
        "created_at": _now_iso(),
        "stats": {
            "messages_total": len(messages),
            "user_messages": len(user_msgs),
            "assistant_messages": len(assistant_msgs),
        },
        "top_terms": top_terms,
        "high_signal_lines": highlights,
        "fingerprint": {"sha1_text": fp},
    }

    if include_messages:
        snap["messages"] = [
            {
                "role": m.role,
                "text": m.text,
                "create_time": m.create_time,
                "id": m.message_id,
            }
            for m in messages
        ]

    return snap


# ----------------------------
# Codebase ingestion (NEW)
# ----------------------------

_DEFAULT_EXTS = {
    ".py", ".json", ".md", ".txt", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".rst", ".csv", ".tsv", ".js", ".ts",
}

def _looks_binary(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(2048)
        if b"\x00" in chunk:
            return True
        # If there are lots of non-text bytes, treat as binary.
        # (keep permissive, we only want to skip true binaries)
        bad = 0
        for b in chunk:
            if b in (9, 10, 13):  # tabs/newlines
                continue
            if 32 <= b <= 126:
                continue
            bad += 1
        return bad > max(40, len(chunk) // 4)
    except Exception:
        return True

def _read_text(path: str, max_bytes: int) -> str:
    # Read up to max_bytes; ignore decode errors for robustness
    with open(path, "rb") as f:
        raw = f.read(max_bytes)
    return raw.decode("utf-8", errors="ignore")

def _walk_files(root: str,
                exts: set[str],
                max_file_bytes: int,
                include_hidden: bool = False) -> List[str]:
    out: List[str] = []
    root = os.path.abspath(root)

    for dirpath, dirnames, filenames in os.walk(root):
        # prune hidden dirs unless requested
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for fn in filenames:
            if not include_hidden and fn.startswith("."):
                continue
            p = os.path.join(dirpath, fn)

            # Skip obvious junk
            if fn.endswith((".pyc", ".pyo")):
                continue

            ext = os.path.splitext(fn)[1].lower()
            if exts and ext not in exts:
                continue

            try:
                st = os.stat(p)
                if st.st_size > max_file_bytes:
                    continue
            except Exception:
                continue

            if _looks_binary(p):
                continue

            out.append(p)

    out.sort()
    return out

def _extract_exports_and_imports_py(text: str) -> Tuple[List[str], List[str], str]:
    exports: List[str] = []
    imports: List[str] = []
    doc = ""

    try:
        tree = ast.parse(text)
    except Exception:
        # Fallback for malformed python: do light regex
        exports = re.findall(r"^\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text, flags=re.M)
        imports = re.findall(r"^\s*(?:from|import)\s+([A-Za-z0-9_\.]+)", text, flags=re.M)
        return sorted(set(exports)), sorted(set(imports)), ""

    # module docstring
    doc = ast.get_docstring(tree) or ""
    if doc:
        doc = doc.strip().split("\n\n")[0].strip()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports.append(node.name)
        elif isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return sorted(set(exports)), sorted(set(imports)), doc

def _high_signal_lines(text: str, limit: int = 18) -> List[str]:
    lines = (text or "").splitlines()
    scored: List[Tuple[int, str]] = []

    # weight hints
    for i, ln in enumerate(lines):
        s = 0
        l = ln.strip()
        if not l:
            continue
        if l.startswith(("def ", "class ")):
            s += 120
        if any(k in l for k in ("TODO", "FIXME", "NOTE", "BUG", "HACK")):
            s += 70
        if l.startswith(("#", '"""', "'''")):
            s += 10
        if "raise " in l or "assert " in l:
            s += 10
        if "ExistenceMode" in l or "Ontological" in l or "Contract" in l or "IVM" in l:
            s += 25
        # longer, information-dense lines get a small boost
        s += min(25, len(l) // 20)
        if s > 0:
            scored.append((s, l[:260]))

    scored.sort(key=lambda x: (-x[0], x[1]))
    out: List[str] = []
    seen = set()
    for s, l in scored:
        h = _sha1(l)
        if h in seen:
            continue
        seen.add(h)
        out.append(l)
        if len(out) >= limit:
            break
    return out

def summarize_codebase(root_dir: str,
                       name: str,
                       exts: set[str],
                       max_file_bytes: int,
                       max_read_bytes: int,
                       include_hidden: bool = False) -> Dict[str, Any]:
    files = _walk_files(root_dir, exts=exts, max_file_bytes=max_file_bytes, include_hidden=include_hidden)
    per_file: Dict[str, Any] = {}

    global_terms: Dict[str, int] = {}
    repo_fp_parts: List[str] = []
    exports_total = 0

    for p in files:
        rel = os.path.relpath(p, os.path.abspath(root_dir))
        try:
            st = os.stat(p)
        except Exception:
            continue

        text = _read_text(p, max_bytes=max_read_bytes)
        raw_fp = _sha1(text)

        ext = os.path.splitext(p)[1].lower()
        exports: List[str] = []
        imports: List[str] = []
        doc_summary = ""

        if ext == ".py":
            exports, imports, doc_summary = _extract_exports_and_imports_py(text)
            exports_total += len(exports)

        # term bag
        toks = _tokenize(text)
        bag = _bag(toks)
        for k, v in bag.items():
            global_terms[k] = global_terms.get(k, 0) + v

        hs = _high_signal_lines(text)

        per_file[rel] = {
            "path": rel,
            "ext": ext,
            "bytes": st.st_size,
            "mtime": int(st.st_mtime),
            "sha1": raw_fp,
            "doc": doc_summary,
            "exports": exports,
            "imports": imports,
            "top_terms": dict(_top_terms_from_bag(bag, n=16)),
            "high_signal_lines": hs,
        }

        repo_fp_parts.append(rel + ":" + raw_fp)

    repo_fp = _sha1("|".join(repo_fp_parts))
    top_terms = dict(_top_terms_from_bag(global_terms, n=40))

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "codebase",
        "name": name,
        "root_dir": os.path.abspath(root_dir),
        "created_at": _now_iso(),
        "stats": {
            "files_total": len(per_file),
            "exports_total": exports_total,
        },
        "top_terms": top_terms,
        "files": per_file,
        "fingerprint": {"sha1_repo": repo_fp},
    }


# ----------------------------
# Merge + Schema Upgrades
# ----------------------------

def _history_list_to_dict(hist_list: List[Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in hist_list:
        if not isinstance(item, dict):
            continue
        h = _sha1(json.dumps(item, sort_keys=True))
        out[h] = item
    return out

def ensure_schema(dst: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upgrade older DB schemas in-place.
    - history: list -> dict
    - adds systems namespace for code ingestion
    """
    if not dst:
        dst = {}

    dst.setdefault("app", APP_NAME)
    dst.setdefault("schema_version", SCHEMA_VERSION)
    dst.setdefault("created_at", dst.get("created_at") or _now_iso())
    dst.setdefault("updated_at", _now_iso())
    dst.setdefault("threads", {})

    # continuity
    dst.setdefault("continuity", {})
    if not isinstance(dst["continuity"], dict):
        dst["continuity"] = {}
    dst["continuity"].setdefault("top_terms", {})
    dst["continuity"].setdefault("latest", {})
    dst["continuity"].setdefault("systems", {})  # aggregated code terms, etc.

    # systems
    dst.setdefault("systems", {})
    if not isinstance(dst["systems"], dict):
        dst["systems"] = {}

    # history
    if "history" not in dst:
        dst["history"] = {}
    else:
        if isinstance(dst["history"], list):
            dst["history"] = _history_list_to_dict(dst["history"])
        elif not isinstance(dst["history"], dict):
            dst["history"] = {}

    # threads
    if not isinstance(dst.get("threads"), dict):
        dst["threads"] = {}

    return dst

def merge_update_chat(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    dst = ensure_schema(dst)

    src_fp = (src.get("fingerprint") or {}).get("sha1_text") or _sha1(json.dumps(src, sort_keys=True))
    title = src.get("title") or f"shared:{src_fp[:8]}"
    stats = src.get("stats") or {}

    threads = dst["threads"]
    thread = threads.get(src_fp)
    if thread is None:
        thread = threads[src_fp] = {
            "first_seen": _now_iso(),
            "last_seen": _now_iso(),
            "title": title,
            "stats_last": {},
            "stats_max": {},
            "top_terms_max": {},
            "highlights": {},   # hash -> {role,line}
            "messages": [],     # full transcript (optional)
        }
    else:
        thread["last_seen"] = _now_iso()
        if title:
            thread["title"] = title

    # stats
    thread["stats_last"] = stats
    thread.setdefault("stats_max", {})
    for k, v in stats.items():
        iv = _safe_int(v)
        pv = _safe_int(thread["stats_max"].get(k))
        if iv > pv:
            thread["stats_max"][k] = iv

    # top terms
    thread.setdefault("top_terms_max", {})
    src_terms = src.get("top_terms") or {}
    if isinstance(src_terms, dict):
        for term, cnt in src_terms.items():
            if not term:
                continue
            cnt_i = _safe_int(cnt)
            prev_t = _safe_int(thread["top_terms_max"].get(term))
            if cnt_i > prev_t:
                thread["top_terms_max"][term] = cnt_i

            prev_g = _safe_int(dst["continuity"]["top_terms"].get(term))
            if cnt_i > prev_g:
                dst["continuity"]["top_terms"][term] = cnt_i

    # highlights
    thread.setdefault("highlights", {})
    for item in (src.get("high_signal_lines") or []):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "unknown")
        line = str(item.get("line") or "").strip()
        if not line:
            continue
        h = _sha1(role + "|" + line)
        if h not in thread["highlights"]:
            thread["highlights"][h] = {"role": role, "line": line}

    # full transcript (store every message, not just highlights)
    src_msgs = src.get("messages")
    if isinstance(src_msgs, list) and src_msgs:
        thread["messages"] = src_msgs
        thread["messages_last_seen"] = _now_iso()
        # stable-ish fingerprint of stored message list
        try:
            thread["messages_sha1"] = _sha1(json.dumps(src_msgs, ensure_ascii=False, separators=(",", ":"), sort_keys=True)[:500000])
        except Exception:
            thread["messages_sha1"] = _sha1(str(src_msgs)[:500000])

    dst["continuity"]["latest"] = {
        "at": _now_iso(),
        "kind": "chat_share",
        "fingerprint": src_fp,
        "title": title,
        "stats": stats,
    }

    event = {"at": _now_iso(), "event": "ingest_chat", "fingerprint": src_fp, "title": title, "stats": stats}
    eh = _sha1(json.dumps(event, sort_keys=True))
    dst["history"][eh] = event

    dst["updated_at"] = _now_iso()
    return dst

def merge_update_code(dst: Dict[str, Any], snap: Dict[str, Any]) -> Dict[str, Any]:
    dst = ensure_schema(dst)

    sys_name = snap.get("name") or "codebase"
    repo_fp = (snap.get("fingerprint") or {}).get("sha1_repo") or _sha1(json.dumps(snap, sort_keys=True))

    systems = dst["systems"]
    sys_bucket = systems.get(sys_name)
    if sys_bucket is None:
        sys_bucket = systems[sys_name] = {
            "first_seen": _now_iso(),
            "last_seen": _now_iso(),
            "repos": {},   # sha1_repo -> snapshot metadata + files
            "latest": {},
        }
    else:
        sys_bucket["last_seen"] = _now_iso()

    repos = sys_bucket.setdefault("repos", {})
    repos[repo_fp] = snap

    # update latest
    sys_bucket["latest"] = {
        "at": _now_iso(),
        "fingerprint": repo_fp,
        "root_dir": snap.get("root_dir"),
        "stats": snap.get("stats") or {},
    }

    # aggregate terms into continuity.systems
    src_terms = snap.get("top_terms") or {}
    if isinstance(src_terms, dict):
        agg = dst["continuity"]["systems"].setdefault(sys_name, {})
        if not isinstance(agg, dict):
            agg = {}
            dst["continuity"]["systems"][sys_name] = agg
        for term, cnt in src_terms.items():
            cnt_i = _safe_int(cnt)
            agg[term] = max(_safe_int(agg.get(term)), cnt_i)

    dst["continuity"]["latest"] = {
        "at": _now_iso(),
        "kind": "codebase",
        "fingerprint": repo_fp,
        "title": f"{sys_name}:{repo_fp[:8]}",
        "stats": snap.get("stats") or {},
    }

    event = {"at": _now_iso(), "event": "ingest_code", "system": sys_name, "fingerprint": repo_fp, "root_dir": snap.get("root_dir")}
    eh = _sha1(json.dumps(event, sort_keys=True))
    dst["history"][eh] = event

    dst["updated_at"] = _now_iso()
    return dst


# ----------------------------
# CLI
# ----------------------------

def cmd_ingest(args: argparse.Namespace) -> int:
    share_id = extract_share_id(args.target)
    if not share_id:
        print("Could not parse share id. Provide a chatgpt.com/share/<id> link or raw id.", file=sys.stderr)
        return 2

    data = fetch_shared_conversation_json(share_id)
    title = data.get("title") or f"shared:{share_id}"
    mapping = data.get("mapping") or {}

    messages = linearize_mapping(mapping)
    if not messages:
        print("Fetched share JSON but extracted 0 messages. Share may be empty/redacted.", file=sys.stderr)

    snap = summarize_conversation(messages, title=title, include_messages=(not args.compact))

    db_path = args.db or DEFAULT_DB_PATH
    db = _read_json(db_path) if os.path.exists(db_path) else {}
    db = merge_update_chat(db, snap)
    _write_json(db_path, db, pretty=args.pretty)

    print(f"[OK] Ingested chat: {title}")
    print(f"[OK] Messages: {len(messages)}")
    print(f"[OK] DB: {db_path}")
    return 0

def cmd_ingest_code(args: argparse.Namespace) -> int:
    root_dir = args.root_dir
    if not root_dir or not os.path.isdir(root_dir):
        print("ingest-code requires a valid directory path.", file=sys.stderr)
        return 2

    exts = set([e.strip().lower() for e in (args.ext or "").split(",") if e.strip()]) if args.ext else set(_DEFAULT_EXTS)
    if exts and not all(e.startswith(".") for e in exts):
        # normalize: allow 'py' -> '.py'
        exts = set([("." + e.lstrip(".")) for e in exts])

    snap = summarize_codebase(
        root_dir=root_dir,
        name=args.name or "aurora",
        exts=exts,
        max_file_bytes=args.max_file_kb * 1024,
        max_read_bytes=args.max_read_kb * 1024,
        include_hidden=args.include_hidden,
    )

    db_path = args.db or DEFAULT_DB_PATH
    db = _read_json(db_path) if os.path.exists(db_path) else {}
    db = merge_update_code(db, snap)
    _write_json(db_path, db, pretty=args.pretty)

    print(f"[OK] Ingested codebase: {snap.get('name')} ({snap.get('root_dir')})")
    print(f"[OK] Files indexed: {snap.get('stats', {}).get('files_total')}")
    print(f"[OK] Repo fingerprint: {(snap.get('fingerprint') or {}).get('sha1_repo')}")
    print(f"[OK] DB: {db_path}")
    return 0


# ----------------------------
# Claude share-link text ingestion
# ----------------------------
#
# Claude.ai share pages are pure SPAs — no public JSON API, content
# loads via JavaScript after page execution.  stdlib-only Python cannot
# fetch the rendered conversation.
#
# Workflow to get a conversation in:
#   1. Open the share link in your browser.
#   2. Copy all visible text from the page  (Ctrl-A / Select All → Copy).
#   3. Paste into a .txt file and add role markers before each turn:
#
#        [Human]
#        your message here
#
#        [Claude]
#        response text here
#
#        [Human]
#        ...
#
#   4. Run:  python chatscriber.py ingest-text conversation.txt --db <path>
#
# The markers are case-insensitive: [Human]/[User]/[Me] → role "user"
#                                   [Claude]/[Assistant]/[AI] → role "assistant"
#
# Lines that don't follow a marker are attached to the current speaker.

_HUMAN_HEADER   = re.compile(r"^\[(human|user|me)\]\s*$", re.I)
_CLAUDE_HEADER  = re.compile(r"^\[(claude|assistant|ai)\]\s*$", re.I)

def parse_text_conversation(text: str) -> List[Dict[str, Any]]:
    """
    Parse a plain-text conversation file into [{role, text}, ...].
    Expects [Human] / [Claude] markers on their own lines between turns.
    Falls back to a heuristic scan if no markers are found.
    """
    lines = (text or "").splitlines()

    # --- marker-based parse ---
    messages: List[Dict[str, Any]] = []
    current_role: Optional[str] = None
    buf: List[str] = []

    def flush():
        if current_role and buf:
            body = "\n".join(buf).strip()
            if body:
                messages.append({"role": current_role, "text": body})
        buf.clear()

    for ln in lines:
        stripped = ln.strip()
        if _HUMAN_HEADER.match(stripped):
            flush()
            current_role = "user"
        elif _CLAUDE_HEADER.match(stripped):
            flush()
            current_role = "assistant"
        else:
            buf.append(ln)

    flush()

    if messages:
        return messages

    # --- heuristic fallback: no markers found ---
    # Split on blank lines; odd blocks → user, even blocks → assistant
    # (rough but better than returning nothing)
    blocks = re.split(r"\n{2,}", text.strip())
    for i, block in enumerate(blocks):
        body = block.strip()
        if body:
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "text": body})

    return messages


def cmd_ingest_text(args: argparse.Namespace) -> int:
    """
    Ingest a plain-text Claude conversation saved from a share link.
    See module docstring above for the expected format.
    """
    path = args.input_file
    if not path or not os.path.isfile(path):
        print(f"File not found: {path}", file=sys.stderr)
        return 2

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    messages = parse_text_conversation(raw)
    if not messages:
        print("No messages parsed. Make sure the file has [Human]/[Claude] markers.", file=sys.stderr)
        return 1

    title = args.title or os.path.splitext(os.path.basename(path))[0]

    snap = {
        "title": title,
        "messages": messages,
        "fingerprint": {
            "sha1_text": _sha1(json.dumps(messages, ensure_ascii=False, sort_keys=True))
        },
        "stats": {
            "messages_total": len(messages),
            "user_messages":      sum(1 for m in messages if m["role"] == "user"),
            "assistant_messages": sum(1 for m in messages if m["role"] == "assistant"),
        },
        "top_terms": dict(_top_terms_from_bag(
            _bag(_tokenize(" ".join(m["text"] for m in messages))), n=30
        )),
        "high_signal_lines": [
            {"role": m["role"], "line": _first_line(m["text"], 220)}
            for m in sorted(messages,
                            key=lambda m: len(m["text"]) + 6 * len(re.findall(r"\b[A-Z][a-z]{2,}\b", m["text"])),
                            reverse=True)[:12]
            if m["text"].strip()
        ],
    }

    db_path = args.db or DEFAULT_DB_PATH
    db = _read_json(db_path) if os.path.exists(db_path) else {}
    db = merge_update_chat(db, snap)
    _write_json(db_path, db, pretty=args.pretty)

    print(f"[OK] Ingested: {title}")
    print(f"[OK] Messages: {len(messages)}  (user: {snap['stats']['user_messages']}, assistant: {snap['stats']['assistant_messages']})")
    print(f"[OK] DB: {db_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chatscriber.py",
        description="Chats Criteria: ingest ChatGPT share links, Claude conversations, and local codebases into a persistent continuity JSON (stdlib-only).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="Ingest a chatgpt.com/share/<id> link")
    ing.add_argument("target", help="Share link or share id")
    ing.add_argument("--db", default=DEFAULT_DB_PATH, help=f"Path to persistent JSON (default: {DEFAULT_DB_PATH})")
    ing.add_argument("--pretty", action="store_true", help="Pretty-print JSON output (default: compact)")
    ing.add_argument("--compact", action="store_true", help="Do NOT store full message transcript (highlights/stats only).")
    ing.set_defaults(func=cmd_ingest)

    ic = sub.add_parser("ingest-code", help="Ingest a local codebase directory into the continuity DB")
    ic.add_argument("root_dir", help="Root directory of codebase (e.g. /storage/emulated/0/Aurora)")
    ic.add_argument("--name", default="aurora", help="System name bucket (default: aurora)")
    ic.add_argument("--db", default=DEFAULT_DB_PATH, help=f"Path to persistent JSON (default: {DEFAULT_DB_PATH})")
    ic.add_argument("--pretty", action="store_true", help="Pretty-print JSON output (default: compact)")
    ic.add_argument("--ext", default="", help="Comma-separated extensions to include (default: common text/code). Example: .py,.md,.json")
    ic.add_argument("--max-file-kb", type=int, default=512, help="Skip files larger than this (KB). Default: 512")
    ic.add_argument("--max-read-kb", type=int, default=512, help="Read at most this many KB per file for analysis. Default: 512")
    ic.add_argument("--include-hidden", action="store_true", help="Include hidden files/dirs (default: off)")
    ic.set_defaults(func=cmd_ingest_code)

    it = sub.add_parser(
        "ingest-text",
        help="Ingest a Claude conversation saved as plain text (from a share link or paste).",
        description=(
            "Claude.ai share pages render via JavaScript — there is no public JSON API.\n"
            "Workflow: open the share link → copy all text → save to a .txt file with\n"
            "[Human] / [Claude] markers before each turn → run this command.\n\n"
            "Example file format:\n"
            "  [Human]\n"
            "  what does your crystal promotion ladder look like?\n\n"
            "  [Claude]\n"
            "  BASE crystals promote to COMPOSITE when ...\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    it.add_argument("input_file", help="Path to the plain-text conversation file")
    it.add_argument("--title", default="", help="Title for this conversation (default: filename)")
    it.add_argument("--db", default=DEFAULT_DB_PATH, help=f"Path to persistent JSON (default: {DEFAULT_DB_PATH})")
    it.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    it.set_defaults(func=cmd_ingest_text)

    return p

def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())

