#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import re
import secrets
import textwrap
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


SECTION_MARKER_RE = re.compile(r"(?m)^## ")
OPAQUE_BLOCK_RE = re.compile(
    r"(?ms)^\[\[GATE ([0-9a-f]{24})\]\]\n"
    r"VERIFY_SHA256: ([0-9a-f]{64})\n"
    r"PLAINTEXT_BYTES: (\d+)\n"
    r"CIPHERTEXT_BASE64:\n"
    r"(.*?)\n"
    r"\[\[/GATE \1\]\]\n?"
)
NUMBERED_BLOCK_RE = re.compile(
    r"(?ms)^\[\[SECTION (\d+)\]\]\n"
    r"EXPECTED_SHA256: ([0-9a-f]{64})\n"
    r"PLAINTEXT_BYTES: (\d+)\n"
    r"CIPHERTEXT_BASE64:\n"
    r"(.*?)\n"
    r"\[\[/SECTION \1\]\]\n?"
)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def split_top_level_sections(source_text: str) -> List[str]:
    matches = list(SECTION_MARKER_RE.finditer(source_text))
    if not matches:
        return [source_text]

    sections: List[str] = []
    first_start = matches[0].start()
    preamble = source_text[:first_start]
    if preamble:
        sections.append(preamble)

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(source_text)
        sections.append(source_text[start:end])
    return sections


def derive_first_working_key(master_key: str) -> str:
    return sha256_hex(f"FIRST|{master_key}")


def derive_next_working_key(previous_working_key: str, previous_plaintext: str) -> str:
    previous_sha = sha256_hex(previous_plaintext)
    return sha256_hex(f"{previous_working_key}\n{previous_sha}\n{previous_plaintext}")


def opaque_gate_id(working_key: str) -> str:
    return sha256_hex(f"GATE|{working_key}")[:24]


def keystream_bytes(working_key: str, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(f"{working_key}|{counter}".encode("utf-8")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def xor_cipher(plaintext: bytes, working_key: str) -> bytes:
    stream = keystream_bytes(working_key, len(plaintext))
    return bytes(p ^ s for p, s in zip(plaintext, stream))


def wrap_base64(data: bytes, width: int = 96) -> str:
    raw = base64.urlsafe_b64encode(data).decode("ascii")
    return "\n".join(textwrap.wrap(raw, width=width)) or raw


def unwrap_base64(data: str) -> bytes:
    compact = "".join(line.strip() for line in data.splitlines() if line.strip())
    return base64.urlsafe_b64decode(compact.encode("ascii"))


def build_encoded_document(
    source_name: str,
    source_text: str,
    master_key: str,
    *,
    style: str = "opaque-gates",
) -> str:
    sections = split_top_level_sections(source_text)
    working_key = derive_first_working_key(master_key)

    lines: List[str] = [
        "# AURORA SYSTEM DOSSIER - CHAINED COPY",
        "",
        "This copy is intentionally chained so each section depends on the exact plaintext of the section before it.",
        "",
        f"MASTER_KEY: {master_key}",
        f"SOURCE_FILE: {source_name}",
        f"SOURCE_SHA256: {sha256_hex(source_text)}",
        f"CHAIN_STYLE: {style}",
        'SECTION_BOUNDARY_RULE: "preamble before first ## heading, then each top-level ## section"',
        "",
        "KEY_SCHEDULE:",
        '  FIRST_WORKING_KEY = SHA256("FIRST|" + MASTER_KEY)',
        '  NEXT_WORKING_KEY = SHA256(previous_working_key + "\\n" + SHA256(previous_plaintext) + "\\n" + previous_plaintext)',
        "",
        "CIPHER:",
        '  block_i = SHA256(working_key + "|" + str(i))',
        "  keystream = block_0 || block_1 || ... truncated to plaintext length",
        "  ciphertext = plaintext_bytes XOR keystream",
        "  storage = urlsafe_base64(ciphertext)",
        "",
        "VERIFY:",
        "  After decrypting a section, confirm SHA256(decoded_plaintext) == EXPECTED_SHA256.",
        "  If the hash fails, every later section key will also fail.",
        "",
    ]

    for idx, plaintext in enumerate(sections):
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext = xor_cipher(plaintext_bytes, working_key)
        expected_sha = sha256_hex(plaintext)
        if style == "opaque-gates":
            gate_id = opaque_gate_id(working_key)
            lines.extend(
                [
                    f"[[GATE {gate_id}]]",
                    f"VERIFY_SHA256: {expected_sha}",
                    f"PLAINTEXT_BYTES: {len(plaintext_bytes)}",
                    "CIPHERTEXT_BASE64:",
                    wrap_base64(ciphertext),
                    f"[[/GATE {gate_id}]]",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"[[SECTION {idx:03d}]]",
                    f"EXPECTED_SHA256: {expected_sha}",
                    f"PLAINTEXT_BYTES: {len(plaintext_bytes)}",
                    "CIPHERTEXT_BASE64:",
                    wrap_base64(ciphertext),
                    f"[[/SECTION {idx:03d}]]",
                    "",
                ]
            )
        working_key = derive_next_working_key(working_key, plaintext)

    return "\n".join(lines).rstrip() + "\n"


def parse_encoded_document(encoded_text: str) -> Tuple[str, List[Tuple[str, str, int, str]]]:
    master_match = re.search(r"(?m)^MASTER_KEY: (.+)$", encoded_text)
    if master_match is None:
        raise ValueError("MASTER_KEY not found in encoded document")
    master_key = master_match.group(1).strip()

    blocks: List[Tuple[str, str, int, str]] = []
    for regex in (OPAQUE_BLOCK_RE, NUMBERED_BLOCK_RE):
        matches = list(regex.finditer(encoded_text))
        if not matches:
            continue
        for match in matches:
            block_id = match.group(1)
            expected_sha = match.group(2)
            plaintext_bytes = int(match.group(3))
            payload = match.group(4).strip()
            blocks.append((block_id, expected_sha, plaintext_bytes, payload))
        break

    if not blocks:
        raise ValueError("No chained sections found in encoded document")
    return master_key, blocks


def decode_sections(encoded_text: str, *, limit: int | None = None) -> List[str]:
    master_key, blocks = parse_encoded_document(encoded_text)
    working_key = derive_first_working_key(master_key)
    plaintext_sections: List[str] = []

    for index, (_block_id, expected_sha, plaintext_size, payload) in enumerate(blocks):
        if limit is not None and index >= limit:
            break
        ciphertext = unwrap_base64(payload)
        plaintext_bytes = xor_cipher(ciphertext, working_key)
        if len(plaintext_bytes) != plaintext_size:
            raise ValueError(
                f"Section {index:03d} byte count mismatch: expected {plaintext_size}, got {len(plaintext_bytes)}"
            )
        plaintext = plaintext_bytes.decode("utf-8")
        actual_sha = sha256_hex(plaintext)
        if actual_sha != expected_sha:
            raise ValueError(
                f"Section {index:03d} hash mismatch: expected {expected_sha}, got {actual_sha}"
            )
        plaintext_sections.append(plaintext)
        working_key = derive_next_working_key(working_key, plaintext)

    return plaintext_sections


def encode_command(args: argparse.Namespace) -> int:
    source_path = Path(args.source)
    output_path = Path(args.output)
    master_key = args.master_key or secrets.token_urlsafe(18)
    source_text = source_path.read_text(encoding="utf-8")
    encoded_text = build_encoded_document(
        source_path.name,
        source_text,
        master_key,
        style=str(args.style or "opaque-gates"),
    )
    output_path.write_text(encoded_text, encoding="utf-8")
    print(f"Wrote chained dossier to {output_path}")
    print(f"MASTER_KEY={master_key}")
    return 0


def decode_command(args: argparse.Namespace) -> int:
    encoded_path = Path(args.source)
    output_path = Path(args.output)
    encoded_text = encoded_path.read_text(encoding="utf-8")
    plaintext_sections = decode_sections(encoded_text, limit=args.limit)
    output_path.write_text("".join(plaintext_sections), encoding="utf-8")
    print(f"Decoded {len(plaintext_sections)} sections to {output_path}")
    return 0


def verify_command(args: argparse.Namespace) -> int:
    encoded_path = Path(args.source)
    encoded_text = encoded_path.read_text(encoding="utf-8")
    plaintext_sections = decode_sections(encoded_text, limit=args.limit)
    print(f"Verified {len(plaintext_sections)} chained sections from {encoded_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Encode or decode the Strata dossier as a chained, section-dependent document."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode_parser = subparsers.add_parser("encode", help="Create a chained encoded copy of a markdown dossier.")
    encode_parser.add_argument("source", help="Source markdown file to encode.")
    encode_parser.add_argument("output", help="Output path for the chained encoded copy.")
    encode_parser.add_argument(
        "--master-key",
        help="Optional master key. If omitted, a random key is generated and written into the output header.",
    )
    encode_parser.add_argument(
        "--style",
        choices=["opaque-gates", "numbered-sections"],
        default="opaque-gates",
        help="Output style. opaque-gates hides section numbering and uses derived gate IDs.",
    )
    encode_parser.set_defaults(func=encode_command)

    decode_parser = subparsers.add_parser("decode", help="Decode a chained encoded copy back into plaintext.")
    decode_parser.add_argument("source", help="Encoded dossier path.")
    decode_parser.add_argument("output", help="Output path for decoded plaintext.")
    decode_parser.add_argument(
        "--limit",
        type=int,
        help="Decode only the first N sections. Useful for spot checks.",
    )
    decode_parser.set_defaults(func=decode_command)

    verify_parser = subparsers.add_parser("verify", help="Verify chained decoding without writing plaintext.")
    verify_parser.add_argument("source", help="Encoded dossier path.")
    verify_parser.add_argument(
        "--limit",
        type=int,
        help="Verify only the first N sections.",
    )
    verify_parser.set_defaults(func=verify_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
