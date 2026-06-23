#!/usr/bin/env python3
"""Verify the CodeAutoEvolver syntax safety gate.

apply_operator() must never overwrite a Python source file with content that
does not parse. This guards Aurora's self-modification path from corrupting its
own modules. Valid Python is still written normally.

Run standalone (pytest optional):

    python tests/test_autoevolver_syntax_gate.py
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.aurora_code_autoevolver import CodeAutoEvolver


def _run() -> None:
    with tempfile.TemporaryDirectory() as root:
        good = os.path.join(root, "good_module.py")
        bad = os.path.join(root, "bad_module.py")
        with open(good, "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("y = 2\n")

        ev = CodeAutoEvolver(repo_root=root)
        # Bypass plan generation; feed a controlled update set directly.
        ev._build_update_plan = lambda key, targets: {  # type: ignore[assignment]
            "updates": {
                good: "x = 42\n",                 # valid Python -> should write
                bad: "def broken(:\n    pass\n",  # malformed -> must be rejected
            },
            "details": [],
            "manifest": {},
        }

        result = ev.apply_operator("noop", [])

        # Valid file was rewritten.
        with open(good, "r", encoding="utf-8") as fh:
            assert fh.read() == "x = 42\n", "valid update should have been written"
        assert good in result["changed_files"], "valid file missing from changed_files"

        # Malformed file was NOT written and is reported as rejected.
        with open(bad, "r", encoding="utf-8") as fh:
            assert fh.read() == "y = 2\n", "malformed update must NOT corrupt the file"
        assert bad not in result["changed_files"], "rejected file must not be in changed_files"
        assert result["rejected_count"] == 1, "rejection should be counted"
        assert result["rejected"][0]["file"] == bad
        assert result["rejected"][0]["reason"] == "syntax_error"


def test_syntax_gate_blocks_malformed_writes() -> None:
    _run()


if __name__ == "__main__":
    _run()
    print("OK: autoevolver syntax gate rejects malformed Python and preserves valid writes.")
