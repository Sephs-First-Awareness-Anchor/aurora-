#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo

import argparse
import requests
import json
import os
from bs4 import BeautifulSoup


def fetch_share_link(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (AuroraDoc/1.0)"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def extract_messages_from_html(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Try Next.js embedded JSON first (most reliable)
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    messages = []

    if script and script.string:
        try:
            data = json.loads(script.string)

            def walk(x):
                if isinstance(x, dict):
                    role = None
                    text = None

                    if "author" in x and isinstance(x["author"], dict):
                        role = x["author"].get("role")

                    if "content" in x:
                        c = x["content"]
                        if isinstance(c, dict):
                            parts = c.get("parts")
                            if isinstance(parts, list):
                                text = "\n".join(
                                    p for p in parts if isinstance(p, str)
                                )

                    if role in ("user", "assistant") and text:
                        messages.append((role, text.strip()))

                    for v in x.values():
                        walk(v)

                elif isinstance(x, list):
                    for i in x:
                        walk(i)

            walk(data)
        except Exception:
            pass

    # Fallback scrape if JSON path fails
    if not messages:
        text = soup.get_text("\n")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        role = None
        buffer = []

        def flush():
            nonlocal buffer, role
            if role and buffer:
                messages.append((role, "\n".join(buffer)))
            buffer = []

        for line in lines:
            low = line.lower()
            if low in ("you", "user"):
                flush()
                role = "user"
                continue
            if low in ("assistant", "chatgpt"):
                flush()
                role = "assistant"
                continue
            if role:
                buffer.append(line)

        flush()

    return messages


def write_transcript(messages, output_dir="chat_dump"):
    os.makedirs(output_dir, exist_ok=True)

    path = os.path.join(output_dir, "transcript.md")

    with open(path, "w", encoding="utf-8") as f:
        f.write("# Shared Chat Transcript\n\n")
        for role, text in messages:
            header = "User" if role == "user" else "Assistant"
            f.write(f"## {header}\n\n{text}\n\n")

    print(f"✔ Transcript saved to {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc", type=str, help="ChatGPT share link to document")
    args = parser.parse_args()

    if not args.doc:
        print("Provide a share link using --doc")
        return

    print("Fetching share link...")
    html = fetch_share_link(args.doc)

    print("Extracting messages...")
    messages = extract_messages_from_html(html)

    if not messages:
        print("⚠ Could not extract messages. The share link may require login.")
        return

    write_transcript(messages)


if __name__ == "__main__":
    main()
